"""Sound, FUN mode, volume and difficulty."""

from ..app import Scene
from ..audio import UI
from ..config import DIFFICULTIES, LIME, MUTED, RED, WHITE, WIDTH, DIM, HEIGHT, key_action
from ..ui import Item, Menu, draw_text


class SettingsScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        s = app.save.settings
        self.menu = Menu(
            [
                Item(lambda: f"SOUND {'ON' if not s.muted else 'OFF'}", self.toggle_sound,
                     color=lambda: RED if s.muted else LIME),
                Item(lambda: f"FUN {'ON' if s.fun else 'OFF'}", self.toggle_fun,
                     color=lambda: LIME if s.fun else RED),
                Item(lambda: f"VOLUME {s.volume}%", lambda: self.volume(10, wrap=True),
                     on_left=lambda: self.volume(-5), on_right=lambda: self.volume(5)),
                Item(lambda: DIFFICULTIES[s.difficulty].name, lambda: self.difficulty(1),
                     on_left=lambda: self.difficulty(-1), on_right=lambda: self.difficulty(1)),
                Item("BACK", self.close),
            ],
            center_x=WIDTH // 2, top=80, spacing=32, size=16, click=lambda: app.audio.play(UI, "click"),
        )

    def _changed(self) -> None:
        self.app.audio.apply_volume()
        self.app.persist()

    def toggle_sound(self) -> None:
        self.app.save.settings.muted = not self.app.save.settings.muted
        self._changed()

    def toggle_fun(self) -> None:
        self.app.save.settings.fun = not self.app.save.settings.fun
        self._changed()

    def volume(self, step: int, wrap: bool = False) -> None:
        s = self.app.save.settings
        value = s.volume + step
        s.volume = value % 110 if wrap else min(100, max(0, value))
        self.app.audio.play(UI, "click")
        self._changed()

    def difficulty(self, step: int) -> None:
        s = self.app.save.settings
        s.difficulty = (s.difficulty + step) % len(DIFFICULTIES)
        self._changed()

    def close(self) -> None:
        self.app.pop()

    def handle_event(self, event) -> None:
        if key_action(event) == "back":
            self.close()
        else:
            self.menu.handle_event(event)

    def draw(self, screen) -> None:
        screen.fill((0, 0, 0))
        draw_text(screen, "SETTINGS", 24, WHITE, title=True, center=(WIDTH // 2, 32))
        self.menu.draw(screen)
        lives = DIFFICULTIES[self.app.save.settings.difficulty].lives
        draw_text(screen, f"{lives} {'LIFE' if lives == 1 else 'LIVES'}", 8, MUTED, center=(WIDTH // 2, 80 + 3 * 32 + 14))
        draw_text(screen, "LEFT / RIGHT TO ADJUST", 8, DIM, center=(WIDTH // 2, HEIGHT - 20))
