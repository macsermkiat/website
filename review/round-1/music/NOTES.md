# Music writer, round 1 (pass 5): "Lanterns After Closing"

## Read this first, Mac

The panel found a real fault in the pass-4 tenor, and it's the kind you objected to. Held notes cut out by about 40 dB and re-attacked mid-note. The clearest case was the opening B-flat to A (0:01-0:06, again in bars 9-10, 25-26 and 34). It is fixed, and a check now fails the build if it comes back. Nobody has listened to the fixed version yet. I can't hear audio, and I still can't reach you from this session.

**The easiest way to listen: https://claude.ai/artifact/HXBzuBTGyAKvMgGMNoEXPu**

This private page has the full mix with jump buttons for each section, the tenor head with the band and alone, and the brush A/B. It also has two answer boxes. Your answers are saved with the page, and I read them at the start of the next pass. The page is private to the claude.ai account that published it. If that account isn't yours, the market owner has to share it with you from the page's Share menu, or send you the files below.

**The same files in the repo:**

1. `site/public/audio/ballad-mix.mp3` (4:29). The tenor matters most at 0:00-0:45 (head) and 1:28-2:56 (tenor chorus). The sections are head 0:01-1:28, tenor chorus 1:28-2:56, piano half-chorus 2:56-3:39, and out head and ending 3:39-4:29.
2. `music/listen/head_mtg.mp3` and `head_mtg_tenor.mp3`: bars 1-16 with the band, then the tenor alone with its room. The `head_musyngkite*` and `head_fluidr3*` files are the other two tenor banks, re-rendered with the same fix.
3. `music/listen/brushes_recorded.mp3` (what ships) and `brushes_modelled.mp3` (passes 1-3). The `_alone` files are the drums alone, 12 dB up.
4. `music/listen/chorus_b_excerpt.mp3`: the second tenor chorus, which the site plays on every second pass through the loop.

**Questions** (one sentence each is enough):

- **Q1: Tenor.** Is it still too bright, too breathy, too synthetic, or now too dull? The settings are at the top of `music/render/sax.py`: `AIR` (hiss above 2.4 kHz, 0.4), `BREATH` (breath inside the dark EQ, 1.2), `CORE` (subtone body, 0.9) and `TONE["mtg"]` (filter corners). A retune and re-render takes about 7 minutes.
- **Q5: Brushes.** Do the recorded brushes sound better than the modelled ones?
- Q3 (3/4 or 4/4) and Q4 (the title) are still open. See "Still open: 3/4 or 4/4". Without an answer the waltz and the title stay as they are.

**Answers received so far:** none. The page's answer store was empty when I checked it after publishing.

## What changed in pass 5

| Panel asked | Done |
|---|---|
| Fix `SaxBank._prepare` so splice pieces come only from the steady part of each MTG sample; end the window where the level first falls about 3 dB under the steady median; bump the cache to `mtg_tenor_v6`; re-render everything and republish the listening files | **Done.** `steady_window()` ends the splice window where the 100 ms level first falls 3 dB under the median of 0.5-2.0 s. For the MTG notes that is 2.5-3.2 s into the file, where it used to be `len - 0.15 s` (3.5-4.7 s), deep in each note's decay. `level_drift()` also levels the slow 1-3 dB drift inside the window, so pieces from its two ends join at the same level. The cache is now `mtg_tenor_v6.npz`. All five stems, the mix, both alternate-chorus files and the light set were re-rendered in a full run (no `--reuse`). All 12 files in `music/listen/` were republished; `chorus_b_excerpt.mp3` now has its own script, `listen_chorus_b.py`. |
| Add an automated check to `measure.py` that fails on a held note that dips more than 12 dB mid-note and recovers; run it on `ballad-sax.mp3` and `ballad-sax-b.mp3`; regenerate `sax_detail.jpg` | **Done.** `checks.held_note_dips()` reads every tenor note of 0.6 s or more from 0.25 s after the onset to 0.12 s before the end. A dip is the lowest 20 ms level measured against the loudest point before it *and* the loudest point after it, so a fade into breath doesn't count but a hole does. `measure.py` exits with status 1 if either file has one. Pass 4's files fail: 11 of 97 held notes (deepest 41.8 dB) and 3 of 39 (37.2 dB). Pass 5's files pass: 0 of 97 (deepest 0.7 dB) and 0 of 39 (0.8 dB). `checks.prepared_bank_dips()` runs the same test on the prepared samples themselves: 27 of 28 were holed in pass 4 (deepest 58 dB), and none are now (deepest 2.5 dB over 14 s). `sax_detail.jpg` now covers bars 1-10 and draws pass 5 above pass 4, with each dip marked. |
| Re-measure the "tenor phrase dynamics 19.2 dB" figure and the claim that "the recorded samples move more" | **Corrected.** The median 5th-95th percentile level range inside phrases is **15.6 dB** (full range 19.7 dB). Pass 4 read 19.2 dB (26.6 dB) and pass 3 read 13.3 dB. Of the 5.9 dB rise from pass 3 to pass 4, **3.6 dB came from the splice holes**. "The recorded samples move more" was **wrong**. A prepared MTG note moves 0.7 dB (5th-95th percentile over 7 s), against 1.7 dB for Musyng Kite and 1.6 dB for FluidR3 through the same splicer (3.4 dB and 2.0 dB with the old one). The MTG tone is the steadiest of the three. The remaining 2.3 dB over pass 3 comes from the renderer and the bank change (the attacks, the fades into breath, and the level steps between separately recorded semitones), not from movement inside the samples. On the same bars (1-16), with the same chain and notes, the three banks measure MTG 15.7 dB, Musyng Kite 13.6 dB and FluidR3 18.1 dB. |
| Get Mac to listen after the fix, and log his Q1 and Q5 answers | **Half done.** The listening page above went up after the fix, and the files in the repo are the fixed ones. No answers yet. |
| Report the key from the score, or say which chroma method gives r 0.69 | **Both.** From `score/ballad.mid`, a duration-weighted pitch-class histogram of every pitched note (chorus B left out, drums excluded) against the Krumhansl-Kessler profiles gives **G minor, r 0.754**, with B-flat major (the relative major) next at 0.647. The last bass note is G, the tenor track reads G minor and the bass track reads G minor. The piano track alone reads B-flat major, because rootless voicings leave out the root. The r 0.69 figure (now 0.697) is `measure.key_estimate()` on the sum of the sax, piano and bass stems: mono, decimated to 22.05 kHz, 8192-point STFT with hop 4096, magnitudes compressed as log1p(1000·\|X\|/max), summed per pitch class over 55-2000 Hz, Pearson r against all 24 KK profiles. Audio chroma of this piece is not stable across methods: power chroma of the same stems reads C minor (0.51), the full-mix log chroma reads B-flat major (0.37), and the panel's own chroma read D minor. All four are close relatives of G minor. The score is the reference, and `measurements.json` now carries `key_from_score_midi` and the method text. |
| (Minor) one phrase start rose in 49 ms at 72.9 s; clamp non-legato attacks to about 0.10 s | **Done as a floor.** `MIN_ATTACK = 0.10` is now the lowest attack time for any note that starts from silence (they already drew 0.13-0.23 s). The breath intake's fade-in is now at least 0.12 s. The sound at 72.9 s in the pass-4 stem is the recorded breath intake (72.70-73.03 s) before the phrase at 73.10 s; the note itself rises over about 140 ms (73.08-73.22 s). With my own measure (`checks.phrase_start_rise`: 10% to 90% of the amplitude the note reaches in its first 0.12-0.47 s), the fastest phrase start in pass 5 is 70 ms (the 0.52 s G3 at 7.59 s) and the median is 290 ms. |
| (Optional) use the MTG loud layer at the climax if Mac finds the solo thin | Not done. It waits for Q1. |
| Market owner items: the light stem set, the listening files in git, the MTG upstream licence | Not mine to decide. See "For the market owner". I tried the licence check again: the proxy still refuses freesound.org (HTTP 403 on the tunnel), and a fetch through the web tool was not approved. `CREDITS.md` records the attempt. |

### Side effects of the fix, measured

- **Sax centroid down 45 Hz** (644 to 599 Hz, active-frame mean). The re-attacks and the decayed tails were bright.
- **Release tails are now steady tone down to near-silence.** The phrase-final G3 before chorus B (85.81-87.96 s) now releases into -69 dBFS where pass 4 had -115 dBFS, because the note's tail now reads steady tone, not the sample's decayed end. -69 dBFS is inaudible. It makes the alternate file's start-edge residual read -27.6 dB relative to that signal (about -97 dBFS absolute). The renders are still identical at both edges: 0.0 for the sax, 1.5e-8 for the room.
- **The chorus-B mix peak moved up**, from -2.64 to -1.66 dBFS decoded (-1.30 dBFS in the WAV), because held notes in chorus B no longer drop out. The renderer's local limiter on the alternate stems holds it under the ceiling. The main mix peak is -2.45 dBFS.

## Measurements (re-measured from the shipped MP3s)

Run `python3 music/render/measure.py`. It prints `PASS held-note dips: ...` or exits 1. The full output is in `music/out/measurements.json` and the browser check is in `music/out/browser_check.json`.

| Check | Result |
|---|---|
| Stems | 5 files, 11,874,816 samples each (269.27 s decoded), 128 kbps CBR stereo, 4.31 MB each. Equal length, sample-aligned. |
| Browser (Chromium, `decodeAudioData`, re-run this pass) | All five stems and the mix decode to 11,874,816 samples at 44.1 kHz and 12,924,969 at 48 kHz, with **0 samples** of lag against the render. The loop jump matches normal playback across `loopStart` within 0.2 dB on every stem. |
| Tempo | Designed at 66 bpm (3/4). Onset autocorrelation of bass and drums: **66.0 bpm**. |
| Key | **G minor from the score MIDI** (r 0.754; final bass note G). Audio: G minor on the pitched stems with log chroma (r 0.697). See the method above. |
| Duration | **4:29** (269.22 s rendered). The loop runs 44.845-219.391 s (bars 17-80). |
| Form | 32-bar AABA in 3/4: head (1-32), tenor chorus (33-64), piano half-chorus (65-80), out head from the bridge (81-96) with a ritardando and a rubato fermata. |
| **Sax spectral centroid** (target below 900 Hz) | **599 Hz** (mean over active frames). The median is 558 Hz and the long-term spectrum 558 Hz. Across 13 methods (1024-8192-point frames × active at -40 dB, active at -60 dB, or every non-silent frame, plus the whole-file spectrum) it ranges **523-786 Hz**. The harshest method (8192-point frames over every non-silent frame) was 864 Hz in pass 4. The alternate chorus measures 588 Hz. |
| **Held-note dips** (new gate, limit 12 dB) | `ballad-sax.mp3`: 0 of 97 held notes, deepest 0.7 dB. `ballad-sax-b.mp3`: 0 of 39, deepest 0.8 dB. Prepared bank: 0 of 28 semitones, deepest 2.5 dB. The `head_*_tenor.mp3` listening files also pass: deepest 6.6 dB, with the room filling in. |
| Tenor phrase dynamics | 5th-95th percentile range inside phrases: 15.6 dB median over 35 phrases (pass 4: 19.2 dB with holes; pass 3: 13.3 dB). |
| Phrase-start rise (10-90%) | Fastest 70 ms, median 290 ms, over 35 phrase starts. |
| Tenor air (3.2-6.4 kHz relative to total) | -48.5 dB. |
| Tenor runs without a breath | Longest 9.0 s, none over 10 s. |
| Melody audibility (head, 200-1500 Hz) | Sax 8.8 dB over the piano; held notes median 14.7 dB. |
| Tenor sample tuning | Median +0.3 cents, worst 2.3 cents. |
| Piano voicings | 143 voicings: 0 outside the low interval limits, 0 two-note shells, 105 three-note and 38 four-note. |
| **Mix peak** (target below -1 dBFS) | **-2.45 dBFS** sample peak, -2.44 dBTP true peak. With chorus B: -1.66 dBFS. |
| **Mix loudness** (target about -18 LUFS) | **-18.0 LUFS integrated**. Stems: sax -20.1, piano -24.6, bass -24.2, drums -30.5, room -27.8. |
| Loop seam | The sample step at the jump is 0.0011, against a 99th-percentile step of 0.0245 nearby. The level changes 4.52 dB across the jump and 4.52 dB across `loopStart` in normal playback: it is the same music. The 0.4 s before the jump matches what precedes `loopStart` to -27.6 dB (MP3 coding noise). |

## Audio weight

| Set | Size | Status |
|---|---|---|
| Five stems, 128 kbps stereo | 21.5 MB | shipped (the brief's line) |
| Mix, 128 kbps | 4.3 MB | shipped; the lite market loads only this |
| Alternate chorus (sax and room segments) | 3.0 MB | shipped |
| Four player stems mono at 64 kbps, room stereo at 80 kbps | 11.3 MB | `music/out/light/`, re-rendered with the fix, **not shipped** |

## For the market owner

1. **Send Mac the listening page** (or the files listed at the top) and ask for one sentence each on Q1 and Q5. If he still hears harshness, the next pass lowers `AIR` or `TONE["mtg"]["lp_bright"]` and re-renders.
2. **Light stem set.** Ship `music/out/light/` only if you relax the brief's 128-160 kbps line for stems. Otherwise leave it as it is.
3. **Listening files in git.** `music/listen/` holds 9.3 MB, rewritten this pass, and the pass-3 files remain in history (commit 73eabf9). Either accept that or move them to a release asset before the next pass. Every re-render rewrites these MP3s, so each pass adds up to 9.3 MB to the history.
4. **MTG upstream licence.** Confirm freesound.org packs 20251, 20239, 20247 and 20253 from a machine that can reach them, and record the result in `CREDITS.md`. The credit now relies on the sfzinstruments LICENSE (CC BY 4.0).

## For the engineer

Nothing changes on your side. The manifest is the same shape, the stems keep their names and length, and `license.recording.credit` is unchanged.

## Still open: 3/4 or 4/4 (Q3)

- **Now:** 3/4, 96 bars, 4:29 at 66 bpm, with a full 32-bar tenor chorus (two written choruses for the loop). It is a jazz-waltz ballad.
- **A 4/4 version that fits the 4.5-minute limit:** head (32 bars), tenor half-chorus (16), piano half-chorus (16) and out head of the last A only (8). That is 72 bars, about 4:30 with the ritardando and fermata.
- **A 4/4 version with an 80-bar form:** 4:51, over the limit.

I recommend keeping the waltz unless the lilt sounds wrong to you.

## Files

- **`site/public/audio/`** (28 MB, all re-rendered): five stems at 4.31 MB each, `ballad-mix.mp3` (4.31 MB), `ballad-sax-b.mp3` and `ballad-room-b.mp3` (1.49 MB each), `ballad-events.json`, `manifest.json`.
- **`music/listen/`** (9.3 MB, all republished): `head_{mtg,musyngkite,fluidr3}[_tenor].mp3`, `brushes_{recorded,modelled}[_alone].mp3`, `chorus_b_excerpt.mp3`, `ab.json`.
- **Review images:** `spectrogram_sax.png`, `spectrogram_mix.png`, `sax_detail.jpg` (bars 1-10, pass 5 above pass 4 with the dips marked), `arrangement.jpg`, `brushes.jpg`, `piano_voicings.jpg` (unchanged; the piano didn't change).
- **Code changed this pass:**
  - `sax.py`: `steady_window()`, `level_drift()`, the new `_prepare`, cache v6, `MIN_ATTACK`, the intake fade-in floor.
  - `checks.py`: `held_note_dips()`, `prepared_bank_dips()`, `phrase_start_rise()`.
  - `measure.py`: `key_from_midi()`, the key method text, power chroma on the pitched stems, and the dip gate with its exit status.
  - `sax_detail.py`: bars 1-10, dip markers, an optional before-file.
  - `listen_chorus_b.py`: new.
  - `README.md` and `CREDITS.md`: updated.
- **Render time:** 5 min 52 s wall clock for a full render; the tenor bank rebuild adds about 19 s the first time.

## Open issues

- **Not listened to.** Mac's ear on Q1 and Q5 is the only real test of the "soft, non-harsh subtone". The splice fault that went unnoticed for a pass is a reminder that measurement alone missed something audible.
- **The MTG tone is steady.** A prepared note moves only 0.7 dB. All the life in a held note now comes from the renderer (swells, vibrato, pressure), so a long note could sound a little static. Mac's ear will tell.
- **The tenor is still a sampler**: one soft sample per semitone, spliced and reshaped. A real player recording the head would still be the big upgrade. The loud MTG layer is unused.
- **The chorus-B mix peak is -1.66 dBFS**, still under -1 dBFS but with less margin than the main mix (-2.45).
- **The MTG upstream licence is unconfirmed.** freesound.org is still blocked here.
- **Audio chroma disagrees with itself** (G minor, C minor, B-flat major; the panel read D minor). The score says G minor.
- **Listening files and the light set** wait on the market owner (see above).

## Contract notes

- I wrote only inside `music/`, `site/public/audio/`, `review/round-1/music/` and my section of `CREDITS.md`. I didn't touch `site/src/`.
- The listening page is a private claude.ai artifact built from files in `music/listen/` and `site/public/audio/`. It is not part of the site, and nothing in the repo depends on it.
- No git commit or push.
