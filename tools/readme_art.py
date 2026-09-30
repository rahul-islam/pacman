"""Render the README images into docs/.

    python tools/readme_art.py

- docs/banner.png: 1280x640 banner (also usable as the GitHub social preview).
  The layout mirrors the "README Banner" page in the Claude Design project
  "Pac-Man Neon Asset Kit"; keep the two in step when changing either.
- docs/screens/*.png: screenshots of the real game, rendered headless.
"""

import os
import random
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

pygame.init()
pygame.mixer.init()

from pacman import art  # noqa: E402
from pacman.app import App  # noqa: E402
from pacman.config import CYAN, FONT_TITLE, FONT_UI, INK, PELLET, TILE  # noqa: E402
from pacman.level import load_level  # noqa: E402

DOCS = ROOT / "docs"
W, H = 1280, 640


def font(path, size):
    return pygame.font.Font(str(path), size)


def text_at_baseline(surface, face, label, color, x, baseline):
    img = face.render(label, True, color)
    surface.blit(img, (x, baseline - face.get_ascent()))
    return img


def glow_text(surface, face, label, color, glow, x, baseline, radius):
    """Text with a blurred halo, like canvas shadowBlur."""
    img = face.render(label, True, glow)
    pad = radius * 2
    halo = pygame.Surface((img.get_width() + 2 * pad, img.get_height() + 2 * pad), pygame.SRCALPHA)
    halo.blit(img, (pad, pad))
    w, h = halo.get_size()
    small = pygame.transform.smoothscale(halo, (max(1, w // radius), max(1, h // radius)))
    halo = pygame.transform.smoothscale(small, (w, h))
    top = baseline - face.get_ascent()
    for _ in range(2):
        surface.blit(halo, (x - pad, top - pad))
    surface.blit(face.render(label, True, color), (x, top))


def maze_scene(level) -> pygame.Surface:
    """Level 1 with pellets and a few actors on a transparent background."""
    layer = art.image(f"maze/{level.name}.png").copy()
    layer.fill((*CYAN, 255), special_flags=pygame.BLEND_RGBA_MULT)
    for r, row in enumerate(level.rows):
        for c, ch in enumerate(row):
            if ch == "-":
                layer.fill(PELLET, (c * TILE, r * TILE + 3, TILE, 2))
            elif ch == ".":
                layer.fill(PELLET, (c * TILE + 3, r * TILE + 3, 2, 2))
            elif ch == "o":
                pygame.draw.circle(layer, PELLET, (c * TILE + 4, r * TILE + 4), 3)

    def put(img, col, row):
        layer.blit(img, img.get_rect(center=(round(col * TILE + 4), round(row * TILE + 4))))

    ghost = {name: art.ghost_art(name)["walk"] for name in art.GHOST_NAMES}
    put(ghost["blinky"]["left"][0], 13.5, 11)
    put(ghost["pinky"]["up"][1], 13.5, 14)
    put(ghost["inky"]["up"][0], 11.5, 14)
    put(ghost["clyde"]["up"][1], 15.5, 14)
    put(art.pacman_art("classic")["walk"]["up"][2], 21, 17)
    put(art.shared_art()["fruits"][0], 13.5, 17)
    return layer


def gradient(size, start_alpha, end_alpha, horizontal):
    w, h = size
    surface = pygame.Surface(size, pygame.SRCALPHA)
    steps = w if horizontal else h
    for i in range(steps):
        a = round(start_alpha + (end_alpha - start_alpha) * i / max(1, steps - 1))
        rect = (i, 0, 1, h) if horizontal else (0, i, w, 1)
        surface.fill((*INK, a), rect)
    return surface


def banner() -> pygame.Surface:
    out = pygame.Surface((W, H), 0, 24)
    out.fill(INK)
    grid = pygame.Surface((W, H), pygame.SRCALPHA)
    for x in range(0, W + 1, 16):
        grid.fill((*CYAN, 13), (x, 0, 1, H))
    for y in range(0, H + 1, 16):
        grid.fill((*CYAN, 13), (0, y, W, 1))
    out.blit(grid, (0, 0))

    maze = maze_scene(load_level(0))
    mx, my, scale = 700, -60, 3
    out.blit(pygame.transform.scale(maze, (maze.get_width() * scale, maze.get_height() * scale)), (mx, my))
    out.blit(gradient((220, H), 255, 0, horizontal=True), (mx, 0))
    out.blit(gradient((W - mx, 120), 0, 230, horizontal=False), (mx, H - 120))

    left = 88
    text_at_baseline(out, font(FONT_UI, 26), "NEON EDITION", (255, 79, 216), left, 190)
    title = font(FONT_TITLE, 84)
    glow_text(out, title, "PAC-MAN", (255, 246, 184), (255, 79, 216), left, 300, radius=18)
    glow_text(out, title, "PAC-MAN", (255, 246, 184), (255, 225, 77), left, 300, radius=6)
    ui = font(FONT_UI, 24)
    text_at_baseline(out, ui, "11 MAZES · 7 SKINS · CHIPTUNE SOUND", (232, 232, 244), left, 360)
    text_at_baseline(out, ui, "PYTHON + PYGAME", (154, 154, 184), left, 396)

    # Chase strip: Pac-Man heading for a power pellet, scared ghosts beyond
    y = 500
    pac = art.pacman_art("classic")
    aura = pygame.transform.smoothscale(pac["aura"], (200, 200))
    out.blit(aura, (left - 68, y - 100))

    def big(img, x, s):
        scaled = pygame.transform.scale(img, (img.get_width() * s, img.get_height() * s))
        out.blit(scaled, (x, y - scaled.get_height() // 2))

    big(pac["walk"]["right"][2], left, 5)
    for i in range(4):
        out.fill(PELLET, (left + 92 + i * 32, y - 4, 8, 8))
    halo = pygame.Surface((60, 60), pygame.SRCALPHA)
    for r, a in ((28, 30), (22, 60), (18, 110)):
        pygame.draw.circle(halo, (*PELLET, a), (30, 30), r)
    out.blit(halo, (left + 250 - 30, y - 30))
    pygame.draw.circle(out, PELLET, (left + 250, y), 14)
    scared = art.shared_art()["scared"]
    for i, frame in enumerate((0, 1, 0, 1)):
        big(scared[frame], left + 300 + i * 70, 4)
    return out


def screenshots() -> dict[str, pygame.Surface]:
    from pacman.scenes.menu import MenuScene
    from pacman.scenes.play import PlayScene
    from pacman.scenes.skins import SkinsScene

    with tempfile.TemporaryDirectory() as tmp:
        app = App(save_path=Path(tmp) / "save.json", scaled=False)
        app.save.fruit_bank = [14, 9, 12, 6, 7, 5, 3]
        app.save.skins = ["classic", "neon", "robot"]
        shots = {}

        app.push(MenuScene(app))
        app.top.tint = CYAN
        app.top.enter()
        app.top.draw(app.screen)
        shots["title"] = app.screen.copy()

        play = PlayScene(app, CYAN)
        app.replace(play)
        play.phase = "play"
        play._spawn_timers()
        play._collide = lambda now: None  # keep the demo run alive
        rng = random.Random(5)
        for i in range(900):
            if i % 25 == 0:
                play.pac.steer(rng.choice(["left", "right", "up", "down"]))
            app.step([])
        app.top.draw(app.screen)
        shots["gameplay"] = app.screen.copy()

        app.push(SkinsScene(app))
        app.top.menu.move(1)
        app.top.draw(app.screen)
        shots["skins"] = app.screen.copy()
    return shots


def main() -> None:
    (DOCS / "screens").mkdir(parents=True, exist_ok=True)
    pygame.display.set_mode((W, H))  # sprites need a display to convert against
    pygame.image.save(banner(), str(DOCS / "banner.png"))
    for name, shot in screenshots().items():
        doubled = pygame.transform.scale(shot, (shot.get_width() * 2, shot.get_height() * 2))
        pygame.image.save(doubled, str(DOCS / "screens" / f"{name}.png"))
    print(f"wrote README images to {DOCS}")


if __name__ == "__main__":
    main()
