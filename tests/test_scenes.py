import pygame
import pytest

from pacman.scenes.levels import LevelsScene
from pacman.scenes.menu import MenuScene
from pacman.scenes.records import RecordsScene
from pacman.scenes.settings import SettingsScene
from pacman.scenes.skins import SkinsScene

DOWN = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, unicode="")


@pytest.mark.parametrize("scene_type", [MenuScene, LevelsScene, SkinsScene, RecordsScene, SettingsScene])
def test_every_menu_item_draws(app, scene_type):
    """Focus each item in turn and draw — catches bad colours/labels per state."""
    app.save.skins = ["classic", "neon", "gold"]  # owned, locked and current skins
    app.save.skin = "neon"
    app.save.records[0] = [900, 500]
    app.push(MenuScene(app))
    if scene_type is not MenuScene:
        app.push(scene_type(app))
    scene = app.top
    for _ in range(len(getattr(getattr(scene, "menu", None), "items", [None])) + 1):
        scene.draw(app.screen)
        scene.handle_event(DOWN)
