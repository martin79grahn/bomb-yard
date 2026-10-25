"""The themed monsters and bosses, drawn once for every version of the game.

Each creature is drawn from simple shapes in a unit box, so the same drawing works at the NES
size (16 x 16 monsters, 24 x 16 bosses) and the Mega Drive size (32 x 24 bosses). Everything
faces left. A drawing is a grid of colour roles:
  0 see-through, 1 dark outline, 2 main colour, 3 second colour, 4 accent (eyes and such)
Each version maps the roles to its own palette: the NES has only three colours, so the accent
becomes role 1, 2 or 3 (NES_ACCENT).

Usage from another tool: import creatures; creatures.draw("asp", 16, 16, frame)
"""
import math

MONSTERS = ["asp", "yeti", "imp", "angel"]            # Sand Pit, Frost Cave, Lava Peak, Cloud Nine
BOSSES = ["kraxking", "scorpion", "mammoth", "dragon", "storm"]   # The Yard .. Cloud Nine
# what the accent turns into on the NES (only 3 colours per sprite)
NES_ACCENT = {"asp": 1, "yeti": 1, "imp": 3, "angel": 1,
              "kraxking": 3, "scorpion": 3, "mammoth": 1, "dragon": 3, "storm": 3}


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [[0] * w for _ in range(h)]

    # shapes take unit coordinates (0..1 across the box); pixel centres are tested
    def fill(self, inside, role):
        for y in range(self.h):
            for x in range(self.w):
                if inside((x + 0.5) / self.w, (y + 0.5) / self.h):
                    self.p[y][x] = role

    def ell(self, cx, cy, rx, ry, role):
        self.fill(lambda u, v: ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2 <= 1, role)

    def rect(self, x0, y0, x1, y1, role):
        self.fill(lambda u, v: x0 <= u <= x1 and y0 <= v <= y1, role)

    def poly(self, pts, role):
        def inside(u, v):
            n, c = len(pts), False
            for i in range(n):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
                if (y1 > v) != (y2 > v) and u < (x2 - x1) * (v - y1) / (y2 - y1) + x1:
                    c = not c
            return c
        self.fill(inside, role)

    def line(self, x0, y0, x1, y1, role, px=1.0):
        """a line px pixels thick (at least one pixel), in unit coordinates"""
        steps = int(max(abs(x1 - x0) * self.w, abs(y1 - y0) * self.h) * 2) + 1
        r = max(0.0, (px - 1) / 2)
        for i in range(steps + 1):
            t = i / steps
            x = (x0 + (x1 - x0) * t) * self.w
            y = (y0 + (y1 - y0) * t) * self.h
            for yy in range(int(y - r - 1), int(y + r + 2)):
                for xx in range(int(x - r - 1), int(x + r + 2)):
                    if 0 <= xx < self.w and 0 <= yy < self.h and abs(xx + 0.5 - x) <= r + 0.5 and abs(yy + 0.5 - y) <= r + 0.5:
                        self.p[yy][xx] = role

    def dot(self, u, v, role, size=1):
        x, y = int(u * self.w), int(v * self.h)
        for yy in range(y, y + size):
            for xx in range(x, x + size):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    self.p[yy][xx] = role

    def outline(self):
        new = [row[:] for row in self.p]
        for y in range(self.h):
            for x in range(self.w):
                if self.p[y][x] in (2, 3, 4):
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        xx, yy = x + dx, y + dy
                        if not (0 <= xx < self.w and 0 <= yy < self.h) or self.p[yy][xx] == 0:
                            if 0 <= xx < self.w and 0 <= yy < self.h:
                                new[yy][xx] = 1
                            else:
                                new[y][x] = 1
        self.p = new


# ---------------------------------------------------------------- monsters (16 x 16)
def asp(c, f):
    """a cobra reared up, hood spread, coils on the ground"""
    c.ell(0.62, 0.84, 0.32, 0.12, 2)                  # coils
    c.ell(0.70, 0.74, 0.20, 0.08, 2)
    c.rect(0.36, 0.40, 0.52, 0.82, 2)                 # neck
    c.ell(0.42, 0.36, 0.26, 0.24, 2)                  # hood
    c.ell(0.42, 0.40, 0.08, 0.17, 3)                  # the hood's pale mark
    c.rect(0.40, 0.56, 0.48, 0.80, 3)                 # belly
    c.ell(0.30, 0.16, 0.16, 0.11, 2)                  # head
    c.dot(0.26, 0.13, 4)                              # eye
    if f:                                             # tongue flicks out
        c.line(0.13, 0.20, 0.03, 0.22, 4)
    c.outline()


def yeti(c, f):
    """a little snow beast: white fur, a blue face, horns"""
    c.ell(0.5, 0.58, 0.40, 0.36, 2)                   # furry body
    for i in range(5):                                # ragged fur at the bottom
        c.ell(0.18 + i * 0.16, 0.90, 0.08, 0.07, 2)
    c.ell(0.40, 0.42, 0.22, 0.17, 3)                  # face
    c.dot(0.30, 0.38, 4); c.dot(0.48, 0.38, 4)        # eyes
    c.line(0.32, 0.50, 0.46, 0.50, 4)                 # mouth
    c.line(0.20, 0.22, 0.12, 0.06, 3, 1.5)            # horns
    c.line(0.70, 0.22, 0.80, 0.06, 3, 1.5)
    arm = 0.06 if f else 0.0
    c.ell(0.10, 0.62 - arm, 0.08, 0.14, 2)            # arms
    c.ell(0.90, 0.62 + arm, 0.08, 0.14, 2)
    c.outline()


def imp(c, f):
    """a fire imp: round orange body, horns, bat wings, a pointed tail"""
    flap = -0.06 if f else 0.04
    c.poly([(0.30, 0.45), (0.02, 0.22 + flap), (0.10, 0.50), (0.04, 0.62 + flap)], 3)    # wings
    c.poly([(0.70, 0.45), (0.98, 0.22 + flap), (0.90, 0.50), (0.96, 0.62 + flap)], 3)
    c.line(0.66, 0.80, 0.90, 0.92, 2, 1.2)            # tail
    c.poly([(0.86, 0.86), (0.98, 0.84), (0.94, 0.98)], 2)
    c.ell(0.48, 0.56, 0.27, 0.30, 2)                  # body
    c.poly([(0.30, 0.34), (0.24, 0.10), (0.40, 0.28)], 1)   # horns
    c.poly([(0.56, 0.28), (0.72, 0.10), (0.66, 0.34)], 1)
    c.dot(0.36, 0.48, 3); c.dot(0.54, 0.48, 3)        # glowing eyes
    c.line(0.38, 0.66, 0.56, 0.66, 1)                 # grin
    c.outline()


def angel(c, f):
    """a little angel: white robe and wings, a golden halo and hair"""
    up = -0.08 if f else 0.0
    c.poly([(0.36, 0.44), (0.04, 0.28 + up), (0.02, 0.50 + up), (0.14, 0.66), (0.36, 0.62)], 2)   # wings
    c.poly([(0.64, 0.44), (0.96, 0.28 + up), (0.98, 0.50 + up), (0.86, 0.66), (0.64, 0.62)], 2)
    c.poly([(0.34, 0.48), (0.66, 0.48), (0.76, 0.96), (0.24, 0.96)], 2)    # robe
    c.ell(0.5, 0.34, 0.17, 0.16, 2)                   # face
    c.ell(0.5, 0.22, 0.18, 0.08, 3)                   # hair
    c.ell(0.5, 0.06, 0.20, 0.05, 3)                   # halo
    c.dot(0.42, 0.34, 4); c.dot(0.56, 0.34, 4)        # eyes
    c.rect(0.34, 0.60, 0.66, 0.64, 3)                 # golden belt
    c.outline()


# ---------------------------------------------------------------- bosses (24 x 16, or 32 x 24)
def kraxking(c, f):
    """a giant Krax wearing a crown, wings beating as it struts"""
    c.ell(0.56, 0.58, 0.34, 0.30, 2)                  # body
    c.poly([(0.86, 0.50), (1.0, 0.36), (0.98, 0.70)], 2)   # tail feathers
    c.ell(0.26, 0.34, 0.17, 0.24, 2)                  # head
    c.poly([(0.12, 0.30), (0.0, 0.40), (0.12, 0.46)], 3)   # beak
    c.dot(0.20, 0.28, 3, max(1, c.w // 24))           # eye
    c.poly([(0.14, 0.12), (0.16, 0.0), (0.21, 0.08), (0.26, 0.0), (0.31, 0.08), (0.36, 0.0), (0.38, 0.12)], 3)   # crown
    if f:
        c.poly([(0.40, 0.40), (0.62, 0.06), (0.80, 0.18), (0.74, 0.46)], 2)   # wing up
    else:
        c.poly([(0.40, 0.50), (0.84, 0.48), (0.72, 0.80)], 2)                 # wing folded
    leg = 0.04 if f else -0.04
    c.line(0.48 + leg, 0.84, 0.46 + leg, 1.0, 3, c.w / 24)                    # legs
    c.line(0.64 - leg, 0.84, 0.66 - leg, 1.0, 3, c.w / 24)
    c.outline()
    if f:
        c.line(0.50, 0.38, 0.70, 0.26, 1)             # a line through the raised wing
    else:
        c.line(0.48, 0.56, 0.74, 0.60, 1)


def scorpion(c, f):
    """a giant scorpion: claws forward, its tail curled over its back"""
    sh = 0.03 if f else -0.03
    for i in range(4):                                # legs
        x = 0.36 + i * 0.12
        c.line(x, 0.72, x - 0.06 + (sh if i % 2 else -sh), 0.98, 2, c.w / 24)
    c.ell(0.48, 0.70, 0.24, 0.14, 2)                  # body
    for x, y in ((0.72, 0.60), (0.82, 0.46), (0.82, 0.30), (0.72, 0.20)):   # tail segments, curling up and forward
        c.ell(x, y, 0.075, 0.11, 2)
    c.poly([(0.66, 0.14), (0.52, 0.22), (0.64, 0.30)], 3)   # stinger
    c.line(0.26, 0.66, 0.12, 0.56, 2, c.w / 16)       # arms
    c.ell(0.10, 0.48, 0.09, 0.12, 2)                  # claws
    c.poly([(0.02, 0.36), (0.10, 0.42), (0.04, 0.48)], 0 if f else 2)   # the claw opens and shuts
    c.dot(0.30, 0.62, 3); c.dot(0.36, 0.62, 3)        # eyes
    c.outline()


def mammoth(c, f):
    """a woolly mammoth: a shaggy body, trunk, curved tusks"""
    leg = 0.03 if f else -0.03
    for x, s in ((0.40, 1), (0.52, -1), (0.70, 1), (0.82, -1)):   # legs
        c.rect(x - 0.05 + leg * s, 0.70, x + 0.05 + leg * s, 1.0, 2)
    c.ell(0.62, 0.50, 0.34, 0.34, 2)                  # body
    c.ell(0.28, 0.38, 0.20, 0.26, 2)                  # head, a high dome
    c.ell(0.40, 0.42, 0.10, 0.18, 2)                  # ear
    c.poly([(0.12, 0.44), (0.20, 0.50), (0.12, 0.92), (0.04, 0.96), (0.02, 0.88)], 2)   # trunk
    c.line(0.20, 0.58, 0.10, 0.70, 3, c.w / 16)       # tusk
    c.line(0.10, 0.70, 0.04, 0.62, 3, c.w / 16)
    c.outline()
    c.dot(0.20, 0.32, 1, max(1, c.w // 24))           # eye
    c.line(0.42, 0.30, 0.42, 0.56, 1)                 # the ear's edge
    for x in (0.56, 0.70, 0.84):                      # shaggy fur
        c.line(x, 0.30, x - 0.03, 0.44, 1)


def dragon(c, f):
    """a dragon: horned head, wings beating, a spiked tail"""
    c.poly([(0.80, 0.56), (1.0, 0.40), (0.96, 0.66), (0.80, 0.74)], 2)   # tail
    c.poly([(0.94, 0.38), (1.0, 0.30), (1.0, 0.46)], 3)                   # its spike
    leg = 0.03 if f else -0.03
    c.rect(0.40 + leg, 0.74, 0.48 + leg, 1.0, 2)      # legs
    c.rect(0.64 - leg, 0.74, 0.72 - leg, 1.0, 2)
    c.ell(0.58, 0.62, 0.26, 0.20, 2)                  # body
    c.ell(0.56, 0.70, 0.18, 0.10, 3)                  # belly
    c.poly([(0.36, 0.56), (0.24, 0.26), (0.32, 0.20), (0.46, 0.50)], 2)   # neck
    c.ell(0.20, 0.24, 0.14, 0.13, 2)                  # head
    c.poly([(0.08, 0.20), (0.0, 0.28), (0.10, 0.34)], 2)   # snout
    c.poly([(0.24, 0.12), (0.34, 0.0), (0.30, 0.16)], 3)   # horn
    c.dot(0.18, 0.20, 3)                              # eye
    if f:
        c.poly([(0.50, 0.46), (0.62, 0.0), (0.92, 0.10), (0.74, 0.46)], 3)   # wing up
    else:
        c.poly([(0.50, 0.48), (0.66, 0.26), (0.98, 0.30), (0.76, 0.52)], 3)  # wing down
    c.outline()


def storm(c, f):
    """a thundercloud with an angry face, lightning striking below"""
    for cx, cy, r in ((0.24, 0.50, 0.20), (0.46, 0.36, 0.26), (0.72, 0.42, 0.22), (0.86, 0.56, 0.14), (0.52, 0.60, 0.24)):
        c.ell(cx, cy, r * 0.75, r * 1.05, 2)
    bx = 0.30 if f else 0.66                          # the bolt strikes on one side, then the other
    c.poly([(bx, 0.66), (bx + 0.12, 0.66), (bx + 0.06, 0.78), (bx + 0.13, 0.78), (bx - 0.04, 1.0), (bx + 0.01, 0.84), (bx - 0.06, 0.84)], 3)
    c.dot(0.36, 0.44, 3, max(1, c.w // 16)); c.dot(0.56, 0.44, 3, max(1, c.w // 16))   # glowing eyes
    c.outline()
    c.line(0.30, 0.34, 0.40, 0.40, 1)                 # angry brows
    c.line(0.62, 0.34, 0.52, 0.40, 1)
    c.line(0.40, 0.58, 0.54, 0.58, 1)                 # a scowl


DRAW = {"asp": asp, "yeti": yeti, "imp": imp, "angel": angel,
        "kraxking": kraxking, "scorpion": scorpion, "mammoth": mammoth, "dragon": dragon, "storm": storm}


def draw(name, w, h, frame=0):
    c = Canvas(w, h)
    DRAW[name](c, frame)
    return c.p


def nes(name, w, h, frame=0):
    """the drawing with the accent folded into the NES's three colours"""
    a = NES_ACCENT[name]
    return [[a if v == 4 else v for v in row] for row in draw(name, w, h, frame)]


if __name__ == "__main__":
    for n in MONSTERS:
        for f in (0, 1):
            print(n, f)
            for row in draw(n, 16, 16, f):
                print("".join(".#ab*"[v] for v in row))
