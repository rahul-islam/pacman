"""Skin shop: pick an owned skin or buy one with banked fruit."""

import pygame

from .. import art
from ..app import Scene
from ..audio import UI
from ..config import GOLD, WHITE, WIDTH, key_action
from ..ui import Item, Menu, blit_center, draw_text


class SkinsScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.fruits = art.shared_art()["fruits"]
        self.preview = app.save.skin
        items = [self._item(skin) for skin in art.SKINS]
        items.append(Item("BACK", app.pop, on_focus=lambda: self._show(app.save.skin)))
        focus = next(i for i, s in enumerate(art.SKINS) if s.key == app.save.skin)
        self.menu = Menu(items, center_x=58, top=90, spacing=20, size=16, focus=focus,
                         click=lambda: app.audio.play(UI, "click"))

    def _item(self, skin) -> Item:
        save = self.app.save

        def label():
            return f"-{skin.label}-" if save.skin == skin.key else skin.label

        def price(surface, rect):
            if skin.key in save.skins:
                return
            x = rect.right + 8
            for index, count in skin.cost:
                x = draw_text(surface, count, 8, WHITE, topleft=(x, rect.centery - 5)).right + 1
                blit_center(surface, self.fruits[index], (x + 6, rect.centery))
                x += 16

        return Item(label, lambda: self._choose(skin), on_focus=lambda: self._show(skin.key),
                    color=lambda: None if skin.key in save.skins else GOLD, extra=price)

    def _show(self, key: str) -> None:
        self.preview = key

    def _choose(self, skin) -> None:
        save = self.app.save
        if not save.buy(skin):
            return
        save.skin = skin.key
        self.app.persist()
        self.app.pop()

    def handle_event(self, event) -> None:
        if key_action(event) == "back":
            self.app.pop()
        else:
            self.menu.handle_event(event)

    def draw(self, screen) -> None:
        screen.fill((0, 0, 0))
        draw_text(screen, "SELECT SKIN", 16, WHITE, title=True, center=(WIDTH // 2, 26))
        for i, fruit in enumerate(self.fruits):
            x = 26 + i * 29
            blit_center(screen, fruit, (x, 50))
            draw_text(screen, self.app.save.fruit_bank[i], 8, WHITE, center=(x, 64))
        self.menu.draw(screen)
        frame = art.pacman_art(self.preview)["walk"]["right"][2]
        big = pygame.transform.scale(frame, (65, 65))
        screen.blit(big, big.get_rect(center=(178, 150)))
