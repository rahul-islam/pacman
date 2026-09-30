import filecmp
import os
import shutil
import subprocess

import pytest

from pacman import art
from pacman.config import ASSETS

ROOT = os.path.dirname(ASSETS)
IMAGES = ASSETS / "images"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_images_match_design_source(tmp_path):
    """assets/images must be exactly what design/pixelkit.js generates."""
    subprocess.run(["node", os.path.join(ROOT, "tools", "build_assets.mjs"), str(tmp_path)], check=True)
    generated = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*.png"))
    committed = sorted(p.relative_to(IMAGES) for p in IMAGES.rglob("*.png"))
    assert generated == committed
    for rel in generated:
        assert filecmp.cmp(tmp_path / rel, IMAGES / rel, shallow=False), rel


def test_every_skin_and_ghost_has_art(app):
    for skin in art.SKINS:
        sprites = art.pacman_art(skin.key)
        assert {d: len(f) for d, f in sprites["walk"].items()} == dict.fromkeys(art.DIRECTIONS, 4)
        assert len(sprites["dead"]) == 12
    for name in art.GHOST_NAMES:
        assert all(len(f) == 2 for f in art.ghost_art(name)["walk"].values())
    shared = art.shared_art()
    assert len(shared["fruits"]) == 7 and len(shared["medals"]) == 5
