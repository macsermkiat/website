# Round 9 engineer: judges (pass 2)

## Judge 1: Improve

- Failed: Screenshots show each moment at its peak. The harmonica frame shows one bauble glowing and dive_4 shows a fisheye inside-glass view with snow. But schwib_3_light_wave hardly differs from schwib_4_settled: bulbs and bloom are a little brighter, and no warm band about 8 m wide is visible lying across the cobbles at the stalls as claimed. The wave still does not read in a still frame.
- Failed: Work is committed. The builder says src changes, smoke.mjs, NOTES.md, logs and screenshots are all uncommitted, so nothing reaches Pages until the parent session commits them.
- Failed: Smoke log matches the test file on disk. The builder edited smoke.mjs after the run started (deleted the unused skip helper and renamed the wave check), so the log is not a run of the exact file on disk. The edits look harmless but should be re-run.
- Fix: Make the Schwibbogen light wave visible in a still frame. schwib_3_light_wave.jpg looks almost the same as schwib_4_settled.jpg, with no warm band visible on the cobbles. Make the band clearly brighter than the cobbles around it (or the dimmed market around it darker), and retake the screenshot at a moment when the band is plainly visible on the square between the camera and the stalls.
- Fix: Re-run the full smoke test against the final tests/smoke.mjs so the log matches the file on disk, including the renamed wave-frame check.
- Fix: Have the parent session commit all round-9 work: src/shop/lightWave.js, schmuck.js, wurst.js, grillSausages.js, the plate.js deletion, smoke.mjs, NOTES.md, logs, screenshots and the pass1/ renames.
- Fix: Make the ground band and the grill cut less fragile. Select the band's ground materials by a tag or extras flag instead of name patterns (cobble*, setts*, granite_bands, puddle*), and have the load fail loudly (console warn plus a smoke check) if the sausages_grill mesh does not split into exactly 10 pieces.
- Fix: Mac to run npm run perf on a real GPU to confirm the draw counts, the per-frame mirror cost and the dive cube capture.
