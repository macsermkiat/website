"""Write the score as a type-1 MIDI file (grid-quantised, with chord symbols and section markers)
and a readable lead sheet with the piano voicings."""
from __future__ import annotations

import mido

import ballad

TPB = 480
NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def nn(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def _tick(beat):
    return int(round(beat * TPB))


def _track(name, program, channel, notes):
    """notes: (start_beat, len_beats, midi, vel)"""
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage("track_name", name=name, time=0))
    tr.append(mido.Message("program_change", program=program, channel=channel, time=0))
    evs = []
    for b, L, m, v in notes:
        evs.append((_tick(b), 1, m, max(1, min(127, int(v * 127)))))
        evs.append((_tick(b + max(L, 0.05)), 0, m, 0))
    evs.sort(key=lambda e: (e[0], e[1]))
    now = 0
    for t, on, m, v in evs:
        tr.append(mido.Message("note_on" if on else "note_off", note=m, velocity=v if on else 0, channel=channel, time=t - now))
        now = t
    return tr


def write(ev, path):
    mf = mido.MidiFile(type=1, ticks_per_beat=TPB)
    bars = ev["bars"]
    # conductor: tempo map, time signature, section markers, chord symbols
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage("track_name", name=ballad.TITLE, time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0))
    tr.append(mido.MetaMessage("key_signature", key="Cm", time=0))
    metas = [(0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(ballad.TEMPO)))]
    B = ballad.RIT_B0
    while B < ballad.bar_beat(97):
        dt = ballad.beat_time(B + 1) - ballad.beat_time(B)
        metas.append((_tick(B), mido.MetaMessage("set_tempo", tempo=int(dt * 1e6))))
        B += 1
    labels = {1: "Head A1", 9: "A2", 17: "B (bridge)", 25: "A3", 33: "Tenor chorus", 49: "Tenor: bridge",
              65: "Piano half-chorus", 81: "Out head (bridge)", 89: "Out head A3", 93: "ritardando", 96: "fermata"}
    for b in bars:
        B0 = ballad.bar_beat(b["bar"])
        if b["bar"] in labels:
            metas.append((_tick(B0), mido.MetaMessage("marker", text=labels[b["bar"]])))
        acc = 0
        for ch, nb in b["segs"]:
            metas.append((_tick(B0 + acc), mido.MetaMessage("text", text=ch.symbol)))
            acc += nb
    metas.sort(key=lambda x: x[0])
    now = 0
    for t, m in metas:
        m.time = t - now
        tr.append(m)
        now = t
    mf.tracks.append(tr)
    mf.tracks.append(_track("Tenor sax", 66, 0, [(n.beat, n.beats, n.midi, n.vel) for n in ev["tenor"]]))
    mf.tracks.append(_track("Piano", 0, 1, [(n.beat, n.beats, n.midi, n.vel) for n in ev["piano"]]))
    mf.tracks.append(_track("Double bass", 32, 2, [(n.beat, n.beats, n.midi, n.vel) for n in ev["bass"]]))
    # drums (GS brush kit numbering): 38 brush tap, 40 brush swirl, 36 kick, 44 pedal hat, 51 ride
    kit = {"tap": 38, "sweep": 40, "kick": 36, "hat": 44, "ride": 51, "swell": 49}
    dn = []
    for e in ev["drums"]:
        b = time_to_beat(e["t"])
        L = (time_to_beat(e["t1"]) - b) if "t1" in e else 0.25
        dn.append((b, L, kit[e["kind"]], float(e["vel"])))
    mf.tracks.append(_track("Drums (brushes)", 40, 9, dn))
    mf.save(path)


def time_to_beat(t):
    lo, hi = 0.0, ballad.bar_beat(98)
    for _ in range(50):
        mid = (lo + hi) / 2
        if ballad.beat_time(mid) < t:
            lo = mid
        else:
            hi = mid
    return lo


def write_leadsheet(ev, path):
    bars = ev["bars"]
    lines = [f"# {ballad.TITLE}", "",
             "An original jazz ballad for the Nachtmarkt bandstand quartet: tenor sax, piano, double bass and drums with brushes.",
             "Generated from `music/score/ballad.py` (the source of truth); the same notes are in `ballad.mid`.", "",
             f"- Key: {ballad.KEY}, with warm turns to E-flat major 7#11, B-flat major and A-flat major (first written in C minor, moved down a fourth so the tenor head sits in the subtone register, D3-E4)",
             f"- Metre and tempo: 3/4, quarter = {ballad.TEMPO:g} (a slow jazz waltz ballad), ritardando from bar {ballad.RIT_FROM_BAR}, rubato fermata on bar 96",
             "- Form: 32-bar AABA (A = 8 bars, B = 8 bars)", "",
             "| Bars | Section | Who leads | Bass | Brushes |", "|---|---|---|---|---|",
             "| pickup, 1-32 | Head: A1 A2 B A3 | tenor (melody) | one-feel (A1), then two-feel | sweeps, taps on 2 and 3, feathered kick; foot hat from the bridge |",
             "| 33-64 | Tenor chorus | tenor, written-out improvisation with space | two-feel, walking from bar 41 | taps busier, hat on 2 and 3, brushed ride at the bridge |",
             "| 65-80 | Piano half-chorus (A1 A2) | piano | walking | lighter |",
             "| 81-96 | Out head from the bridge (B A3) | tenor | two-feel; low G under the fermata | ritardando, cymbal swell at the end |", "",
             "The site loops bars 17-80. Bar 80 ends exactly like bar 16 (tenor pickup F, A into the bridge, same comp, bass and brush), so the jump back is seamless.", "",
             "## Changes", "",
             "ii-V-i motion is everywhere: Am7b5-D7b9-Gm9 (bars 3-5), Cm9-F13-Bbmaj9 (6-7), Dm7-G7b9-Cm9 (A2, 7-8), Em7b5-A7b9-Dm9 (bridge 2-3), Bbm9-Eb13-Abmaj9 (bridge 5-6), Am7b5-D7alt (bridge 7-8).",
             "Tritone substitutions: Db7#11 for G7 (bridge 3), B7#11 for F7 (bridge 4), Ab7#11 for D7 (A3, bar 7).", ""]
    for sec, rng in (("A1", range(1, 9)), ("A2", range(9, 17)), ("B", range(17, 25)), ("A3", range(25, 33))):
        cells = []
        for b in bars[rng.start - 1:rng.stop - 1]:
            cells.append(" ".join(f"{c.symbol}" + ("" if nb == 3 else f"({nb})") for c, nb in b["segs"]))
        lines.append(f"**{sec}** | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["(n) = beats when a bar holds two chords (2 + 1).", "",
              "## Head melody (tenor, concert pitch)", "",
              "Written as `note:beats`, bars separated by `|`; `_` ties, `r` rests. C4 is middle C.", "", "```",
              ballad.HEAD.strip(), "```", "",
              "## Piano voicings (head, bars 1-32)", "",
              "Rootless voicings (Bill Evans A/B forms: 3-5-7-9 or 7-9-3-5 and their altered cousins, or a three-note shell of one), chosen by the smallest total voice movement from the previous chord. Every voicing keeps the low interval limits (no minor 2nd below E3, no major 2nd below E-flat 3, no minor 3rd below C3), so nothing clusters in the bass register. Because the tenor's head now sits low (D3-E4), the comp sits just above the tune in the piano's middle register instead of under it, and a voice a semitone from the tune note is left out rather than moved down. The bass plays the roots.", "",
              "| Bar | Chord | Voicing (low to high) |", "|---|---|---|"]
    for bar, sym, v in ev["voicings"]:
        if bar <= 32:
            lines.append(f"| {bar} | {sym} | {' '.join(nn(m) for m in v)} |")
    lines += ["", "## Tenor chorus (bars 33-64, written-out improvisation)", "", "```", ballad.TENOR_CHORUS.strip(), "```", "",
              "## Piano half-chorus (bars 65-80, right hand)", "", "```", ballad.PIANO_SOLO.strip(), "```", "",
              "## Out head (from beat 3 of bar 80)", "", "```", ballad.OUT_HEAD.strip(), "```", ""]
    path.write_text("\n".join(lines))
