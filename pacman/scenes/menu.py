"""Title screen."""

import random

import pygame

from .. import art
from ..app import Scene
from ..audio import UI
from ..config import MAZE_TINTS, MAZE_TOP, WIDTH, YELLOW, key_action
from ..level import level_files, load_level
from ..ui import CheatCodes, Item, Menu, draw_text, frosted


class MenuScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        from .levels import LevelsScene
        from .play import PlayScene
        from .records import RecordsScene
        from .settings import SettingsScene
        from .skins import SkinsScene

        self.tint = random.choice(MAZE_TINTS)
        self.menu = Menu(
            [
                Item("PLAY", lambda: app.replace(PlayScene(app, self.tint))),
                Item("LEVELS", lambda: app.push(LevelsScene(app))),
                Item("SKINS", lambda: app.push(SkinsScene(app))),
                Item("RECORDS", lambda: app.push(RecordsScene(app))),
                Item("SETTINGS", lambda: app.push(SettingsScene(app))),
                Item("EXIT", app.quit),
            ],
            center_x=64, top=100, spacing=26, size=16, click=lambda: app.audio.play(UI, "click"),
        )
        self.cheats = CheatCodes({"pycman": self.unlock_all})
        self.backdrop = None

    def enter(self) -> None:
        self._make_backdrop()

    def _make_backdrop(self) -> None:
        level = load_level(self.app.save.level)
        maze = art.maze_image(level.name, self.tint)
        full = pygame.Surface(self.app.screen.get_size())
        full.blit(maze, (0, MAZE_TOP))
        self.backdrop = frosted(full, dim=120)

    def unlock_all(self) -> None:
        self.app.audio.play(UI, "cheat")
        self.app.save.unlock_all(len(level_files()))

    def handle_event(self, event) -> None:
        self.cheats.handle_event(event)
        if key_action(event) == "back":
            self.tint = random.choice([t for t in MAZE_TINTS if t != self.tint])
            self._make_backdrop()
        else:
            self.menu.handle_event(event)

    def draw(self, screen) -> None:
        screen.blit(self.backdrop, (0, 0))
        draw_text(screen, "PACMAN", 32, YELLOW, title=True, center=(WIDTH // 2, 30))
        draw_text(screen, f"LEVEL {self.app.save.level + 1}", 8, title=True, center=(WIDTH // 2, 58))
        self.menu.draw(screen)
        frames = art.pacman_art(self.app.save.skin)["walk"]["right"]
        frame = frames[(pygame.time.get_ticks() // 125) % len(frames)]
        big = pygame.transform.scale(frame, (65, 65))
        screen.blit(big, big.get_rect(center=(168, 160)))
