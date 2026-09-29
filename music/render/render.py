"""
Render "Lanterns After Closing" to stems, a mix preview, the site manifest and the MIDI score.

    python3 music/render/render.py            # render everything (about 3-4 minutes on one core)
    python3 music/render/render.py --reuse    # reuse cached instrument renders, redo mix + export

Pipeline: score events -> per-instrument samplers (dry stems) -> levels -> reverb sends -> room
stem -> linked bus compression (one gain curve from the mix, applied to every stem, so the stems
still sum to the mix) -> loudness to -18 LUFS -> linked peak safety -> loop-seam splice ->
MP3 stems (128 kbps) + manifest.json, mix preview in music/out/, measurements.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import lameenc
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, CACHE, OUT, SITE_AUDIO, MUSIC, to_stereo, db  # noqa: E402
import ballad  # noqa: E402

STEMS = ["sax", "piano", "bass", "drums", "room"]
# licence of the rendered recording, by tenor bank (see CREDITS.md, music writer)
LICENSES = {
    "musyngkite": {
        "sax, room, mix": "Share-alike: must be offered under CC BY-SA 3.0, because they contain the MusyngKite "
                          "tenor samples (CC BY-SA 3.0, via gleitz/midi-js-soundfonts)",
        "piano": "Attribution: Salamander Grand Piano by Alexander Holm (CC BY 3.0)",
        "bass, drums": "No conditions (CC0 sources)",
        "credit": "Piano: Salamander Grand Piano by Alexander Holm (CC BY 3.0). Tenor sax: MusyngKite soundfont "
                  "via gleitz/midi-js-soundfonts (CC BY-SA 3.0). Bass: Karoryfer Meatbass (CC0). Drums: Virtuosity "
                  "Drums by Versilian Studios (CC0). Recording: CC BY-SA 3.0.",
    },
    "fluidr3": {
        "sax, room, mix": "Attribution: FluidR3 GM by Frank Wen (CC BY 3.0) and Salamander Grand Piano (mix, room)",
        "piano": "Attribution: Salamander Grand Piano by Alexander Holm (CC BY 3.0)",
        "bass, drums": "No conditions (CC0 sources)",
        "credit": "Piano: Salamander Grand Piano by Alexander Holm (CC BY 3.0). Tenor sax: FluidR3 GM by Frank Wen "
                  "(CC BY 3.0 via gleitz/midi-js-soundfonts). Bass: Karoryfer Meatbass (CC0). Drums: Virtuosity "
                  "Drums by Versilian Studios (CC0).",
    },
}
# relative levels (integrated LUFS of each dry stem before the final loudness step)
TARGET = {"sax": -21.0, "piano": -24.5, "bass": -25.0, "drums": -31.5}
PIANO_SOLO_LUFS = -22.95    # the piano's level in its half-chorus (the same as pass 2's)
SEND = {"sax": 0.42, "piano": 0.33, "bass": 0.10, "drums": 0.30}
PAN = {"sax": 0.10, "bass": 0.02}
ROOM_REL_DB = -9.0          # room return, relative to the dry mix loudness
MIX_LUFS = -18.0
PEAK_CEIL_DB = -1.6
KBPS = 128
# the alternate chorus segment: from half a second before bar 33 (the head is still identical) to
# the downbeat of bar 67 (both choruses' last notes and their reverb have died away)
ALT_START = lambda b: b.beat_time(b.bar_beat(33)) - 0.5  # noqa: E731
ALT_END = lambda b: b.beat_time(b.bar_beat(67))  # noqa: E731
TAIL = 2.9                  # seconds after the last written beat
FADE = 2.2


def render_alt_sax(ev, n, reuse, sax_bank):
    """The tenor with the alternate chorus (bars 33-64). Only the notes up to bar 64 are rendered:
    everything before the chorus is identical to the main render, and the file is cut to the chorus."""
    cp = CACHE / "stem_sax_b.npy"
    if reuse and cp.exists():
        x = np.load(cp)
        if len(x) == n:
            return x
    import sax
    t0 = time.time()
    cut = ballad.bar_beat(65)
    notes = [x for x in ev["tenor_b"] if x.beat < cut]
    phr = [[x for x in p if x.beat < cut] for p in ev["phrases_b"] if p[0].beat < cut]
    x = to_stereo(sax.render(notes, phr, n, bank=sax_bank), PAN["sax"])
    np.save(cp, x)
    print(f"  rendered sax (alternate chorus) in {time.time() - t0:.1f}s")
    return x


def render_instruments(ev, n, reuse, sax_bank="fluidr3"):
    stems = {}
    for name in ["sax", "piano", "bass", "drums"]:
        cp = CACHE / f"stem_{name}.npy"
        if reuse and cp.exists():
            x = np.load(cp)
            if len(x) == n:
                stems[name] = x
                continue
        t0 = time.time()
        if name == "sax":
            import sax
            x = sax.render(ev["tenor"], ev["phrases"], n, bank=sax_bank)
        elif name == "piano":
            import piano
            x = piano.render(ev["piano"], n)
        elif name == "bass":
            import bass
            x = bass.render(ev["bass"], n)
        else:
            import drums
            x = drums.render(ev["drums"], n)
        x = to_stereo(x, PAN.get(name, 0.0))
        np.save(cp, x)
        stems[name] = x
        print(f"  rendered {name} in {time.time() - t0:.1f}s")
    return stems


def lufs(x):
    return pyln.Meter(SR).integrated_loudness(x.astype(np.float64))


def bus_gain(mix, threshold_db, ratio=2.0, knee=6.0, attack=0.025, release=0.30):
    """Gain curve (linear, per sample) of a gentle RMS glue compressor fed by the mix."""
    mono = mix.mean(axis=1)
    win = int(0.02 * SR)
    p = np.convolve(mono.astype(np.float64) ** 2, np.ones(win) / win, mode="same")
    lvl = 10 * np.log10(np.maximum(p, 1e-12))
    over = lvl - threshold_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    # attack/release smoothing of the gain reduction (in dB), decimated for speed
    hop = 64
    g = gr[::hop]
    a_att = np.exp(-hop / (attack * SR))
    a_rel = np.exp(-hop / (release * SR))
    sm = np.zeros_like(g)
    s = 0.0
    for i, v in enumerate(g):
        a = a_att if v > s else a_rel
        s = a * s + (1 - a) * v
        sm[i] = s
    full = np.interp(np.arange(len(mix)), np.arange(len(sm)) * hop, sm)
    return (10 ** (-full / 20)).astype(np.float32), float(sm.max())


def peak_gain(mix, ceil_db, look=0.004, release=0.08):
    ceil = 10 ** (ceil_db / 20)
    a = np.abs(mix).max(axis=1)
    need = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    if need.min() >= 1.0:
        return np.ones(len(mix), np.float32)
    L = int(look * SR)
    # running minimum over the look-ahead window, then smooth release
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * L + 1)
    out = np.empty_like(g)
    s = 1.0
    r = np.exp(-1 / (release * SR))
    for i in range(len(g)):
        s = g[i] if g[i] < s else r * s + (1 - r) * g[i]
        out[i] = s
    return out.astype(np.float32)


def splice_loop(stems, ls, le, X=0.8):
    """Make the jump from loopEnd back to loopStart seamless: the last X seconds before loopEnd
    fade into a copy of the X seconds before loopStart (the same musical moment: the tenor's pickup
    into the bridge over the same comp, bass and brush). Full copy for the last X/2 seconds, so
    the waveform at loopEnd continues exactly into loopStart."""
    n = int(X * SR)
    w = np.clip(np.linspace(0, 2, n), 0, 1)
    w = (0.5 - 0.5 * np.cos(np.pi * w))[:, None].astype(np.float32)
    m = int(0.25 * SR)
    w2 = (0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, m)))[:, None].astype(np.float32)
    for k, x in stems.items():
        a = x[le - n:le].copy()
        b = x[ls - n:ls]
        x[le - n:le] = a * (1 - w) + b * w
        # straight playback past loopEnd (only the full-length preview does this): hand back from the
        # continuation of loopStart to the real out head over 250 ms, so there is no click there either
        x[le:le + m] = x[ls:ls + m] * (1 - w2) + x[le:le + m] * w2


def encoder_delay():
    """Samples LAME (via lameenc) adds before the audio when there is no gapless header."""
    x = np.zeros((SR, 2), np.int16)
    x[10000] = 20000
    b = encode(x.astype(np.float32) / 32767, KBPS)
    p = CACHE / "delay_probe.mp3"
    p.write_bytes(b)
    d, _ = sf.read(str(p), always_2d=True)
    return int(np.argmax(np.abs(d[:, 0]))) - 10000


def encode(x, kbps):
    e = lameenc.Encoder()
    e.set_bit_rate(kbps)
    e.set_in_sample_rate(SR)
    e.set_channels(2)
    e.set_quality(2)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    return bytes(e.encode(pcm.tobytes()) + e.flush())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", action="store_true")
    import sax
    ap.add_argument("--sax-bank", default=sax.DEFAULT_BANK, choices=sorted(sax.BANKS),
                    help="tenor sample bank (see sax.BANKS and music/README.md for the A/B)")
    ap.add_argument("--cut-stems", action="store_true",
                    help="end the five stems 1 s after loopEnd (the mix file keeps the ending)")
    args = ap.parse_args()
    t_start = time.time()
    ev = ballad.events()
    tl = ballad.timeline()
    duration = tl["end_music"] + TAIL
    n = int(round(duration * SR))
    print(f"{ballad.TITLE}: {n / SR:.2f}s, loop {tl['loopStart']:.3f}-{tl['loopEnd']:.3f}")
    stems = render_instruments(ev, n, args.reuse, args.sax_bank)
    # the alternate chorus: its own sax and room, carried through every gain step with the stems
    # they replace, so they drop into the same mix
    alt = {"sax": render_alt_sax(ev, n, args.reuse, args.sax_bank)}

    def scale(k, g):
        stems[k] = stems[k] * g
        if k in alt:
            alt[k] = alt[k] * g

    # ---- levels ----
    for k, tgt in TARGET.items():
        if k == "piano":
            # the piano is levelled on its own half-chorus (bars 65-80), where it leads, so that a
            # softer comp under the tenor stays softer instead of being turned back up
            p0 = int(ballad.beat_time(ballad.bar_beat(65)) * SR)
            p1 = int(ballad.beat_time(ballad.bar_beat(81)) * SR)
            scale(k, 10 ** ((PIANO_SOLO_LUFS - lufs(stems[k][p0:p1])) / 20))
            continue
        scale(k, 10 ** ((tgt - lufs(stems[k])) / 20))
    dry = sum(stems[k] for k in TARGET)
    # ---- room ----
    import room
    send = sum(stems[k] * SEND[k] for k in TARGET)
    ir = room.impulse_response(seed=5)
    irx = room.impulse_response(seed=6)
    wet = room.reverb(send, ir, irx)
    room_gain = 10 ** ((lufs(dry) + ROOM_REL_DB - lufs(wet)) / 20)
    stems["room"] = wet * room_gain
    alt["room"] = room.reverb(send + (alt["sax"] - stems["sax"]) * SEND["sax"], ir, irx) * room_gain
    mix = sum(stems[k] for k in STEMS)

    # ---- glue compression (linked) ----
    L0 = lufs(mix)
    g, max_gr = bus_gain(mix, threshold_db=L0 + 4.0)
    for k in STEMS:
        scale(k, g[:, None])
    # ---- loudness ----
    for _ in range(2):
        mix = sum(stems[k] for k in STEMS)
        gain = 10 ** ((MIX_LUFS - lufs(mix)) / 20)
        for k in STEMS:
            scale(k, gain)
        mix = sum(stems[k] for k in STEMS)
        pg = peak_gain(mix, PEAK_CEIL_DB)
        for k in STEMS:
            scale(k, pg[:, None])
    # the alternate chorus's own peaks: limit its two stems locally if the other mix needs it
    mix_b = mix - stems["sax"] - stems["room"] + alt["sax"] + alt["room"]
    pg_b = peak_gain(mix_b, PEAK_CEIL_DB)
    for k in alt:
        alt[k] = alt[k] * pg_b[:, None]

    # ---- loop seam + end fade ----
    ls = int(round(tl["loopStart"] * SR))
    le = int(round(tl["loopEnd"] * SR))
    splice_loop(stems, ls, le)
    f = int(FADE * SR)
    fade = (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, f)))[:, None].astype(np.float32)
    for k in STEMS:
        stems[k][-f:] *= fade
    mix = sum(stems[k] for k in STEMS)
    print(f"  mix {lufs(mix):.2f} LUFS, peak {db(np.abs(mix).max()):.2f} dBFS, bus GR max {max_gr:.1f} dB")

    # ---- export ----
    OUT.mkdir(exist_ok=True)
    SITE_AUDIO.mkdir(parents=True, exist_ok=True)
    d = encoder_delay()
    print(f"  encoder delay {d} samples (compensated)")

    def shifted(x):
        return np.concatenate([x[d:], np.zeros((d, 2), np.float32)]) if d > 0 else x

    # MP3 round trip loses ~0.4 dB of loudness here; measure it on the decoded stem sum and correct once
    files = {k: f"ballad-{k}.mp3" for k in STEMS}
    for attempt in range(2):
        for k in STEMS:
            (SITE_AUDIO / files[k]).write_bytes(encode(shifted(stems[k]), KBPS))
        dec = sum(sf.read(str(SITE_AUDIO / files[k]), always_2d=True, dtype="float32")[0][:n] for k in STEMS)
        err = MIX_LUFS - lufs(dec)
        print(f"  decoded stem sum {lufs(dec):.2f} LUFS, peak {db(np.abs(dec).max()):.2f} dBFS")
        if abs(err) < 0.1:
            break
        for k in STEMS:
            scale(k, 10 ** (err / 20))
        mix = sum(stems[k] for k in STEMS)
    if args.cut_stems:
        # optional: stems end 1 s after loopEnd (about 18% smaller); the ending then lives only in
        # the mix file, which a player can hand over to for the out head
        cut = le + SR
        f2 = int(0.5 * SR)
        for k in STEMS:
            x = shifted(stems[k])[:cut].copy()
            x[-f2:] *= np.linspace(1, 0, f2, dtype=np.float32)[:, None]
            (SITE_AUDIO / files[k]).write_bytes(encode(x, KBPS))
    # ---- the alternate chorus: a segment of the sax and room stems, same timeline ----
    a0 = int(round(ALT_START(ballad) * SR))
    a1 = int(round(ALT_END(ballad) * SR))
    same = {k: float(np.abs(alt[k][a0 - SR // 2:a0 + SR // 2] - stems[k][a0 - SR // 2:a0 + SR // 2]).max()) for k in alt}
    same_end = {k: float(np.abs(alt[k][a1 - SR // 2:a1 + SR // 2] - stems[k][a1 - SR // 2:a1 + SR // 2]).max()) for k in alt}
    print(f"  alternate chorus {a0 / SR:.3f}-{a1 / SR:.3f}s; max difference from the main stems "
          f"around its start {same}, around its end {same_end}")
    alt_files = {k: f"ballad-{k}-b.mp3" for k in alt}
    for k in alt:
        seg = alt[k][a0:a1].copy()
        (SITE_AUDIO / alt_files[k]).write_bytes(encode(shifted(seg), KBPS))
    mix_b = mix.copy()
    for k in alt:
        mix_b[a0:a1] += alt[k][a0:a1] - stems[k][a0:a1]
    (OUT / "ballad_mix_chorus_b_preview.mp3").write_bytes(encode(shifted(mix_b), 192))
    sf.write(OUT / "ballad_mix_chorus_b.wav", mix_b, SR, subtype="PCM_24")
    for k in alt:
        sf.write(OUT / f"stem_{k}_b.wav", alt[k], SR, subtype="PCM_24")

    sf.write(OUT / "ballad_mix.wav", mix, SR, subtype="PCM_24")
    for k in STEMS:
        sf.write(OUT / f"stem_{k}.wav", stems[k], SR, subtype="PCM_24")
    (SITE_AUDIO / "ballad-mix.mp3").write_bytes(encode(shifted(mix), KBPS))
    (OUT / "ballad_mix_preview.mp3").write_bytes(encode(shifted(mix), 192))

    manifest = {
        "title": ballad.TITLE,
        "composer": "Nachtmarkt music writer (original composition)",
        "bpm": ballad.TEMPO,
        "timeSignature": "3/4",
        "key": ballad.KEY,
        "tenorBank": args.sax_bank,
        "sampleRate": SR,
        "duration": round(n / SR, 6),
        "loopStart": round(ls / SR, 6),
        "loopEnd": round(le / SR, 6),
        "stems": {k: files[k] for k in STEMS},
        "mix": "ballad-mix.mp3",
        "events": "ballad-events.json",
        "form": "32-bar AABA in 3/4: head (1-32), tenor chorus (33-64), piano half-chorus (65-80), "
                "out head from the bridge (81-96) with ritardando and a rubato fermata; the loop is bars 17-80, "
                "with a second written tenor chorus for alternate passes (alternates)",
        "sections": [{"name": name, "bar": bar, "t": round(ballad.beat_time(ballad.bar_beat(bar)), 3)}
                     for name, bar in (("head", 1), ("head bridge", 17), ("tenor chorus", 33),
                                       ("piano half-chorus", 65), ("out head", 81), ("fermata", 96))],
        "ending": {
            "start": round(le / SR, 6),
            "fermata": round(ballad.beat_time(ballad.bar_beat(96)), 3),
            "musicEnds": round(tl["end_music"], 3),
            "howTo": "To finish the tune instead of looping, let playback run on past loopEnd to the end "
                     "of the file: the out head (bars 81-96) follows seamlessly and ends on a fermata.",
        },
        "alternates": [{
            "name": "tenor chorus B",
            "bars": [33, 64],
            "when": "every second pass through the loop (pass 1 plays the main stems, pass 2 this, and so on)",
            "start": round(a0 / SR, 6),
            "end": round(a1 / SR, 6),
            "stems": alt_files,
            "howTo": "The files hold the stems' audio from start to end on the same timeline (sample 0 = start). "
                     "On an alternate pass, play them in place of the sax and room stems between start and end. "
                     "The first and last 0.5 s are identical to the main stems, so any crossfade inside those "
                     "windows is seamless; the other three stems do not change.",
            "maxDifferenceFromMainStemsAtEdges": round(max(list(same.values()) + list(same_end.values())), 6),
        }],
        "decodedDuration": None,
        "stemsEnd": round((le + SR) / SR, 6) if args.cut_stems else None,
        "durationNote": "duration is the rendered length; an MP3 decoder (Chromium, libmpg123) returns "
                        "decodedDuration, which is longer by the encoder's final-frame padding (silence).",
        "license": {
            "composition": "Original composition for this site (all rights with the site owner)",
            "recording": LICENSES[args.sax_bank],
        },
    }
    manifest["decodedDuration"] = round(len(sf.read(str(SITE_AUDIO / files["sax"]), dtype="float32")[0]) / SR, 6)
    (SITE_AUDIO / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_events(ev, (a0 / SR, a1 / SR))
    import midi_export
    midi_export.write(ev, MUSIC / "score" / "ballad.mid")
    midi_export.write_leadsheet(ev, MUSIC / "score" / "LEADSHEET.md")
    print(f"done in {time.time() - t_start:.0f}s")


def write_events(ev, alt_span):
    """Note onsets per player (for animating the musicians); times are in stem time. `saxAlt` is
    the tenor in the alternate chorus (manifest.alternates), for the passes that play it."""
    out = {"sax": [], "saxAlt": [], "piano": [], "bass": [], "drums": []}
    for n in ev["tenor"]:
        out["sax"].append([round(n.t, 3), round(n.dur, 3), n.midi, round(n.vel, 2)])
    for n in ev["tenor_b"]:
        if alt_span[0] <= n.t < alt_span[1]:
            out["saxAlt"].append([round(n.t, 3), round(n.dur, 3), n.midi, round(n.vel, 2)])
    for n in ev["piano"]:
        out["piano"].append([round(n.t, 3), round(n.dur, 3), n.midi, round(n.vel, 2)])
    for n in ev["bass"]:
        out["bass"].append([round(n.t, 3), round(n.dur, 3), n.midi, round(n.vel, 2)])
    for e in ev["drums"]:
        if e["kind"] in ("tap", "kick", "hat", "ride", "sweep"):
            out["drums"].append([round(e["t"], 3), e["kind"], round(float(e["vel"]), 2)])
    for k in out:
        out[k].sort(key=lambda r: r[0])
    doc = {"format": "[time s, duration s, midi, velocity] per note; drums: [time s, kind, velocity]; "
                     "saxAlt replaces the sax notes between manifest.alternates[0].start and end on alternate passes",
           **out}
    (SITE_AUDIO / "ballad-events.json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
