"""Synthesize the game's chiptune sound set (standard library only).

    python tools/synth_sounds.py [out_dir]      (default: assets/sounds)

Writes <name>.wav for every sound the game plays, plus pitch/timbre variants
under fun/<name>/ that FUN mode picks from at random. All melodies are
original compositions.
"""

import math
import os
import random
import struct
import sys
import wave

RATE = 22050
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOTE_INDEX = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}


def freq(note: str) -> float:
    """'A4' -> 440.0"""
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((NOTE_INDEX[name] + (octave - 4) * 12) / 12)


# ---------------------------------------------------------------------------
# Oscillators and envelopes
# ---------------------------------------------------------------------------
def osc(wave_name: str, phase: float) -> float:
    p = phase % 1.0
    if wave_name == "square":
        return 1.0 if p < 0.5 else -1.0
    if wave_name == "pulse":
        return 1.0 if p < 0.25 else -1.0
    if wave_name == "triangle":
        return 4 * abs(p - 0.5) - 1
    if wave_name == "saw":
        return 2 * p - 1
    return math.sin(2 * math.pi * p)


def tone(freq_fn, seconds: float, wave_name="square", volume=0.3, attack=0.005, release=0.03, vibrato=0.0):
    """Render one voice; freq_fn(t) gives the frequency at time t."""
    n = int(seconds * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = freq_fn(t) * (1 + vibrato * math.sin(2 * math.pi * 6 * t))
        phase += f / RATE
        env = min(1.0, t / attack if attack else 1.0, (seconds - t) / release if release else 1.0)
        out.append(osc(wave_name, phase) * volume * max(env, 0.0))
    return out


def note(name, seconds, **kw):
    f = freq(name)
    return tone(lambda _t: f, seconds, **kw)


def rest(seconds):
    return [0.0] * int(seconds * RATE)


def sweep(f0, f1, seconds, curve="exp", **kw):
    if curve == "exp":
        return tone(lambda t: f0 * (f1 / f0) ** (t / seconds), seconds, **kw)
    return tone(lambda t: f0 + (f1 - f0) * t / seconds, seconds, **kw)


def seq(notes, step, **kw):
    """notes: list of note names, '.' for rest, or (name, steps) tuples."""
    out = []
    for item in notes:
        name, steps = item if isinstance(item, tuple) else (item, 1)
        out += rest(step * steps) if name == "." else note(name, step * steps, **kw)
    return out


def mix(*tracks):
    length = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(length)]


def noise(seconds, volume=0.2):
    rng = random.Random(7)
    n = int(seconds * RATE)
    return [rng.uniform(-1, 1) * volume * (1 - i / n) for i in range(n)]


# ---------------------------------------------------------------------------
# Sound designs. Each takes pitch (multiplier) and wave (lead timbre).
# ---------------------------------------------------------------------------
def transpose(notes, pitch):
    if pitch == 1:
        return notes
    shift = round(12 * math.log2(pitch))
    names = list(NOTE_INDEX)

    def move(n):
        if n == ".":
            return n
        idx = names.index(n[:-1]) + shift
        return names[idx % 12] + str(int(n[-1]) + idx // 12)

    return [(move(n[0]), n[1]) if isinstance(n, tuple) else move(n) for n in notes]


def intro(pitch=1.0, wave_name="pulse"):
    step = 0.13
    lead = ["A4", "C5", "E5", "A5", "G5", "E5", "C5", "E5",
            "F5", "A5", "C6", "A5", "G5", ".", "E5", ".",
            "D5", "F5", "A5", "D6", "C6", "A5", "E5", "C5",
            "B4", "D5", "G5", "B5", ("A5", 4)]
    bass = ["A2", ".", "A3", ".", "C3", ".", "C3", ".",
            "F2", ".", "F3", ".", "C3", ".", "G2", ".",
            "D3", ".", "D3", ".", "A2", ".", "A2", ".",
            "G2", ".", "G2", ".", ("A2", 4)]
    return mix(seq(transpose(lead, pitch), step, wave_name=wave_name, volume=0.22),
               seq(transpose(bass, pitch), step, wave_name="triangle", volume=0.35))


def win(pitch=1.0, wave_name="pulse"):
    step = 0.12
    lead = ["C5", "E5", "G5", "C6", ".", "G5", "C6", ("E6", 8)]
    bass = [("C3", 2), ("G3", 2), ("C3", 2), ("C4", 8)]
    return mix(seq(transpose(lead, pitch), step, wave_name=wave_name, volume=0.22, vibrato=0.004),
               seq(transpose(bass, pitch), step, wave_name="triangle", volume=0.35))


def lose(pitch=1.0, wave_name="square"):
    step = 0.28
    lead = ["E5", "D5", "C5", "B4", ("A4", 2), ".", ("A3", 4)]
    return seq(transpose(lead, pitch), step, wave_name=wave_name, volume=0.22, vibrato=0.01, release=0.12)


def death(pitch=1.0, wave_name="square"):
    fall = sweep(900 * pitch, 110 * pitch, 1.3, wave_name=wave_name, volume=0.22, vibrato=0.06, release=0.05)
    blip = note("C4", 0.1, wave_name="square", volume=0.2)
    if pitch != 1:
        blip = sweep(freq("C4") * pitch, freq("C4") * pitch, 0.1, wave_name="square", volume=0.2)
    return fall + rest(0.12) + blip + rest(0.08) + blip


def seed(pitch=1.0, wave_name="triangle"):
    return sweep(300 * pitch, 620 * pitch, 0.075, wave_name=wave_name, volume=0.35, release=0.02)


def siren():
    # Two full wobbles in 1.6 s so the loop point is seamless.
    return tone(lambda t: 430 + 150 * math.sin(2 * math.pi * t / 0.8), 1.6, wave_name="triangle", volume=0.22, attack=0, release=0)


def frightened():
    return tone(lambda t: 190 + 220 * ((t / 0.125) % 1.0), 1.0, wave_name="square", volume=0.11, attack=0, release=0)


def eat_fruit():
    return seq(["E5", "G5", "C6", "E6"], 0.065, wave_name="pulse", volume=0.25)


def eat_ghost():
    return sweep(180, 1500, 0.42, wave_name="square", volume=0.2)


def cheat():
    sparkle = seq(["C6", "E6", "G6", "C7", "G6", "E6", "C7"], 0.07, wave_name="triangle", volume=0.3)
    echo = rest(0.1) + [s * 0.4 for s in sparkle]
    return mix(sparkle, echo)


def click():
    return mix(note("C6", 0.03, wave_name="square", volume=0.15, release=0.02), noise(0.03, 0.08))


SOUNDS = {
    "intro": intro,
    "back": siren,
    "frightened": frightened,
    "seed": seed,
    "eat_fruit": eat_fruit,
    "eat_ghost": eat_ghost,
    "death": death,
    "win": win,
    "lose": lose,
    "cheat": cheat,
    "click": click,
}

# FUN mode variants: (pitch, lead wave)
FUN_VARIANTS = {
    name: [(0.75, "saw"), (1.5, "square"), (1.26, "triangle")]
    for name in ("intro", "death", "seed", "win", "lose")
}


def write_wav(path, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = min(1.0, 0.9 / peak)
    frames = b"".join(struct.pack("<h", int(max(-1, min(1, s * gain)) * 32767)) for s in samples)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(frames)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "sounds")
    for name, fn in SOUNDS.items():
        write_wav(os.path.join(out_dir, f"{name}.wav"), fn())
    for name, variants in FUN_VARIANTS.items():
        for i, (pitch, wave_name) in enumerate(variants, 1):
            write_wav(os.path.join(out_dir, "fun", name, f"{i}.wav"), SOUNDS[name](pitch, wave_name))
    print(f"wrote {len(SOUNDS)} sounds and {sum(map(len, FUN_VARIANTS.values()))} fun variants to {out_dir}")


if __name__ == "__main__":
    main()
