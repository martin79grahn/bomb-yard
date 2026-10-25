#!/usr/bin/env python3
"""Build chr.bin (8 KB of NES tile graphics) from the PICO-8 sprite sheet of bomb.p8.

Pattern table 0 ($0000) holds background tiles:
  0        HUD/blank tile (all colour 3)
  1..42    font (see FONT below), white on colour 3
  $2C,$2D,$3C,$3D  the extra-life heart (16 x 16, item palette: 1 outline, 2 shine, 3 fill)
  $40-$7F  the cart's map tiles, sprite-sheet rows 4-7, at the same index as in PICO-8
  $80-$9F  explosion pieces, 16 x 16 each (flame palette: 1 red edge, 2 orange, 3 yellow core):
           centre $80, across $82, up-down $84, ends rounded to the left $86, right $88,
           up $8A, down $8C, and a lone ball $8E
  $A0,$A1,$B0,$B1  the penetrator bomb power-up: a bomb pierced by an arrow (item palette)
Pattern table 1 ($1000) holds sprites:
  $00-$2F  the bomber frames (sheet rows 0-2)
  $30,$31  confetti specks
  $4E,$4F,$5E,$5F  the creature ("Krax") monster
  $6E,$6F,$7E,$7F  the Deep Sea's fish (Krax palette: 1 outline, 2 white stripes, 3 orange)
  $80-$85,$90-$95  the shark boss, 24 x 16 facing left, two tail frames side by side
                   (boss palette: 1 outline, 2 grey back, 3 white belly)

Each PICO-8 colour is mapped to one of the NES's 4 palette slots per tile group,
because every NES tile can only use 3 colours plus transparent/background.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
gfx = open(os.path.join(HERE, "pico_gfx.txt")).read().strip()


def pico_tile(n):
    """8x8 list of PICO-8 colour indices for sheet tile n."""
    tx, ty = n % 16, n // 16
    return [[int(gfx[(ty * 8 + y) * 128 + tx * 8 + x], 16) for x in range(8)] for y in range(8)]


def encode(pixels):
    """8x8 grid of 0..3 -> 16 bytes of NES 2bpp planar data."""
    lo, hi = [], []
    for row in pixels:
        a = b = 0
        for x, v in enumerate(row):
            a |= (v & 1) << (7 - x)
            b |= ((v >> 1) & 1) << (7 - x)
        lo.append(a); hi.append(b)
    return bytes(lo + hi)


def mapped(n, cmap, default):
    return [[cmap.get(c, default) for c in row] for row in pico_tile(n)]


# PICO-8 colour -> NES palette slot, per group
GRASS = {11: 0, 3: 1}
BLOCK = {7: 1, 6: 2, 13: 2, 5: 3, 0: 3}
FLAME = {12: 0, 8: 1, 0: 1, 2: 1, 9: 2, 10: 3, 7: 3, 15: 3}
ITEM  = {12: 0, 0: 1, 1: 1, 5: 1, 13: 1, 2: 1, 7: 2, 6: 2, 15: 2, 8: 3, 9: 3, 10: 3, 14: 3, 4: 3}
HERO  = {12: 0, 0: 1, 1: 1, 5: 1, 13: 1, 2: 1, 3: 1, 7: 2, 6: 2, 15: 2, 8: 3, 9: 3, 10: 3, 14: 3, 4: 3, 11: 3}
KRAX  = {14: 0, 12: 0, 0: 1, 1: 1, 5: 1, 13: 1, 2: 1, 7: 2, 6: 2, 15: 2, 8: 3, 9: 3, 10: 3, 4: 3}

BG_GROUPS = {}
for t in (0x44, 0x45, 0x54, 0x55): BG_GROUPS[t] = (GRASS, 1)
for t in (0x40, 0x41, 0x50, 0x51, 0x42, 0x43, 0x52, 0x53): BG_GROUPS[t] = (BLOCK, 2)
for t in (0x48, 0x49, 0x58, 0x59): BG_GROUPS[t] = (FLAME, 0)
for t in (0x46, 0x47, 0x56, 0x57, 0x4A, 0x4B, 0x5A, 0x5B, 0x4C, 0x4D, 0x5C, 0x5D, 0x60, 0x61, 0x70, 0x71):
    BG_GROUPS[t] = (ITEM, 0)

# 5x7 font, '#' = ink. Order defines tile numbers 1..
FONT = {
 '0': [" ### ","#   #","#  ##","# # #","##  #","#   #"," ### "],
 '1': ["  #  "," ##  ","  #  ","  #  ","  #  ","  #  "," ### "],
 '2': [" ### ","#   #","    #","  ## "," #   ","#    ","#####"],
 '3': ["#### ","    #","    #"," ### ","    #","    #","#### "],
 '4': ["   # ","  ## "," # # ","#  # ","#####","   # ","   # "],
 '5': ["#####","#    ","#### ","    #","    #","#   #"," ### "],
 '6': [" ### ","#    ","#    ","#### ","#   #","#   #"," ### "],
 '7': ["#####","    #","   # ","  #  "," #   "," #   "," #   "],
 '8': [" ### ","#   #","#   #"," ### ","#   #","#   #"," ### "],
 '9': [" ### ","#   #","#   #"," ####","    #","    #"," ### "],
 'A': [" ### ","#   #","#   #","#####","#   #","#   #","#   #"],
 'B': ["#### ","#   #","#   #","#### ","#   #","#   #","#### "],
 'C': [" ### ","#   #","#    ","#    ","#    ","#   #"," ### "],
 'D': ["#### ","#   #","#   #","#   #","#   #","#   #","#### "],
 'E': ["#####","#    ","#    ","#### ","#    ","#    ","#####"],
 'F': ["#####","#    ","#    ","#### ","#    ","#    ","#    "],
 'G': [" ### ","#   #","#    ","# ###","#   #","#   #"," ####"],
 'H': ["#   #","#   #","#   #","#####","#   #","#   #","#   #"],
 'I': [" ### ","  #  ","  #  ","  #  ","  #  ","  #  "," ### "],
 'J': ["  ###","   # ","   # ","   # ","   # ","#  # "," ##  "],
 'K': ["#   #","#  # ","# #  ","##   ","# #  ","#  # ","#   #"],
 'L': ["#    ","#    ","#    ","#    ","#    ","#    ","#####"],
 'M': ["#   #","## ##","# # #","# # #","#   #","#   #","#   #"],
 'N': ["#   #","##  #","# # #","#  ##","#   #","#   #","#   #"],
 'O': [" ### ","#   #","#   #","#   #","#   #","#   #"," ### "],
 'P': ["#### ","#   #","#   #","#### ","#    ","#    ","#    "],
 'Q': [" ### ","#   #","#   #","#   #","# # #","#  # "," ## #"],
 'R': ["#### ","#   #","#   #","#### ","# #  ","#  # ","#   #"],
 'S': [" ####","#    ","#    "," ### ","    #","    #","#### "],
 'T': ["#####","  #  ","  #  ","  #  ","  #  ","  #  ","  #  "],
 'U': ["#   #","#   #","#   #","#   #","#   #","#   #"," ### "],
 'V': ["#   #","#   #","#   #","#   #","#   #"," # # ","  #  "],
 'W': ["#   #","#   #","#   #","# # #","# # #","## ##","#   #"],
 'X': ["#   #","#   #"," # # ","  #  "," # # ","#   #","#   #"],
 'Y': ["#   #","#   #"," # # ","  #  ","  #  ","  #  ","  #  "],
 'Z': ["#####","    #","   # ","  #  "," #   ","#    ","#####"],
 ':': ["     ","  #  ","  #  ","     ","  #  ","  #  ","     "],
 '!': ["  #  ","  #  ","  #  ","  #  ","  #  ","     ","  #  "],
 '-': ["     ","     ","     "," ### ","     ","     ","     "],
 '.': ["     ","     ","     ","     ","     "," ##  "," ##  "],
 '>': [" #   ","  #  ","   # ","    #","   # ","  #  "," #   "],
 '/': ["    #","   # ","   # ","  #  "," #   "," #   ","#    "],
}
FONT_ORDER = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:!-.>/"


def font_tile(rows):
    px = [[3] * 8 for _ in range(8)]
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == '#':
                px[y][x + 1] = 1
    return px


bg = [encode([[3] * 8 for _ in range(8)])] + [bytes(16)] * 255
for i, ch in enumerate(FONT_ORDER):
    bg[1 + i] = encode(font_tile(FONT[ch]))
for t, (cmap, default) in BG_GROUPS.items():
    bg[t] = encode(mapped(t, cmap, default))

# the extra-life heart, drawn from the heart curve: fill, a dark outline and a shine
def heart_pixels():
    px = [[0] * 16 for _ in range(16)]
    inside = lambda x, y: (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0
    for y in range(16):
        for x in range(16):
            if inside((x - 7.5) / 6.2, (8.0 - y) / 6.2):
                px[y][x] = 3
    for y in range(16):
        for x in range(16):
            if px[y][x] == 3 and any(not (0 <= x + dx < 16 and 0 <= y + dy < 16) or px[y + dy][x + dx] == 0
                                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[y][x] = 1
    for x, y in ((4, 4), (5, 4), (4, 5), (4, 6), (5, 5)):
        px[y][x] = 2
    return px


heart = heart_pixels()
for i, t in enumerate((0x2C, 0x2D, 0x3C, 0x3D)):
    ox, oy = (i & 1) * 8, (i >> 1) * 8
    bg[t] = encode([row[ox:ox + 8] for row in heart[oy:oy + 8]])

# the penetrator bomb: a dark bomb with a shine and fuse, an arrow driven right through it
def penetrator_pixels():
    px = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if (x - 7.0) ** 2 + (y - 9.0) ** 2 <= 5.6 ** 2:
                px[y][x] = 1
    for x, y in ((5, 6), (4, 7), (5, 7), (4, 8)):
        px[y][x] = 2
    for x, y in ((9, 3), (10, 2), (11, 1)):          # fuse
        px[y][x] = 2
    px[0][12] = 3; px[1][12] = 3
    for x in range(0, 12):                           # the shaft
        px[9][x] = 3
    for x, h in ((11, 3), (12, 2), (13, 2), (14, 1), (15, 0)):   # the head
        for y in range(9 - h, 10 + h):
            px[y][x] = 3
    for y in (7, 11):                                # fletching
        px[y][0] = 2; px[y][1] = 2
    px[8][1] = 2; px[10][1] = 2
    return px


pen = penetrator_pixels()
for i, t in enumerate((0xA0, 0xA1, 0xB0, 0xB1)):
    ox, oy = (i & 1) * 8, (i >> 1) * 8
    bg[t] = encode([row[ox:ox + 8] for row in pen[oy:oy + 8]])

# explosion pieces: a beam with a red edge, orange body and yellow core, rounded at the ends
def flame_piece(left, right, up, down):
    """16x16 pixels for a flame cell joined to its neighbours on the given sides."""
    px = [[0] * 16 for _ in range(16)]
    c = 7.5
    for y in range(16):
        for x in range(16):
            # distance to the nearest point of the beam's centre line
            best = ((x - c) ** 2 + (y - c) ** 2) ** 0.5           # the middle
            if left and x <= c:
                best = min(best, abs(y - c))
            if right and x >= c:
                best = min(best, abs(y - c))
            if up and y <= c:
                best = min(best, abs(x - c))
            if down and y >= c:
                best = min(best, abs(x - c))
            r = 6.6 if (left or right or up or down) else 6.2
            if best <= r * 0.42:
                px[y][x] = 3
            elif best <= r * 0.72:
                px[y][x] = 2
            elif best <= r:
                px[y][x] = 1
    return px


PIECES = [(1, 1, 1, 1), (1, 1, 0, 0), (0, 0, 1, 1), (0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0), (0, 0, 0, 0)]
for k, sides in enumerate(PIECES):
    piece = flame_piece(*sides)
    base = 0x80 + k * 2
    for i, t in enumerate((base, base + 1, base + 16, base + 17)):
        ox, oy = (i & 1) * 8, (i >> 1) * 8
        bg[t] = encode([row[ox:ox + 8] for row in piece[oy:oy + 8]])

spr = [bytes(16)] * 256
for t in list(range(0x00, 0x0E)) + list(range(0x10, 0x1E)) + list(range(0x20, 0x2E)):
    spr[t] = encode(mapped(t, HERO, 1))
for t in (0x4E, 0x4F, 0x5E, 0x5F):
    spr[t] = encode(mapped(t, KRAX, 1))
# confetti for the victory screens: a 3 x 3 speck in colour 2 ($30) or colour 3 ($31)
for t, v in ((0x30, 2), (0x31, 3)):
    spr[t] = encode([[v if x < 3 and y < 3 else 0 for x in range(8)] for y in range(8)])

# the Deep Sea's fish: an orange body with two white bands, a fan tail, facing left
def fish_pixels():
    px = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            inside = ((x - 6.8) / 6.0) ** 2 + ((y - 8.0) / 4.4) ** 2 <= 1
            tail = 11 <= x <= 15 and abs(y - 8.0) <= (x - 10.5) * 1.1 and abs(y - 8.0) <= 5
            if inside or tail:
                px[y][x] = 3
    for y in range(16):
        for x in range(16):
            if px[y][x] == 3 and (x in (4, 5) or x in (9, 10)) and 3 < y < 13:
                px[y][x] = 2
    for x in range(16):                               # outline
        for y in range(16):
            if px[y][x] and any(not (0 <= x + dx < 16 and 0 <= y + dy < 16) or not px[y + dy][x + dx]
                                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[y][x] = 1
    px[7][2] = 1; px[7][3] = 1                        # eye
    px[10][1] = 1                                     # mouth
    return px


def shark_pixels(frame):
    """24 x 16, facing left: grey back, white belly, a dorsal fin, teeth, and a tail that swings."""
    px = [[0] * 24 for _ in range(16)]
    sw = 1 if frame else 0
    for y in range(16):
        for x in range(24):
            body = ((x - 10.0) / 9.6) ** 2 + ((y - 9.5) / 4.6) ** 2 <= 1
            fin = 8 <= x <= 13 and y >= 2 + (13 - x) * 0.0 and y >= 1 + abs(x - 10.5) * 1.4 and y <= 6
            tail = 17 <= x <= 23 and (abs(y - (5.5 - sw)) <= (x - 17) * 0.55 + 0.3 and y < 9.5 - sw * 0.5 or
                                      abs(y - (13.0 + sw)) <= (x - 17) * 0.35 + 0.3 and y > 9.5)
            pec = 8 <= x <= 12 and 12 <= y <= 15 and y - 12 <= (12 - x) * 0.9 + 1
            stalk = 15 <= x <= 19 and abs(y - 9.3) <= 1.6     # where the tail joins
            if body or fin or tail or pec or stalk:
                px[y][x] = 2
    for y in range(16):
        for x in range(24):
            if px[y][x] == 2 and y >= 10 and x <= 16 and ((x - 10.0) / 9.6) ** 2 + ((y - 9.5) / 4.6) ** 2 <= 1:
                px[y][x] = 3
    for x in range(24):
        for y in range(16):
            if px[y][x] and any(not (0 <= x + dx < 24 and 0 <= y + dy < 16) or not px[y + dy][x + dx]
                                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[y][x] = 1
    px[8][4] = 1; px[8][5] = 1                        # eye
    for x in (2, 4, 6):                               # teeth
        px[11][x] = 3
    for x in range(1, 8):
        px[12][x] = 1                                 # the mouth line
    for y in (8, 9):                                  # gills
        px[y][11] = 1
    return px


fish = fish_pixels()
for i, t in enumerate((0x6E, 0x6F, 0x7E, 0x7F)):
    ox, oy = (i & 1) * 8, (i >> 1) * 8
    spr[t] = encode([row[ox:ox + 8] for row in fish[oy:oy + 8]])
for frame in range(2):
    shark = shark_pixels(frame)
    for ty in range(2):
        for tx in range(3):
            spr[0x80 + ty * 16 + frame * 3 + tx] = encode([row[tx * 8:tx * 8 + 8] for row in shark[ty * 8:ty * 8 + 8]])

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "chr.bin")
open(out, "wb").write(b"".join(bg) + b"".join(spr))

# font map for the C code: char -> tile number
with open(os.path.join(HERE, "..", "font.h"), "w") as f:
    f.write("/* generated by tools/make_chr.py: ASCII -> font tile */\n")
    f.write("static const unsigned char FONT_MAP[96] = {\n")
    m = []
    for c in range(32, 128):
        ch = chr(c).upper()
        m.append(1 + FONT_ORDER.index(ch) if ch in FONT_ORDER else 0)
    for i in range(0, 96, 16):
        f.write("  " + ",".join("%d" % v for v in m[i:i + 16]) + ",\n")
    f.write("};\n")
print("wrote", out)
