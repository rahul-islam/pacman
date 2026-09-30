"""A round of Pac-Man on the selected level."""

import random

import pygame

from .. import art
from ..actors import DIRS, FRIGHT, GHOST_TYPES, PacMan
from ..app import Scene
from ..audio import MUSIC, SFX, UI
from ..config import (CYAN, DIFFICULTIES, INK, MAX_LIVES, MAZE_TINTS, MAZE_TOP, MUTED, PELLET, ROWS, TILE,
                      WHITE, WIDTH, YELLOW, key_action)
from ..level import cell_center, level_files, load_level
from ..ui import CheatCodes, blit_center, draw_text

FRUIT_DELAY_MS = 9000
POPUP_MS = 500
HOUSE_TIMEOUT_MS = 10000


class PlayScene(Scene):
    def __init__(self, app, tint=None) -> None:
        super().__init__(app)
        self.level_index = app.save.level
        self.level = load_level(self.level_index)
        self.tint = tint or random.choice(MAZE_TINTS)
        self.maze = art.maze_image(self.level.name, self.tint)
        self.difficulty = DIFFICULTIES[app.save.settings.difficulty]
        self.fruits = art.shared_art()["fruits"]
        self.life_icon = art.pacman_art(app.save.skin)["walk"]["right"][1]

        self.pellets = set(self.level.pellets)
        self.power = set(self.level.power)
        self.score = 0
        self.lives = self.difficulty.lives
        self.combo = 0
        self.fruit_index = 0
        self.fruit_state = "wait"
        self.fruit_at = 0
        self.fruit_popup = 0
        self.fruits_eaten: list[int] = []

        self.phase = "intro"
        self.started = False
        self.intro_at = 0
        self.cheats = CheatCodes({"god": self.win, "kill": self.lose, "aezakmi": self.extra_life})
        self._spawn()

    @property
    def now(self) -> int:
        return self.app.game_clock.now()

    def _spawn(self) -> None:
        """(Re)place Pac-Man and the ghosts; pellets and score carry over."""
        self.pac = PacMan(self.level, self.app.save.skin)
        self.pac.on_tile = self._eat
        self.ghosts = [kind(self.level, self.difficulty) for kind in GHOST_TYPES]
        now = self.now
        for ghost in self.ghosts:
            ghost.mode_at = now
        self.life_at = now
        self.eaten_this_life = 0

    # -- scene hooks ---------------------------------------------------------
    def enter(self) -> None:
        if not self.started:
            self.started = True
            self.app.audio.shuffle_fun()
            self.app.audio.stop_all()
            self.app.audio.play(MUSIC, "intro")
            self.intro_at = pygame.time.get_ticks()
        else:
            self.app.game_clock.resume()
            self.app.audio.resume_all()

    def leave(self, covered: bool) -> None:
        if covered:
            self.app.game_clock.pause()
            self.app.audio.pause_all()
        else:
            self.app.audio.stop_all()
            self.app.game_clock.resume()

    def handle_event(self, event) -> None:
        self.cheats.handle_event(event)
        action = key_action(event)
        if action in DIRS:
            self.pac.steer(action)
        elif action == "back":
            from .overlays import PauseScene

            self.app.push(PauseScene(self.app, self))

    # -- game logic ------------------------------------------------------------
    def update(self, dt: int) -> None:
        if self.phase == "intro":
            if not self.app.audio.busy(MUSIC) and pygame.time.get_ticks() - self.intro_at > 100:
                self.phase = "play"
                self._spawn_timers()
            return
        self._tick(dt)

    def _spawn_timers(self) -> None:
        now = self.now
        self.life_at = self.fruit_at = now
        for ghost in self.ghosts:
            ghost.mode_at = now

    def _tick(self, dt: int) -> None:
        now = self.now
        if self.pac.dead:
            if self.pac.death_done(now):
                if self.lives > 0:
                    self._spawn()
                else:
                    self.lose()
            return

        self.pac.update(dt)
        blinky = self.ghosts[0]
        total = self.level.pellet_total
        for ghost in self.ghosts:
            if self.eaten_this_life > ghost.leave_share * total or now - self.life_at >= HOUSE_TIMEOUT_MS:
                ghost.release()
            ghost.update(now, self.pac, blinky)
        self._collide(now)
        self._update_fruit(now)

        if not self.pac.dead:
            frightened = any(g.state == FRIGHT for g in self.ghosts)
            self.app.audio.keep(MUSIC, "frightened" if frightened else "back")
        if not self.pellets and not self.power:
            self.win()

    def _eat(self, col: int, row: int) -> None:
        cell = (col % len(self.level.rows[0]), row)
        if cell in self.pellets:
            self.pellets.remove(cell)
            self.score += 10
            self.eaten_this_life += 1
            self.app.audio.play_if_idle(SFX, "seed")
        elif cell in self.power:
            self.power.remove(cell)
            self.score += 50 * self.difficulty.score_mult
            self.combo = 0
            now = self.now
            for ghost in self.ghosts:
                ghost.frighten(now)

    def _collide(self, now: int) -> None:
        for ghost in self.ghosts:
            if self.pac.distance_to(ghost) >= 4:
                continue
            if ghost.edible:
                points = 200 * 2**self.combo * self.difficulty.score_mult
                self.combo += 1
                self.score += points
                ghost.eat(now, points)
                self.app.audio.play(SFX, "eat_ghost")
            elif ghost.dangerous:
                self.lives -= 1
                self.pac.die(now)
                self.app.audio.stop(MUSIC)
                self.app.audio.play(SFX, "death")
                return

    def _update_fruit(self, now: int) -> None:
        if self.fruit_state == "wait" and now - self.fruit_at >= FRUIT_DELAY_MS:
            self.fruit_state = "active"
        elif self.fruit_state == "active":
            fx, fy = self.level.spawns["fruit"]
            if abs(self.pac.x - fx) < 4 and abs(self.pac.y - fy) < 4:
                self.fruit_popup = 300 * (self.fruit_index + 1) * self.difficulty.score_mult
                self.score += self.fruit_popup
                self.app.save.fruit_bank[self.fruit_index] += 1
                self.fruits_eaten.append(self.fruit_index)
                self.fruit_state, self.fruit_at = "popup", now
                self.app.audio.play(SFX, "eat_fruit")
        elif self.fruit_state == "popup" and now - self.fruit_at >= POPUP_MS:
            self.fruit_index += 1
            self.fruit_state = "wait" if self.fruit_index < len(self.fruits) else "gone"
            self.fruit_at = now

    # -- outcomes ----------------------------------------------------------------
    def win(self) -> None:
        from .overlays import ResultScene

        save = self.app.save
        save.add_record(self.level_index, self.score)
        save.unlock_after(self.level_index, len(level_files()))
        self.app.persist()
        self.app.replace(ResultScene(self.app, self.snapshot(), won=True, score=self.score))

    def lose(self) -> None:
        from .overlays import ResultScene

        self.app.persist()
        self.app.replace(ResultScene(self.app, self.snapshot(), won=False, score=self.score))

    def extra_life(self) -> None:
        self.app.audio.play(UI, "cheat")
        self.lives = min(self.lives + 1, MAX_LIVES)

    # -- drawing -----------------------------------------------------------------
    def draw(self, screen) -> None:
        screen.fill(INK)
        screen.blit(self.maze, (0, MAZE_TOP))
        for col, row in self.level.doors:
            screen.fill(PELLET, (col * TILE, MAZE_TOP + row * TILE + 3, TILE, 2))
        for cell in self.pellets:
            x, y = cell_center(*cell)
            screen.fill(PELLET, (x - 1, y - 1, 2, 2))
        now = self.now
        if (now // 125) % 2 == 0:
            for cell in self.power:
                pygame.draw.circle(screen, PELLET, cell_center(*cell), 3)

        fruit_pos = self.level.spawns["fruit"]
        if self.fruit_state == "active":
            blit_center(screen, self.fruits[self.fruit_index], fruit_pos)
        elif self.fruit_state == "popup":
            draw_text(screen, self.fruit_popup, 8, CYAN, center=fruit_pos)

        for ghost in self.ghosts:
            img = ghost.sprite(now)
            if img is None:
                draw_text(screen, ghost.popup_score, 8, CYAN, center=(ghost.x, ghost.y))
            else:
                self._draw_actor(screen, img, ghost, ghost.art["aura"] if ghost.state != FRIGHT else None)
        if not (self.pac.dead and self.pac.death_done(now)):
            self._draw_actor(screen, self.pac.sprite(now), self.pac, self.pac.art["aura"])

        self._draw_hud(screen)
        if self.phase == "intro":
            elapsed = pygame.time.get_ticks() - self.intro_at
            label = "READY" if elapsed < self.app.audio.length("intro") * 750 else "GO!"
            if (elapsed // 125) % 2 == 0:
                draw_text(screen, label, 24, YELLOW, title=True, center=(WIDTH // 2, MAZE_TOP + 17 * TILE + 4))

    def _draw_actor(self, screen, img, actor, aura) -> None:
        # Draw a copy on the far side while crossing the tunnel.
        for shift in (-WIDTH, 0, WIDTH):
            pos = (actor.x + shift, actor.y)
            if aura is not None:
                blit_center(screen, aura, pos)
            blit_center(screen, img, pos)

    def _draw_hud(self, screen) -> None:
        screen.fill(INK, (0, 0, WIDTH, MAZE_TOP))
        draw_text(screen, "SCORE", 8, MUTED, topleft=(8, 2))
        draw_text(screen, self.score, 8, WHITE, topleft=(8, 12))
        draw_text(screen, "BEST", 8, MUTED, midright=(WIDTH - 8, 6))
        draw_text(screen, max(self.score, self.app.save.best(self.level_index)), 8, WHITE, midright=(WIDTH - 8, 16))
        draw_text(screen, f"LEVEL {self.level_index + 1}", 8, CYAN, center=(WIDTH // 2, 11))

        bottom = MAZE_TOP + ROWS * TILE + TILE
        for i in range(self.lives - (0 if self.pac.dead else 1)):
            blit_center(screen, self.life_icon, (10 + i * 15, bottom))
        for i, index in enumerate(self.fruits_eaten):
            blit_center(screen, self.fruits[index], (WIDTH - 10 - i * 14, bottom))
