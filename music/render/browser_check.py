"""
Check the shipped MP3s as Chromium decodes them (decodeAudioData), against the renderer's timeline.

    python3 -m http.server 8765 --bind 127.0.0.1 --directory site/public/audio &
    node music/render/browser/decode_check.mjs 8765 music/.cache/browser_decode.json
    python3 music/render/browser_check.py music/.cache/browser_decode.json

Reports, per stem: decoded length (all equal = sample-aligned), the lag of the decoded audio
against the rendered WAV (0 = the 1105-sample pre-shift is exactly right in this browser), and the
loop jump as the site plays it (last samples before loopEnd followed by the samples from loopStart),
next to the same measure across loopStart in ordinary playback. Writes music/out/browser_check.json.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import soundfile as sf

from lib import OUT, SR


def lag(a, b, max_lag=3000):
    """Lag (samples) of b against a, by cross-correlation over +-max_lag."""
    a = a - a.mean()
    b = b - b.mean()
    n = min(len(a), len(b))
    best, bl = -2.0, 0
    for L in range(-max_lag, max_lag + 1, 1):
        if L >= 0:
            x, y = a[:n - L], b[L:n]
        else:
            x, y = a[-L:n], b[:n + L]
        c = float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))
        if c > best:
            best, bl = c, L
    return bl, best


def main(path):
    d = json.loads(open(path).read())
    man = d["manifest"]
    rep = {"userAgent": d["userAgent"], "stems": {}}
    ref_names = {"sax": "stem_sax", "piano": "stem_piano", "bass": "stem_bass", "drums": "stem_drums",
                 "room": "stem_room", "mix": "ballad_mix"}
    ls, le = man["loopStart"], man["loopEnd"]
    for k, ref in ref_names.items():
        rec = d["stems"][f"{k}@44100"]
        wav = sf.read(str(OUT / f"{ref}.wav"), dtype="float32", always_2d=True)[0][:, 0]
        start = np.array(rec["start"], np.float32)
        # coarse lag on a decimated copy (fast), then refine at full rate
        s0 = int(0.25 * SR)
        L, c = lag(wav[s0:s0 + int(2.5 * SR)], start[s0:s0 + int(2.5 * SR)], 400)
        # the site's loop jump: 1 s before loopEnd, then 1 s from loopStart
        before = np.array(rec["atLoopEnd"], np.float32)[:SR]
        after = np.array(rec["atLoopStart"], np.float32)[SR:]
        joined = np.concatenate([before, after])
        step = np.abs(np.diff(joined))
        w = int(0.02 * SR)
        rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
        rep["stems"][k] = {
            "decoded_samples_44k1": rec["length"],
            "decoded_samples_48k": d["stems"][f"{k}@48000"]["length"],
            "lag_vs_render_samples": int(L), "lag_correlation": round(c, 4),
            "loop_jump_step": round(float(step[SR - 1]), 5),
            "loop_jump_p99_step_nearby": round(float(np.percentile(step, 99)), 5),
            "loop_jump_level_change_db": round(float(rms(after[:w]) - rms(before[-w:])), 2),
            "same_in_normal_play_across_loopStart_db": round(float(
                rms(np.array(rec["atLoopStart"], np.float32)[SR:SR + w]) - rms(np.array(rec["atLoopStart"], np.float32)[SR - w:SR])), 2),
        }
    lens = {v["decoded_samples_44k1"] for v in rep["stems"].values()}
    rep["all_equal_length"] = len(lens) == 1
    rep["decoded_duration_s"] = round(min(lens) / SR, 6)
    (OUT / "browser_check.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(OUT.parent / ".cache" / "browser_decode.json"))
