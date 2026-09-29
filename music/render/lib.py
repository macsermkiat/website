"""Shared helpers for the offline renderer: paths, sample loading and caching, filters, envelopes."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
MUSIC = Path(__file__).resolve().parents[1]
REPO = MUSIC.parent
SAMPLES = MUSIC / ".samples"
CACHE = MUSIC / ".cache"
OUT = MUSIC / "out"
SITE_AUDIO = REPO / "site" / "public" / "audio"
REVIEW = REPO / "review" / "round-1" / "music"
sys.path.insert(0, str(MUSIC / "score"))

CACHE.mkdir(exist_ok=True)


def load(path, keep_seconds=None, mono=False) -> np.ndarray:
    """Load an audio file as float32 (n, ch) at SR. Resampled copies are cached in music/.cache."""
    path = Path(path)
    key = hashlib.md5(f"{path}|{keep_seconds}|{mono}|v2".encode()).hexdigest()[:16]
    cp = CACHE / f"{path.stem}_{key}.npy"
    if cp.exists():
        return np.load(cp)
    x, sr = sf.read(str(path), always_2d=True, dtype="float32")
    if sr != SR:
        g = np.gcd(SR, sr)
        x = signal.resample_poly(x, SR // g, sr // g, axis=0).astype(np.float32)
    if mono:
        x = x.mean(axis=1, keepdims=True)
    if keep_seconds:
        x = x[: int(keep_seconds * SR)]
    np.save(cp, x)
    return x


def trim_onset(x: np.ndarray, rel=0.004, pre=48) -> np.ndarray:
    a = np.abs(x).max(axis=1)
    thr = a.max() * rel
    i = int(np.argmax(a > thr))
    return x[max(0, i - pre):]


def sos(kind, f, order=2, sr=SR):
    if kind == "bp":
        return signal.butter(order, [f[0] / (sr / 2), f[1] / (sr / 2)], btype="bandpass", output="sos")
    return signal.butter(order, f / (sr / 2), btype={"lp": "lowpass", "hp": "highpass"}[kind], output="sos")


def filt(s, x):
    return signal.sosfilt(s, x, axis=0).astype(np.float32)


def biquad(kind, f0, gain_db=0.0, q=0.707, sr=SR):
    """RBJ cookbook biquads as an sos row: 'peak', 'lowshelf', 'highshelf'."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    if kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sa)]
        a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sa]
    elif kind == "highshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
        a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    else:
        raise ValueError(kind)
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return np.concatenate([b, a])[None, :]


def eq_chain(x, bands):
    s = np.concatenate([biquad(*b) for b in bands], axis=0)
    return signal.sosfilt(s, x, axis=0).astype(np.float32)


def add_into(buf: np.ndarray, x: np.ndarray, start: int):
    if start >= len(buf):
        return
    if start < 0:
        x = x[-start:]
        start = 0
    n = min(len(x), len(buf) - start)
    if n > 0:
        buf[start:start + n] += x[:n]


def pan_gains(p):
    """Equal-power pan, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def to_stereo(x, pan=0.0):
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[1] == 1:
        gl, gr = pan_gains(pan)
        return np.concatenate([x * gl, x * gr], axis=1).astype(np.float32) * np.sqrt(2)
    return x


def narrow(x, width):
    """Mid/side width control for a stereo signal (1 = unchanged, 0 = mono)."""
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1]) * width
    return np.stack([m + s, m - s], axis=1).astype(np.float32)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-12))
