# Round 1: lighting and atmosphere (lighting designer), pass 2

`site/src/lighting/` is the night. `index.js` exports `createLighting({ scene, renderer, camera, lite })`, which returns `{ composer, update(dt, t), setSnow(on), dispose() }`, plus the helpers the engine uses (`placeLights`, `tune`) and a few for tuning (`captureEnvironment`, `captureProbes`, `fitShadow`, `stats`). The settings and the reasoning behind them are in `site/src/lighting/README.md`.

The market report still says `lighting: "lighting"`, with 12 real-time lights, 64 pools and no warnings.

## What changed in pass 2

Each row is one of the panel's requests, in their order.

| Request | What I did | Where to see it |
|---|---|---|
| **Copper pot reads black** | The pot is in `Stall_Wires` with the wires and hinges: `PaletteMaterial002`, metalness 1 and roughness 0.25 from a 64×4 palette texture (copper `#ffc287`). Those values are right; the pot was black because it reflected a dark synthetic sky. Now each of the nearest stalls (6 on full, 2 on lite) gets a **local reflection probe**, captured once from the middle of its metal, glass and glazed props with those props hidden. The probe becomes those materials' `envMap`, so the pot reflects the lit back wall, the bulbs and the dark market in front, as in Cycles. The global `?capture=1` path no longer turns the snow purple, because it now captures from out in front `[2.5, 2.2, 7]`, not from inside the stall's glow. | `pot_closeup.jpg`, `side_by_side.jpg`, `after_capture.jpg` |
| **Specular highlights bloom** | Two fixes. (1) The bloom input clamp went from 14 to **5**, and it now scales by the brightest channel, so hue is kept. A glint enters the bloom no brighter than a bulb (max 6). (2) **Light size**: for direct light only, roughness is floored at 0.32 and clear-coat roughness at 0.30. The reference mugs and pot have a clear coat of roughness 0, which turned three's point lights into single blazing pixels. Environment reflections stay sharp. The glare stars on the pot and mugs are gone; the bulbs still bloom. | `pot_closeup.jpg`, `bulbs_garland.jpg` |
| **Light leaks** | `interiorShadow` went from 0.78 to **0.95**. The wall bounce comes from a dim, unshadowed glow at the same spot (intensity 9, reach 2.4 m), not from a see-through shadow. Unshadowed interior lights (all of them on lite) drop 0.3 m below the eaves, reach 3 m (was 4.2) and run at 70 %. On lite, the roof top no longer glows orange and there is no pool behind the stall. | `after_lite.jpg`, `pass1_vs_pass2.jpg` |
| **Crisper bulbs** | Strength went from 0.65 to **0.40**. The mip weights went from `[1, .7, .38, .16, .06]` to `[1, .4, .13, .045, .015]`. The garland under the bulbs reads clearly. | `bulbs_garland.jpg` |
| **Paler, cooler ground; `capture=1` purple** | The hemisphere fill is paler and less saturated (`#4a5c90` at 0.38) and the moonlight is less saturated (`#9ab0f0` at 0.36). The front fill is now a wide spot aimed down, so the cobbles in front get a cream pool. The bench ground is `#d6dbe4`, near the Cycles preview's snow. The ground right of the stall went from magenta (hue 344°) to neutral cream (hue 21°, saturation 0.08). With `?capture=1` the ground stays blue-grey. | `side_by_side_full.jpg`, `after_capture.jpg`, table below |
| **Lite bloom weights** | Lite (half-resolution bloom) has its own weights `[1, .2, .04, .008, 0]`. On lite the moon halo and lamp glows are now the same size on screen as on full. | `bloom_full_vs_lite.jpg` |
| **Crowd are black cut-outs** | The crowd's coats have albedo 0.01–0.07, so more light alone could not show them. I added a **moon rim**: a cool grazing sheen on steep faces that face the moon disc, added as radiance rather than multiplied by albedo, the way wool catches light. Figures now show cool outlines and some shape against the cobbles. As a side effect, the bench stall's left wall now reads as cool moonlit wood; the reference's is almost black. | `market_home.jpg` |
| **Docs match main.js** | README and these notes now describe the engine as it is: `main.js` calls `lighting.raw.placeLights` and skips `engine/snowfall.js`. `adoptEngineLights` is marked legacy and is opt-in only (`options.adoptEngineLights = true`). The engine-snow masking code is removed. | `README.md` |
| **Real-GPU profile** | There is no GPU in this container (no `/dev/dri`), so I cannot measure it here. Instead: (1) `perf.mjs` profiles the real market (rAF frame times, GPU composer time from timer queries, draw calls, adaptive level) and runs as `node src/lighting/perf.mjs --gpu --headed --fixed` on Mac's laptop; (2) the full profile **adapts at runtime** (see below). Software-GL numbers are in "Performance". | `perf.mjs`, `README.md` → Adaptive quality |
| **Garland and lambrequin lit by the bulbs** | I added **local glows** (`shading.js`): each short, level string of bulbs on a stall becomes a diffuse-only line light (0.6 × bulb colour, 1.1 m reach), evaluated from one shared uniform array in every lit material. The garland, the bulbs' fascia and the lambrequin are lit by their bulbs, and this adds no three.js lights. The wheel, the carousel crown, the tree and the long festoons are skipped. | `bulbs_garland.jpg` |
| **Golden wood, no magenta** | `punch` went from 0.45 to **0.35**. The warm lights now use the Cycles previews' linear colour **(1.0, 0.6, 0.3)** in place of the 2900 K black-body fit, which was linear (1, 0.42, 0.13) and was the main source of the red. The front fill is slightly paler, (1.0, 0.7, 0.36). The counter and sign hues moved from 16–23° to 25–28°, against the reference's 26–29° (table below). | table below |
| **Lite leak pool** | Covered by the leak fix above: 3 m reach, 70 %, dropped below the eaves. | `after_lite.jpg` |
| **Snow blend at any frame rate** | The blend now runs on wall-clock time (`performance.now()`), using the larger of the real `dt` and the wall step. It never uses the 0.1 s clamp. The 2 s fade is 2 s at 5 fps too. | `index.js` → `update` |
| **Refresh reflections** | On full, the global environment is re-captured every **30 s**. It renders **one cube face per frame** (six frames, each one extra 256² scene render with shadow-map updates off) and converts into the same PMREM texture in place. A snow toggle triggers a refresh 2.5 s later. | `env.js` → `createEnvUpdater` |

## Colour against the Cycles reference

`site/src/lighting/measure.py` averages patches of the 1280×720 frames (same camera). The values are sRGB means, then hue in degrees, saturation and lightness.

| Patch | Cycles | Pass 1 | Pass 2 (full) |
|---|---|---|---|
| Counter top | (127, 80, 38) h28 s.54 l.33 | (138, 71, 30) h23 s.65 l.33 | (147, 99, 58) h28 s.43 l.40 |
| Counter front | (62, 31, 7) h26 s.79 l.14 | (79, 29, 3) h20 s.92 l.16 | (68, 35, 11) h25 s.72 l.15 |
| Sign board | (66, 34, 5) h29 s.85 l.14 | (62, 17, 1) **h16** s.97 l.12 | (84, 45, 15) h26 s.70 l.19 |
| Front planks | (59, 30, 4) h28 s.86 l.12 | (54, 13, 1) **h13** s.96 l.11 | (65, 32, 9) h25 s.75 l.15 |
| Back wall | (193, 128, 79) h26 s.48 l.53 | (204, 135, 84) h26 s.54 l.57 | (197, 143, 99) h27 s.46 l.58 |
| Copper pot | (157, 89, 43) h24 s.57 l.39 | (170, 111, 66) h26 s.44 l.46 (a bloom glare over a black pot) | (184, 119, 83) h21 s.42 l.52 |
| Ground right of the stall | (141, 119, 102) h26 s.16 l.48 | (85, 59, 66) **h344** s.18 l.28 | (122, 110, 103) h21 s.08 l.44 |
| Ground left (in the stall's moon shadow in Cycles) | (20, 26, 44) l.13 | (16, 28, 65) s.60 l.16 | (29, 44, 76) s.45 l.20 |

The wood hue now matches within 1–3°. It is a little less saturated than Cycles, because the moonlit fill still reaches the front. The sky is brighter than the reference's near-black, by design: the stars, the moon's halo and the clouds are part of the brief.

## Performance

**Real GPU: not measured.** There is no GPU in this container. The numbers below are SwiftShader (software GL on 4 shared CPUs) and are only a smoke test. They show that the code paths run, not how fast they run.

Run with `perf.mjs` and a frame-by-frame draw-call count on the real market (`?lighting-adaptive=0`):

| Run | Canvas | Frame (rAF p50) | Composer GPU time (timer query) | Draw calls per frame |
|---|---|---|---|---|
| Full, pixel ratio 1.75 | 2180×980 | 20.1 s | no result within the 3 frames sampled | – |
| Full, pixel ratio 1 | 1246×560 | 19.8 s | no result within the frames sampled | 2290 base; +~700 on moon-shadow frames (every 2nd); +~950 on the 6 frames of a reflection refresh every 30 s |
| Lite, pixel ratio 1.75 (capped at 1.25 by main.js) | 1557×700 | 4.1 s | 4.08 s | – |
| Lite, pixel ratio 1 | 1246×560 | 2.8 s | 2.83 s | 906 |

The draw calls are the one number here that carries over to a real GPU. The full market has 1155 visible meshes (704 cast shadows), about 2.6 M triangles in the main pass, 53 shader programs and 686 textures. Most of the calls are the scene itself. This module adds:

- the moon's shadow pass: about 700 calls, now only every 2nd frame (before: every frame, which was 3233 calls a frame on average);
- bloom: 12 calls;
- the grade pass, the sky and the snow: 1 call each (3 for the snow layers);
- the reflection refresh: about 950 calls on each of 6 frames every 30 s.

The interior shadows and the probes are drawn once, at load.

What protects the frame rate on a real laptop, without a measurement from here:

- **Adaptive quality (full only).** After 200 frames, if the median frame over 150 frames is slower than 18.2 ms (about 55 fps), the module steps down once per window, and never back up: MSAA 4× → 2×, then the composer pixel ratio capped at 1.5 (the canvas keeps its own), then bloom at half resolution with the half-resolution weights, then the moon shadow every 4th frame. These are the panel's three suggested fallbacks, applied only on machines that need them. `stats()` reports the level reached, and `?lighting-adaptive=0` turns it off for profiling.
- **The moon's shadow map is redrawn every 2nd frame** (`moonShadowEvery: 2`), which saves about 350 draw calls a frame on average.
- The static interior shadows are drawn once. The probes are drawn once. The reflection refresh is spread over six frames. The local glows are one loop of at most 16 short-circuited iterations per pixel, not extra three.js lights.

**To do on Mac's laptop:** run `cd site && node src/lighting/perf.mjs --gpu --headed --fixed --dpr 1.75`, then run it again without `--fixed`, and paste the two JSON lines here. The first line is the full profile as is (4× MSAA, bloom, 1.75× pixel ratio, static cube shadows). The second shows where the adaptive step-down settles.

## Images in this folder

| Image | What it shows |
|---|---|
| `side_by_side.jpg`, `side_by_side_full.jpg` | The Cycles reference beside pass 2 (half size, and stacked at full size). |
| `pass1_vs_pass2.jpg` | The reference, pass 1, pass 2 full and pass 2 lite. |
| `pot_closeup.jpg` | The copper pot: Cycles, pass 1 (black, glare), pass 2, and pass 2 lite. |
| `bulbs_garland.jpg` | The bulb row and garland: Cycles, pass 1, pass 2. |
| `before_after.jpg`, `before.jpg`, `after.jpg` | Before is the engine's stand-in lighting (`lighting-fallback.js`). After is this module. |
| `after_lite.jpg` | The lite profile: 4 lights, no shadows. |
| `after_capture.jpg` | Full with `?capture=1`: the ground stays blue-grey. |
| `bloom_full_vs_lite.jpg` | Moon halo and glows, full against lite. |
| `sky_moon_stars.jpg` | The sky with the moon, halo, stars and clouds. |
| `wide.jpg` | Fog, ground mist and the front pool. |
| `snow_on.jpg`, `snow_toggle.jpg` | Snow off and on, the lite snow, and a close view showing the depth layers. |
| `market_home*.jpg` | The real market home view with this module, in full, snow and lite. |

## Budgets

| Item | Size |
|---|---|
| Models and textures | None shipped. The sky, stars, snow, environment and probes are generated. |
| Code | About 80 KB of unminified JS in 9 files (`shading.js` is new) |
| Sky dome | 4k triangles |
| Snow | 28.5k points on full, 8k on lite |
| Post | 1 half-float MSAA target, 5 bloom mips, 1 grade pass |
| Shadows | Moon 2048², redrawn every 2nd frame, plus 4 × 512² interior cube maps drawn once (full); none on lite |
| Real-time warm lights | 14 on full, 4 on lite, minus the engine's reserved lights (12 in the market report) |
| Reflections | Global 256² PMREM (refresh: one 256² cube face per frame for 6 frames every 30 s); 6 probes at 128² (full), 2 at 64² (lite), captured once |
| Local glows | 16 (full) / 6 (lite) slots in one shared uniform of 51 / 21 vec4 |

## Open issues and requests

- **BUILD.md: `--palette false`.** This is the only request left for the contract. `gltf-transform optimize` with default settings palettises `bulb_warm` into `PaletteMaterial00x` (the reference glb shipped that way, and the test page renames it), and it merges the copper pot with the wires. The probes cope with palettised metals, but `tuneEmissives` and the bulb glows need the `bulb_` names.
- **Real-GPU frame times** are still to be measured (see Performance).
- **The bench stall's left wall** reads as cool moonlit wood because of the moon rim. The reference's left wall is almost black. I kept the rim because the crowd needs it; if the panel prefers the darker wall, lower `NIGHT.rim.strength` from 0.09 to about 0.05.
- **Glows ignore walls.** A bulb-string glow has a 1.1 m reach and no shadow, so the few centimetres of wall right behind a string also catch it. At this reach it reads as bounce.
- **Snow does not settle.** Snow cover on the ground and roofs (a height-and-normal mask) would pair with `snow_` caps. It is not started.
- **The fog and shading chunk patches are global** to three's `ShaderChunk`. Custom `ShaderMaterial`s with `fog: true` must define `mvPosition`, as stock three already requires. `dispose()` restores the chunks.
