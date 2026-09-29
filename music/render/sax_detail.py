"""Zoomed view of the tenor stem (head, bars 1-8) to check articulation: scoops, vibrato, breaths,
and the phrase shaping (10 ms level, with a 400 ms smoothed curve for the breath-group swells)."""
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
from lib import OUT, REVIEW
import ballad

x, sr = sf.read(str(OUT / "stem_sax.wav"))
x = x.mean(1)
t0 = ballad.beat_time(ballad.bar_beat(1)) - 1.0
t1 = ballad.beat_time(ballad.bar_beat(9))
seg = x[int(t0 * sr):int(t1 * sr)]
f, t, Z = signal.stft(seg, sr, nperseg=8192, noverlap=8192 - 256)
P = 20 * np.log10(np.abs(Z) + 1e-9)
P -= P.max()
ramp = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("b", ramp)
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12.8, 7.2), dpi=100, gridspec_kw=dict(height_ratios=[3, 1]), sharex=True)
m = f <= 1600
ax.pcolormesh(t + t0, f[m], P[m], cmap=cmap, vmin=-80, vmax=0, shading="auto", rasterized=True)
ax.set_ylabel("frequency (Hz)", color="#4a4a46")
ax.set_title("Tenor, head bars 1-8 (G minor, MTG recorded tenor, AIR 0.4): scoops, late-blooming vibrato, breaths, phrase swells", loc="left", fontsize=12, color="#1f1f1d")
for b in range(1, 10):
    tb = ballad.beat_time(ballad.bar_beat(b))
    ax.axvline(tb, color="#c9c8c2", lw=0.8)
    ax2.axvline(tb, color="#c9c8c2", lw=0.8)
    if b < 9:
        ax.text(tb + 0.05, 1520, f"bar {b}", fontsize=9, color="#4a4a46")
hop = int(0.01 * sr)
n = len(seg) // hop
r = np.sqrt((seg[:n * hop].reshape(n, hop) ** 2).mean(1))
lv = 20 * np.log10(r + 1e-6)
ax2.plot(t0 + np.arange(n) * 0.01, lv, color="#9ec5f4", lw=1.0, label="10 ms level")
k = 40
sm = 10 * np.log10(np.convolve(r ** 2, np.ones(k) / k, mode="same") + 1e-12)
sm[lv < -60] = np.nan
ax2.plot(t0 + np.arange(n) * 0.01, sm, color="#184f95", lw=2.0, label="400 ms (phrase shape)")
ax2.legend(loc="lower right", frameon=False, fontsize=8)
ax2.set_ylim(-80, -10)
ax2.set_ylabel("level (dBFS)", color="#4a4a46")
ax2.set_xlabel("time (s)", color="#4a4a46")
for a in (ax, ax2):
    for s in a.spines.values():
        s.set_color("#c9c8c2")
    a.tick_params(colors="#4a4a46")
fig.tight_layout()
fig.savefig(REVIEW / "sax_detail.jpg", pil_kwargs={"quality": 88})
