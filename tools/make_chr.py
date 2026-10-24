#!/usr/bin/env python3
"""Build chr.bin (8 KB of NES tile graphics) from the PICO-8 sprite sheet of bomb.p8.

Pattern table 0 ($0000) holds background tiles:
  0        HUD/blank tile (all colour 3)
  1..41    font (see FONT below), white on colour 3
  $40-$7F  the cart's map tiles, sprite-sheet rows 4-7, at the same index as in PICO-8
Pattern table 1 ($1000) holds sprites:
  $00-$2F  the bomber frames (sheet rows 0-2)
  $4E,$4F,$5E,$5F  the creature ("Krax") monster

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
}
FONT_ORDER = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:!-.>"


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

spr = [bytes(16)] * 256
for t in list(range(0x00, 0x0E)) + list(range(0x10, 0x1E)) + list(range(0x20, 0x2E)):
    spr[t] = encode(mapped(t, HERO, 1))
for t in (0x4E, 0x4F, 0x5E, 0x5F):
    spr[t] = encode(mapped(t, KRAX, 1))

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
