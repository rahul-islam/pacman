"""Sprite loading and scaling."""

import os
import pygame
from .constants import TILE_SIZE


def load_assets(base_path: str) -> dict:
    """Load all game sprites.  Returns name → Surface dict."""
    gfx = os.path.join(base_path, "graphics")
    assets: dict = {}

    # Pac-Man: 4 directions × 3 animation frames
    for direction in ("right", "left", "up", "down"):
        frames = []
        for i in range(1, 4):
            path = os.path.join(gfx, f"pacman-{direction}", f"{i}.png")
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            frames.append(img)
        assets[f"pacman_{direction}"] = frames

    # Ghosts
    for name in ("blinky", "pinky", "inky", "clyde", "blue_ghost"):
        path = os.path.join(gfx, "ghosts", f"{name}.png")
        img = pygame.image.load(path).convert_alpha()
        assets[name] = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))

    # White (flashing) frightened ghost
    white_ghost = assets["blue_ghost"].copy()
    white_ghost.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
    assets["white_ghost"] = white_ghost

    # Collectibles
    for name in ("dot", "apple", "strawberry"):
        path = os.path.join(gfx, "other", f"{name}.png")
        img = pygame.image.load(path).convert_alpha()
        size = (6, 6) if name == "dot" else (TILE_SIZE, TILE_SIZE)
        assets[name] = pygame.transform.scale(img, size)

    return assets
