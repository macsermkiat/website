"""
Re-measure the shipped ballad from the files the site serves (site/public/audio/manifest.json and
its MP3 stems) and draw the review figures.

    python3 music/render/measure.py

Reports: stem durations (sample alignment), tempo (onset autocorrelation of bass + drums), key
(chroma vs. Krumhansl-Kessler profiles), sax spectral centroid (three ways), mix peak (sample and
4x true peak), integrated loudness (ITU-R BS.1770 via pyloudnorm) and loop-seam smoothness.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from lib import SR, SITE_AUDIO, REVIEW, OUT, MUSIC  # noqa: E402

NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def frames(x, n=2048, hop=512):
    w = np.hanning(n)
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * w
    return fr


def centroid_report(x):
    mono = x.mean(axis=1)
    fr = frames(mono)
    S = np.abs(np.fft.rfft(fr, axis=1))
    f = np.fft.rfftfreq(2048, 1 / SR)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    active = rms > rms.max() * 10 ** (-50 / 20)
    tot = S.sum(axis=1)
    c = np.where(tot > 0, (S * f).sum(axis=1) / np.maximum(tot, 1e-20), 0.0)
    ltas = S[active].mean(axis=0)
    return {
        "active_frames_mean_hz": float(c[active].mean()),
        "active_frames_median_hz": float(np.median(c[active])),
        "all_frames_mean_hz": float(c.mean()),
        "long_term_spectrum_hz": float((ltas * f).sum() / ltas.sum()),
    }


def tempo_estimate(x, lo=50, hi=90):
    """Onset-strength autocorrelation, folded so the answer is reported in quarter notes."""
    mono = x.mean(axis=1)
    hop = 441
    fr = frames(mono, 2048, hop)
    S = np.abs(np.fft.rfft(fr, axis=1))
    flux = np.maximum(np.diff(np.log1p(100 * S), axis=0), 0).sum(axis=1)
    flux = flux - np.convolve(flux, np.ones(50) / 50, mode="same")
    flux = np.maximum(flux, 0)
    fps = SR / hop
    ac = signal.fftconvolve(flux, flux[::-1], mode="full")[len(flux) - 1:]
    lags = np.arange(len(ac)) / fps
    bpm = 60 / np.maximum(lags, 1e-9)
    m = (bpm >= lo) & (bpm <= hi)
    best = bpm[m][np.argmax(ac[m])]
    # refine by parabolic interpolation
    i = np.where(m)[0][np.argmax(ac[m])]
    y0, y1, y2 = ac[i - 1], ac[i], ac[i + 1]
    d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return float(60 / ((i + d) / fps)), float(best)


def key_estimate(x, comp="log"):
    """Chroma matched against the Krumhansl-Kessler profiles. comp="log" uses log-compressed
    magnitudes (the usual MIR choice, so the loudest line does not decide the key alone);
    comp="power" is the round-1 measure, which the tenor's long notes dominate."""
    mono = x.mean(axis=1)[::2]
    sr = SR / 2
    f, t, Z = signal.stft(mono, sr, nperseg=8192, noverlap=4096)
    M = np.abs(Z)
    P = M ** 2 if comp == "power" else np.log1p(1000 * M / M.max())
    chroma = np.zeros(12)
    for i, fr in enumerate(f):
        if 55 <= fr <= 2000:
            pc = int(round(12 * np.log2(fr / 440) + 69)) % 12
            chroma[pc] += P[i].sum()
    chroma /= chroma.sum()
    best = None
    for k in range(12):
        for mode, prof in (("major", KK_MAJOR), ("minor", KK_MINOR)):
            r = np.corrcoef(chroma, np.roll(prof, k))[0, 1]
            if best is None or r > best[0]:
                best = (r, f"{NAMES[k]} {mode}")
    return best[1], float(best[0]), chroma


def phrase_dynamics(sax, phrases, min_span=1.5):
    """Level movement inside the tenor's phrases: 50 ms RMS from 0.15 s after the first onset to the
    end of the last note, per phrase of at least `min_span` seconds. Returns the median over phrases
    of the 5th-95th percentile range and of the full range, in dB."""
    x = sax.mean(axis=1) if sax.ndim > 1 else sax
    w = int(0.05 * SR)
    p90, full = [], []
    for ph in phrases:
        a, b = ph[0].t + 0.15, ph[-1].t + ph[-1].dur
        if b - a < min_span:
            continue
        seg = x[int(a * SR):int(b * SR)]
        n = len(seg) // w
        r = 20 * np.log10(np.sqrt((seg[:n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-9)
        p90.append(np.percentile(r, 95) - np.percentile(r, 5))
        full.append(r.max() - r.min())
    return {"phrases": len(p90), "median_p5_p95_range_db": round(float(np.median(p90)), 1),
            "median_full_range_db": round(float(np.median(full)), 1)}


def true_peak(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(np.abs(up).max()))


def seam_report(mix, ls, le):
    """Compare the spliced loop jump with ordinary playback around it."""
    n = int(0.5 * SR)
    joined = np.concatenate([mix[le - n:le], mix[ls:ls + n]])
    step = np.abs(np.diff(joined.mean(axis=1)))
    seam_step = step[n - 1]
    typical = np.percentile(step, 99)
    # 20 ms RMS either side of the jump vs the same across the natural point loopStart
    w = int(0.02 * SR)
    rms = lambda a: 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12)
    jump_db = rms(mix[ls:ls + w]) - rms(mix[le - w:le])
    natural_db = rms(mix[ls:ls + w]) - rms(mix[ls - w:ls])
    # difference between what is played just before the jump and what precedes loopStart
    d = mix[le - n // 2:le] - mix[ls - n // 2:ls]
    resid_db = rms(d) - rms(mix[ls - n // 2:ls])
    # spectral flux at the seam vs the median flux around it
    fr = frames(joined.mean(axis=1), 1024, 256)
    S = np.abs(np.fft.rfft(fr, axis=1))
    flux = np.sqrt((np.diff(S, axis=0) ** 2).sum(axis=1))
    k = (n - 512) // 256
    return {
        "sample_step_at_seam": float(seam_step),
        "p99_sample_step_nearby": float(typical),
        "rms_change_across_seam_db": float(jump_db),
        "rms_change_across_loopStart_in_normal_play_db": float(natural_db),
        "residual_before_jump_vs_before_loopStart_db": float(resid_db),
        "spectral_flux_at_seam_vs_median": float(flux[k - 1:k + 2].max() / np.median(flux)),
    }


def spectrogram_png(x, path, title, fmax=8000):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    ramp = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = LinearSegmentedColormap.from_list("seq_blue", ramp)
    mono = x.mean(axis=1)[::2]
    sr = SR / 2
    f, t, Z = signal.stft(mono, sr, nperseg=2048, noverlap=2048 - 256)
    P = 20 * np.log10(np.abs(Z) + 1e-9)
    P -= P.max()
    m = (f >= 40) & (f <= fmax)
    fig, ax = plt.subplots(figsize=(12.8, 5.2), dpi=100)
    ax.pcolormesh(t, f[m], P[m], cmap=cmap, vmin=-90, vmax=0, shading="auto", rasterized=True)
    ax.set_yscale("log")
    ax.set_ylim(40, fmax)
    ax.set_yticks([50, 100, 200, 500, 900, 2000, 5000])
    ax.set_yticklabels(["50", "100", "200", "500", "900", "2k", "5k"])
    ax.axhline(900, color="#6b6b66", lw=0.8, ls=(0, (4, 3)))
    ax.text(t[-1], 900 * 1.06, "900 Hz ", ha="right", va="bottom", fontsize=9, color="#4a4a46")
    ax.set_xlabel("time (s)", color="#4a4a46")
    ax.set_ylabel("frequency (Hz, log)", color="#4a4a46")
    ax.set_title(title, loc="left", fontsize=12, color="#1f1f1d")
    for s in ax.spines.values():
        s.set_color("#c9c8c2")
    ax.tick_params(colors="#4a4a46")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def overview_jpg(stems, man, path):
    """Loudness of each player over time, with the form: what the arrangement does."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"sax": "#256abf", "piano": "#e0701b", "bass": "#1f8a6e", "drums": "#8c5ad1", "room": "#8a8a84"}
    fig, ax = plt.subplots(figsize=(12.8, 4.6), dpi=100)
    hop = int(0.25 * SR)
    for k in ["sax", "piano", "bass", "drums", "room"]:
        x = stems[k].mean(axis=1)
        n = len(x) // hop
        r = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
        ax.plot(np.arange(n) * 0.25, 20 * np.log10(r + 1e-6), color=cols[k], lw=2 if k != "room" else 1.2, label=k)
    import ballad
    for bar, lab in ((1, "head"), (33, "tenor chorus"), (65, "piano half"), (81, "out head"), (96, "fermata")):
        t = ballad.beat_time(ballad.bar_beat(bar))
        ax.axvline(t, color="#c9c8c2", lw=1)
        ax.text(t + 1, -8, lab, fontsize=9, color="#4a4a46")
    ax.axvspan(man["loopStart"], man["loopEnd"], color="#f0efec", zorder=-1)
    ax.text(man["loopStart"] + 1, -76, "site loop (bars 17-80)", fontsize=9, color="#4a4a46")
    ax.set_ylim(-80, -5)
    ax.set_xlim(0, man["duration"])
    ax.set_xlabel("time (s)", color="#4a4a46")
    ax.set_ylabel("level (dBFS, 250 ms RMS)", color="#4a4a46")
    ax.set_title(f"{man['title']}: stem levels across the form", loc="left", fontsize=12, color="#1f1f1d")
    ax.legend(loc="lower right", ncol=5, frameon=False, fontsize=9)
    for s in ax.spines.values():
        s.set_color("#c9c8c2")
    ax.tick_params(colors="#4a4a46")
    fig.tight_layout()
    fig.savefig(path, pil_kwargs={"quality": 88})
    plt.close(fig)


def main():
    sys.path.insert(0, str(MUSIC / "score"))
    man = json.loads((SITE_AUDIO / "manifest.json").read_text())
    stems = {}
    lengths = {}
    for k, fn in man["stems"].items():
        x, sr = sf.read(str(SITE_AUDIO / fn), always_2d=True, dtype="float32")
        assert sr == SR
        stems[k] = x
        lengths[k] = len(x)
    n = min(lengths.values())
    mix = sum(stems[k][:n] for k in stems)
    meter = pyln.Meter(SR)
    ls, le = int(round(man["loopStart"] * SR)), int(round(man["loopEnd"] * SR))
    key, kr, chroma = key_estimate(mix)
    key_p, kr_p, _ = key_estimate(mix, "power")
    # round 1, pass 4: the recorded brushes are broadband noise that flattens the log chroma of the
    # full mix, so the key is also measured on the pitched stems alone (tenor, piano, bass)
    pitched = stems["sax"][:n] + stems["piano"][:n] + stems["bass"][:n]
    key_t, kr_t, _ = key_estimate(pitched)
    import ballad
    ev = ballad.events()
    head = [n.midi for n in ev["tenor"] if n.beat < ballad.bar_beat(33)]
    t_ref, t_raw = tempo_estimate(stems["bass"][:n] + stems["drums"][:n])
    rep = {
        "files": {k: {"file": man["stems"][k], "bytes": os.path.getsize(SITE_AUDIO / man["stems"][k]),
                      "samples": lengths[k], "seconds": round(lengths[k] / SR, 4)} for k in stems},
        "stems_equal_length": len(set(lengths.values())) == 1,
        "manifest": {k: man[k] for k in ("bpm", "duration", "loopStart", "loopEnd")},
        "tempo_design_bpm": man["bpm"],
        "tempo_measured_bpm": round(t_ref, 2),
        "key_design": man.get("key"),
        "key_measured": key, "key_correlation": round(kr, 3),
        "key_measured_pitched_stems": key_t, "key_correlation_pitched_stems": round(kr_t, 3),
        "key_measured_power_chroma": key_p, "key_correlation_power_chroma": round(kr_p, 3),
        "tenor_head_range_midi": [min(head), max(head)],
        "tenor_head_notes_below_C4": f"{sum(m < 60 for m in head)} of {len(head)}",
        "sax_phrase_dynamics": phrase_dynamics(stems["sax"][:n], ev["phrases"]),
        "piano_voicings": {"count": len(ev["voicings"]),
                           "below_low_interval_limits": len(ballad.voicing_problems(ev["voicings"])),
                           "voices": {str(k): sum(len(v) == k for _, _, v, *_ in ev["voicings"]) for k in (2, 3, 4)}},
        "duration_s": round(n / SR, 3),
        "sax_centroid": {k: round(v, 1) for k, v in centroid_report(stems["sax"]).items()},
        "mix_centroid": {k: round(v, 1) for k, v in centroid_report(mix).items()},
        "mix_sample_peak_dbfs": round(float(20 * np.log10(np.abs(mix).max())), 2),
        "mix_true_peak_dbtp": round(true_peak(mix), 2),
        "mix_integrated_lufs": round(float(meter.integrated_loudness(mix.astype(np.float64))), 2),
        "stem_lufs": {k: round(float(meter.integrated_loudness(stems[k][:n].astype(np.float64))), 2) for k in stems},
        "loop_seam": {k: round(v, 4) for k, v in seam_report(mix, ls, le).items()},
    }
    # ---- pass 3 checks (checks.py): breathing, melody on top, air, intonation, alternate chorus ----
    import checks
    rep["tenor_runs_score"] = checks.runs_summary(checks.tenor_runs_score(ev["tenor"]))
    rep["tenor_runs_audio"] = checks.runs_summary(checks.tenor_runs_audio(stems["sax"][:n]))
    t_head0, t_head1 = ballad.beat_time(0), ballad.beat_time(ballad.bar_beat(33))
    rep["melody_audibility_head"] = checks.melody_audibility(stems["sax"][:n], stems["piano"][:n], ev["tenor"], t_head0, t_head1)
    a, t = checks.piano_top_vs_tenor([x for x in ev["voicings"] if x[0] <= 32], ev["tenor"])
    a2, t2 = checks.piano_top_vs_tenor(ev["voicings"], ev["tenor"])
    rep["piano_top_above_tenor"] = {"head": f"{a} of {t}", "whole_piece": f"{a2} of {t2}",
                                    "max_top_voice_while_tenor_plays": int(max(max(v) for bar, sym, v, *_ in ev["voicings"]
                                                                               if bar < 96 and not 65 <= bar <= 80))}
    rep["sax_air"] = checks.air_band(stems["sax"][:n])
    rep["tenor_sample_intonation"] = checks.intonation(man.get("tenorBank", "musyngkite"))
    alts = []
    for alt in man.get("alternates", []):
        a0, a1 = int(round(alt["start"] * SR)), int(round(alt["end"] * SR))
        seg = {k: sf.read(str(SITE_AUDIO / fn), always_2d=True, dtype="float32")[0] for k, fn in alt["stems"].items()}
        L = min(len(v) for v in seg.values())
        mix_b = mix[a0:a0 + L].copy()
        for k, v in seg.items():
            mix_b += v[:L] - stems[k][a0:a0 + L]
        # skip the first 0.1 s: an MP3 without a gapless header starts with the decoder's priming
        e0, e1 = int(0.1 * SR), int(0.5 * SR)
        diff = {k: round(float(20 * np.log10(np.sqrt(np.mean((v[e0:e1] - stems[k][a0 + e0:a0 + e1]) ** 2)) /
                                              (np.sqrt(np.mean(stems[k][a0 + e0:a0 + e1] ** 2)) + 1e-12) + 1e-12)), 1)
                for k, v in seg.items()}
        a_runs = checks.tenor_runs_audio(seg["sax"][:L])
        alts.append({"name": alt["name"], "decoded_samples": {k: len(v) for k, v in seg.items()},
                     "expected_samples": a1 - a0,
                     "start_edge_residual_vs_main_db_0.1_to_0.5s": diff,
                     "mix_peak_dbfs": round(float(20 * np.log10(np.abs(mix_b).max())), 2),
                     "mix_lufs_segment": round(float(meter.integrated_loudness(mix_b.astype(np.float64))), 2),
                     "main_mix_lufs_same_segment": round(float(meter.integrated_loudness(mix[a0:a0 + L].astype(np.float64))), 2),
                     "sax_centroid_hz": round(centroid_report(seg["sax"][:L])["active_frames_mean_hz"], 1),
                     "tenor_runs_audio": checks.runs_summary([(x + alt["start"], y + alt["start"]) for x, y in a_runs])})
    rep["alternates"] = alts
    mf = SITE_AUDIO / man["mix"] if man.get("mix") else None
    if mf and mf.exists():
        y, _ = sf.read(str(mf), always_2d=True, dtype="float32")
        L = min(len(y), n)
        rep["shipped_mix_file_vs_stem_sum_residual_db"] = round(float(
            20 * np.log10(np.sqrt(np.mean((y[:L] - mix[:L]) ** 2)) / np.sqrt(np.mean(mix[:L] ** 2)))), 1)
    REVIEW.mkdir(parents=True, exist_ok=True)
    spectrogram_png(stems["sax"], REVIEW / "spectrogram_sax.png",
                    f"Tenor stem: spectrogram (spectral centroid {rep['sax_centroid']['active_frames_mean_hz']:.0f} Hz, dashed line = 900 Hz)")
    spectrogram_png(mix, REVIEW / "spectrogram_mix.png",
                    f"Full mix: spectrogram ({rep['mix_integrated_lufs']} LUFS, peak {rep['mix_sample_peak_dbfs']} dBFS)", fmax=16000)
    overview_jpg({k: v[:n] for k, v in stems.items()}, man, REVIEW / "arrangement.jpg")
    (OUT / "measurements.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
