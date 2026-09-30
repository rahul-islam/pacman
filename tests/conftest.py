import os
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]

import pygame  # noqa: E402

pygame.init()
pygame.mixer.init()


@pytest.fixture
def fake_ticks(monkeypatch):
    """Drive every pygame timer from a counter the test controls."""
    now = [1000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
    return now


@pytest.fixture
def app(tmp_path, fake_ticks):
    from pacman.app import App

    return App(save_path=tmp_path / "save.json", scaled=False)
