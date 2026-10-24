#!/usr/bin/env python3
"""Synthesize the sound effects as WAV files (res/sfx/*.wav). rescomp converts them to
8-bit PCM for the XGM2 driver, which plays them on FM channel 6 next to the music.

Usage: make_sfx.py OUTDIR
"""
import math
import os
import random
import struct
import sys
import wave

OUT = sys.argv[1] if len(sys.argv) > 1 else "res/sfx"
RATE = 22050
rnd = random.Random(7)


def env(t, attack, decay):
    return min(1.0, t / attack) * math.exp(-t / decay) if attack else math.exp(-t / decay)


def lowpass(xs, cutoff_fn):
    out, y = [], 0.0
    for i, x in enumerate(xs):
        fc = cutoff_fn(i / RATE)
        a = 1 - math.exp(-2 * math.pi * fc / RATE)
        y += a * (x - y)
        out.append(y)
    return out


def tone(freq_fn, dur, wave_fn=math.sin, amp_fn=lambda t: 1.0):
    out, ph = [], 0.0
    for i in range(int(dur * RATE)):
        t = i / RATE
        ph += 2 * math.pi * freq_fn(t) / RATE
        out.append(wave_fn(ph) * amp_fn(t))
    return out


def square(ph):
    return 1.0 if math.sin(ph) >= 0 else -1.0


def mix(*parts):
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def save(name, xs, gain=1.0):
    peak = max(1e-9, max(abs(x) for x in xs))
    xs = [x / peak * 0.95 * gain for x in xs]
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x)) * 32767)) for x in xs))


os.makedirs(OUT, exist_ok=True)

# explosion: a deep thump under a burst of noise that closes down
dur = 0.85
noise = [rnd.uniform(-1, 1) for _ in range(int(dur * RATE))]
burst = lowpass(noise, lambda t: 5000 * math.exp(-t * 5) + 150)
burst = [x * env(i / RATE, 0.004, 0.22) * 2.2 for i, x in enumerate(burst)]
thump = tone(lambda t: 95 * math.exp(-t * 6) + 38, dur, amp_fn=lambda t: env(t, 0.002, 0.18))
crackle = [rnd.uniform(-1, 1) * (1 if rnd.random() < 0.04 else 0) * env(i / RATE, 0.05, 0.25) * 0.6
           for i in range(int(dur * RATE))]
save("boom", mix(burst, [x * 1.3 for x in thump], crackle))

# placing a bomb: a soft wooden knock
save("place", mix(tone(lambda t: 220 * math.exp(-t * 18) + 110, 0.12, amp_fn=lambda t: env(t, 0.001, 0.035)),
                  [rnd.uniform(-1, 1) * env(i / RATE, 0.0005, 0.006) * 0.4 for i in range(int(0.02 * RATE))]), 0.8)

# power-up: a bright upward arpeggio
notes = [72, 76, 79, 84]
seq = []
for k, n in enumerate(notes):
    f = 440 * 2 ** ((n - 69) / 12)
    seq += tone(lambda t, f=f: f, 0.055, lambda ph: 0.6 * square(ph) + 0.4 * math.sin(2 * ph),
                lambda t: env(t, 0.002, 0.08))
save("pickup", seq, 0.75)

# extra life: a shimmering sparkle that rises and rings out
seq = []
for k, n in enumerate([76, 79, 84, 88, 91, 96]):
    f = 440 * 2 ** ((n - 69) / 12)
    last = k == 5
    seq += tone(lambda t, f=f: f * (1 + 0.006 * math.sin(t * 40)), 0.30 if last else 0.05,
                lambda ph: math.sin(ph) + 0.35 * math.sin(3 * ph), lambda t, last=last: env(t, 0.002, 0.16 if last else 0.06))
save("heart", seq, 0.8)

# losing a life: a falling, wobbling whine
save("die", tone(lambda t: 700 * math.exp(-t * 2.6) * (1 + 0.06 * math.sin(t * 60)), 0.75,
                 lambda ph: 0.7 * square(ph) + 0.3 * math.sin(ph), lambda t: env(t, 0.005, 0.4)), 0.7)

# the boss is hit: a metal clang and a low growl
clang = mix(*[tone(lambda t, f=f: f, 0.5, amp_fn=lambda t, d=d: env(t, 0.001, d))
              for f, d in ((523, 0.18), (1247, 0.1), (1871, 0.06), (311, 0.25))])
growl = tone(lambda t: 90 + 20 * math.sin(t * 30), 0.5, square, lambda t: env(t, 0.02, 0.2) * 0.4)
save("bosshit", mix(clang, growl))

# clock tick in the last seconds: a short wood block
save("tick", tone(lambda t: 1800, 0.04, amp_fn=lambda t: env(t, 0.0005, 0.008)), 0.5)

# menu move and confirm
save("menu", tone(lambda t: 880, 0.05, square, lambda t: env(t, 0.001, 0.02)), 0.5)
save("select", tone(lambda t: 660 if t < 0.05 else 990, 0.14, square, lambda t: env(t, 0.001, 0.07)), 0.6)
print("sfx written")
