# Latest judges on lighting, end of round 1

## Opus (pass 1): Improve

Failed checks:
- Lite profile is free of visible light leaks: My lite.png render (crop of the roof and gable): the unshadowed interior point light lights the gable barge boards and roof eave outside the stall and shows as bright slits through the left wall's plank gaps. The full profile has no such leaks. NOTES also measure the lite shelf wall at lightness 0.67 against Cycles 0.39.
- Real-GPU frame time is verified for the heaviest module: NOTES 'Performance': not measured (no GPU). Full uses 4x MSAA, a 1536² moon shadow every 3rd frame, 4 cube shadows, 24 per-fragment glows patched into every lit material, bloom and grade, at about 2400 draw calls per frame. The adaptive step-down exists but is unproven.
- Builder's report matches the files: The report claims a 2048² moon shadow, no MSAA on lite, engine snow masked with layers.disableAll() and 52 KB in 8 files. The files show 1536² (settings.js), lite msaa: 2, no disableAll (main.js uses ownSnow instead), and 9 modules at about 100 KB including shading.js. The report is stale from an earlier pass; NOTES.md is accurate.

Fixes:
- Lite light leak: with shadows off, the interior point lights shine through the walls. They light the gable barge boards and roof eave outside and show as bright slits in the plank gaps (visible in test.html?lite=1). On lite, clip the interior light's contribution the same way the one-sided interior glow is clipped (use the glow only with lower real-light intensity, or cap the height/side), or give the lite interior a spot light pointed into the stall.
- Lite back and shelf wall wash-out (lightness 0.67 against Cycles 0.39): lower the lite interior intensity or reach until it sits within about 0.1 of the reference, now that the interior glow carries the warmth.
- Measure real-GPU frame time on Mac's laptop (perf.mjs --gpu --fixed --dpr 1.75) before launch. If p50 is over 16.7 ms, make msaa 2 the default and consider cutting the 24 per-fragment glow loop to the nearest 8-12.
- Correct the round report so it matches the files (1536² moon shadow, lite 2x MSAA, no disableAll hack, shading.js included, about 100 KB). The panel and market owner rely on it.
- Market owner items raised by the designer: add `--palette false` to the gltf-transform step in BUILD.md, and have main.js drop the now-redundant SNOW_FOG_MAX override.
- Minor: bring the lambrequin under the bulb row down a little further (0.35 against 0.26), for example with a slightly tighter first bloom mip or a lower bulb-glow intensity on the fascia.

## Fable (pass 1): Ship

Failed checks:
- Review images respect the contract's 1280 px maximum width: bulbs_garland.jpg is 1800x130, ground_artifacts.jpg and lite_counter.jpg are 1440x180 (PIL sizes); BUILD.md asks for JPEG at most 1280 px wide. All other images are 1280 px or less.
- The builder's report matches the files on disk: The report text describes an older pass (2048^2 shadows, no MSAA on lite, layers.disableAll() masking of engine snowfall, re-tuning engine-placed lights, 52 KB in 8 files) and omits shading.js, perf.mjs, measure.py and diag-market.mjs; on disk there is no disableAll/2048, lite has 2x MSAA, 11 JS files (~98 KB), and NOTES.md is labelled pass 3. The files are better than the summary says, but the summary is stale.
- Real-GPU performance of the full profile is measured: NOTES.md and README state the full profile (4x MSAA half-float target, 15 real-time lights, 4 static cube shadows, 1536^2 moon shadow every 3rd frame, 24 per-fragment glows, bloom, ~2400 draw calls) has only been run on SwiftShader; the adaptive step-down (MSAA -> pixel ratio -> half bloom -> shadow cadence) and the lite market are the mitigation, not a measurement.

Fixes:
- Measure the full profile on a real GPU before launch: run `node src/lighting/perf.mjs --gpu --headed --fixed --dpr 1.75` on Mac's laptop; if p50 > 16.7 ms set PROFILES.full.msaa = 2 in settings.js (one line), as the NOTES already propose. This is the one unverified risk in the module.
- Resize the three review strips that exceed the contract (bulbs_garland.jpg 1800 px, ground_artifacts.jpg and lite_counter.jpg 1440 px) to 1280 px wide or less in compose.py.
- Rewrite the builder report to describe the pass-3 files: list shading.js, perf.mjs, measure.py and diag-market.mjs; 1536^2 moon shadow every 3rd frame; 2x MSAA on lite; placeLights called by main.js (no re-tuning of engine lights, no engine snowfall masking); ~98 KB in 11 files.
- Warm the eave and the ground beside the stall toward the Cycles reference: the shingle strip above the bulbs measures lightness .06 vs .23 in Cycles and the ground right of the stall is blue (h250) where Cycles has warm grey (h7). Tilt the front-fill spot a little upward or add a short one-sided glow under the eave, and let the front fill spill a metre further onto the ground.
- Tighten the bulb bloom slightly: blobs are 17-21 px wide against 13-16 px in Cycles and the left bulbs merge into one 143 px run; the band under the bulbs reads 154 vs 112 luma. Try bloom.strength 0.4 -> 0.33 or factors[1] 0.3 -> 0.2 and re-measure with measure.py.
- Bring the back wall and sign down toward the reference (l .66 vs .56, .34 vs .22): section interior 40 -> ~34 or glow.interior.lit 9 -> 7, keeping the counter top where it is.
- Lite: the shelf wall stays at lightness .67 vs .39 because there are no shadows; a cheap fix is a ceiling clip on the interior glow just under the shelf, or the baked-AO/lightmap step the README already reserves for later.
- Market owner: add `--palette false` to the standard gltf-transform optimize step in BUILD.md; the reference glb shows the default palettises bulb_warm into PaletteMaterial00x, which the module's bulb_ name matching then cannot find without the test page's rename.

