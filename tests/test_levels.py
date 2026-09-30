import pytest

import generate_levels
from pacman.level import level_files, load_level

LEVELS = range(len(level_files()))


def test_level_count():
    assert len(level_files()) == len(generate_levels.LEVELS) + 1  # classic + generated


def test_first_level_is_the_classic_maze():
    level = load_level(0)
    assert len(level.pellets) == 240 and len(level.power) == 4


@pytest.mark.parametrize("index", LEVELS)
def test_level_is_valid(index):
    maze = level_files()[index].read_text().split()
    assert generate_levels.validate(maze) == []


@pytest.mark.parametrize("index", range(len(generate_levels.LEVELS)))
def test_generator_reproduces_committed_level(index):
    seed, cols, rows = generate_levels.LEVELS[index]
    expected = generate_levels.rasterize(generate_levels.carve(seed, cols, rows), rows)
    committed = level_files()[index + generate_levels.FIRST_GENERATED - 1]
    assert committed.read_text().split() == expected


def test_level_geometry():
    level = load_level(0)
    assert level.pellet_total == len(level.pellets) + 4
    assert level.open(-1, 14) and level.open(28, 14)  # tunnel beyond the edges
    assert not level.open(-1, 1)
    assert level.slow(2, 14) and not level.slow(10, 14)
    assert level.exit_cell == (14, 11)
