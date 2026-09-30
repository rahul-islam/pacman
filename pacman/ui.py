"""Text rendering, menus, backdrops and cheat-code input."""

from functools import lru_cache
from typing import Callable

import pygame

from .config import CYAN, FONT_TITLE, FONT_UI, INK, MUTED, PINK, WHITE, key_action


@lru_cache(maxsize=None)
def font(title: bool, size: int) -> pygame.font.Font:
    return pygame.font.Font(str(FONT_TITLE if title else FONT_UI), size)


@lru_cache(maxsize=1024)
def text(label: str, size: int, color=WHITE, title: bool = False) -> pygame.Surface:
    """Render text; large title text gets a soft neon halo."""
    face = font(title, size)
    img = face.render(label, False, color)
    if not (title and size >= 16 and label):
        return img
    pad = 4
    w, h = img.get_width() + 2 * pad, img.get_height() + 2 * pad
    halo = pygame.Surface((w, h), pygame.SRCALPHA)
    halo.blit(face.render(label, False, PINK), (pad, pad))
    halo = pygame.transform.smoothscale(pygame.transform.smoothscale(halo, (w // 3, h // 3)), (w, h))
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(halo, (0, 0))
    out.blit(halo, (0, 0))
    out.blit(img, (pad, pad))
    return out


def draw_text(surface, label, size, color=WHITE, *, title=False, center=None, topleft=None, midright=None):
    img = text(str(label), size, color, title)
    rect = img.get_rect()
    if center:
        rect.center = center
    elif midright:
        rect.midright = midright
    else:
        rect.topleft = topleft or (0, 0)
    surface.blit(img, rect)
    return rect


def blit_center(surface, img, center) -> None:
    surface.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def frosted(surface: pygame.Surface, dim: int = 170) -> pygame.Surface:
    """Blurred, darkened copy of a scene, used behind overlays."""
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface.convert(), (w // 4, h // 4))
    out = pygame.transform.smoothscale(small, (w, h))
    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    veil.fill((*INK, dim))
    out.blit(veil, (0, 0))
    return out


class Item:
    def __init__(self, label: str | Callable[[], str], action: Callable | None = None, *, color=None,
                 on_left: Callable | None = None, on_right: Callable | None = None,
                 on_focus: Callable | None = None, extra: Callable | None = None) -> None:
        self._label = label
        self.action = action
        self.color = color  # colour when not focused (callable or tuple)
        self.on_left = on_left
        self.on_right = on_right
        self.on_focus = on_focus
        self.extra = extra  # draw hook: extra(surface, rect)

    @property
    def label(self) -> str:
        return self._label() if callable(self._label) else self._label

    def idle_color(self):
        color = self.color() if callable(self.color) else self.color
        return color or MUTED


class Menu:
    """Vertical list of items driven by keyboard or mouse."""

    def __init__(self, items: list[Item], *, center_x: int, top: int, spacing: int, size: int = 16,
                 focus: int = 0, click: Callable | None = None) -> None:
        self.items = items
        self.center_x, self.top, self.spacing, self.size = center_x, top, spacing, size
        self.focus = focus
        self.click = click
        self.rects: list[pygame.Rect] = []
        self._notify_focus()

    def _notify_focus(self) -> None:
        item = self.items[self.focus]
        if item.on_focus:
            item.on_focus()

    def move(self, step: int) -> None:
        self.focus = (self.focus + step) % len(self.items)
        self._notify_focus()

    def activate(self) -> None:
        item = self.items[self.focus]
        if item.action:
            if self.click:
                self.click()
            item.action()

    def handle_event(self, event) -> None:
        action = key_action(event)
        item = self.items[self.focus]
        if action == "up":
            self.move(-1)
        elif action == "down":
            self.move(1)
        elif action == "select":
            self.activate()
        elif action == "left" and item.on_left:
            item.on_left()
        elif action == "right" and item.on_right:
            item.on_right()
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            for i, rect in enumerate(self.rects):
                if rect.inflate(16, 4).collidepoint(event.pos):
                    if i != self.focus:
                        self.focus = i
                        self._notify_focus()
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self.activate()
                    break

    def draw(self, surface) -> None:
        self.rects = []
        for i, item in enumerate(self.items):
            focused = i == self.focus
            y = self.top + i * self.spacing
            rect = draw_text(surface, item.label, self.size, CYAN if focused else item.idle_color(),
                             center=(self.center_x, y))
            self.rects.append(rect)
            if focused:
                for side, x in ((1, rect.left - 6), (-1, rect.right + 6)):
                    tip = x + 3 * side
                    pygame.draw.polygon(surface, PINK, [(x, rect.centery - 3), (tip, rect.centery), (x, rect.centery + 3)])
            if item.extra:
                item.extra(surface, rect)


class CheatCodes:
    """Detects typed words; letters more than a second apart start over."""

    def __init__(self, codes: dict[str, Callable]) -> None:
        self.codes = codes
        self.typed = ""
        self.last = 0

    def handle_event(self, event) -> None:
        if event.type != pygame.KEYDOWN or not event.unicode.isalpha():
            return
        now = pygame.time.get_ticks()
        if now - self.last > 1000:
            self.typed = ""
        self.last = now
        self.typed += event.unicode.lower()
        for code, action in self.codes.items():
            if self.typed.endswith(code):
                self.typed = ""
                action()
                return
