"""
Double bass: Karoryfer Meatbass pizzicato (a 1958 Otto Rubner bass, gut-warm Spirocores), four
velocity layers and four round robins, sampled in minor thirds. Walking notes are damped by the
next note, two-feel notes ring, ghosted "skip" notes are short and dead, and a few notes slide in.
"""
from __future__ import annotations

import numpy as np

from lib import SR, SAMPLES, load, trim_onset, sos, filt, eq_chain

PCS = {"c": 0, "eb": 3, "gb": 6, "a": 9}


class BassBank:
    def __init__(self):
        self.roots = []
        for o in range(0, 5):
            for nm, pc in PCS.items():
                m = 12 * (o + 1) + pc
                if 21 <= m <= 60:
                    self.roots.append((m, f"{nm}{o}"))
        self.cache = {}

    def get(self, name, vl, rr):
        k = (name, vl, rr)
        if k not in self.cache:
            x = load(SAMPLES / "karoryfer.meatbass" / "Samples" / "pizz" / f"{name}_vl{vl}_rr{rr}.wav", mono=True)
            self.cache[k] = trim_onset(x, rel=0.01, pre=16)[:, 0]
        return self.cache[k]


def render(notes, n_samples, seed=13):
    rng = np.random.default_rng(seed)
    bank = BassBank()
    out = np.zeros(n_samples, np.float32)
    rr_count = {}
    for n in notes:
        m = n.midi
        rm, name = min(bank.roots, key=lambda r: (abs(r[0] - m), r[0] > m))
        ghost = n.tags.get("ghost")
        vel = float(np.clip(n.vel, 0.05, 1))
        vl = 1 if ghost else int(np.clip(1 + round((vel - 0.35) / 0.2), 1, 4))
        rr = rr_count.get((name, vl), int(rng.integers(1, 5)))
        rr_count[(name, vl)] = rr % 4 + 1
        s = bank.get(name, vl, rr)
        dur = 0.07 if ghost else n.dur
        rel = 0.05 if ghost else (0.09 if n.beats <= 1 else 0.16)
        if n.tags.get("final"):
            rel = 1.2
        N = int(min(dur + rel * 4, len(s) / SR - 0.01) * SR)
        t = np.arange(N) / SR
        cents = np.zeros(N)
        slide = (not ghost) and n.beats <= 1.0 and rng.random() < 0.08
        if slide:
            cents -= 100 * np.exp(-t / 0.05)
        cents += 2.5 * np.sin(2 * np.pi * 0.5 * t + rng.uniform(0, 6))       # string settling
        ratio = 2 ** ((m - rm) / 12 + cents / 1200)
        pos = np.cumsum(ratio) - ratio[0]
        pos = np.minimum(pos, len(s) - 2)
        v = np.interp(pos, np.arange(len(s)), s).astype(np.float32)
        after = t - dur
        v *= np.where(after > 0, np.exp(-np.maximum(after, 0) / rel), 1.0).astype(np.float32)
        fade = min(N, int(0.01 * SR))
        v[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        g = (0.45 + 0.55 * vel) * (0.5 if ghost else 1.0)
        if ghost:
            v = filt(sos("lp", 700.0), v)
        s0 = int(round(n.t * SR))
        e = min(n_samples, s0 + N)
        if s0 < n_samples:
            out[s0:e] += v[:e - s0] * g
    out = filt(sos("hp", 32.0), out)
    out = eq_chain(out, [("peak", 95.0, 2.0, 0.9), ("peak", 700.0, -1.5, 1.0), ("highshelf", 3500.0, -4.0, 0.7)])
    return out
