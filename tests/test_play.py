import random

import pygame
import pytest

from pacman.actors import CHASE, EYES, FRIGHT, HOME, SCATTER, Clyde, Inky, PacMan, Pinky
from pacman.config import DIFFICULTIES
from pacman.level import cell_center, level_files
from pacman.scenes.menu import MenuScene
from pacman.scenes.overlays import PauseScene, ResultScene
from pacman.scenes.play import PlayScene


def start(app, fake_ticks, level=0):
    app.save.level = level
    app.push(MenuScene(app))
    scene = PlayScene(app)
    app.replace(scene)
    scene.phase = "play"
    scene._spawn_timers()
    return scene


def frames(app, fake_ticks, n, before=None):
    for i in range(n):
        fake_ticks[0] += 16
        if before:
            before(i)
        app.step([])


def key(name):
    return pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f"K_{name}"), unicode=name if len(name) == 1 else "")


@pytest.mark.parametrize("level", range(len(level_files())))
def test_everyone_stays_on_the_paths(app, fake_ticks, level):
    scene = start(app, fake_ticks, level)
    rng = random.Random(level)
    scene._collide = lambda now: None  # invincible: this test is about movement
    left_house = set()

    def check(i):
        if i % 20 == 0:
            scene.pac.steer(rng.choice(["left", "right", "up", "down"]))
        if app.top is not scene:
            return
        for actor in [scene.pac, *scene.ghosts]:
            roaming = actor is scene.pac or actor.state in (CHASE, SCATTER, FRIGHT, EYES)
            if roaming and actor.centered():
                assert scene.level.open(*actor.cell), (type(actor).__name__, actor.cell)
        left_house.update(g.name for g in scene.ghosts if g.state != HOME)

    frames(app, fake_ticks, 3000, check)
    assert left_house == {"blinky", "pinky", "inky", "clyde"}


def test_ghost_targets(app, fake_ticks):
    scene = start(app, fake_ticks)
    pac, blinky = scene.pac, scene.ghosts[0]
    pac.x, pac.y = cell_center(10, 20)
    pac.dir = "up"
    blinky.x, blinky.y = cell_center(6, 23)
    assert Pinky.chase_target(scene.ghosts[1], pac, blinky) == (10, 18)
    assert Inky.chase_target(scene.ghosts[2], pac, blinky) == (14, 13)  # 2 ahead, doubled away from Blinky

    clyde = next(g for g in scene.ghosts if isinstance(g, Clyde))
    clyde.state = CHASE
    clyde.x, clyde.y = cell_center(12, 20)
    clyde._step_mode(0, pac)
    assert clyde.state == SCATTER
    clyde.x, clyde.y = cell_center(26, 1)
    clyde._step_mode(0, pac)
    assert clyde.state == CHASE


def test_power_pellet_and_eating_a_ghost(app, fake_ticks):
    scene = start(app, fake_ticks)
    blinky = scene.ghosts[0]
    scene._eat(*next(iter(scene.level.power)))
    assert blinky.state == FRIGHT
    assert all(g.state == HOME for g in scene.ghosts[1:])  # ghosts at home aren't affected

    scene.pac.x, scene.pac.y = blinky.x, blinky.y
    before = scene.score
    scene._collide(scene.now)
    assert scene.score - before == 200 * scene.difficulty.score_mult
    # Eyes fly home, re-enter the house and come back out.
    states = set()
    frames(app, fake_ticks, 900, lambda i: states.add(blinky.state))
    assert {"popup", "eyes", "entering", "leaving"} <= states
    assert blinky.state in (SCATTER, CHASE) and blinky.revived


def test_death_and_respawn(app, fake_ticks):
    scene = start(app, fake_ticks)
    lives = scene.lives
    blinky = scene.ghosts[0]
    scene.pac.x, scene.pac.y = blinky.x, blinky.y
    scene._collide(scene.now)
    assert scene.pac.dead and scene.lives == lives - 1
    frames(app, fake_ticks, 200)
    assert not scene.pac.dead and scene.pac.cell == (14, 23)


def test_pause_freezes_game_time(app, fake_ticks):
    scene = start(app, fake_ticks)
    app.step([key("ESCAPE")])
    assert isinstance(app.top, PauseScene)
    frozen = app.game_clock.now()
    frames(app, fake_ticks, 100)
    assert app.game_clock.now() == frozen
    app.step([key("ESCAPE")])
    assert app.top is scene
    frames(app, fake_ticks, 10)
    assert app.game_clock.now() == frozen + 160


def test_cheats_win_and_lose(app, fake_ticks):
    scene = start(app, fake_ticks)
    for ch in "aezakmi":
        app.step([key(ch)])
    assert scene.lives == scene.difficulty.lives + 1
    for ch in "god":
        app.step([key(ch)])
    assert isinstance(app.top, ResultScene) and app.top.won
    assert app.save.unlocked == 2 and app.save.records[0] == [scene.score]

    scene = start(app, fake_ticks)
    for ch in "kill":
        app.step([key(ch)])
    assert isinstance(app.top, ResultScene) and not app.top.won


def test_fruit_banks_and_scores(app, fake_ticks):
    scene = start(app, fake_ticks)
    scene._collide = lambda now: None
    frames(app, fake_ticks, 9100 // 16)
    assert scene.fruit_state == "active"
    scene.pac.x, scene.pac.y = scene.level.spawns["fruit"]
    scene._update_fruit(scene.now)
    assert app.save.fruit_bank[0] == 1 and scene.fruits_eaten == [0]


@pytest.mark.parametrize("level", range(len(level_files())))
def test_eaten_ghost_eyes_always_get_home(app, level):
    """From every tile, eyes reach the house and the ghost comes back out."""
    from pacman.actors import Blinky
    from pacman.level import load_level

    maze = load_level(level)
    pac = PacMan(maze, "classic")
    for r, row in enumerate(maze.rows):
        for c in range(len(row)):
            if not maze.open(c, r):
                continue
            ghost = Blinky(maze, DIFFICULTIES[0])
            ghost.x, ghost.y = cell_center(c, r)
            ghost.dir, ghost.state, ghost.moving = "left", EYES, True
            for t in range(1500):
                ghost.update(t * 16, pac, ghost)
                if ghost.state in (CHASE, SCATTER):
                    break
            assert ghost.state in (CHASE, SCATTER), (level + 1, (c, r), ghost.state, ghost.cell)
