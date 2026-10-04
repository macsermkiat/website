# Round 2: lighting and atmosphere (lighting designer)

This pass (pass 3) continued from the partial round-2 work on disk after a restart. It adds warmer bulb cores, softer shelf shadows and a softer Ferris hub, re-shoots the bench, the home view, the Glühwein approach and both lite entered views, and brings this file up to date with the code (the sign-lamp hood, the focus checks).

Pass 4 (after a second restart) changed no code. It found that the bench screenshots on disk (`raw/after.png`, `raw/lite.png`, `raw/snow.png`, `raw/nosign.png`) were still the pass-1 renders, so `after.jpg`, `after_lite.jpg`, `side_by_side*.jpg`, `snow_toggle.jpg`, `sign_lamp_bench.jpg` and `lite_gable.jpg` showed the brighter × 4.8 bulbs and the hard shelf shadows. It re-shot all four from the current code, re-made those images and `bulbs_closeup.jpg` (the pass-1 frames are kept in `raw_pass1/` for that comparison), and re-ran `measure.py`: every number in the colour table below comes from the new `raw/after.png` and `raw/lite.png`.

## Fix pass (the judges' round-2 fixes)

This pass made the five fixes the judging panel asked for, in their order:

| Fix asked for | What I did | Where to see it |
|---|---|---|
| **Ferris hub starburst** | Two causes, both fixed. (1) **The hub's bulbs:** the 16 spokes' bulb strings converge on the hub and their last 3–4 m overlapped into one bloom. New `hubFade` (`lights.js`, settings `emissive.hubFade`): every `bulbs_` mesh under a `rot_wheel` gets a per-vertex fade by distance from the wheel's axis, **0.15** at the hub's rim (1.2 m) up to full at 5 m, through a cloned bulb material with a one-line emissive patch. The inner bulbs sit under the bloom threshold, so they read as small amber dots and the wheel reads as rim and spokes. It adds no draw calls, and the gondolas' bulbs are left alone. (2) **The wash light:** three's distance window (1 − (d/D)⁴)² at an 18 m reach still gave the hub 7.5× the rim's light. The wash now hangs 9.2 m in front of the hub (`washOut` 3 → 6), with reach 18 → 30 m and intensity 70 → 56: the rim keeps its light and the hub gets 63 % less (2.7× the rim). **Home view, measured** (40 px square on the hub): mean luma 141 → **100**, brightest pixel 242 → **201**, pixels over 230: 62 → **0**. | `market.jpg`, `market_hub.jpg` (home-view hub, pass 3 against this pass), `wheel_hub_bench.jpg` (the wheel alone on the bench with its own lights) |
| **Re-shoot `market_sign_wurst.jpg`** | Re-shot from the current code, along with every other full-market image (home, both sign approaches, both stalls entered) and both lite entered views. To make this affordable, `shoot-market.mjs` can now take several views in one page load: `@snap=name` captures mid-sequence, `@home` goes back to the home view, and `@front=place_bratwurst,7.5,1.7` frames a stall's sign from a visitor's approach. Loading the market is most of a 45-minute software-GL shot. | `market_signs.jpg`, `market_sign_wurst.jpg`, `market_sign_glueh.jpg`, `market_glueh.jpg`, `market_wurst.jpg`, `market_lite_*.jpg` |
| **Explicit `focusPlace` from the engine** | The request for BUILD.md (the market owner adds it; I don't edit BUILD.md): *Engine: `openPlace(id)` calls `lighting.raw.focusPlace(id)` before the camera flight starts, and closing the panel or `resetView()` calls `lighting.raw.focusPlace(null)`.* In `main.js` that is one line in `openPlace` (`lighting.raw?.focusPlace?.(id);`) and one in the close and reset paths. On my side, the first explicit call now turns the camera-settle detection off for good. Before, `focusPlace(null)` handed control back to it, so a close would have re-armed the heuristic. | README "The entered place gets the lights"; `market_lite_glueh.jpg`, `market_lite_band.jpg` (shot with explicit calls) |
| **Back-wall bulb merging: baked AO, not more bloom** | The carpenter's stalls ship a baked AO map (`occlusionTexture`, uv1) since round 3, but three applies it only to the hemisphere and the environment. `shading.js` now applies it (`lightingAO()`, settings `ao`) to every local glow in full (they stand in for bounce light) and to the short-reach interior lamps at 60 % (reach under 6 m, so not the washes or the bandstand). On the shipped Glühwein stall the bulbs hang in front of the red lambrequin and stand apart: 15 runs, widest 16 px, with the AO a little darker under the roof (`ao_stall.jpg`, `ao_bulb_row.jpg`). The 123 px run comes from the old bench glb (`review/reference/gluehwein_stall_web.glb`), which has no AO map and hangs its bulbs in front of the pale back wall. I raycast the bench and found that wall 0.85 m from the lamp, just under its horizon. I tried a lamp radius for diffuse light (r 0.3–0.7 m), a shade over the lamp's horizon, a lower interior-glow ceiling, and no interior glow at all. None of them separated the bulbs without darkening the shelves (best: widest run 117 px with the shelf wall down from .34 to .30, Cycles .39). So none of them are kept, and the bench numbers below are unchanged. | `ao_stall.jpg`, `ao_bulb_row.jpg`, `bulbs_closeup.jpg` |
| **Real-GPU p50, MSAA 2× if over 16.7 ms** | **Not measurable here.** This machine has no GPU (no `/dev/dri`; Chromium uses SwiftShader), and this session cannot reach Mac's laptop. Instead the judges' rule now runs at run time: the adaptive quality's first step (MSAA 4× → 2×) triggers at a median of **16.7 ms** (`adaptiveMs`, was 18.2), so any GPU slower than 60 fps settles at 2× within about 5 s. The laptop command and what to set are in README "Real-GPU frame time". | README |

The bench images (`after`, `after_lite`, `side_by_side*`, `snow_toggle`, `sign_lamp_bench`, `lite_gable`, `bulbs_closeup`) were not re-shot. None of this pass's changes reach the bench glb: it has no wheel and no AO map, so its pixels match pass 4. I checked this with a fresh `after` shot of the final code: it differs from pass 4's `raw/after.png` by 0.0006 code values on average (9 at most, from the noise of the snow-free grain), and every number in the table below is the same.

`site/src/lighting/` is the night. `index.js` exports `createLighting({ scene, renderer, camera, lite })`, which returns `{ composer, update(dt, t), setSnow(on), dispose() }`. It also has the helpers the engine uses (`placeLights`, `tune`) and one new one this round, `focusPlace(id)`. The settings and the reasons for them are in `site/src/lighting/README.md`. Every round-2 change there is marked "round 2" and gives the round-1 value it replaced.

The market report for the full home view says `lighting: "lighting"`, with 12 real-time lights (4 section interiors, 4 front fills, bandstand, tree, carousel, Ferris wheel) and no warnings.

## Round-2 priorities

| Priority | What I did | Where to see it |
|---|---|---|
| **1. Light the stall signs** | Every stall with a `slot_sign` now gets a **sign lamp** (`lights.js` `signRect` / `signFixture`, `settings.js` `glow.sign`). The module finds the board by casting rays at `slot_sign` from in front of the stall and walking out to the board's edges, so it works whatever board the carpenter or vendor built. It then puts a one-sided line glow (a small area light) 0.3 m in front of the board and 0.1 m over its top, 75 % of the board's width, at intensity 1.5 with 1.1 m reach. The glow is clipped from 8 cm below the board to just under the lamp, so it never lights the roof. There is a visible fixture too: a picture-light hood (a 3.5 cm bronze arc over a warm tube, with a warm reflector inside and two arms down to the board's top edge), all lamps merged into one mesh (3 draw calls, 112 triangles a lamp). Because it is a glow and not a three.js light, full and lite get the same lamp and lite keeps its four real lights. I also found why the Glühwein board had washed out: round 1's roof glow (`glow.eave`) caught the market Glühwein stand's fascia board and pushed it to 240/255 with pale pink letters. That glow now stops at the top of any sign board in front of it. | `market_signs.jpg`, `market_sign_glueh.jpg`, `market_sign_wurst.jpg`, `sign_lamp_bench.jpg`, `home_signs.jpg`, `market_glueh.jpg` |
| **2. Codex fix 2: glare, moon dominance, signs, crowd and facades** | **Moon:** disc 0.03 → 0.02 rad, HDR 4.2 → 2.8, halo 0.55 → 0.3. It is no longer the biggest, brightest thing in the home view. **Glare:** warm bulbs 6 → 4.8, since up close their white cores and halos were glare and washed the Glühwein board. Ground spill under each section stall 11 → 7.5 with reach 8 → 6 m, since those pools were the brightest ground in the home view. **Crowd:** the hemisphere's ground colour is now a warm bounce, `#3a2c22` (was a cold near-black `#14161c`), at 0.4. That lifts sideways- and downward-facing surfaces (coats, faces, eave undersides) toward warm grey, while roofs and cobbles keep the cool sky fill. The moon rim on dark materials goes 0.06 → 0.09, so figures stand out against the cobbles. **Facades:** a new "town wash" term in the glow loop (`NIGHT.town`) puts warm light on the town ring's walls (radius past 36 m, full past 46 m) that face the square. It falls off over 9 m of height, so doors and timbering read while roofs and upper storeys stay blue. Fog 0.0135 → 0.0115, so facades 50–60 m out keep their windows (transmittance 0.58 → 0.67). | `before_after_market.jpg`, `market.jpg` |
| **2b. Close-ups, pass 3 (this pass): white bulb cores, shelf shadows, the wheel's hub** | **Bulb cores:** `bulb_warm` (1, .62, .30) × 4.8 → (1, .55, .24) × **3.9**, bloom 0.32 → 0.34. AgX turns any channel past about 4 white, so up close each bulb was a white disc with an orange rim. Now only the red channel is far over the bloom threshold: a warm cream core with an amber halo. Bench: bulbs median 13 px (Cycles 14, pass 1 15), band under the bulbs luma 151 (pass 1 161, Cycles 111). **Shelf shadows:** the static interior cube shadows' kernel 5 → **8** texels with 16 taps (was 12): the shelf boards' shadows on the back wall had a hard 2–3 px edge; a stall lamp is a 10 cm bulb a metre away. The maps are drawn once, so it costs 4 taps per shaded fragment. **Ferris hub:** the home view showed a white starburst at the hub. The wash light (`light_2`, 3.2 m in front of the hub) gave the steel round the hub 13× the rim's light. It now hangs 3 m further out (`warm.landmark.washOut`), 60 → 70, reach 16 → 18 m: hub 4× the rim, rim unchanged. | `market.jpg`, `before_after_market.jpg`, `bulbs_closeup.jpg`, `after.jpg` |
| **3. Codex fix 3: lite lights go to the entered place** | `focusPlace(id)`. The module calls it by itself once the camera settles at a place's `cam_view` looking at `cam_target`, and an engine call overrides that. The entered place's `light_` spots with no real light **borrow** unshadowed lights from other models, up to 2 and never more than 2 per model. Deco stalls give theirs first, then landmarks and the tree, then section stalls, farthest first. Lights are moved, not created, so the number of lights stays the same, no material recompiles and nothing pops: a moved light fades in over about 0.3 s. Leaving the place puts every light back. On lite, this is how the bandstand, the wheel and the carousel get a real light when entered, and how an entered section stall gets its front fill. **The Bücherstand's third light** (the counter prop's `light_lamp`) is now a small glow: any model gets at most `warm.perModel` = 2 real lights. | `market_lite_band.jpg`, `market_lite_glueh.jpg`, and the focus lines under "Checks" below |
| **4. Round-1 judges' points** | See the next table. | |

## Round-1 judges' points

| Point (judge) | Now |
|---|---|
| Lite light leak through the walls onto the gable and eave (Opus) | Every unshadowed interior light is clipped to its stall's interior box: side, back and lower front walls, plus the roof as a tent. The lite gable, barge boards and eave are dark, and the plank gaps no longer show slits. | `lite_gable.jpg`, `after_lite.jpg` |
| Lite shelf wall 0.67 against Cycles 0.39 (Opus, Fable) | **0.49** now (clip, plus the unshadowed interior at 50 %). The lite back wall is 0.42 (Cycles 0.53). |
| Report did not match the files (Opus, Fable) | This NOTES file and the structured report describe what is on disk. |
| Review images over 1280 px (Fable) | `compose.py` clamps every image to 1280 px wide. All images in this folder are 1280 px or narrower. |
| Tighten the bulb bloom (Opus, Fable) | Bloom strength 0.40 → 0.32, second mip 0.3 → 0.2. Bulbs are 12–19 px wide, median 15 (Cycles median 14, round 1 median 18). The lambrequin under the bulb row measures **0.26** (Cycles 0.26; round 1 0.35). |
| Back wall and sign too bright (Fable) | Section interior 40 → 34, shadowed interior glow 9 → 7. Back wall **0.54** (Cycles 0.53; round 1 0.58). The bench sign board is now *meant* to be brighter than Cycles, because of the sign lamp (next table). |
| Warm eave and ground beside the stall (Fable) | Roof glow (`glow.eave`) and ground spill (`glow.spill`). Roof strip **0.23** (Cycles 0.24; round 1 0.06). The ground beside the stall is warm grey, no longer blue. |
| Real-GPU frame times (Opus, Fable) | **Still not measured**, because this machine has no GPU. The commands are below. Round 2 adds 4 glow slots (28 on full, 16 on lite), 3 draw calls for the sign fixtures and one term in the glow loop. It adds no three.js lights and no shadow maps. |
| `--palette false`, `SNOW_FOG_MAX` (market owner) | These are still requests to the market owner; I left BUILD.md and main.js alone. `optimize.mjs` keeps material names, so `bulb_warm` is found in the new web glbs. |

## Colour against the Cycles reference (test bench, 1280×720, same camera)

From `site/src/lighting/measure.py` (sRGB lightness), re-measured after this pass's dimmer bulbs. The lambrequin dropped from .26 to .21 because the bulbs that light it are dimmer; it now sits a little under Cycles instead of on it, which is the trade for warm bulb cores instead of white ones.

| Patch | Cycles | Round 1 (as judged) | Round 2 full | Round 2 lite |
|---|---|---|---|---|
| Counter top | .33 | .40 | .29 | .31 |
| Back wall | .53 | .58 | .54 | .42 |
| Shelf wall | .39 | .39 | .34 | .49 (round 1 .67) |
| Lambrequin | .26 | .35 | .21 | .18 |
| Roof strip over the bulbs | .24 | .06 | .22 | .22 |
| Copper pot | .39 | .51 | .47 | .39 |
| Moon-side wall | .01 | .03 | .03 | .03 |
| Sign board | .14 | .19 | **.37** (sign lamp) | .37 |

The wood hue is within 1–3° of Cycles everywhere. The one deliberate difference is the sign board. In Cycles the board is dark and the pale letters carry the word. In the browser the task is for the Glühwein and Bratwurst boards to read from the square, so the lamp lights the board as a real stall would (`sign_lamp_bench.jpg`: Cycles, no lamp, lamp).

## Checks

- Fix pass, full market (one page load, `-full` in `shoot-market.mjs`): 12 real-time lights, no warnings, `hub fade on 1 bulb meshes of place_riesenrad`. Home view, then the two sign approaches, then both stalls entered. Lite (`-lite`): 4 lights throughout; `focus glueh (1 lights moved)`, `focus band (2 lights moved)`, both from explicit `focusPlace` calls, as the engine will make them.
- Real market, full home view: 12 real-time lights, `lighting: "lighting"`, no warnings. `placeLights` logs `placed 10 lights (4 shadowed, 0 clipped to their stall), 29 pools, glows {"interior":4,"eave":4,"spill":4,"sign":4}`. The deco stalls and rides that load later add 2 more lights and 9 sign glows.
- Lite, entered places (`shoot-market.mjs`, which opens the place and calls `focusPlace` as the engine would from `openPlace`): Glühwein entered → `focus glueh (1 lights moved)`, the Bücherstand's unshadowed light becomes the Glühwein front fill; bandstand entered → `focus band (2 lights moved)`, the Bücherstand's and the Bratwurst stand's lights go to the bandstand's two stage lights. The real-time light count stays at 4 throughout, with no warnings.
- The engine's place ids are now short (`glueh`, `band`, ...), not the layout ids (`gluehwein`, `bandstand`). `focusPlace` matches either, through the model's `userData.place`.
- On software GL the market draws a frame every few seconds, so the camera-based detection (two settled checks 10 frames apart) does not fire before a capture. That is why the shoot script calls `focusPlace` itself. On a real GPU it fires about a third of a second after the camera settles.

## Performance

**Real GPU: not measured** (no GPU here: no `/dev/dri`, Chromium uses SwiftShader, and this session cannot reach the laptop). Since the fix pass the adaptive quality's first step (MSAA 4× → 2×) triggers at a median of 16.7 ms, so the judges' rule applies itself on any GPU. On the M3 laptop:

```sh
cd site
node src/lighting/perf.mjs --gpu --headed --fixed --dpr 1.75   # the full profile as is
node src/lighting/perf.mjs --gpu --headed --dpr 1.75           # where the adaptive step-down settles
```

If the fixed run's p50 is over 16.7 ms, set `PROFILES.full.msaa = 2` in `settings.js`. If it is still over 18 ms, set `moonShadowEvery: 4`, then lower `glows` from 28 to 16.

## Images in this folder

| Image | What it shows |
|---|---|
| `market_signs.jpg`, `market_sign_glueh.jpg`, `market_sign_wurst.jpg` | **The Glühwein and Bratwurst stands in the full market** from a visitor's approach (6.5 and 7.5 m in front of each sign, eye height 1.7 m, `@front=`), with their sign lamps. Both re-shot in the fix pass from the shipped code. |
| `market_hub.jpg` | Fix pass: the Ferris hub in the home view at 3×, pass 3 (starburst) against this pass (hub fade and the farther wash). |
| `wheel_hub_bench.jpg` | Fix pass: the Ferris wheel alone on the bench with its own lights (`?glb=/models/ferris.glb&tune=1&own=landmark`), pass-3 settings against this pass. |
| `ao_stall.jpg`, `ao_bulb_row.jpg` | Fix pass: the shipped Glühwein stall on the bench (Cycles camera), the baked AO used by the hemisphere only against AO also in the glows and interior lamps, and its bulb row. |
| `market.jpg`, `before_after_market.jpg` | The full market's home view (fix pass); round 1 against round 2 (smaller moon, softer pools, warmer facades and crowd, no hub starburst). |
| `home_signs.jpg` | The home view's left stalls at 2×, round 1 against round 2. The Bratwurst board over the roof now reads. The Glühwein board is behind the crowd's speech bubble in this frame, which comes from the crowd, not the lighting. |
| `market_glueh.jpg`, `market_wurst.jpg`, `before_after_glueh.jpg`, `before_after_wurst.jpg` | The two stalls entered, full, round 1 against round 2 (the Glühwein board no longer washed out; less bulb glare). |
| `market_lite_glueh.jpg`, `market_lite_band.jpg`, `before_after_lite_glueh.jpg`, `before_after_lite_band.jpg` | Lite, entered: the Glühwein stall and the bandstand, with the lights they borrow (round 1: the bandstand had no real light on lite). |
| `bulbs_closeup.jpg` | The bench's bulb row and shelves: Cycles, round 2 pass 1 (bulbs × 4.8, from `raw_pass1/`), pass 3 code (× 3.9 in deeper amber, softer shelf shadows), re-shot in pass 4. |
| `side_by_side.jpg`, `side_by_side_pair.jpg` | Test bench: the Cycles reference, round 1, round 2 full and round 2 lite. |
| `sign_lamp_bench.jpg` | The bench's Glühwein board: Cycles, no lamp, lamp. |
| `lite_gable.jpg` | The lite gable and eave: no light through the walls. |
| `before.jpg`, `after.jpg`, `after_lite.jpg` | The test bench: round 1 (before), round 2 full, round 2 lite. |
| `snow_toggle.jpg` | Snow off and on (`setSnow`) on the bench. |

## Budgets

| Item | Size |
|---|---|
| Models and textures | None shipped. The sky, stars, snow, environment, probes and sign fixtures are generated in code. |
| Code | About 175 KB of unminified JS in 15 files: 9 modules (`index`, `lights`, `shading`, `settings`, `sky`, `env`, `snow`, `fog`, `grade`) plus tools and configs (`shoot*.mjs`, `perf.mjs`, `diag-market.mjs`, two vite configs). `compose.py` and `measure.py` make and measure the review images. |
| Sign fixtures | 112 triangles per lamp, all lamps in one mesh, 3 draw calls per `placeLights` call |
| Real-time warm lights | 14 on full, 4 on lite, minus the engine's reserved lights (12 in the market report). The entered place borrows up to 2 and the total stays the same. |
| Local glows | 28 (full) / 16 (lite) slots in one shared uniform |
| Shadows | Moon 1536², every 3rd frame, plus 4 × 512² static interior cube maps (full). None on lite. |
| Snow | 28.5k points on full, 8k on lite |
| Hub fade (fix pass) | One Float32 attribute on the wheel's bulb mesh (22,560 vertices, 90 KB of GPU memory), one cloned material, no extra draw calls |

## What I would improve next

- Measure real-GPU frame times on Mac's laptop (above) and write the p50 into README.
- The bench's left bulbs still merge into one bright run of about 120 px. That glb has no AO map and hangs its bulbs in front of the pale back wall. The shipped stalls have AO, which the lighting now uses, and their bulbs stand apart. Next step: bake the same AO into the bench glb (the market owner's `review/reference/`), or switch the bench to `stall_gluehwein.glb` once a Cycles reference of that stall from the bench camera exists.
- Snow does not settle on the ground or roofs yet.
- The engine should call `lighting.raw.focusPlace(id)` from `openPlace` and `focusPlace(null)` on close and reset (the BUILD.md line is in the fix-pass table above). The camera-based detection then stops for good, and the focus is set before the flight starts rather than a third of a second after it ends.

## Contract

Nothing here breaks BUILD.md. Requests to the market owner:

1. **New (fix pass):** add to BUILD.md, for the engineer: *`openPlace(id)` calls `lighting.raw.focusPlace(id)` before the camera flight starts, and closing the panel or `resetView()` calls `lighting.raw.focusPlace(null)`.*
2. Still open: add `--palette false` wherever plain `gltf-transform optimize` is still used, and drop main.js's redundant `SNOW_FOG_MAX`.
