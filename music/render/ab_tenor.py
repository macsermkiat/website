"""
A/B the tenor sample bank on the first half of the head (bars 1-16): MTG (recorded, the default since pass 4)
against MusyngKite and FluidR3 (General MIDI soundfonts).

    python3 music/render/ab_tenor.py      # after render.py; writes music/listen/*.mp3 and ab.json

Both banks go through the same tenor chain (sax.py) with the same notes, and each is mixed with
the shipped piano, bass and drums and a fresh room at the shipped tenor level, so the only
difference is the source sample. Files for listening:
    music/listen/head_<bank>.mp3          band
    music/listen/head_<bank>_tenor.mp3    tenor alone (dry + room)
Proxies for "less synthetic" (no ear involved, so they only inform the choice):
  source (the raw samples C3-F#4, before any processing)
    timbre_motion_in_sustain_db   how much the harmonic envelope moves inside a held note; a
                                  static, organ-like tone moves little
    semitone_to_semitone_timbre_jump_db   timbre change between neighbouring semitones; a GM bank
                                  switches recordings every few notes, and big jumps sound like
                                  different instruments playing alternate notes
    level_movement_in_sustain_db, baked_vibrato_sd_cents   the player's own movement in the sample
  rendered (the dry tenor after sax.py)
    legato_note_to_note_timbre_jump_db, centroid_hz, phrase dynamics as in measure.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, OUT, MUSIC, to_stereo  # noqa: E402
import ballad  # noqa: E402
import measure  # noqa: E402
import room  # noqa: E402
import sax  # noqa: E402
from render import encode, SEND, PAN  # noqa: E402

AB = MUSIC / "listen"   # tracked, so the files reach Mac (review/ is for preview images only)
EXCERPT_END_BAR = 17
KBPS_LISTEN = 128
BANKS_AB = ("mtg", "musyngkite", "fluidr3")   # the first sets the shared room gain


GRID = np.geomspace(150, 3000, 40)


def harmonic_envelope(x, midi, t0, t1, n=8192, hop=2205):
    """Spectral envelope (dB, level removed) from the harmonic peaks of `midi`, per frame."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    ks = np.arange(1, int(3200 / f0))
    out = []
    for s0 in range(int(t0 * SR), int(t1 * SR) - n, hop):
        X = np.abs(np.fft.rfft(x[s0:s0 + n] * np.hanning(n)))
        a = [X[max(int(round(k * f0 * n / SR)) - 3, 0):int(round(k * f0 * n / SR)) + 4].max() for k in ks]
        e = np.interp(np.log(GRID), np.log(ks * f0), 20 * np.log10(np.array(a) + 1e-9))
        out.append(e - e.mean())
    return np.array(out)


def source_metrics(bank):
    """The raw samples of the head's range (C3-F#4), before any processing."""
    import base64, io, re
    if bank != "mtg":
        text = (sax.SAMPLES / "gleitz" / sax.BANKS[bank] / "tenor_sax-ogg.js").read_text()
        items = dict(re.findall(r'"([A-G]b?\d)":\s*"data:audio/ogg;base64,([^"]+)"', text))
    env, motion, level, vib = {}, [], [], []
    for m in range(48, 67):
        if bank == "mtg":
            d = sax._load_mtg(f"ten_p_{m - 43:02d}")
        else:
            d, _ = sf.read(io.BytesIO(base64.b64decode(items[sax._name(m)])), dtype="float32")
            d = d.mean(axis=1) if d.ndim > 1 else d
        E = harmonic_envelope(d, m, 0.4, 2.9)
        env[m] = E.mean(axis=0)
        motion.append(np.sqrt(((E - E.mean(axis=0)) ** 2).mean()))
        w = int(0.05 * SR)
        seg = d[int(0.4 * SR):int(2.9 * SR)]
        r = 20 * np.log10(np.sqrt((seg[:len(seg) // w * w].reshape(-1, w) ** 2).mean(axis=1)))
        level.append(np.percentile(r, 95) - np.percentile(r, 5))
        t, c = sax.pitch_track(d, m)
        c = c[t > 0.3 * SR]
        vib.append(np.std(c - np.convolve(c, np.ones(50) / 50, "same")))
    jumps = [np.sqrt(((env[m + 1] - env[m]) ** 2).mean()) for m in range(48, 66)]
    return {"timbre_motion_in_sustain_db": round(float(np.median(motion)), 2),
            "semitone_to_semitone_timbre_jump_db": round(float(np.median(jumps)), 2),
            "largest_timbre_jump_db": round(float(max(jumps)), 2),
            "level_movement_in_sustain_db": round(float(np.median(level)), 2),
            "baked_vibrato_sd_cents": round(float(np.median(vib)), 1)}


def rendered_metrics(x, notes):
    """Timbre change between consecutive legato notes of the rendered tenor (harmonic envelopes)."""
    jumps, prev = [], None
    for n in notes:
        if n.dur < 0.4 or n.t + n.dur > len(x) / SR:
            prev = None
            continue
        E = harmonic_envelope(x, n.midi, n.t + 0.1, n.t + n.dur)
        if len(E) == 0:
            prev = None
            continue
        m = E.mean(axis=0)
        if prev is not None:
            jumps.append(float(np.sqrt(((m - prev) ** 2).mean())))
        prev = m if n.tags.get("legato_next") is not None else None
    return {"legato_note_to_note_timbre_jump_db": round(float(np.median(jumps)), 2)}


def main():
    AB.mkdir(parents=True, exist_ok=True)
    ev = ballad.events()
    # the first two A sections (bars 1-16, 0:00-0:46): long enough to judge the tone, and small
    # enough to keep in git (128 kbps, about 0.7 MB a file)
    t_end = ballad.beat_time(ballad.bar_beat(EXCERPT_END_BAR)) + 1.5
    n = int(t_end * SR)
    phr = [p for p in ev["phrases"] if p[0].beat < ballad.bar_beat(EXCERPT_END_BAR)]
    notes = [x for p in phr for x in p]
    band = {k: sf.read(str(OUT / f"stem_{k}.wav"), dtype="float32")[0][:n] for k in ("sax", "piano", "bass", "drums", "room")}
    meter = pyln.Meter(SR)
    ref_sax = meter.integrated_loudness(band["sax"].astype(np.float64))
    ref_room = meter.integrated_loudness(band["room"].astype(np.float64))
    ir, irx = room.impulse_response(seed=5), room.impulse_response(seed=6)
    fade = np.ones((n, 1), np.float32)
    fade[-int(1.2 * SR):, 0] = np.linspace(1, 0, int(1.2 * SR))
    report, room_gain = {}, None
    for bank in BANKS_AB:
        dry = sax.render(notes, phr, n, bank=bank)
        st = to_stereo(dry, PAN["sax"])
        st *= 10 ** ((ref_sax - meter.integrated_loudness(st.astype(np.float64))) / 20)
        send = st * SEND["sax"] + sum(band[k] * SEND[k] for k in ("piano", "bass", "drums"))
        wet = room.reverb(send, ir, irx)[:n]
        if room_gain is None:      # set once, on the first bank, then used for both
            room_gain = 10 ** ((ref_room - meter.integrated_loudness(wet.astype(np.float64))) / 20)
        wet = wet * room_gain
        tenor_wet = room.reverb(st * SEND["sax"], ir, irx)[:n] * room_gain
        mix = (st + band["piano"] + band["bass"] + band["drums"] + wet) * fade
        solo = (st + tenor_wet) * fade
        g = 10 ** ((-18.0 - meter.integrated_loudness(mix.astype(np.float64))) / 20)
        (AB / f"head_{bank}.mp3").write_bytes(encode(mix * g, KBPS_LISTEN))
        (AB / f"head_{bank}_tenor.mp3").write_bytes(encode(solo * g, KBPS_LISTEN))
        cen = measure.centroid_report(st)
        report[bank] = {
            "centroid_hz": round(cen["active_frames_mean_hz"], 1),
            **rendered_metrics(dry, notes),
            "source": source_metrics(bank),
            "phrase_dynamics": measure.phrase_dynamics(st, phr),
        }
        print(bank, report[bank])
    (AB / "ab.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
