#!/usr/bin/env python3
"""Write the Mega Drive music as VGM files (res/music/*.vgm), which SGDK's rescomp turns
into XGM2 songs.

The level songs are new arrangements of the NES songs: the same melodies and grooves,
played on five FM voices (lead, bass, chords, drums, and an echo of the lead in stereo)
with PSG noise for shakers, hi-hats and snares. FM channel 6 is left free for the PCM sound
effects. The title and boss songs and the jingles are new.

Usage: make_music.py OUTDIR
"""
import math
import os
import struct
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "res/music"
FM_CLOCK, PSG_CLOCK = 7670453, 3579545
FPS, SAMPLES_PER_FRAME = 60, 735

# ---------------------------------------------------------------- FM instruments
# alg_fb, then per operator 1-4: DT/MUL, TL, RS/AR, AM/D1R, D2R, D1L/RR
PATCH = {
    "bass": (0x2C, [(0x01, 0x1E, 0x1F, 0x0A, 0x00, 0x2F), (0x01, 0x0C, 0x1F, 0x08, 0x02, 0x4A),
                    (0x00, 0x24, 0x1F, 0x0C, 0x00, 0x2F), (0x01, 0x10, 0x1F, 0x06, 0x02, 0x4A)]),
    "lead": (0x34, [(0x02, 0x22, 0x1F, 0x05, 0x00, 0x1F), (0x31, 0x14, 0x1F, 0x03, 0x01, 0x27),
                    (0x01, 0x1C, 0x1F, 0x05, 0x00, 0x1F), (0x71, 0x16, 0x1F, 0x03, 0x01, 0x27)]),
    "pluck": (0x1C, [(0x01, 0x26, 0x1F, 0x08, 0x00, 0x3F), (0x02, 0x18, 0x1F, 0x0C, 0x04, 0x58),
                     (0x03, 0x30, 0x1F, 0x08, 0x00, 0x3F), (0x01, 0x1C, 0x1F, 0x0A, 0x04, 0x58)]),
    "drum": (0x07, [(0x01, 0x7F, 0x1F, 0x00, 0x00, 0x0F), (0x01, 0x7F, 0x1F, 0x00, 0x00, 0x0F),
                    (0x01, 0x7F, 0x1F, 0x00, 0x00, 0x0F), (0x01, 0x02, 0x1F, 0x10, 0x0A, 0xFF)]),
    "marimba": (0x14, [(0x04, 0x22, 0x1F, 0x14, 0x00, 0xFF), (0x01, 0x04, 0x1F, 0x0E, 0x08, 0xF8),
                       (0x01, 0x2A, 0x1F, 0x10, 0x00, 0xFF), (0x01, 0x08, 0x1F, 0x0C, 0x08, 0xF8)]),
    "bell": (0x04, [(0x17, 0x20, 0x1F, 0x07, 0x02, 0x26), (0x02, 0x08, 0x1F, 0x05, 0x02, 0x36),
                    (0x05, 0x26, 0x1F, 0x09, 0x02, 0x26), (0x01, 0x0C, 0x1F, 0x04, 0x01, 0x36)]),
    "pad": (0x25, [(0x01, 0x2A, 0x0E, 0x02, 0x00, 0x16), (0x01, 0x14, 0x0C, 0x02, 0x01, 0x16),
                   (0x32, 0x18, 0x0C, 0x02, 0x01, 0x16), (0x71, 0x14, 0x0C, 0x02, 0x01, 0x16)]),
    "reed": (0x32, [(0x01, 0x1C, 0x1F, 0x04, 0x00, 0x18), (0x03, 0x30, 0x1F, 0x05, 0x00, 0x18),
                    (0x01, 0x22, 0x1F, 0x04, 0x00, 0x18), (0x01, 0x08, 0x14, 0x02, 0x01, 0x28)]),
    "brass": (0x34, [(0x01, 0x1A, 0x15, 0x05, 0x00, 0x17), (0x01, 0x0C, 0x13, 0x03, 0x01, 0x27),
                     (0x02, 0x22, 0x15, 0x05, 0x00, 0x17), (0x01, 0x10, 0x13, 0x03, 0x01, 0x27)]),
    # pipe organ: four sine drawbars (8', 4', 2', 16') all heard at once, held while the key is down
    "organ": (0x07, [(0x01, 0x14, 0x1F, 0x00, 0x00, 0x07), (0x02, 0x1C, 0x1F, 0x00, 0x00, 0x07),
                     (0x04, 0x24, 0x1F, 0x00, 0x00, 0x07), (0x00, 0x1A, 0x1F, 0x00, 0x00, 0x07)]),
    # voices singing "aah": two soft, slightly detuned pairs that swell in
    "choir": (0x2C, [(0x01, 0x2C, 0x10, 0x02, 0x00, 0x17), (0x31, 0x0E, 0x0D, 0x01, 0x00, 0x18),
                     (0x03, 0x34, 0x10, 0x02, 0x00, 0x17), (0x71, 0x10, 0x0D, 0x01, 0x00, 0x18)]),
}
SLOT = (0x0, 0x8, 0x4, 0xC)                     # register offsets of operators 1-4
CARRIERS = {0: (3,), 1: (3,), 2: (3,), 3: (3,), 4: (1, 3), 5: (1, 2, 3), 6: (1, 2, 3), 7: (0, 1, 2, 3)}


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def fm_freq(f):
    for block in range(8):
        fnum = f * (1 << 20) / (FM_CLOCK / 144) / (1 << max(0, block - 1)) if block else f * (1 << 21) / (FM_CLOCK / 144)
        if fnum < 2048:
            return block, int(round(fnum))
    return 7, 2047


# ---------------------------------------------------------------- song description
class Note:
    def __init__(self, step, note, length, vol=1.0, slide=0.0, vib=0.0):
        self.step, self.note, self.length, self.vol = step, note, length, vol
        self.slide, self.vib = slide, vib      # semitones per frame; vibrato depth in semitones


class Song:
    def __init__(self, rate, steps, loop=True):
        self.rate, self.steps, self.loop = rate, steps, loop     # frames per 16th step
        self.fm = {}            # channel 0-4 -> (patch, pan, gain, [Note])
        self.psg = {}           # tone channel 0-2 -> (gain, [Note])
        self.noise = []         # (step, kind)

    def track(self, ch, patch, pan="C", gain=1.0):
        notes = []
        self.fm[ch] = (patch, {"C": 0xC0, "L": 0x80, "R": 0x40}[pan], gain, notes)
        return notes

    def tone(self, ch, gain=1.0):
        notes = []
        self.psg[ch] = (gain, notes)
        return notes


# noise drums: per-frame (attenuation, mode) envelopes; mode = (white, rate)
NOISE_KITS = {
    "hat":    [(1, (1, 0)), (5, (1, 0)), (9, (1, 0)), (13, (1, 0))],
    "ohat":   [(1, (1, 0)), (3, (1, 0)), (5, (1, 0)), (7, (1, 0)), (9, (1, 0)), (11, (1, 0)), (13, (1, 0))],
    "shaker": [(4, (1, 0)), (2, (1, 0)), (5, (1, 0)), (9, (1, 0)), (13, (1, 0))],
    "snare":  [(0, (1, 1)), (0, (1, 1)), (1, (1, 1)), (3, (1, 2)), (5, (1, 2)), (7, (1, 2)), (9, (1, 2)), (11, (1, 2)), (13, (1, 2))],
    "slap":   [(0, (1, 1)), (3, (1, 1)), (7, (1, 1)), (11, (1, 1))],
    "wind":   [(15 - min(6, i // 3) if i < 24 else 9 + (i - 24) // 4, (1, 2)) for i in range(48)],
    "crash":  [(min(15, 1 + i // 3), (1, 0)) for i in range(40)],
}


# ---------------------------------------------------------------- rendering to VGM
def render(song):
    cmds = bytearray()          # VGM command stream
    frames_total = song.steps * song.rate
    loop_pos = None

    def ym(port, reg, val):
        cmds.extend((0x52 + port, reg, val & 0xFF))

    def psg(b):
        cmds.extend((0x50, b & 0xFF))

    def fm_reg(ch, reg, val):
        ym(ch // 3, reg + ch % 3, val)

    keycode = lambda ch: (ch % 3) | (4 if ch >= 3 else 0)
    # set up the chips
    ym(0, 0x22, 0x00); ym(0, 0x27, 0x00)
    for ch in range(6):
        ym(0, 0x28, keycode(ch))
    for b in (0x9F, 0xBF, 0xDF, 0xFF):
        psg(b)
    base_tl = {}
    for ch, (patch, pan, gain, _) in song.fm.items():
        alg_fb, ops = PATCH[patch]
        for i, op in enumerate(ops):
            for r, v in zip((0x30, 0x40, 0x50, 0x60, 0x70, 0x80), op):
                fm_reg(ch, r + SLOT[i], v)
            fm_reg(ch, 0x90 + SLOT[i], 0)
        fm_reg(ch, 0xB0, alg_fb)
        fm_reg(ch, 0xB4, pan)
        base_tl[ch] = [op[1] for op in ops]

    # per-frame events
    fm_on = {}                  # ch -> (note obj, start frame)
    fm_last = {}                # ch -> (block, fnum)
    psg_last = {}
    noise_env = []
    loop_pos = len(cmds)
    ev_fm = {ch: sorted(t[3], key=lambda n: n.step) for ch, t in song.fm.items()}
    ev_psg = {ch: sorted(t[1], key=lambda n: n.step) for ch, t in song.psg.items()}
    noise_by_frame = {}
    for step, kind in song.noise:
        noise_by_frame.setdefault(step * song.rate, []).append(kind)
    starts_fm = {}
    for ch, ns in ev_fm.items():
        for n in ns:
            starts_fm.setdefault((ch, n.step * song.rate), n)
    starts_psg = {}
    for ch, ns in ev_psg.items():
        for n in ns:
            starts_psg.setdefault((ch, n.step * song.rate), n)
    psg_on = {}
    for f in range(frames_total):
        # FM
        for ch, (patch, pan, gain, _) in song.fm.items():
            n = starts_fm.get((ch, f))
            cur = fm_on.get(ch)
            if cur and (n or f >= cur[1] + cur[0].length * song.rate - 1):
                ym(0, 0x28, keycode(ch))
                del fm_on[ch]
                cur = None
            if n:
                alg = PATCH[patch][0] & 7
                att = int(round((1 - n.vol * gain) * 28)) + 6     # headroom for the PSG and the effects
                for i in CARRIERS[alg]:
                    fm_reg(ch, 0x40 + SLOT[i], min(127, base_tl[ch][i] + max(0, att)))
                fm_on[ch] = (n, f)
                fm_last.pop(ch, None)
            cur = fm_on.get(ch)
            if cur:
                nt, f0 = cur
                age = f - f0
                pitch = nt.note + nt.slide * age
                if nt.vib and age > 8:
                    pitch += nt.vib * math.sin(age * 2 * math.pi / 14)
                bf = fm_freq(hz(pitch))
                if fm_last.get(ch) != bf:
                    fm_reg(ch, 0xA4, (bf[0] << 3) | (bf[1] >> 8))
                    fm_reg(ch, 0xA0, bf[1] & 0xFF)
                    fm_last[ch] = bf
                if age == 0:
                    ym(0, 0x28, 0xF0 | keycode(ch))
        # PSG tones
        for ch, (gain, _) in song.psg.items():
            n = starts_psg.get((ch, f))
            cur = psg_on.get(ch)
            if n:
                psg_on[ch] = (n, f)
                cur = psg_on[ch]
            if cur:
                nt, f0 = cur
                age = f - f0
                if age >= nt.length * song.rate - 1:
                    psg(0x90 | (ch << 5) | 15)
                    del psg_on[ch]
                    continue
                pitch = nt.note + (nt.vib * math.sin(age * 2 * math.pi / 12) if nt.vib and age > 6 else 0)
                per = max(1, min(1023, int(round(PSG_CLOCK / (32 * hz(pitch))))))
                if psg_last.get(ch) != per:
                    psg(0x80 | (ch << 5) | (per & 15)); psg((per >> 4) & 0x3F)
                    psg_last[ch] = per
                base = 15 - int(round(nt.vol * gain * 11))
                att = min(15, base + age // 6)          # a plucky fade
                psg(0x90 | (ch << 5) | att)
        # noise
        for kind in noise_by_frame.get(f, []):
            noise_env = [list(x) for x in NOISE_KITS[kind]]
            noise_env_mode = None
        if noise_env:
            att, mode = noise_env.pop(0)
            psg(0xE0 | (mode[0] << 2) | mode[1])
            psg(0xF0 | att)
            if not noise_env:
                psg(0xFF)
        cmds.extend((0x62,))
    if not song.loop:
        for ch in song.fm:
            ym(0, 0x28, keycode(ch))
        for b in (0x9F, 0xBF, 0xDF, 0xFF):
            psg(b)
        cmds.extend((0x62,) * 2)
    cmds.append(0x66)

    header = bytearray(0x100)
    header[0:4] = b"Vgm "
    struct.pack_into("<I", header, 0x08, 0x160)
    struct.pack_into("<I", header, 0x0C, PSG_CLOCK)
    total = frames_total * SAMPLES_PER_FRAME
    struct.pack_into("<I", header, 0x18, total)
    if song.loop:
        struct.pack_into("<I", header, 0x1C, 0x100 + loop_pos - 0x1C)
        struct.pack_into("<I", header, 0x20, total)
    struct.pack_into("<I", header, 0x24, 60)
    struct.pack_into("<H", header, 0x28, 0x0009)
    header[0x2A] = 16
    struct.pack_into("<I", header, 0x2C, FM_CLOCK)
    struct.pack_into("<I", header, 0x34, 0x100 - 0x34)
    data = header + cmds
    struct.pack_into("<I", data, 0x04, len(data) - 4)
    return bytes(data)


# ---------------------------------------------------------------- helpers for writing parts
def from_steps(arr, length_to_next=True, maxlen=8, offset=0, vol=1.0, held_flag=None):
    """NES-style arrays: a MIDI note starts a note, 0 rings on, 1 cuts. -> [Note]"""
    out = []
    n = len(arr)
    for i, v in enumerate(arr):
        if v > 1:
            note = v & 0x7F if held_flag else v
            j = i + 1
            while j < n and arr[j] == 0 and j - i < maxlen:
                j += 1
            out.append(Note(i + offset, note, j - i, vol))
    return out


def shift(notes, steps=0, semis=0, vol=1.0):
    return [Note(n.step + steps, n.note + semis, n.length, n.vol * vol, n.slide, n.vib) for n in notes]


def repeat(notes, times, period):
    return [Note(n.step + k * period, n.note, n.length, n.vol, n.slide, n.vib) for k in range(times) for n in notes]


def chord_arp(chords, steps_per_chord, pattern, octave_up=12, vol=0.6, length=1):
    out = []
    for ci, ch in enumerate(chords):
        for k in range(steps_per_chord):
            idx = pattern[k % len(pattern)]
            note = ch[idx % len(ch)] + (octave_up if idx >= len(ch) else 0)
            out.append(Note(ci * steps_per_chord + k, note, length, vol * (1.0 if k % 4 == 0 else 0.8)))
    return out


# ---------------------------------------------------------------- the NES songs (from main.c)
LEAD_YARD = [81,0,0,79, 0,76,0,0, 79,0,76,0, 74,0,0,0,   76,0,0,74, 0,72,0,0, 74,0,72,0, 69,0,0,0,
             69,0,72,0, 74,0,76,0, 79,0,0,76, 0,79,81,0, 84,0,0,81, 0,79,0,76, 79,0,76,0, 74,72,69,0]
TRI_YARD = [45,0,67,67, 60,0,67,0, 45,0,67,60, 67,60,60,0,  45,0,67,67, 60,0,67,0, 45,67,60,67, 60,67,60,60,
            45,0,67,67, 60,0,67,0, 45,0,67,60, 67,60,60,0,  45,67,67,60, 60,67,60,67, 72,72,67,67, 60,60,45,45]
LEAD_SAND = [74,0,0,75, 74,0,72,0, 70,0,72,0, 69,0,0,0,  66,0,67,0, 69,0,70,69, 67,0,66,0, 63,0,62,0,
             62,0,66,0, 67,0,69,0, 70,0,69,70, 72,0,70,69, 67,69,67,66, 63,0,66,0, 62,0,0,0, 0,0,1,0]
LEAD_LAVA = [62,0,0,0, 0,0,0,0, 63,0,0,0, 62,0,0,0,      0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0,
             68,0,0,0, 0,0,67,0, 65,0,0,0, 63,0,0,0,     62,0,0,0, 0,0,0,0, 61,0,0,0, 62,0,1,0]
LEAD_CLOUD = [72,0,0,0, 76,0,0,0, 79,0,0,0, 77,0,76,0,    74,0,0,0, 0,0,0,0, 76,0,0,0, 0,0,0,0,
              77,0,0,0, 76,0,74,0, 72,0,0,0, 74,0,0,0,    71,0,0,0, 0,0,0,0, 72,0,0,0, 0,0,0,0]
LEAD_FROST = [76,0,0,0, 83,0,0,0, 81,0,0,0, 0,0,0,0,      79,0,0,0, 78,0,0,0, 74,0,0,0, 0,0,0,0,
              76,0,0,0, 83,0,0,0, 88,0,0,0, 86,0,0,0,     83,0,0,0, 81,0,79,0, 78,0,0,0, 0,0,0,0]
SHK, DUM, TEK = "shaker", "dum", "tek"


def yard():
    s = Song(7, 128)
    lead = from_steps(LEAD_YARD, vol=0.95)
    s.track(0, "marimba", "C", 1.0).extend(repeat(lead, 2, 64))
    s.track(4, "marimba", "L", 0.55).extend(shift(repeat(lead, 2, 64), 3, 12, 0.8))   # echo, an octave up
    # bass: Am F C G, a tropical bounce
    roots = [45, 41, 48, 43]
    bass = []
    for bar, r in enumerate(roots * 2):
        for k, (st, octv) in enumerate(((0, 0), (3, 0), (6, 12), (8, 0), (11, 0), (14, 12))):
            bass.append(Note(bar * 16 + st, r - 12 + octv, 2, 0.95 if k % 3 == 0 else 0.8))
    s.track(1, "bass", "C", 1.0).extend(bass)
    chords = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]] * 2
    arp = chord_arp(chords, 16, [0, 1, 2, 3, 2, 1, 2, 3], vol=0.45)
    s.track(2, "pluck", "R", 0.8).extend(arp)
    # drums: bongos from the NES triangle part, with the low log drum as a kick
    drums = []
    for i, v in enumerate(TRI_YARD * 2):
        if v == 45:
            drums.append(Note(i, 45, 2, 1.0, slide=-1.2))
        elif v:
            drums.append(Note(i, v - 5, 1, 0.75, slide=-0.6))
    s.track(3, "drum", "C", 1.0).extend(drums)
    groove = ["shaker", "shaker", "hat", "shaker"]
    for i in range(128):
        if i % 2 == 0 or i % 16 in (7, 13):
            s.noise.append((i, groove[i % 4] if i % 8 != 4 else "slap"))
    # second half: a PSG counter-melody high above
    s.tone(0, 0.5).extend(shift(lead[::2], 64 + 6, 12, 0.7))
    return s


def sand():
    s = Song(8, 128)
    lead = from_steps(LEAD_SAND, vol=1.0)
    for n in lead:
        n.vib = 0.25
    s.track(0, "reed", "C", 1.0).extend(repeat(lead, 2, 64))
    s.track(4, "reed", "L", 0.5).extend(shift(repeat(lead, 2, 64), 2, 0, 0.75))
    # a droning bass on D that leans on Eb, like the NES triangle
    bass = []
    for rep in range(2):
        for bar, r in enumerate((38, 39, 38, 43)):
            b0 = rep * 64 + bar * 16
            bass += [Note(b0, r, 6, 1.0), Note(b0 + 6, r, 4, 0.8), Note(b0 + 10, r + 12, 2, 0.7), Note(b0 + 12, r, 4, 0.85)]
    s.track(1, "bass", "C", 1.0).extend(bass)
    # an oud-like pluck walking the D hijaz chord
    hijaz = [[62, 66, 69, 72], [63, 67, 70, 74], [62, 66, 69, 72], [67, 70, 74, 75]] * 2
    s.track(2, "pluck", "R", 0.75).extend(chord_arp(hijaz, 16, [0, 2, 1, 3, 2, 0, 3, 1], 0, vol=0.5, length=2)[::2])
    # darbuka: dum (low), tek (high) - the maqsum rhythm
    pattern = [DUM, 0, TEK, 0, SHK, 0, TEK, 0, DUM, 0, SHK, 0, TEK, 0, SHK, 0]
    drums = []
    for i in range(128):
        k = pattern[i % 16]
        if k == DUM:
            drums.append(Note(i, 43, 2, 1.0, slide=-0.8))
        elif k == TEK:
            drums.append(Note(i, 64, 1, 0.7, slide=-0.4))
            s.noise.append((i, "slap"))
        elif k == SHK:
            s.noise.append((i, "shaker"))
        elif i % 2:
            s.noise.append((i, "shaker"))
    s.track(3, "drum", "C", 1.0).extend(drums)
    return s


def frost():
    s = Song(11, 128)
    lead = from_steps(LEAD_FROST, vol=1.0, maxlen=8)
    s.track(0, "bell", "C", 1.0).extend(repeat(lead, 2, 64))
    s.track(4, "bell", "L", 0.45).extend(shift(repeat(lead, 2, 64), 2, 0, 0.7))    # the echo of each bell
    bass_notes = [40, 47, 36, 43, 40, 47, 38, 45]
    bass = [Note(i * 8 + rep * 64, n, 8, 0.85) for rep in range(2) for i, n in enumerate(bass_notes)]
    s.track(1, "bass", "C", 0.85).extend(bass)
    pads = {40: 67, 47: 66, 36: 64, 43: 62, 38: 66, 45: 64}
    s.track(2, "pad", "R", 0.65).extend([Note(n.step, pads[n.note], 8, 0.7) for n in bass])
    # twinkles on the PSG, and the wind
    tw = []
    for i in range(0, 128, 4):
        if i % 16 in (2, 10) or (i >= 64 and i % 8 == 6):
            tw.append(Note(i + 2, 88 + (i // 4) % 3 * 3, 1, 0.5))
    s.tone(0, 0.6).extend(tw)
    s.noise += [(0, "wind"), (64, "wind")]
    for i in range(128):
        if i % 8 == 4:
            s.noise.append((i, "hat"))
    s.track(3, "drum", "C", 0.7).extend([Note(i, 36, 4, 0.8, slide=-0.5) for i in range(0, 128, 16)])
    return s


def lava():
    """Lava Peak: a dark dirge in D phrygian. Ghostly voices, a tolling bell, a heartbeat."""
    s = Song(10, 128)
    lead = from_steps(LEAD_LAVA, vol=1.0, maxlen=12)
    for n in lead:
        n.vib = 0.3
    s.track(0, "choir", "C", 1.0).extend(repeat(lead, 2, 64))
    s.track(4, "choir", "L", 0.55).extend(shift(repeat(lead, 2, 64), 4, -12, 0.8))   # a lower voice answers
    bass = []
    for rep in range(2):
        for bar, (r1, r2) in enumerate(((38, 39), (38, 39), (44, 43), (38, 37))):
            b0 = rep * 64 + bar * 16
            bass += [Note(b0, r1 - 12, 6, 1.0), Note(b0 + 6, r1 - 12, 2, 0.8), Note(b0 + 8, r2 - 12, 4, 0.9), Note(b0 + 12, r1 - 12, 4, 0.85)]
    s.track(1, "bass", "C", 1.0).extend(bass)
    # a big bell tolls at the start of every bar, a tritone above the bass in the third
    tolls = [50, 51, 56, 49]
    s.track(2, "bell", "R", 0.8).extend([Note(rep * 64 + bar * 16, n, 16, 0.9) for rep in range(2) for bar, n in enumerate(tolls)])
    # heartbeat: two low thumps per bar
    s.track(3, "drum", "C", 1.0).extend([Note(i + d, 33, 2, 1.0 if d == 0 else 0.8, slide=-0.6) for i in range(0, 128, 16) for d in (0, 2)])
    s.noise += [(8, "wind"), (40, "wind"), (72, "wind"), (104, "wind")]
    return s


def cloud():
    """Cloud Nine: a hymn in C major. Organ chords and pedals, a choir sings the tune."""
    s = Song(9, 128)
    lead = from_steps(LEAD_CLOUD, vol=1.0, maxlen=8)
    for n in lead:
        n.vib = 0.12
    s.track(0, "choir", "C", 1.0).extend(repeat(lead, 2, 64))
    # organ: three chord voices per bar and pedal notes, C G F G
    chords = [(60, 64, 67), (59, 62, 67), (57, 60, 65), (59, 62, 65)]
    pedals = [(36, 40), (43, 43), (41, 45), (43, 36)]
    for v, ch in enumerate((2, 3, 4)):
        notes = [Note(rep * 64 + bar * 16, chords[bar][v], 16, 0.9) for rep in range(2) for bar in range(4)]
        s.track(ch, "organ", "C" if v == 1 else ("L" if v == 0 else "R"), 0.8).extend(notes)
    s.track(1, "organ", "C", 0.9).extend([Note(rep * 64 + bar * 16 + half * 8, pedals[bar][half], 8, 0.9)
                                          for rep in range(2) for bar in range(4) for half in range(2)])
    # second time round a high descant floats over the choir on the PSG
    s.tone(0, 0.35).extend(shift(lead, 64, 12, 0.5))
    return s


def boss_song():
    s = Song(6, 128)
    # C minor: Cm Ab Bb G, a driving bass and brass stabs
    roots = [36, 32, 34, 31]
    bass = []
    for bar, r in enumerate(roots * 2):
        for k in range(8):
            octv = 12 if k % 4 == 3 else 0
            bass.append(Note(bar * 16 + k * 2, r + octv, 2, 1.0 if k % 2 == 0 else 0.8))
    s.track(1, "bass", "C", 1.0).extend(bass)
    melody = [  # (step, note, len)
        (0, 72, 3), (3, 75, 3), (6, 79, 2), (8, 77, 4), (12, 75, 2), (14, 74, 2),
        (16, 72, 3), (19, 75, 3), (22, 80, 2), (24, 79, 6), (30, 77, 2),
        (32, 74, 3), (35, 77, 3), (38, 82, 2), (40, 80, 4), (44, 79, 2), (46, 77, 2),
        (48, 79, 4), (52, 78, 2), (54, 79, 2), (56, 83, 6), (62, 79, 2)]
    lead = [Note(a, b, c, 1.0, vib=0.15) for a, b, c in melody]
    s.track(0, "brass", "C", 1.0).extend(lead + shift(lead, 64, 12, 0.9))
    s.track(4, "brass", "L", 0.5).extend(shift(lead + shift(lead, 64, 12, 0.9), 3, -12, 0.8))
    chords = [[60, 63, 67], [56, 60, 63], [58, 62, 65], [55, 59, 62]] * 2
    s.track(2, "pluck", "R", 0.7).extend(chord_arp(chords, 16, [0, 1, 2, 1], vol=0.5))
    drums = []
    for i in range(128):
        if i % 16 in (0, 6, 8, 11):
            drums.append(Note(i, 40, 2, 1.0, slide=-1.4))
        if i % 16 in (4, 12):
            s.noise.append((i, "snare"))
        elif i % 2 == 0:
            s.noise.append((i, "hat"))
        if i % 64 >= 60:
            drums.append(Note(i, 52 - (i % 4) * 3, 1, 0.9, slide=-0.6))
    s.noise.append((0, "crash")); s.noise.append((64, "crash"))
    s.track(3, "drum", "C", 1.0).extend(drums)
    return s


def title():
    s = Song(7, 64)
    melody = [(0, 67, 2), (2, 72, 2), (4, 76, 2), (6, 79, 4), (10, 76, 2), (12, 79, 4),
              (16, 77, 2), (18, 76, 2), (20, 74, 2), (22, 72, 4), (26, 74, 2), (28, 76, 4),
              (32, 67, 2), (34, 72, 2), (36, 76, 2), (38, 79, 4), (42, 81, 2), (44, 79, 4),
              (48, 77, 2), (50, 74, 2), (52, 76, 2), (54, 72, 6), (60, 67, 4)]
    lead = [Note(a, b, c, 1.0) for a, b, c in melody]
    s.track(0, "lead", "C", 0.9).extend(lead)
    s.track(4, "marimba", "L", 0.5).extend(shift(lead, 2, 12, 0.7))
    roots = [36, 41, 43, 36]
    bass = [Note(bar * 16 + st, r + (12 if st % 8 == 6 else 0), 2, 0.9) for bar, r in enumerate(roots)
            for st in (0, 3, 6, 8, 11, 14)]
    s.track(1, "bass", "C", 1.0).extend(bass)
    s.track(2, "pluck", "R", 0.7).extend(chord_arp([[60, 64, 67], [60, 65, 69], [59, 62, 67], [60, 64, 67]], 16, [0, 1, 2, 3], vol=0.45))
    s.track(3, "drum", "C", 1.0).extend([Note(i, 40, 2, 1.0, slide=-1.3) for i in range(0, 64, 4)])
    for i in range(64):
        if i % 8 == 4:
            s.noise.append((i, "snare"))
        elif i % 2 == 0:
            s.noise.append((i, "hat"))
    return s


def jingle(notes, bass, rate=6, steps=None, patch="brass"):
    s = Song(rate, steps or max(a + c for a, b, c in notes) + 2, loop=False)
    s.track(0, patch, "C", 1.0).extend([Note(a, b, c, 1.0) for a, b, c in notes])
    s.track(4, patch, "C", 0.6).extend([Note(a, b - 12 + 4 if False else b - 5, c, 0.8) for a, b, c in notes])
    s.track(1, "bass", "C", 1.0).extend([Note(a, b, c, 1.0) for a, b, c in bass])
    return s


SONGS = {
    "title": title(),
    "yard": yard(),
    "sand": sand(),
    "frost": frost(),
    "lava": lava(),
    "cloud": cloud(),
    "boss": boss_song(),
    "clear": jingle([(0, 72, 1), (1, 76, 1), (2, 79, 1), (3, 84, 2), (6, 79, 1), (7, 84, 8)],
                    [(0, 48, 3), (3, 43, 3), (6, 48, 9)], rate=6, steps=17),
    "gameover": jingle([(0, 67, 3), (3, 66, 3), (6, 65, 3), (9, 64, 3), (12, 63, 4), (16, 60, 12)],
                       [(0, 43, 6), (6, 41, 6), (12, 39, 4), (16, 36, 12)], rate=8, steps=30, patch="pad"),
    "victory": jingle([(0, 67, 2), (2, 72, 2), (4, 76, 2), (6, 79, 4), (10, 76, 2), (12, 79, 4),
                       (16, 81, 2), (18, 79, 2), (20, 81, 2), (22, 84, 10)],
                      [(0, 48, 6), (6, 43, 6), (12, 41, 4), (16, 45, 6), (22, 48, 10)], rate=7, steps=34),
}

os.makedirs(OUT, exist_ok=True)
for name, song in SONGS.items():
    data = render(song)
    with open(os.path.join(OUT, name + ".vgm"), "wb") as f:
        f.write(data)
print("music:", ", ".join(f"{k} {len(render(v)) // 1024}K" for k, v in SONGS.items()))
