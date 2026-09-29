"""
A/B the brushes: the recorded brushes (Karoryfer Swirly Drums, the default since round 1 pass 4)
against the round-1 model (noise through a sampled snare response).

    python3 music/render/ab_brushes.py    # after render.py; writes music/listen/brushes_*.mp3

The excerpt is the bridge of the head into the tenor chorus (bars 17-36, 0:45-1:40), where the
hi-hat foot and the brushed ride join the sweeps and taps. The band files use the shipped sax,
piano, bass and room stems with each drum take levelled to the shipped drum stem, so only the
drums differ (the room still carries the recorded brushes' reverb, which is a small share of it).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, OUT, MUSIC, REVIEW  # noqa: E402
import ballad  # noqa: E402
import drums  # noqa: E402
from render import encode  # noqa: E402

LISTEN = MUSIC / "listen"
BARS = (17, 37)


def main():
    LISTEN.mkdir(exist_ok=True)
    ev = ballad.events()
    t0 = ballad.beat_time(ballad.bar_beat(BARS[0])) - 0.8
    t1 = ballad.beat_time(ballad.bar_beat(BARS[1])) + 1.0
    a, b = int(t0 * SR), int(t1 * SR)
    band = {k: sf.read(str(OUT / f"stem_{k}.wav"), dtype="float32")[0] for k in ("sax", "piano", "bass", "drums", "room")}
    n = len(band["drums"])
    meter = pyln.Meter(SR)
    ref = meter.integrated_loudness(band["drums"][a:b].astype(np.float64))
    fade = np.ones((b - a, 1), np.float32)
    k = int(0.4 * SR)
    fade[:k, 0] = np.linspace(0, 1, k)
    fade[-int(1.0 * SR):, 0] = np.linspace(1, 0, int(1.0 * SR))
    others = (band["sax"] + band["piano"] + band["bass"] + band["room"])[a:b]
    takes = {}
    for kit in ("recorded", "modelled"):
        if kit == "recorded":
            d = band["drums"][a:b]
        else:
            x = drums.render([e for e in ev["drums"] if t0 - 3 < e["t"] < t1], n, kit="modelled")[a:b]
            d = x * 10 ** ((ref - meter.integrated_loudness(x.astype(np.float64))) / 20)
        (LISTEN / f"brushes_{kit}.mp3").write_bytes(encode((others + d) * fade, 128))
        # the drums alone, 12 dB up, so the brush texture can be heard
        (LISTEN / f"brushes_{kit}_alone.mp3").write_bytes(encode(d * fade * 10 ** (12 / 20), 128))
        takes[kit] = d
        print(kit, "done")
    figure(takes, t0)


def figure(takes, t0):
    """Four bars of the drums alone (bars 33-36, the tenor chorus start), both takes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from scipy import signal
    s0 = ballad.beat_time(ballad.bar_beat(33)) - t0
    s1 = ballad.beat_time(ballad.bar_beat(37)) - t0
    cmap = LinearSegmentedColormap.from_list("b", ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                                                   "#256abf", "#184f95", "#0d366b"])
    fig, axes = plt.subplots(2, 1, figsize=(12.8, 7.2), dpi=100, sharex=True)
    ref = None
    for ax, kit in zip(axes, ("recorded", "modelled")):
        x = takes[kit][int(s0 * SR):int(s1 * SR)].mean(axis=1)
        f, t, Z = signal.stft(x, SR, nperseg=2048, noverlap=2048 - 256)
        P = 20 * np.log10(np.abs(Z) + 1e-9)
        ref = P.max() if ref is None else ref
        ax.pcolormesh(t + s0 + t0, f / 1000, P - ref, cmap=cmap, vmin=-75, vmax=0, shading="auto", rasterized=True)
        ax.set_ylim(0, 12)
        ax.set_ylabel("kHz", color="#4a4a46")
        name = ("Recorded brushes (Swirly Drums): stirs, brush taps and digs, hi-hat foot" if kit == "recorded"
                else "Modelled brushes (round 1 passes 1-3): noise through a sampled snare response")
        ax.set_title(name, loc="left", fontsize=11, color="#1f1f1d")
        for bar in range(33, 38):
            ax.axvline(ballad.beat_time(ballad.bar_beat(bar)), color="#c9c8c2", lw=0.8)
        for sp in ax.spines.values():
            sp.set_color("#c9c8c2")
        ax.tick_params(colors="#4a4a46")
    axes[-1].set_xlabel("time (s), bars 33-36, drums alone at the shipped level", color="#4a4a46")
    fig.tight_layout()
    fig.savefig(REVIEW / "brushes.jpg", pil_kwargs={"quality": 88})


if __name__ == "__main__":
    main()
