#!/usr/bin/env python3
"""Write the Mega Drive pages of the manual (manual/project/MegaDrive*.dc.html).

The pictures are the game's own pixel art from make_gfx.py, drawn as inline SVG so the
pages need no image files.

Usage: manual_pages.py MANUAL_PROJECT_DIR
"""
import os
import runpy
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "manual", "project")

# run make_gfx.py for its drawing functions, writing its C files somewhere harmless
argv = sys.argv
sys.argv = ["make_gfx.py", tempfile.mkdtemp()]
G = runpy.run_path(os.path.join(HERE, "make_gfx.py"))
sys.argv = argv
Pic, hexrgb = G["Pic"], G["hexrgb"]


def svg(layers, w, h, scale, label):
    """layers: [(Pic, palette as #hex list, dx, dy)] drawn in order, colour 0 see-through."""
    px = {}
    for pic, pal, dx, dy in layers:
        for y in range(pic.h):
            for x in range(pic.w):
                c = pic.p[y][x]
                if c and 0 <= x + dx < w and 0 <= y + dy < h:
                    px[(x + dx, y + dy)] = pal[c]
    rects = []
    for y in range(h):
        x = 0
        while x < w:
            col = px.get((x, y))
            if col is None:
                x += 1
                continue
            x0 = x
            while x < w and px.get((x, y)) == col:
                x += 1
            rects.append(f'<rect x="{x0}" y="{y}" width="{x - x0}" height="1" fill="{col}"></rect>')
    return (f'<svg role="img" aria-label="{label}" viewBox="0 0 {w} {h}" width="{w * scale}" height="{h * scale}" '
            f'shape-rendering="crispEdges" style="display: block; flex-shrink: 0">' + "".join(rects) + "</svg>")


P0 = G["pal0"]("yard")
P1 = G["PAL1"]
SP = {k: G["sprite_pal"](k) for k in ("p1", "boss", "angry")}

# ---------- an arena corner with a blast going off ----------
W, H = 7, 5
WALL, FLOOR, STONE = "W", "F", "S"
grid = ["WWWWWWW",
        "WFFSFFW",
        "WFWFWFW",
        "WFFFFFW",
        "WWWWWWW"]
flames = {(1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (3, 2)}
layers = []
for cy in range(H):
    for cx in range(W):
        k = grid[cy][cx]
        if k == WALL:
            pic = G["wall_cell"]()
        elif k == STONE:
            pic = G["stone_cell"]()
        else:
            top = cy > 0 and grid[cy - 1][cx] != FLOOR
            left = cx > 0 and grid[cy][cx - 1] != FLOOR
            pic = G["floor_cell"](17 + ((cx * 7 + cy * 3) >> 1 & 1) * 101, top, left)
        layers.append((pic, P0, cx * 16, cy * 16))
for (cx, cy) in flames:
    sides = (1 if (cx - 1, cy) in flames else 0) | (2 if (cx + 1, cy) in flames else 0) | \
            (4 if (cx, cy - 1) in flames else 0) | (8 if (cx, cy + 1) in flames else 0)
    layers.append((G["flame_pic"](sides, 0, 0), P1, cx * 16, cy * 16))
layers.append((G["bomb_pic"](0, False), P1, 5 * 16, 2 * 16))
layers.append((G["item_fire"](), P1, 4 * 16, 1 * 16))
layers.append((G["item_skate"](), P1, 2 * 16, 1 * 16))
layers.append((G["bomber"](0, 0), SP["p1"], 1 * 16, 1 * 16 - 8))
layers.append((G["krax"](0).hflip(), SP["p1"], 5 * 16, 1 * 16))
ARENA_SVG = svg(layers, W * 16, H * 16, 2, "A corner of the Yard: Bit, a Krax, a bomb, two power-ups and a blast")


def char(pic, pal, label, scale=3):
    return svg([(pic, pal, 0, 0)], pic.w, pic.h, scale, label)


BOSS_SVG = char(G["bomber"](0, 0, boss=True), SP["boss"], "The boss")
ANGRY_SVG = char(G["bomber"](0, 0, boss=True), SP["angry"], "The boss after two hits")

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&amp;family=Archivo:wght@400;600;800&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#A01800}}a:hover{{color:#6E1000}}
</style>
</helmet>
<div style="width: 480px; height: 680px; box-sizing: border-box; background-color: #F3EEDF; color: #141414; font-family: 'Archivo', sans-serif; display: flex; flex-direction: column">
  <div style="background-color: #141414; padding: 18px 28px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 6px solid #D82800">
    <h2 style="margin: 0; font-family: 'Press Start 2P', monospace; font-size: 16px; color: #FCFCFC">{heading}</h2>
    <span style="font-family: 'Press Start 2P', monospace; font-size: 9px; color: #BCBCBC">{tag}</span>
  </div>
"""
FOOT = """
  <div style="padding: 12px 28px 16px; display: flex; justify-content: space-between; align-items: center; font-family: 'Press Start 2P', monospace; font-size: 9px; color: #6E6A60">
    <span>BOMB YARD</span>
    <span>{page}</span>
  </div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":480,"height":680}}}}'>
class Component extends DCLogic {{
  renderVals() {{
    return {{}};
  }}
}}
</script>
</body>
</html>
"""
LABEL = "font-family: 'Press Start 2P', monospace; font-size: 10px"
H3 = "margin: 2px 0 0; font-family: 'Press Start 2P', monospace; font-size: 12px; color: #A01800"


def feature(title, text):
    return f"""      <div style="display: flex; flex-direction: column; gap: 4px">
        <span style="{LABEL}">{title}</span>
        <span style="font-size: 13px; line-height: 1.4">{text}</span>
      </div>
"""


page10 = HEAD.format(title="The Mega Drive version", heading="MEGA DRIVE", tag="16-BIT") + f"""
  <div style="flex: 1; padding: 16px 28px 0; display: flex; flex-direction: column; gap: 12px">
    <p style="margin: 0; font-size: 14px; line-height: 1.45">Bomb Yard is on the Sega Mega Drive too, with the same rules as on the NES. Everything you see and hear is new.</p>

    <div style="align-self: center; border: 3px solid #141414">
      {ARENA_SVG}
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px; border: 3px solid #141414; background-color: #FCFCFC; padding: 12px 14px">
{feature("GRAPHICS", "Shaded pixel art. Blocks cast shadows, fire flickers and bombs flash red before they blow. Each level has its own colours.")}{feature("MUSIC", "The NES tunes rearranged for the FM synth, plus new title and boss songs.")}{feature("SOUND", "Sampled effects: deep explosions, a sparkle for the heart, a clang for the boss.")}    </div>

    <p style="margin: 0; font-size: 12px; line-height: 1.4; color: #4A463E">The ROM is md/bomb-yard.bin and runs in any Mega Drive emulator. Player 2 uses controller 2.</p>
  </div>
""" + FOOT.format(page=10)

ROW = "display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 10px; align-items: center; padding: 5px 0; border-bottom: 2px solid #D8D0BC"
KEY = "font-family: 'Press Start 2P', monospace; font-size: 9px; background-color: #141414; color: #FCFCFC; padding: 6px 6px; text-align: center"


def control(key, what):
    return f"""      <div style="{ROW}">
        <span style="{KEY}">{key}</span>
        <span style="font-size: 13px; line-height: 1.3">{what}</span>
      </div>
"""


page11 = HEAD.format(title="Mega Drive controls and the boss", heading="MD CONTROLS", tag="3-BUTTON PAD") + f"""
  <div style="flex: 1; padding: 14px 28px 0; display: flex; flex-direction: column; gap: 10px">
    <div style="display: flex; flex-direction: column">
{control("D-PAD", "Walk. In the menus: choose")}{control("A B C", "Drop a bomb (any of the three)")}{control("START", "Start, pause and play on")}{control("B", "Options screen: go back")}{control("C", "Title screen: debug mode, walk through walls")}    </div>

    <h3 style="{H3}">THE SCREEN</h3>
    <p style="margin: 0; font-size: 13px; line-height: 1.4">Left panel: your bombs, blast range, skates and lives. Right panel: Krax left, the boss's hits to go, or player 2. Top: the level and the clock, which turns yellow in the last 20 seconds while the music speeds up.</p>

    <h3 style="{H3}">THE BOSS</h3>
    <div style="display: flex; gap: 14px; align-items: center">
      {BOSS_SVG}
      {ANGRY_SVG}
      <span style="font-size: 13px; line-height: 1.4">Waits between levels 1 and 2. Drops 2 bombs at a time with a blast of 5. Three hits beat it; after two it turns red, runs faster and drops 3 bombs. Its own bombs can't hurt it, only yours can.</span>
    </div>
  </div>
""" + FOOT.format(page=11)

with open(os.path.join(OUT, "MegaDrive.dc.html"), "w") as f:
    f.write(page10)
with open(os.path.join(OUT, "MegaDrivePlay.dc.html"), "w") as f:
    f.write(page11)
print("pages:", len(page10) // 1024, "KB,", len(page11) // 1024, "KB")
