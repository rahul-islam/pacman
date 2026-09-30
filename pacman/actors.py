"""Pac-Man and the ghosts.

Actors live on pixel coordinates but only change direction when they reach
the exact centre of a tile; `advance` walks centre to centre so speeds can be
any fraction of a pixel per frame.
"""

import math
import random

from . import art
from .config import MAZE_TOP, TILE, WIDTH
from .level import Level, cell_center

DIRS = {"right": (1, 0), "down": (0, 1), "left": (-1, 0), "up": (0, -1)}
OPPOSITE = {"right": "left", "left": "right", "up": "down", "down": "up"}
TURN_ORDER = ("up", "left", "down", "right")  # tie-break when paths are equally good
FRAME_MS = 125
EPS = 1e-6


class Actor:
    def __init__(self, level: Level, spawn: tuple[float, float]) -> None:
        self.level = level
        self.x, self.y = spawn
        self.dir = "left"
        self.moving = False

    @property
    def cell(self) -> tuple[int, int]:
        """Tile whose centre is nearest."""
        return round((self.x - TILE / 2) / TILE), round((self.y - MAZE_TOP - TILE / 2) / TILE)

    def centered(self) -> bool:
        cx, cy = cell_center(*self.cell)
        return abs(self.x - cx) < EPS and abs(self.y - cy) < EPS

    def can_go(self, direction: str) -> bool:
        c, r = self.cell
        dx, dy = DIRS[direction]
        return self.level.open(c + dx, r + dy)

    def arrive(self) -> None:
        """Called on reaching a tile centre; may change `dir` or stop."""

    def _gap(self) -> float:
        """Distance to the next tile centre ahead."""
        dx, dy = DIRS[self.dir]
        pos, origin, sign = (self.x, TILE / 2, dx) if dx else (self.y, MAZE_TOP + TILE / 2, dy)
        k = (pos - origin) / TILE
        nxt = math.floor(k + EPS) + 1 if sign > 0 else math.ceil(k - EPS) - 1
        return abs(nxt * TILE + origin - pos)

    def advance(self, distance: float) -> None:
        while distance > EPS and self.moving:
            if self.centered():
                self.x, self.y = cell_center(*self.cell)
                self.arrive()
                if not self.moving:
                    return
            gap = self._gap()
            step = min(distance, gap)
            dx, dy = DIRS[self.dir]
            self.x += dx * step
            self.y += dy * step
            if step == gap:
                self.x, self.y = cell_center(*self.cell)
            distance -= step
            # Tunnel wrap-around
            if self.x < -TILE / 2:
                self.x += WIDTH
            elif self.x > WIDTH + TILE / 2:
                self.x -= WIDTH

    def distance_to(self, other: "Actor") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


# ---------------------------------------------------------------------------
# Pac-Man
# ---------------------------------------------------------------------------
class PacMan(Actor):
    SPEED = 1.0

    def __init__(self, level: Level, skin: str) -> None:
        super().__init__(level, level.spawns["pacman"])
        self.art = art.pacman_art(skin)
        self.want: str | None = None
        self.dead = False
        self.dead_at = 0
        self.walk_ms = 0
        self.on_tile = None  # callback(col, row) when a tile centre is reached

    def steer(self, direction: str) -> None:
        self.want = direction
        if self.moving and direction == OPPOSITE[self.dir]:
            self.dir = direction  # reversing is allowed anywhere

    def arrive(self) -> None:
        if self.on_tile:
            self.on_tile(*self.cell)
        if self.want and self.can_go(self.want):
            self.dir = self.want
            self.moving = True
        else:
            self.moving = self.can_go(self.dir)

    def _start(self) -> None:
        if self.centered():
            self.arrive()
        elif self.want in ("left", "right") and abs(self.y - cell_center(*self.cell)[1]) < EPS:
            self.dir, self.moving = self.want, True  # spawn sits between two tiles
        elif self.want in ("up", "down") and abs(self.x - cell_center(*self.cell)[0]) < EPS:
            self.dir, self.moving = self.want, True

    def update(self, dt_ms: int) -> None:
        if self.dead:
            return
        if not self.moving and self.want:
            self._start()
        self.advance(self.SPEED)
        if self.moving:
            self.walk_ms += dt_ms

    def die(self, now: int) -> None:
        self.dead = True
        self.dead_at = now
        self.moving = False

    def death_done(self, now: int) -> bool:
        return self.dead and now - self.dead_at >= 2500

    def sprite(self, now: int):
        if self.dead:
            frames = self.art["dead"]
            return frames[min((now - self.dead_at) // FRAME_MS, len(frames) - 1)]
        frames = self.art["walk"][self.dir]
        return frames[(self.walk_ms // FRAME_MS) % len(frames)] if self.moving else frames[0]


# ---------------------------------------------------------------------------
# Ghosts
# ---------------------------------------------------------------------------
HOME, LEAVING, CHASE, SCATTER, FRIGHT, POPUP, EYES, ENTERING = (
    "home", "leaving", "chase", "scatter", "fright", "popup", "eyes", "entering")


class Ghost(Actor):
    name = ""
    corner = (0, 0)  # scatter target tile
    leave_share = 0.0  # fraction of pellets eaten before leaving the house
    scatter_ms = (6000, 3000, 1500)  # per difficulty tier
    HOUSE_SPEED = 0.5

    def __init__(self, level: Level, difficulty) -> None:
        super().__init__(level, level.spawns[self.name])
        self.difficulty = difficulty
        self.art = art.ghost_art(self.name)
        self.shared = art.shared_art()
        self.state = HOME
        self.bob = 1
        self.revived = False
        self.mode_at = self.fright_at = self.popup_at = 0
        self.popup_score = 0

    # -- targeting ---------------------------------------------------------
    def chase_target(self, pac: PacMan, blinky: "Ghost") -> tuple[int, int]:
        return pac.cell

    def goal(self, pac, blinky) -> tuple[int, int]:
        if self.state == EYES:
            return self.level.exit_cell
        if self.state == SCATTER:
            return self.corner
        return self.chase_target(pac, blinky)

    def arrive(self) -> None:
        if self.state == EYES and self.cell == self.level.exit_cell:
            self.state, self.moving = ENTERING, False
            return
        c, r = self.cell
        if self.state == EYES:
            # Follow the shortest path home; greedy steering can circle forever.
            steps = self.level.steps_home
            self.dir = min((d for d in TURN_ORDER if self.can_go(d)),
                           key=lambda d: steps.get(self.level.wrap(c + DIRS[d][0], r + DIRS[d][1]), math.inf))
            self.moving = True
            return
        options = [d for d in TURN_ORDER if d != OPPOSITE[self.dir] and self.can_go(d)] or [OPPOSITE[self.dir]]
        if self.state == FRIGHT:
            self.dir = random.choice(options)
        else:
            tx, ty = self._goal
            self.dir = min(options, key=lambda d: (c + DIRS[d][0] - tx) ** 2 + (r + DIRS[d][1] - ty) ** 2)
        self.moving = True

    # -- state changes -------------------------------------------------------
    def release(self) -> None:
        if self.state == HOME:
            self.state = LEAVING

    def frighten(self, now: int) -> None:
        if self.state in (CHASE, SCATTER, FRIGHT):
            self.state = FRIGHT
            self.fright_at = now

    def eat(self, now: int, score: int) -> None:
        self.state = POPUP
        self.popup_at = now
        self.popup_score = score
        self.moving = False

    @property
    def dangerous(self) -> bool:
        return self.state in (CHASE, SCATTER)

    @property
    def edible(self) -> bool:
        return self.state == FRIGHT

    def _roam(self, now: int, state: str) -> None:
        self.state = state
        self.mode_at = now
        self.dir = random.choice(("left", "right"))
        self.moving = True

    # -- per-frame update ----------------------------------------------------
    def _step_mode(self, now: int, pac: PacMan) -> None:
        if self.state == CHASE and now - self.mode_at >= self.difficulty.chase_ms:
            self.state, self.mode_at = SCATTER, now
        elif self.state == SCATTER and now - self.mode_at >= self.scatter_ms[self.difficulty.tier]:
            self.state, self.mode_at = CHASE, now

    def _move_to(self, x: float, y: float, speed: float) -> bool:
        """Scripted movement inside the house: x first, then y. True when there."""
        if abs(self.x - x) > EPS:
            self.x += max(-speed, min(speed, x - self.x))
            self.dir = "right" if x > self.x else "left"
            return False
        if abs(self.y - y) > EPS:
            self.y += max(-speed, min(speed, y - self.y))
            self.dir = "down" if y > self.y else "up"
            return False
        return True

    def update(self, now: int, pac: PacMan, blinky: "Ghost") -> None:
        if self.state == HOME:
            self.y += self.bob * self.HOUSE_SPEED
            if abs(self.y - self.level.spawns[self.name][1]) >= 3:
                self.bob = -self.bob
            self.dir = "down" if self.bob > 0 else "up"
            return
        if self.state == LEAVING:
            if self._move_to(*self.level.house_exit, self.HOUSE_SPEED):
                self._roam(now, SCATTER if self.revived else CHASE)
            return
        if self.state == ENTERING:
            if self._move_to(*self.level.house_center, 2.0):
                self.state, self.revived = LEAVING, True
            return
        if self.state == POPUP:
            if now - self.popup_at >= 500:
                self.state, self.moving = EYES, True
            return
        if self.state == FRIGHT and now - self.fright_at >= self.difficulty.fright_ms:
            self.state, self.mode_at = SCATTER, now
        self._step_mode(now, pac)

        speed = {FRIGHT: 0.5, EYES: 2.0}.get(self.state, 1.0)
        if self.state != EYES and self.level.slow(*self.cell):
            speed /= 2
        self._goal = self.goal(pac, blinky)
        self.advance(speed)

    def sprite(self, now: int):
        if self.state == POPUP:
            return None
        if self.state in (EYES, ENTERING):
            return self.shared["eyes"][self.dir][0]
        if self.state == FRIGHT:
            left = self.difficulty.fright_ms - (now - self.fright_at)
            frames = self.shared["flash" if left < 2000 else "scared"]
        else:
            frames = self.art["walk"][self.dir]
        return frames[(now // FRAME_MS) % len(frames)]


class Blinky(Ghost):
    """Red: heads straight for Pac-Man. Starts outside the house."""

    name = "blinky"
    corner = (25, -3)

    def __init__(self, level, difficulty) -> None:
        super().__init__(level, difficulty)
        self._roam(0, CHASE)


class Pinky(Ghost):
    """Pink: aims two tiles ahead of Pac-Man."""

    name = "pinky"
    corner = (2, -3)

    def chase_target(self, pac, blinky):
        (c, r), (dx, dy) = pac.cell, DIRS[pac.dir]
        return c + 2 * dx, r + 2 * dy


class Inky(Ghost):
    """Cyan: flanks, using Blinky's position mirrored past Pac-Man."""

    name = "inky"
    corner = (27, 32)
    leave_share = 0.08
    scatter_ms = (5000, 3000, 1000)

    def chase_target(self, pac, blinky):
        (c, r), (dx, dy) = pac.cell, DIRS[pac.dir]
        ax, ay = c + 2 * dx, r + 2 * dy
        bx, by = blinky.cell
        return 2 * ax - bx, 2 * ay - by


class Clyde(Ghost):
    """Orange: chases from afar, retreats to his corner when close."""

    name = "clyde"
    corner = (0, 32)
    leave_share = 0.15

    def _step_mode(self, now, pac) -> None:
        (c, r), (pc, pr) = self.cell, pac.cell
        near = math.hypot(c - pc, r - pr) <= 8
        if self.state == CHASE and near:
            self.state = SCATTER
        elif self.state == SCATTER and not near:
            self.state = CHASE


GHOST_TYPES = (Blinky, Pinky, Inky, Clyde)
