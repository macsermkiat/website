# Music: the bandstand ballad

"Lanterns After Closing" is an original jazz ballad for the bandstand quartet: tenor sax, piano, double bass and drums with brushes. It is in G minor, in 3/4 at quarter = 66, and lasts 4:29. The form is a 32-bar AABA chorus. This folder holds the score and the offline renderer that turns it into the stems the site plays.

| Path | What it is |
|---|---|
| `score/ballad.py` | The score and the source of truth. It holds the changes, the written head, the written-out tenor chorus and piano half-chorus, and the rules for the rhythm section: voice-led rootless voicings within the low interval limits, one-feel, two-feel and walking bass, and the brush pattern. It also holds the tempo map and the loop points. `python3 music/score/ballad.py` prints a summary and the voicing check. |
| `score/ballad.mid` | The same notes as a type-1 MIDI file, quantised to the grid, with chord symbols, section markers and the ritardando. Generated. |
| `score/LEADSHEET.md` | A readable chart with the form, the changes, the head, the voicing table, the solos and the out head. Generated. |
| `render/render.py` | Renders the stems, the mix, the MP3s, `site/public/audio/manifest.json`, the events file, the MIDI and the lead sheet. `--sax-bank {mtg,musyngkite,fluidr3}` switches the tenor source (default `mtg`), `--brushes {swirly,modelled}` the brushes (default `swirly`), `--light-stems` also writes an unshipped smaller stem set to `out/light/` (four player stems mono at 64 kbps, room stereo at 80 kbps) and `--cut-stems` ends the stems 1 s after `loopEnd` (do not use it now: the site plays the ending from the stems). |
| `render/sax.py`, `piano.py`, `bass.py`, `drums.py`, `room.py` | The instruments and the room. |
| `render/measure.py` | Re-measures the shipped MP3s (length, tempo, key from the audio and from `score/ballad.mid`, sax centroid, tenor phrase dynamics, peak, loudness, loop seam, voicing check, plus the `checks.py` measures and the alternate chorus) and draws the review figures. |
| `render/checks.py` | Round 1, pass 3 measures: how long the tenor plays without a breath (from the score and from the audio), whether the melody stays on top (piano top voice against the tune, sax-versus-piano band energy at 200-1500 Hz in the head), the breath air at 3.2-8 kHz, and the tuning of every prepared tenor sample. Pass 5 adds `held_note_dips` (a held note that falls more than 12 dB mid-note and comes back: a splice hole), `prepared_bank_dips` (the same on the prepared samples) and `phrase_start_rise` (attack rise times). `measure.py` exits with status 1 when `held_note_dips` finds anything in `ballad-sax.mp3` or `ballad-sax-b.mp3`. |
| `render/ab_tenor.py` | Renders bars 1-16 with each tenor bank (MTG, MusyngKite, FluidR3) through the same chain, for listening (`listen/head_*.mp3`) and for the measured comparison in `listen/ab.json`. |
| `render/ab_brushes.py` | Renders bars 17-36 with the recorded brushes and with the round-1 model (`listen/brushes_*.mp3`, band and drums alone) and draws `review/round-1/music/brushes.jpg`. |
| `render/browser/decode_check.mjs`, `render/browser_check.py` | Decode the shipped MP3s in Chromium with `decodeAudioData` (Playwright) and check length, alignment against the render, and the loop jump as the site plays it. |
| `render/sax_detail.py`, `render/voicing_figure.py` | Draw the tenor close-up (bars 1-10, with every held-note dip marked; pass an older stem as the argument to draw it underneath) and the piano-register figure. |
| `render/listen_chorus_b.py` | Cuts `listen/chorus_b_excerpt.mp3` (the second tenor chorus with 2 s either side) from the chorus-B mix. |
| `fetch_samples.sh` | Fetches the sample libraries into `.samples/`. This is about 800 MB of working files and is git-ignored. |
| `listen/` | The files for Mac to listen to (tracked, 128 kbps, not shipped): the tenor A/B, the brush A/B and an excerpt with the second tenor chorus. They lived in `review/round-1/music/listen/` until pass 3; `review/` is for preview images only. |
| `out/` | `ballad_mix_preview.mp3` and `ballad_mix_chorus_b_preview.mp3` (192 kbps, not shipped), the tenor A/B in `out/ab/`, `measurements.json`, `browser_check.json`, and the working WAVs. The whole folder is git-ignored, so the files for listening are in `listen/`. |

## Rebuild

```sh
music/fetch_samples.sh                      # once; needs git and curl
pip install lameenc pyloudnorm mido matplotlib soundfile scipy numpy
python3 music/render/render.py              # about 6 min on one core; --reuse keeps cached instrument renders
python3 music/render/measure.py             # re-measure the shipped files and redraw review/round-1/music/*; exits 1 on a held-note dip
python3 music/render/ab_tenor.py            # optional: tenor A/B files and numbers in music/listen/
python3 music/render/ab_brushes.py          # optional: brush A/B files in music/listen/ and review/round-1/music/brushes.jpg
python3 music/render/listen_chorus_b.py     # optional: music/listen/chorus_b_excerpt.mp3
python3 music/render/sax_detail.py [OLD.mp3] # review/round-1/music/sax_detail.jpg
# optional: the browser check
python3 -m http.server 8765 --bind 127.0.0.1 --directory site/public/audio &
node music/render/browser/decode_check.mjs 8765 music/.cache/browser_decode.json
python3 music/render/browser_check.py music/.cache/browser_decode.json
```

## The tenor source

Since round 1 pass 4 the tenor is a **recorded** tenor saxophone: the MTG Solo Saxophones set (Music Technology Group, UPF, on freesound.org; SFZ by kinwie; CC BY 4.0), one soft (p) sample per semitone from A-flat 2 to E5, plus 64 recordings of the player's breathing, which `sax.py` uses for the intakes before phrases. It replaced the two General MIDI soundfont banks of passes 1-3 (Musyng Kite, CC BY-SA 3.0, and FluidR3, CC BY 3.0), which stay one flag away. With MTG the whole recording is attribution-only; with Musyng Kite the sax, room and mix files would be share-alike.

`ab_tenor.py` renders bars 1-16 with each bank through the same chain (`music/listen/head_<bank>.mp3`, and `_tenor` for the tenor alone with its room). The recorded breaths are used with every bank, so only the notes differ. Nobody has listened yet. The measured comparison (`music/listen/ab.json`, pass 5 settings, AIR 0.4, steady-window splices):

| Measure | MTG (recorded) | MusyngKite | FluidR3 |
|---|---|---|---|
| Timbre movement inside a held note (raw sample, C3-F#4) | 1.82 dB | 1.76 dB | 1.39 dB |
| Timbre jump from one semitone to the next (raw sample, median) | 4.91 dB | 2.60 dB | 3.99 dB |
| Level movement inside a held note (raw sample, 0.4-2.9 s, which for MTG includes the start of each note's decay) | 3.1 dB | 4.0 dB | 1.9 dB |
| Level movement inside a prepared 14 s note (5th-95th percentile, 0.9-8 s, pass 5 splicing) | 0.7 dB | 1.7 dB | 1.6 dB |
| Timbre jump between slurred notes (rendered, median) | 4.1 dB | 4.8 dB | 5.5 dB |
| Tenor spectral centroid (rendered, bars 1-16) | 594 Hz | 614 Hz | 729 Hz |

MTG has one recording per semitone, so its raw notes differ more from their neighbours than MusyngKite's, but after the renderer's legato joins it has the smallest note-to-note colour change of the three, and it is a real player on a real horn. `sax.py` takes the recorded vibrato out of every sample (so the only vibrato is the one the renderer plays) and tunes the sustained part of each to its nominal pitch.

**Splicing (pass 5).** A held note longer than its recording is sustained by splicing pieces of the recording's own steady tone. The pieces come only from `steady_window()`: from 0.6 s to where the level first falls 3 dB under the median of 0.5-2.0 s (2.5-3.2 s into each MTG note). In pass 4 the window ran to 0.15 s before the end of the file, and the MTG notes spend their last 1-1.5 s dying away, so 27 of the 28 prepared samples had holes of 12-58 dB and the opening B-flat to A cut out and re-attacked mid-note. The slow 1-3 dB drift inside the window is levelled (`level_drift()`) so pieces from its two ends join at the same level. The prepared bank is cached as `.cache/<bank>_tenor_v6.npz`.

The tenor's sound is set by constants at the top of `sax.py`: `BREATH` (breath noise inside the dark EQ, 1.2), `AIR` (breath air at 2.4-7 kHz that bypasses the final low-pass, 0.4 since pass 4, was 1.0), `CORE` (the subtone body, 0.9), the `TONE` corners for each bank and `INHALE_GAP` (the shortest silence that gets an audible intake). Lower `AIR` or `BREATH` for less hiss, lower the bank's `lp_bright` for a darker core, raise `CORE` for a rounder, hollower low end.

## The brushes

Since pass 4 the brushes are recorded too: Karoryfer's Swirly Drums (CC0) is a jazz kit played with brushes, with long recordings of the brush stirring circles on the snare. `drums.py` plays one stir circle per bar from a random stretch of those recordings (at the dynamic level nearest the bar's), shaped by the brush's speed around the circle and crossfaded bar to bar; the taps on 2 and 3 are recorded brush hits and digs; the hi-hat foot and the ride come from the same kit. The feathered bass drum stays Virtuosity Drums' jazz kick. The round-1 model is still there (`--brushes modelled`) for the A/B in `music/listen/brushes_*.mp3`. The snare is panned, not widened with a delayed copy, because the site folds the drum stem to mono.

## What ships (`site/public/audio/`)

- `ballad-{sax,piano,bass,drums,room}.mp3`: five stems, 128 kbps CBR stereo at 44.1 kHz. They all have the same length and are aligned to the sample. The four player stems are dry, and `room` is the reverb return of all four. Played together at unity gain they sum to the mix.
- `ballad-mix.mp3`: the same mix in one file, at the same length and with the same loop points. The lite market could decode this one file instead of five.
- `ballad-sax-b.mp3`, `ballad-room-b.mp3`: the alternate tenor chorus (bars 33-64, `TENOR_CHORUS_B` in the score), as a segment of the sax and room stems from `alternates[0].start` to `end` (87.98-181.21 s, 93 s, 1.5 MB each). On every second pass through the loop a player can play these in place of the sax and room stems; the piano, bass and drums do not change, because the comp and the fills were chosen against both choruses. The first and last half second of each segment equal the main stems, so the switch can be a crossfade anywhere in those windows (skip the first 0.1 s, which holds the MP3 decoder's priming).
- `ballad-events.json`: each player's note onsets in stem time, for animating the musicians (`saxAlt` for the alternate chorus).
- `manifest.json`: `{bpm, duration, loopStart, loopEnd, stems}` plus title, key, time signature, `tenorBank`, `brushes`, `mix`, `events`, `sections` (form with times), `ending` (how to play out instead of looping), `alternates` (the second tenor chorus), `decodedDuration` and `license`.

The site (`site/src/audio/songplan.js`, the engineer's) plays from 0, loops `loopStart`-`loopEnd` (bars 17-80) a few times with the alternate chorus on every second pass, then plays on past `loopEnd` into the written ending. Bar 80 is written to end exactly like bar 16, and the last 0.4 s before `loopEnd` are spliced from the moment just before `loopStart`. As a result the jump back is continuous to the sample and is the same music. The ending (bars 81-96, the out head, ritardando and fermata) follows `loopEnd` seamlessly in the files, so a player that stops looping and plays on finishes the tune.

LAME adds a 1105-sample encoder delay. The files have no gapless header, so the renderer pre-shifts the audio by that amount. Chromium's `decodeAudioData` (checked with Playwright, Chrome 141) returns exactly the rendered timeline: zero samples of lag on every stem, all five stems 11,874,816 samples at 44.1 kHz (12,924,969 at 48 kHz). The decoded length is 269.270 s, 0.048 s longer than `duration` (269.222 s) because of the encoder's padding in the last MP3 frame, which is silence; the manifest gives both.
