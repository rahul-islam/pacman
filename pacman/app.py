"""Main loop and scene stack."""

import sys

import pygame

from .audio import Audio
from .clock import GameClock
from .config import FPS, HEIGHT, SAVE_FILE, WIDTH
from .save import SaveData


class Scene:
    """One screen. Scenes are stacked; only the top one gets input and updates."""

    def __init__(self, app: "App") -> None:
        self.app = app

    def enter(self) -> None:
        """Became the top scene (first time or after an overlay closed)."""

    def leave(self, covered: bool) -> None:
        """Stopped being the top scene; `covered` means another scene went on top."""

    def handle_event(self, event) -> None:
        pass

    def update(self, dt: int) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        pass

    def snapshot(self) -> pygame.Surface:
        surface = pygame.Surface((WIDTH, HEIGHT))
        self.draw(surface)
        return surface


class App:
    def __init__(self, save_path=SAVE_FILE, scaled: bool = True) -> None:
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED if scaled else 0)
        self.clock = pygame.time.Clock()
        self.game_clock = GameClock()
        self.save_path = save_path
        self.save = SaveData.load(save_path)
        self.audio = Audio(self.save.settings)
        self.stack: list[Scene] = []

    @property
    def top(self) -> Scene:
        return self.stack[-1]

    def push(self, scene: Scene) -> None:
        if self.stack:
            self.top.leave(covered=True)
        self.stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        self.stack.pop().leave(covered=False)
        if self.stack:
            self.top.enter()

    def replace(self, scene: Scene) -> None:
        """Clear the stack and show `scene`."""
        while self.stack:
            self.stack.pop().leave(covered=False)
        self.push(scene)

    def persist(self) -> None:
        self.save.write(self.save_path)

    def step(self, events) -> None:
        """Run one frame: events, logic, drawing."""
        for event in events:
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_q and event.mod & pygame.KMOD_CTRL
            ):
                self.quit()
            self.top.handle_event(event)
        self.top.update(self.clock.get_time())
        self.top.draw(self.screen)

    def run(self) -> None:
        while True:
            self.step(pygame.event.get())
            pygame.display.flip()
            self.clock.tick(FPS)

    def quit(self) -> None:
        self.persist()
        pygame.quit()
        sys.exit()
