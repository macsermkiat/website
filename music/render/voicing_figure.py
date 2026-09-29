"""Piano comp register, an earlier pass against now: every voicing as dots at its pitches, with
the tenor line, the E3 line (below which 2nds are muddy) and the B-flat 4 cap on the comp's top
voice while the tenor plays.

    python3 music/render/voicing_figure.py [old_ballad.py]

Without the argument only the current score is drawn."""
from __future__ import annotations

import importlib.util
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from lib import REVIEW  # noqa: E402
import ballad  # noqa: E402

NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def muddy(v):
    v = sorted(v)
    return any(b - a <= 2 and a < 52 for a, b in zip(v, v[1:]))


def panel(ax, mod, title, bars=(1, 32)):
    ev = mod.events()
    x0 = 0
    for bar, sym, v, *_ in ev["voicings"]:
        pass
    # x = bar + position of the chord inside the bar
    seen = {}
    bad = 0
    for bar, sym, v, *_ in ev["voicings"]:
        if not bars[0] <= bar <= bars[1]:
            continue
        k = seen.get(bar, 0)
        seen[bar] = k + 1
        x = bar + 0.5 * k
        m = muddy(v)
        bad += m
        ax.plot([x] * len(v), v, "o", ms=4.5, color="#c0392b" if m else "#256abf", zorder=3,
                mfc="none" if len(v) == 2 else None)
        if len(v) == 2:
            ax.annotate("two-note shell", (x, max(v)), xytext=(x + 0.8, max(v) + 5), fontsize=8, color="#1f1f1d",
                        arrowprops=dict(arrowstyle="-", color="#6b6b66", lw=0.8))
        ax.plot([x, x], [min(v), max(v)], color="#c0392b" if m else "#9ec5f4", lw=1, zorder=2)
    for key, col in (("tenor", "#e0701b"), ("tenor_b", "#f2b27a")):
        for n in ev.get(key, []):
            if not mod.bar_beat(bars[0]) <= n.beat < mod.bar_beat(bars[1] + 1):
                continue
            if key == "tenor_b" and bars[1] <= 32:
                continue
            b = (n.beat - mod.PICKUP) / mod.METER + 1
            ax.plot([b, b + n.beats / mod.METER], [n.midi, n.midi], color=col, lw=2.2, solid_capstyle="butt", zorder=1)
    ax.axhline(52, color="#6b6b66", lw=0.8, ls=(0, (4, 3)))
    ax.text(bars[1] + 1.2, 52.4, "E3", fontsize=8, color="#4a4a46", va="bottom", ha="right")
    ax.set_ylim(38, 80)
    ax.set_xlim(bars[0] - 0.5, bars[1] + 1.3)
    ax.set_yticks(range(40, 81, 5))
    ax.set_yticklabels([f"{NAMES[m % 12]}{m // 12 - 1}" for m in range(40, 81, 5)])
    ax.axhline(70, color="#6b6b66", lw=0.8, ls=(0, (1, 2)))
    ax.text(bars[1] + 1.2, 70.4, "Bb4", fontsize=8, color="#4a4a46", va="bottom", ha="right")
    head = [v for bar, sym, v, *_ in ev["voicings"] if bars[0] <= bar <= bars[1]]
    two = sum(len(v) == 2 for bar, sym, v, *_ in ev["voicings"])
    over = sum(max(v) > 70 for v in head)
    ax.set_title(f"{title}: {bad} with a 2nd below E3, {over} of {len(head)} tops above Bb4, "
                 f"{two} two-note shells in the whole piece", loc="left", fontsize=10.5, color="#1f1f1d")
    for s in ax.spines.values():
        s.set_color("#c9c8c2")
    ax.tick_params(colors="#4a4a46", labelsize=8)


BARS = (33, 64)   # round 1 pass 4: the tenor chorus, where bar 46 had the last two-note shell


def main():
    old = sys.argv[1] if len(sys.argv) > 1 else None
    rows = 2 if old else 1
    fig, axes = plt.subplots(rows, 1, figsize=(12.8, 3.4 * rows + 0.6), dpi=100, sharex=True)
    axes = axes if rows > 1 else [axes]
    if old:
        panel(axes[0], load(old, "ballad_earlier"), "Pass 3: comp (blue), chorus A (orange), chorus B (light)", BARS)
    panel(axes[-1], ballad, "Pass 4: open shell at bar 46", BARS)
    axes[-1].set_xlabel("bar", color="#4a4a46")
    fig.tight_layout()
    fig.savefig(REVIEW / "piano_voicings.jpg", pil_kwargs={"quality": 88})


if __name__ == "__main__":
    main()
