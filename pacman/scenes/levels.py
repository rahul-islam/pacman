"""Level picker: browse unlocked levels with left/right."""

import pygame

from .. import art
from ..app import Scene
from ..audio import UI
from ..config import CYAN, DIM, HEIGHT, WHITE, WIDTH, key_action
from ..level import level_files, load_level
from ..ui import draw_text


class LevelsScene(Scene):
    PREVIEW = (134, 148)

    def __init__(self, app) -> None:
        super().__init__(app)
        self.total = len(level_files())
        self._render()

    def _render(self) -> None:
        maze = art.maze_image(load_level(self.app.save.level).name, CYAN)
        self.preview = pygame.transform.smoothscale(maze, self.PREVIEW)

    def _shift(self, step: int) -> None:
        target = self.app.save.level + step
        if 0 <= target < self.app.save.unlocked:
            self.app.save.level = target
            self.app.audio.play(UI, "click")
            self._render()

    def _close(self) -> None:
        self.app.persist()
        self.app.pop()

    def handle_event(self, event) -> None:
        action = key_action(event)
        if action == "left":
            self._shift(-1)
        elif action == "right":
            self._shift(1)
        elif action in ("select", "back"):
            self._close()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            x = event.pos[0]
            if x < WIDTH // 4:
                self._shift(-1)
            elif x > WIDTH * 3 // 4:
                self._shift(1)
            else:
                self._close()

    def draw(self, screen) -> None:
        screen.fill((0, 0, 0))
        draw_text(screen, "SELECT LEVEL", 16, WHITE, title=True, center=(WIDTH // 2, 30))
        rect = self.preview.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(self.preview, rect)
        draw_text(screen, f"LEVEL {self.app.save.level + 1}/{self.total}", 16, WHITE, center=rect.center)
        cy = rect.centery
        if self.app.save.level > 0:
            pygame.draw.polygon(screen, DIM, [(24, cy), (36, cy - 10), (36, cy + 10)])
        if self.app.save.level + 1 < self.app.save.unlocked:
            pygame.draw.polygon(screen, DIM, [(WIDTH - 24, cy), (WIDTH - 36, cy - 10), (WIDTH - 36, cy + 10)])
        draw_text(screen, "ENTER TO CHOOSE", 8, DIM, center=(WIDTH // 2, HEIGHT - 20))
