"""
"Lanterns After Closing" -- an original jazz ballad for the Nachtmarkt bandstand quartet
(tenor saxophone, piano, double bass, drums with brushes).

Composed for this site by the music writer. Not based on any existing song: the melody, the
changes and the solos are all written here. The file is the score: the chord changes, the
written head, the written-out "improvised" tenor chorus and piano half-chorus, and the rules the
rhythm section follows (voice-led rootless piano voicings, two-feel and walking bass, brush
pattern). `events()` turns it into timed, humanised note events for the renderer and the MIDI file.

Key G minor (warm turns to E-flat major 7#11, B-flat major and A-flat major), 3/4, quarter = 66.
The piece was first written in C minor and moved down a fourth in round 1, pass 2, so that the
tenor's head sits mostly below concert C4, where a subtone lives (the head spans D3-E4).
Form: 32-bar AABA (A = 8 bars, B = 8 bars).

    pickup  1 beat (sax, piano)
    bars  1-32   head            tenor melody, piano comps, bass one-feel then two-feel
    bars 33-64   tenor chorus    written-out improvisation with space, bass walks from bar 41
    bars 65-80   piano half      piano solo over A A, bass walks, tenor lays out
    bars 81-96   out head        tenor from the bridge (B A); ritardando from bar 93,
                                 bar 96 is a rubato fermata on G minor 6/9
    TENOR_CHORUS_B               a second written tenor chorus over bars 33-64, rendered as
                                 alternate sax and room segments for every second pass of the loop

Breathing (round 1, pass 3): every written rest of half a beat or more ends a phrase and is heard as
a breath, and the head, the chorus and the out head have breaths written in, so the tenor never
plays more than about 9 s without one.

The site loops bars 17-80 (head bridge .. end of piano half-chorus): the last beat of bar 80 is
played exactly like the last beat of bar 16 (same pickup, same comp, same bass and brush), so the
jump back to bar 17 is musically and acoustically seamless.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

TITLE = "Lanterns After Closing"
TEMPO = 66.0          # quarter notes per minute
METER = 3             # beats per bar
LEAD = 0.30           # seconds of silence before the pickup
PICKUP = 1            # beats of pickup before bar 1
KEY = "G minor"
BARS = 96
LOOP_BARS = (17, 81)  # loop from the downbeat of bar 17 to the downbeat of bar 81
RIT_FROM_BAR = 93     # ritardando starts here
SWING = 0.56          # position of the off-beat eighth inside a beat (0.5 = straight)

# --------------------------------------------------------------------------------------------
# harmony
# --------------------------------------------------------------------------------------------
NOTE_PC = {"C": 0, "Db": 1, "C#": 1, "D": 2, "Eb": 3, "D#": 3, "E": 4, "Fb": 4, "F": 5, "Gb": 6,
           "F#": 6, "G": 7, "Ab": 8, "G#": 8, "A": 9, "Bb": 10, "A#": 10, "B": 11, "Cb": 11}

# chord qualities: chord tones (for bass lines and melody checks), scale (for passing notes)
# and the two rootless piano voicing shapes (Bill Evans "A" and "B" forms, intervals over root).
QUALITIES = {
    "m9":      dict(tones=[0, 3, 7, 10, 14], scale=[0, 2, 3, 5, 7, 9, 10],  A=[3, 7, 10, 14], B=[10, 14, 15, 19]),
    "m7":      dict(tones=[0, 3, 7, 10],     scale=[0, 2, 3, 5, 7, 9, 10],  A=[3, 7, 10, 14], B=[10, 14, 15, 19]),
    "m69":     dict(tones=[0, 3, 7, 9, 14],  scale=[0, 2, 3, 5, 7, 9, 11],  A=[3, 7, 9, 14],  B=[9, 14, 15, 19]),
    "maj9":    dict(tones=[0, 4, 7, 11, 14], scale=[0, 2, 4, 5, 7, 9, 11],  A=[4, 7, 11, 14], B=[11, 14, 16, 19]),
    "maj7#11": dict(tones=[0, 4, 7, 11, 18], scale=[0, 2, 4, 6, 7, 9, 11],  A=[4, 11, 14, 18], B=[11, 14, 16, 18]),
    "7b9":     dict(tones=[0, 4, 7, 10, 13], scale=[0, 1, 4, 5, 7, 8, 10],  A=[4, 8, 10, 13], B=[10, 13, 16, 20]),
    "7alt":    dict(tones=[0, 4, 10, 13, 15, 20], scale=[0, 1, 3, 4, 6, 8, 10], A=[4, 8, 10, 15], B=[10, 15, 16, 20]),
    "13":      dict(tones=[0, 4, 7, 10, 14, 21], scale=[0, 2, 4, 5, 7, 9, 10], A=[4, 9, 10, 14], B=[10, 14, 16, 21]),
    "7#11":    dict(tones=[0, 4, 7, 10, 18], scale=[0, 2, 4, 6, 7, 9, 10],  A=[4, 6, 10, 14], B=[10, 14, 16, 18]),
    "m7b5":    dict(tones=[0, 3, 6, 10],     scale=[0, 1, 3, 5, 6, 8, 10],  A=[3, 6, 10, 12], B=[10, 12, 15, 18]),
}
SYMBOL_QUALITY = {"m9": "m9", "m7": "m7", "m6/9": "m69", "maj9": "maj9", "maj7#11": "maj7#11",
                  "7b9": "7b9", "7alt": "7alt", "13": "13", "7#11": "7#11", "m7b5": "m7b5"}


@dataclass
class Chord:
    symbol: str
    root: int      # pitch class
    quality: str

    @property
    def q(self):
        return QUALITIES[self.quality]


def parse_chord(sym: str) -> Chord:
    root = sym[:2] if len(sym) > 1 and sym[1] in "b#" else sym[:1]
    rest = sym[len(root):]
    return Chord(sym, NOTE_PC[root], SYMBOL_QUALITY[rest])


# each bar: list of (chord symbol, beats). ii-V-i cadences are marked in the comments.
A1 = [[("Gm9", 3)], [("Ebmaj7#11", 3)],
      [("Am7b5", 3)], [("D7b9", 3)],                    # ii-V ...
      [("Gm9", 2), ("G7b9", 1)],                        # ... i, then V of iv
      [("Cm9", 2), ("F13", 1)],                        # ii-V of B-flat ...
      [("Bbmaj9", 2), ("Ebmaj7#11", 1)],                # ... I (relative major), IV
      [("Am7b5", 2), ("D7alt", 1)]]                     # ii-V back to G minor
A2 = A1[:4] + [[("Gm9", 2), ("G7b9", 1)],
               [("Cm9", 2), ("F13", 1)],
               [("Dm7", 2), ("G7b9", 1)],               # ii-V of C minor
               [("Cm9", 2), ("F7b9", 1)]]              # ii-V into the bridge in B-flat
B = [[("Bbmaj9", 3)],
     [("Em7b5", 2), ("A7b9", 1)],                       # ii-V ...
     [("Dm9", 2), ("Db7#11", 1)],                       # ... i; Db7 = tritone sub of G7
     [("Cm9", 2), ("B7#11", 1)],                        # ii - (B7 = tritone sub of F7) ...
     [("Bbm9", 2), ("Eb13", 1)],                        # B-flat minor: ii-V of A-flat
     [("Abmaj9", 3)],                                   # A-flat major (Neapolitan warmth)
     [("Am7b5", 3)], [("D7alt", 3)]]                    # ii-V back to G minor
A3 = A1[:6] + [[("Am7b5", 2), ("Ab7#11", 1)],           # ii - tritone-sub V ...
               [("Gm9", 2), ("D7alt", 1)]]              # ... i, turnaround
ENDING_A3 = A3[:7] + [[("Gm6/9", 3)]]                   # final fermata

SECTION_BARS = {"A1": A1, "A2": A2, "B": B, "A3": A3}


def chart():
    """The 96 bars: list of dicts with bar number, chord segments, section, part."""
    plan = [("head", ["A1", "A2", "B", "A3"]),
            ("tenor", ["A1", "A2", "B", "A3"]),
            ("piano", ["A1", "A2"]),
            ("out", ["B", "A3end"])]
    bars = []
    n = 1
    for part, sections in plan:
        for sec in sections:
            src = ENDING_A3 if sec == "A3end" else SECTION_BARS[sec]
            for i, segs in enumerate(src):
                bars.append(dict(bar=n, part=part, section=sec.replace("end", ""), idx=i,
                                 segs=[(parse_chord(s), b) for s, b in segs]))
                n += 1
    assert len(bars) == BARS
    return bars


def chord_at(bars, beat):
    """Chord sounding at global beat (bar 1 downbeat = PICKUP)."""
    if beat < PICKUP:
        return parse_chord("D7alt")
    b = int((beat - PICKUP) // METER)
    b = min(b, len(bars) - 1)
    pos = (beat - PICKUP) - b * METER
    acc = 0
    for ch, n in bars[b]["segs"]:
        if pos < acc + n - 1e-9:
            return ch
        acc += n
    return bars[b]["segs"][-1][0]


# --------------------------------------------------------------------------------------------
# time: beats -> seconds (constant tempo, ritardando at the end, rubato fermata on bar 96)
# --------------------------------------------------------------------------------------------
def bar_beat(bar, beat=0.0):
    return PICKUP + (bar - 1) * METER + beat


RIT_B0 = bar_beat(RIT_FROM_BAR)
FERMATA_B0 = bar_beat(96)
RIT_END_TEMPO = 48.0
FERMATA_BEAT_SEC = 1.55   # bar 96: each beat of the fermata bar lasts this long


def beat_time(B: float) -> float:
    spb = 60.0 / TEMPO
    if B <= RIT_B0:
        return LEAD + B * spb
    t = LEAD + RIT_B0 * spb
    # tempo falls linearly from TEMPO to RIT_END_TEMPO over bars 93-95 (9 beats): integrate dt = db / tempo
    L = FERMATA_B0 - RIT_B0
    x = min(B, FERMATA_B0) - RIT_B0
    k = (RIT_END_TEMPO - TEMPO) / L
    # t = 60 * integral_0^x db / (TEMPO + k b) = 60/k ln((TEMPO + k x)/TEMPO)
    t += 60.0 / k * math.log((TEMPO + k * x) / TEMPO)
    if B > FERMATA_B0:
        t += (B - FERMATA_B0) * FERMATA_BEAT_SEC
    return t


def swing(pos_in_beat_units: float) -> float:
    """Move off-beat eighths (x.5) to the ballad swing position; leave other subdivisions."""
    f = pos_in_beat_units - math.floor(pos_in_beat_units)
    if abs(f - 0.5) < 1e-6:
        return math.floor(pos_in_beat_units) + SWING
    return pos_in_beat_units


# --------------------------------------------------------------------------------------------
# written parts. Tokens: "Eb4:1.5" note (pitch, beats); "r:1" rest; "_:2" tie (extend previous
# note); "|" bar line (checked). Fractions like 1/3 allowed. C4 = MIDI 60.
# --------------------------------------------------------------------------------------------
def midi(name: str) -> int:
    p = name[:-1]
    octv = int(name[-1])
    return 12 * (octv + 1) + NOTE_PC[p]


HEAD = """
D3:1 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:1 | r:.5 F3:.5 A3:1 G3:1 | C4:1 A3:.5 Eb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:1.5 r:.5 G3:.5 Bb3:.5 | A3:.5 G3:.5 A3:.5 C4:.5 Eb4:1 | D4:1.5 C4:.5 F#3:.5 r:.5 |
D4:1.5 C4:.5 B3:1 | C4:.5 Eb4:1.5 D4:.5 r:.5 | C4:2 B3:.5 Ab3:.5 | G3:1.5 r:.5 F3:.5 A3:.5 |
D4:1.5 C4:.5 A3:1 | G3:1 r:.5 Bb3:.5 C#4:1 | D4:.5 E4:1.5 B3:1 | Bb3:1.5 G3:.5 A3:.5 r:.5 |
F3:.5 Ab3:.5 C4:1.5 Bb3:.5 | C4:1.5 Bb3:.5 G3:.5 r:.5 | Eb3:1 G3:.5 A3:.5 C4:1 | Eb4:1 D4:.5 Bb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:.5 r:.5 | C4:1 Bb3:.5 A3:.5 Eb3:.5 F#3:.5 | G3:2.5 r:.5 |
"""

TENOR_CHORUS = """
r:1.5 D3:.5 G3:.5 A3:.5 | Bb3:2.5 A3:.5 | G3:1 r:2 | r:.5 F#3:.5 A3:.5 C4:.5 Eb4:.5 D4:.5 |
Bb3:1.5 A3:.5 B3:.5 D4:.5 | Eb4:1 D4:.5 C4:.5 A3:1 | D4:1.5 r:.5 G3:.5 Bb3:.5 | A3:.5 C4:.5 Eb4:1 D4:.25 C4:.25 Bb3:.25 Ab3:.25 |
F#3:.5 G3:2.5 | r:1 F3:.5 G3:.5 A3:1 | C4:1.5 Bb3:.5 A3:.5 G3:.5 | F#3:1 r:2 |
r:1 Bb3:.5 D4:.5 F4:.5 Eb4:.5 | D4:1 Eb4:.25 D4:.25 C4:.25 Bb3:.25 A3:1 | C4:1.5 A3:.5 B3:.5 Ab3:.5 | G3:1.5 r:.5 A3:.5 C4:.5 |
D4:1 F4:2 | E4:.5 D4:.5 Bb3:1 C#4:.5 E4:.5 | F4:1 E4:.5 C4:.5 B3:.5 Ab3:.5 | r:.5 D4:.25 F4:.25 Eb4:.5 C4:.5 A3:.5 F#3:.5 |
F3:.5 Ab3:.5 C4:1 Db4:.5 C4:.5 | C4:2.5 r:.5 | r:.5 Eb3:.5 G3:.5 A3:.5 C4:.5 Eb4:.5 | D4:1/3 Eb4:1/3 D4:1/3 C4:.5 Bb3:.5 Ab3:.5 F#3:.5 |
G3:1.5 r:1.5 | r:.5 D3:.5 G3:.5 Bb3:.5 D4:1 | C4:.75 Bb3:.25 A3:.5 G3:.5 Eb3:1 | F#3:.5 A3:.5 C4:.5 Eb4:.5 r:1 |
D4:2 B3:1 | Bb3:.5 G3:.5 Eb3:.5 r:.5 D3:1 | Eb3:.5 G3:.5 C4:1 F#3:.5 Eb3:.5 | G3:2 r:1 |
"""

PIANO_SOLO = """
r:1 D4:.5 F4:.5 A4:.5 Bb4:.5 | A4:1.5 G4:.5 D4:1 | Eb4:.5 G4:.5 C5:1 Bb4:.5 A4:.5 | F#4:.5 Eb4:.5 C4:.5 A3:.5 F#3:1 |
G4:1.5 r:.5 B4:.5 Ab4:.5 | G4:1/3 Ab4:1/3 G4:1/3 Eb4:1 D4:1 | F4:.5 A4:.5 C5:1 Bb4:.5 G4:.5 | A4:1 Eb4:1 F#4:.5 Ab4:.5 |
Bb4:2 r:1 | r:.5 Bb4:.5 D5:.5 A4:.5 G4:1 | Eb4:.25 G4:.25 A4:.25 C5:.25 Eb5:1 D5:.5 C5:.5 | Bb4:.5 A4:.5 F#4:.5 Eb4:.5 C4:1 |
Bb3:.5 D4:.5 A4:1 Ab4:1 | G4:1.5 Eb4:.5 D4:.5 C4:.5 | C4:.5 F4:.5 A4:1 Ab4:.5 F4:.5 | Eb4:2 r:1 |
"""

# the tenor re-enters on beat 3 of bar 80 with the same pickup as bar 16, then plays the out head
OUT_HEAD = """
r:2 F3:.5 A3:.5 |
D4:1.5 C4:.5 A3:1 | G3:1 r:.5 Bb3:.5 C#4:1 | D4:.5 E4:1.5 B3:1 | Bb3:1.5 G3:.5 A3:.5 r:.5 |
F3:.5 Ab3:.5 C4:1.5 Bb3:.5 | C4:2 Bb3:.5 r:.5 | Eb3:1 G3:.5 A3:.5 C4:1 | Eb4:1 D4:.5 Bb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:.5 r:.5 | C4:1 Bb3:.5 A3:.5 Eb3:.5 F#3:.5 | G3:1 Bb3:.5 A3:1.5 |
"""

# A second written tenor chorus over the same changes (bars 33-64), played on alternate passes of
# the site's loop so a visitor who stays hears a different solo the second time round. Same breath
# plan as the first chorus (the piano's fills answer in the gaps both choruses leave), different
# lines: a sparser first A built on a falling Bb-A motif, a sequence in the second A, long notes
# in the bridge, and a low, dark last A.
TENOR_CHORUS_B = """
r:2 D4:.5 C4:.5 | Bb3:2 A3:1 | G3:1.5 r:1.5 | r:.5 A3:.5 C4:.5 Eb4:.5 D4:.5 C4:.5 |
Bb3:1 A3:.5 G3:.5 B3:1 | C4:2 r:1 | r:.5 D4:.5 F4:.5 D4:.5 Eb4:1 | C4:1 A3:.5 F#3:.5 Eb3:1 |
D3:.5 G3:2 r:.5 | r:1 Bb3:.5 D4:.5 A3:1 | G3:.5 A3:.5 C4:1.5 r:.5 | F#3:.5 A3:.5 C4:.5 Eb4:1.5 |
D4:1.5 r:.5 B3:.5 Ab3:.5 | G3:1 Bb3:.5 D4:.5 Eb4:1 | F4:1.5 D4:.5 B3:1 | C4:1 r:.5 A3:.5 Gb3:.5 A3:.5 |
Bb3:2.5 r:.5 | r:.5 G3:.5 Bb3:.5 D4:.5 C#4:1 | D4:2 B3:1 | Bb3:1.5 r:.5 A3:.5 F3:.5 |
Ab3:1 C4:.5 Eb4:.5 Db4:1 | C4:.5 Bb3:.5 G3:2 | r:1.5 Eb3:.5 G3:.5 C4:.5 | Eb4:1 D4:.5 Bb3:.5 F#3:1 |
G3:2 r:1 | r:.5 D3:.5 F3:.5 A3:.5 D4:1 | C4:1.5 Bb3:.5 A3:.5 G3:.5 | F#3:1 r:.5 A3:.5 C4:.5 Eb4:.5 |
D4:1.5 Bb3:.5 B3:1 | C4:1 Eb4:1 r:.5 D3:.5 | Eb3:.5 G3:.5 C4:1.5 Gb3:.5 | G3:2 r:1 |
"""


@dataclass
class Note:
    beat: float          # global beat position (grid)
    beats: float         # written length in beats
    midi: int
    vel: float = 0.6
    t: float = 0.0       # performed onset (s)
    dur: float = 0.0     # performed length (s)
    tags: dict = field(default_factory=dict)


def parse_part(text: str, start_beat: float):
    notes = []
    pos = start_beat
    bar_start = start_beat
    toks = text.split()
    first_bar = True
    for tok in toks:
        if tok == "|":
            length = pos - bar_start
            ok = abs(length - METER) < 1e-6 or (first_bar and abs(length - PICKUP) < 1e-6)
            assert ok, f"bar length {length} at beat {bar_start}: {text[:30]}"
            bar_start = pos
            first_bar = False
            continue
        p, d = tok.split(":")
        if "/" in d:
            a, b = d.split("/")
            beats = float(a) / float(b)
        else:
            beats = float(d)
        if p == "r":
            pass
        elif p == "_":
            notes[-1].beats += beats
        else:
            notes.append(Note(pos, beats, midi(p)))
        pos += beats
    return notes, pos


# --------------------------------------------------------------------------------------------
# performance helpers
# --------------------------------------------------------------------------------------------
class Human:
    """Slowly wandering timing offset (seconds) plus small per-note jitter."""

    def __init__(self, rng, mean, drift, jitter, rate=0.25):
        self.rng, self.mean, self.drift, self.jitter, self.rate = rng, mean, drift, jitter, rate
        self.phase = rng.random() * 6.28
        self.phase2 = rng.random() * 6.28

    def at(self, t):
        slow = self.drift * (0.65 * math.sin(self.rate * t + self.phase) + 0.35 * math.sin(0.37 * self.rate * t + self.phase2))
        return self.mean + slow + self.rng.gauss(0, self.jitter)


def section_dynamic(bar):
    """Overall band dynamic 0..1 by bar (the arc of the performance)."""
    if bar <= 0:
        return 0.55
    if bar <= 16:
        return 0.55 + 0.05 * (bar / 16)
    if bar <= 24:
        return 0.62 + 0.04 * math.sin(math.pi * (bar - 16) / 8)
    if bar <= 32:
        return 0.58
    if bar <= 48:
        return 0.60 + 0.08 * (bar - 32) / 16
    if bar <= 56:
        return 0.70 + 0.04 * math.sin(math.pi * (bar - 48) / 8)
    if bar <= 64:
        return 0.66 - 0.06 * (bar - 56) / 8
    if bar <= 80:
        return 0.56 + 0.06 * math.sin(math.pi * (bar - 64) / 16)
    if bar <= 88:
        return 0.62
    return 0.60 - 0.12 * (bar - 88) / 8


def beat_to_bar(B):
    return int((B - PICKUP) // METER) + 1


# --------------------------------------------------------------------------------------------
# tenor
# --------------------------------------------------------------------------------------------
PHRASE_SPLIT = 0.5   # a rest of half a beat or more is a breath: the phrase ends there


def tenor_notes(rng, chorus="A"):
    """The tenor's notes with performed times. `chorus` picks the written solo for bars 33-64:
    "A" (TENOR_CHORUS, the main render) or "B" (TENOR_CHORUS_B, the alternate for every second
    pass of the loop). Everything before bar 33 is drawn from the random stream first, so the head
    is identical, sample for sample, in both."""
    head, _ = parse_part(HEAD, 0.0)
    solo, end = parse_part(TENOR_CHORUS if chorus == "A" else TENOR_CHORUS_B, bar_beat(33))
    assert abs(end - bar_beat(65)) < 1e-6, end
    out, end = parse_part(OUT_HEAD, bar_beat(80))
    assert abs(end - bar_beat(97)) < 1e-6, end
    notes = head + solo + out
    # the head pickup into bar 17 and the out-head pickup into bar 81 must match (loop seam)
    p16 = [(n.beat - bar_beat(16), n.beats, n.midi) for n in notes if bar_beat(16) <= n.beat < bar_beat(17)][-2:]
    p80 = [(n.beat - bar_beat(80), n.beats, n.midi) for n in notes if bar_beat(80) <= n.beat < bar_beat(81)]
    assert p16 == p80, (p16, p80)

    hum = Human(rng, mean=0.050, drift=0.028, jitter=0.010, rate=0.21)
    rng_fall = random.Random(rng.random())
    notes.sort(key=lambda n: n.beat)
    # phrases: a written rest of half a beat or more is a breath and ends the phrase. Inside a
    # phrase the notes are slurred (each sounds until the next begins); a phrase's last note stops
    # just before its written end, so every rest is heard as a breath.
    phrases = [[notes[0]]]
    for a, b in zip(notes, notes[1:]):
        gap = b.beat - (a.beat + a.beats)
        (phrases.append([b]) if gap >= PHRASE_SPLIT - 1e-6 else phrases[-1].append(b))
    for ph in phrases:
        hi = max(n.midi for n in ph)
        n_ph = len(ph)
        for i, n in enumerate(ph):
            bar = beat_to_bar(n.beat)
            dyn = section_dynamic(bar)
            # phrase arc: rise toward the highest note, relax at the end
            rel = (n.midi - (hi - 12)) / 12.0
            arc = 0.08 * rel + 0.05 * math.sin(math.pi * (i + 0.5) / n_ph) - (0.06 if i == n_ph - 1 and n_ph > 2 else 0)
            accent = 0.03 if n.beats >= 1.5 else (-0.05 if n.beats <= 0.3 else 0.0)
            n.vel = max(0.25, min(0.95, dyn + arc + accent + rng.gauss(0, 0.025)))
            on_grid = swing(n.beat)
            lay = hum.at(beat_time(on_grid))
            if n.beats >= 1.5 and abs(n.beat - round(n.beat)) < 1e-6:
                lay += 0.025      # long notes on the beat sit further back
            n.t = beat_time(on_grid) + lay
            n.tags["phrase_start"] = i == 0
            n.tags["phrase_end"] = i == n_ph - 1
            n.tags["leap"] = (i > 0 and abs(n.midi - ph[i - 1].midi) >= 5)
        for i, n in enumerate(ph):
            if i + 1 < n_ph:
                nxt = ph[i + 1]
                n.dur = nxt.t - n.t          # legato: sounds until the next note
                n.tags["legato_next"] = nxt.midi
            else:
                # stop at the written end (less a breath of 0.08 beat), never into the rest
                end_b = n.beat + n.beats
                n.dur = beat_time(end_b) - n.t - 0.08 * 60 / TEMPO
                n.tags["legato_next"] = None
            n.dur = max(0.09, n.dur)
    # the rest after each phrase (s, from the written end to the next phrase's onset) for the renderer
    for ph, nxt in zip(phrases, phrases[1:] + [None]):
        last = ph[-1]
        last.tags["rest_after"] = (nxt[0].t - (last.t + last.dur)) if nxt else 9.0
    # a few expressive falls at phrase ends before long rests, and the final note
    for ph, nxt in zip(phrases, phrases[1:] + [None]):
        last = ph[-1]
        rest = (nxt[0].beat - (last.beat + last.beats)) if nxt else 9
        if rest >= 1.5 and last.beats <= 1.0 and rng_fall.random() < 0.35:
            last.tags["fall"] = True
    notes[-1].tags["final"] = True
    return notes, phrases


# --------------------------------------------------------------------------------------------
# piano: comping with voice-led rootless voicings, fills, and the half-chorus solo
# --------------------------------------------------------------------------------------------
# Low interval limits: the lowest note (MIDI) at which each interval (in semitones) still sounds
# clear on the piano. A voicing whose adjacent voices form a closer interval lower down is muddy
# and is never played: a minor 2nd needs E3 or higher, a major 2nd E-flat 3, a minor 3rd C3.
LOW_INTERVAL_LIMIT = {1: 52, 2: 51, 3: 48, 4: 46, 5: 45, 6: 46, 7: 34}


def lil_ok(v):
    v = sorted(v)
    return all(b - a > 7 or a >= LOW_INTERVAL_LIMIT[b - a] for a, b in zip(v, v[1:]) if b > a)


def voicing_candidates(ch: Chord, lo, hi):
    """Rootless A- and B-form voicings of `ch` inside [lo, hi], their drop-2 spreads (the second
    voice from the top taken down an octave, which opens the voicing around a low tune), and the
    three-note shells of each (one inner voice left out), all within the low interval limits."""
    out = []
    for form in ("A", "B"):
        shape = ch.q[form]
        for base in range(24, 96, 12):
            close = [base + ch.root + i for i in shape]
            drop2 = sorted(close[:2] + [close[2] - 12] + close[3:])
            for kind, v in ((form, close), (form + "d2", drop2)):
                if v[0] >= lo and v[-1] <= hi:
                    out.append((kind, v))
                    for k in (1, 2):
                        out.append((kind + "3", v[:k] + v[k + 1:]))
    return [(f, v) for f, v in out if lil_ok(v)]


def open_shells(ch: Chord, lo, hi):
    """Open three-note rootless shells: the third and the seventh plus one colour tone (9th, 11th,
    13th or an altered tone), each placed in any octave inside [lo, hi], at most an octave and a
    fifth wide, within the low interval limits. Used only when no close or drop-2 voicing clears
    the tune."""
    pcs = sorted({i % 12 for f in ("A", "B") for i in ch.q[f]})
    guides = [i for i in pcs if i in (3, 4, 10, 11)]
    colours = [i for i in pcs if i not in guides]
    out = []
    if len(guides) < 2:
        return out

    def places(pc):
        return [m for m in range(lo, hi + 1) if (m - ch.root - pc) % 12 == 0]
    for c in colours:
        for a in places(guides[0]):
            for b in places(guides[1]):
                for x in places(c):
                    v = sorted((a, b, x))
                    if len(set(v)) == 3 and v[-1] - v[0] <= 19 and lil_ok(v):
                        out.append(("open3", v))
    return out


# The comp's top voice while the tenor plays: B-flat 4 at most, so the piano stays in the tenor's
# shadow instead of floating a brighter line above the soft subtone melody.
TOP_CAP = 70


def choose_voicing(ch, prev, lo, hi, melody=None, target_center=58, avoid=(), avoid_now=(), held=False, top_cap=None):
    """Pick the voicing that moves least from `prev`, sits near `target_center` and stays out of
    the tenor's way.
      melody  (midi, beats) of the tune notes sounding while the chord sounds (both written tenor
              choruses in bars 33-64, so the comp suits either)
      avoid   the tune notes sounding at the strike (avoid_now) and the next one after it (the
              look-ahead): no voice may sit within a semitone of them. Voicings are re-chosen, not thinned, so a
              clash never leaves a two-note shell
      held    the tenor holds a long note (1.5 beats or more) over this chord: thin the comp to a
              three-note shell under or around it, the way a pianist leaves room for a held note
      top_cap the highest top voice while the tenor plays (TOP_CAP)"""
    cands = voicing_candidates(ch, lo, hi) or voicing_candidates(ch, lo - 5, hi + 5)
    # Filters, strictest first: clear of the tune now and of its next note, then clear of the note
    # now only, then the same with a little more range; each first under the top-voice cap, then
    # without it. The first stage with any voicing left wins. Only if all fail does clear_melody()
    # thin the chosen voicing.
    now = tuple(avoid_now)
    stages = []
    for cap in ((top_cap, None) if top_cap is not None else (None,)):
        for av, rng_ in ((avoid, (lo, hi)), (now, (lo, hi)), (avoid, (lo - 4, hi + 4)), (now, (lo - 4, hi + 4))):
            stages.append((cap, av, rng_))
    found = False
    for cap, av, (l2, h2) in stages:
        pool = cands if (l2, h2) == (lo, hi) else voicing_candidates(ch, l2, h2)
        pool = [(f, v) for f, v in pool if all(abs(x - m) > 1 for x in v for m in av)
                and (cap is None or v[-1] <= cap)]
        if pool:
            cands = pool
            found = True
            break
    if not found:
        # Round 1, pass 4: when no close or drop-2 voicing clears the tune (bar 46, where the two
        # choruses sit on the chord's third and its seventh at the same time), open the shell
        # instead of thinning it: the two guide tones and one colour tone, each in its own octave.
        for cap, av, (l2, h2) in stages:
            pool = [(f, v) for f, v in open_shells(ch, l2, h2)
                    if all(abs(x - m) > 1 for x in v for m in av) and (cap is None or v[-1] <= cap)]
            if pool:
                cands = pool
                break
    mel = [m for m, _ in melody] if melody else []
    key = max(avoid_now) if avoid_now else (max(avoid) if avoid else (mel[0] if mel else None))
    if key is not None and key >= 60 and top_cap is not None:
        # a tune note at C4 or above: the comp may go under it, down to B-flat 2 (the low interval
        # limits keep that register open), so the melody is the top voice
        under = [(f, v) for f, v in voicing_candidates(ch, 46, key - 2)
                 if all(abs(x - m) > 1 for x in v for m in (avoid or ()))]
        cands = cands + under
    best, bc = None, 1e9
    for form, v in cands:
        cost = 0.0
        if prev:
            pv = sorted(prev)
            cost += sum(min(abs(x - y) for y in pv) for x in v)            # voice leading
            cost += 0.75 * abs(len(v) - len(pv))
        cost += 0.35 * abs(sum(v) / len(v) - target_center)
        if held:
            cost += 3.0 if len(v) == 4 else 0.0                            # a shell under a held note
        elif len(v) == 3:
            cost += 4.0                                                    # otherwise prefer four voices
        for m, beats in (melody or []):
            for x in v:
                d = abs(x - m)
                if d <= 1:
                    cost += 10 if beats >= 0.5 else 4                      # minor-2nd rub or unison with the tune
                elif d == 2:
                    cost += 2.5 if beats >= 0.5 else 0.8                   # a 2nd against the tune: allowed, not sought
                elif d % 12 in (1, 11) and d < 25:
                    cost += 2 if beats >= 0.5 else 0.5                     # minor 9th against the tune
        if key is not None:
            if key >= 60:
                if v[-1] >= key - 1:
                    cost += 8                                              # a C4-and-up tune note keeps the comp under it
            else:
                if v[0] < key < v[-1] and min(abs(x - key) for x in v) < 3:
                    cost += 5                                              # straddle a low tune only with room around it
                if v[-1] < key:
                    cost += 9                                              # never comp under a low tune (mud)
                cost += 0.6 * max(0, v[-1] - (key + 12))                   # stay within an octave above a low tune
        if cost < bc:
            bc, best = cost, v
    return sorted(best)


def clear_melody(v, mel):
    """Last resort (choose_voicing() already avoids the tune): leave out a voice a semitone from (or
    doubling) the melody note. Voices are only removed, never moved down, so nothing turns to mud."""
    if mel is None:
        return v
    kept = [x for x in v if abs(x - mel) > 1]
    return sorted(kept) if len(kept) >= 2 else sorted(v)


def melody_span(notes, b0, b1):
    """(midi, beats) of the tune notes sounding between beats b0 and b1."""
    return [(n.midi, n.beats) for n in notes if n.beat < b1 - 0.01 and n.beat + n.beats > b0 + 0.01]


def voicing_problems(log):
    """Voicings that break the low interval limits (should be none)."""
    return [(bar, sym, v) for bar, sym, v, *_ in log if not lil_ok(v)]


def melody_at(notes, beat):
    for n in notes:
        if n.beat - 0.01 <= beat < n.beat + n.beats - 0.01:
            return n.midi
    return None


def melody_next(notes, beat, until):
    """The first tune note that starts after `beat` and before `until` (the look-ahead)."""
    for n in sorted(notes, key=lambda n: n.beat):
        if beat + 0.01 < n.beat < until - 0.01:
            return n.midi
    return None


def piano_part(rng, bars, tenor, tenor_alt=None):
    """Returns list of piano Notes (with performed times), plus the voicing log for the score.
    `tenor_alt` is the tenor with the alternate chorus: in bars 33-64 the comp and the fills are
    chosen against both choruses, so the one piano track suits either."""
    out = []
    log = []
    hum = Human(rng, mean=0.012, drift=0.010, jitter=0.006, rate=0.3)
    prev = None
    solo, end = parse_part(PIANO_SOLO, bar_beat(65))
    assert abs(end - bar_beat(81)) < 1e-6
    seam_template = None

    def add(beat, beats, m, vel, roll=0.0, tags=None, sustain_to=None):
        on = swing(beat)
        t = beat_time(on) + hum.at(beat_time(on)) + roll
        end_t = beat_time(sustain_to if sustain_to is not None else beat + beats)
        n = Note(beat, beats, m, vel, t, max(0.08, end_t - t), dict(tags or {}))
        out.append(n)
        return n

    # pickup: a soft rolled D7alt over the tenor's low D
    v = choose_voicing(parse_chord("D7alt"), None, 50, 75, melody=[(50, 1.0)], target_center=63)
    prev = v
    for i, m in enumerate(v):
        add(0, 1, m, 0.34 + 0.03 * i, roll=0.028 * i, tags={"comp": 1})

    for b in bars:
        bar = b["bar"]
        B0 = bar_beat(bar)
        dyn = section_dynamic(bar)
        part = b["part"]
        in_solo = part == "piano"
        lo, hi, center = (50, 74, 61) if not in_solo else (46, 66, 55)
        tunes = [tenor] + ([tenor_alt] if tenor_alt is not None and part == "tenor" else [])
        segs = b["segs"]
        acc = 0
        # comping rhythm for this bar
        pattern = rng.random()
        for si, (ch, nb) in enumerate(segs):
            sb = B0 + acc
            avoid, avoid_now, held, cap = (), (), False, None
            if in_solo:
                span = melody_span(solo, sb, sb + nb) or [(67, 1.0)]
                span = [(max(m for m, _ in span), 1.0)]      # the left hand stays under the solo line
                mel = None
            else:
                span = [x for tn in tunes for x in melody_span(tn, sb, sb + nb)] if part in ("head", "tenor", "out") else []
                mel = melody_at(tenor, sb) if span else None
                cap = TOP_CAP if part in ("head", "tenor", "out") and bar < 96 else None
                if span:
                    now = [melody_at(tn, sb) for tn in tunes]
                    ahead = [melody_next(tn, sb, sb + nb) for tn in tunes]
                    avoid = tuple({m for m in now + ahead if m is not None})
                    avoid_now = tuple({m for m in now if m is not None})
                    held = any(bb >= 1.5 for _, bb in span)
            v = choose_voicing(ch, prev, lo, hi, melody=span, target_center=center, avoid=avoid,
                               avoid_now=avoid_now, held=held, top_cap=cap)
            prev = v
            v = clear_melody(v, mel)
            log.append((bar, ch.symbol, v, sb))
            # when is it struck?
            strike = sb
            if si == 0 and acc == 0 and bar > 1 and pattern < 0.22 and part != "out" and bar not in (17, 81, 96):
                strike = sb - 0.5     # anticipate on the "and" of 3
            if bar == 96:
                strike = sb
            vel = dyn * (0.78 if not in_solo else 0.70) + rng.gauss(0, 0.02)
            if part in ("head", "tenor", "out") and bar < 96:
                vel *= 0.86           # the comp sits under the soft tenor
            if held:
                vel *= 0.80           # and steps back further under a held tenor note
            end_beat = sb + nb
            roll_step = 0.018 if (bar in (1, 17, 33, 49, 65, 81, 96) or rng.random() < 0.25) else 0.006
            cid = (bar, si)
            for i, m in enumerate(v):
                top = i == len(v) - 1
                add(strike, end_beat - strike, m, vel * (1.08 if top else 0.94), roll=roll_step * i,
                    tags={"comp": cid}, sustain_to=end_beat + 0.05)
            # a soft re-strike on beat 3 in a one-chord bar, sometimes (ballad "breathing")
            if len(segs) == 1 and part != "piano" and rng.random() < 0.28 and bar not in (96,) and not held:
                for i, m in enumerate(v[1:]):
                    add(sb + 2.0, 1, m, vel * 0.72, roll=0.01 * i, tags={"comp": cid}, sustain_to=sb + 3.05)
            acc += nb

        # fills in the tenor's gaps (head, tenor chorus, out head): short right-hand answers
        if part in ("head", "tenor", "out") and bar not in (16, 80, 96):
            gap_start, gap_len = tenor_gap(tenor if not (tenor_alt and part == "tenor") else tenor + tenor_alt, B0)
            if gap_len >= 1.4 and rng.random() < 0.8:
                ch = chord_at(bars, gap_start + 0.01)
                fill_notes(rng, add, ch, gap_start, gap_len, dyn, prev)

    # the half-chorus solo line (right hand), with a few thirds added under long notes
    for n in solo:
        bar = beat_to_bar(n.beat)
        dyn = section_dynamic(bar)
        vel = dyn * 0.95 + 0.05 * (n.midi - 72) / 12 + rng.gauss(0, 0.03)
        if n.beats <= 0.34:
            vel -= 0.06
        nn = add(n.beat, n.beats, n.midi, vel, tags={"solo": 1}, sustain_to=n.beat + n.beats * 1.05)
        if n.beats >= 1.5:
            ch = chord_at(bars, n.beat + 0.01)
            tones = [(ch.root + i) % 12 for i in ch.q["tones"]]
            below = [m for m in range(n.midi - 5, n.midi - 2) if m % 12 in tones]
            if below:
                add(n.beat, n.beats, below[-1], vel * 0.8, roll=0.012, tags={"solo": 1},
                    sustain_to=n.beat + n.beats * 1.05)

    # ending: high chime over the fermata (A5 over D5 -- the 9th ringing)
    fb = bar_beat(96)
    add(fb + 1.6, 1.4, 74, 0.36, tags={"chime": 1}, sustain_to=fb + 3.2)
    add(fb + 1.6, 1.4, 81, 0.33, roll=0.02, tags={"chime": 1}, sustain_to=fb + 3.2)

    # pedal changes: a new chord damps the old one; a re-strike damps only the re-struck keys
    comp = sorted([n for n in out if "comp" in n.tags], key=lambda n: n.t)
    strikes = sorted({(round(n.t, 2), n.tags["comp"]) for n in comp})
    for n in comp:
        for st, cid in strikes:
            if st <= n.t + 0.06:
                continue
            same = cid == n.tags["comp"]
            if not same or any(o.midi == n.midi and abs(o.t - st) < 0.06 for o in comp if o.tags["comp"] == cid):
                n.dur = min(n.dur, st - n.t + 0.04)
                break
    # loop seam: make the comp on the last beat of bar 80 identical to bar 16
    seam_fix(out, bar_beat(16), bar_beat(80))
    out.sort(key=lambda n: n.t)
    return out, log


def seam_fix(notes, b16, b80):
    """Replace every note struck in the last beat of bar 80 with a copy of those in bar 16."""
    lastbeat16 = (b16 + 2 - 0.5, b16 + 3)
    lastbeat80 = (b80 + 2 - 0.5, b80 + 3)
    keep = [n for n in notes if not (lastbeat80[0] <= n.beat < lastbeat80[1])]
    shift = b80 - b16
    dt = beat_time(b80) - beat_time(b16)
    add = []
    for n in notes:
        if lastbeat16[0] <= n.beat < lastbeat16[1]:
            add.append(Note(n.beat + shift, n.beats, n.midi, n.vel, n.t + dt, n.dur, dict(n.tags)))
    notes[:] = keep + add


def tenor_gap(tenor, B0):
    """Longest rest of the tenor inside bar starting at B0 (start beat, length)."""
    busy = []
    for n in tenor:
        if n.beat < B0 + 3 and n.beat + n.beats > B0:
            busy.append((max(B0, n.beat), min(B0 + 3, n.beat + n.beats)))
    busy.sort()
    cur = B0
    best = (B0, 0.0)
    for a, b in busy:
        if a - cur > best[1]:
            best = (cur, a - cur)
        cur = max(cur, b)
    if B0 + 3 - cur > best[1]:
        best = (cur, B0 + 3 - cur)
    return best


def fill_notes(rng, add, ch, start, length, dyn, voicing):
    """A short, soft right-hand answer in the upper register: chord tones and a passing tone."""
    tones = sorted({(ch.root + i) % 12 for i in ch.q["tones"]})
    top = max(voicing) if voicing else 64
    pool = [m for m in range(top + 3, top + 17) if m % 12 in tones]
    if len(pool) < 3:
        return
    n = 3 if length < 2 else rng.choice([3, 4])
    kind = rng.random()
    if kind < 0.5:
        seq = sorted(rng.sample(pool, n), reverse=True)        # falling arpeggio
    elif kind < 0.8:
        seq = sorted(rng.sample(pool, n))                      # rising
    else:
        a = rng.choice(pool)
        seq = [a + 2 if (a + 2) % 12 in [(ch.root + i) % 12 for i in ch.q["scale"]] else a + 1, a, a - 1 if (a - 1) % 12 in tones else a]
    step = 0.5 if length >= 2 else 1 / 3
    b = start + (0.5 if length >= 2.5 else 0.0)
    for i, m in enumerate(seq):
        if b + step > start + length + 0.01:
            break
        last = i == len(seq) - 1
        add(b, step, m, dyn * 0.62 + (0.04 if last else 0) + rng.gauss(0, 0.02), tags={"fill": 1},
            sustain_to=b + (step * (2.2 if last else 1.1)))
        b += step


# --------------------------------------------------------------------------------------------
# bass
# --------------------------------------------------------------------------------------------
def bass_feel(bar, part, section):
    if bar == 96:
        return "fermata"
    if part == "head":
        return "one" if bar <= 8 else "two"
    if part == "tenor":
        return "two" if bar <= 40 else "walk"
    if part == "piano":
        return "walk"
    return "two"


def nearest(pc, prev, lo=28, hi=50):
    cands = [m for m in range(lo, hi + 1) if m % 12 == pc]
    return min(cands, key=lambda m: (abs(m - prev), m))


def bass_part(rng, bars):
    out = []
    hum = Human(rng, mean=-0.004, drift=0.006, jitter=0.005, rate=0.33)
    prev = 36

    def add(beat, beats, m, vel, tags=None, ring=0.96):
        on = swing(beat)
        t = beat_time(on) + hum.at(beat_time(on))
        end_t = beat_time(beat + beats * ring)
        out.append(Note(beat, beats, m, vel, t, max(0.1, end_t - t), dict(tags or {})))

    def approach(target, cur, kind):
        if kind == "chrom":
            c = [target - 1, target + 1]
            return min(c, key=lambda m: abs(m - cur))
        if kind == "fifth":
            c = [target + 7, target - 5]
            return min(c, key=lambda m: abs(m - cur))
        return target + (2 if cur > target else -2)

    beats_list = []   # (beat, chord, is_change)
    for b in bars:
        B0 = bar_beat(b["bar"])
        acc = 0
        for ch, nb in b["segs"]:
            for k in range(nb):
                beats_list.append((B0 + acc + k, ch, k == 0, b))
            acc += nb

    i = 0
    while i < len(beats_list):
        beat, ch, change, b = beats_list[i]
        bar, part = b["bar"], b["part"]
        feel = bass_feel(bar, part, b["section"])
        dyn = section_dynamic(bar)
        pos = beat - bar_beat(bar)
        nxt = beats_list[i + 1] if i + 1 < len(beats_list) else None
        root = nearest(ch.root, prev, 31, 50)
        if feel == "fermata":
            if pos == 0:
                add(beat, 3, 43, 0.58, tags={"final": 1}, ring=1.6)
                add(beat + 0.02, 3, 31, 0.55, tags={"final": 1}, ring=1.6)
            i += 1
            continue
        if feel == "one":
            if pos == 0 or change:
                m = root
                add(beat, 3, m, dyn * 0.95 + rng.gauss(0, 0.02), ring=0.97)
                prev = m
            elif pos == 2 and nxt and rng.random() < 0.35:
                # little pickup into the next bar
                tgt = nearest(nxt[1].root, prev, 31, 50)
                add(beat + 0.5, 0.5, approach(tgt, prev, "chrom"), dyn * 0.8, ring=0.9)
            i += 1
            continue
        if feel == "two":
            if pos == 0 or (change and pos == 2):
                m = root if change or pos == 0 else prev
                if pos == 0 and not change:
                    m = root
                length = 2 if pos == 0 else 1
                # beat 3 of a one-chord bar gets an approach tone to the next chord instead
                add(beat, length, m, dyn * (0.95 if pos == 0 else 0.85) + rng.gauss(0, 0.02), ring=0.97)
                prev = m
            elif pos == 2 and nxt:
                tgt = nearest(nxt[1].root, prev, 31, 50)
                kind = "fifth" if rng.random() < 0.45 else "chrom"
                m = approach(tgt, prev, kind)
                if m == prev:
                    m = approach(tgt, prev, "chrom")
                if not (28 <= m <= 52):
                    m = tgt + 1
                add(beat, 1, m, dyn * 0.82 + rng.gauss(0, 0.02), ring=0.95)
                prev = m
            i += 1
            continue
        # walking: one note per beat
        if change:
            m = root
            if pos != 0 and rng.random() < 0.15:
                m = nearest((ch.root + ch.q["tones"][1]) % 12, prev, 31, 50)
        else:
            # is the next beat a chord change? approach it; otherwise a chord/scale tone
            if nxt and nxt[2]:
                tgt = nearest(nxt[1].root, prev, 31, 50)
                kinds = ["chrom", "chrom", "fifth", "step"]
                rng.shuffle(kinds)
                for kind in kinds + ["chrom"]:
                    m = approach(tgt, prev, kind)
                    if m != prev:
                        break
            else:
                tones = [(ch.root + x) % 12 for x in ch.q["tones"][:4]]
                cands = [x for x in range(prev - 5, prev + 6) if x % 12 in tones and x != prev and 30 <= x <= 50]
                m = rng.choice(cands) if cands else prev + 2
        m = max(28, min(52, m))
        vel = dyn * (0.95 if pos == 0 else 0.84) + rng.gauss(0, 0.025)
        add(beat, 1, m, vel, ring=0.93)
        # occasional ghosted "skip" note on the swung eighth before a downbeat
        if pos == 2 and rng.random() < 0.12:
            add(beat + 0.5, 0.5, m, 0.3, tags={"ghost": 1}, ring=0.5)
        prev = m
        i += 1

    # loop seam: beat 3 of bar 80 must equal beat 3 of bar 16 (two-feel approach into the bridge)
    seam_fix(out, bar_beat(16), bar_beat(80))
    out.sort(key=lambda n: n.t)
    return out


# --------------------------------------------------------------------------------------------
# drums with brushes
# --------------------------------------------------------------------------------------------
def drum_part(rng, bars):
    """Events: sweep (one circle per bar, left hand), tap (right hand on 2 and 3), kick (feathered),
    hat (foot chick), ride (soft brushed ride at section starts), swell (cymbal swell at the end)."""
    ev = []
    hum = Human(rng, mean=0.0, drift=0.004, jitter=0.004, rate=0.4)

    def at(beat):
        on = swing(beat)
        return beat_time(on) + hum.at(beat_time(on))

    # pickup: a single soft swish
    ev.append(dict(kind="sweep", t=beat_time(0), t1=beat_time(1), vel=0.35, circle=0))
    for b in bars:
        bar, part = b["bar"], b["part"]
        B0 = bar_beat(bar)
        dyn = section_dynamic(bar)
        if bar == 96:
            ev.append(dict(kind="sweep", t=beat_time(B0), t1=beat_time(B0 + 3.0), vel=0.30, circle=bar))
            ev.append(dict(kind="swell", t=beat_time(B0) - 0.3, vel=0.42))
            ev.append(dict(kind="kick", t=beat_time(B0), vel=0.30))
            continue
        ev.append(dict(kind="sweep", t=beat_time(B0), t1=beat_time(B0 + 3), vel=dyn * (0.95 + rng.gauss(0, 0.04)), circle=bar))
        ev.append(dict(kind="kick", t=at(B0), vel=0.22 + 0.1 * dyn + rng.gauss(0, 0.02)))
        solo = part in ("tenor", "piano")
        tap_lvl = {"head": 0.62, "tenor": 0.78, "piano": 0.66, "out": 0.64}[part]
        if bar <= 4:
            tap_lvl = 0.45
        for k in (1, 2):
            v = dyn * tap_lvl * (1.0 if k == 1 else 0.9) + rng.gauss(0, 0.03)
            ev.append(dict(kind="tap", t=at(B0 + k), vel=max(0.12, v)))
        # swung pickup tap on the "and" of 3, sometimes
        if rng.random() < (0.30 if solo else 0.16):
            ev.append(dict(kind="tap", t=at(B0 + 2.5), vel=dyn * tap_lvl * 0.55))
        if part in ("tenor", "piano") or (part in ("head", "out") and b["section"] in ("B", "A3")):
            ev.append(dict(kind="hat", t=at(B0 + 1), vel=0.45 * dyn + 0.1))
            if solo:
                ev.append(dict(kind="hat", t=at(B0 + 2), vel=0.30 * dyn + 0.08))
        if bar in (17, 33, 49, 65, 81):
            ev.append(dict(kind="ride", t=at(B0), vel=0.40 + 0.2 * dyn))
        if part == "tenor" and b["section"] == "B" and bar % 2 == 1:
            ev.append(dict(kind="ride", t=at(B0 + 1), vel=0.22 + 0.1 * dyn))
    # loop seam: copy the last beat of bar 16 onto bar 80
    b16, b80 = bar_beat(16), bar_beat(80)
    t16a, t16b = beat_time(b16 + 1.5), beat_time(b16 + 3)
    t80a, t80b = beat_time(b80 + 1.5), beat_time(b80 + 3)
    dt = beat_time(b80) - beat_time(b16)
    ev = [e for e in ev if not (t80a <= e["t"] < t80b and e["kind"] != "sweep")] + \
         [dict(e, t=e["t"] + dt) for e in ev if t16a <= e["t"] < t16b and e["kind"] != "sweep"]
    ev.sort(key=lambda e: e["t"])
    return ev


# --------------------------------------------------------------------------------------------
def events(seed=1958):
    rng = random.Random(seed)
    bars = chart()
    tenor, phrases = tenor_notes(random.Random(seed + 1))
    tenor_b, phrases_b = tenor_notes(random.Random(seed + 1), chorus="B")
    piano, voicings = piano_part(random.Random(seed + 2), bars, tenor, tenor_b)
    bass = bass_part(random.Random(seed + 3), bars)
    drums = drum_part(random.Random(seed + 4), bars)
    return dict(bars=bars, tenor=tenor, phrases=phrases, tenor_b=tenor_b, phrases_b=phrases_b,
                piano=piano, voicings=voicings, bass=bass, drums=drums)


def timeline():
    return dict(
        bpm=TEMPO, meter=METER, lead=LEAD,
        loopStart=beat_time(bar_beat(LOOP_BARS[0])), loopEnd=beat_time(bar_beat(LOOP_BARS[1])),
        end_music=beat_time(bar_beat(97)),
    )


if __name__ == "__main__":
    ev = events()
    tl = timeline()
    print(TITLE, KEY, f"{TEMPO} bpm 3/4")
    print("tenor notes", len(ev["tenor"]), "piano notes", len(ev["piano"]), "bass", len(ev["bass"]), "drum events", len(ev["drums"]))
    print("loop", tl, "music ends", tl["end_music"])
    bad = voicing_problems(ev["voicings"])
    print("voicings", len(ev["voicings"]), "below the low interval limits:", len(bad), bad[:5])
    lows = [m for n in ev["tenor"] for m in [n.midi]]
    head = [n.midi for n in ev["tenor"] if n.beat < bar_beat(33)]
    print("tenor range", min(lows), max(lows), "head notes below C4:", sum(m < 60 for m in head), "of", len(head))
