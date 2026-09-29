"""
Drums with brushes.

Round 1, pass 4: the brushes are recorded. Karoryfer's Swirly Drums (CC0) is a jazz kit played with
brushes, and it includes the one thing most kits leave out: long recordings of the brush stirring
circles on the snare head (four dynamic levels, four takes, two mics). The kit plays:
  - sweep (left hand, one slow circle per bar): a random stretch of a recorded stir at the dynamic
    level nearest the bar's, shaped by the speed of the brush around the circle (slow at the top,
    faster across the bottom, a push on each beat), crossfaded bar to bar, so the texture never
    repeats and is never cut;
  - taps (right hand on 2 and 3, a swung pickup sometimes): the softest recorded brush hits on the
    snare (12 velocity layers, 4 takes, top and bottom mics), with an occasional "dig", where the
    brush stays on the head and mutes it;
  - hi-hat foot chick on 2 (and 3 in the solos) and the brushed ride at section starts, all from
    the same kit; the ride's bloom, without its attack, is the swell under the final fermata;
  - feathered bass drum on 1, felt more than heard: Virtuosity Drums' jazz kick (CC0), low-passed.
The round-1 model (noise played through a sampled snare response) is kept as render_modelled() for
A/B: render.py --brushes modelled.
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


def render_modelled(events, n_samples, seed=17):
    """Round 1 passes 1-3: modelled brushes (noise through the snare response). Kept for A/B."""
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


# --------------------------------------------------------------------------------------------
# recorded brushes: Karoryfer Swirly Drums
# --------------------------------------------------------------------------------------------
SW = SAMPLES / "karoryfer.swirly-drums" / "Samples"


def _sw(sub, name):
    return load(SW / sub / name, mono=True)[:, 0]


def _two_mics(sub, stem, top="top", btm="btm", w_top=1.0, w_btm=0.55):
    """A hit from the top (brush side) and bottom (snare wires) mics, onset-aligned."""
    a = _sw(sub, f"{stem}_{top}.wav")
    b = _sw(sub, f"{stem}_{btm}.wav")
    n = max(len(a), len(b))
    x = np.zeros(n, np.float32)
    x[:len(a)] += a * w_top
    x[:len(b)] += b * w_btm
    return trim_onset(x[:, None], rel=0.02, pre=24)[:, 0]


def _stirs():
    """Stirs by dynamic level (1-4): each a mono mix of the wires mic and the skin mic."""
    out = {}
    for dl in (1, 2, 3, 4):
        takes = []
        for rr in (1, 2, 3, 4):
            a = _sw("snare_stir", f"stir_dl{dl}_rr{rr}.wav")
            b = _sw("snare_stir", f"stir_dl{dl}_skin_rr{rr}.wav")
            n = min(len(a), len(b))
            takes.append((a[:n] * 0.8 + b[:n] * 0.6).astype(np.float32))
        out[dl] = takes
    # level-match the four dynamic levels to a gentle ladder, so a bar's velocity picks the colour
    # of that level (a harder stir is brighter) while the level itself follows the velocity
    for dl, takes in out.items():
        r = np.sqrt(np.mean(np.concatenate(takes)[: 10 * SR] ** 2)) + 1e-9
        out[dl] = [t / r * 0.05 for t in takes]
    return out


def render(events, n_samples, seed=17, kit="swirly"):
    if kit == "modelled":
        return render_modelled(events, n_samples, seed)
    rng = np.random.default_rng(seed)
    out = np.zeros((n_samples, 2), np.float32)
    snare = np.zeros(n_samples, np.float32)       # mono snare (stirs, taps, digs), spread at the end

    # ---- sweeps: recorded stirs, one circle per bar ----
    stirs = _stirs()
    xf = int(0.30 * SR)
    for e in [e for e in events if e["kind"] == "sweep"]:
        a, b = int(e["t"] * SR), int(e["t1"] * SR)
        N = b - a + xf
        v = float(np.clip(e["vel"], 0.05, 1.0))
        dl = int(np.clip(round(1 + v * 3.2 - 0.6), 1, 4))
        src = stirs[dl][int(rng.integers(0, 4))]
        o = int(rng.uniform(0.3 * SR, len(src) - N - 0.3 * SR))
        x = src[o:o + N].copy()
        t = np.arange(N) / SR
        T = (b - a) / SR
        ph = np.clip(t / T, 0, 1.1)
        # the circle: slow at the top, faster across the bottom, a small push on each beat
        speed = 0.62 + 0.38 * np.sin(np.pi * ph) ** 2 + 0.10 * np.sin(2 * np.pi * 3 * ph - 0.6) ** 2
        # bar-to-bar crossfade (equal power) so the stir never stops
        fin = np.sin(0.5 * np.pi * np.clip(t / (xf / SR), 0, 1))
        fout = np.cos(0.5 * np.pi * np.clip((t - T) / (xf / SR), 0, 1))
        env = speed * fin * fout * (0.35 + 0.9 * v) * 0.117
        seg = (x * env).astype(np.float32)
        end = min(n_samples, a + N)
        if 0 <= a < n_samples:
            snare[a:end] += seg[: end - a]

    # ---- taps: recorded brush hits (and the occasional dig) ----
    hits = {vl: [_two_mics("snare_main", f"snare_hit_vl{vl}_rr{rr}") for rr in (1, 2, 3, 4)] for vl in range(1, 7)}
    digs = {vl: [_two_mics("snare_dig", f"snare_dig_vl{vl}_rr{rr}") for rr in (1, 2, 3, 4)] for vl in (1, 2, 3)}
    ref = np.sqrt(np.mean(hits[3][0][: int(0.1 * SR)] ** 2)) + 1e-9
    for e in [e for e in events if e["kind"] == "tap"]:
        s0 = int(e["t"] * SR)
        v = float(np.clip(e["vel"], 0.05, 1))
        vl = int(np.clip(round(v * 6.5), 1, 6))
        if rng.random() < 0.18 and vl <= 3:
            x = digs[vl][int(rng.integers(0, 4))][: int(0.9 * SR)]
        else:
            x = hits[vl][int(rng.integers(0, 4))][: int(0.9 * SR)]
        x = x / ref * 0.050 * v ** 1.2
        end = min(n_samples, s0 + len(x))
        if 0 <= s0 < n_samples:
            snare[s0:end] += x[: end - s0]

    # the snare sits a little left of centre. Panned only, with no delayed copy for width: the site
    # folds the drum stem to mono, and a delayed copy would comb-filter the brushes there (notches
    # every 550 Hz, as the round-1 model had); the room gives the width instead
    snare = filt(sos("hp", 70.0), snare)
    out += to_pan(snare, -0.12)

    # ---- kick (Virtuosity), hat foot, brushed ride, swell (Swirly) ----
    kicks = [_mix_mics("kick", f"kick_snoff_vl1_rr{r}", (("oh", 0.5), ("room", 0.4), ("kickmic", 0.35))) for r in (1, 2, 3, 4)]
    hats = {vl: [_sw("hat_foot", f"hh_foot_vl{vl}_rr{rr}.wav") for rr in (1, 2, 3, 4)] for vl in (1, 2, 3, 4)}
    rides = {vl: [_sw("ride", f"ride_vl{vl}_rr{rr}.wav") for rr in (1, 2, 3, 4)] for vl in (2, 4, 6)}
    lp_kick = sos("lp", 220.0)
    hat_ref = np.sqrt(np.mean(hats[2][0] ** 2)) + 1e-9
    ride_ref = np.sqrt(np.mean(rides[4][0][: SR] ** 2)) + 1e-9
    for e in events:
        k = e["kind"]
        s0 = int(e["t"] * SR)
        v = float(np.clip(e["vel"], 0.02, 1))
        if k == "kick":
            x = filt(lp_kick, kicks[int(rng.integers(0, 4))][: int(0.8 * SR)]) * (0.9 * v)
        elif k == "hat":
            vl = int(np.clip(round(v * 5), 1, 4))
            h = hats[vl][int(rng.integers(0, 4))][: int(0.6 * SR)]
            x = to_pan(h / hat_ref * 0.0018 * v, 0.35)
        elif k == "ride":
            vl = 2 if v < 0.35 else (4 if v < 0.55 else 6)
            r = rides[vl][int(rng.integers(0, 4))][: int(6 * SR)]
            x = to_pan(filt(sos("lp", 9000.0), r) / ride_ref * 0.0075 * v, -0.4)
        elif k == "swell":
            L = int(7.0 * SR)
            r = rides[6][0]
            x = r[int(0.35 * SR):int(0.35 * SR) + L].copy()                 # the bloom, no attack
            x = np.pad(x, (0, L - len(x)))
            t = np.arange(L) / SR
            x = filt(sos("lp", 8000.0), x * smooth_swell(t).astype(np.float32)) / ride_ref * 0.0225 * v
            x = to_pan(x, -0.4)
        else:
            continue
        end = min(n_samples, s0 + len(x))
        if 0 <= s0 < n_samples:
            out[s0:end] += x[: end - s0]
    out = narrow(out, 0.8)
    out = filt(sos("hp", 35.0), out)
    out = eq_chain(out, [("highshelf", 9000.0, -2.0, 0.7)])
    return out


def to_pan(x, p):
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1).astype(np.float32) * np.sqrt(2)
