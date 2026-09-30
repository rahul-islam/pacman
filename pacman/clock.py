import pygame


class GameClock:
    """Milliseconds of play time. Stands still while paused, so ghost, fruit
    and death timers don't run out behind the pause menu."""

    def __init__(self) -> None:
        self._paused_at: int | None = None
        self._offset = 0

    def now(self) -> int:
        real = self._paused_at if self._paused_at is not None else pygame.time.get_ticks()
        return real - self._offset

    def pause(self) -> None:
        if self._paused_at is None:
            self._paused_at = pygame.time.get_ticks()

    def resume(self) -> None:
        if self._paused_at is not None:
            self._offset += pygame.time.get_ticks() - self._paused_at
            self._paused_at = None
