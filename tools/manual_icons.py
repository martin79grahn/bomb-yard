#!/usr/bin/env python3
"""Pictures of the monsters and bosses for the manual, cut from chr.bin in NES colours.

Usage from another script: import manual_icons; manual_icons.ICONS["asp"] -> a data: URI (PNG)
"""
import base64, io, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
NES = {0x00: "7C7C7C", 0x05: "A80020", 0x06: "A81000", 0x0A: "006800", 0x0F: "000000", 0x10: "BCBCBC",
       0x12: "0058F8", 0x16: "F83800", 0x17: "E45C10", 0x1A: "00A800", 0x21: "3CBCFC", 0x27: "FCA044",
       0x28: "F8B800", 0x29: "B8F818", 0x30: "FCFCFC", 0x38: "F8D878"}
chr_ = open(os.path.join(HERE, "..", "chr.bin"), "rb").read()


def tile(n):
    b = chr_[0x1000 + n * 16: 0x1000 + n * 16 + 16]
    return [[((b[y] >> (7 - x)) & 1) | (((b[y + 8] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def picture(first, tw, th, pal, scale=2):
    im = Image.new("RGBA", (tw * 8, th * 8))
    for ty in range(th):
        for tx in range(tw):
            t = tile(first + ty * 16 + tx)
            for y in range(8):
                for x in range(8):
                    if t[y][x]:
                        c = NES[pal[t[y][x] - 1]]
                        im.putpixel((tx * 8 + x, ty * 8 + y), (int(c[:2], 16), int(c[2:4], 16), int(c[4:], 16), 255))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


KRAX = (0x0F, 0x30, 0x27)
ICONS = {
    "krax": picture(0x4E, 2, 2, KRAX), "asp": picture(0x40, 2, 2, (0x0F, 0x1A, 0x38)),
    "yeti": picture(0x44, 2, 2, (0x0F, 0x30, 0x21)), "imp": picture(0x48, 2, 2, (0x0F, 0x27, 0x38)),
    "angel": picture(0x60, 2, 2, (0x0F, 0x30, 0x28)), "fish": picture(0x6E, 2, 2, KRAX),
    "kraxking": picture(0xA0, 3, 2, (0x0F, 0x00, 0x28)), "scorpion": picture(0xA6, 3, 2, (0x0F, 0x12, 0x28)),
    "mammoth": picture(0xC0, 3, 2, (0x0F, 0x17, 0x30)), "dragon": picture(0xC6, 3, 2, (0x0F, 0x16, 0x27)),
    "storm": picture(0xE0, 3, 2, (0x0F, 0x10, 0x28)), "shark": picture(0x80, 3, 2, (0x0F, 0x10, 0x30)),
    "bomber": picture(0x00, 2, 3, (0x0F, 0x0A, 0x29)),
}
