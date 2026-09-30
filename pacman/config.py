"""Game-wide constants: screen geometry, palette, fonts, input and difficulty."""

from dataclasses import dataclass
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SAVE_FILE = ROOT / "storage.json"

# Geometry: a 28x31 tile maze with a HUD strip above and below.
TILE = 8
COLS, ROWS = 28, 31
MAZE_TOP = 3 * TILE
WIDTH = COLS * TILE
HEIGHT = MAZE_TOP + ROWS * TILE + 2 * TILE
FPS = 60

# Neon palette (matches design/pixelkit.js)
INK = (11, 11, 18)
WHITE = (244, 244, 255)
MUTED = (154, 154, 184)
DIM = (70, 70, 96)
CYAN = (61, 232, 255)
PINK = (255, 79, 216)
VIOLET = (122, 92, 255)
LIME = (124, 255, 107)
AMBER = (255, 165, 61)
RED = (255, 59, 92)
GOLD = (255, 201, 61)
YELLOW = (255, 225, 77)
PELLET = (255, 194, 238)
SILVER = (207, 214, 230)
BRONZE = (224, 138, 79)
MAZE_TINTS = (CYAN, PINK, VIOLET, LIME, AMBER)

FONT_TITLE = ASSETS / "fonts" / "PressStart2P-Regular.ttf"
FONT_UI = ASSETS / "fonts" / "Silkscreen-Regular.ttf"

KEYS = {
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "select": (pygame.K_RETURN, pygame.K_SPACE),
    "back": (pygame.K_ESCAPE,),
}


def key_action(event) -> str | None:
    """Map a KEYDOWN event to 'up'/'down'/'left'/'right'/'select'/'back'."""
    if event.type != pygame.KEYDOWN:
        return None
    for action, keys in KEYS.items():
        if event.key in keys:
            return action
    return None


@dataclass(frozen=True)
class Difficulty:
    name: str
    lives: int
    score_mult: int  # applied to everything except plain pellets
    fright_ms: int
    chase_ms: int
    tier: int  # index into per-ghost scatter tables


DIFFICULTIES = (
    Difficulty("CHILD", lives=3, score_mult=1, fright_ms=8000, chase_ms=20000, tier=0),
    Difficulty("NORMAL", lives=2, score_mult=2, fright_ms=4000, chase_ms=40000, tier=1),
    Difficulty("HARDCORE", lives=1, score_mult=3, fright_ms=2000, chase_ms=80000, tier=2),
)
MAX_LIVES = 4

FRUIT_NAMES = ("cherry", "strawberry", "orange", "apple", "melon", "bell", "key")
