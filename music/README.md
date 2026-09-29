# Music: the bandstand ballad

"Lanterns After Closing" is an original jazz ballad for the bandstand quartet: tenor sax, piano, double bass and drums with brushes. It is in G minor, in 3/4 at quarter = 66, and lasts 4:29. The form is a 32-bar AABA chorus. This folder holds the score and the offline renderer that turns it into the stems the site plays.

| Path | What it is |
|---|---|
| `score/ballad.py` | The score and the source of truth. It holds the changes, the written head, the written-out tenor chorus and piano half-chorus, and the rules for the rhythm section: voice-led rootless voicings within the low interval limits, one-feel, two-feel and walking bass, and the brush pattern. It also holds the tempo map and the loop points. `python3 music/score/ballad.py` prints a summary and the voicing check. |
| `score/ballad.mid` | The same notes as a type-1 MIDI file, quantised to the grid, with chord symbols, section markers and the ritardando. Generated. |
| `score/LEADSHEET.md` | A readable chart with the form, the changes, the head, the voicing table, the solos and the out head. Generated. |
| `render/render.py` | Renders the stems, the mix, the MP3s, `site/public/audio/manifest.json`, the events file, the MIDI and the lead sheet. `--sax-bank fluidr3` switches the tenor source. |
| `render/sax.py`, `piano.py`, `bass.py`, `drums.py`, `room.py` | The instruments and the room. |
| `render/measure.py` | Re-measures the shipped MP3s (length, tempo, key, sax centroid, tenor phrase dynamics, peak, loudness, loop seam, voicing check) and draws the review figures. |
| `render/ab_tenor.py` | Renders the head with each tenor bank through the same chain, for listening and for the measured comparison in `out/ab/ab.json`. |
| `render/browser/decode_check.mjs`, `render/browser_check.py` | Decode the shipped MP3s in Chromium with `decodeAudioData` (Playwright) and check length, alignment against the render, and the loop jump as the site plays it. |
| `render/sax_detail.py`, `render/voicing_figure.py` | Draw the tenor close-up and the piano-register figure. |
| `fetch_samples.sh` | Fetches the sample libraries into `.samples/`. This is about 550 MB of working files and is git-ignored. |
| `out/` | `ballad_mix_preview.mp3` (192 kbps, not shipped), the tenor A/B in `out/ab/`, `measurements.json`, `browser_check.json`, and the working WAVs, which are git-ignored. |

## Rebuild

```sh
music/fetch_samples.sh                      # once; needs git and curl
pip install lameenc pyloudnorm mido matplotlib soundfile scipy numpy
python3 music/render/render.py              # about 4 min on one core; --reuse keeps cached instrument renders
python3 music/render/measure.py             # re-measure the shipped files and redraw review/round-1/music/*
python3 music/render/ab_tenor.py            # optional: tenor A/B files and numbers in music/out/ab/
# optional: the browser check
python3 -m http.server 8765 --bind 127.0.0.1 --directory site/public/audio &
node music/render/browser/decode_check.mjs 8765 music/.cache/browser_decode.json
python3 music/render/browser_check.py music/.cache/browser_decode.json
```

## The tenor source (A/B, round 1)

Two freely licensed General MIDI tenor banks were reachable, both as per-note renders in gleitz/midi-js-soundfonts: FluidR3 (CC BY 3.0) and Musyng Kite (CC BY-SA 3.0). `ab_tenor.py` renders the head with each through the same chain (`music/out/ab/head_*.mp3`, with the band and tenor alone). Nobody has listened yet, so the choice rests on measurements of what makes a sampled horn sound synthetic:

| Measure (C3-F#4, the head's range) | FluidR3 | MusyngKite |
|---|---|---|
| Timbre movement inside a held note (raw sample) | 1.39 dB | 1.76 dB |
| Timbre jump from one semitone to the next (raw sample, median) | 3.99 dB | 2.60 dB |
| Level movement inside a held note (raw sample) | 1.9 dB | 4.0 dB |
| Timbre jump between slurred notes (rendered head, median) | 6.5 dB | 4.6 dB |
| Tenor spectral centroid (rendered head) | 637 Hz | 526 Hz |

MusyngKite is darker at the source, moves more like a player inside a note, and keeps a more even colour from note to note, so it is the default. FluidR3 was kept as the alternative, not the default, because its notes change colour more from one semitone to the next (it switches recordings every few notes) and its held tone is steadier, which is the organ-like quality Mac heard. MusyngKite carries a slow vibrato of its own (about 5 cents); `sax.py` takes it out of every sample so the only vibrato is the one the renderer plays. The cost is share-alike: the stems that contain the MusyngKite tenor (sax, room, mix) must be offered under CC BY-SA 3.0 (see CREDITS.md). `render.py --sax-bank fluidr3` gives an attribution-only recording.

## What ships (`site/public/audio/`)

- `ballad-{sax,piano,bass,drums,room}.mp3`: five stems, 128 kbps CBR stereo at 44.1 kHz. They all have the same length and are aligned to the sample. The four player stems are dry, and `room` is the reverb return of all four. Played together at unity gain they sum to the mix.
- `ballad-mix.mp3`: the same mix in one file, at the same length and with the same loop points. The lite market could decode this one file instead of five.
- `ballad-events.json`: each player's note onsets in stem time, for animating the musicians.
- `manifest.json`: `{bpm, duration, loopStart, loopEnd, stems}` plus title, key, time signature, `mix`, `events`, `sections` (form with times), `ending` (how to play out instead of looping), `decodedDuration` and `license`.

The site plays from 0 and then loops `loopStart`-`loopEnd`, which is bars 17-80. Bar 80 is written to end exactly like bar 16, and the last 0.4 s before `loopEnd` are spliced from the moment just before `loopStart`. As a result the jump back is continuous to the sample and is the same music. The ending (bars 81-96, the out head, ritardando and fermata) follows `loopEnd` seamlessly in the files, so a player that stops looping and plays on finishes the tune.

LAME adds a 1105-sample encoder delay. The files have no gapless header, so the renderer pre-shifts the audio by that amount. Chromium's `decodeAudioData` (checked with Playwright, Chrome 141) returns exactly the rendered timeline: zero samples of lag on every stem, all five stems 11,874,816 samples at 44.1 kHz (12,924,969 at 48 kHz). The decoded length is 269.270 s, 0.048 s longer than `duration` (269.222 s) because of the encoder's padding in the last MP3 frame, which is silence; the manifest gives both.
