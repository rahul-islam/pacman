"""Generate the game's mazes (levels 02-11; 01.txt is the hand-made classic
arcade layout and is left alone).

    python tools/generate_levels.py [out_dir]     (default: assets/levels)

A maze is built on a lattice of corridor "nodes" over the left half of the
board. Starting from the full lattice, random corridor segments are removed
while the maze stays connected and dead-end free; the half is then mirrored.
The ghost house, tunnel, spawn points and power pellets sit at fixed places.

Level file format (31 rows x 28 columns):
    #  wall                 .  pellet             o  power pellet
    =  open, no pellet      -  ghost-house door   _  ghost-house floor
    P  Pac-Man spawn        B  Blinky spawn       F  fruit spot
    p / i / c  Pinky / Inky / Clyde spawn (inside the house)
Two-cell markers (PP, BB, FF...) place a spawn between the two cells.
"""

import os
import random
import sys
from collections import deque

COLS, ROWS = 28, 31
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (seed, lattice columns, lattice rows) for levels 2..11
LEVELS = [
    (11, (1, 6, 9, 12), (1, 5, 8, 11, 14, 17, 20, 23, 26, 29)),
    (23, (1, 6, 9, 12), (1, 4, 8, 11, 14, 17, 20, 23, 26, 29)),
    (37, (1, 4, 9, 12), (1, 5, 8, 11, 14, 17, 20, 23, 26, 29)),
    (41, (1, 6, 9, 12), (1, 5, 8, 11, 14, 17, 20, 23, 26, 29)),
    (53, (1, 4, 9, 12), (1, 4, 8, 11, 14, 17, 20, 23, 26, 29)),
    (67, (1, 6, 9, 12), (1, 4, 8, 11, 14, 17, 20, 23, 26, 29)),
    (71, (1, 4, 9, 12), (1, 5, 8, 11, 14, 17, 20, 23, 26, 29)),
    (83, (1, 6, 9, 12), (1, 5, 8, 11, 14, 17, 20, 23, 26, 29)),
    (97, (1, 4, 9, 12), (1, 4, 8, 11, 14, 17, 20, 23, 26, 29)),
    (101, (1, 6, 9, 12), (1, 4, 8, 11, 14, 17, 20, 23, 26, 29)),
]

HOUSE = {
    12: "###--###",
    13: "#______#",
    14: "#iippcc#",
    15: "#______#",
    16: "########",
}
HOUSE_LEFT = 10
TUNNEL_ROW = 14
FIRST_GENERATED = 2  # level number of the first generated maze
PAC_ROW = 23
CENTER = 99  # pseudo column: corridor crossing the centre line


def build_graph(cols, rows):
    """Candidate nodes/edges on the left half, and which edges are mandatory."""
    banned_nodes = {(1, 11), (1, 17), (12, 14)}
    nodes = {(c, r) for c in cols for r in rows if (c, r) not in banned_nodes}
    edges, mandatory = set(), set()

    def add(a, b, must=False):
        if a in nodes and (b in nodes or b[0] == CENTER):
            edges.add((a, b))
            if must:
                mandatory.add((a, b))

    for r in rows:
        for c1, c2 in zip(cols, cols[1:]):
            if r == TUNNEL_ROW and c1 == 9:
                continue  # ghost house
            must = r == TUNNEL_ROW or (r in (11, 17) and c1 == 9)
            add((c1, r), (c2, r), must)
        if r != TUNNEL_ROW:
            add((cols[-1], r), (CENTER, r), must=r in (11, 17, PAC_ROW))
    for c in cols:
        for r1, r2 in zip(rows, rows[1:]):
            if c == cols[-1] and 11 <= r1 < 17:
                continue  # ghost house
            add((c, r1), (c, r2), must=c == 9 and 11 <= r1 < 17)
    return nodes, edges, mandatory


def degrees(edges):
    deg = {}
    for a, b in edges:
        deg[a] = deg.get(a, 0) + 1
        if b[0] == CENTER:
            deg[a] += 1  # mirrored side counts as a neighbour
        else:
            deg[b] = deg.get(b, 0) + 1
    deg[(1, TUNNEL_ROW)] = deg.get((1, TUNNEL_ROW), 0) + 1  # tunnel exit
    return deg


def connected(edges):
    """The mirrored maze is connected iff the left half is (crossing edges
    only link a node to its own mirror image)."""
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set())
        if b[0] != CENTER:
            adj.setdefault(b, set())
            adj[a].add(b)
            adj[b].add(a)
    if not adj:
        return False
    start = next(iter(adj))
    seen, todo = {start}, [start]
    while todo:
        for n in adj[todo.pop()]:
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return len(seen) == len(adj)


def carve(seed, cols, rows):
    rng = random.Random(seed)
    _, edges, mandatory = build_graph(cols, rows)
    optional = sorted(edges - mandatory)
    rng.shuffle(optional)
    target = int(len(optional) * rng.uniform(0.32, 0.42))
    removed = 0
    for e in optional:
        if removed >= target:
            break
        trial = edges - {e}
        if any(d == 1 for d in degrees(trial).values()) or not connected(trial):
            continue
        edges = trial
        removed += 1
    return edges


def rasterize(edges, rows):
    grid = [["#"] * COLS for _ in range(ROWS)]

    def open_cell(c, r, ch="."):
        grid[r][c] = ch
        grid[r][COLS - 1 - c] = ch

    for a, b in edges:
        (c1, r1), (c2, r2) = a, ((COLS // 2 - 1) if b[0] == CENTER else b[0], b[1])
        for c in range(min(c1, c2), max(c1, c2) + 1):
            for r in range(min(r1, r2), max(r1, r2) + 1):
                open_cell(c, r)
    open_cell(0, TUNNEL_ROW)

    for r, line in HOUSE.items():
        for i, ch in enumerate(line):
            grid[r][HOUSE_LEFT + i] = ch

    # No pellets around the ghost house or in the tunnels.
    for r in range(9, 20):
        for c in range(7, COLS - 7):
            if grid[r][c] == ".":
                grid[r][c] = "="
    for c in list(range(0, 6)) + list(range(COLS - 6, COLS)):
        if grid[TUNNEL_ROW][c] == ".":
            grid[TUNNEL_ROW][c] = "="

    for c in (13, 14):
        grid[11][c] = "B"
        grid[17][c] = "F"
        grid[PAC_ROW][c] = "P"
    for r in (rows[1], PAC_ROW):
        open_cell(1, r, "o")
    return ["".join(row) for row in grid]


# ---------------------------------------------------------------------------
# Validation (also used by the tests)
# ---------------------------------------------------------------------------
WALKABLE = set(".o=PBF")


def validate(maze):
    problems = []
    if len(maze) != ROWS or any(len(row) != COLS for row in maze):
        return ["bad size"]
    for r, row in enumerate(maze):
        mirrored = row[::-1].translate(str.maketrans("ic", "ci"))
        if row != mirrored:
            problems.append(f"row {r} not symmetric")

    def walk(c, r):
        if 0 <= r < ROWS and 0 <= c < COLS:
            return maze[r][c] in WALKABLE
        return 0 <= r < ROWS and (c < 0 or c >= COLS) and maze[r][0] in WALKABLE

    cells = [(c, r) for r in range(ROWS) for c in range(COLS) if maze[r][c] in WALKABLE]
    for c, r in cells:
        if sum(walk(c + dx, r + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) < 2:
            problems.append(f"dead end at {(c, r)}")
    start = next((c, r) for c, r in cells if maze[r][c] == "P")
    seen, todo = {start}, deque([start])
    while todo:
        c, r = todo.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = ((c + dx) % COLS, r + dy)
            if n not in seen and walk(c + dx, r + dy):
                seen.add(n)
                todo.append(n)
    if len(seen) != len(cells):
        problems.append(f"{len(cells) - len(seen)} unreachable cells")
    text = "".join(maze)
    for marker, count in (("P", 2), ("B", 2), ("F", 2), ("p", 2), ("i", 2), ("c", 2), ("o", 4), ("-", 2)):
        if text.count(marker) != count:
            problems.append(f"expected {count} '{marker}', found {text.count(marker)}")
    pellets = text.count(".")
    if not 180 <= pellets <= 300:
        problems.append(f"{pellets} pellets")
    return problems


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "levels")
    os.makedirs(out_dir, exist_ok=True)
    for i, (seed, cols, rows) in enumerate(LEVELS, FIRST_GENERATED):
        maze = rasterize(carve(seed, cols, rows), rows)
        problems = validate(maze)
        if problems:
            raise SystemExit(f"level {i} (seed {seed}): {problems}")
        with open(os.path.join(out_dir, f"{i:02d}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(maze) + "\n")
        print(f"level {i:02d}: {''.join(maze).count('.')} pellets")


if __name__ == "__main__":
    main()
