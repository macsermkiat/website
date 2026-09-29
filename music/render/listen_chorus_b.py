"""The listening excerpt of the second written tenor chorus (the one the site plays on every second
pass through the loop): the chorus-B mix from 2 s before the alternate section to 2 s after it,
with short fades, at 128 kbps.

    python3 music/render/listen_chorus_b.py     # after render.py; writes music/listen/chorus_b_excerpt.mp3
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, OUT, MUSIC, SITE_AUDIO  # noqa: E402
from render import encode  # noqa: E402


def main():
    man = json.loads((SITE_AUDIO / "manifest.json").read_text())
    alt = man["alternates"][0]
    x, sr = sf.read(str(OUT / "ballad_mix_chorus_b.wav"), dtype="float32", always_2d=True)
    assert sr == SR
    a, b = int((alt["start"] - 2.0) * SR), int((alt["end"] + 2.0) * SR)
    seg = x[a:b].copy()
    f = int(0.5 * SR)
    seg[:f] *= np.linspace(0, 1, f, dtype=np.float32)[:, None]
    seg[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    out = MUSIC / "listen" / "chorus_b_excerpt.mp3"
    out.write_bytes(encode(seg, 128))
    print(f"{out}: {len(seg) / SR:.1f} s")


if __name__ == "__main__":
    main()
