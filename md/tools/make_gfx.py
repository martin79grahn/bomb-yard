#!/usr/bin/env python3
"""Draw every Mega Drive graphic for Bomb Yard and write src/gen/gfx.c and gfx.h.

Nothing is loaded from image files: each picture is drawn here pixel by pixel, lit from the
top left, with a dark outline, in the colours of the palette lines below.

Palette lines (index 0 is see-through in every line):
  PAL0 arena and HUD: 1 outline, 2-4 floor (dark, mid, light), 5-7 wall block, 8-10 stone
       block, 11 floor in shadow, 12 panel (also the backdrop), 13 panel edge, 14 white,
       15 yellow. One set of colours per level; the tiles stay the same.
  PAL1 bombs, flames, power-ups, logo: 1 outline, 2-4 bomb, 5 white, 6 fuse, 7-11 fire from
       deep red to pale yellow, 12-13 bubble blue, 14 pink, 15 green.
  PAL2 player 1 and the Krax.  PAL3 player 2, or the boss.
       1 outline, 2-4 suit, 5 visor, 6 visor glint, 7-8 gloves and trim, 9-10 boots,
       11-13 Krax feathers, 14 beak and feet, 15 eye white.

Usage: make_gfx.py OUTDIR [preview.png]
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "src/gen"
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
HERE = os.path.dirname(os.path.abspath(__file__))


def md(rgb):
    """RGB 0-255 to a Mega Drive colour word (3 bits per channel)."""
    q = [min(7, int(round(v / 255 * 7))) for v in rgb]
    return (q[2] << 9) | (q[1] << 5) | (q[0] << 1)


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# ---------------------------------------------------------------- palettes
PANEL, PANEL_EDGE = "#141a33", "#2c3a66"
ARENA = {   # floor dark/mid/light, wall dark/mid/light, stone dark/mid/light, floor shadow
    "yard":  ["#2e7a2a", "#48a83a", "#7ed456", "#565e70", "#9aa2b4", "#dfe3ec", "#6e3412", "#b8642a", "#eca456", "#20561c"],
    "sand":  ["#a8803e", "#d4ae64", "#f4dc9c", "#80582c", "#c09254", "#eecb8a", "#702818", "#ac4426", "#e07a46", "#806030"],
    "frost": ["#4a7cb0", "#86bce6", "#d2eefc", "#3e5c86", "#86aad2", "#e8f6ff", "#5a7aa6", "#a8cbea", "#ffffff", "#3a6694"],
    "boss":  ["#3c2a56", "#584078", "#7e64a4", "#3a3448", "#6c6680", "#aaa6be", "#5a1e2a", "#8e3040", "#c65c62", "#2a1c40"],
}


def pal0(theme):
    a = ARENA[theme]
    return [PANEL, "#0c0e16"] + a[0:9] + [a[9], PANEL, PANEL_EDGE, "#f4f4f4", "#ffe14d"]


PAL1 = ["#000000", "#100c14", "#1c2238", "#3a4466", "#8090bc", "#ffffff", "#a8743c",
        "#8a1010", "#e02a1a", "#ff8a1a", "#ffd02a", "#fff6b8", "#1a48b0", "#4aa6ff", "#ff7aa8", "#2ab04a"]
KRAX = ["#1e1e2a", "#3e3e58", "#6e6e92", "#ff9a1a", "#ffffff"]
SUITS = {   # suit shade/mid/light, visor, glint, trim dark/light, boots dark/light
    "p1":    ["#8890b0", "#c8cee2", "#ffffff", "#182040", "#5ad8ff", "#1e54d0", "#4a90ff", "#4a2a18", "#8a5a30"],
    "p2":    ["#902030", "#d83a4a", "#ff9090", "#182040", "#5ad8ff", "#b08a10", "#ffd84a", "#4a2a18", "#8a5a30"],
    "sky":   ["#1c4aa8", "#3a8ae8", "#9ad2ff", "#101830", "#ffe04a", "#b08a10", "#ffd84a", "#2a2a3a", "#5a5a72"],
    "nova":  ["#a86a10", "#e8b028", "#fff08a", "#2a1440", "#ff7ad0", "#5a28a8", "#9a62ff", "#3a2014", "#6a4428"],
    "boss":  ["#3e2478", "#7048c8", "#a888ff", "#140c24", "#ff5a5a", "#a87a10", "#ffd84a", "#241430", "#4a2c5a"],
    "angry": ["#801440", "#cc2c62", "#ff7aa0", "#140c24", "#ffe04a", "#a87a10", "#ffd84a", "#241430", "#4a2c5a"],
}


def sprite_pal(suit):
    return ["#000000", "#100c14"] + SUITS[suit] + KRAX


PALETTES = {
    "arena": [[md(hexrgb(c)) for c in pal0(t)] for t in ("yard", "sand", "frost", "boss")],
    "items": [md(hexrgb(c)) for c in PAL1],
    # the four characters (Bit, Ruby, Sky, Nova), then the boss and the angry boss
    "sprites": [[md(hexrgb(c)) for c in sprite_pal(s)] for s in ("p1", "p2", "sky", "nova", "boss", "angry")],
}

# ---------------------------------------------------------------- canvas helpers
class Pic:
    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.p = [[fill] * w for _ in range(h)]

    def get(self, x, y):
        return self.p[y][x] if 0 <= x < self.w and 0 <= y < self.h else 0

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = c

    def outline(self, c=1, diag=False):
        new = [row[:] for row in self.p]
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (-1, 1), (1, -1), (-1, -1)] if diag else [])
        for y in range(self.h):
            for x in range(self.w):
                if self.p[y][x] == 0 and any(self.get(x + dx, y + dy) not in (0, c) for dx, dy in nb):
                    new[y][x] = c
        self.p = new

    def hflip(self):
        q = Pic(self.w, self.h)
        q.p = [row[::-1] for row in self.p]
        return q


L = (-0.48, -0.58, 0.66)
_n = math.sqrt(sum(v * v for v in L))
L = tuple(v / _n for v in L)


def sphere_light(x, y, cx, cy, r):
    nx, ny = (x - cx) / r, (y - cy) / r
    nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
    return nx * L[0] + ny * L[1] + nz * L[2]


def band(v, cols, cuts):
    """cols dark..light, cuts ascending thresholds (len(cols) - 1)."""
    for c, t in zip(cols, cuts):
        if v < t:
            return c
    return cols[-1]


def fill_sphere(pic, cx, cy, r, cols, cuts=(0.42, 0.78), ry=None, spec=None):
    ry = ry or r
    for y in range(pic.h):
        for x in range(pic.w):
            px, py = x + 0.5, y + 0.5
            if ((px - cx) / r) ** 2 + ((py - cy) / ry) ** 2 <= 1:
                v = sphere_light(px, cy + (py - cy) * r / ry, cx, cy, r)
                pic.set(x, y, band(v, cols, cuts))
                if spec is not None and v > 0.95:
                    pic.set(x, y, spec)


def in_rrect(px, py, x0, y0, x1, y1, rad):
    if not (x0 <= px <= x1 and y0 <= py <= y1):
        return False
    cx = min(max(px, x0 + rad), x1 - rad)
    cy = min(max(py, y0 + rad), y1 - rad)
    return (px - cx) ** 2 + (py - cy) ** 2 <= rad * rad


# ---------------------------------------------------------------- tiles
tiles = []          # list of 8x8 index grids
tile_ids = {}       # dedupe for background tiles


def add_tile(grid, dedupe=True):
    key = tuple(tuple(r) for r in grid)
    if dedupe and key in tile_ids:
        return tile_ids[key]
    tiles.append([list(r) for r in grid])
    tile_ids.setdefault(key, len(tiles) - 1)
    return len(tiles) - 1


def cut(pic, x0, y0):
    return [[pic.get(x0 + x, y0 + y) for x in range(8)] for y in range(8)]


def add_cell(pic, dedupe=True):
    """A 16x16 background cell: 4 tiles TL, TR, BL, BR."""
    return [add_tile(cut(pic, ox, oy), dedupe) for oy in (0, 8) for ox in (0, 8)]


def add_sprite(pic):
    """A sprite of w x h tiles, column-major as the VDP wants. Returns the first tile."""
    first = len(tiles)
    for tx in range(pic.w // 8):
        for ty in range(pic.h // 8):
            tiles.append(cut(pic, tx * 8, ty * 8))
    return first


consts = {}
arrays = {}      # name -> list of ints (u16)

# ---------------------------------------------------------------- arena cells (PAL0)
add_tile([[0] * 8 for _ in range(8)])       # tile 0: see-through


def floor_cell(seed, shadow_top, shadow_left):
    rnd = random.Random(seed)
    p = Pic(16, 16, 3)
    for _ in range(9):          # light blades
        x, y = rnd.randrange(1, 15), rnd.randrange(2, 15)
        p.set(x, y, 4); p.set(x, y - 1, 4)
        if rnd.random() < 0.5:
            p.set(x + 1, y - 1, 4)
    for _ in range(7):          # dark specks and blade roots
        x, y = rnd.randrange(0, 16), rnd.randrange(0, 16)
        p.set(x, y, 2)
    for y in range(16):
        for x in range(16):
            sh = (shadow_top and (y < 4 or (y == 4 and x % 2 == 0))) or \
                 (shadow_left and (x < 3 or (x == 3 and y % 2 == 0)))
            if sh:
                p.set(x, y, 11 if p.get(x, y) != 2 else 1)
    return p


FLOOR = []      # [texture][shadow] -> 4 tiles; shadow bit 0 top, bit 1 left
for tex in range(2):
    FLOOR.append([add_cell(floor_cell(17 + tex * 101, s & 1, s & 2)) for s in range(4)])


def wall_cell():
    p = Pic(16, 16, 6)
    for y in range(16):
        for x in range(16):
            if y < 2 or x < 2:
                p.set(x, y, 7)
            if y > 13 or x > 13:
                p.set(x, y, 5)
    p.set(0, 15, 6); p.set(15, 0, 6); p.set(1, 14, 6); p.set(14, 1, 6)
    for y in range(4, 12):      # an inset panel
        for x in range(4, 12):
            if y == 4 or x == 4:
                p.set(x, y, 5)
            elif y == 11 or x == 11:
                p.set(x, y, 7)
    for x, y in ((6, 7), (9, 9), (7, 10)):
        p.set(x, y, 5)
    for i in range(16):
        p.set(i, 15, 1); p.set(15, i, 1)
    return p


def stone_cell():
    p = Pic(16, 16, 9)
    for row in range(4):
        y0 = row * 4
        off = 0 if row % 2 == 0 else 4
        for y in range(y0, y0 + 4):
            for x in range(16):
                bx = (x + off) % 8
                if y == y0 + 3 or bx == 7:
                    p.set(x, y, 8)          # mortar
                elif y == y0 or bx == 0:
                    p.set(x, y, 10)         # lit edge of the brick
    for i in range(16):
        p.set(i, 15, 1); p.set(15, i, 1)
    for i in range(15):
        p.set(i, 0, 10); p.set(0, i, 10)
    return p


arrays["WALL_T"] = add_cell(wall_cell())
arrays["STONE_T"] = add_cell(stone_cell())
arrays["FLOOR_T"] = [t for tex in FLOOR for s in tex for t in s]

# ---------------------------------------------------------------- bombs (PAL1, plane A)
def bomb_pic(spark, flash):
    p = Pic(16, 16)
    body = (7, 8, 11) if flash else (2, 3, 4)
    fill_sphere(p, 7.5, 9.3, 6.2, body, spec=5)
    for x in range(6, 10):
        for y in range(2, 4):
            p.set(x, y, 3 if not flash else 8)
    for x, y in ((9, 1), (10, 1), (11, 0)):
        p.set(x, y, 6)
    if spark == 0:
        for x, y in ((12, 0), (12, 1), (11, 1)):
            p.set(x, y, 10)
        p.set(12, 0, 11)
    else:
        for x, y in ((12, 0), (13, 1), (11, 0), (12, 1), (13, 0)):
            p.set(x, y, 9)
        p.set(12, 0, 5)
    p.outline()
    return p


consts["T_BOMB"] = add_cell(bomb_pic(0, False), False)[0]
add_cell(bomb_pic(1, False), False)
add_cell(bomb_pic(0, True), False)
add_cell(bomb_pic(1, True), False)


# ---------------------------------------------------------------- flames (PAL1, plane A)
def flame_pic(sides, size, phase):
    """A blast piece joined to the flames on the given sides (bit 0 left, 1 right, 2 up, 3 down),
    rounded where the beam ends. size 0 is full, 1 is dying down."""
    rnd = random.Random(phase * 977 + sides * 31 + size * 7)
    noise = [[rnd.random() for _ in range(16)] for _ in range(16)]
    p = Pic(16, 16)
    c = 7.5
    r = (7.4 if sides else 6.8) if size == 0 else (5.0 if sides else 4.6)
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5 - 0.5, y + 0.5 - 0.5
            d = math.hypot(px - c, py - c)
            if sides & 1 and px <= c: d = min(d, abs(py - c))
            if sides & 2 and px >= c: d = min(d, abs(py - c))
            if sides & 4 and py <= c: d = min(d, abs(px - c))
            if sides & 8 and py >= c: d = min(d, abs(px - c))
            d += (noise[y][x] - 0.5) * 1.1      # a ragged, flickering edge
            f = d / r
            if f <= 0.22: col = 11
            elif f <= 0.45: col = 10
            elif f <= 0.68: col = 9
            elif f <= 0.88: col = 8
            elif f <= 1.0: col = 7
            else: col = 0
            p.set(x, y, col)
    return p


consts["T_FLAME"] = len(tiles)      # [size][phase][sides] -> 4 tiles each
for size in range(2):
    for phase in range(2):
        for sides in range(16):
            add_cell(flame_pic(sides, size, phase), False)


# ---------------------------------------------------------------- power-ups (PAL1, plane A)
def bubble():
    p = Pic(16, 16)
    for y in range(16):
        for x in range(16):
            if in_rrect(x + 0.5, y + 0.5, 1, 1, 15, 15, 4):
                p.set(x, y, 13 if (x + y) < 14 else 12)
    for x, y in ((3, 3), (4, 3), (3, 4), (5, 2), (2, 5)):
        p.set(x, y, 5)
    return p


def item_bomb():
    p = bubble()
    fill_sphere(p, 7.5, 9.0, 3.8, (1, 2, 3), cuts=(0.3, 0.75))
    p.set(6, 7, 5)
    for x, y in ((9, 5), (10, 4), (11, 3)):
        p.set(x, y, 6)
    p.set(11, 2, 10); p.set(12, 3, 9); p.set(12, 2, 11)
    p.outline()
    return p


def item_fire():
    p = bubble()
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            # a teardrop flame: circle at the bottom, point at the top
            dy = py - 9.5
            w = 4.0 * math.sqrt(max(0, 1 - (dy / 4.0) ** 2)) if dy >= 0 else 4.0 * (1 + dy / 7.5)
            if py < 2.5 or py > 13.6:
                continue
            dx = abs(px - 7.8 - (0 if dy >= 0 else -dy * 0.12))
            if dx <= w:
                f = dx / max(w, 0.1)
                core = dy > -1 and f < 0.45
                p.set(x, y, 11 if core and dy > 1 else 10 if f < 0.55 else 9 if f < 0.85 else 8)
    p.outline()
    return p


def item_skate():
    p = bubble()
    # a running shoe: red upper, white sole, speed lines
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            if in_rrect(px, py, 5, 4.5, 9, 10.5, 1.5) or in_rrect(px, py, 5, 8, 13, 11.5, 1.8):
                p.set(x, y, 8 if py > 6.5 and px > 7 else 14 if px < 7 else 8)
            if 11.5 <= py <= 12.8 and 4.5 <= px <= 13.5:
                p.set(x, y, 5)
    for x in range(1, 4):
        p.set(x, 7, 5); p.set(x + 1, 10, 5)
    p.set(9, 8, 5); p.set(10, 9, 5)
    p.outline()
    return p


def heart_pic():
    p = Pic(16, 16)
    for y in range(16):
        for x in range(16):
            px, py = (x + 0.5 - 8) / 6.6, (y + 0.5 - 8.4) / 6.6
            # classic heart curve
            v = (px * px + py * py - 0.55) ** 3 - px * px * (-py) ** 3 * 1.2
            if v <= 0:
                lit = sphere_light(x + 0.5, y + 0.5, 8, 7, 7)
                p.set(x, y, 7 if lit < 0.25 else 8 if lit < 0.7 else 14)
    for x, y in ((4, 4), (5, 4), (4, 5)):
        p.set(x, y, 5)
    p.outline()
    return p


consts["T_ITEM_SHOE"] = add_cell(item_skate(), False)[0]
consts["T_ITEM_FIRE"] = add_cell(item_fire(), False)[0]
consts["T_ITEM_BOMB"] = add_cell(item_bomb(), False)[0]
consts["T_ITEM_LIFE"] = add_cell(heart_pic(), False)[0]


# ---------------------------------------------------------------- font and boxes (PAL0)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
FONT = {}
src = open(os.path.join(HERE, "..", "..", "tools", "make_chr.py")).read()
start = src.index("FONT = {")
end = src.index("}", start)
exec(src[start:end + 1], {}, FONT_NS := {})
FONT = FONT_NS["FONT"]
FONT[" "] = ["     "] * 7
EXTRA = {
    "'": ["  #  ", "  #  ", "     ", "     ", "     ", "     ", "     "],
    ",": ["     ", "     ", "     ", "     ", "     ", "  #  ", " #   "],
    "?": [" ### ", "#   #", "    #", "  ## ", "  #  ", "     ", "  #  "],
    "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    "x": ["     ", "     ", "#   #", " # # ", "  #  ", " # # ", "#   #"],
}
FONT.update(EXTRA)
FONT_ORDER = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:!-.>/',?+x"


def glyph_tile(ch, ink):
    g = FONT[ch]
    t = [[12] * 8 for _ in range(8)]
    on = set()
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c == "#":
                on.add((x + 1, y)); on.add((x + 2, y))     # one pixel bolder
    for (x, y) in on:
        if (x + 1, y + 1) not in on and x + 1 < 8 and y + 1 < 8:
            t[y + 1][x + 1] = 1
    for (x, y) in on:
        if x < 8:
            t[y][x] = ink
    return t


consts["T_FONT"] = len(tiles)
for ch in FONT_ORDER:
    tiles.append(glyph_tile(ch, 14))
consts["T_FONT_Y"] = len(tiles)
for ch in FONT_ORDER:
    tiles.append(glyph_tile(ch, 15))
font_map = [0] * 96
for i, ch in enumerate(FONT_ORDER):
    font_map[ord(ch) - 32] = i
for ch in "abcdefghijklmnopqrstuvwyz":
    font_map[ord(ch) - 32] = FONT_ORDER.index(ch.upper())
arrays["FONT_MAP"] = font_map


def box_tile(kind):
    """9-slice message box: kind is (top, bottom, left, right) edge flags."""
    top, bottom, left, right = kind
    t = [[12] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            e = []
            if top: e.append(y)
            if bottom: e.append(7 - y)
            if left: e.append(x)
            if right: e.append(7 - x)
            d = min(e) if e else 9
            corner = (top or bottom) and (left or right)
            if corner:
                yy = y if top else 7 - y
                xx = x if left else 7 - x
                if xx + yy < 2:
                    t[y][x] = 0
                    continue
                if xx + yy == 2:
                    d = 0
                elif xx + yy == 3:
                    d = min(d, 1)
            t[y][x] = 1 if d == 0 else 13 if d == 1 else 12
    return t


consts["T_BOX"] = len(tiles)    # TL T TR L C R BL B BR
for tb in ((1, 0), (0, 0), (0, 1)):
    for lr in ((1, 0), (0, 0), (0, 1)):
        tiles.append(box_tile((tb[0], tb[1], lr[0], lr[1])))
# HUD panel edge (a vertical line on the arena side) and the top band's underline
consts["T_PANEL_L"] = add_tile([[12] * 6 + [13, 1] for _ in range(8)], False)
consts["T_PANEL_R"] = add_tile([[1, 13] + [12] * 6 for _ in range(8)], False)


# ---------------------------------------------------------------- characters (sprites)
def bomber(direction, frame, boss=False):
    """16x24 bomber. direction 0 down, 1 up, 2 left. frame 0 stand, 1 and 2 steps."""
    p = Pic(16, 24)
    lift = 1 if frame else 0
    step = (0, 1, -1)[frame]
    hy = 8.6 - lift
    # hand behind the body (side view)
    def hand(x, y):
        fill_sphere(p, x, y, 1.9, (7, 7, 8), cuts=(0.3, 0.55))
    def foot(x, y, rx=2.7):
        fill_sphere(p, x, y, rx, (9, 9, 10), cuts=(0.3, 0.6), ry=1.7)
    if direction == 2:
        foot(9.8 - step * 1.6, 21.9)
        hand(11.2, 16.6 - step - lift)
    # feet
    if direction != 2:
        foot(4.9, 21.9 - (1.2 if frame == 1 else 0))
        foot(10.6, 21.9 - (1.2 if frame == 2 else 0))
    # body: a short rounded barrel
    bx0, bx1 = (3.4, 12.6) if direction != 2 else (4.4, 11.6)
    for y in range(24):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            if in_rrect(px, py, bx0, 13.6 - lift, bx1, 20.6 - lift, 2.6):
                cx = (bx0 + bx1) / 2
                nx = (px - cx) / ((bx1 - bx0) / 2 + 0.4)
                v = nx * L[0] + math.sqrt(max(0, 1 - nx * nx)) * L[2] - 0.08 * (py - 14)
                p.set(x, y, band(v, (2, 3, 4), (0.32, 0.66)))
                if abs(py - (17.6 - lift)) < 0.8:
                    p.set(x, y, 7 if v < 0.5 else 8)       # belt
    if direction == 2:
        foot(5.6 + step * 1.6, 21.9)
    # head
    fill_sphere(p, 7.5, hy, 6.7, (2, 3, 4), cuts=(0.36, 0.74), spec=4)
    # knob on top
    fill_sphere(p, 7.5, hy - 7.0, 1.7, (7, 8, 8), cuts=(0.3, 0.6))
    # visor and eyes
    if direction != 1:
        vx0, vx1 = (2.6, 12.4) if direction == 0 else (0.9, 8.8)
        for y in range(24):
            for x in range(16):
                px, py = x + 0.5, y + 0.5
                if in_rrect(px, py, vx0, hy - 2.6, vx1, hy + 3.0, 2.4):
                    p.set(x, y, 5)
        eyes = (5.4, 9.6) if direction == 0 else (3.4,)
        for ex in eyes:
            for y in range(24):
                for x in range(16):
                    px, py = x + 0.5, y + 0.5
                    if ((px - ex) / 1.05) ** 2 + ((py - hy - 0.2) / 1.7) ** 2 <= 1:
                        p.set(x, y, 4)
            if boss:   # angry brows: cut the inner top corner of each eye
                inner = 1 if ex < 7.5 else -1
                p.set(int(ex + inner * 0.6), int(hy - 1.4), 5)
                p.set(int(ex), int(hy - 1.6), 5)
        gx = int(vx0) + 1
        p.set(gx, int(hy - 2), 6); p.set(gx + 1, int(hy - 2), 6); p.set(gx, int(hy - 1), 6)
    else:
        for x in range(5, 11):
            p.set(x, int(hy + 3), 2)
    if boss:   # horns
        for side in (-1, 1):
            if direction == 2 and side == 1:
                continue
            base = 7.5 + side * 5.0
            for i in range(5):
                x = base + side * (i * 0.55)
                y = hy - 4.5 - i * 1.0
                p.set(int(x), int(y), 8 if i < 3 else 7)
                p.set(int(x - side), int(y), 7 if i < 3 else 0)
    # hands in front
    if direction == 2:
        hand(4.4, 16.8 + step - lift)
    else:
        swing = (0, 1, -1)[frame]
        hand(2.3, 16.4 - lift + swing)
        hand(12.7, 16.4 - lift - swing)
    p.outline()
    return p


def krax(frame):
    """16x16 Krax facing left: a round dark bird with a big eye and an orange beak."""
    p = Pic(16, 16)
    bob = 1 if frame else 0
    for fx, lift in ((6.5, frame == 1), (10.5, frame == 2)):
        y = 15 - (1 if lift else 0)
        p.set(int(fx), y, 14); p.set(int(fx) - 1, y, 14); p.set(int(fx), y - 1, 14)
    fill_sphere(p, 8.6, 9.2 - bob, 6.2, (11, 12, 13), cuts=(0.35, 0.75), ry=5.6)
    # wing
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            if ((px - 10.8) / 3.0) ** 2 + ((py - 10.4 + bob) / 2.2) ** 2 <= 1 and p.get(x, y):
                p.set(x, y, 11)
    # tuft
    p.set(9, 2 - bob, 12); p.set(10, 2 - bob, 11); p.set(10, 1 - bob, 12)
    # eye
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            if (px - 5.6) ** 2 + (py - 7.6 + bob) ** 2 <= 2.4 ** 2:
                p.set(x, y, 15)
    p.set(4, 7 - bob, 1); p.set(4, 8 - bob, 1)
    p.set(4, 5 - bob, 1); p.set(5, 5 - bob, 1); p.set(6, 4 - bob, 1)   # angry brow
    # beak
    for y in range(16):
        for x in range(16):
            px, py = x + 0.5, y + 0.5
            if 0.6 <= px <= 4.0 and abs(py - (10.2 - bob)) <= (px - 0.6) * 0.45 + 0.2:
                p.set(x, y, 14)
    p.outline()
    return p


consts["S_BOMBER"] = len(tiles)        # [direction][frame] 2x3 sprites, 6 tiles each
for d in range(3):
    for f in range(3):
        add_sprite(bomber(d, f))
consts["S_BOSS"] = len(tiles)
for d in range(3):
    for f in range(3):
        add_sprite(bomber(d, f, boss=True))
consts["S_KRAX"] = len(tiles)          # 3 frames, 2x2 sprites
for f in range(3):
    add_sprite(krax(f))
# confetti specks (PAL1 colours, 1x1 sprites)
consts["S_CONFETTI"] = len(tiles)
for c in (8, 9, 10, 13, 14, 15):
    t = [[0] * 8 for _ in range(8)]
    for y in range(2, 5):
        for x in range(2, 5):
            t[y][x] = c
    tiles.append(t)


# ---------------------------------------------------------------- title logo (PAL1)
def logo():
    font = ImageFont.truetype("/usr/share/fonts/google-noto/NotoSans-ExtraCondensedBlack.ttf", 46)
    text = "BOMB YARD"
    W, H = 288, 64
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    bb = d.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    ox, oy = (W - tw) // 2 - bb[0], (H - th) // 2 - bb[1] - 2
    d.text((ox, oy), text, font=font, fill=255)
    m = mask.load()
    p = Pic(W, H)
    top, bot = oy + bb[1], oy + bb[3]
    for y in range(H):
        for x in range(W):
            if m[x, y] > 110:
                f = (y - top) / max(1, bot - top)
                p.set(x, y, 11 if f < 0.18 else 10 if f < 0.45 else 9 if f < 0.75 else 8)
    # thick outline and a drop shadow
    p.outline(1, diag=True)
    p.outline(1)
    sh = Pic(W, H)
    for y in range(H):
        for x in range(W):
            if p.get(x, y):
                sh.set(x + 3, y + 3, 7)
    for y in range(H):
        for x in range(W):
            if not p.get(x, y) and sh.get(x, y):
                p.set(x, y, 7 if sh.get(x, y) else 0)
    return p


lg = logo()
consts["LOGO_W"], consts["LOGO_H"] = lg.w // 8, lg.h // 8
logo_map = []
for ty in range(lg.h // 8):
    for tx in range(lg.w // 8):
        logo_map.append(add_tile(cut(lg, tx * 8, ty * 8)))
arrays["LOGO_MAP"] = logo_map
consts["NTILES"] = len(tiles)


# ---------------------------------------------------------------- write C
def encode(t):
    out = []
    for row in t:
        v = 0
        for c in row:
            v = (v << 4) | (c & 15)
        out.append(v)
    return out


os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "gfx.h"), "w") as f:
    f.write("/* generated by tools/make_gfx.py */\n#pragma once\n#include <genesis.h>\n\n")
    for k, v in consts.items():
        f.write(f"#define {k} {v}\n")
    f.write("\nextern const u32 GFX_TILES[];\n")
    f.write("extern const u16 PAL_ARENA[4][16];\nextern const u16 PAL_ITEMS[16];\nextern const u16 PAL_SPRITES[6][16];\n")
    for k, v in arrays.items():
        f.write(f"extern const u16 {k}[{len(v)}];\n")
with open(os.path.join(OUT, "gfx.c"), "w") as f:
    f.write('/* generated by tools/make_gfx.py */\n#include "gfx.h"\n\n')
    f.write("const u32 GFX_TILES[] = {\n")
    for t in tiles:
        f.write("  " + ",".join(f"0x{v:08X}" for v in encode(t)) + ",\n")
    f.write("};\n")

    def arr(name, vals):
        return f"const u16 {name} = {{" + ",".join(f"0x{v:04X}" for v in vals) + "};\n"
    f.write("const u16 PAL_ARENA[4][16] = {\n" + ",\n".join("  {" + ",".join(f"0x{v:04X}" for v in p) + "}" for p in PALETTES["arena"]) + "\n};\n")
    f.write(arr("PAL_ITEMS[16]", PALETTES["items"]))
    f.write("const u16 PAL_SPRITES[6][16] = {\n" + ",\n".join("  {" + ",".join(f"0x{v:04X}" for v in p) + "}" for p in PALETTES["sprites"]) + "\n};\n")
    for k, v in arrays.items():
        f.write(f"const u16 {k}[{len(v)}] = {{" + ",".join(str(x) for x in v) + "};\n")
print(f"gfx: {len(tiles)} tiles")


# ---------------------------------------------------------------- preview
if PREVIEW:
    def rgbs(pal_hex):
        return [hexrgb(c) for c in pal_hex]
    P0, P1 = rgbs(pal0("yard")), rgbs(PAL1)
    SP = rgbs(sprite_pal("p1"))

    def draw_pic(img, pic, ox, oy, pal, s=3, bg=None):
        for y in range(pic.h):
            for x in range(pic.w):
                c = pic.p[y][x]
                if c or bg is not None:
                    col = pal[c] if c else bg
                    for yy in range(s):
                        for xx in range(s):
                            img.putpixel((ox + x * s + xx, oy + y * s + yy), col)
    img = Image.new("RGB", (900, 640), (40, 40, 40))
    s = 3
    x = 10
    fl = floor_cell(17, 0, 0)
    for i, pic in enumerate([floor_cell(17, 0, 0), floor_cell(118, 1, 0), floor_cell(17, 1, 2), wall_cell(), stone_cell()]):
        draw_pic(img, pic, 10 + i * 54, 10, P0, s)
    for i, pic in enumerate([bomb_pic(0, False), bomb_pic(1, True), item_bomb(), item_fire(), item_skate(), heart_pic()]):
        draw_pic(img, fl, 10 + i * 54, 70, P0, s)
        draw_pic(img, pic, 10 + i * 54, 70, P1, s)
    row = [3, 2, 1, 2, 3]   # a blast row: end-left, across, centre... masks
    masks = [2, 3, 15, 3, 1]
    for i, mk in enumerate(masks):
        draw_pic(img, fl, 10 + i * 48, 130, P0, s)
        draw_pic(img, flame_pic(mk, 0, 0), 10 + i * 48, 130, P1, s)
    for i, mk in enumerate([2, 3, 15, 3, 1]):
        draw_pic(img, fl, 280 + i * 48, 130, P0, s)
        draw_pic(img, flame_pic(mk, 1, 1), 280 + i * 48, 130, P1, s)
    for d in range(3):
        for f in range(3):
            draw_pic(img, bomber(d, f), 10 + (d * 3 + f) * 54, 190, SP, s, bg=P0[3])
    BP = rgbs(sprite_pal("boss"))
    for d in range(3):
        draw_pic(img, bomber(d, 0, True), 10 + d * 54, 270, BP, s, bg=P0[3])
    draw_pic(img, bomber(0, 0, True), 180, 270, rgbs(sprite_pal("angry")), s, bg=P0[3])
    draw_pic(img, bomber(0, 1), 240, 270, rgbs(sprite_pal("p2")), s, bg=P0[3])
    for f in range(3):
        draw_pic(img, krax(f), 320 + f * 54, 270, SP, s, bg=P0[3])
    draw_pic(img, lg, 10, 360, P1, 2, bg=P0[3])
    ts = [glyph_tile(ch, 14) for ch in "LEVEL 1 BOSS 2:59"]
    for i, t in enumerate(ts):
        pic = Pic(8, 8); pic.p = t
        draw_pic(img, pic, 10 + i * 24, 500, P0, 3)
    img.save(PREVIEW)
