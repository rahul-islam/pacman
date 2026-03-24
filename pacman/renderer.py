"""HUD drawing helpers — header, footer, text overlays."""

import pygame
from .constants import (
    TILE_SIZE, HALF_TILE, ROWS, SCREEN_WIDTH, HEADER_HEIGHT,
    WHITE, YELLOW, RED, CYAN,
)


def draw_header(surface, fonts, score, high_score, level):
    fs, fm = fonts["small"], fonts["medium"]
    lbl = fs.render("SCORE", True, WHITE)
    surface.blit(lbl, (10, 5))
    val = fm.render(str(score), True, WHITE)
    surface.blit(val, (10, 22))

    lbl = fs.render("HIGH SCORE", True, WHITE)
    surface.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, 5))
    val = fm.render(str(high_score), True, WHITE)
    surface.blit(val, (SCREEN_WIDTH // 2 - val.get_width() // 2, 22))

    lbl = fs.render(f"LEVEL {level}", True, YELLOW)
    surface.blit(lbl, (SCREEN_WIDTH - lbl.get_width() - 10, 5))


_footer_cache: dict[str, pygame.Surface] = {}


def _get_footer_sprite(assets, key, size=(18, 18)):
    """Return a cached scaled sprite for footer display."""
    if key not in _footer_cache:
        src = assets[key] if not isinstance(assets[key], list) else assets[key][0]
        _footer_cache[key] = pygame.transform.scale(src, size)
    return _footer_cache[key]


def draw_footer(surface, assets, lives, level):
    y = HEADER_HEIGHT + ROWS * TILE_SIZE + 10
    pac = _get_footer_sprite(assets, "pacman_right")
    for i in range(lives):
        surface.blit(pac, (10 + i * 24, y))
    if level >= 1:
        img = _get_footer_sprite(assets, "apple")
        surface.blit(img, (SCREEN_WIDTH - 30, y))
    if level >= 2:
        img = _get_footer_sprite(assets, "strawberry")
        surface.blit(img, (SCREEN_WIDTH - 56, y))


def draw_ready_text(surface, font):
    txt = font.render("READY!", True, YELLOW)
    surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                        15 * TILE_SIZE + HEADER_HEIGHT))


def draw_game_over_overlay(surface, fonts, frame_count):
    txt = fonts["large"].render("GAME  OVER", True, RED)
    y = 15 * TILE_SIZE + HEADER_HEIGHT
    surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y))
    if (frame_count // 30) % 2 == 0:
        p = fonts["medium"].render("Press ENTER to continue", True, WHITE)
        surface.blit(p, (SCREEN_WIDTH // 2 - p.get_width() // 2, y + 40))
