#!/usr/bin/env python3
"""Build manual/bomb-yard-manual.pdf, the whole manual in one file.

The page sources in manual/project/ show their pictures from /_blob/ uploads, which live only in
the Claude artifact. This script draws every one of them again from the games themselves, into
manual/images/<blob id>.png, puts them into the pages as data: URIs (data-img keeps the id),
then renders each page in headless Firefox and joins the pages into a PDF:

  - sprites and tiles straight from chr.bin, in NES colours
  - NES screenshots from bomb-yard.nes, played in the cynes emulator (RAM from labels.txt)
  - web screenshots from web/bomb-yard.html in Firefox

Needs Python 3 with Pillow and cynes, and Firefox. Build the NES ROM first (./build.sh writes
labels.txt). Usage: python3 manual/tools/build.py [--images-only | --pdf-only]
"""
import base64, io, json, os, re, shutil, subprocess, sys, tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MANUAL = os.path.dirname(HERE)
ROOT = os.path.dirname(MANUAL)
IMAGES = os.path.join(MANUAL, "images")
PROJECT = os.path.join(MANUAL, "project")
TMP = tempfile.mkdtemp(prefix="bomb-yard-manual-")

# the NES palette (2C02, as most emulators show it)
NES = [0x7C7C7C, 0x0000FC, 0x0000BC, 0x4428BC, 0x940084, 0xA80020, 0xA81000, 0x881400, 0x503000, 0x007800,
       0x006800, 0x005800, 0x004058, 0x000000, 0x000000, 0x000000, 0xBCBCBC, 0x0078F8, 0x0058F8, 0x6844FC,
       0xD800CC, 0xE40058, 0xF83800, 0xE45C10, 0xAC7C00, 0x00B800, 0x00A800, 0x00A844, 0x008888, 0x000000,
       0x000000, 0x000000, 0xF8F8F8, 0x3CBCFC, 0x6888FC, 0x9878F8, 0xF878F8, 0xF85898, 0xF87858, 0xFCA044,
       0xF8B800, 0xB8F818, 0x58D854, 0x58F898, 0x00E8D8, 0x787878, 0x000000, 0x000000, 0xFCFCFC, 0xA4E4FC,
       0xB8B8F8, 0xD8B8F8, 0xF8B8F8, 0xF8A4C0, 0xF0D0B0, 0xFCE0A8, 0xF8D878, 0xD8F878, 0xB8F8B8, 0xB8F8D8,
       0x00FCFC, 0xF8D8F8, 0x000000, 0x000000]
CHR = open(os.path.join(ROOT, "chr.bin"), "rb").read()


def save(blob, im):
    im.save(os.path.join(IMAGES, blob + ".png"))


# ---------------------------------------------------------------- tiles from chr.bin
def tiles(first, tw, th, pal, sprites):
    """tw x th tiles from the pattern table (sprites: the second one), colour 0 see-through"""
    base = 0x1000 if sprites else 0
    im = Image.new("RGBA", (tw * 8, th * 8))
    for ty in range(th):
        for tx in range(tw):
            off = base + (first + ty * 16 + tx) * 16
            b = CHR[off:off + 16]
            for y in range(8):
                for x in range(8):
                    v = ((b[y] >> (7 - x)) & 1) | (((b[y + 8] >> (7 - x)) & 1) << 1)
                    if v:
                        c = NES[pal[v - 1]]
                        im.putpixel((tx * 8 + x, ty * 8 + y), (c >> 16, (c >> 8) & 255, c & 255, 255))
    return im


def sprite_images():
    ITEM = (0x0F, 0x30, 0x27)
    save("40675b1174f0ee5956862208332665b9", tiles(0x00, 2, 3, (0x0F, 0x30, 0x16), True))   # Bit
    save("5a5d70b6ea68bbc2d1db1ddd715a8f2d", tiles(0x00, 2, 3, (0x0F, 0x16, 0x36), True))   # Red, player 2
    save("996c7940da557b621dc01c3e7e42d218", tiles(0x4E, 2, 2, ITEM, True))                 # a Krax
    save("b91ec3bc0a1135cd8d67c165a8c11379", tiles(0x46, 2, 2, ITEM, False))                # bomb
    save("04de7ddf57e4a6efde50649de32768c2", tiles(0x4C, 2, 2, ITEM, False))                # bomb-up
    save("1555d9933a3d8cae21d15165d696da88", tiles(0x4A, 2, 2, ITEM, False))                # skate
    save("9ea2bd8c3c4a14a17c7e4ac3cea3d89a", tiles(0x60, 2, 2, ITEM, False))                # fire-up
    save("58a2f6aa45209d3c4468c693692927b1", tiles(0x42, 2, 2, (0x30, 0x10, 0x00), False))  # stone
    save("c1c945bd8bc6b9a8834c5b5a84a852df", tiles(0x40, 2, 2, (0x30, 0x10, 0x00), False))  # concrete
    save("5ea9cb2aa1de4045381e34d2f1251424", tiles(0x8E, 2, 2, (0x16, 0x27, 0x38), False))  # fire


# ---------------------------------------------------------------- NES screenshots
def nes_images():
    from cynes import NES as Emu
    lab = {m.group(2): int(m.group(1), 16)
           for m in re.finditer(r"al 00([0-9A-F]{4}) \._(\w+)", open(os.path.join(ROOT, "labels.txt")).read())}
    R, L, D, U, ST, SE, B, A = 1, 2, 4, 8, 16, 32, 64, 128

    def run(n, k, p=0):
        n.controller = p
        f = None
        for _ in range(k):
            f = n.step()
        return f

    def tap(n, b):
        run(n, 2, b)
        return run(n, 4)

    def shot(blob, frame):
        save(blob, Image.fromarray(frame.copy()))

    def clear(n):          # beat the monsters or the boss on this stage, and wait for the next one
        if n[lab["boss"]]:
            n[lab["palive"] + 1] = 0; n[lab["pdeath"] + 1] = 0
        else:
            n[lab["malive"]] = 0; n[lab["malive"] + 1] = 0

    n = Emu(os.path.join(ROOT, "bomb-yard.nes"))
    shot("f1ef4b4140813ee3ff78a1c2ca6d1aab", run(n, 90))                  # the title screen
    tap(n, ST); tap(n, ST)
    shot("cca673c931be55a8031ec3c922e8a1a2", run(n, 140))                 # level 1
    run(n, 12, R); run(n, 10); tap(n, A); run(n, 18, L); run(n, 4, D)
    shot("edd9cf3267fb88a7ed148296a9a61bde", run(n, 60))                  # Bit drops a bomb
    n[lab["debug"]] = 1
    run(n, 150)
    clear(n)
    shot("0b233afb33588241136468e7ccd37b38", run(n, 40))                  # LEVEL CLEARED
    blobs = {2: "a0676ed0adc260681991f2b4e2bd93d6", 3: "2052f91c219d1454ceeb68f77501bddc"}
    for stage in range(13):          # through every level and boss; message screens move on by themselves
        run(n, 400)
        lv = n[lab["level"]] + 1
        if not n[lab["boss"]] and lv in blobs:
            shot(blobs.pop(lv), run(n, 1))
        n[lab["debug"]] = 1
        final = n[lab["boss"]] and n[lab["fin"]]
        if n[lab["boss"]] and n[lab["level"]] + 2 in blobs:
            n[lab["debug"]] = 0       # so the next level's picture has no DEBUG on it
        clear(n)
        if final:
            break
    shot("6c948c5a0902a8b394bbf9468674c009", run(n, 140))                 # CONGRATULATIONS!

    n = Emu(os.path.join(ROOT, "bomb-yard.nes"))                         # 2 players
    run(n, 60); tap(n, D); tap(n, ST)
    n[lab["opt_wins"]] = 1                                                # first to 5
    run(n, 10); tap(n, R); tap(n, L)                                      # redraw the options
    shot("f69348c221398a62ba398cc6b4329d33", run(n, 30))
    tap(n, ST)
    shot("b472909a02eb76e8e11269696702ad94", run(n, 220))


# ---------------------------------------------------------------- web screenshots
def firefox(html, w, h, out):
    prof = os.path.join(TMP, "ff")
    os.makedirs(prof, exist_ok=True)
    for lock in ("lock", ".parentlock"):
        try:
            os.remove(os.path.join(prof, lock))
        except FileNotFoundError:
            pass
    page = os.path.join(TMP, "page.html")
    with open(page, "w") as f:
        f.write(html)
    subprocess.run(["firefox", "--headless", "--no-remote", "--profile", prof, f"--window-size={w},{h}",
                    "--screenshot", out, "file://" + page], timeout=90, capture_output=True)
    return Image.open(out).convert("RGB")


def web_page(script, coarse=False):
    s = open(os.path.join(ROOT, "web", "bomb-yard.html")).read()
    if coarse:
        s = s.replace("@media (pointer: coarse)", "@media all")
    i = s.rindex("</body>")
    return s[:i] + "<script>(()=>{" + script + "})();</script>" + s[i:]


SHOW = """const img = document.createElement("img"); img.src = SRC.toDataURL();
img.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;z-index:9999;image-rendering:pixelated;object-fit:fill";
document.body.appendChild(img);"""


def web_images():
    out = os.path.join(TMP, "shot.png")
    # Classic mode: level 1, the arena on its own
    js = """setStyle("classic"); start("cpu"); G.t = 30; draw();""" + SHOW.replace("SRC", "cv")
    save("b2905f7e72947975f726c170f8f357ff", firefox(web_page(js), 512, 512, out))
    # New enhanced mode: the Frost Cave
    js = """setStyle("enhanced"); start("cpu"); level = 3; newRound(); phase = "play"; drawEnhanced(1000);""" + SHOW.replace("SRC", "cv3")
    save("12c6b18ae2a6278cf1df069c31e4cc5f", firefox(web_page(js), 640, 360, out))
    # the enhanced slime, beetle and wisp, close up on the Yard's grass
    for kind, blob in (("blob", "53b1f77c826d53f57554efa124a7a881"), ("beetle", "cb3280daa7f590a410ef435761ec8edf"),
                       ("wisp", "55a468e453166ac31326fac6b20a7a0f")):
        js = f"""setStyle("enhanced"); start("cpu"); newRound(); phase = "play";
const c = document.createElement("canvas"); c.width = 224; c.height = 224; const x = c.getContext("2d");
x.fillStyle = "#6fc24c"; x.fillRect(0, 0, 224, 224); x.scale(3.5, 3.5);
proj = () => [32, 52];
drawMonster(x, Object.assign(makeMonster(3, 3, 1), {{ kind: "{kind}", moving: true, bob: 12, dir: "l" }}), 1000);""" + SHOW.replace("SRC", "c")
        save(blob, firefox(web_page(js), 224, 224, out))
    # two players on one phone
    js = """setStyle("classic"); start("2p"); G.t = 30; draw(); renderHud();"""
    save("fb9a76161f24d4ad48c388c6e49e3960", firefox(web_page(js, coarse=True), 450, 600, out))


# ---------------------------------------------------------------- pictures into the pages
def embed():
    """Put each picture into the page sources as a data: URI, so the pages are whole on their own
    (in the artifact and on GitHub). data-img keeps the picture's id for the next rebuild."""
    def uri(blob):
        return "data:image/png;base64," + base64.b64encode(open(os.path.join(IMAGES, blob + ".png"), "rb").read()).decode()
    for name in os.listdir(PROJECT):
        if not name.endswith(".dc.html"):
            continue
        path = os.path.join(PROJECT, name)
        html = open(path).read()
        new = re.sub(r'src="/_blob/([0-9a-f]+)"', lambda m: f'src="{uri(m.group(1))}" data-img="{m.group(1)}"', html)
        new = re.sub(r'src="data:image/png;base64,[^"]*" data-img="([0-9a-f]+)"', lambda m: f'src="{uri(m.group(1))}" data-img="{m.group(1)}"', new)
        if new != html:
            open(path, "w").write(new)
            print("pictures in", name)


# ---------------------------------------------------------------- the PDF
def build_pdf():
    order = json.load(open(os.path.join(PROJECT, "canvas.json")))["order"]
    pages = []
    for name in order:
        html = open(os.path.join(PROJECT, name)).read()
        html = re.sub(r'src="/_blob/([0-9a-f]+)"', lambda m: f'src="file://{IMAGES}/{m.group(1)}.png"', html)
        html = html.replace('<script src="./support.js"></script>', "<style>html { zoom: 2 }</style>")   # twice as sharp
        im = firefox(html, 960, 1360, os.path.join(TMP, "page.png"))
        pages.append(im.crop((0, 0, 960, 1360)))
        print("page", name)
    out = os.path.join(MANUAL, "bomb-yard-manual.pdf")
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=192, title="Bomb Yard manual")
    print("wrote", out)


if __name__ == "__main__":
    os.makedirs(IMAGES, exist_ok=True)
    if "--pdf-only" not in sys.argv:
        sprite_images()
        nes_images()
        web_images()
        print("images in", IMAGES)
        embed()
    if "--images-only" not in sys.argv:
        build_pdf()
    shutil.rmtree(TMP, ignore_errors=True)
