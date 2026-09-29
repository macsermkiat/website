# Music writer, round 1 (pass 4): "Lanterns After Closing"

## Read this first, Mac

Nobody has listened to this recording yet, me included. I can't hear audio, and this session has no way to reach you, so the market owner has to send you these files. Every result below is a measurement. The tenor was your original complaint, so it isn't finished until you have heard it.

**What to listen to** (all in git, so they reach your MacBook):

1. **The whole tune: `site/public/audio/ballad-mix.mp3`** (4:29). The tenor matters most at 0:00-0:45 (the head) and 1:28-2:56 (the tenor chorus).
   - Head: 0:01-1:28.
   - Tenor chorus: 1:28-2:56.
   - Piano half-chorus: 2:56-3:39.
   - Out head and ending: 3:39-4:29.
2. **Tenor A/B, `music/listen/head_*.mp3`** (bars 1-16, 46 s each). `head_mtg.mp3` is what now ships. `head_musyngkite.mp3` is what shipped in pass 3 and `head_fluidr3.mp3` is the other soundfont. The `_tenor` files are the tenor alone with its room.
3. **Brush A/B, `music/listen/brushes_*.mp3`** (0:44-1:40). `brushes_recorded.mp3` is what now ships and `brushes_modelled.mp3` is passes 1-3. The `_alone` files are the drums alone, 12 dB up.
4. **`music/listen/chorus_b_excerpt.mp3`**: the second tenor chorus, which the site plays on every second pass through the loop.

**Questions:**

- **Q1: Tenor sound.** Is it still too bright, too breathy, too synthetic, or now too dull? The tenor is now a recorded player (see "Tenor"), and I turned the air down from 1.0 to 0.4 before you listen. The settings are at the top of `music/render/sax.py`:
  - `AIR` (hiss above 2.4 kHz, now 0.4);
  - `BREATH` (breath inside the dark EQ, 1.2);
  - `CORE` (the hollow subtone body, 0.9);
  - `TONE["mtg"]` (the dark and bright filter corners).

  One sentence from you is enough for me to retune them, for example "darker", "less hiss" or "more air".
- **Q2: Licence.** This question no longer blocks anything. The shipped tenor is now the MTG recording, under CC BY 4.0, so the whole recording is attribution-only and nothing on the site is share-alike. The CC BY-SA 3.0 Musyng Kite tenor is now only in two listening files in `music/listen/`, which the site does not serve. If you prefer the Musyng Kite tenor by ear, say so and accept share-alike for the sax, room and mix files.
- **Q3: 3/4 or 4/4?** Same question as before (see "Still open: 3/4 or 4/4"). I recommend keeping the waltz.
- **Q4: Title.** Is "Lanterns After Closing" fine?
- **Q5: Brushes.** Do the recorded brushes sound better than the old modelled ones? I switched on the strength of the source alone.

**Your decisions so far:** none. No answers have reached me in four passes. The metre stays 3/4 and the title stays as it is. I'll log each answer here when it comes.

## Correction: what the earlier summary got wrong

The summary I gave the panel after pass 2 was not updated after pass 3, so it described files that no longer shipped. This is what shipped in pass 3 and what ships now:

| | Earlier summary (stale) | Actually shipped in pass 3 | Ships now (pass 4) |
|---|---|---|---|
| Key | C minor | G minor | G minor |
| Tenor samples | FluidR3 GM, CC BY 3.0 | **MusyngKite, CC BY-SA 3.0** (share-alike on the sax, room, mix and both alternate-chorus files) | **MTG Solo Saxophones, a recorded tenor, CC BY 4.0** (no share-alike anywhere on the site) |
| Brushes | modelled | modelled | **recorded** (Swirly Drums, CC0) |
| Sax centroid | 705 Hz | 761 Hz (736-854 Hz in the panel's re-measure) | **644 Hz** (548-864 Hz across 13 methods, see "Measurements") |
| Mix peak | -2.74 dBFS | -3.00 dBFS | **-2.18 dBFS** |
| Alternate chorus | not mentioned | `ballad-sax-b.mp3` and `ballad-room-b.mp3` shipped | same files, re-rendered |

The switch to Musyng Kite in pass 3 made those files share-alike, and the panel had to find that out from the repo. That was my mistake. Pass 4 removes the problem rather than asking Mac to accept it.

## What changed in pass 4

| Panel asked | Done |
|---|---|
| Get Mac to listen and retune from his answer | I can't reach Mac from here. The files he needs are listed above and in `music/listen/`. Nothing was retuned from an answer, because none came. |
| Replace the stale summary with the pass-3 facts | Done above ("Correction"). The structured summary for this pass describes what ships now. |
| Mac's decision on CC BY-SA 3.0. If he declines, go to FluidR3 with a lower `AIR` | I went one better than FluidR3: the tenor is now a **recorded** tenor under CC BY 4.0 (attribution-only), so no share-alike ships and no decision is needed. FluidR3 at `AIR` 0.4 would measure about 731 Hz (bars 1-16, `music/listen/ab.json`). |
| Pull `AIR` back to about 0.5 before Mac listens | `AIR` is now **0.4** (it was 1.0). At 0.5 one centroid method (8192-point frames, every non-silent frame) read 898 Hz; at 0.4 the worst is 864 Hz. |
| Play the ending on the site, then ship `--cut-stems` | The engineer's new `site/src/audio/songplan.js` (in progress this pass) plays the head, three loop passes and then the written ending, **from the stems**. So `--cut-stems` must **not** ship: it would cut the ending out of the stems the site now plays it from. The stems stay full length and `stemsEnd` stays null. |
| Keep looking for a recorded brush kit and tenor | **Both found** in the sfzinstruments GitHub organisation, which the MCP GitHub search could list although the plain search API is blocked. Karoryfer Swirly Drums (CC0) is a brushed jazz kit with recorded snare stirs. MTG Solo Saxophones (CC BY 4.0) is a recorded tenor with breath noises. Both are now the defaults. See "Tenor" and "Brushes". |
| Correct the builder report (key, bank, centroid, peak, share-alike, alternates) | Done (see "Correction" and "Measurements"). |
| Cut the audio weight (mono 64-80 kbps player stems, room 96 kbps) | Built but **not shipped**, because the brief sets 128-160 kbps for stems and only the market owner can relax that. `render.py --light-stems` writes the smaller set to `music/out/light/`: four mono player stems at 64 kbps (2.15 MB each) and a stereo room at 80 kbps (2.69 MB), **11.3 MB against 21.5 MB**. At 56 and 64 kbps it would be about 9.7 MB. The lite market already loads only `ballad-mix.mp3` (`stems.js`: `useStems = !lite`). |
| Move the listening MP3s out of `review/round-1/music/` | Moved to **`music/listen/`**, which I own and which is tracked: 9.3 MB at 128 kbps, with shorter excerpts than before. `review/round-1/music/` now holds only images and this file. The old files are still in git history (commit 73eabf9); whether to rewrite history, and whether listening files belong in git at all, is the market owner's call. |
| Push the ending and alternate-chorus hand-offs to the engineer | The engineer is building both this pass (`songplan.js`: the alternate chorus on every second pass, 0.25 s inside the manifest's edges, then the written ending). The manifest is unchanged in shape, so nothing on my side blocks it. |
| Re-voice the two-note shell at bar 46 (F13) | Done. **0 of 143 voicings are two-note shells** (was 1). Bar 46's F13 is now E-flat 3, G4, A4 (7th, 9th, 3rd): an open rootless shell. See "Piano". |
| Keep the length under 4.5 min | Unchanged at 269.22 s (269.27 s decoded), 0.7 s under the cap. Nothing in this pass added length. |

### Tenor

The tenor source is now **MTG Solo Saxophones**, tenor. The Music Technology Group at Universitat Pompeu Fabra recorded it and published it on freesound.org, kinwie trimmed and mapped it to SFZ, and the sfzinstruments organisation hosts it under CC BY 4.0. It gives:

- one soft (p) sustained note per semitone from A-flat 2 to E5, recorded at 48 kHz and resampled to 44.1 kHz;
- 64 recordings of the player's breathing.

What `sax.py` does with it:

- **Same chain as before.** Each sample loses its recorded vibrato and is tuned to its nominal pitch: median +0.3 cents, worst 2.3 cents over 28 samples. Long notes are sustained by splicing the sample's own steady tone. The subtone body and the pitch-gated breath layer sit on top, and the whole voice goes through the dark EQ. The rendering code still has the slow attacks (130-220 ms), the breath-noise layer, the late vibrato (4.7-5.3 Hz) and the scoops and falls.
- **Recorded breath intakes.** The intakes before phrases are now the player's own breaths, low-passed at 3 kHz and set to the level of the modelled intake they replace. The A/B files use the same recorded breaths for all three banks, so only the notes differ.
- **`AIR` at 0.4 instead of 1.0.** The tenor measures -48.0 dB at 3.2-6.4 kHz relative to its total, against -40.7 dB in pass 3.
- **A floor gate** (`floor_gate()`). It fades the stem to true silence where it sits 70-80 dB under its loud level: the last of the air tails, inaudible in the mix but bright on their own. The reference level is fixed, so the main and alternate-chorus renders gate identically.

Why MTG, going by measurements only (`music/listen/ab.json`, bars 1-16):

- The rendered legato joins change colour least of the three banks: 3.8 dB median, against 4.8 dB for Musyng Kite and 5.5 dB for FluidR3.
- The raw notes differ more from their neighbours (4.9 dB, against 2.6 dB for Musyng Kite), because each semitone is a separate recording.
- Its centroid in bars 1-16 is 656 Hz, between Musyng Kite (632 Hz) and FluidR3 (731 Hz).
- It is a real player on a real horn, not a General MIDI patch.

### Brushes

The brushes come from **Karoryfer Swirly Drums** (CC0), a jazz kit recorded with brushes. `drums.py` now plays:

- **Sweeps.** One stir circle per bar, taken from a random stretch of the 13-second stir recordings. There are four dynamic levels, four takes and two mics (skin and wires). Each circle is shaped by the brush's speed around it and crossfaded bar to bar, so the stir never repeats and never stops.
- **Taps on 2 and 3.** Recorded brush hits: 6 of the 12 velocity layers, 4 takes, top and bottom mics. About one in five soft taps is a "dig", where the brush stays on the head.
- **Hi-hat foot and brushed ride.** Recorded, from the same kit. The ride's bloom, without its attack, makes the swell under the fermata.
- **Feathered kick.** Still the Virtuosity Drums jazz kick (CC0), low-passed.

Component levels were matched to the model's balance: sweeps and taps level with each other, the hat about 13 dB under them.

**Mono fix.** The old model (and my first recorded version) widened the snare with a 2 ms delayed copy. `stems.js` folds the drum stem to mono, where that copy made comb notches every 550 Hz; `brushes.jpg` shows the horizontal striping in both takes. The snare is now panned instead, with no delayed copy. The modelled take in the A/B still has the comb, as it always did.

### Piano

`choose_voicing()` now has one more fallback before it would thin a chord (`open_shells()`). When no close or drop-2 rootless voicing clears both tenor choruses, it opens the shell: the 3rd and 7th plus one colour tone, each in its own octave, at most an octave and a fifth wide, within the low interval limits. The case is bar 46, beat 3: chorus A sits on F13's third (A3) while chorus B sits on its seventh (E-flat 4). The voicing is now E-flat 3, G4, A4. No other voicing changed. See `piano_voicings.jpg`, bars 33-64, pass 3 against pass 4.

## Measurements (re-measured from the shipped MP3s)

Run `python3 music/render/measure.py`. The full output is in `music/out/measurements.json` and the browser check in `music/out/browser_check.json`.

| Check | Result |
|---|---|
| Stems | 5 files, each 11,874,816 samples (269.27 s decoded), 128 kbps CBR stereo, 4.31 MB. All the same length and aligned to the sample. |
| Browser (Chromium 141 headless, `decodeAudioData`) | All five stems and the mix decode to 11,874,816 samples at 44.1 kHz and 12,924,969 at 48 kHz. The lag against the render is **0 samples** on every file. |
| Tempo | Designed at 66 bpm (3/4). Onset autocorrelation of bass and drums gives **66.0 bpm**. |
| Key | Designed in G minor. The log chroma of the pitched stems (tenor, piano, bass) gives **G minor** (r = 0.69). The full mix now reads A minor (r = 0.36): the recorded brushes are broadband noise that flattens the chroma. This is a new measure; the old one is kept in the JSON for comparison. |
| Duration | **4:29** (269.22 s rendered). The loop is 44.845-219.391 s (bars 17-80). |
| Form | 32-bar AABA in 3/4: head (1-32), tenor chorus (33-64), piano half-chorus (65-80), out head from the bridge (81-96) with a ritardando and a rubato fermata. |
| **Sax spectral centroid** (target below 900 Hz) | **644 Hz**: the mean over active frames, magnitude-weighted. The median is 577 Hz and the long-term spectrum 572 Hz. Across 13 methods (1024-8192-point frames; active frames at -40 or -60 dB; all non-silent frames; whole file) it ranges **548-864 Hz**. The highest, 864 Hz, is 8192-point frames averaged over every non-silent frame, which counts quiet breath frames as much as notes. Power-weighted centroids are about 285 Hz. The alternate chorus measures 620 Hz by the first method (542-866 Hz range). |
| Tenor air (3.2-6.4 kHz relative to total) | -48.0 dB (pass 3: -40.7 dB). |
| Tenor runs without a breath | Longest 9.0 s, none over 10 s, 42 runs in the audio (35 phrases in the score). |
| Tenor phrase dynamics | 5th-95th percentile level range inside phrases: 19.2 dB median over 35 phrases (pass 3: 13.3 dB). The recorded samples and the fades into breath move more. |
| Melody audibility (head, 200-1500 Hz) | Sax 8.4 dB over the piano; held notes median 14.4 dB. The weakest held notes are the phrase-final G3s in bars 16 and 32 (-4.0 and -3.5 dB), where the tenor fades into breath by design and G3's fundamental sits under the band. |
| Piano voicings | 143 voicings: 0 outside the low interval limits, **0 two-note shells**, 0 tops above B-flat 4 while the tenor plays. |
| **Mix peak** (target below -1 dBFS) | **-2.18 dBFS** sample peak, -2.18 dBTP true peak. |
| **Mix loudness** (target about -18 LUFS) | **-18.0 LUFS integrated**. Stems: sax -20.0, piano -24.5, bass -24.1, drums -30.5, room -27.7. |
| Loop seam | The sample step at the jump is 0.006, against a 99th-percentile step of 0.025 nearby. The level changes by 4.58 dB across the jump and by 4.59 dB across `loopStart` in normal playback, so it is the same music. The last 0.4 s before the jump matches what precedes `loopStart` to -27.7 dB (MP3 coding noise). In Chromium the jump matches normal playback within 0.2 dB on every stem. |
| Alternate chorus | Renders identical to the main stems at both edges (largest difference 1.5e-8). In the MP3s the sax edge at 0.1-0.5 s is silence, -115 dBFS, with a -120 dBFS residual. Mix with chorus B: peak -2.64 dBFS, -17.05 LUFS over the segment (main mix -17.23 LUFS there). Longest run without a breath: 7.2 s. |

## Audio weight

| Set | Size | Status |
|---|---|---|
| Five stems, 128 kbps stereo | 21.5 MB | shipped (the brief's line) |
| Mix, 128 kbps | 4.3 MB | shipped; the lite market loads only this |
| Alternate chorus (sax and room segments) | 3.0 MB | shipped; the site needs them only from the second pass |
| Four player stems mono at 64 kbps, room stereo at 80 kbps | 11.3 MB | `music/out/light/`, **not shipped**, waiting on the market owner |

`--cut-stems` is retired for now, because the site plays the ending from the stems.

## For the engineer

1. **Credits.** Your credits section already reads `license.recording.credit` and prints it in the footer. The text changed this pass (MTG tenor, Swirly Drums brushes), and your build picks it up without code changes. The FluidR3 line you add for the fallback band is yours, and none of the recorded files I ship use FluidR3 any more.
2. **Ending and alternates.** Both work with the manifest as it is. Keep playing the ending from the stems; I won't cut them.
3. **Drums at 32 kHz mono.** The drum stem is now mono-safe (see "Mono fix").

## Still open: 3/4 or 4/4 (Q3)

- **Now:** 3/4, 96 bars, 4:29 at 66 bpm, with a full 32-bar tenor chorus (two written choruses for the loop). It is a jazz-waltz ballad.
- **A 4/4 version that fits the 4.5-minute limit:** head (32 bars), tenor half-chorus (16), piano half-chorus (16) and out head of the last A only (8). That is 72 bars, about 4:30 with the ritardando and fermata, and it needs the melody and solos rewritten in 4/4.
- **A 4/4 version with an 80-bar form:** 4:51 at 66 bpm, over the limit.

I recommend keeping the waltz unless the lilt sounds wrong to you.

## Files and sizes

- **`site/public/audio/`:**
  - five stems at 4.31 MB each (21.5 MB);
  - `ballad-mix.mp3`, 4.31 MB;
  - `ballad-sax-b.mp3` and `ballad-room-b.mp3`, 1.49 MB each;
  - `ballad-events.json`, 38 KB;
  - `manifest.json`, 3.4 KB (now with `brushes`).
- **`music/listen/`** (for Mac; tracked, not shipped): 9.3 MB, 128 kbps.
  - six tenor A/B files of 46 s, 0.74 MB each;
  - four brush A/B files of 57 s, 0.90 MB each;
  - `chorus_b_excerpt.mp3`, 1.55 MB;
  - `ab.json`.
- **Review images:**
  - `spectrogram_sax.png` and `spectrogram_mix.png`;
  - `sax_detail.jpg`: bars 1-8 of the MTG tenor;
  - `brushes.jpg`: bars 33-36 of the drums alone, recorded against modelled;
  - `piano_voicings.jpg`: bars 33-64, pass 3 against pass 4;
  - `arrangement.jpg`: stem levels across the form.
- **New or changed code:**
  - `fetch_samples.sh` fetches the MTG tenor and the Swirly Drums brushes (about 230 MB more, git-ignored);
  - `sax.py` has the `mtg` bank, recorded breaths, `AIR` at 0.4 and `floor_gate`;
  - `drums.py` has the recorded brushes, with the model kept as `render_modelled`;
  - `render.py` has `--brushes` and `--light-stems`, and the MTG licence;
  - `ballad.py` has `open_shells()`;
  - `ab_tenor.py` covers three banks, writes to `music/listen/` and renders 16 bars;
  - `ab_brushes.py` is new;
  - `measure.py` adds the key on the pitched stems;
  - `voicing_figure.py` draws the tenor chorus.
- **Render time:** a full render takes about 7 min on one core.
- No 3D assets, so there are no triangle counts.

## Open issues

- **Not listened to.** This covers the new tenor, the recorded brushes, `AIR` 0.4 and the bar-46 voicing. Mac's ear on Q1 and Q5 is the only real test of "soft, non-harsh subtone". Until he has heard it, the piece is not finished on the one point he complained about.
- **The tenor is still a sampler.** It is recorded now, but one soft sample per semitone, spliced and reshaped, is not a phrase played by a person. A real player recording the head would still be the big upgrade.
- **MTG's upstream licence is unconfirmed.** The CC BY 4.0 licence comes from the sfzinstruments repository's LICENSE and README. freesound.org is blocked from this machine, so the original MTG packs' page could not be checked.
- **The loudest MTG layer is unused.** Only the soft layer plays. Loud passages are the soft samples pushed harder, which suits a whispered ballad but could sound thin at the climax of the tenor chorus.
- **The brush balance is set by numbers.** The level of the stirs against the taps was matched to the old model, not judged by ear.
- **Listening files in git.** `music/listen/` adds 9.3 MB to the repo, and the pass-3 files are already in history. The market owner should decide where such files live.
- **Weight.** The 128-160 kbps line in the brief keeps the stems at 21.5 MB. The 11.3 MB set is ready if the market owner relaxes it.
- **Waiting on Mac:** Q1-Q5.

## Contract notes

- I wrote only inside `music/`, `site/public/audio/`, `review/round-1/music/` and my section of `CREDITS.md`. I did not touch `site/src/`.
- `review/round-1/music/` now holds only this file and preview images. The listening files moved to `music/listen/`.
- The spectrograms are PNG, as the brief asked. The other previews are JPEG at 1280 px wide.
