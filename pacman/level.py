"""Maze files (assets/levels/NN.txt) and grid geometry.

See tools/generate_levels.py for the file format.
"""

from collections import deque
from functools import cached_property, lru_cache
from pathlib import Path

from .config import ASSETS, COLS, MAZE_TOP, ROWS, TILE

LEVELS_DIR = ASSETS / "levels"

CORRIDOR = set(".o=PBF")  # where Pac-Man and roaming ghosts may go
HOUSE = set("_-pic")  # ghost house floor, door and ghost spawns


def cell_center(col: int, row: int) -> tuple[float, float]:
    return col * TILE + TILE / 2, MAZE_TOP + row * TILE + TILE / 2


def cell_at(x: float, y: float) -> tuple[int, int]:
    return int(x // TILE), int((y - MAZE_TOP) // TILE)


def level_files() -> list[Path]:
    return sorted(LEVELS_DIR.glob("*.txt"))


class Level:
    def __init__(self, path: Path) -> None:
        self.name = path.stem
        self.rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        if len(self.rows) != ROWS or any(len(r) != COLS for r in self.rows):
            raise ValueError(f"{path}: expected {ROWS} rows of {COLS} columns")

        cells: dict[str, list[tuple[int, int]]] = {}
        for r, row in enumerate(self.rows):
            for c, ch in enumerate(row):
                cells.setdefault(ch, []).append((c, r))

        self.pellets = set(cells.get(".", []))
        self.power = set(cells.get("o", []))
        self.doors = cells.get("-", [])
        self.tunnel_rows = {r for r, row in enumerate(self.rows) if row[0] in CORRIDOR}

        def spot(marker: str) -> tuple[float, float]:
            centers = [cell_center(c, r) for c, r in cells[marker]]
            return sum(x for x, _ in centers) / len(centers), sum(y for _, y in centers) / len(centers)

        self.spawns = {name: spot(m) for name, m in (("pacman", "P"), ("blinky", "B"), ("pinky", "p"),
                                                     ("inky", "i"), ("clyde", "c"), ("fruit", "F"))}
        # Ghosts leave through the spot above the door and regroup at Pinky's.
        self.house_exit = self.spawns["blinky"]
        self.house_center = self.spawns["pinky"]
        self.exit_cell = cell_at(*self.house_exit)

    @property
    def pellet_total(self) -> int:
        return len(self.pellets) + len(self.power)

    def char(self, col: int, row: int) -> str:
        if not 0 <= row < ROWS:
            return "#"
        if not 0 <= col < COLS:
            return "=" if row in self.tunnel_rows else "#"
        return self.rows[row][col]

    def open(self, col: int, row: int) -> bool:
        return self.char(col, row) in CORRIDOR

    def wrap(self, col: int, row: int) -> tuple[int, int]:
        """Fold tunnel columns past the edges back onto the board."""
        return (col % COLS, row) if row in self.tunnel_rows else (col, row)

    @cached_property
    def steps_home(self) -> dict[tuple[int, int], int]:
        """Shortest walking distance from every open tile to the house exit."""
        dist = {self.exit_cell: 0}
        todo = deque([self.exit_cell])
        while todo:
            c, r = todo.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = self.wrap(c + dc, r + dr)
                if nxt not in dist and self.open(*nxt):
                    dist[nxt] = dist[(c, r)] + 1
                    todo.append(nxt)
        return dist

    def slow(self, col: int, row: int) -> bool:
        """Tunnel stretch where ghosts move at half speed."""
        return row in self.tunnel_rows and (col <= 5 or col >= COLS - 6)


@lru_cache(maxsize=None)
def load_level(index: int) -> Level:
    return Level(level_files()[index])
