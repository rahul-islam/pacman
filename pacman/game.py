"""Main game loop, pygame initialization, and scene orchestration."""

import os
import sys
import pygame

from .constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BLACK
from .assets import load_assets
from .sound import SoundManager
from .scenes import SceneManager, MenuScene


class Game:
    """Top-level game controller."""

    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PAC-MAN")
        self.clock = pygame.time.Clock()

        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets")
        assets = load_assets(base)
        sound = SoundManager(base)

        fonts = {
            "large": pygame.font.SysFont("arial", 28, bold=True),
            "medium": pygame.font.SysFont("arial", 20, bold=True),
            "small": pygame.font.SysFont("arial", 16, bold=True),
        }

        self.scene_manager = SceneManager()
        self.ctx = {
            "assets": assets,
            "fonts": fonts,
            "sound": sound,
            "high_score": self._load_high_score(),
            "frame_count": 0,
            "scene_manager": self.scene_manager,
            "save_high_score": self._save_high_score,
        }
        self.scene_manager.switch_to(MenuScene(self.ctx))

    # ------------------------------------------------------------------
    # High score persistence
    # ------------------------------------------------------------------
    @staticmethod
    def _hs_path():
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "highscore.txt")

    def _load_high_score(self):
        try:
            with open(self._hs_path()) as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def _save_high_score(self, score):
        try:
            with open(self._hs_path(), "w") as f:
                f.write(str(score))
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._quit()
                self.scene_manager.handle_event(event)

            self.scene_manager.update()
            self.screen.fill(BLACK)
            self.scene_manager.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
            self.ctx["frame_count"] += 1

    def _quit(self):
        self._save_high_score(self.ctx["high_score"])
        pygame.quit()
        sys.exit()
