# Music writer, round 1 (pass 3): "Lanterns After Closing"

## Read this first, Mac

Nobody has listened to this recording yet, me included: I can't hear audio, so every result below is a measurement. The tenor was your original complaint, so it isn't finished until you have heard it. These files are now in git, so they reach your MacBook:

1. **The whole tune: `site/public/audio/ballad-mix.mp3`** (4:29).
   - Head: 0:01-1:28.
   - Tenor chorus: 1:28-2:56.
   - Piano half-chorus: 2:56-3:39.
   - Out head and ending: 3:39-4:29.
2. **Tenor A/B, in `review/round-1/music/listen/`.** `head_musyngkite.mp3` and `head_fluidr3.mp3` are the head with each tenor sample bank, and the `_tenor` files are the tenor alone. Which one sounds less synthetic? I chose MusyngKite from measurements only.
3. **`review/round-1/music/listen/chorus_b_excerpt.mp3`** is the new second tenor chorus (see below), 1:26-3:03 of the tune.

Questions (answer any time; nothing below waits on them):

- **Q1: Tenor sound.** Is it still too bright, too breathy, too synthetic, or now too dull? In pass 3 it gained a little high air and now breathes between phrases.
  - The settings are at the top of `music/render/sax.py`: `AIR` (new), `BREATH`, `CORE`, and the `TONE` corners for each bank.
  - I'll adjust them from your answer.
- **Q2: Share-alike licence.** The MusyngKite tenor samples are CC BY-SA 3.0. That makes these files share-alike:
  - the sax, room and mix files;
  - the two alternate-chorus files;
  - the listening files that contain MusyngKite.

  They would have to be offered under CC BY-SA 3.0 with a credit line. Your composition is not affected. Is that fine? If not, I re-render with `--sax-bank fluidr3` and the recording becomes attribution-only (CC BY). With FluidR3 I would also lower `AIR` to about 0.6, because it measures 876 Hz, close to the 900 Hz limit.
- **Q3: 3/4 or 4/4?** Same question as before, with the concrete options under "Still open from pass 2". I recommend keeping the waltz.
- **Q4: Title.** Is "Lanterns After Closing" fine?

**Your decisions so far:** none. You were away during this pass, so the licence, the metre (3/4) and the title stay as they were. I'll log each answer here when it comes.

## What changed in pass 3

| Judges asked | Done |
|---|---|
| **Let the tenor breathe.** Stop legato at a written rest, split phrases at rests of 0.5 beat, intake threshold of about 0.35 s, breath points in the head, no run over about 8-10 s | Done. **The longest tenor run is now 9.2 s, down from 64.0 s** (audio gap scan). See "Breathing" below. |
| Get the listening files to Mac | The four A/B files (re-rendered with the pass-3 tenor) and a chorus-B excerpt are in `review/round-1/music/listen/` (8.7 MB, tracked). This file points to the tracked `site/public/audio/ballad-mix.mp3` for the whole tune. |
| Get Mac's answer on CC BY-SA 3.0 | Asked again (Q2). Mac was asleep during this pass. Nothing was re-rendered with FluidR3. |
| Make sure the credits page and plain-HTML version carry the attribution line | Not done yet: that is the engineer's code. As of this pass, nothing in `site/src` or `content/` carries the line. The request is repeated under "For the engineer". |
| **Keep the melody on top.** Cap the comp's top voice at about A4-Bb4, or thin to shells under held tenor notes, and check audibility at 200-1500 Hz | Both done. See "Melody on top". |
| Recheck the breath air (the tenor measured -46.5 dB at 3.2-6.4 kHz) | Added a low air path at 2.4-7 kHz that bypasses the final low-pass (`AIR` in `sax.py`). The tenor at 3.2-6.4 kHz rose from **-46.5 dB to -40.7 dB** relative to its total, and at 6.4-8 kHz from -72.4 dB to -51.0 dB. It still needs Mac's ear. |
| Enable `--cut-stems` once the engineer plays the ending from the mix | Not yet. `site/src/audio/stems.js` still trims at `loopEnd` and has no ending handover, so the stems stay full length and `stemsEnd` stays null. |
| Log Mac's 3/4 and title decisions | No answers yet (Q3, Q4). |
| Fix `midi_export.py` key signature 'Cm' | It now comes from `ballad.KEY` (`key_signature()`). `ballad.mid` has been regenerated and reads `Gm`. |
| Re-voice the 24 two-note shells with a look-ahead | Done. **Two-note voicings went from 24 of 143 to 1 of 143.** See "Piano voicings". |
| Centre the long-note intonation (+5.4 cents sharp) | Fixed, but the cause was different from the one described (see "Intonation"). The tuning is now **+0.3 cents median** over all 28 samples, with a mean absolute error of 1.3 cents. |
| A second tenor chorus for the endless loop, and a freely licensed brush multisample | The chorus is written, rendered and shipped as an optional alternate. The only brush multisample found is itself synthesised, so it was rejected. See "Alternate chorus" and "Brushes". |

### Breathing

What changed:

- **Phrases.** `ballad.tenor_notes()` now ends a phrase at any written rest of half a beat or more (`PHRASE_SPLIT = 0.5`, before 0.74). Inside a phrase, notes are slurred. The last note of a phrase stops 0.08 beat before its written end and never runs into the rest.
- **Release.** In `sax.py`, a phrase's last note releases in at most half the rest that follows it, so even a half-beat rest is a real gap.
- **Breath intake.** It now comes before every phrase after 0.35 s or more of silence (`INHALE_GAP`, before 1.0 s), and it is shortened to fit the gap.
- **Breaths written into the score.** No note was added and the harmony is unchanged. The breaths are:
  - in the head after bars 4, 8, 10, 12 and 14;
  - in the bridge in bars 18, 20, 22 and 24;
  - in the last A in bar 30;
  - the same in the out head;
  - in the chorus at bars 52 and 62.
- **Loop seam.** Bar 16 still matches bar 80.

Gap scan: a breath is at least 0.15 s at more than 30 dB under the loud level.

| | Pass 2 | Pass 3 |
|---|---|---|
| Longest run in the audio | 64.0 s (7.7-71.7) | **9.2 s** (131.2-140.4, bars 48-51 of the tenor chorus) |
| Next longest runs | 27.7 s, 25.8 s, 18.8 s | 9.0 s, 8.6 s, 8.2 s |
| Runs over 10 s | 6 | **0** |
| Phrases | 12 | 35 |
| Longest run in the score (note on/off, 0.3 s gaps) | 64 s | 9.0 s |

The alternate chorus is the same or shorter: its longest run is 7.2 s. The duration is unchanged at 269.2 s, because no bars were added.

### Melody on top

Changes in `ballad.choose_voicing()` and `piano_part()`:

- While the tenor plays, the comp's top voice is capped at B-flat 4 (`TOP_CAP = 70`). Before, 14 of the 48 head voicings went above it, up to E-flat 5. Now 0 of 143 do.
- Under a held tenor note (1.5 beats or more), the comp prefers a three-note shell, plays at 0.80 of its velocity, and skips the soft re-strike on beat 3.
- Under any tenor note, the comp plays at 0.86 of its velocity.
- The piano stem is now levelled on its own half-chorus, at the same -22.3 LUFS as pass 2. Before, it was levelled on the whole piece, which turned a softer comp back up.
- Drop-2 spreads are new candidates. They open the voicing around a low tune, with one voice under it and the rest above. See `piano_voicings.jpg`.
- A tune note at C4 or above may now take a comp entirely under it.

**Audibility in the head** (sax stem against piano stem, band energy at 200-1500 Hz):

| | Pass 2 | Pass 3 |
|---|---|---|
| Sax over piano, whole head | +7.1 dB | **+8.4 dB** |
| Sax over piano, median over the 21 held notes | +14.5 dB | +13.2 dB |
| Weakest held note | -0.3 dB | -1.7 dB |

The weakest held notes are the phrase-final low G3s (bars 5, 16, 29, 32). There the tenor fades into breath by design, and G3's fundamental (196 Hz) sits just below the 200 Hz band. The held-note median is a little lower than in pass 2 because the tenor's phrase tails now fade sooner. The piano under held notes is not louder.

**Top voice above the tenor:** 41 of 44 comp chords in the head and 96 of 107 in the whole piece. It was 93 of 93 in the judges' count, measured differently. Most head chords still reach above the tune, because the head sits at D3-C4. A comp entirely under a G3 would sit in the muddy register below E3, which the low interval limits forbid. What changed is that the chords now straddle a low tune (a voice below, the rest above) instead of stacking over it, and none goes above B-flat 4.

### Piano voicings

`choose_voicing()` now filters in stages:

1. Clear of the tune note at the strike and of the next tune note (the look-ahead). In bars 33-64 this applies to both tenor choruses.
2. Clear of the note at the strike only.
3. The same two with 4 semitones more range.

Each stage is tried first under the top-voice cap, then without it. `clear_melody()` only thins a voicing when every stage fails.

Result, 143 voicings:

| | Pass 2 | Pass 3 |
|---|---|---|
| Two-note voicings | 24 | 1 (bar 46, F13 on one beat, where the two choruses and their next notes leave no rootless voicing clear) |
| Three-note voicings | 98 | 104 |
| Four-note voicings | 21 | 38 |
| Voicings breaking the low interval limits | 0 | 0 |

### Intonation

The +5 cents was not a centring-window problem. `flatten_pitch()` subtracted each sample's own median from its pitch curve. That removed the vibrato but kept each sample's tuning, and the MusyngKite samples sit a median 5 cents sharp (G3 +10). Now the sustained part (0.6 s to the end, the part the splicer reuses) is the reference, and its median offset is removed as well. Measured on the prepared samples (`checks.intonation()`):

| Bank | Median | Mean absolute | Worst |
|---|---|---|---|
| MusyngKite, pass 2 | +5.2 cents | 5.3 cents | +10.3 cents |
| MusyngKite, pass 3 | **+0.3 cents** | 1.3 cents | -5.0 cents |
| FluidR3, pass 3 | +0.4 cents | 0.6 cents | -1.9 cents |

The sample cache is now `*_tenor_v5.npz`.

### Alternate chorus (for the endless loop)

`TENOR_CHORUS_B` in `ballad.py` is a second written tenor chorus over the same changes (bars 33-64). It is original and has the same breath plan as the first. The lines are different:

- a sparse first A built on a falling B-flat to A motif;
- a sequence in the second A;
- long notes in the bridge;
- a dark, low last A.

How it ships:

- **Files.** `ballad-sax-b.mp3` and `ballad-room-b.mp3` are segments of the sax and room stems from 87.98 s to 181.21 s: 93 s, 1.5 MB each, 3.0 MB together. Nothing else changes, because the comp and the piano fills were chosen against both choruses.
- **Manifest.** `manifest.alternates` gives start, end, files and how to switch.
- **Events.** `ballad-events.json` has `saxAlt`.
- **Matching edges.** The first and last half second of each segment are identical to the main stems in the render: the largest difference is 2e-8. After MP3 coding they differ by -28 dB (sax) and -20 dB (room), which is coding noise. A crossfade anywhere in those windows is therefore seamless. The first 0.1 s must be skipped, because it holds the MP3 decoder's priming.
- **Mix with chorus B.** Peak -2.61 dBFS. Loudness -17.27 LUFS over the segment, against -17.42 LUFS for the main mix over the same segment.
- **Tenor centroid in chorus B.** 767 Hz.

Playing it needs the engineer (see below). Until then it does nothing, and the site is unchanged.

### Brushes

I searched GitHub code for brush-sweep SFZ multisamples. The only hit was `matthewmackes/map2-audio` (`data/drums/factory_kits/jazz_brush`). It is CC0, but its README says the samples were "generated procedurally", so it is not a recording and would be no better than the modelled sweeps. I rejected it. The GitHub repository search API is blocked from this machine, and Freesound needs an API key. The brushes stay modelled.

## Measurements (re-measured from the shipped MP3s)

Run `python3 music/render/measure.py`. The full output is in `music/out/measurements.json`.

| Check | Result |
|---|---|
| Stems | 5 files, each 11,874,816 samples (269.27 s decoded), 128 kbps, 4.31 MB. All the same length and aligned to the sample. |
| Tempo | Designed at 66 bpm (3/4). Onset autocorrelation of bass + drums gives **65.99 bpm**. |
| Key | Designed in G minor. Log-compressed chroma gives **G minor** (r = 0.58). Power chroma gives B-flat major, the relative major, which is dominated by the tenor's long notes. |
| Duration | **4:29** (269.2 s). The loop is 44.845-219.391 s (bars 17-80, 174.5 s). |
| Sax spectral centroid (target below 900 Hz) | **761 Hz** mean over active frames. The median is 749 Hz and the long-term spectrum 734 Hz. It was 548 Hz in pass 2; the rise comes from the new air path, and with `AIR = 0` the head measures 575 Hz. |
| Tenor air (sax at 3.2-6.4 kHz relative to its total) | -40.7 dB (pass 2: -46.5 dB). At 6.4-8 kHz: -51.0 dB (pass 2: -72.4 dB). |
| Tenor runs without a breath | Longest 9.2 s, none over 10 s (see "Breathing"). |
| Tenor phrase dynamics | 5th-95th percentile level range inside phrases, as a median over 35 phrases: 13.3 dB. |
| Piano voicings | 143 voicings: 0 outside the low interval limits, 1 two-note, 0 tops above B-flat 4 while the tenor plays. |
| Melody audibility (head, 200-1500 Hz) | Sax +8.4 dB over the piano. |
| Tenor sample tuning | +0.3 cents median. |
| Mix peak (target below -1 dBFS) | **-3.00 dBFS** sample peak, -2.99 dBTP true peak. |
| Mix loudness (target about -18 LUFS) | **-18.0 LUFS integrated**. Stems: sax -20.1, piano -24.7, bass -24.2, drums -30.4, room -27.7. |
| Loop seam | The sample step at the jump is 0.0008, against a 99th-percentile step of 0.022 nearby. The level changes by 3.05 dB across the jump and by 3.01 dB across `loopStart` in normal playback, so it is the same music. The last 0.4 s before the jump matches what precedes `loopStart` to -26.2 dB (MP3 coding noise). Spectral flux at the seam is 1.7 times the median. |
| Browser (Chrome headless via Playwright, `decodeAudioData`) | All five stems and the mix decode to 11,874,816 samples at 44.1 kHz and 12,924,969 at 48 kHz. The lag against the render is **0 samples on every file**, with correlation 0.96-1.00. The loop jump level matches normal playback within 0.4 dB on every stem. Output: `music/out/browser_check.json`. The two alternate segments were decoded with libmpg123 (4,112,640 samples each), not in Chromium. |

## For the engineer (please pick up)

1. **Credits (licence obligation).** Put the attribution line from CREDITS.md (music writer section) on the credits page and in the plain-HTML version. The same text is in `manifest.license.recording.credit`. As long as the MusyngKite tenor ships, the files must be offered under CC BY-SA 3.0 with this line.
2. **Play the ending.** On a "last tune" action, or when the visitor leaves the bandstand, hand over from the looping stems to the streamed `mix` element at the same position and let it run past `loopEnd`. `manifest.ending` has the times. Once that works, tell me and I'll ship `render.py --cut-stems`: the stems end 1 s after `loopEnd`, which takes them from 21.5 MB to about 17.7 MB, and I'll set `manifest.stemsEnd`.
3. **Alternate chorus (optional).** On every second pass through the loop, play `alternates[0].stems.sax` and `.room` in place of the sax and room stems from `start` to `end`. Crossfade in the first and last half second, skipping the first 0.1 s. The segments are 1.5 MB each and are only needed from the second pass on, so they can load late. If memory matters, fold them to mono and 24 kHz like the stems. The musicians' animation can use `saxAlt` from `ballad-events.json` on those passes.

## Still open from pass 2: 3/4 or 4/4 (Q3)

- **Now:** 3/4, 96 bars, 4:29 at 66 bpm, with a full 32-bar tenor chorus (two of them now). It is a jazz-waltz ballad.
- **4/4 that fits the 4.5-minute limit:**
  - head, 32 bars;
  - tenor half-chorus (bridge and last A), 16 bars;
  - piano half-chorus (A A), 16 bars;
  - out head of the last A only, 8 bars.

  That is 72 bars, about 4:30 with the ritardando, fermata and tail. It needs the melody and solos rewritten in 4/4.
- **4/4 with an 80-bar form:** 4:51 at 66 bpm, over the limit. Going slower makes it longer, not shorter.

I recommend keeping the waltz unless the lilt sounds wrong to you.

## Files and sizes

- **`site/public/audio/`:**
  - five stems at 4.31 MB each (21.5 MB);
  - `ballad-mix.mp3`, 4.31 MB;
  - `ballad-sax-b.mp3` and `ballad-room-b.mp3`, 1.49 MB each (not needed on first load);
  - `ballad-events.json`, 38 KB;
  - `manifest.json`, 3.2 KB.
- **`review/round-1/music/listen/`:** four A/B files of 90 s at 160 kbps (1.8 MB each) and `chorus_b_excerpt.mp3` (1.55 MB). They are for Mac, not shipped.
- **Review images:**
  - `spectrogram_sax.png` and `spectrogram_mix.png`;
  - `sax_detail.jpg`: bars 1-8 of the tenor, with the new breaths visible as gaps;
  - `piano_voicings.jpg`: the comp in pass 2 against pass 3, with the E3 line and the B-flat 4 cap;
  - `arrangement.jpg`: stem levels across the form.
- **New code:** `music/render/checks.py` (the pass-3 measures, also run by `measure.py`).
- **Not tracked:** `music/out/` (git-ignored) holds `ballad_mix_preview.mp3`, `ballad_mix_chorus_b_preview.mp3`, the WAVs and the JSON reports.
- **Render time:** a full render takes 4.7 min on one core; `--reuse` takes about 4 min.
- No 3D assets, so there are no triangle counts.

## Open issues

- **Not listened to.** This covers the breaths, the air path, the retuned samples, the new comp and the alternate chorus. The biggest remaining risk is still that the tenor is a General MIDI soundfont, however much it is reshaped. A real player recording the head would be the real upgrade.
- **Air against darkness.** The air path raised the tenor centroid from 548 to 761 Hz. That is still under 900, but it moves toward the brightness Mac disliked. If he hears it as hiss or harshness, set `AIR` to 0.5 (or 0).
- **Licence.** The CC BY-SA 3.0 answer is pending (Q2). The MusyngKite licence comes only from the gleitz repo's README, because synthfont.com is blocked from this machine.
- **Waiting on the engineer.** The credits line, the ending handover, `--cut-stems` and alternate-chorus playback all need the engineer.
- **One tight voicing.** Bar 46 is still a two-note shell.
- **Brushes.** They are still modelled: no recorded, freely licensed brush multisample was reachable.

## Contract notes

- I wrote only inside `music/`, `site/public/audio/`, `review/round-1/music/` and my section of `CREDITS.md`. The share-alike file list was updated there. I did not touch `site/src/`.
- The spectrograms are PNG, as the brief asked. The other previews are JPEG at 1280 px wide.
