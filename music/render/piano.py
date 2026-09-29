"""
Piano: Salamander Grand Piano V3 (Yamaha C5, AB pair), five of its sixteen velocity layers,
sampled in minor thirds. Notes blend the two nearest velocity layers, are re-pitched by at most a
semitone, and are damped with a short release when the pedal or finger lifts.
"""
from __future__ import annotations

import numpy as np

from lib import SR, SAMPLES, load, trim_onset, sos, filt, eq_chain, narrow

LAYERS = [3, 5, 7, 9, 11]
ROOTS = {"C": 0, "D#": 3, "F#": 6, "A": 9}


class PianoBank:
    def __init__(self):
        self.cache = {}

    def roots(self):
        out = []
        for o in range(1, 8):
            for nm, pc in ROOTS.items():
                m = 12 * (o + 1) + pc
                if (o <= 6) or (o == 7 and nm == "C"):
                    out.append((m, f"{nm}{o}"))
        return out

    def get(self, root_name, layer, keep=None):
        k = (root_name, layer)
        if k not in self.cache:
            x = load(SAMPLES / "SalamanderGrandPiano" / "Samples" / f"{root_name}v{layer}.flac", keep_seconds=8.5)
            self.cache[k] = trim_onset(x, rel=0.002, pre=24)
        return self.cache[k]


def render(notes, n_samples, seed=11):
    rng = np.random.default_rng(seed)
    bank = PianoBank()
    roots = bank.roots()
    out = np.zeros((n_samples, 2), np.float32)
    for n in notes:
        m = n.midi
        rm, rname = min(roots, key=lambda r: (abs(r[0] - m), r[0] < m))
        rate = 2 ** ((m - rm) / 12)
        vel = float(np.clip(n.vel, 0.05, 1.0))
        lf = np.clip((vel - 0.12) / 0.78, 0, 1) * (len(LAYERS) - 1)
        l0 = int(np.floor(lf))
        l1 = min(l0 + 1, len(LAYERS) - 1)
        fr = lf - l0
        # release: dampers (none above ~F6); low notes ring a little longer
        rel = 0.28 if m < 48 else (0.20 if m < 72 else 0.16)
        undamped = m >= 89
        ring = n.dur + (rel * 5 if not undamped else 3.0)
        N = int(min(ring, 8.0 / rate) * SR)
        pos = np.arange(N) * rate
        voice = np.zeros((N, 2), np.float32)
        for li, wgt in ((l0, 1 - fr), (l1, fr)):
            if wgt < 1e-3:
                continue
            s = bank.get(rname, LAYERS[li])
            p = np.minimum(pos, len(s) - 2)
            for c in range(2):
                voice[:, c] += wgt * np.interp(p, np.arange(len(s)), s[:, c]).astype(np.float32)
        t = np.arange(N) / SR
        if not undamped:
            after = t - n.dur
            damp = np.where(after > 0, np.exp(-np.maximum(after, 0) / rel), 1.0)
            voice *= damp[:, None].astype(np.float32)
        fade = min(N, int(0.02 * SR))
        voice[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
        g = 0.55 + 0.45 * vel          # layers already carry most of the dynamic
        s0 = int(round(n.t * SR))
        e = min(n_samples, s0 + N)
        if s0 < n_samples:
            out[s0:e] += voice[:e - s0] * g
    out = narrow(out, 0.7)
    out = filt(sos("hp", 38.0), out)
    out = eq_chain(out, [("peak", 320.0, 1.0, 0.8), ("peak", 2800.0, -1.5, 0.9), ("highshelf", 7000.0, -3.0, 0.7)])
    return out
