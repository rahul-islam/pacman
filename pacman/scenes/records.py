"""Top-5 scores for the selected level."""

import pygame

from .. import art
from ..app import Scene
from ..audio import UI
from ..config import BRONZE, GOLD, HEIGHT, RED, SILVER, WHITE, WIDTH, key_action
from ..ui import Item, Menu, draw_text

RANK_COLORS = (GOLD, SILVER, BRONZE, WHITE, WHITE)


class RecordsScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.medals = art.shared_art()["medals"]
        self.menu = Menu([Item("BACK", app.pop)], center_x=WIDTH // 2, top=HEIGHT - 30, spacing=0, size=16,
                         click=lambda: app.audio.play(UI, "click"))

    def handle_event(self, event) -> None:
        if key_action(event) == "back":
            self.app.pop()
        else:
            self.menu.handle_event(event)

    def draw(self, screen) -> None:
        screen.fill((0, 0, 0))
        level = self.app.save.level
        draw_text(screen, "RECORDS", 24, WHITE, title=True, center=(WIDTH // 2, 28))
        draw_text(screen, f"LEVEL {level + 1}", 8, title=True, center=(WIDTH // 2, 54))
        scores = self.app.save.records[level] if level < self.app.save.unlocked else []
        if not scores:
            draw_text(screen, "NO RECORDS", 24, RED, center=(WIDTH // 2, 110))
        for i, score in enumerate(scores):
            y = 88 + i * 34
            screen.blit(pygame.transform.scale(self.medals[i], (28, 28)), (28, y - 14))
            draw_text(screen, score, 24, RANK_COLORS[i], topleft=(68, y - 12))
        self.menu.draw(screen)
