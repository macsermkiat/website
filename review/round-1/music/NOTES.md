# Music writer, round 1 (pass 2): "Lanterns After Closing"

## Read this first, Mac

Nobody has heard this recording yet, including me: I can't listen to audio, so everything below is measured. The tenor was your complaint, so it doesn't count as done until you have listened. Please listen to:

1. `music/out/ballad_mix_preview.mp3`, the whole tune. Listen to the tenor at 0:00-0:45 (the head) and 1:28-2:56 (the tenor chorus), and to the brushes throughout.
2. `music/out/ab/head_musyngkite.mp3` and `head_fluidr3.mp3`, the head with each tenor sample bank, then the `_tenor` versions of both, which have the tenor alone. Tell me which one sounds less synthetic. I chose MusyngKite from measurements, not by ear.

Questions (answer any time):

- **Tenor.** Is it still too bright, too breathy, too synthetic or too dull? The settings to change are in `music/render/sax.py`: `BREATH`, `CORE`, and the `TONE` corners for each bank (`lp_dark`, `lp_bright`, `shelf_db`).
- **Share-alike.** The MusyngKite tenor is CC BY-SA 3.0. That means the sax stem, the room stem and the mix have to be offered under CC BY-SA 3.0 with a credit line. Your composition is not affected, only the recording. Is that fine? If not, `render.py --sax-bank fluidr3` makes the whole recording attribution-only (CC BY).
- **3/4 or 4/4.** This is the same question as in pass 1; the concrete choice is set out below.
- **Title.** "Lanterns After Closing" is a placeholder. Keep it or rename it.

## What changed in pass 2

| Judges asked | Done |
|---|---|
| A/B the tenor source (MusyngKite vs FluidR3) and record why one was rejected | Done with `render/ab_tenor.py`. MusyngKite now ships and FluidR3 is the alternative; see "Tenor A/B" for the numbers and the reason. Both A/B renders are in `music/out/ab/`. |
| Fix the muddy low piano voicings | `choose_voicing()` now filters every candidate through low interval limits (no minor 2nd below E3, no major 2nd below E-flat 3, no minor 3rd below C3, and so on). `clear_melody()` now only leaves a voice out and never moves it an octave down. Over the whole piece, voicings with a 2nd below E3 went from **18 of 143** (bars 5-8, 22-23, 29-30, 32, 39, 54-55, 62, 64, 86-87, 93-94) to **0 of 143**. See `piano_voicings.jpg`. |
| Correct the "low intervals are kept open" claim | That claim was false in pass 1. The code had only a soft penalty, and the octave drop in `clear_melody()` bypassed it. It is true now, and `ballad.py` checks it (`voicing_problems()`). |
| Put the tenor where the subtone lives | The piece moved down a fourth, from C minor to **G minor**. The head now spans D3-E4 (concert), and **69 of its 97 notes are below C4**. The piano comp now sits just above the low tune in its middle register instead of being pushed under it, which was the root cause of the mud. |
| Widen the tenor's in-phrase dynamics | Each phrase is now shaped in breath groups of 2.5-4.5 s. Pressure rises about 5.5-8 dB into the group's peak note and relaxes after it, and the phrase tail falls 10-13 dB. Long notes swell 2.5-4 dB, and phrase-final notes fade into breath. The breath share rises and the tone darkens as the pressure drops. Measured in-phrase level range (5th-95th percentile, median over phrases, first 150 s, same notes and timing): **9.3 dB in pass 1, 12.8 dB now** (11.7 dB over the whole piece). The full range inside a phrase is about 22 dB. |
| Make long notes less organ-like | New in pass 2. Long notes no longer repeat one fixed loop. They are built from pieces of the sample's own steady tone, spliced in random order at waveform-aligned points with 40 ms crossfades, so a held note keeps changing slightly and never cycles. A click check on every spliced note finds no discontinuity (worst second-difference peak 1.7 times the 99.9th percentile, against 1.3-1.4 in the untouched samples). |
| Check in Chromium that `decodeAudioData` keeps the stems aligned and the seam clean | Done in headless Chrome 141 via Playwright (`render/browser/decode_check.mjs` + `render/browser_check.py`). Results are under "Browser check" below. The 1105-sample pre-shift is exact (0 samples of lag), so no gapless header is needed. |
| Ending and weight: coordinate with the engineer | The manifest now has `ending`, `sections`, `decodedDuration`, `license` and `stemsEnd`. `render.py --cut-stems` exists but is off. Requests to the engineer are below. |
| Manifest `duration` vs decoded length | `duration` (269.222 s) is the rendered length. `decodedDuration` (269.270 s) is what Chromium and libmpg123 return. The difference is the encoder's padding of the last frame, which is silence. `durationNote` says this. |
| Get Mac's answers (listening, 3/4 vs 4/4, title) | Mac was away during this pass, so the questions are at the top of this file. Nothing was re-rendered in 4/4. |

## The piece (unchanged apart from the key)

- **Tune.** G minor, with warm turns to E-flat maj7#11 (bar 2), B-flat major (the A sections) and B-flat minor to A-flat major (the bridge). It is a 32-bar AABA in 3/4 at quarter = 66, and it lasts 4:29.
- **Form.** Pickup and head (bars 1-32), a written-out tenor chorus with space (33-64), a piano half-chorus over A A (65-80), then the out head from the bridge (81-96) with a ritardando and a rubato fermata on G minor 6/9. The chart is in `music/score/LEADSHEET.md` and `ballad.mid`, and the source is `music/score/ballad.py`.
- **Harmony.** ii-V-i throughout: Am7b5-D7b9-Gm9, Cm9-F13-Bbmaj9, Dm7-G7b9-Cm9, Em7b5-A7b9-Dm9, Bbm9-Eb13-Abmaj9. There are three tritone substitutions: Db7#11 for G7, B7#11 for F7 and Ab7#11 for D7. The piano plays rootless A/B-form voicings or three-note shells of them (21 four-note, 98 three-note and 24 two-note voicings), chosen for the least voice movement.
- **Bass and brushes.** The bass plays one-feel, then two-feel, then walks from bar 41. The drums are brush sweeps, taps on 2 and 3, a feathered kick and the foot hi-hat.
- **Timing.** The tenor lays back about 50 ms with 56:44 swing.

## Tenor A/B

Both banks are gleitz/midi-js-soundfonts per-note renders. They went through the same chain, with the same notes, the same level and a centroid-matched tone. Numbers are in `music/out/ab/ab.json`.

| Measure (C3-F#4, the head's range) | FluidR3 (CC BY 3.0) | MusyngKite (CC BY-SA 3.0) |
|---|---|---|
| Timbre movement inside a held note (raw sample) | 1.39 dB | 1.76 dB |
| Timbre jump from one semitone to the next (raw sample, median) | 3.99 dB | 2.60 dB |
| Level movement inside a held note (raw sample) | 1.9 dB | 4.0 dB |
| Vibrato baked into the sample (sd) | 2.0 cents | 5.3 cents (taken out by `flatten_pitch()`) |
| Timbre jump between slurred notes (rendered head, median) | 6.5 dB | 4.6 dB |
| Tenor spectral centroid (rendered head) | 637 Hz | 526 Hz |

MusyngKite ships because it wins every measure that separates a player from an organ:

- its held tone moves more;
- its colour stays more even from note to note;
- it carries the player's own swell;
- it is darker at the source, so it needs less filtering.

FluidR3 was rejected as the default for two reasons. It changes colour more from one semitone to the next, because it switches recordings every few notes. Its held tone is also steadier, which is the synthetic quality in the complaint. Both findings are proxies, and only your ear can confirm them.

MusyngKite also opens each note with the player's own accent, 2-3 dB above the settled tone for about 0.4 s. Slurred notes therefore start reading the sample after that accent, so a legato line is not re-tongued on every note.

## Measurements (re-measured from the shipped MP3s)

Run `python3 music/render/measure.py`. The full output is in `music/out/measurements.json`.

| Check | Result |
|---|---|
| Stems | 5 files, each 11,874,816 samples (269.27 s decoded), 128 kbps, 4.31 MB. All the same length and aligned to the sample. |
| Tempo | Designed at 66 bpm (3/4). Onset autocorrelation of bass + drums gives **66.0 bpm**. |
| Key | Designed in G minor. Log-compressed chroma against the Krumhansl-Kessler profiles gives **G minor** (r = 0.57). The pass-1 measure used power chroma, which the tenor's long notes dominate, and it now says D minor (r = 0.63), the dominant key. I switched to log chroma, the usual choice, and I report both. |
| Duration | **4:29** (269.2 s). The loop is 44.845-219.391 s (bars 17-80, 174.5 s). |
| Sax spectral centroid (target below 900 Hz) | **548 Hz** mean over active frames. The median is 514 Hz, the mean over all frames 480 Hz, and the long-term spectrum 553 Hz. In pass 1 the mean was 705 Hz. |
| Tenor phrase dynamics | 5th-95th percentile level range inside phrases, as a median over 12 phrases: **11.7 dB**. The full range is 22.1 dB. Over the first 150 s, with the same method and the same notes, pass 1 measured 9.3 dB and this pass measures 12.8 dB. |
| Piano voicings | 143 voicings, **0** outside the low interval limits. |
| Mix peak (target below -1 dBFS) | **-2.97 dBFS** sample peak, -2.97 dBTP true peak. |
| Mix loudness (target about -18 LUFS) | **-18.0 LUFS integrated**. Stems: sax -20.3, piano -23.8, bass -24.4, drums -30.6, room -27.5. |
| Loop seam | The sample step at the jump is 0.0005, against a 99th-percentile step of 0.021 nearby. The level changes by 4.07 dB across the jump and by 4.08 dB across `loopStart` in normal playback: it is the same music. The last 0.4 s before the jump matches what precedes `loopStart` to -26.8 dB (MP3 coding noise). Spectral flux at the seam is 2.4 times the median, about the size of a note onset. |

## Browser check (Chromium `decodeAudioData`)

Chrome 141 headless, through Playwright. The output is in `music/out/browser_check.json`.

- All five stems and the mix decode to **11,874,816 samples** at 44.1 kHz and to 12,924,969 at 48 kHz. They are equal, so they stay aligned in the engineer's context at either rate.
- The lag against the rendered timeline is **0 samples on every stem**, with correlation 0.96-1.00; the drums are lowest because MP3 coding of noise is least exact. Chromium adds no 529-sample decoder delay to these header-less files, so the pre-shift is right and the onsets in `ballad-events.json` line up.
- The loop jump as the site plays it (1 s before `loopEnd`, then from `loopStart`) has sample steps well under the 99th percentile nearby on every stem. The level change at the jump equals the change across `loopStart` in normal playback to within 0.2 dB (sax 0.07 against 0.11, mix 4.56 against 4.41). The bass's 19 dB change is its own downbeat attack on bar 17, which happens in normal playback too.

## For the engineer (please pick up)

1. **Play the ending.** When a visitor leaves the bandstand, or on a "last tune" action, stop looping and let playback run past `loopEnd`. The out head (bars 81-96) follows seamlessly and ends on a fermata; `manifest.ending` has the times. `stems.js` trims the decoded stems at `loopEnd` + 0.05 s, so the cheapest way is to hand over to the streamed `mix` element at the current position, the same handover you already do in the other direction. Nothing extra needs to be decoded.
2. **Lite market.** Use `ballad-mix.mp3`, as `stems.js` already does.
3. **Size.** If the ending plays from the mix file, the stems never need anything past `loopEnd`. `render.py --cut-stems` ends the five stems 1 s after `loopEnd`, which saves about 18% (21.5 MB down to about 17.7 MB), and the mix keeps the ending. Tell me and I'll ship it; it is off for now so nothing changes under you.
4. **Credits.** The plain-HTML version and the credits page need the attribution line from CREDITS.md (music writer). With the MusyngKite tenor, that line includes "recording CC BY-SA 3.0". `manifest.license.recording.credit` has the same text.

## 3/4 or 4/4: the concrete alternative

The brief asks for a head, a tenor chorus, a piano half-chorus and an out head in a 32-bar form at 56-66 bpm, all in at most 4.5 minutes.

- **Now:** 3/4, 96 bars, 4:29 at 66 bpm, with a full 32-bar tenor chorus. It is a jazz-waltz ballad, which is legitimate, but it lilts more than a 4/4 ballad would.
- **4/4 with a 16-bar tenor half-chorus and the out head from the bridge:** 32 + 16 + 16 + 16 = 80 bars, which takes 4:51 at 66 bpm plus the ending. Slowing down makes it longer (5:10 at 62 bpm), and it would need 71 bpm to fit in 4.5 minutes. So this version does not fit the brief. The judges' note suggesting "about 62 bpm" has the direction reversed.
- **4/4 that fits:** head 32, tenor half-chorus 16 (bridge + last A), piano half-chorus 16 (A A), and an out head of the last A only (8), with the fermata on its last bar. That is 72 bars: 4:22 at 66 bpm, and about 4:30 with the ritardando, the fermata and the tail. It needs the melody and solos rewritten in 4/4 in `ballad.py`; everything downstream re-renders as it is.

My recommendation is to keep the waltz unless the 3/4 lilt sounds wrong to you in the preview.

## Files and sizes

- `site/public/audio/`: five stems at 4.31 MB each (21.5 MB), `ballad-mix.mp3` 4.31 MB, `ballad-events.json` 36 KB, `manifest.json` 2.4 KB.
- `music/out/`: `ballad_mix_preview.mp3` 6.5 MB (for listening, not shipped); `ab/` holds four 90 s A/B files at 160 kbps (1.8 MB each), plus `ab.json`, `measurements.json` and `browser_check.json`. The WAVs, the render cache and the sample libraries (about 1.1 GB) are git-ignored.
- Review images in this folder:
  - `spectrogram_sax.png` and `spectrogram_mix.png`;
  - `sax_detail.jpg`: bars 1-8 of the tenor, with a 400 ms phrase-shape curve;
  - `piano_voicings.jpg`: comp register in pass 1 against now, with the E3 line;
  - `arrangement.jpg`: stem levels across the form.
- No 3D assets, so there are no triangle counts.

## Open issues

- **Not listened to.** The tenor source, the brushes (still modelled, since no freely licensed brush samples were found) and the new dynamics all need Mac's ear. The biggest remaining quality risk is that the tenor is still a General MIDI soundfont, however much it is reshaped. A real player recording the head would be the real upgrade.
- **MusyngKite licence provenance.** The CC BY-SA 3.0 statement comes from the gleitz repo's README. The upstream synthfont.com page is blocked from this machine, so I could not confirm it at the source.
- **Two-note voicings.** 24 of 143 voicings are two-note shells, where a voice clashed with the tune and was left out. That is idiomatic, but a pianist would sometimes re-voice instead. A next step is to let `choose_voicing()` look one melody note ahead.
- **One solo.** The loop is the same 174.5 s every time. A second written tenor chorus, played on alternate passes, would stop regular visitors from hearing it repeat.
- **Brushes.** They are unchanged from pass 1 and remain modelled.

## Contract notes

- The spectrograms are PNG because the brief asked for PNG. The other previews are JPEG at 1280 px wide.
- I wrote only inside `music/`, `site/public/audio/`, `review/round-1/music/` and my section of `CREDITS.md`. I did not touch `site/src/audio/stems.js`; the requests for it are above.
- BUILD.md has no audio budget. The stems are 21.5 MB (or about 17.7 MB with `--cut-stems`), and the site's 25 MB first-load aim holds only because the stems load after the market shows.
