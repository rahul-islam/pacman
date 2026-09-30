"""Sound playback on three reserved channels, with volume, mute and FUN mode."""

import random

import pygame

from .config import ASSETS

SOUNDS_DIR = ASSETS / "sounds"
NAMES = ("intro", "back", "frightened", "seed", "eat_fruit", "eat_ghost", "death", "win", "lose", "cheat", "click")
FUN_NAMES = ("intro", "seed", "death", "win", "lose")  # have remixes under sounds/fun/<name>/

UI, MUSIC, SFX = 0, 1, 2


class Audio:
    def __init__(self, settings) -> None:
        self.settings = settings
        pygame.mixer.set_num_channels(8)
        pygame.mixer.set_reserved(3)
        self.channels = [pygame.mixer.Channel(i) for i in (UI, MUSIC, SFX)]
        self.base = {name: pygame.mixer.Sound(str(SOUNDS_DIR / f"{name}.wav")) for name in NAMES}
        self.sounds = dict(self.base)
        self.apply_volume()

    def apply_volume(self) -> None:
        volume = 0 if self.settings.muted else self.settings.volume / 100
        for channel in self.channels:
            channel.set_volume(volume)

    def shuffle_fun(self) -> None:
        """Pick sounds for the next game: FUN mode swaps in random remixes."""
        self.sounds = dict(self.base)
        if self.settings.fun:
            for name in FUN_NAMES:
                variants = sorted((SOUNDS_DIR / "fun" / name).glob("*.wav"))
                self.sounds[name] = pygame.mixer.Sound(str(random.choice(variants)))

    def length(self, name: str) -> float:
        return self.sounds[name].get_length()

    def play(self, channel: int, name: str) -> None:
        self.channels[channel].play(self.sounds[name])

    def play_if_idle(self, channel: int, name: str) -> None:
        if not self.channels[channel].get_busy():
            self.play(channel, name)

    def keep(self, channel: int, name: str) -> None:
        """Keep `name` playing on `channel`, restarting it whenever it ends."""
        if self.channels[channel].get_sound() is not self.sounds[name]:
            self.play(channel, name)

    def busy(self, channel: int) -> bool:
        return self.channels[channel].get_busy()

    def stop(self, channel: int) -> None:
        self.channels[channel].stop()

    def stop_all(self) -> None:
        for channel in self.channels:
            channel.stop()

    def pause_all(self) -> None:
        for channel in self.channels:
            channel.pause()

    def resume_all(self) -> None:
        for channel in self.channels:
            channel.unpause()
