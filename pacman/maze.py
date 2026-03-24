"""Maze data, collision map, wall rendering, and dot management."""

import pygame
from .constants import (
    TILE_SIZE, HALF_TILE, COLS, ROWS, HEADER_HEIGHT, SCREEN_WIDTH, TUNNEL_ROW,
    T_DOT, T_WALL, T_EMPTY, T_PELLET, T_DOOR, T_HOUSE,
    POINTS_DOT, POINTS_PELLET,
    DIR_RIGHT, DIR_DOWN, DIR_LEFT, DIR_UP, DIR_BIT, ALL_DIRS, DIRECTION_VEC,
    BLUE, DARK_BLUE, PEACH,
    tile_to_pixel,
)

# ---------------------------------------------------------------------------
# Layout  (28 cols × 31 rows)
# ---------------------------------------------------------------------------
MAZE_LAYOUT = [
    "1111111111111111111111111111",  # 0
    "1000000000000110000000000001",  # 1
    "1011110111110110111110111101",  # 2
    "1311110111110110111110111131",  # 3
    "1000000000000000000000000001",  # 4
    "1011110110111111110110111101",  # 5
    "1000000110000110000110000001",  # 6
    "1111110111110110111110111111",  # 7
    "1111110111110110111110111111",  # 8
    "1111110110000000000110111111",  # 9
    "1111110110111441110110111111",  # 10
    "1111110110155555510110111111",  # 11
    "2222220000155555510000222222",  # 12
    "1111110110155555510110111111",  # 13
    "1111110110111111110110111111",  # 14
    "1111110110000000000110111111",  # 15
    "1111110110111111110110111111",  # 16
    "1111110110111111110110111111",  # 17
    "1000000000000110000000000001",  # 18
    "1011110111110110111110111101",  # 19
    "1300110000000000000000110031",  # 20
    "1110110110111111110110110111",  # 21
    "1000000110000110000110000001",  # 22
    "1011111111110110111111111101",  # 23
    "1000000000000000000000000001",  # 24
    "1111111111111111111111111111",  # 25
    "1111111111111111111111111111",  # 26
    "1111111111111111111111111111",  # 27
    "1111111111111111111111111111",  # 28
    "1111111111111111111111111111",  # 29
    "1111111111111111111111111111",  # 30
]


class Maze:
    """Tile-based maze with collision map and dot tracking."""

    def __init__(self):
        self.grid: list[list[int]] = []
        self.collision_map: list[list[int]] = []
        self.total_dots = 0
        self.wall_surface: pygame.Surface | None = None
        self._flash_surface: pygame.Surface | None = None
        self._parse()

    # ------------------------------------------------------------------
    # Parsing & collision map
    # ------------------------------------------------------------------
    def _parse(self):
        self.grid = []
        self.total_dots = 0
        for row_str in MAZE_LAYOUT:
            row = [int(ch) for ch in row_str]
            self.grid.append(row)
            for val in row:
                if val in (T_DOT, T_PELLET):
                    self.total_dots += 1
        self._build_collision_map()

    def _build_collision_map(self):
        """Auto-generate 4-bit direction flags per cell.
        bit 0 = right passable, bit 1 = down, bit 2 = left, bit 3 = up.
        """
        self.collision_map = [[0] * COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == T_WALL:
                    continue
                flags = 0
                for d in ALL_DIRS:
                    dx, dy = DIRECTION_VEC[d]
                    nc, nr = c + dx, r + dy
                    if self._is_passable(nc, nr, from_tile=self.grid[r][c]):
                        flags |= (1 << DIR_BIT[d])
                self.collision_map[r][c] = flags

    def _is_passable(self, col, row, from_tile=T_EMPTY):
        """Can a character step into (col, row)?"""
        if row < 0 or row >= ROWS:
            return False
        if col < 0 or col >= COLS:
            return row == TUNNEL_ROW
        val = self.grid[row][col]
        if val == T_WALL:
            return False
        return True

    def reset(self):
        self._parse()
        self.wall_surface = None
        self._flash_surface = None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def can_move(self, col, row, direction, *, is_ghost=False, allow_house=False):
        """Check if direction is passable from cell (col, row).

        ``allow_house`` must be explicitly True for an entity to move
        through the ghost-house door or into house tiles.  Normal ghosts
        in Chase/Scatter must NOT pass through the door.
        """
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            if row == TUNNEL_ROW:
                return True
            return False
        flags = self.collision_map[row][col]
        bit = DIR_BIT[direction]
        can = bool(flags & (1 << bit))
        if not can:
            return False
        # Check if destination is door/house
        dx, dy = DIRECTION_VEC[direction]
        nc, nr = col + dx, row + dy
        if 0 <= nc < COLS and 0 <= nr < ROWS:
            val = self.grid[nr][nc]
            if val in (T_DOOR, T_HOUSE) and not allow_house:
                return False
        return True

    def eat_dot(self, col, row):
        """Eat a dot/pellet.  Returns (points, is_power_pellet)."""
        if col < 0 or col >= COLS or row < 0 or row >= ROWS:
            return 0, False
        val = self.grid[row][col]
        if val == T_DOT:
            self.grid[row][col] = T_EMPTY
            self.total_dots -= 1
            return POINTS_DOT, False
        if val == T_PELLET:
            self.grid[row][col] = T_EMPTY
            self.total_dots -= 1
            return POINTS_PELLET, True
        return 0, False

    def get_valid_directions(self, col, row, current_dir, *,
                              is_ghost=True, allow_house=False):
        """Valid directions excluding reverse of current_dir."""
        from .constants import OPPOSITE_DIR
        dirs = []
        for d in ALL_DIRS:
            if d == OPPOSITE_DIR.get(current_dir):
                continue
            if self.can_move(col, row, d, is_ghost=is_ghost,
                             allow_house=allow_house):
                dirs.append(d)
        return dirs

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render_walls(self):
        self.wall_surface = pygame.Surface(
            (SCREEN_WIDTH, ROWS * TILE_SIZE), pygame.SRCALPHA)
        for r in range(ROWS):
            for c in range(COLS):
                val = self.grid[r][c]
                if val == T_WALL:
                    self._draw_wall_tile(c, r)
                elif val == T_DOOR:
                    x, y = c * TILE_SIZE, r * TILE_SIZE
                    pygame.draw.rect(self.wall_surface, PEACH,
                                     (x, y + HALF_TILE - 2, TILE_SIZE, 4))

    def _draw_wall_tile(self, col, row):
        x, y = col * TILE_SIZE, row * TILE_SIZE
        pygame.draw.rect(self.wall_surface, DARK_BLUE,
                         (x, y, TILE_SIZE, TILE_SIZE))
        neighbours = [
            (0, -1, x, y, TILE_SIZE, 2),
            (0, 1, x, y + TILE_SIZE - 2, TILE_SIZE, 2),
            (-1, 0, x, y, 2, TILE_SIZE),
            (1, 0, x + TILE_SIZE - 2, y, 2, TILE_SIZE),
        ]
        for dx, dy, bx, by, bw, bh in neighbours:
            nc, nr = col + dx, row + dy
            draw = True
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                draw = self.grid[nr][nc] != T_WALL
            if draw:
                pygame.draw.rect(self.wall_surface, BLUE, (bx, by, bw, bh))

    def draw_walls(self, surface, *, flash=False):
        if self.wall_surface is None:
            self.render_walls()
        if flash:
            if self._flash_surface is None:
                self._flash_surface = self.wall_surface.copy()
                self._flash_surface.fill(
                    (200, 200, 200, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(self._flash_surface, (0, HEADER_HEIGHT))
        else:
            surface.blit(self.wall_surface, (0, HEADER_HEIGHT))

    def draw_dots(self, surface, assets, frame_count):
        for r in range(ROWS):
            for c in range(COLS):
                val = self.grid[r][c]
                if val == T_DOT:
                    cx, cy = tile_to_pixel(c, r)
                    dot = assets["dot"]
                    surface.blit(dot, (cx - dot.get_width() // 2,
                                       cy - dot.get_height() // 2))
                elif val == T_PELLET:
                    if (frame_count // 10) % 2 == 0:
                        cx, cy = tile_to_pixel(c, r)
                        pygame.draw.circle(surface, PEACH, (cx, cy), 6)
