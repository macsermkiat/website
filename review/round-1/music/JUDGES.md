# Latest judges on music, end of round 1

## Opus (pass 3): Ship

Failed checks:
- A human has confirmed the tenor is no longer harsh: NOTES.md: no Q1/Q5 answers from Mac; listening page answer store empty — acoustic measures are strong but the subjective brief is unverified (not a builder-fixable blocker)

Fixes:
- Non-blocking: market owner to get Mac's Q1 (tenor tone) and Q5 (brushes) answers via the listening page or the listed MP3s; if he hears harshness or static long notes, lower AIR / TONE['mtg']['lp_bright'] or add the MTG loud layer at the climax and re-render.
- Non-blocking: confirm the upstream freesound.org MTG pack licences (20251, 20239, 20247, 20253) from a machine that can reach them and record the result in CREDITS.md.
- Non-blocking: manifest 'maxDifferenceFromMainStemsAtEdges: 0.0' is true for the render but not after MP3 decode (first ~4 ms of ballad-sax-b.mp3 decodes silent vs a -45 dB tail); either state it as render-only or tell the engineer to crossfade after the first 10 ms of the 0.5 s window.
- Non-blocking: move music/listen/ MP3s out of git history (release asset) before further re-render passes, and have the market owner decide on the 11.3 MB light stem set.

## Fable (pass 3): Ship

Failed checks:

Fixes:

