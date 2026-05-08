"""
Super Mario Bros. 1 - Famicom edition (Pygame)
60 FPS, NES-accurate Mario physics, all 32 stages (1-1 to 8-4).
No external assets - every sprite is drawn procedurally in code.

Run:    python acholdingsmb4k.py        (requires pygame / pygame-ce)

Controls
  Arrow Left / Right or A / D : walk
  hold Shift                  : run
  Space / Z / Up              : jump (variable height)
  R                           : restart current stage
  N / P                       : next / previous stage
  Esc                         : quit
"""

import sys
import math
import pygame
from pygame.locals import (
    QUIT, KEYDOWN, KEYUP,
    K_LEFT, K_RIGHT, K_UP, K_DOWN,
    K_a, K_d, K_w, K_s,
    K_SPACE, K_z, K_x,
    K_LSHIFT, K_RSHIFT,
    K_n, K_p, K_r, K_ESCAPE,
)


# ====================================================================
# Display & timing
# ====================================================================
NES_W, NES_H = 256, 240
SCALE = 3
SCREEN_W, SCREEN_H = NES_W * SCALE, NES_H * SCALE
FPS = 60
TILE = 16
ROWS = NES_H // TILE          # 15
VIS_COLS = NES_W // TILE      # 16

# ====================================================================
# Famicom-tuned physics (px / frame at 60 fps)
# Values track the NES original closely enough to "feel" right.
# ====================================================================
WALK_ACC     = 0.0586
RUN_ACC      = 0.0889
SKID_DEC     = 0.1016
RELEASE_DEC  = 0.0508
WALK_MAX     = 1.5625
RUN_MAX      = 2.5625
JUMP_V_LOW   = -4.0
JUMP_V_HIGH  = -5.0
GRAV_HOLD    = 0.125
GRAV_FREE    = 0.4375
MAX_FALL     = 4.5
ENEMY_WALK   = 0.4
SHELL_SPEED  = 3.0
BUMP_DURATION = 8


# ====================================================================
# Palette (close to NES master palette)
# ====================================================================
SKY_DAY    = (92,  148, 252)
SKY_NIGHT  = (0,   0,   0)
WHITE      = (252, 252, 252)
BLACK      = (0,   0,   0)
RED        = (228, 0,   88)
RED_D      = (148, 0,   0)
SKIN       = (252, 188, 152)
HAIR       = (124, 60,  0)
BROWN      = (172, 76,  0)
BROWN_D    = (124, 60,  0)
BLUE_OVR   = (0,   88,  248)
GREEN      = (0,   168, 0)
GREEN_D    = (0,   100, 0)
GRAY       = (180, 180, 180)
DGRAY      = (96,  96,  96)
BRICK_C    = (204, 80,  0)
QGOLD      = (252, 188, 24)
QSHAD      = (132, 76,  0)
COIN_C     = (252, 216, 80)
LAVA_R     = (228, 0,   0)
LAVA_O     = (252, 152, 0)
FLAG_BALL  = (228, 0,   0)
CASTLE_C   = (180, 180, 180)
CASTLE_D   = (124, 124, 124)
SHELL_C    = (228, 228, 0)


# ====================================================================
# Tile IDs
# ====================================================================
EMPTY     = 0
GROUND    = 1
BRICK_T   = 2
QBLOCK    = 3
HBLOCK    = 4    # bumped/used "?" block
PIPE_TL   = 5
PIPE_TR   = 6
PIPE_BL   = 7
PIPE_BR   = 8
FLAG      = 9
FLAG_TOP  = 10
CASTLE_T  = 11
LAVA_T    = 12
CLOUD_T   = 13
HARD_T    = 14   # rocky cement block (Bowser stages)
COIN_T    = 15
BLOCK_U   = 16   # underground / castle brick (gray-blue)
BUSH_T    = 17

SOLID = {
    GROUND, BRICK_T, QBLOCK, HBLOCK,
    PIPE_TL, PIPE_TR, PIPE_BL, PIPE_BR,
    CASTLE_T, HARD_T, BLOCK_U,
}
DEADLY = {LAVA_T}
BUMPABLE = {BRICK_T, QBLOCK}


# ====================================================================
# Procedural sprite builders
# ====================================================================
def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def build_mario_small(facing_right=True):
    """12x16 stylised SMB1 small Mario."""
    s = _surf(12, 16)
    px = s.set_at
    for x in range(2, 10):
        px((x, 1), RED); px((x, 2), RED)
    for x in range(1, 4):
        px((x, 3), RED)
    for x in (4, 5):
        px((x, 3), HAIR)
    px((4, 4), HAIR); px((4, 5), HAIR); px((4, 6), HAIR)
    for y in range(3, 7):
        for x in range(6, 10):
            px((x, y), SKIN)
    px((5, 4), SKIN); px((5, 5), SKIN); px((5, 6), SKIN)
    px((8, 4), BLACK); px((8, 5), BLACK)
    for x in range(7, 10):
        px((x, 6), HAIR)
    px((6, 7), RED); px((7, 7), RED)
    for x in range(2, 10):
        px((x, 8), RED)
    for x in range(1, 11):
        px((x, 9), RED)
    for x in range(3, 9):
        px((x, 10), BLUE_OVR)
    for x in range(2, 10):
        px((x, 11), BLUE_OVR)
    px((4, 10), QGOLD); px((7, 10), QGOLD)
    for x in range(2, 5):
        px((x, 12), BLUE_OVR)
    for x in range(7, 10):
        px((x, 12), BLUE_OVR)
    for x in range(1, 5):
        px((x, 13), BROWN_D); px((x, 14), BROWN_D)
    for x in range(7, 11):
        px((x, 13), BROWN_D); px((x, 14), BROWN_D)
    if not facing_right:
        s = pygame.transform.flip(s, True, False)
    return s


def build_mario_jump(facing_right=True):
    s = build_mario_small(True)
    s = pygame.transform.flip(s, False, False)
    if not facing_right:
        s = pygame.transform.flip(s, True, False)
    return s


def build_goomba():
    s = _surf(TILE, TILE)
    pygame.draw.ellipse(s, BROWN,   (1, 2, 14, 10))
    pygame.draw.ellipse(s, BROWN_D, (1, 2, 14, 10), 1)
    pygame.draw.rect(s, BROWN,      (2, 9, 12, 4))
    pygame.draw.rect(s, WHITE, (3, 6, 3, 4))
    pygame.draw.rect(s, WHITE, (10, 6, 3, 4))
    pygame.draw.rect(s, BLACK, (4, 7, 1, 2))
    pygame.draw.rect(s, BLACK, (11, 7, 1, 2))
    pygame.draw.line(s, BLACK, (3, 5), (6, 6))
    pygame.draw.line(s, BLACK, (12, 5), (9, 6))
    pygame.draw.rect(s, BROWN_D, (1, 13, 5, 3))
    pygame.draw.rect(s, BROWN_D, (10, 13, 5, 3))
    return s


def build_goomba_squashed():
    s = _surf(TILE, TILE)
    pygame.draw.ellipse(s, BROWN,   (1, 11, 14, 5))
    pygame.draw.rect(s, BROWN_D,    (1, 14, 14, 2))
    pygame.draw.rect(s, BLACK, (4, 12, 2, 2))
    pygame.draw.rect(s, BLACK, (10, 12, 2, 2))
    return s


def build_koopa():
    s = _surf(TILE, TILE * 2 - 8)  # 16 x 24
    pygame.draw.ellipse(s, GREEN,   (0, 8, 16, 14))
    pygame.draw.ellipse(s, GREEN_D, (0, 8, 16, 14), 2)
    pygame.draw.rect(s, SHELL_C,    (3, 12, 10, 6))
    pygame.draw.ellipse(s, SHELL_C, (4, 0, 9, 9))
    pygame.draw.rect(s, BLACK,      (10, 3, 1, 2))
    pygame.draw.rect(s, SHELL_C,    (1, 20, 4, 3))
    pygame.draw.rect(s, SHELL_C,    (11, 20, 4, 3))
    return s


def build_block(kind, font_q):
    s = _surf(TILE, TILE)
    if kind == GROUND:
        pygame.draw.rect(s, BROWN,   (0, 0, TILE, TILE))
        pygame.draw.rect(s, BROWN_D, (0, 0, TILE, TILE), 1)
        pygame.draw.line(s, BROWN_D, (4, 0), (4, TILE - 1))
        pygame.draw.line(s, BROWN_D, (12, 0), (12, TILE - 1))
        pygame.draw.line(s, BROWN_D, (0, 8), (TILE - 1, 8))
    elif kind == BRICK_T:
        pygame.draw.rect(s, BRICK_C, (0, 0, TILE, TILE))
        pygame.draw.rect(s, BLACK,   (0, 0, TILE, TILE), 1)
        pygame.draw.line(s, BLACK, (0, 8), (TILE - 1, 8))
        pygame.draw.line(s, BLACK, (4, 0), (4, 7))
        pygame.draw.line(s, BLACK, (12, 0), (12, 7))
        pygame.draw.line(s, BLACK, (8, 8), (8, TILE - 1))
    elif kind == QBLOCK:
        pygame.draw.rect(s, QGOLD, (0, 0, TILE, TILE))
        pygame.draw.rect(s, QSHAD, (0, 0, TILE, TILE), 1)
        q = font_q.render("?", True, BLACK)
        s.blit(q, (5, 1))
        pygame.draw.rect(s, QSHAD, (1, 1, 2, 2))
        pygame.draw.rect(s, QSHAD, (TILE - 3, 1, 2, 2))
        pygame.draw.rect(s, QSHAD, (1, TILE - 3, 2, 2))
        pygame.draw.rect(s, QSHAD, (TILE - 3, TILE - 3, 2, 2))
    elif kind == HBLOCK:
        pygame.draw.rect(s, QSHAD, (0, 0, TILE, TILE))
        pygame.draw.rect(s, BLACK, (0, 0, TILE, TILE), 1)
    elif kind == HARD_T:
        pygame.draw.rect(s, GRAY,  (0, 0, TILE, TILE))
        pygame.draw.rect(s, DGRAY, (0, 0, TILE, TILE), 1)
        pygame.draw.line(s, DGRAY, (8, 0), (8, TILE - 1))
        pygame.draw.line(s, DGRAY, (0, 8), (TILE - 1, 8))
    elif kind == BLOCK_U:
        pygame.draw.rect(s, (148, 76, 0), (0, 0, TILE, TILE))
        pygame.draw.rect(s, (60, 32, 0),  (0, 0, TILE, TILE), 1)
        pygame.draw.line(s, (60, 32, 0), (0, 8), (TILE - 1, 8))
    elif kind == PIPE_TL:
        pygame.draw.rect(s, GREEN,   (2, 0, TILE - 2, TILE))
        pygame.draw.rect(s, GREEN_D, (0, 0, TILE, 6))
        pygame.draw.rect(s, BLACK,   (0, 0, TILE, 6), 1)
        pygame.draw.rect(s, BLACK,   (2, 0, TILE - 2, TILE), 1)
        pygame.draw.line(s, GREEN,   (4, 1), (4, 4))
    elif kind == PIPE_TR:
        pygame.draw.rect(s, GREEN,   (0, 0, TILE - 2, TILE))
        pygame.draw.rect(s, GREEN_D, (0, 0, TILE, 6))
        pygame.draw.rect(s, BLACK,   (0, 0, TILE, 6), 1)
        pygame.draw.rect(s, BLACK,   (0, 0, TILE - 2, TILE), 1)
    elif kind == PIPE_BL:
        pygame.draw.rect(s, GREEN, (2, 0, TILE - 2, TILE))
        pygame.draw.rect(s, BLACK, (2, 0, TILE - 2, TILE), 1)
        pygame.draw.line(s, GREEN_D, (3, 0), (3, TILE - 1))
    elif kind == PIPE_BR:
        pygame.draw.rect(s, GREEN, (0, 0, TILE - 2, TILE))
        pygame.draw.rect(s, BLACK, (0, 0, TILE - 2, TILE), 1)
        pygame.draw.line(s, GREEN_D, (TILE - 3, 0), (TILE - 3, TILE - 1))
    elif kind == FLAG:
        pygame.draw.rect(s, GRAY, (TILE // 2 - 1, 0, 2, TILE))
    elif kind == FLAG_TOP:
        pygame.draw.rect(s, GRAY, (TILE // 2 - 1, 4, 2, TILE - 4))
        pygame.draw.polygon(s, FLAG_BALL,
                            [(TILE // 2, 0), (TILE - 1, 4), (TILE // 2, 8)])
    elif kind == CASTLE_T:
        pygame.draw.rect(s, CASTLE_C, (0, 0, TILE, TILE))
        pygame.draw.rect(s, CASTLE_D, (0, 0, TILE, TILE), 1)
        pygame.draw.rect(s, CASTLE_D, (4, 4, 8, 8), 1)
    elif kind == LAVA_T:
        pygame.draw.rect(s, LAVA_R, (0, 4, TILE, TILE - 4))
        pygame.draw.rect(s, LAVA_O, (0, 4, TILE, 2))
    elif kind == CLOUD_T:
        pygame.draw.ellipse(s, WHITE, (0, 4, TILE, TILE - 4))
    elif kind == COIN_T:
        pygame.draw.ellipse(s, COIN_C, (TILE // 2 - 3, 3, 6, TILE - 6))
        pygame.draw.ellipse(s, QSHAD,  (TILE // 2 - 3, 3, 6, TILE - 6), 1)
    elif kind == BUSH_T:
        pygame.draw.ellipse(s, GREEN,   (0, 6, TILE, TILE - 6))
        pygame.draw.ellipse(s, GREEN_D, (0, 6, TILE, TILE - 6), 1)
    return s


# ====================================================================
# Level construction (procedural - all 32 stages)
# ====================================================================
def stage_theme(world, stage):
    """Pick a theme for each (world, stage)."""
    # Underground: 1-2, 4-2
    # Castles: x-4
    # Athletic / sky: 1-3, 3-3, 5-3, 6-3
    # Water-ish (rendered as overworld here): 2-2, 7-2
    # Night overworld: 3-1, 6-3, 8-1, 8-2, 8-3 (slight night mood)
    if stage == 4:
        return 'castle'
    if (world, stage) in {(1, 2), (4, 2)}:
        return 'under'
    if stage == 3 and world in (1, 3, 5, 6, 7):
        return 'sky'
    if (world, stage) in {(3, 1), (8, 1), (8, 2), (8, 3)}:
        return 'night'
    return 'over'


def _empty_grid(cols):
    return [[EMPTY for _ in range(cols)] for _ in range(ROWS)]


def _floor(grid, cols, holes=()):
    holes_set = set()
    for h in holes:
        for k in range(h[1]):
            holes_set.add(h[0] + k)
    for c in range(cols):
        if c in holes_set:
            continue
        grid[ROWS - 1][c] = GROUND
        grid[ROWS - 2][c] = GROUND


def _pipe(grid, c, height):
    """Place a 2-wide pipe with given vertical height (>= 2)."""
    height = max(2, height)
    top_row = ROWS - 2 - height
    grid[top_row][c]     = PIPE_TL
    grid[top_row][c + 1] = PIPE_TR
    for r in range(top_row + 1, ROWS - 2):
        grid[r][c]     = PIPE_BL
        grid[r][c + 1] = PIPE_BR


def _qblock_row(grid, c0, row, pattern):
    for i, ch in enumerate(pattern):
        if ch == 'B':
            grid[row][c0 + i] = BRICK_T
        elif ch == '?':
            grid[row][c0 + i] = QBLOCK


def _stairs(grid, c0, height, ascending=True):
    for i in range(height):
        for j in range(i + 1):
            r = ROWS - 3 - j
            c = c0 + i if ascending else c0 + (height - 1 - i)
            grid[r][c] = HARD_T


def _flag_and_castle(grid, cols):
    flag_col = cols - 8
    pole_top = 2
    grid[pole_top][flag_col] = FLAG_TOP
    for r in range(pole_top + 1, ROWS - 2):
        grid[r][flag_col] = FLAG
    cc0 = flag_col + 4
    grid[ROWS - 4][cc0 + 1] = CASTLE_T
    grid[ROWS - 4][cc0 + 2] = CASTLE_T
    for c in range(cc0, cc0 + 4):
        grid[ROWS - 3][c] = CASTLE_T
        grid[ROWS - 2][c] = CASTLE_T
    return flag_col


def _decorate_clouds_bushes(grid, cols, theme, world):
    if theme not in ('over', 'sky', 'night'):
        return
    # Clouds
    for c in range(4, cols - 10, 22 + (world % 3)):
        grid[2][c]     = CLOUD_T
        grid[2][c + 1] = CLOUD_T
        grid[2][c + 2] = CLOUD_T
    # Bushes (only over)
    if theme == 'over':
        for c in range(6, cols - 10, 18):
            grid[ROWS - 3][c]     = BUSH_T
            grid[ROWS - 3][c + 1] = BUSH_T


def _build_overworld_backdrop(cols, world, stage):
    """Generate parallax decoration data for deluxe overworld visuals."""
    hills = []
    bushes = []
    clouds = []
    # Hills: larger, slower parallax layer.
    for c in range(10, cols - 10, 24):
        h = 3 + ((c + world + stage) % 3)  # tile height
        hills.append((c, h))
    # Bush strips: foreground, slight parallax.
    for c in range(6, cols - 8, 18):
        w = 2 + ((c + stage) % 2)
        bushes.append((c, w))
    # Extra high clouds for depth.
    for c in range(4, cols - 8, 22):
        w = 2 + ((c + world) % 2)
        row = 1 + ((c + stage) % 2)
        clouds.append((c, row, w))
    return {'hills': hills, 'bushes': bushes, 'clouds': clouds}


def build_1_1():
    cols = 212
    grid = _empty_grid(cols)
    _floor(grid, cols, holes=[(69, 2), (87, 2), (132, 3)])
    # Iconic block clusters
    grid[10][16] = QBLOCK
    _qblock_row(grid, 20, 10, "B?B?B")
    grid[6][22]  = QBLOCK
    # Pipes (heights 2,3,4,4)
    _pipe(grid, 28, 2)
    _pipe(grid, 38, 3)
    _pipe(grid, 46, 4)
    _pipe(grid, 57, 4)
    # Mid section bricks
    _qblock_row(grid, 77, 10, "BBB?BBB")
    grid[6][80]  = QBLOCK
    _qblock_row(grid, 94, 10, "BB?BB")
    # Stair after second pit
    _stairs(grid, 134, 4, ascending=True)
    _stairs(grid, 140, 4, ascending=False)
    _stairs(grid, 148, 4, ascending=True)
    _stairs(grid, 155, 4, ascending=False)
    _stairs(grid, 181, 4, ascending=True)
    # Final pipe
    _pipe(grid, 163, 2)
    _decorate_clouds_bushes(grid, cols, 'over', 1)
    flag_col = _flag_and_castle(grid, cols)
    enemies = [
        (22, ROWS - 3, 'goomba'),
        (40, ROWS - 3, 'goomba'),
        (50, ROWS - 3, 'goomba'),
        (51, ROWS - 3, 'goomba'),
        (96, ROWS - 3, 'koopa'),
        (105, ROWS - 3, 'goomba'),
        (106, ROWS - 3, 'goomba'),
        (122, ROWS - 3, 'goomba'),
        (123, ROWS - 3, 'goomba'),
    ]
    return {
        'grid': grid, 'cols': cols, 'enemies': enemies,
        'theme': 'over', 'sky': SKY_DAY,
        'flag_col': flag_col, 'mario_start': (32, (ROWS - 3) * TILE),
        'deluxe_bg': _build_overworld_backdrop(cols, 1, 1),
    }


def build_overworld(world, stage, length, seed):
    """Generic overworld stage with pipes, gaps, blocks, goombas, koopas."""
    cols = length
    grid = _empty_grid(cols)
    rng = (seed * 9301 + 49297) % 233280
    holes = []
    # Schedule a few pits
    pit_cols = [60 + (seed * 7 + i * 47) % 30 + i * 45 for i in range(3)]
    for pc in pit_cols:
        if 30 < pc < cols - 30:
            holes.append((pc, 2 + (seed + pc) % 2))
    _floor(grid, cols, holes=holes)
    # Block rows
    for i in range(4 + (stage % 3)):
        c = 18 + i * 28 + (seed + i) % 5
        if c + 6 >= cols - 16:
            break
        pattern = ["B?B?B", "B?BB", "BB?B", "?B?B?"][i % 4]
        _qblock_row(grid, c, 10 - (i % 2), pattern)
        if i % 2 == 0:
            grid[6][c + 2] = QBLOCK
    # Pipes
    for i, h in enumerate([2, 3, 4, 3, 2]):
        c = 26 + i * 30
        if c + 2 >= cols - 16:
            break
        _pipe(grid, c, h)
    # Stairs near end
    _stairs(grid, cols - 26, 4, ascending=True)
    # Decorations
    _decorate_clouds_bushes(grid, cols, 'over', world)
    flag_col = _flag_and_castle(grid, cols)
    # Enemies
    enemies = []
    base_e = 4 + world * 2
    for i in range(base_e):
        c = 22 + i * 18 + (seed + i * 3) % 6
        if c >= cols - 16:
            break
        kind = 'goomba' if (i + world) % 3 != 2 else 'koopa'
        enemies.append((c, ROWS - 3, kind))
    return {
        'grid': grid, 'cols': cols, 'enemies': enemies,
        'theme': 'over', 'sky': SKY_DAY,
        'flag_col': flag_col, 'mario_start': (32, (ROWS - 3) * TILE),
        'deluxe_bg': _build_overworld_backdrop(cols, world, stage),
    }


def build_underground(world, stage, length, seed):
    cols = length
    grid = _empty_grid(cols)
    # Ceiling and floor of brick (BLOCK_U)
    for c in range(cols):
        grid[0][c] = BLOCK_U
        grid[1][c] = BLOCK_U
        grid[ROWS - 1][c] = BLOCK_U
        grid[ROWS - 2][c] = BLOCK_U
    # Side walls at start and end
    for r in range(2, ROWS - 2):
        grid[r][0] = BLOCK_U
        grid[r][cols - 1] = BLOCK_U
    # Brick / coin clusters
    for i in range(8):
        c = 8 + i * 18 + (seed + i) % 4
        if c + 6 >= cols - 6:
            break
        for k in range(5):
            grid[8][c + k] = BRICK_T
        grid[8][c + 2] = QBLOCK
        for k in range(3):
            grid[10][c + 1 + k] = BRICK_T
    # Hanging stalactites of brick
    for i in range(6):
        c = 14 + i * 22 + (seed * 3 + i) % 5
        if c >= cols - 6:
            break
        grid[2][c] = BLOCK_U
        grid[3][c] = BLOCK_U
    flag_col = _flag_and_castle(grid, cols)
    # Erase castle/flag side wall it overlapped
    for r in range(2, ROWS - 2):
        if grid[r][cols - 1] == BLOCK_U:
            grid[r][cols - 1] = BLOCK_U
    enemies = []
    for i in range(3 + world):
        c = 18 + i * 22 + (seed + i * 5) % 5
        if c >= cols - 16:
            break
        enemies.append((c, ROWS - 3, 'goomba'))
    return {
        'grid': grid, 'cols': cols, 'enemies': enemies,
        'theme': 'under', 'sky': SKY_NIGHT,
        'flag_col': flag_col, 'mario_start': (32, (ROWS - 3) * TILE),
    }


def build_sky(world, stage, length, seed):
    cols = length
    grid = _empty_grid(cols)
    # Sparse ground, mostly mushroom platforms
    # Start ground patch
    for c in range(0, 14):
        grid[ROWS - 1][c] = GROUND
        grid[ROWS - 2][c] = GROUND
    # End ground patch
    for c in range(cols - 22, cols):
        grid[ROWS - 1][c] = GROUND
        grid[ROWS - 2][c] = GROUND
    # Mushroom platforms (HARD_T cap on a stalk)
    plats = []
    c = 18
    while c < cols - 26:
        height = 5 + (seed + c) % 5
        width = 4 + (c % 3)
        for k in range(width):
            grid[ROWS - 2 - height][c + k] = HARD_T
        # Stalk
        grid[ROWS - 1 - height][c + width // 2] = BLOCK_U
        plats.append((c, ROWS - 2 - height, width))
        c += width + 5 + (seed + c) % 4
    _decorate_clouds_bushes(grid, cols, 'sky', world)
    flag_col = _flag_and_castle(grid, cols)
    enemies = []
    for (pc, pr, pw) in plats[:6]:
        enemies.append((pc + pw // 2, pr - 1, 'koopa' if (pc + world) % 2 else 'goomba'))
    return {
        'grid': grid, 'cols': cols, 'enemies': enemies,
        'theme': 'sky', 'sky': SKY_DAY,
        'flag_col': flag_col, 'mario_start': (32, (ROWS - 3) * TILE),
    }


def build_castle(world, stage, length, seed):
    cols = length
    grid = _empty_grid(cols)
    # Solid floor of castle brick
    for c in range(cols):
        grid[ROWS - 1][c] = BLOCK_U
        grid[ROWS - 2][c] = BLOCK_U
    # Outer walls
    for r in range(0, ROWS):
        grid[r][0] = BLOCK_U
    for r in range(0, ROWS - 2):
        grid[r][cols - 1] = BLOCK_U
    # Ceiling segments
    for c in range(1, cols - 1):
        grid[0][c] = BLOCK_U
    # Lava pits
    n_pits = 2 + world // 2
    for i in range(n_pits):
        c0 = 30 + i * (cols // (n_pits + 1))
        if c0 + 4 >= cols - 12:
            break
        for k in range(4):
            grid[ROWS - 1][c0 + k] = LAVA_T
            grid[ROWS - 2][c0 + k] = LAVA_T
        # Floating platforms over lava
        grid[ROWS - 5][c0 + 1] = HARD_T
        grid[ROWS - 5][c0 + 2] = HARD_T
    # Bowser-style stair near end
    base = cols - 18
    for i in range(5):
        for j in range(i + 1):
            grid[ROWS - 3 - j][base + i] = BLOCK_U
    # Axe / pole stand-in: a flag-castle tail
    flag_col = _flag_and_castle(grid, cols)
    enemies = []
    for i in range(2 + world):
        c = 16 + i * 14
        if c >= cols - 22:
            break
        enemies.append((c, ROWS - 3, 'koopa' if i % 2 else 'goomba'))
    return {
        'grid': grid, 'cols': cols, 'enemies': enemies,
        'theme': 'castle', 'sky': SKY_NIGHT,
        'flag_col': flag_col, 'mario_start': (32, (ROWS - 3) * TILE),
    }


def build_level(world, stage):
    if (world, stage) == (1, 1):
        return build_1_1()
    theme = stage_theme(world, stage)
    seed = world * 100 + stage
    length = 200 + (world * 6) + (stage * 4)
    if theme == 'under':
        return build_underground(world, stage, length, seed)
    if theme == 'sky':
        return build_sky(world, stage, length, seed)
    if theme == 'castle':
        return build_castle(world, stage, length, seed)
    if theme == 'night':
        lvl = build_overworld(world, stage, length, seed)
        lvl['sky'] = SKY_NIGHT
        lvl['theme'] = 'night'
        return lvl
    return build_overworld(world, stage, length, seed)


# ====================================================================
# Mario
# ====================================================================
class Mario:
    def __init__(self, x, y, sprites):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.w = 12
        self.h = 16
        self.facing_right = True
        self.on_ground = False
        self.holding_jump = False
        self.alive = True
        self.dead_timer = 0
        self.win_timer = 0
        self.on_flag = False
        self.flag_x = 0.0
        self.invincible = 0
        self.sprites = sprites
        self.anim = 0.0
        self.score = 0
        self.coins = 0
        self.lives = 3

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, keys, level):
        if not self.alive:
            self.dead_timer += 1
            self.vy += GRAV_FREE
            if self.vy > MAX_FALL:
                self.vy = MAX_FALL
            self.y += self.vy
            return
        if self.on_flag:
            # Lock Mario to pole X and slide down vertically.
            self.x = self.flag_x - (self.w // 2)
            self.vx = 0
            self.vy = 1.2
            self.y += self.vy
            ground_y = (ROWS - 2) * TILE - self.h
            if self.y >= ground_y:
                self.y = ground_y
                self.on_flag = False
                self.win_timer = max(1, self.win_timer)
            return
        if self.win_timer > 0:
            self.win_timer += 1
            self.vx = 0.6
            self.vy += GRAV_FREE
            if self.vy > MAX_FALL:
                self.vy = MAX_FALL
            self.x += self.vx
            self.y += self.vy
            self._collide(level)
            return

        left  = keys[K_LEFT]  or keys[K_a]
        right = keys[K_RIGHT] or keys[K_d]
        run   = keys[K_LSHIFT] or keys[K_RSHIFT] or keys[K_x]
        jump  = keys[K_SPACE] or keys[K_z] or keys[K_UP] or keys[K_w]

        max_v = RUN_MAX if run else WALK_MAX
        acc   = RUN_ACC if run else WALK_ACC
        if right and not left:
            if self.vx < 0:
                self.vx += SKID_DEC
            else:
                self.vx += acc
            self.facing_right = True
        elif left and not right:
            if self.vx > 0:
                self.vx -= SKID_DEC
            else:
                self.vx -= acc
            self.facing_right = False
        else:
            if self.vx > 0:
                self.vx = max(0.0, self.vx - RELEASE_DEC)
            elif self.vx < 0:
                self.vx = min(0.0, self.vx + RELEASE_DEC)

        if self.vx > max_v:
            self.vx = max_v
        if self.vx < -max_v:
            self.vx = -max_v

        if jump and self.on_ground:
            speed = abs(self.vx)
            self.vy = JUMP_V_HIGH if speed > 1.5 else JUMP_V_LOW
            self.on_ground = False
            self.holding_jump = True
        if not jump:
            self.holding_jump = False

        gravity = GRAV_HOLD if (self.holding_jump and self.vy < 0) else GRAV_FREE
        self.vy += gravity
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        self.x += self.vx
        self._collide_axis(level, axis='x')
        self.y += self.vy
        self.on_ground = False
        self._collide_axis(level, axis='y')

        if self.x < 0:
            self.x = 0
            self.vx = 0
        if self.y > NES_H + 32:
            self.die()

        self.anim += abs(self.vx) * 0.4

    def _solid_at(self, level, c, r):
        grid = level['grid']
        if r < 0 or r >= ROWS:
            return False
        if c < 0 or c >= level['cols']:
            return c < 0
        return grid[r][c] in SOLID

    def _deadly_at(self, level, c, r):
        grid = level['grid']
        if 0 <= r < ROWS and 0 <= c < level['cols']:
            return grid[r][c] in DEADLY
        return False

    def _collide_axis(self, level, axis):
        rect = self.rect
        c0 = max(0, rect.left // TILE)
        c1 = min(level['cols'] - 1, rect.right // TILE)
        r0 = max(0, rect.top // TILE)
        r1 = min(ROWS - 1, rect.bottom // TILE)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if self._deadly_at(level, c, r):
                    if rect.colliderect(pygame.Rect(c * TILE, r * TILE, TILE, TILE)):
                        self.die()
                        return
                if not self._solid_at(level, c, r):
                    continue
                tile_rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                if not rect.colliderect(tile_rect):
                    continue
                if axis == 'x':
                    if self.vx > 0:
                        self.x = tile_rect.left - self.w
                    elif self.vx < 0:
                        self.x = tile_rect.right
                    self.vx = 0
                else:
                    if self.vy > 0:
                        self.y = tile_rect.top - self.h
                        self.vy = 0
                        self.on_ground = True
                    elif self.vy < 0:
                        self.y = tile_rect.bottom
                        self.vy = 0
                        self._head_bump(level, c, r)
                rect = self.rect

    def _collide(self, level):
        self._collide_axis(level, axis='x')
        self._collide_axis(level, axis='y')

    def _head_bump(self, level, c, r):
        t = level['grid'][r][c]
        if t == QBLOCK:
            level['grid'][r][c] = HBLOCK
            level.setdefault('coins_popped', []).append((c, r, 18))
            self.coins += 1
            self.score += 200
        elif t == BRICK_T:
            level['grid'][r][c] = EMPTY
            self.score += 50

    def die(self):
        if not self.alive:
            return
        self.alive = False
        self.vy = -5.0
        self.vx = 0
        self.dead_timer = 0
        self.lives -= 1

    def win(self, flag_col):
        if self.win_timer == 0:
            self.win_timer = 1
            self.on_flag = True
            self.flag_x = flag_col * TILE + TILE // 2
            self.vx = 0
            self.vy = 0
            self.score += 1000

    def draw(self, screen, cam_x):
        if self.win_timer > 0 and (self.win_timer // 4) % 2 == 0:
            spr = self.sprites['mario_jump_r' if self.facing_right else 'mario_jump_l']
        elif not self.on_ground:
            spr = self.sprites['mario_jump_r' if self.facing_right else 'mario_jump_l']
        else:
            spr = self.sprites['mario_r' if self.facing_right else 'mario_l']
        screen.blit(spr, (int(self.x) - cam_x, int(self.y)))


# ====================================================================
# Enemies
# ====================================================================
class Enemy:
    def __init__(self, x, y, kind, sprites):
        self.x = float(x)
        self.y = float(y)
        self.vx = -ENEMY_WALK
        self.vy = 0.0
        self.kind = kind
        self.sprites = sprites
        if kind == 'koopa':
            self.w, self.h = 16, 24
        else:
            self.w, self.h = 16, 16
        self.alive = True
        self.squash_timer = 0
        self.shell = False
        self.shell_moving = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, level):
        if not self.alive:
            return
        if self.squash_timer > 0:
            self.squash_timer -= 1
            if self.squash_timer == 0:
                self.alive = False
            return

        if self.shell and not self.shell_moving:
            # idle shell
            self.vx = 0
        elif self.shell and self.shell_moving:
            pass  # vx already set
        # gravity
        self.vy += GRAV_FREE
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        self.x += self.vx
        self._collide_axis(level, 'x')
        self.y += self.vy
        self._collide_axis(level, 'y')

        # Off bottom
        if self.y > NES_H + 32:
            self.alive = False

    def _solid_at(self, level, c, r):
        if 0 <= r < ROWS and 0 <= c < level['cols']:
            return level['grid'][r][c] in SOLID
        return False

    def _collide_axis(self, level, axis):
        rect = self.rect
        c0 = max(0, rect.left // TILE)
        c1 = min(level['cols'] - 1, rect.right // TILE)
        r0 = max(0, rect.top // TILE)
        r1 = min(ROWS - 1, rect.bottom // TILE)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if not self._solid_at(level, c, r):
                    continue
                tile_rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                if not rect.colliderect(tile_rect):
                    continue
                if axis == 'x':
                    if self.vx > 0:
                        self.x = tile_rect.left - self.w
                    else:
                        self.x = tile_rect.right
                    self.vx = -self.vx
                else:
                    if self.vy > 0:
                        self.y = tile_rect.top - self.h
                        self.vy = 0
                    else:
                        self.y = tile_rect.bottom
                        self.vy = 0
                rect = self.rect

    def stomp(self):
        if self.kind == 'goomba':
            self.squash_timer = 24
            self.vx = 0
        elif self.kind == 'koopa':
            if not self.shell:
                self.shell = True
                self.shell_moving = False
                self.vx = 0
                self.h = 16
                self.y += 8
            else:
                self.shell_moving = not self.shell_moving
                self.vx = SHELL_SPEED if self.shell_moving else 0

    def draw(self, screen, cam_x):
        if not self.alive:
            return
        if self.squash_timer > 0:
            spr = self.sprites['goomba_squashed']
        elif self.kind == 'goomba':
            spr = self.sprites['goomba']
        else:
            spr = self.sprites['koopa']
        screen.blit(spr, (int(self.x) - cam_x, int(self.y)))


# ====================================================================
# Rendering
# ====================================================================
def draw_level(nes_surf, level, tile_imgs, cam_x):
    nes_surf.fill(level['sky'])
    if level.get('theme') in ('over', 'night'):
        _draw_deluxe_overworld_bg(nes_surf, level, cam_x)
    grid = level['grid']
    cols = level['cols']
    c0 = max(0, cam_x // TILE - 1)
    c1 = min(cols, cam_x // TILE + VIS_COLS + 2)
    for r in range(ROWS):
        for c in range(c0, c1):
            t = grid[r][c]
            if t == EMPTY:
                continue
            img = tile_imgs.get(t)
            if img is None:
                continue
            nes_surf.blit(img, (c * TILE - cam_x, r * TILE))
    # Coin pops (animated bumps)
    for cp in level.get('coins_popped', [])[:]:
        c, r, t = cp
        cp_idx = level['coins_popped'].index(cp)
        y_off = -((BUMP_DURATION - t) ** 2) // 4 if t > 0 else 0
        coin_img = tile_imgs[COIN_T]
        nes_surf.blit(coin_img, (c * TILE - cam_x, r * TILE - 12 + y_off))
        level['coins_popped'][cp_idx] = (c, r, t - 1)
    level['coins_popped'] = [cp for cp in level.get('coins_popped', []) if cp[2] > 0]


def _draw_deluxe_overworld_bg(nes_surf, level, cam_x):
    """Parallax hills/clouds for deluxe overworld look."""
    bg = level.get('deluxe_bg')
    if not bg:
        return

    hill_c = (80, 170, 96) if level.get('theme') == 'over' else (40, 90, 52)
    hill_o = (32, 96, 44) if level.get('theme') == 'over' else (18, 44, 26)
    bush_c = (48, 160, 56) if level.get('theme') == 'over' else (20, 72, 32)
    cloud_c = WHITE if level.get('theme') == 'over' else (168, 168, 168)

    # Far hills (slow parallax)
    for c, h in bg.get('hills', []):
        x = c * TILE - int(cam_x * 0.35)
        y = (ROWS - 2 - h) * TILE
        w = 3 * TILE
        pygame.draw.ellipse(nes_surf, hill_c, (x, y, w, h * TILE + 6))
        pygame.draw.ellipse(nes_surf, hill_o, (x, y, w, h * TILE + 6), 1)

    # Mid clouds (medium parallax)
    for c, row, w in bg.get('clouds', []):
        x = c * TILE - int(cam_x * 0.6)
        y = row * TILE + 2
        pygame.draw.ellipse(nes_surf, cloud_c, (x, y, w * TILE, TILE - 4))

    # Near bushes (slightly slower than tiles)
    for c, w in bg.get('bushes', []):
        x = c * TILE - int(cam_x * 0.85)
        y = (ROWS - 3) * TILE + 2
        pygame.draw.ellipse(nes_surf, bush_c, (x, y, w * TILE, TILE - 2))


def draw_hud(nes_surf, font, mario, world, stage, time_left):
    # Draw HUD in fixed columns so TIME digits never clip off-screen.
    score_txt = font.render(f"MARIO {mario.score:06d}", True, WHITE)
    coin_txt = font.render(f"COIN x{mario.coins:02d}", True, WHITE)
    world_txt = font.render(f"WORLD {world}-{stage}", True, WHITE)
    time_txt = font.render(f"TIME {max(0, int(time_left)):03d}", True, WHITE)
    nes_surf.blit(score_txt, (8, 6))
    nes_surf.blit(coin_txt, (8, 18))
    nes_surf.blit(world_txt, (112, 6))
    nes_surf.blit(time_txt, (188, 6))
    if not mario.alive:
        msg = font.render("GAME OVER - press R", True, WHITE)
        nes_surf.blit(msg, (NES_W // 2 - msg.get_width() // 2, NES_H // 2))
    elif mario.win_timer > 0:
        msg = font.render("STAGE CLEAR!", True, WHITE)
        nes_surf.blit(msg, (NES_W // 2 - msg.get_width() // 2, NES_H // 2 - 12))


# ====================================================================
# Game wiring
# ====================================================================
def build_sprites():
    font_q = pygame.font.SysFont("Arial", 12, bold=True)
    sprites = {
        'mario_r': build_mario_small(True),
        'mario_l': build_mario_small(False),
        'mario_jump_r': build_mario_jump(True),
        'mario_jump_l': build_mario_jump(False),
        'goomba': build_goomba(),
        'goomba_squashed': build_goomba_squashed(),
        'koopa': build_koopa(),
    }
    tile_imgs = {}
    for t in (GROUND, BRICK_T, QBLOCK, HBLOCK, HARD_T, BLOCK_U,
              PIPE_TL, PIPE_TR, PIPE_BL, PIPE_BR,
              FLAG, FLAG_TOP, CASTLE_T, LAVA_T, CLOUD_T, COIN_T, BUSH_T):
        tile_imgs[t] = build_block(t, font_q)
    return sprites, tile_imgs


def stage_index_to_world_stage(idx):
    return idx // 4 + 1, idx % 4 + 1


def load_stage(idx, sprites):
    world, stage = stage_index_to_world_stage(idx)
    level = build_level(world, stage)
    level['coins_popped'] = []
    enemies = [Enemy(c * TILE, r * TILE - (24 if k == 'koopa' else 16) + TILE,
                     k, sprites) for (c, r, k) in level['enemies']]
    return level, enemies, world, stage


def main():
    pygame.init()
    pygame.display.set_caption("ac holdings smb1 py port")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    nes_surf = pygame.Surface((NES_W, NES_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier New", 10, bold=True)

    sprites, tile_imgs = build_sprites()

    stage_idx = 0
    level, enemies, world, stage = load_stage(stage_idx, sprites)
    mario = Mario(*level['mario_start'], sprites)
    cam_x = 0
    time_left = 400
    time_tick_frames = 0

    def reset_stage():
        nonlocal level, enemies, mario, cam_x, time_left, time_tick_frames, world, stage
        level, enemies, world, stage = load_stage(stage_idx, sprites)
        mario_score = mario.score
        mario_coins = mario.coins
        mario_lives = mario.lives
        mario = Mario(*level['mario_start'], sprites)
        mario.score = mario_score
        mario.coins = mario_coins
        mario.lives = mario_lives
        cam_x = 0
        time_left = 400
        time_tick_frames = 0

    running = True
    while running:
        # busy_loop gives tighter frame pacing for a steadier 60 Hz update.
        clock.tick_busy_loop(FPS)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_r:
                    reset_stage()
                elif event.key == K_n:
                    stage_idx = (stage_idx + 1) % 32
                    reset_stage()
                elif event.key == K_p:
                    stage_idx = (stage_idx - 1) % 32
                    reset_stage()

        keys = pygame.key.get_pressed()
        mario.update(keys, level)

        # Stage clear when touching flag
        if mario.alive and mario.win_timer == 0:
            fc = level['flag_col']
            if mario.x + mario.w >= fc * TILE - 2:
                mario.win(fc)

        # Advance stage after a small delay
        if mario.win_timer > 60:
            stage_idx = (stage_idx + 1) % 32
            reset_stage()

        # Restart stage if dead long enough
        if not mario.alive and mario.dead_timer > 120:
            if mario.lives <= 0:
                mario.lives = 3
                mario.score = 0
                mario.coins = 0
                stage_idx = 0
            reset_stage()

        # Update enemies
        for e in enemies:
            e.update(level)
        # Mario vs enemies
        if mario.alive and mario.win_timer == 0:
            for e in enemies:
                if not e.alive or e.squash_timer > 0:
                    continue
                if mario.rect.colliderect(e.rect):
                    if mario.vy > 0 and (mario.y + mario.h - e.y) < 10:
                        e.stomp()
                        mario.vy = JUMP_V_LOW * 0.6
                        mario.score += 100
                    elif e.shell and not e.shell_moving:
                        e.shell_moving = True
                        e.vx = SHELL_SPEED if mario.x < e.x else -SHELL_SPEED
                        mario.score += 100
                    else:
                        mario.die()
                        break

        # Camera follows Mario forward only (NES style)
        target = int(mario.x) - NES_W // 3
        if target > cam_x:
            cam_x = target
        cam_x = max(0, min(cam_x, level['cols'] * TILE - NES_W))

        # NES-like TIME countdown (integer ticks, pauses during death/clear).
        if mario.alive and mario.win_timer == 0:
            time_tick_frames += 1
            if time_tick_frames >= 24:
                time_tick_frames = 0
                time_left = max(0, time_left - 1)
        if time_left <= 0 and mario.alive:
            mario.die()

        # Draw to NES surface, then upscale
        draw_level(nes_surf, level, tile_imgs, cam_x)
        for e in enemies:
            e.draw(nes_surf, cam_x)
        mario.draw(nes_surf, cam_x)
        draw_hud(nes_surf, font, mario, world, stage, time_left)
        pygame.transform.scale(nes_surf, (SCREEN_W, SCREEN_H), screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
