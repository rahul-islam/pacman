"""Persistent progress: settings, unlocked levels, records, fruit bank, skins."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .art import SKIN_BY_KEY
from .config import DIFFICULTIES, FRUIT_NAMES

VERSION = 1
MAX_RECORDS = 5


@dataclass
class Settings:
    volume: int = 100
    muted: bool = False
    difficulty: int = 0
    fun: bool = False


@dataclass
class SaveData:
    settings: Settings = field(default_factory=Settings)
    level: int = 0  # currently selected level
    records: list[list[int]] = field(default_factory=lambda: [[]])  # one list per unlocked level
    fruit_bank: list[int] = field(default_factory=lambda: [0] * len(FRUIT_NAMES))
    skins: list[str] = field(default_factory=lambda: ["classic"])
    skin: str = "classic"
    # Set by the unlock-everything cheat: progress is no longer written to disk.
    frozen: bool = field(default=False, compare=False)

    # -- levels & records ----------------------------------------------------
    @property
    def unlocked(self) -> int:
        return len(self.records)

    def best(self, level: int) -> int:
        return max(self.records[level], default=0) if level < self.unlocked else 0

    def add_record(self, level: int, score: int) -> None:
        if level < self.unlocked:
            top = sorted(set(self.records[level]) | {score}, reverse=True)
            self.records[level] = top[:MAX_RECORDS]

    def unlock_after(self, level: int, total_levels: int) -> None:
        if level + 1 == self.unlocked < total_levels:
            self.records.append([])

    def unlock_all(self, total_levels: int) -> None:
        self.records += [[] for _ in range(total_levels - self.unlocked)]
        self.skins = list(SKIN_BY_KEY)
        self.frozen = True

    # -- skins -------------------------------------------------------------
    def can_afford(self, skin) -> bool:
        return all(self.fruit_bank[i] >= n for i, n in skin.cost)

    def buy(self, skin) -> bool:
        if skin.key in self.skins:
            return True
        if not self.can_afford(skin):
            return False
        for i, n in skin.cost:
            self.fruit_bank[i] -= n
        self.skins.append(skin.key)
        return True

    # -- persistence -------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "SaveData":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("version") != VERSION:
                return cls()
            data = cls(
                settings=Settings(**raw["settings"]),
                level=int(raw["level"]),
                records=[list(map(int, r)) for r in raw["records"]] or [[]],
                fruit_bank=list(map(int, raw["fruit_bank"])),
                skins=[s for s in raw["skins"] if s in SKIN_BY_KEY] or ["classic"],
                skin=raw["skin"],
            )
        except (OSError, ValueError, KeyError, TypeError):
            return cls()
        data.settings.difficulty %= len(DIFFICULTIES)
        data.level = min(max(data.level, 0), data.unlocked - 1)
        if data.skin not in data.skins:
            data.skin = "classic"
        return data

    def write(self, path: Path) -> None:
        if self.frozen:
            return
        payload = {"version": VERSION, **asdict(self)}
        payload.pop("frozen")
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
