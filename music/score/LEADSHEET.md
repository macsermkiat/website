# Lanterns After Closing

An original jazz ballad for the Nachtmarkt bandstand quartet: tenor sax, piano, double bass and drums with brushes.
Generated from `music/score/ballad.py` (the source of truth); the same notes are in `ballad.mid`.

- Key: G minor, with warm turns to E-flat major 7#11, B-flat major and A-flat major (first written in C minor, moved down a fourth so the tenor head sits in the subtone register, D3-E4)
- Metre and tempo: 3/4, quarter = 66 (a slow jazz waltz ballad), ritardando from bar 93, rubato fermata on bar 96
- Form: 32-bar AABA (A = 8 bars, B = 8 bars)

| Bars | Section | Who leads | Bass | Brushes |
|---|---|---|---|---|
| pickup, 1-32 | Head: A1 A2 B A3 | tenor (melody) | one-feel (A1), then two-feel | sweeps, taps on 2 and 3, feathered kick; foot hat from the bridge |
| 33-64 | Tenor chorus | tenor, written-out improvisation with space | two-feel, walking from bar 41 | taps busier, hat on 2 and 3, brushed ride at the bridge |
| 65-80 | Piano half-chorus (A1 A2) | piano | walking | lighter |
| 81-96 | Out head from the bridge (B A3) | tenor | two-feel; low G under the fermata | ritardando, cymbal swell at the end |

The site loops bars 17-80. Bar 80 ends exactly like bar 16 (tenor pickup F, A into the bridge, same comp, bass and brush), so the jump back is seamless.

## Changes

ii-V-i motion is everywhere: Am7b5-D7b9-Gm9 (bars 3-5), Cm9-F13-Bbmaj9 (6-7), Dm7-G7b9-Cm9 (A2, 7-8), Em7b5-A7b9-Dm9 (bridge 2-3), Bbm9-Eb13-Abmaj9 (bridge 5-6), Am7b5-D7alt (bridge 7-8).
Tritone substitutions: Db7#11 for G7 (bridge 3), B7#11 for F7 (bridge 4), Ab7#11 for D7 (A3, bar 7).

**A1** | Gm9 | Ebmaj7#11 | Am7b5 | D7b9 | Gm9(2) G7b9(1) | Cm9(2) F13(1) | Bbmaj9(2) Ebmaj7#11(1) | Am7b5(2) D7alt(1) |

**A2** | Gm9 | Ebmaj7#11 | Am7b5 | D7b9 | Gm9(2) G7b9(1) | Cm9(2) F13(1) | Dm7(2) G7b9(1) | Cm9(2) F7b9(1) |

**B** | Bbmaj9 | Em7b5(2) A7b9(1) | Dm9(2) Db7#11(1) | Cm9(2) B7#11(1) | Bbm9(2) Eb13(1) | Abmaj9 | Am7b5 | D7alt |

**A3** | Gm9 | Ebmaj7#11 | Am7b5 | D7b9 | Gm9(2) G7b9(1) | Cm9(2) F13(1) | Am7b5(2) Ab7#11(1) | Gm9(2) D7alt(1) |

(n) = beats when a bar holds two chords (2 + 1).

## Head melody (tenor, concert pitch)

Written as `note:beats`, bars separated by `|`; `_` ties, `r` rests. C4 is middle C.

```
D3:1 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:1 | r:.5 F3:.5 A3:1 G3:1 | C4:1 A3:.5 Eb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:1.5 r:.5 G3:.5 Bb3:.5 | A3:.5 G3:.5 A3:.5 C4:.5 Eb4:1 | D4:1.5 C4:.5 F#3:.5 r:.5 |
D4:1.5 C4:.5 B3:1 | C4:.5 Eb4:1.5 D4:.5 r:.5 | C4:2 B3:.5 Ab3:.5 | G3:1.5 r:.5 F3:.5 A3:.5 |
D4:1.5 C4:.5 A3:1 | G3:1 r:.5 Bb3:.5 C#4:1 | D4:.5 E4:1.5 B3:1 | Bb3:1.5 G3:.5 A3:.5 r:.5 |
F3:.5 Ab3:.5 C4:1.5 Bb3:.5 | C4:1.5 Bb3:.5 G3:.5 r:.5 | Eb3:1 G3:.5 A3:.5 C4:1 | Eb4:1 D4:.5 Bb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:.5 r:.5 | C4:1 Bb3:.5 A3:.5 Eb3:.5 F#3:.5 | G3:2.5 r:.5 |
```

Every rest of half a beat or more is a breath: the tenor's phrase ends there, and no run goes on longer than about 6 s without one.

## Piano voicings (head, bars 1-32)

Rootless voicings (Bill Evans A/B forms: 3-5-7-9 or 7-9-3-5 and their altered cousins, their drop-2 spreads, or a three-note shell of one), chosen by the smallest total voice movement from the previous chord. Every voicing keeps the low interval limits (no minor 2nd below E3, no major 2nd below E-flat 3, no minor 3rd below C3), so nothing clusters in the bass register. The comp is chosen clear of the tune note it is struck against and of the next tune note (a look-ahead), so a clash is re-voiced rather than thinned. While the tenor plays, the comp's top voice stays at or below B-flat 4; under a held tenor note the comp thins to a three-note shell and steps back; under a tune note of C4 or higher it may go under the melody. Because the head sits low (D3-E4), most chords still reach above the tune: a comp entirely under a tune at G3 would sit in the muddy register below E3. The bass plays the roots.

| Bar | Chord | Voicing (low to high) |
|---|---|---|
| 1 | Gm9 | F3 D4 A4 |
| 2 | Ebmaj7#11 | F3 D4 A4 |
| 3 | Am7b5 | C4 Eb4 G4 A4 |
| 4 | D7b9 | C4 Gb4 Bb4 |
| 5 | Gm9 | Bb3 F4 A4 |
| 5 | G7b9 | B3 Eb4 F4 Ab4 |
| 6 | Cm9 | Bb3 D4 Eb4 G4 |
| 6 | F13 | Eb3 D4 G4 |
| 7 | Bbmaj9 | D3 C4 F4 |
| 7 | Ebmaj7#11 | D4 F4 G4 A4 |
| 8 | Am7b5 | G3 Eb4 A4 |
| 8 | D7alt | Gb3 Bb3 C4 F4 |
| 9 | Gm9 | F3 D4 A4 |
| 10 | Ebmaj7#11 | F3 D4 A4 |
| 11 | Am7b5 | C4 G4 A4 |
| 12 | D7b9 | C4 Gb4 Bb4 |
| 13 | Gm9 | Bb3 F4 A4 |
| 13 | G7b9 | F3 Eb4 Ab4 |
| 14 | Cm9 | Bb2 Eb3 G3 |
| 14 | F13 | Eb3 A3 G4 |
| 15 | Dm7 | C3 E3 A3 |
| 15 | G7b9 | F3 Eb4 Ab4 |
| 16 | Cm9 | Eb3 D4 G4 |
| 16 | F7b9 | Eb3 Db4 Gb4 |
| 17 | Bbmaj9 | D3 A3 F4 |
| 18 | Em7b5 | D4 E4 G4 Bb4 |
| 18 | A7b9 | G3 F4 Bb4 |
| 19 | Dm9 | C3 E3 A3 |
| 19 | Db7#11 | F3 G3 Eb4 |
| 20 | Cm9 | Eb3 D4 G4 |
| 20 | B7#11 | Eb3 Db4 F4 |
| 21 | Bbm9 | Ab3 Db4 F4 |
| 21 | Eb13 | Db3 G3 F4 |
| 22 | Abmaj9 | G3 Eb4 Bb4 |
| 23 | Am7b5 | C4 Eb4 A4 |
| 24 | D7alt | C4 Gb4 Bb4 |
| 25 | Gm9 | F3 D4 A4 |
| 26 | Ebmaj7#11 | F3 D4 A4 |
| 27 | Am7b5 | C4 Eb4 G4 A4 |
| 28 | D7b9 | C4 Gb4 Bb4 |
| 29 | Gm9 | Bb3 F4 A4 |
| 29 | G7b9 | B3 Eb4 F4 Ab4 |
| 30 | Cm9 | Bb3 D4 Eb4 G4 |
| 30 | F13 | Eb3 D4 G4 |
| 31 | Am7b5 | G3 Eb4 A4 |
| 31 | Ab7#11 | C4 D4 Gb4 Bb4 |
| 32 | Gm9 | Bb3 D4 A4 |
| 32 | D7alt | C4 F4 Bb4 |

## Tenor chorus (bars 33-64, written-out improvisation)

```
r:1.5 D3:.5 G3:.5 A3:.5 | Bb3:2.5 A3:.5 | G3:1 r:2 | r:.5 F#3:.5 A3:.5 C4:.5 Eb4:.5 D4:.5 |
Bb3:1.5 A3:.5 B3:.5 D4:.5 | Eb4:1 D4:.5 C4:.5 A3:1 | D4:1.5 r:.5 G3:.5 Bb3:.5 | A3:.5 C4:.5 Eb4:1 D4:.25 C4:.25 Bb3:.25 Ab3:.25 |
F#3:.5 G3:2.5 | r:1 F3:.5 G3:.5 A3:1 | C4:1.5 Bb3:.5 A3:.5 G3:.5 | F#3:1 r:2 |
r:1 Bb3:.5 D4:.5 F4:.5 Eb4:.5 | D4:1 Eb4:.25 D4:.25 C4:.25 Bb3:.25 A3:1 | C4:1.5 A3:.5 B3:.5 Ab3:.5 | G3:1.5 r:.5 A3:.5 C4:.5 |
D4:1 F4:2 | E4:.5 D4:.5 Bb3:1 C#4:.5 E4:.5 | F4:1 E4:.5 C4:.5 B3:.5 Ab3:.5 | r:.5 D4:.25 F4:.25 Eb4:.5 C4:.5 A3:.5 F#3:.5 |
F3:.5 Ab3:.5 C4:1 Db4:.5 C4:.5 | C4:2.5 r:.5 | r:.5 Eb3:.5 G3:.5 A3:.5 C4:.5 Eb4:.5 | D4:1/3 Eb4:1/3 D4:1/3 C4:.5 Bb3:.5 Ab3:.5 F#3:.5 |
G3:1.5 r:1.5 | r:.5 D3:.5 G3:.5 Bb3:.5 D4:1 | C4:.75 Bb3:.25 A3:.5 G3:.5 Eb3:1 | F#3:.5 A3:.5 C4:.5 Eb4:.5 r:1 |
D4:2 B3:1 | Bb3:.5 G3:.5 Eb3:.5 r:.5 D3:1 | Eb3:.5 G3:.5 C4:1 F#3:.5 Eb3:.5 | G3:2 r:1 |
```

## Alternate tenor chorus (bars 33-64, played on every second pass of the site's loop)

```
r:2 D4:.5 C4:.5 | Bb3:2 A3:1 | G3:1.5 r:1.5 | r:.5 A3:.5 C4:.5 Eb4:.5 D4:.5 C4:.5 |
Bb3:1 A3:.5 G3:.5 B3:1 | C4:2 r:1 | r:.5 D4:.5 F4:.5 D4:.5 Eb4:1 | C4:1 A3:.5 F#3:.5 Eb3:1 |
D3:.5 G3:2 r:.5 | r:1 Bb3:.5 D4:.5 A3:1 | G3:.5 A3:.5 C4:1.5 r:.5 | F#3:.5 A3:.5 C4:.5 Eb4:1.5 |
D4:1.5 r:.5 B3:.5 Ab3:.5 | G3:1 Bb3:.5 D4:.5 Eb4:1 | F4:1.5 D4:.5 B3:1 | C4:1 r:.5 A3:.5 Gb3:.5 A3:.5 |
Bb3:2.5 r:.5 | r:.5 G3:.5 Bb3:.5 D4:.5 C#4:1 | D4:2 B3:1 | Bb3:1.5 r:.5 A3:.5 F3:.5 |
Ab3:1 C4:.5 Eb4:.5 Db4:1 | C4:.5 Bb3:.5 G3:2 | r:1.5 Eb3:.5 G3:.5 C4:.5 | Eb4:1 D4:.5 Bb3:.5 F#3:1 |
G3:2 r:1 | r:.5 D3:.5 F3:.5 A3:.5 D4:1 | C4:1.5 Bb3:.5 A3:.5 G3:.5 | F#3:1 r:.5 A3:.5 C4:.5 Eb4:.5 |
D4:1.5 Bb3:.5 B3:1 | C4:1 Eb4:1 r:.5 D3:.5 | Eb3:.5 G3:.5 C4:1.5 Gb3:.5 | G3:2 r:1 |
```

## Piano half-chorus (bars 65-80, right hand)

```
r:1 D4:.5 F4:.5 A4:.5 Bb4:.5 | A4:1.5 G4:.5 D4:1 | Eb4:.5 G4:.5 C5:1 Bb4:.5 A4:.5 | F#4:.5 Eb4:.5 C4:.5 A3:.5 F#3:1 |
G4:1.5 r:.5 B4:.5 Ab4:.5 | G4:1/3 Ab4:1/3 G4:1/3 Eb4:1 D4:1 | F4:.5 A4:.5 C5:1 Bb4:.5 G4:.5 | A4:1 Eb4:1 F#4:.5 Ab4:.5 |
Bb4:2 r:1 | r:.5 Bb4:.5 D5:.5 A4:.5 G4:1 | Eb4:.25 G4:.25 A4:.25 C5:.25 Eb5:1 D5:.5 C5:.5 | Bb4:.5 A4:.5 F#4:.5 Eb4:.5 C4:1 |
Bb3:.5 D4:.5 A4:1 Ab4:1 | G4:1.5 Eb4:.5 D4:.5 C4:.5 | C4:.5 F4:.5 A4:1 Ab4:.5 F4:.5 | Eb4:2 r:1 |
```

## Out head (from beat 3 of bar 80)

```
r:2 F3:.5 A3:.5 |
D4:1.5 C4:.5 A3:1 | G3:1 r:.5 Bb3:.5 C#4:1 | D4:.5 E4:1.5 B3:1 | Bb3:1.5 G3:.5 A3:.5 r:.5 |
F3:.5 Ab3:.5 C4:1.5 Bb3:.5 | C4:2 Bb3:.5 r:.5 | Eb3:1 G3:.5 A3:.5 C4:1 | Eb4:1 D4:.5 Bb3:.5 r:.5 D3:.5 |
Bb3:2.5 A3:.5 | _:2.5 r:.5 | r:1 G3:.5 A3:.5 C4:1 | Eb4:1.5 D4:.5 F#3:1 |
G3:1.5 r:.5 F3:.5 Ab3:.5 | Eb3:.5 G3:1 Bb3:.5 A3:.5 r:.5 | C4:1 Bb3:.5 A3:.5 Eb3:.5 F#3:.5 | G3:1 Bb3:.5 A3:1.5 |
```
