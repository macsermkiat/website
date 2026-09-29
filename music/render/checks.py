"""
Checks added in round 1, pass 3 (the judges' listening proxies). measure.py calls these on the
shipped files; `python3 music/render/checks.py` runs them on the working WAVs in music/out/.

  tenor_runs       how long the tenor plays without a breath, from the score (note on/off) and
                   from the audio (50 ms level of the sax stem)
  melody_on_top    how often the piano's top voice sits above the tenor, and the sax-versus-piano
                   band energy at 200-1500 Hz while the tenor plays the head
  air_band         sax energy at 3.2-6.4 kHz and 6.4-8 kHz relative to its total (the breath air)
  intonation       median offset (cents) of the sustained part of every prepared tenor sample
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, OUT  # noqa: E402
import ballad  # noqa: E402


def tenor_runs_score(notes, breath=0.3):
    """Runs of the tenor with no gap of at least `breath` s between one note's end and the next
    onset (performed times). Returns the runs as (start, end) seconds, longest first."""
    order = sorted(notes, key=lambda n: n.t)
    runs, s, e = [], order[0].t, order[0].t + order[0].dur
    for n in order[1:]:
        if n.t - e >= breath:
            runs.append((s, e))
            s = n.t
        e = max(e, n.t + n.dur)
    runs.append((s, e))
    return sorted(runs, key=lambda r: r[0] - r[1])


def tenor_runs_audio(x, below_db=-30.0, min_gap=0.15, hop=0.05):
    """Runs in the sax audio: a breath is at least `min_gap` s with the 50 ms level more than
    `below_db` under the level of the loudest 5% of frames. Returns runs (start, end), longest first."""
    mono = x.mean(axis=1) if x.ndim > 1 else x
    w = int(hop * SR)
    n = len(mono) // w
    r = 20 * np.log10(np.sqrt((mono[:n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-9)
    ref = np.percentile(r[r > r.max() - 60], 95)
    on = r > ref + below_db
    runs, i = [], 0
    k = int(round(min_gap / hop))
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        while j < n:
            if on[j]:
                j += 1
                continue
            g = j
            while g < n and not on[g]:
                g += 1
            if g - j >= k or g >= n:
                break
            j = g
        runs.append((i * hop, j * hop))
        i = j
    return sorted(runs, key=lambda r: r[0] - r[1])


def runs_summary(runs, top=5):
    return {"longest_s": round(runs[0][1] - runs[0][0], 1),
            "longest_runs": [[round(a, 1), round(b, 1), round(b - a, 1)] for a, b in runs[:top]],
            "runs_over_10s": sum(1 for a, b in runs if b - a > 10.0),
            "count": len(runs)}


def piano_top_vs_tenor(voicings_log, tenor):
    """For each comp chord struck while the tenor plays a note (head, tenor chorus, out head), is the
    piano's top voice above the tenor's note at that moment?"""
    above = total = 0
    for bar, sym, v, beat in voicings_log:
        m = ballad.melody_at(tenor, beat)
        if m is None:
            continue
        total += 1
        above += max(v) > m
    return above, total


def band_db(x, t0, t1, lo=200.0, hi=1500.0):
    mono = x.mean(axis=1) if x.ndim > 1 else x
    seg = mono[int(t0 * SR):int(t1 * SR)]
    f, p = signal.welch(seg, SR, nperseg=4096)
    m = (f >= lo) & (f <= hi)
    return float(10 * np.log10(p[m].sum() + 1e-20))


def melody_audibility(sax, piano, tenor, t0, t1):
    """Sax minus piano band energy (dB, 200-1500 Hz) over the whole span and in the moments the tenor
    holds a note (notes of 1.5 beats or more), where a comp above it would cover it most."""
    whole = band_db(sax, t0, t1) - band_db(piano, t0, t1)
    held = []
    for n in tenor:
        if t0 <= n.t < t1 and n.beats >= 1.5 and n.dur > 0.8:
            a, b = n.t + 0.2, n.t + n.dur - 0.05
            held.append(band_db(sax, a, b) - band_db(piano, a, b))
    return {"sax_minus_piano_200_1500_db": round(whole, 1),
            "held_notes_median_db": round(float(np.median(held)), 1) if held else None,
            "held_notes_min_db": round(float(np.min(held)), 1) if held else None,
            "held_notes": len(held)}


def air_band(x):
    mono = x.mean(axis=1) if x.ndim > 1 else x
    f, p = signal.welch(mono, SR, nperseg=8192)
    tot = p.sum()
    out = {}
    for lo, hi in ((3200, 6400), (6400, 8000), (8000, 12000)):
        m = (f >= lo) & (f < hi)
        out[f"{lo}_{hi}_hz_rel_db"] = round(float(10 * np.log10(p[m].sum() / tot + 1e-20)), 1)
    return out


def intonation(bank):
    """Median cents of the sustained part (0.6 s to the end, the part the splicer uses) of every
    prepared sample, measured the same way flatten_pitch() measures."""
    import sax
    b = sax.SaxBank(bank)
    meds = []
    for m, d in sorted(b.s.items()):
        t, c = sax.pitch_track(d[:int(4.0 * SR)], m)
        ok = t > 0.6 * SR
        meds.append(float(np.median(c[ok])))
    meds = np.array(meds)
    return {"median_cents": round(float(np.median(meds)), 1),
            "mean_abs_cents": round(float(np.mean(np.abs(meds))), 1),
            "worst_cents": round(float(meds[np.argmax(np.abs(meds))]), 1)}


def main():
    import soundfile as sf
    ev = ballad.events()
    sax_x = sf.read(str(OUT / "stem_sax.wav"), dtype="float32")[0]
    pno = sf.read(str(OUT / "stem_piano.wav"), dtype="float32")[0]
    rep = {"tenor_runs_score": runs_summary(tenor_runs_score(ev["tenor"])),
           "tenor_runs_audio": runs_summary(tenor_runs_audio(sax_x))}
    t0, t1 = ballad.beat_time(0), ballad.beat_time(ballad.bar_beat(33))
    rep["melody_audibility_head"] = melody_audibility(sax_x, pno, ev["tenor"], t0, t1)
    if len(ev["voicings"][0]) == 4:
        a, t = piano_top_vs_tenor(ev["voicings"], ev["tenor"])
        rep["piano_top_above_tenor"] = f"{a} of {t}"
    rep["sax_air"] = air_band(sax_x)
    import json
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
