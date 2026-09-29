"""
Drums with brushes. The kit is Virtuosity Drums (a jazz club kit, overhead + room mics).

The brushes are modelled because no freely licensed brush multisample was found:
  - sweep (left hand, one slow circle per bar): noise whose level and colour follow the speed of
    the brush around the circle, with bristle crackle, played "through" the real snare: the noise
    is convolved with the kit's own snare response (a soft hit, snares on), so it carries that
    drum's head tone and wire buzz;
  - taps (right hand on 2 and 3, a swung pickup sometimes): a short slap of noise through the same
    snare response, layered with the softest real snare hits;
  - feathered bass drum on 1 (felt more than heard), hi-hat foot on 2 (and 3 in the solos),
    a brushed ride at section starts and a cymbal swell under the final fermata.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from lib import SR, SAMPLES, load, trim_onset, sos, filt, eq_chain, narrow

VD = SAMPLES / "virtuosity_drums" / "Samples"


def _mix_mics(kind, name, weights=(("oh", 0.7), ("room", 0.45))):
    parts = []
    for mic, w in weights:
        x = load(VD / mic / kind / f"{mic}_{name}.flac")
        parts.append(x * w)
    n = max(len(p) for p in parts)
    out = np.zeros((n, 2), np.float32)
    for p in parts:
        out[:len(p)] += p if p.shape[1] == 2 else np.repeat(p, 2, axis=1)
    return trim_onset(out, rel=0.003, pre=16)


def snare_response():
    """Mono impulse response of the snare (soft centre hit, snares on), stick click softened."""
    x = load(VD / "snaremic" / "snare" / "snaremic_snare_center_vl4.flac", mono=True)[:, 0]
    x = trim_onset(x[:, None], rel=0.01, pre=8)[:, 0]
    ir = x[: int(0.32 * SR)].copy()
    ir[: int(0.002 * SR)] *= np.linspace(0.2, 1, int(0.002 * SR))
    ir *= np.exp(-np.arange(len(ir)) / (0.07 * SR))   # keep the head's ring short
    ir = filt(sos("lp", 7000.0), ir)
    return ir / np.sqrt(np.sum(ir ** 2))


def render(events, n_samples, seed=17):
    rng = np.random.default_rng(seed)
    out = np.zeros((n_samples, 2), np.float32)
    brush_src = np.zeros(n_samples, np.float32)   # excitation that goes through the snare response

    # ---- sweeps ----
    for e in [e for e in events if e["kind"] == "sweep"]:
        a, b = int(e["t"] * SR), int(e["t1"] * SR)
        N = b - a + int(0.25 * SR)
        t = np.arange(N) / SR
        T = (b - a) / SR
        ph = np.clip(t / T, 0, 1.08)
        # speed around the circle: slow at the top, fast across the bottom, a push on each beat
        speed = 0.38 + 0.62 * np.sin(np.pi * ph) ** 2 + 0.15 * np.sin(2 * np.pi * 3 * ph - 0.6) ** 2
        speed *= np.clip(t / 0.06, 0, 1) * np.clip((N / SR - t) / 0.2, 0, 1)
        speed *= 1 + 0.08 * rng.standard_normal() + 0.06 * np.sin(2 * np.pi * rng.uniform(0.3, 0.8) * t)
        hiss = rng.standard_normal(N).astype(np.float32)
        hiss = filt(sos("bp", (900.0, 9000.0)), hiss)
        # bristle crackle: sparse little impulses, denser when the brush moves fast
        crackle = (rng.random(N) < (speed * 180 / SR)).astype(np.float32) * rng.standard_normal(N).astype(np.float32)
        crackle = filt(sos("hp", 2500.0), crackle) * 0.6
        lvl = e["vel"] * 0.022
        brush_src[a:a + N] += ((hiss * 0.8 + crackle) * speed.astype(np.float32) * lvl)[: max(0, min(N, n_samples - a))]

    # ---- taps ----
    snare_soft = [_mix_mics("snare", f"snare_center_vl{v}") for v in (1, 2, 3, 4, 5, 6)]
    for e in [e for e in events if e["kind"] == "tap"]:
        s0 = int(e["t"] * SR)
        v = float(np.clip(e["vel"], 0.05, 1))
        N = int(0.22 * SR)
        t = np.arange(N) / SR
        env = np.exp(-t / 0.018) * 0.7 + np.exp(-t / 0.075) * 0.3
        env *= np.clip(t / 0.0015, 0, 1)
        slap = filt(sos("bp", (600.0, 8000.0)), rng.standard_normal(N).astype(np.float32)) * env.astype(np.float32)
        end = min(n_samples, s0 + N)
        if s0 < n_samples:
            brush_src[s0:end] += (slap * 0.17 * v ** 1.3)[: end - s0]
        hit = snare_soft[int(np.clip(v * 6, 0, 5))]
        hit = filt(sos("lp", 4500.0), hit[: int(0.5 * SR)])
        end = min(n_samples, s0 + len(hit))
        if s0 < n_samples:
            out[s0:end] += hit[: end - s0] * 0.15 * v

    # the brush excitation, played through the snare
    ir = snare_response()
    wet = signal.oaconvolve(brush_src, ir)[:n_samples].astype(np.float32)
    dry_air = filt(sos("hp", 3000.0), brush_src)          # a touch of the wires' direct fizz
    brush = wet * 0.85 + dry_air * 0.35
    # slight stereo spread for the brush (decorrelated by a few ms)
    d = int(0.0021 * SR)
    out[:, 0] += brush
    out[d:, 1] += brush[:-d] * 0.96

    # ---- kick, hat, ride, swell ----
    kicks = [_mix_mics("kick", f"kick_snoff_vl1_rr{r}", (("oh", 0.5), ("room", 0.4), ("kickmic", 0.35))) for r in (1, 2, 3, 4)]
    hats = [_mix_mics("hh", f"hh_pedal_vl1_rr{r}") for r in (1, 2, 3)]
    rides = [_mix_mics("ride", f"ride_ride_vl1_rr{r}") for r in (1, 2, 3, 4)]
    lp_kick = sos("lp", 220.0)
    for e in events:
        k = e["kind"]
        s0 = int(e["t"] * SR)
        if k == "kick":
            x = filt(lp_kick, kicks[int(rng.integers(0, 4))][: int(0.8 * SR)]) * (0.9 * e["vel"])
        elif k == "hat":
            x = hats[int(rng.integers(0, 3))][: int(0.6 * SR)] * (0.45 * e["vel"])
        elif k == "ride":
            x = rides[int(rng.integers(0, 4))][: int(6 * SR)].copy()
            x[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]       # brush, not stick
            x = filt(sos("lp", 7500.0), x) * (0.30 * e["vel"])
        elif k == "swell":
            L = int(7.0 * SR)
            x = rides[0][int(0.25 * SR):int(0.25 * SR) + L].copy()        # the cymbal's bloom, no attack
            x = np.pad(x, ((0, L - len(x)), (0, 0)))
            t = np.arange(L) / SR
            env = smooth_swell(t)
            noise = filt(sos("bp", (3000.0, 11000.0)), rng.standard_normal((L, 2)).astype(np.float32))
            x = (x * 0.35 + noise * 0.05) * env[:, None].astype(np.float32)
            x = filt(sos("lp", 8000.0), x) * e["vel"]
        else:
            continue
        end = min(n_samples, s0 + len(x))
        if 0 <= s0 < n_samples:
            out[s0:end] += x[: end - s0]
    out = narrow(out, 0.8)
    out = filt(sos("hp", 35.0), out)
    out = eq_chain(out, [("highshelf", 9000.0, -2.0, 0.7)])
    return out


def smooth_swell(t):
    rise = np.clip(t / 1.4, 0, 1) ** 2
    fall = np.exp(-np.maximum(t - 1.4, 0) / 1.6)
    return rise * fall
