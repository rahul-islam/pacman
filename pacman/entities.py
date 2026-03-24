"""Game entities: Character, PacMan, ghosts, Fruit, FloatingScore."""

import math
import random
import pygame
from .constants import (
    TILE_SIZE, HALF_TILE, COLS, ROWS, HEADER_HEIGHT,
    DIR_RIGHT, DIR_LEFT, DIR_UP, DIR_DOWN, DIR_NONE,
    DIRECTION_VEC, OPPOSITE_DIR, ALL_DIRS,
    PACMAN_SPEED, GHOST_SPEED, FRIGHTENED_SPEED, EATEN_SPEED, TUNNEL_SPEED,
    FRIGHTENED_MS, FRIGHTENED_FLASH_MS, FRIGHT_TIMES, GHOST_RELEASE_MS,
    MODE_DURATIONS,
    POINTS_APPLE, POINTS_STRAWBERRY, POINTS_GHOST_BASE,
    GHOST_HOUSE_ENTRANCE, GHOST_HOUSE_CENTER, PACMAN_SPAWN, FRUIT_POS,
    SCATTER_TARGETS, GHOST_STARTS, TUNNEL_ROW,
    T_WALL,
    GhostMode,
    BLUE, WHITE,
    tile_to_pixel, pixel_to_cell, is_at_cell_center,
)


# ---------------------------------------------------------------------------
# Character base
# ---------------------------------------------------------------------------

class Character:
    """Shared movement logic for Pac-Man and ghosts."""

    def __init__(self, start_col, start_row, speed):
        self.base_speed = speed
        self.speed = speed
        self.direction = DIR_NONE
        self.shift_x = 0
        self.shift_y = 0
        self._moving = False
        # Pixel position (center)
        self.px, self.py = tile_to_pixel(start_col, start_row)

    def get_cell(self):
        return pixel_to_cell(self.px, self.py)

    def at_center(self):
        """Check if the character is at (or within its speed of) a cell
        center.  Using the current speed as tolerance prevents the entity
        from overshooting the center when the speed doesn't share a parity
        with the tile grid (e.g. after moving at FRIGHTENED_SPEED = 1 then
        switching back to speed 2)."""
        return is_at_cell_center(self.px, self.py, tolerance=max(self.speed - 1, 0))

    def _snap_if_close(self):
        """If within *speed* pixels of a cell center, snap exactly onto it.
        This must be called whenever at_center() returns True so that the
        position is authoritative for subsequent direction / collision logic."""
        cx = (self.px - HALF_TILE) % TILE_SIZE
        cy = (self.py - HEADER_HEIGHT - HALF_TILE) % TILE_SIZE
        tol = max(self.speed - 1, 0)
        if cx != 0 and (cx <= tol or cx >= TILE_SIZE - tol):
            col, _ = self.get_cell()
            self.px = col * TILE_SIZE + HALF_TILE
        if cy != 0 and (cy <= tol or cy >= TILE_SIZE - tol):
            _, row = self.get_cell()
            self.py = row * TILE_SIZE + HEADER_HEIGHT + HALF_TILE

    def set_direction(self, d):
        self.direction = d
        self.shift_x, self.shift_y = DIRECTION_VEC[d]

    def go(self):
        self._moving = True

    def stop(self):
        self._moving = False
        self.shift_x = 0
        self.shift_y = 0

    def step(self):
        if not self._moving:
            return
        self.px += self.shift_x * self.speed
        self.py += self.shift_y * self.speed
        # Tunnel wrapping — only on the tunnel row
        _, row = pixel_to_cell(int(self.px), int(self.py))
        if row == TUNNEL_ROW:
            total_w = COLS * TILE_SIZE
            if self.px < -HALF_TILE:
                self.px += total_w + TILE_SIZE
            elif self.px > total_w + HALF_TILE:
                self.px -= total_w + TILE_SIZE

    def snap_to_center(self):
        col, row = self.get_cell()
        self.px, self.py = tile_to_pixel(col, row)


# ---------------------------------------------------------------------------
# Pac-Man
# ---------------------------------------------------------------------------

class PacMan(Character):

    ANIM_CYCLE = [0, 1, 2, 1]

    def __init__(self):
        sc, sr = PACMAN_SPAWN
        super().__init__(sc, sr, PACMAN_SPEED)
        self.queued_dir = DIR_LEFT
        self.alive = True
        self.anim_frame = 0
        self.anim_counter = 0

    def reset(self):
        sc, sr = PACMAN_SPAWN
        self.px, self.py = tile_to_pixel(sc, sr)
        self.direction = DIR_NONE
        self.queued_dir = DIR_LEFT
        self.speed = self.base_speed
        self.shift_x = self.shift_y = 0
        self._moving = False
        self.alive = True
        self.anim_frame = 0
        self.anim_counter = 0

    def update(self, maze):
        if not self.alive:
            return

        # Animate while moving
        if self._moving:
            self.anim_counter += 1
            if self.anim_counter >= 5:
                self.anim_counter = 0
                self.anim_frame = (self.anim_frame + 1) % len(self.ANIM_CYCLE)

        # Direction changes only at cell centers
        if self.at_center():
            self._snap_if_close()
            col, row = self.get_cell()
            # Try queued direction
            if maze.can_move(col, row, self.queued_dir, is_ghost=False):
                self.set_direction(self.queued_dir)
                self.go()
            elif self.direction != DIR_NONE and maze.can_move(col, row, self.direction, is_ghost=False):
                # Continue current direction
                self.go()
            else:
                self.stop()

        self.step()

    def draw(self, surface, assets):
        if not self.alive:
            return
        d = self.direction if self.direction != DIR_NONE else DIR_LEFT
        frames = assets.get(f"pacman_{d}", assets["pacman_left"])
        idx = self.ANIM_CYCLE[self.anim_frame]
        surface.blit(frames[idx],
                     (self.px - HALF_TILE, self.py - HALF_TILE))


# ---------------------------------------------------------------------------
# Base ghost
# ---------------------------------------------------------------------------

class BaseGhost(Character):
    """Common ghost behavior. Subclass to define chase_ai/scatter_ai."""

    scatter_target: tuple = (0, 0)
    release_dots: int = 0  # dots Pac-Man must eat before this ghost exits house

    def __init__(self, name, index):
        sc, sr = GHOST_STARTS[name]
        super().__init__(sc, sr, GHOST_SPEED)
        self.name = name
        self.index = index
        self.mode = GhostMode.INDOOR if index != 0 else GhostMode.SCATTER
        self.prev_mode = GhostMode.SCATTER
        self.fright_start = 0
        self.fright_duration = FRIGHTENED_MS
        self.mode_start = 0
        self.mode_index = 0
        self.bob_dir = 1
        self.release_ms = GHOST_RELEASE_MS[index]
        self.spawn_time = 0
        self._exiting = False
        self._entering_house = False
        self._bob_tick = 0

    def reset(self, now_ms=0):
        sc, sr = GHOST_STARTS[self.name]
        self.px, self.py = tile_to_pixel(sc, sr)
        self.speed = self.base_speed
        self.shift_x = self.shift_y = 0
        self._moving = False
        self.mode = GhostMode.INDOOR if self.index != 0 else GhostMode.SCATTER
        self.prev_mode = GhostMode.SCATTER
        self.direction = DIR_LEFT if self.index == 0 else DIR_UP
        self.fright_start = 0
        self.fright_duration = FRIGHTENED_MS
        self.mode_start = now_ms
        self.mode_index = 0
        self.bob_dir = 1
        self.spawn_time = now_ms
        self._exiting = False
        self._entering_house = False
        self._bob_tick = 0

    # ------------------------------------------------------------------
    # AI entry point
    # ------------------------------------------------------------------
    def update(self, maze, pacman, blinky, now_ms, total_dots, dots_eaten, level):
        if self.mode == GhostMode.INDOOR:
            self._indoor_ai(maze, now_ms, total_dots, dots_eaten)
            return

        # Eaten ghost entering house (multi-step animation)
        if self._entering_house:
            self._enter_house_step(now_ms)
            return

        self._update_speed(maze, total_dots - dots_eaten, level)

        if self.mode == GhostMode.FRIGHTENED:
            elapsed = now_ms - self.fright_start
            if elapsed >= self.fright_duration:
                self.mode = self.prev_mode
                # Compensate mode_start so the scatter/chase timer resumes
                # where it left off (timer was effectively paused during fright)
                self.mode_start += elapsed
                self.fright_start = 0
                # Snap position so the new (faster) speed stays aligned
                # with the tile grid.  Frightened speed may have shifted
                # the position to an alignment incompatible with the
                # normal speed, which would cause the ghost to skip
                # every cell center and fly through walls.
                self.snap_to_center()

        # Check scatter/chase timer BEFORE choosing direction.
        # On a mode switch the ghost must immediately reverse direction
        # and skip pathfinding for this frame (authentic Pac-Man behavior).
        if self.mode in (GhostMode.SCATTER, GhostMode.CHASE):
            if self._check_mode_timer(now_ms):
                # Mode just switched — reverse already applied, keep moving
                self.go()
                self.step()
                return

        if self.at_center():
            self._snap_if_close()
            col, row = self.get_cell()
            # Eaten ghost reaching house entrance — start entering
            if self.mode == GhostMode.EATEN:
                ec, er = GHOST_HOUSE_ENTRANCE
                if col == ec and row == er:
                    self.snap_to_center()
                    self._entering_house = True
                    self.stop()
                    return

            self._choose_direction(maze, pacman, blinky, now_ms)
            self.go()

        # Safety: if the next step would land on a wall tile or go
        # out of bounds (except tunnel row), stop and snap to grid.
        if self._moving and self.direction != DIR_NONE:
            next_px = self.px + self.shift_x * self.speed
            next_py = self.py + self.shift_y * self.speed
            nc, nr = pixel_to_cell(int(next_px), int(next_py))
            blocked = False
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                blocked = maze.grid[nr][nc] == T_WALL
            elif nr != TUNNEL_ROW:
                # Out of bounds and not in the tunnel — illegal
                blocked = True
            if blocked:
                self.snap_to_center()
                self.stop()
                return

        self.step()

    def _enter_house_step(self, now_ms):
        """Animate eaten ghost moving down into house center, then
        horizontally to align with the center column."""
        hc_x, hc_y = tile_to_pixel(*GHOST_HOUSE_CENTER)
        enter_speed = 2

        # Phase A: move down from entrance to house-center row
        if self.py < hc_y:
            self.py = min(self.py + enter_speed, hc_y)
            return

        # Phase B: align X with house center column
        if self.px != hc_x:
            if abs(self.px - hc_x) <= enter_speed:
                self.px = hc_x
            else:
                self.px += enter_speed if self.px < hc_x else -enter_speed
            return

        # Arrived at house center
        self.px, self.py = hc_x, hc_y
        self.mode = GhostMode.INDOOR
        self._entering_house = False
        self._exiting = True  # immediately start exiting
        self.release_ms = 500
        self.spawn_time = now_ms
        self.stop()

    def _choose_direction(self, maze, pacman, blinky, now_ms):
        col, row = self.get_cell()
        # Only eaten ghosts may path through the door / into the house
        allow = self.mode == GhostMode.EATEN
        valid = maze.get_valid_directions(col, row, self.direction,
                                          is_ghost=True, allow_house=allow)
        if not valid:
            rev = OPPOSITE_DIR[self.direction]
            valid = [rev]

        if self.mode == GhostMode.FRIGHTENED:
            self.set_direction(random.choice(valid))
            return

        # Determine target
        if self.mode == GhostMode.SCATTER:
            target = self.scatter_target
        elif self.mode == GhostMode.CHASE:
            target = self.chase_target(pacman, blinky)
        elif self.mode == GhostMode.EATEN:
            target = GHOST_HOUSE_ENTRANCE
        else:
            target = self.scatter_target

        # Pick direction minimizing distance to target
        best = valid[0]
        best_dist = float("inf")
        for d in valid:
            dx, dy = DIRECTION_VEC[d]
            nc, nr = col + dx, row + dy
            dist = (nc - target[0]) ** 2 + (nr - target[1]) ** 2
            if dist < best_dist:
                best_dist = dist
                best = d
        self.set_direction(best)

    def _check_mode_timer(self, now_ms):
        """Return True if a mode switch occurred (ghost reversed direction)."""
        if self.mode_index >= len(MODE_DURATIONS):
            return False
        dur = MODE_DURATIONS[self.mode_index]
        if dur == -1:
            return False
        if now_ms - self.mode_start >= dur:
            self.mode_start = now_ms
            self.mode_index += 1
            new_mode = GhostMode.SCATTER if self.mode_index % 2 == 0 else GhostMode.CHASE
            switched = self.mode != new_mode
            if switched:
                self.direction = OPPOSITE_DIR.get(self.direction, self.direction)
                self.set_direction(self.direction)
            self.mode = new_mode
            self.prev_mode = new_mode
            return switched
        return False

    def chase_target(self, pacman, blinky):
        """Override in subclass."""
        return pacman.get_cell()

    # ------------------------------------------------------------------
    # State changes
    # ------------------------------------------------------------------
    def enter_frightened(self, now_ms, level=1):
        if self.mode in (GhostMode.EATEN, GhostMode.INDOOR):
            return
        # Look up per-level fright duration
        idx = min(level - 1, len(FRIGHT_TIMES) - 1)
        fright_ms = FRIGHT_TIMES[idx] if idx >= 0 else 0
        already_frightened = self.mode == GhostMode.FRIGHTENED
        if not already_frightened:
            self.prev_mode = self.mode
            # Always reverse on first fright trigger
            rev = OPPOSITE_DIR.get(self.direction, self.direction)
            self.set_direction(rev)
        if fright_ms == 0:
            # No frightened time at this level — just reverse, don't turn blue
            return
        self.mode = GhostMode.FRIGHTENED
        self.fright_start = now_ms
        self.fright_duration = fright_ms
        self.speed = FRIGHTENED_SPEED

    def get_eaten(self, now_ms):
        self.mode = GhostMode.EATEN
        self.fright_start = 0
        self.speed = EATEN_SPEED

    # ------------------------------------------------------------------
    # Indoor (ghost house)
    # ------------------------------------------------------------------
    def _indoor_ai(self, maze, now_ms, total_dots, dots_eaten):
        center_x, center_y = tile_to_pixel(*GHOST_HOUSE_CENTER)
        entrance_x, entrance_y = tile_to_pixel(*GHOST_HOUSE_ENTRANCE)

        if not self._exiting:
            # Phase 1: Bob up and down at start position.
            # Use integer movement (1 px every other frame) to avoid
            # introducing float positions that break pixel_to_cell
            # and is_at_cell_center elsewhere in the engine.
            self._bob_tick += 1
            if self._bob_tick % 2 == 0:
                self.py += self.bob_dir
                # Only check the boundary AFTER a movement frame,
                # otherwise the reversal gets toggled on non-movement
                # frames (py unchanged, still past threshold) causing
                # the ghost to drift indefinitely.
                if abs(self.py - center_y) >= HALF_TILE:
                    self.bob_dir *= -1

            # Check release conditions: dot-count threshold or timer
            elapsed = now_ms - self.spawn_time
            if elapsed >= self.release_ms or dots_eaten >= self.release_dots:
                self._exiting = True
                self.py = center_y  # snap Y to center row
            return

        # Phase 2: Move horizontally to center column
        if abs(self.px - center_x) > 1:
            self.px += 1 if self.px < center_x else -1
            return

        # Phase 3: Move up toward entrance
        self.px = center_x  # snap X
        if self.py > entrance_y + 1:
            self.py -= 2
            return

        # Phase 4: Reached entrance — fully exit house
        self.px, self.py = entrance_x, entrance_y
        self.snap_to_center()
        self._exiting = False
        self.mode = self.prev_mode
        self.mode_start = now_ms
        # Pick initial direction using pathfinding
        self.set_direction(DIR_LEFT)
        self.go()

    # ------------------------------------------------------------------
    # Speed
    # ------------------------------------------------------------------
    def _update_speed(self, maze, dots_remaining, level):
        if self.mode == GhostMode.FRIGHTENED:
            self.speed = FRIGHTENED_SPEED
            return
        if self.mode == GhostMode.EATEN:
            self.speed = EATEN_SPEED
            return
        col, row = self.get_cell()
        if row == TUNNEL_ROW and (col < 6 or col > 21):
            self.speed = TUNNEL_SPEED
            return
        base = GHOST_SPEED
        # Slight speed increase at higher levels
        if level >= 5:
            base = 3
        # Cruise Elroy — Blinky speeds up in two stages as dots dwindle.
        # Thresholds increase with level (level 1: 20/10, level 2: 30/15,
        # level 3+: 40/20).  With integer speeds, both stages map to
        # speed 3 (the next divisor of TILE_SIZE above 2).
        if self.name == "blinky":
            if level == 1:
                elroy1, elroy2 = 20, 10
            elif level == 2:
                elroy1, elroy2 = 30, 15
            else:
                elroy1, elroy2 = 40, 20
            if dots_remaining <= elroy1:
                base = max(base, 3)
        self.speed = base

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface, assets, now_ms):
        if self.mode == GhostMode.EATEN:
            self._draw_eyes(surface)
            return

        if self.mode == GhostMode.FRIGHTENED:
            remaining = self.fright_duration - (now_ms - self.fright_start)
            flashing = remaining < FRIGHTENED_FLASH_MS and (now_ms // 150) % 2 == 1
            img = assets["white_ghost"] if flashing else assets["blue_ghost"]
        else:
            img = assets[self.name]

        surface.blit(img, (self.px - HALF_TILE, self.py - HALF_TILE))

    def _draw_eyes(self, surface):
        cx, cy = int(self.px), int(self.py)
        eye_data = {
            DIR_RIGHT: ((-3, -2), (3, -2), (1, 0)),
            DIR_LEFT:  ((-3, -2), (3, -2), (-1, 0)),
            DIR_UP:    ((-3, -2), (3, -2), (0, -2)),
            DIR_DOWN:  ((-3, -2), (3, -2), (0, 2)),
        }
        le, re, po = eye_data.get(self.direction, eye_data[DIR_RIGHT])
        for ex, ey in (le, re):
            pygame.draw.circle(surface, WHITE, (cx + ex, cy + ey), 3)
            pygame.draw.circle(surface, BLUE,
                               (cx + ex + po[0], cy + ey + po[1]), 1)


# ---------------------------------------------------------------------------
# Concrete ghosts
# ---------------------------------------------------------------------------

class Blinky(BaseGhost):
    """Red — direct pursuit."""
    scatter_target = SCATTER_TARGETS["blinky"]
    release_dots = 0

    def __init__(self):
        super().__init__("blinky", 0)
        self.mode = GhostMode.SCATTER
        self.prev_mode = GhostMode.SCATTER
        self.set_direction(DIR_LEFT)
        self.go()

    def reset(self, now_ms=0):
        super().reset(now_ms)
        self.mode = GhostMode.SCATTER
        self.prev_mode = GhostMode.SCATTER
        self.set_direction(DIR_LEFT)
        self.go()

    def chase_target(self, pacman, blinky):
        return pacman.get_cell()


class Pinky(BaseGhost):
    """Pink — ambush 4 cells ahead (matching original Pac-Man)."""
    scatter_target = SCATTER_TARGETS["pinky"]
    release_dots = 0

    def __init__(self):
        super().__init__("pinky", 1)

    def chase_target(self, pacman, blinky):
        pc, pr = pacman.get_cell()
        dx, dy = DIRECTION_VEC.get(pacman.direction, (0, 0))
        tc, tr = pc + dx * 4, pr + dy * 4
        # Original arcade overflow bug: when Pac-Man faces UP,
        # the target is also shifted 4 tiles to the left.
        if pacman.direction == DIR_UP:
            tc -= 4
        return (tc, tr)


class Inky(BaseGhost):
    """Cyan — flanking (vector from Blinky through 2-ahead)."""
    scatter_target = SCATTER_TARGETS["inky"]
    release_dots = 30

    def __init__(self):
        super().__init__("inky", 2)

    def chase_target(self, pacman, blinky):
        pc, pr = pacman.get_cell()
        dx, dy = DIRECTION_VEC.get(pacman.direction, (0, 0))
        ahead_c, ahead_r = pc + dx * 2, pr + dy * 2
        # Original arcade overflow bug: when Pac-Man faces UP,
        # the intermediate point is also shifted 2 tiles left.
        if pacman.direction == DIR_UP:
            ahead_c -= 2
        bc, br = blinky.get_cell()
        return (2 * ahead_c - bc, 2 * ahead_r - br)


class Clyde(BaseGhost):
    """Orange — shy (scatter when close)."""
    scatter_target = SCATTER_TARGETS["clyde"]
    release_dots = 60

    def __init__(self):
        super().__init__("clyde", 3)

    def chase_target(self, pacman, blinky):
        pc, pr = pacman.get_cell()
        gc, gr = self.get_cell()
        dist = math.sqrt((pc - gc) ** 2 + (pr - gr) ** 2)
        if dist > 8:
            return (pc, pr)
        return self.scatter_target


def create_ghosts():
    """Factory: create all four ghosts."""
    return [Blinky(), Pinky(), Inky(), Clyde()]


# ---------------------------------------------------------------------------
# Fruit
# ---------------------------------------------------------------------------

class Fruit:
    def __init__(self):
        self.active = False
        self.type = "apple"
        self.timer = 0
        self.points = 0
        self.spawn_time = 0

    def spawn(self, level, now_ms):
        self.active = True
        self.type = "apple" if level % 2 == 1 else "strawberry"
        self.points = POINTS_APPLE if level % 2 == 1 else POINTS_STRAWBERRY
        self.spawn_time = now_ms

    def update(self, now_ms):
        if self.active and now_ms - self.spawn_time > 10000:
            self.active = False

    def draw(self, surface, assets):
        if not self.active:
            return
        cx, cy = tile_to_pixel(*FRUIT_POS)
        img = assets[self.type]
        surface.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


# ---------------------------------------------------------------------------
# Floating score popup
# ---------------------------------------------------------------------------

class FloatingScore:
    def __init__(self, text, x, y, now_ms, duration_ms=1000):
        self.text = text
        self.x = x
        self.y = y
        self.start = now_ms
        self.duration = duration_ms
        self._rise_speed = 0.3  # pixels per update tick

    def alive(self, now_ms):
        return now_ms - self.start < self.duration

    def update(self):
        """Move the score upward. Call once per logic tick, not in draw."""
        self.y -= self._rise_speed

    def draw(self, surface, font, now_ms):
        txt = font.render(self.text, True, WHITE)
        surface.blit(txt, (self.x - txt.get_width() // 2,
                           self.y - txt.get_height() // 2))
