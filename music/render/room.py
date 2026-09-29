"""
The room: a synthetic stereo impulse response for a warm, wood-panelled small hall (the sound of
the quartet heard from the square, a little enclosed by the bandstand roof).

Early reflections from a simple image-source sketch of a 11 x 8 x 4.5 m room, then a dense late
tail made of decorrelated noise split into octave bands, each decaying at its own rate
(RT60 about 1.9 s in the low mids falling to 0.6 s at 8 kHz), so the tail darkens as it fades.
The room stem is the reverb return only: every instrument's send, convolved with this response.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from lib import SR, sos, filt

BANDS = [(63, 2.0), (125, 2.0), (250, 1.9), (500, 1.8), (1000, 1.6), (2000, 1.3), (4000, 0.95), (8000, 0.6)]


def impulse_response(seed=5, length=3.4, predelay=0.014):
    rng = np.random.default_rng(seed)
    N = int(length * SR)
    t = np.arange(N) / SR
    ir = np.zeros((N, 2), np.float64)
    # early reflections (image sources, first and second order), absorbed a little per bounce
    room = np.array([11.0, 8.0, 4.5])
    src = np.array([4.2, 3.0, 1.4])
    lis = [np.array([6.3, 5.6, 1.6]), np.array([6.7, 5.6, 1.6])]
    c = 343.0
    for ch in range(2):
        for nx in range(-2, 3):
            for ny in range(-2, 3):
                for nz in range(-1, 2):
                    order = abs(nx) + abs(ny) + abs(nz)
                    if order == 0 or order > 3:
                        continue
                    img = np.array([
                        nx * room[0] + (src[0] if nx % 2 == 0 else room[0] - src[0]),
                        ny * room[1] + (src[1] if ny % 2 == 0 else room[1] - src[1]),
                        nz * room[2] + (src[2] if nz % 2 == 0 else room[2] - src[2]),
                    ])
                    d = np.linalg.norm(img - lis[ch])
                    k = int((predelay + d / c) * SR)
                    if k < N:
                        ir[k, ch] += (0.72 ** order) / max(d, 1.0) * (1 if rng.random() < 0.7 else -1)
    ir = signal.sosfilt(sos("lp", 5000.0), ir, axis=0)
    # late tail
    late = np.zeros((N, 2))
    onset = predelay + 0.018
    build = np.clip((t - onset) / 0.045, 0, 1) ** 2
    for fc, rt in BANDS:
        lo, hi = fc / np.sqrt(2), min(fc * np.sqrt(2), SR / 2 * 0.95)
        n = rng.standard_normal((N, 2))
        b = signal.sosfilt(signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="bandpass", output="sos"), n, axis=0)
        late += b * np.exp(-6.91 * np.maximum(t - onset, 0) / rt)[:, None]
    late *= build[:, None] * 0.055
    ir = ir + late
    fade = int(0.3 * SR)
    ir[-fade:] *= np.linspace(1, 0, fade)[:, None]
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    return ir.astype(np.float32)


def reverb(send_stereo: np.ndarray, ir: np.ndarray, ir_cross: np.ndarray) -> np.ndarray:
    """Stereo in, stereo out: L->L and R->R through one response, plus a cross-feed through a
    second, decorrelated response so that centred (mono) sends still open into a wide room."""
    n = len(send_stereo)
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        out[:, c] += signal.oaconvolve(send_stereo[:, c], ir[:, c])[:n] * 0.8
        out[:, c] += signal.oaconvolve(send_stereo[:, 1 - c], ir_cross[:, c])[:n] * 0.45
    # tame the room's low end so it stays clear
    return filt(sos("hp", 110.0), out)
