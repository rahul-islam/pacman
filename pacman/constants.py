"""Game-wide constants, enums, directions, colors, and helper functions."""

from enum import Enum, auto

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
TILE_SIZE = 24
HALF_TILE = TILE_SIZE // 2
COLS = 28
ROWS = 31
HEADER_HEIGHT = 3 * TILE_SIZE
FOOTER_HEIGHT = 2 * TILE_SIZE
SCREEN_WIDTH = COLS * TILE_SIZE
SCREEN_HEIGHT = ROWS * TILE_SIZE + HEADER_HEIGHT + FOOTER_HEIGHT
FPS = 60

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BLACK = (0, 0, 0)
BLUE = (33, 33, 222)
DARK_BLUE = (0, 0, 140)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
PINK = (255, 184, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 184, 82)
PEACH = (255, 206, 159)

# ---------------------------------------------------------------------------
# Directions  (strings, matching reference style)
# ---------------------------------------------------------------------------
DIR_RIGHT = "right"
DIR_DOWN = "down"
DIR_LEFT = "left"
DIR_UP = "up"
DIR_NONE = "none"

# (shift_x, shift_y) per direction
DIRECTION_VEC = {
    DIR_RIGHT: (1, 0),
    DIR_DOWN: (0, 1),
    DIR_LEFT: (-1, 0),
    DIR_UP: (0, -1),
    DIR_NONE: (0, 0),
}

OPPOSITE_DIR = {
    DIR_RIGHT: DIR_LEFT, DIR_LEFT: DIR_RIGHT,
    DIR_UP: DIR_DOWN, DIR_DOWN: DIR_UP, DIR_NONE: DIR_NONE,
}

# Collision-map bit indices  (right=0, down=1, left=2, up=3)
DIR_BIT = {DIR_RIGHT: 0, DIR_DOWN: 1, DIR_LEFT: 2, DIR_UP: 3}

# All real directions (for iteration)
ALL_DIRS = (DIR_UP, DIR_LEFT, DIR_DOWN, DIR_RIGHT)

# ---------------------------------------------------------------------------
# Speeds — MUST be integer divisors of TILE_SIZE (24)
# ---------------------------------------------------------------------------
PACMAN_SPEED = 2
GHOST_SPEED = 2
FRIGHTENED_SPEED = 1
EATEN_SPEED = 4
TUNNEL_SPEED = 1

# ---------------------------------------------------------------------------
# Timings (milliseconds — time-based, not frame-based)
# ---------------------------------------------------------------------------
FRIGHTENED_MS = 6000
FRIGHTENED_FLASH_MS = 2000  # start flashing with this much *remaining*

# Per-level frightened durations (ms).  Index 0 = level 1.
# At 0 ms, ghosts reverse but don't turn blue.
FRIGHT_TIMES = [6000, 5000, 4000, 3000, 2000, 5000, 2000, 2000,
                1000, 5000, 2000, 1000, 1000, 3000, 1000, 1000,
                0, 1000, 0]
# Levels beyond this table use 0 (no fright).

# Scatter / Chase durations (ms) per phase
MODE_DURATIONS = [7000, 20000, 7000, 20000, 5000, 20000, 5000, -1]

GHOST_RELEASE_MS = [0, 2000, 5000, 8000]  # Blinky, Pinky, Inky, Clyde

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
POINTS_DOT = 10
POINTS_PELLET = 50
POINTS_GHOST_BASE = 200
POINTS_APPLE = 100
POINTS_STRAWBERRY = 300
EXTRA_LIFE_SCORE = 10000

# ---------------------------------------------------------------------------
# Positions (grid cells)
# ---------------------------------------------------------------------------
GHOST_HOUSE_ENTRANCE = (13, 9)
GHOST_HOUSE_CENTER = (14, 12)
PACMAN_SPAWN = (14, 20)
FRUIT_POS = (14, 15)
TUNNEL_ROW = 12

SCATTER_TARGETS = {
    "blinky": (25, -3),
    "pinky": (2, -3),
    "inky": (27, 34),
    "clyde": (0, 34),
}

# Ghost starting positions  (col, row)
GHOST_STARTS = {
    "blinky": (14, 9),
    "pinky": (14, 12),
    "inky": (12, 12),
    "clyde": (16, 12),
}

# ---------------------------------------------------------------------------
# Tile codes
# ---------------------------------------------------------------------------
T_DOT = 0
T_WALL = 1
T_EMPTY = 2
T_PELLET = 3
T_DOOR = 4
T_HOUSE = 5

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class GhostMode(Enum):
    INDOOR = auto()
    SCATTER = auto()
    CHASE = auto()
    FRIGHTENED = auto()
    EATEN = auto()

class GamePhase(Enum):
    INTRO = auto()
    READY = auto()
    PLAYING = auto()
    DEATH = auto()
    LEVEL_COMPLETE = auto()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def tile_to_pixel(col, row):
    """Return pixel center of tile (col, row)."""
    return col * TILE_SIZE + HALF_TILE, row * TILE_SIZE + HEADER_HEIGHT + HALF_TILE

def pixel_to_cell(px, py):
    """Return grid (col, row) from pixel center.

    Handles tunnel wrapping where px may be outside [0, COLS*TILE_SIZE).
    Always returns integer coordinates even when given float inputs
    (e.g. during ghost-house bobbing).
    """
    col = int((px - HALF_TILE) // TILE_SIZE)
    row = int((py - HEADER_HEIGHT - HALF_TILE) // TILE_SIZE)
    # Wrap column for tunnel (keeps row untouched)
    if col < 0:
        col += COLS
    elif col >= COLS:
        col -= COLS
    return col, row

def is_at_cell_center(px, py, tolerance=0):
    """Check whether a pixel position is at (or within *tolerance* of) a cell
    center.  With tolerance=0 (default) this is an exact check.

    The tolerance allows entities whose speed doesn't evenly divide
    TILE_SIZE to still be recognised as "at center" when they are close
    enough, preventing them from sailing through intersections and walls.
    """
    dx = (px - HALF_TILE) % TILE_SIZE
    dy = (py - HEADER_HEIGHT - HALF_TILE) % TILE_SIZE
    return (dx <= tolerance or dx >= TILE_SIZE - tolerance) and \
           (dy <= tolerance or dy >= TILE_SIZE - tolerance)
