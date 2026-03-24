"""Scene system: MenuScene, GameplayScene, GameOverScene."""

import pygame
from .constants import (
    TILE_SIZE, HALF_TILE, SCREEN_WIDTH, HEADER_HEIGHT,
    DIR_RIGHT, DIR_LEFT, DIR_UP, DIR_DOWN,
    PACMAN_SPEED, POINTS_GHOST_BASE, EXTRA_LIFE_SCORE, FRUIT_POS,
    GhostMode, GamePhase,
    BLACK, WHITE, YELLOW, RED, PINK, CYAN, ORANGE,
    tile_to_pixel,
)
from .maze import Maze
from .entities import PacMan, create_ghosts, Fruit, FloatingScore
from . import renderer


# ---------------------------------------------------------------------------
# Scene base + manager
# ---------------------------------------------------------------------------

class Scene:
    def handle_event(self, event): pass
    def update(self): pass
    def draw(self, surface): pass


class SceneManager:
    def __init__(self):
        self.current: Scene | None = None
        self._next: Scene | None = None

    def switch_to(self, scene):
        self._next = scene

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self):
        if self._next is not None:
            self.current = self._next
            self._next = None
        if self.current:
            self.current.update()

    def draw(self, surface):
        if self.current:
            self.current.draw(surface)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

class MenuScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.ctx["scene_manager"].switch_to(GameplayScene(self.ctx))

    def draw(self, surface):
        ctx = self.ctx
        a, f, fc = ctx["assets"], ctx["fonts"], ctx["frame_count"]
        surface.fill(BLACK)

        title = f["large"].render("PAC-MAN", True, YELLOW)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        cyc = [0, 1, 2, 1]
        surface.blit(a["pacman_right"][cyc[(fc // 8) % 4]],
                     (SCREEN_WIDTH // 2 - HALF_TILE, 170))

        names = ["blinky", "pinky", "inky", "clyde"]
        cols = [RED, PINK, CYAN, ORANGE]
        spacing = 80
        sx = SCREEN_WIDTH // 2 - (spacing * 3) // 2
        for i, n in enumerate(names):
            x = sx + i * spacing
            surface.blit(a[n], (x - HALF_TILE, 220))
            lbl = f["small"].render(n.upper(), True, cols[i])
            surface.blit(lbl, (x - lbl.get_width() // 2, 250))

        for i, line in enumerate([
            "Arrow Keys / WASD to move",
            "Eat all dots to clear the level",
            "Avoid ghosts! Eat power pellets to fight back!",
        ]):
            t = f["small"].render(line, True, WHITE)
            surface.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 320 + i * 30))

        hs = f["medium"].render(f"HIGH SCORE: {ctx['high_score']}", True, CYAN)
        surface.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 440))

        if (fc // 30) % 2 == 0:
            p = f["medium"].render("Press ENTER to Start", True, YELLOW)
            surface.blit(p, (SCREEN_WIDTH // 2 - p.get_width() // 2, 500))


# ---------------------------------------------------------------------------
# Gameplay
# ---------------------------------------------------------------------------

class GameplayScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx
        self.sound = ctx.get("sound")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.dots_eaten = 0
        self.ghost_eat_combo = POINTS_GHOST_BASE
        self.extra_life_given = False
        self.floating_scores: list[FloatingScore] = []
        self.fruit_spawns: list[int] = []
        self._current_siren: int = -1  # tracks which siren level is playing

        self.maze = Maze()
        self.pacman = PacMan()
        self.ghosts = create_ghosts()
        self.fruit = Fruit()

        self.phase = GamePhase.INTRO
        self.phase_start = pygame.time.get_ticks()
        self._start_level()

    def _now(self):
        return pygame.time.get_ticks()

    # ------------------------------------------------------------------
    # Level / life management
    # ------------------------------------------------------------------
    def _start_level(self):
        self.maze.reset()
        self.maze.render_walls()
        self.dots_eaten = 0
        self.fruit = Fruit()
        self.fruit_spawns = []
        self.ghost_eat_combo = POINTS_GHOST_BASE
        self._current_siren = -1  # force siren re-evaluation
        self.floating_scores = []
        self._reset_positions()
        self.phase = GamePhase.INTRO
        self.phase_start = self._now()
        if self.sound:
            self.sound.stop_all()
            self.sound.play_start()

    def _reset_positions(self):
        now = self._now()
        self.pacman.reset()
        if self.level >= 5:
            self.pacman.speed = 3
        for g in self.ghosts:
            g.reset(now)
            # Compute release time from the original base, not the already-reduced value
            from .constants import GHOST_RELEASE_MS
            base_release = GHOST_RELEASE_MS[g.index]
            g.release_ms = max(base_release - (self.level - 1) * 500, 0)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.phase in (GamePhase.READY, GamePhase.PLAYING, GamePhase.INTRO):
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.pacman.queued_dir = DIR_RIGHT
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.pacman.queued_dir = DIR_LEFT
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.pacman.queued_dir = DIR_UP
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.pacman.queued_dir = DIR_DOWN

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self):
        now = self._now()
        elapsed = now - self.phase_start

        if self.phase == GamePhase.INTRO:
            # Wait for start sound to finish (or 4s max)
            if self.sound and not self.sound.start_sound_done() and elapsed < 4500:
                return
            self.phase = GamePhase.READY
            self.phase_start = now

        elif self.phase == GamePhase.READY:
            if elapsed >= 2000:
                self.phase = GamePhase.PLAYING
                self.phase_start = now
                if self.sound:
                    self.sound.play_siren(0)

        elif self.phase == GamePhase.PLAYING:
            self._update_playing(now)

        elif self.phase == GamePhase.DEATH:
            if elapsed >= 2000:
                if self.lives > 0:
                    self._reset_positions()
                    self.phase = GamePhase.READY
                    self.phase_start = now
                else:
                    self._save_high_score()
                    self.ctx["scene_manager"].switch_to(
                        GameOverScene(self.ctx, self.score))

        elif self.phase == GamePhase.LEVEL_COMPLETE:
            if elapsed >= 3000:
                self.level += 1
                self._start_level()

    def _update_playing(self, now):
        self.pacman.update(self.maze)

        # Dot eating — only consume when Pac-Man is exactly on a tile center
        col, row = self.pacman.get_cell()
        if self.pacman.at_center():
            points, is_pellet = self.maze.eat_dot(col, row)
        else:
            points, is_pellet = 0, False
        if points > 0:
            self.score += points
            self.dots_eaten += 1

            if points > 0 and self.sound:
                self.sound.play_eat_dot()

            if is_pellet:
                self.ghost_eat_combo = POINTS_GHOST_BASE
                for g in self.ghosts:
                    g.enter_frightened(now)
                if self.sound:
                    self.sound.play_fright()

            if self.dots_eaten in (70, 170) and self.dots_eaten not in self.fruit_spawns:
                self.fruit_spawns.append(self.dots_eaten)
                self.fruit.spawn(self.level, now)

            if not self.extra_life_given and self.score >= EXTRA_LIFE_SCORE:
                self.lives += 1
                self.extra_life_given = True
                if self.sound:
                    self.sound.play_extra_life()

            self._update_high_score()

            if self.maze.total_dots <= 0:
                self.phase = GamePhase.LEVEL_COMPLETE
                self.phase_start = now
                if self.sound:
                    self.sound.stop_all()
                    self.sound.play_intermission()
                return

        # Update siren based on dots remaining
        any_fright = any(g.mode == GhostMode.FRIGHTENED for g in self.ghosts)
        any_eaten = any(g.mode == GhostMode.EATEN for g in self.ghosts)

        if not any_fright and not any_eaten:
            remaining = self.maze.total_dots
            if remaining > 100:
                siren = 0
            elif remaining > 50:
                siren = 1
            elif remaining > 20:
                siren = 2
            else:
                siren = 3
            # Actually apply the siren level (only change channel when level differs)
            if not hasattr(self, '_current_siren') or self._current_siren != siren:
                self._current_siren = siren
                if self.sound:
                    self.sound.play_siren(siren)

        # Ghost updates
        blinky = self.ghosts[0]
        for g in self.ghosts:
            g.update(self.maze, self.pacman, blinky, now,
                     self.maze.total_dots + self.dots_eaten,
                     self.dots_eaten, self.level)

        # Fright ended?
        if not any(g.mode == GhostMode.FRIGHTENED for g in self.ghosts):
            if any_fright and self.sound:
                if any(g.mode == GhostMode.EATEN for g in self.ghosts):
                    self.sound.play_eyes()
                else:
                    self.sound.stop_fright()
                    current = getattr(self, '_current_siren', 0)
                    self.sound.play_siren(current)

        self.fruit.update(now)

        # Fruit collision
        if self.fruit.active:
            fc, fr = FRUIT_POS
            pc, pr = self.pacman.get_cell()
            if pc == fc and pr == fr:
                self.score += self.fruit.points
                self.floating_scores.append(
                    FloatingScore(str(self.fruit.points),
                                  *tile_to_pixel(fc, fr), now))
                self.fruit.active = False
                self._update_high_score()
                if self.sound:
                    self.sound.play_eat_fruit()

        self._check_ghost_collisions(now)

        # Update and clean floating scores
        for fs in self.floating_scores:
            fs.update()
        self.floating_scores = [fs for fs in self.floating_scores if fs.alive(now)]

    def _check_ghost_collisions(self, now):
        for g in self.ghosts:
            if g.mode in (GhostMode.INDOOR, GhostMode.EATEN):
                continue
            dx = abs(self.pacman.px - g.px)
            dy = abs(self.pacman.py - g.py)
            if dx < TILE_SIZE * 0.7 and dy < TILE_SIZE * 0.7:
                if g.mode == GhostMode.FRIGHTENED:
                    g.get_eaten(now)
                    self.score += self.ghost_eat_combo
                    self.floating_scores.append(
                        FloatingScore(str(self.ghost_eat_combo), g.px, g.py, now))
                    self.ghost_eat_combo *= 2
                    self._update_high_score()
                    if self.sound:
                        self.sound.play_eat_ghost()
                else:
                    self.pacman.alive = False
                    self.lives -= 1
                    self.phase = GamePhase.DEATH
                    self.phase_start = now
                    if self.sound:
                        self.sound.stop_all()
                        self.sound.play_death()
                    return

    def _update_high_score(self):
        if self.score > self.ctx["high_score"]:
            self.ctx["high_score"] = self.score

    def _save_high_score(self):
        self._update_high_score()
        fn = self.ctx.get("save_high_score")
        if fn:
            fn(self.ctx["high_score"])

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface):
        ctx = self.ctx
        a, f = ctx["assets"], ctx["fonts"]
        fc = ctx["frame_count"]
        now = self._now()

        surface.fill(BLACK)
        renderer.draw_header(surface, f, self.score, ctx["high_score"], self.level)

        flash = (self.phase == GamePhase.LEVEL_COMPLETE and
                 ((now - self.phase_start) // 250) % 2 == 1)
        self.maze.draw_walls(surface, flash=flash)
        self.maze.draw_dots(surface, a, fc)

        if self.phase in (GamePhase.PLAYING, GamePhase.READY, GamePhase.INTRO):
            self.fruit.draw(surface, a)
            for g in self.ghosts:
                g.draw(surface, a, now)
            self.pacman.draw(surface, a)

        if self.phase == GamePhase.DEATH:
            elapsed = now - self.phase_start
            if elapsed < 500:
                # Brief pause showing everyone
                for g in self.ghosts:
                    g.draw(surface, a, now)
                self.pacman.draw(surface, a)

        for fs in self.floating_scores:
            fs.draw(surface, f["small"], now)

        renderer.draw_footer(surface, a, self.lives, self.level)

        if self.phase in (GamePhase.READY, GamePhase.INTRO):
            renderer.draw_ready_text(surface, f["large"])


# ---------------------------------------------------------------------------
# Game Over
# ---------------------------------------------------------------------------

class GameOverScene(Scene):
    def __init__(self, ctx, final_score):
        self.ctx = ctx
        self.final_score = final_score

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.ctx["scene_manager"].switch_to(MenuScene(self.ctx))

    def draw(self, surface):
        surface.fill(BLACK)
        renderer.draw_game_over_overlay(surface, self.ctx["fonts"],
                                        self.ctx["frame_count"])
        f = self.ctx["fonts"]
        y = 15 * TILE_SIZE + HEADER_HEIGHT
        st = f["medium"].render(f"SCORE: {self.final_score}", True, WHITE)
        surface.blit(st, (SCREEN_WIDTH // 2 - st.get_width() // 2, y + 80))
        ht = f["medium"].render(f"HIGH SCORE: {self.ctx['high_score']}", True, CYAN)
        surface.blit(ht, (SCREEN_WIDTH // 2 - ht.get_width() // 2, y + 110))
