"""Sound management — loads and plays all game audio."""

import os
import pygame


class SoundManager:
    """Manages all game sound effects and background loops."""

    def __init__(self, base_path: str):
        pygame.mixer.set_num_channels(8)
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._load(base_path)
        self._dot_toggle = False
        self._siren_channel = pygame.mixer.Channel(0)
        self._loop_channel = pygame.mixer.Channel(1)

    def _load(self, base_path: str):
        sounds_dir = os.path.join(base_path, "sounds")
        if not os.path.isdir(sounds_dir):
            return
        for fname in os.listdir(sounds_dir):
            if fname.endswith(".wav"):
                name = fname[:-4]
                try:
                    self._sounds[name] = pygame.mixer.Sound(
                        os.path.join(sounds_dir, fname))
                except pygame.error:
                    pass

    def _play(self, name: str, loops: int = 0, channel=None):
        snd = self._sounds.get(name)
        if not snd:
            return
        if channel:
            channel.play(snd, loops=loops)
        else:
            snd.play(loops=loops)

    # ---- Public API ----

    def play_start(self):
        self.stop_all()
        self._play("start")

    def start_sound_done(self) -> bool:
        snd = self._sounds.get("start")
        if not snd:
            return True
        return not pygame.mixer.get_busy() or not any(
            pygame.mixer.Channel(i).get_sound() == snd
            for i in range(pygame.mixer.get_num_channels())
        )

    def play_eat_dot(self):
        name = "eat_dot_0" if self._dot_toggle else "eat_dot_1"
        self._dot_toggle = not self._dot_toggle
        self._play(name)

    def play_eat_ghost(self):
        self._play("eat_ghost")

    def play_eat_fruit(self):
        self._play("eat_fruit")

    def play_death(self):
        self.stop_siren()
        self._play("death_0")

    def play_extra_life(self):
        self._play("extend")

    def play_fright(self):
        self._siren_channel.stop()
        self._play("fright", loops=-1, channel=self._loop_channel)

    def stop_fright(self):
        self._loop_channel.stop()

    def play_eyes(self):
        self._play("eyes", loops=-1, channel=self._loop_channel)

    def play_siren(self, siren_level: int = 0):
        self._loop_channel.stop()
        level = min(siren_level, 4)
        self._play(f"siren{level}", loops=-1, channel=self._siren_channel)

    def stop_siren(self):
        self._siren_channel.stop()
        self._loop_channel.stop()

    def play_intermission(self):
        self._play("intermission")

    def stop_all(self):
        pygame.mixer.stop()
