"""Zoomed view of the tenor stem (head, bars 1-10) to check articulation: scoops, vibrato, breaths,
the phrase shaping (10 ms level, with a 400 ms smoothed curve for the breath-group swells), and,
since round 1 pass 5, splice holes: every held note that dips more than 12 dB mid-note and
recovers (checks.held_note_dips) is marked in red.

    python3 music/render/sax_detail.py [BEFORE.mp3|wav]

With a BEFORE file (for example the pass-4 stem, `git show 73eabf9:site/public/audio/ballad-sax.mp3`
or any earlier render), its level is drawn under the current one with its dips marked, so a fix
can be seen as well as measured.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy import signal
from lib import OUT, REVIEW, SR
import ballad
import checks

BARS = (1, 11)


def level(seg, sr):
    hop = int(0.01 * sr)
    n = len(seg) // hop
    r = np.sqrt((seg[:n * hop].reshape(n, hop) ** 2).mean(1))
    lv = 20 * np.log10(r + 1e-6)
    k = 40
    sm = 10 * np.log10(np.convolve(r ** 2, np.ones(k) / k, mode="same") + 1e-12)
    sm[lv < -60] = np.nan
    return np.arange(n) * 0.01, lv, sm


def main():
    ev = ballad.events()
    x, sr = sf.read(str(OUT / "stem_sax.wav"))
    x = x.mean(1)
    before = None
    if len(sys.argv) > 1:
        before = sf.read(sys.argv[1])[0]
        before = before.mean(1) if before.ndim > 1 else before
    t0 = ballad.beat_time(ballad.bar_beat(BARS[0])) - 1.0
    t1 = ballad.beat_time(ballad.bar_beat(BARS[1]))
    notes = [n for n in ev["tenor"] if t0 <= n.t and n.t + n.dur <= t1]
    seg = x[int(t0 * sr):int(t1 * sr)]
    f, t, Z = signal.stft(seg, sr, nperseg=8192, noverlap=8192 - 256)
    P = 20 * np.log10(np.abs(Z) + 1e-9)
    P -= P.max()
    ramp = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = LinearSegmentedColormap.from_list("b", ramp)
    rows = 3 if before is not None else 2
    fig, axes = plt.subplots(rows, 1, figsize=(12.8, 7.2 if rows == 2 else 8.6), dpi=100,
                             gridspec_kw=dict(height_ratios=[3, 1.2] + ([1.2] if rows == 3 else [])), sharex=True)
    ax = axes[0]
    m = f <= 1600
    ax.pcolormesh(t + t0, f[m], P[m], cmap=cmap, vmin=-80, vmax=0, shading="auto", rasterized=True)
    ax.set_ylabel("frequency (Hz)", color="#4a4a46")
    ax.set_title("Tenor, head bars 1-10 (G minor, MTG recorded tenor, AIR 0.4, pass 5): scoops, late vibrato, "
                 "breaths, phrase swells", loc="left", fontsize=12, color="#1f1f1d")
    for b in range(BARS[0], BARS[1] + 1):
        tb = ballad.beat_time(ballad.bar_beat(b))
        for a in axes:
            a.axvline(tb, color="#c9c8c2", lw=0.8)
        if b < BARS[1]:
            ax.text(tb + 0.05, 1520, f"bar {b}", fontsize=9, color="#4a4a46")

    def lane(a, y, label):
        tt, lv, sm = level(y[int(t0 * sr):int(t1 * sr)], sr)
        a.plot(t0 + tt, lv, color="#9ec5f4", lw=1.0, label="10 ms level")
        a.plot(t0 + tt, sm, color="#184f95", lw=2.0, label="400 ms (phrase shape)")
        rep, dips = checks.held_note_dips(y, notes)
        for (td, midi, depth) in dips:
            a.axvline(td, color="#c0392b", lw=1.4, ls=(0, (3, 2)))
            a.text(td + 0.08, -76, f"-{depth:.0f} dB", fontsize=8, color="#c0392b")
        verdict = (f"{rep['notes_over_limit']} of {rep['held_notes_checked']} held notes dip over 12 dB"
                   f" (deepest {rep['deepest_dip_db']} dB)")
        a.text(0.005, 0.93, f"{label}: {verdict}", transform=a.transAxes, fontsize=9,
               color="#c0392b" if dips else "#1f6f4a", va="top")
        a.set_ylim(-80, -10)
        a.set_ylabel("level (dBFS)", color="#4a4a46")

    lane(axes[1], x, "pass 5 (steady-window splices)")
    axes[1].legend(loc="lower right", frameon=False, fontsize=8)
    if before is not None:
        lane(axes[2], before, "pass 4 (splices ran into each sample's decay)")
    axes[-1].set_xlabel("time (s)", color="#4a4a46")
    for a in axes:
        for s in a.spines.values():
            s.set_color("#c9c8c2")
        a.tick_params(colors="#4a4a46")
    fig.tight_layout()
    fig.savefig(REVIEW / "sax_detail.jpg", pil_kwargs={"quality": 88})


if __name__ == "__main__":
    main()
