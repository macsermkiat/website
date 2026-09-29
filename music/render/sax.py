"""
The tenor: a soft, low subtone voice (think Ben Webster or Stan Getz at a whisper).

Each note is built from three layers, all following the same performed pitch curve:
  1. a General MIDI tenor-sax sample for that exact semitone (MusyngKite by default, FluidR3 as
     the alternative, see BANKS), with its baked-in vibrato taken out, sustained by splicing
     pieces of its own steady tone in a random order, so a long note never repeats a fixed loop
     the way an organ does;
  2. a "subtone body": the sample's own fundamental and second partial, lifted by a low-pass that
     tracks the note, for the round, hollow core of a subtoned low note;
  3. breath: band-limited noise, gated by the pitch period (the airy fuzz of a subtone) with a
     small puff on every attack, more of it when playing quietly.
Articulation: slow, breathy attacks (130-220 ms from silence; 55 ms legato crossfades inside a
phrase), vibrato that blooms late in long notes (4.7-5.3 Hz, 13-20 cents), scoops into phrase
starts and leaps, occasional falls, audible breath intakes before every phrase that follows a
silence of INHALE_GAP (0.35 s) or more; a phrase's last note releases in at most half the rest that
follows it, so short rests are heard as breaths.
Air (round 1, pass 3): a second, low breath path at 2.4-7 kHz bypasses the dark EQ and the final
5.2 kHz low-pass, so the subtone reads as breathy rather than muffled (AIR sets its level).
Dynamics (round 1, pass 2): each phrase is shaped in breath groups of 2.5-4.5 s. A group's
pressure rises from about -5.5 to -8 dB to its most important note and relaxes after it, the
last group of a phrase falls to about -10 to -13 dB, long notes swell by 2.5-4 dB inside that,
and phrase-final notes fade into breath. Brightness and the breath share follow that pressure, so
soft moments are darker and airier. The whole voice goes through a dark EQ: warm low-mids, a cut
in the honk region, soft top.
"""
from __future__ import annotations

import base64
import io
import math
import re

import numpy as np
import soundfile as sf

from lib import SR, SAMPLES, CACHE, sos, filt, eq_chain, smoothstep

NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
BREATH = 1.2      # breath layer level (650-2600 Hz, inside the dark channel EQ)
CORE = 0.9        # subtone body level (relative to the sample)
AIR = 1.0         # the air path: breath noise at 2.4-7 kHz that bypasses the final low-pass (0 = off)
INHALE_GAP = 0.35 # an audible breath intake before any phrase that follows at least this much silence (s)


def _name(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


# Tenor sample banks (gleitz/midi-js-soundfonts renders of each soundfont, one file per semitone).
BANKS = {
    "fluidr3": "FluidR3_GM",      # Frank Wen, CC BY 3.0 (MIT in the FluidSynth distribution)
    "musyngkite": "MusyngKite",   # CC BY-SA 3.0: share-alike would extend to the rendered stems
}
# MusyngKite won the round-1 A/B on every measured proxy (ab_tenor.py, music/out/ab/ab.json): its
# samples move more inside a held note, change timbre less from one semitone to the next, carry
# the player's own level movement, and are darker at the source. Its CC BY-SA 3.0 licence makes
# the sax stem, the room stem and the mix share-alike (see CREDITS.md). FluidR3 (CC BY 3.0) is
# one flag away: render.py --sax-bank fluidr3.
DEFAULT_BANK = "musyngkite"
# Tone per bank: the dark/bright low-pass corners and the top shelf. MusyngKite is darker at the
# source, so it needs less filtering to land in the same place (tenor centroid about 600 Hz).
TONE = {
    "fluidr3": dict(lp_dark=700.0, lp_bright=1900.0, shelf_db=-7.5),
    "musyngkite": dict(lp_dark=820.0, lp_bright=2300.0, shelf_db=-5.5),
}
# Where a legato note starts reading its sample (s). MusyngKite's notes open with the player's own
# accent, 2-3 dB above the settled tone for about 0.4 s; inside a slurred phrase that accent would
# re-tongue every note, so legato notes enter after it.
LEGATO_START = {"fluidr3": 0.10, "musyngkite": 0.45}


def pitch_track(d, midi, hop=441, n=4096):
    """Cents from the nominal pitch every `hop` samples (strongest of harmonics 1-3, 16x zero-padded)."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    fr = np.fft.rfftfreq(16 * n, 1 / SR)
    win = np.hanning(n)
    out = []
    for s0 in range(0, len(d) - n, hop):
        X = np.abs(np.fft.rfft(d[s0:s0 + n] * win, 16 * n))
        best = (0.0, f0)
        for k in (1, 2, 3):
            band = (fr > k * f0 * 0.95) & (fr < k * f0 * 1.05)
            i = int(np.argmax(np.where(band, X, 0)))
            if X[i] > best[0]:
                best = (X[i], fr[i] / k)
        out.append(best[1])
    c = 1200 * np.log2(np.array(out) / f0)
    t = (np.arange(len(c)) * hop + n / 2)
    return t, c


def flatten_pitch(d, midi):
    """Take out the vibrato and drift baked into a sample (MusyngKite has a 3.5-4.5 Hz vibrato of
    4-8 cents), so that the only vibrato is the one the renderer plays, and tune the sustained part
    to the nominal pitch. The level and colour changes of the recording stay."""
    t, c = pitch_track(d, midi)
    ok = t > 0.12 * SR
    # Tune as well as flatten (round 1, pass 3): up to pass 2 the curve was centred on its own
    # median, which took out the vibrato but kept each sample's tuning, and the MusyngKite samples
    # sit a median 5 cents sharp (G3 +10). Now the pitch is pulled to the nominal pitch, with the
    # sustained part (0.6 s to the end, the part _prepare() splices) as the reference: the
    # deviations are measured from the sustained median, and that median is removed too.
    sus = (t > 0.6 * SR) & (t < len(d) - 0.15 * SR)
    ref = sus if sus.sum() > 5 else ok
    c = (c - np.median(c[ref])) + np.median(c[ref])
    c = np.where(ok, c, np.median(c[ref]))
    c = np.convolve(np.pad(c, 2, mode="edge"), np.ones(5) / 5, mode="valid")    # 50 ms smoothing
    cents = np.interp(np.arange(len(d)), t, c)
    pos = np.cumsum(2 ** (-cents / 1200.0))
    pos -= pos[0]
    pos = pos[pos < len(d) - 1]
    return np.interp(pos, np.arange(len(d)), d).astype(np.float32)


class SaxBank:
    def __init__(self, bank=DEFAULT_BANK, lo=45, hi=72):
        self.bank = bank
        cp = CACHE / f"{bank}_tenor_v5.npz"
        if cp.exists():
            z = np.load(cp)
            self.s = {int(k): z[k] for k in z.files}
        else:
            text = (SAMPLES / "gleitz" / BANKS[bank] / "tenor_sax-ogg.js").read_text()
            items = dict(re.findall(r'"([A-G]b?\d)":\s*"data:audio/ogg;base64,([^"]+)"', text))
            self.s = {}
            for m in range(lo, hi + 1):
                d, sr = sf.read(io.BytesIO(base64.b64decode(items[_name(m)])), dtype="float32")
                if d.ndim > 1:
                    d = d.mean(axis=1)
                assert sr == SR
                self.s[m] = self._prepare(flatten_pitch(d, m), m)
            np.savez(cp, **{str(k): v for k, v in self.s.items()})
        self.lo, self.hi = min(self.s), max(self.s)

    @staticmethod
    def _prepare(d, midi, seconds=14.0, seed=None):
        """Normalise on the steady part, then extend the note to `seconds` by splicing pieces of
        its own steady tone (0.35-0.8 s each) in a random order. Each splice point is aligned to
        the waveform (best correlation within one pitch period) and crossfaded over 40 ms, so the
        sustain keeps the recording's own small changes of level and colour and never cycles."""
        rng = np.random.default_rng(seed if seed is not None else midi * 7919)
        steady = d[int(0.5 * SR):int(1.5 * SR)]
        d = d / (np.sqrt(np.mean(steady ** 2)) + 1e-9) * 0.1
        a = int(0.9 * SR)
        lo_s, hi_s = int(0.6 * SR), len(d) - int(0.15 * SR)
        xf = int(0.04 * SR)
        period = int(SR / (440.0 * 2 ** ((midi - 69) / 12))) + 1
        out = [d[:a].copy()]
        tail = d[a - xf:a]
        total = a
        fade = np.linspace(0, 1, xf, dtype=np.float32)
        last_c = a
        while total < seconds * SR:
            L = int(rng.uniform(0.35, 0.8) * SR)
            for _ in range(8):
                c = int(rng.uniform(lo_s + xf + period, hi_s - L - period))
                if abs(c - last_c) > 0.15 * SR:
                    break
            best, bc = -2.0, c
            for k in range(c - period, c + period + 1):
                seg = d[k - xf:k]
                r = float(np.dot(tail, seg) / (np.linalg.norm(tail) * np.linalg.norm(seg) + 1e-9))
                if r > best:
                    best, bc = r, k
            # crossfade the last xf samples already written with the lead-in of the new piece
            prev = out[-1]
            prev[-xf:] = prev[-xf:] * (1 - fade) + d[bc - xf:bc] * fade
            piece = d[bc:bc + L].copy()
            out.append(piece)
            tail = piece[-xf:]
            total += L
            last_c = bc + L
        return np.concatenate(out)[: int(seconds * SR)].astype(np.float32)


def breath_groups(ph, max_len=4.5):
    """Split a phrase into the groups a player shapes in one breath of pressure: a group ends after
    a long note (1.5 beats or more) once it has lasted 2.5 s, or when it reaches `max_len` s."""
    groups, cur = [], []
    for i, n in enumerate(ph):
        cur.append(n)
        span = n.t + n.dur - cur[0].t
        last = i == len(ph) - 1
        if not last and ((n.beats >= 1.5 and span >= 2.5) or span >= max_len):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def phrase_pressure(phrases, rng):
    """Breath pressure (in dB) across each phrase. Each breath group rises from a softer start to
    its most important note (high, long and strong) and relaxes after it; the last group of a
    phrase falls further, so the phrase tail is soft. Sets n.tags["_pressure"] = fn(t) -> dB."""
    for ph in phrases:
        groups = breath_groups(ph)
        for gi, g in enumerate(groups):
            t_s = g[0].t
            t_e = g[-1].t + g[-1].dur
            span = max(t_e - t_s, 0.2)
            pk = max(g, key=lambda n: n.midi + 7 * n.vel + 1.5 * min(n.dur, 2.0))
            t_p = pk.t + 0.5 * min(pk.dur, 1.4)
            depth = min(1.0, span / 2.0)
            last = gi == len(groups) - 1
            start_db = -(5.5 + rng.uniform(0, 2.5)) * depth * (1.0 if gi == 0 else 0.85)
            tail_db = -(10.0 + rng.uniform(0, 3.0)) * depth if last else -(5.0 + rng.uniform(0, 2.0)) * depth

            def fn(t, t_s=t_s, t_e=t_e, t_p=t_p, a=start_db, z=tail_db):
                t = np.asarray(t, dtype=np.float64)
                up = np.clip((t - t_s) / max(t_p - t_s, 0.05), 0, 1)
                dn = np.clip((t - t_p) / max(t_e - t_p, 0.05), 0, 1)
                rise = a * (0.5 + 0.5 * np.cos(np.pi * up))              # a .. 0
                fall = z * (0.5 - 0.5 * np.cos(np.pi * dn)) ** 1.3       # 0 .. z
                return np.where(t < t_p, rise, fall)
            for n in g:
                n.tags["_pressure"] = fn


def render(notes, phrases, n_samples, seed=7, bank=DEFAULT_BANK):
    rng = np.random.default_rng(seed)
    bank = SaxBank(bank)
    phrase_pressure(phrases, np.random.default_rng(seed + 100))
    out = np.zeros(n_samples, np.float32)
    tc = TONE[bank.bank]
    lp_dark = sos("lp", tc["lp_dark"])
    lp_bright = sos("lp", tc["lp_bright"])
    bp_breath = sos("bp", (650.0, 2600.0))
    lp_air = sos("lp", 900.0)
    bp_click = sos("bp", (1500.0, 4000.0))
    bp_inhale = sos("bp", (320.0, 1500.0))
    hp_air = sos("hp", 2400.0, order=2)
    lp_air_top = np.concatenate([sos("lp", 7000.0, order=8), sos("lp", 4500.0, order=1)])  # steep above 7 kHz, a gentle tilt below
    air_out = np.zeros(n_samples, np.float32)

    order = sorted(notes, key=lambda n: n.t)
    prev_end_t = -10.0
    for i, n in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else None
        prv = order[i - 1] if i > 0 else None
        legato_in = not n.tags.get("phrase_start")
        legato_out = n.tags.get("legato_next") is not None
        final = n.tags.get("final", False)
        f0 = 440.0 * 2 ** ((n.midi - 69) / 12)
        att = 0.055 if legato_in else rng.uniform(0.13, 0.20) * (1.15 if n.beats >= 2 else 1.0)
        rel = 0.055 if legato_out else (1.6 if final else rng.uniform(0.20, 0.30))
        if not legato_out and not final:
            # a short rest is a breath: the note has to be gone well before the next phrase
            rel = min(rel, max(0.09, 0.5 * n.tags.get("rest_after", 9.0)))
        dur = n.dur
        N = int((dur + rel) * SR)
        t = np.arange(N, dtype=np.float64) / SR

        # ---- pitch curve (cents) ----
        cents = 3.0 * np.sin(2 * np.pi * 0.31 * t + rng.uniform(0, 6)) + 2.0 * np.sin(2 * np.pi * 0.77 * t + rng.uniform(0, 6))
        if not legato_in:
            cents += -rng.uniform(40, 75) * np.exp(-t / 0.09)                  # scoop into the phrase
        else:
            iv = n.midi - prv.midi
            depth = float(np.clip(-iv * 100 * 0.35, -120, 120))
            if n.tags.get("leap"):
                depth -= rng.uniform(10, 25)
            cents += depth * np.exp(-t / 0.035)                                   # legato: arrive from the last pitch
        if dur >= 0.7:
            onset = min(0.42 * dur, 0.9) + 0.08
            grow = max(0.35, 0.45 * dur)
            depth = rng.uniform(13, 19) + (6 if final else 0) + (3 if dur > 2.2 else 0)
            rate = rng.uniform(4.7, 5.25) + 0.25 * np.sin(2 * np.pi * 0.4 * t)
            vib_env = smoothstep((t - onset) / grow)
            vib = vib_env * np.sin(2 * np.pi * np.cumsum(rate) / SR)
            cents += depth * vib
        elif dur >= 0.35:
            vib_env = smoothstep((t - 0.2) / 0.3) * 0.4
            vib = vib_env * np.sin(2 * np.pi * 5.0 * t)
            cents += 5 * vib
        else:
            vib = np.zeros_like(t)
        if legato_out:
            iv = n.tags["legato_next"] - n.midi
            cents += iv * 100 * 0.35 * smoothstep((t - (dur - 0.015)) / 0.06)   # bend toward the next note
        if n.tags.get("fall"):
            cents -= 150 * smoothstep((t - dur + 0.02) / 0.28)
        if final:
            cents -= 14 * smoothstep((t - 0.55 * dur) / (0.45 * dur + rel))
        ratio = 2 ** (cents / 1200.0)

        # ---- layer 1: the sample ----
        src = bank.s[int(np.clip(n.midi, bank.lo, bank.hi))]
        start = int(LEGATO_START[bank.bank] * SR) if legato_in else 0
        pos = start + np.cumsum(ratio) - ratio[0]
        pos = np.minimum(pos, len(src) - 2)
        tone = np.interp(pos, np.arange(len(src)), src).astype(np.float32)

        # ---- layer 2: subtone body ----
        # the sample's own lowest partials, lifted by a low-pass that tracks the note. Taken from the
        # same waveform, so it is phase-locked to layer 1 (an independent oscillator beat against it)
        phi = 2 * np.pi * np.cumsum(f0 * ratio) / SR          # pitch phase, used to pulse the breath
        core = filt(sos("lp", min(2.2 * f0, 1100.0)), tone)
        body = tone + CORE * core.astype(np.float32)

        # ---- amplitude envelope ----
        x = np.clip(t / att, 0, 1)
        env = np.sin(0.5 * np.pi * x) if legato_in else x ** 1.6 * (3 - 2 * x)  # legato: equal-power crossfade; else a slow bloom
        env = np.minimum(env, 1.0)
        # per-note shape (dB): long notes swell toward their middle and relax; a phrase-final
        # long note fades toward breath (the subtone dying away) instead of holding like an organ
        shape_db = np.zeros_like(t)
        if dur >= 0.6:
            u = np.clip(t / dur, 0, 1)
            # a swell that leans toward the middle of the note and gives it back before the next
            # one, starting and ending at 0 dB so legato joins stay level
            shape_db += rng.uniform(2.5, 4.0) * np.sin(np.pi * u ** 0.85) ** 1.5
            if not legato_out:
                shape_db += -rng.uniform(3.0, 5.5) * smoothstep((u - 0.45) / 0.55)
        elif not legato_out:
            shape_db += -2.5 * smoothstep((t - 0.5 * dur) / (0.5 * dur + 0.05))
        press_db = n.tags["_pressure"](n.t + t) + shape_db
        dyn = (10 ** (press_db / 20)).astype(np.float64)
        env = env * dyn * (1 + 0.03 * vib)
        rel_t = t - dur
        if legato_out:
            env = env * np.cos(0.5 * np.pi * np.clip(rel_t / rel, 0, 1))
        else:
            env = env * np.where(rel_t > 0, np.exp(-np.maximum(rel_t, 0) / (rel / 3.5)) * np.clip(1 - rel_t / rel, 0, 1), 1)
        gain = n.vel ** 1.5

        # brightness follows breath pressure
        press = np.clip(env * n.vel * 1.15, 0, 1) ** 1.5
        w = (0.15 + 0.55 * press).astype(np.float32)
        dark = filt(lp_dark, body)
        bright = filt(lp_bright, body)
        voice = (dark * (1 - w) + bright * w) * env.astype(np.float32)

        # ---- layer 3: breath ----
        noise = rng.standard_normal(N).astype(np.float32)
        breath = filt(bp_breath, noise) * 1.2 + filt(lp_air, rng.standard_normal(N).astype(np.float32)) * 0.5
        sync = (0.45 + 0.55 * (0.5 + 0.5 * np.cos(phi)) ** 2).astype(np.float32)   # pitch-synchronous air
        base = 0.045 + 0.085 * (1 - n.vel)
        puff = (0.16 if not legato_in else 0.035) * np.exp(-((t - 0.55 * att) / (0.45 * att)) ** 2)
        # breath fades less than the tone when the pressure drops, so soft tails turn airy
        b_env = (env * dyn ** -0.45 * base + puff * np.clip(1 - rel_t / rel, 0, 1)).astype(np.float32)
        voice += breath * sync * b_env * 0.1 * BREATH
        # the air: the same breath, but the part above the dark EQ (2.4-7.5 kHz), low and pulsed by the
        # pitch like the rest of the breath. It bypasses the channel low-pass, so the subtone reads as
        # breathy rather than muffled
        air = filt(lp_air_top, filt(hp_air, rng.standard_normal(N).astype(np.float32)))
        a_env = (env * dyn ** -0.3 * (0.6 + 0.8 * (1 - n.vel)) + 1.6 * puff * np.clip(1 - rel_t / rel, 0, 1)).astype(np.float32)

        # key click on legato note changes (tiny)
        if legato_in:
            nc = int(0.004 * SR)
            voice[:nc] += filt(bp_click, rng.standard_normal(nc).astype(np.float32)) * 0.004 * np.hanning(nc).astype(np.float32)

        s0 = int(round(n.t * SR))
        seg = voice * gain
        e = min(n_samples, s0 + N)
        if s0 < n_samples:
            out[s0:e] += seg[:e - s0]
            air_out[s0:e] += (air * sync * a_env * gain * 0.0088 * AIR)[:e - s0]

        # ---- breath intake before a phrase that follows a rest ----
        gap = n.t - prev_end_t
        if not legato_in and gap > INHALE_GAP:
            # the intake fits in the gap: it starts after the last note has gone, ends 70 ms before
            L = min(rng.uniform(0.26, 0.36), gap - 0.10)
            M = max(int(L * SR), 16)
            tt = np.arange(M) / SR
            e_in = np.sin(np.pi * 0.5 * np.clip(tt / (0.8 * L), 0, 1)) ** 2 * np.clip((L - tt) / (0.2 * L), 0, 1)
            inh = filt(bp_inhale, rng.standard_normal(M).astype(np.float32)) * e_in.astype(np.float32)
            inh *= 0.012 * (0.7 + 0.6 * (1 - n.vel))
            a0 = int((n.t - 0.07 - L) * SR)
            if a0 > 0:
                out[a0:a0 + M] += inh
        prev_end_t = n.t + dur if not legato_out else prev_end_t
        if not legato_out:
            prev_end_t = n.t + dur

    # ---- the dark tenor channel EQ ----
    out = filt(sos("hp", 65.0), out)
    out = eq_chain(out, [("lowshelf", 260.0, 2.5, 0.7),
                         ("peak", 190.0, 1.5, 0.9),
                         ("peak", 1300.0, -4.0, 1.0),
                         ("highshelf", 2700.0, tc["shelf_db"], 0.7)])
    out = filt(sos("lp", 5200.0), out)
    return out + air_out
