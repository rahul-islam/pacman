"""Screens drawn over a frozen, frosted snapshot of the game: pause and results."""

from ..app import Scene
from ..audio import MUSIC, UI
from ..config import MUTED, WHITE, WIDTH, key_action
from ..ui import Item, Menu, draw_text, frosted


class Overlay(Scene):
    def __init__(self, app, snapshot) -> None:
        super().__init__(app)
        self.backdrop = frosted(snapshot)
        self.menu: Menu | None = None

    def click(self) -> None:
        self.app.audio.play(UI, "click")

    def handle_event(self, event) -> None:
        if key_action(event) == "back":
            self.on_back()
        elif self.menu:
            self.menu.handle_event(event)

    def on_back(self) -> None:
        pass

    def draw(self, screen) -> None:
        screen.blit(self.backdrop, (0, 0))
        if self.menu:
            self.menu.draw(screen)


def to_menu(app) -> None:
    from .menu import MenuScene

    app.replace(MenuScene(app))


def new_game(app) -> None:
    from .play import PlayScene

    app.replace(PlayScene(app))


class PauseScene(Overlay):
    def __init__(self, app, game) -> None:
        super().__init__(app, game.snapshot())
        self.menu = Menu(
            [Item("CONTINUE", app.pop), Item("RESTART", lambda: new_game(app)), Item("MENU", lambda: to_menu(app))],
            center_x=WIDTH // 2, top=120, spacing=32, size=16, click=self.click,
        )

    def on_back(self) -> None:
        self.app.pop()

    def draw(self, screen) -> None:
        super().draw(screen)
        draw_text(screen, "PAUSE", 32, WHITE, title=True, center=(WIDTH // 2, 48))


class ResultScene(Overlay):
    def __init__(self, app, snapshot, *, won: bool, score: int) -> None:
        super().__init__(app, snapshot)
        self.won = won
        self.score = score
        items = []
        if won and app.save.level + 1 < app.save.unlocked:
            items.append(Item("NEXT LEVEL", self.next_level))
        if not won:
            items.append(Item("RESTART", lambda: new_game(app)))
        items.append(Item("MENU", lambda: to_menu(app)))
        self.menu = Menu(items, center_x=WIDTH // 2, top=204, spacing=30, size=16, click=self.click)

    def enter(self) -> None:
        self.app.audio.play(MUSIC, "win" if self.won else "lose")

    def leave(self, covered: bool) -> None:
        self.app.audio.stop(MUSIC)

    def next_level(self) -> None:
        self.app.save.level += 1
        self.app.persist()
        new_game(self.app)

    def on_back(self) -> None:
        to_menu(self.app)

    def draw(self, screen) -> None:
        super().draw(screen)
        first, second = ("YOU", "WON") if self.won else ("GAME", "OVER")
        draw_text(screen, first, 40, WHITE, title=True, center=(WIDTH // 2, 36))
        draw_text(screen, second, 40, WHITE, title=True, center=(WIDTH // 2, 80))
        draw_text(screen, f"SCORE {self.score}", 16, WHITE, center=(WIDTH // 2, 132))
        draw_text(screen, f"BEST {self.app.save.best(self.app.save.level)}", 16, MUTED, center=(WIDTH // 2, 158))

