# Round 1: lighting and atmosphere (lighting designer), pass 3

`site/src/lighting/` is the night. `index.js` exports `createLighting({ scene, renderer, camera, lite })`, which returns `{ composer, update(dt, t), setSnow(on), dispose() }`, plus the helpers the engine uses (`placeLights`, `tune`) and a few for tuning (`captureEnvironment`, `refreshEnvironment`, `captureProbes`, `trimMoonCasters`, `fitShadow`, `stats`). The settings and the reasoning behind them are in `site/src/lighting/README.md`.

The market report says `lighting: "lighting"`, with 12 real-time lights on full (the four section interiors, their four front fills, the bandstand, the tree, the wheel and the carousel) and 4 on lite (the four section interiors), and no warnings.

## What changed in pass 3

Each row is one of the panel's requests, in their order. Duplicated requests are answered once.

| Request | What I did | Where to see it |
|---|---|---|
| **Real-GPU frame times** | **Still not measured: this container has no GPU** (no `/dev/dri`). Mac needs to run the two commands under "Performance" and paste the lines here. Because I cannot check p50 ≤ 16.7 ms, I made the default cheaper now rather than waiting: the moon's shadow is drawn every **3rd** frame (was 2nd) into a **1536²** map (was 2048², still 5.5 cm a texel over the market), and meshes of the placed models smaller than 0.15 m stop casting the moon's shadow once the interior shadows are drawn (`trimMoonCasters`, frame 5). MSAA stays 4× on full: M-series GPUs resolve MSAA on-tile, and the adaptive step-down still drops it to 2× first if needed. If Mac's fixed run shows p50 > 16.7 ms, set `PROFILES.full.msaa = 2` (one line). | "Performance" below |
| **No periodic environment refresh** | The 30 s refresh is gone (`env.refresh` and `envRefresh` removed). The global map is captured once on frame 3, and re-captured one face per frame only 0.5 s after the snow blend has settled following a toggle, or when the engine calls the new `refreshEnvironment()` after changing the lights. | `index.js` → `update`, `setSnow` |
| **Stall interiors warm from the home view** | Two causes, both fixed. (1) The light budget gave each model its *nearest* light first, which was the front fill, so three of the four section stalls had no interior light at all (only bratwurst did). A model's first light is now its interior, and on full every section stall gets its interior and its front fill before any landmark. (2) Every section and deco stall now also gets an **interior glow** (`shading.js`, `glow.interior`): a one-sided point glow at its `light_` empty, 16 where the stall has no real light, 9 or 6 as bounce where it has one. It is one-sided, so it cannot shine out through the walls, and clipped by height, so it lights no ground halo and no roof. The glow slots went from 16 to 24 (lite 6 → 12), interiors first. The unshadowed interior lights stay at 70 % (lite only now): at 100 % the lite back wall washed out to lightness 0.72 against 0.39, and the glow brings the stall's warmth back. | `market_home.jpg`, `market_home_snow.jpg`, `market_home_lite.jpg`, `market_pass2_vs_pass3.jpg` |
| **Snow fog 0.017** | `NIGHT.snow.fogDensity` is **0.017**, so `main.js`'s `SNOW_FOG_MAX` override changes nothing and the test page and the market agree. To keep the air reading as snowy at the lower density, the snow fog colour is a touch paler (`#273250`, was `#222c4a`). README matches. The engineer can drop `SNOW_FOG_MAX` or keep it; either way nothing changes now. | `market_home_snow.jpg`, `snow_toggle.jpg` |
| **Dashed streaks and the pale strip on the ground** | Found three causes. (1) **The cube-shadow bias was about 0.3 m.** three's point-light shadow bias is in perspective depth; -0.002 with a 5 cm near plane is about 0.3 m of distance at 2.7 m. So the ground within 0.3 m behind the wall base was treated as unshadowed. That was the pale strip, not the bounce glow. Now near 0.15 m and bias -0.0003 (1.4 cm at 2.7 m). (2) **The reference stall's wall planks have real hairline gaps**, and a 512² cube map lets some of them through as sharp dashes. Each stall with a shadowed interior light now gets a **shadow-only shell** (`shadowBlocker`): a floor 5 cm over the base and planes 12 mm outside the side, back and lower front walls, placed by casting rays at the stall from outside. It draws nothing on screen and nothing into the moon's shadow. (3) The interior shadow kernel is wider (radius 5 texels, taken with 12 taps instead of 5), as a lamp has a size. I confirmed each cause with single-light close-ups (`?lights=0&cam=…`). The glow now has a floor clip as well. | `ground_artifacts.jpg`, `side_by_side_full.jpg` |
| **Dots on the lite counter** | This was not a normal map. The counter top's boards have hairline gaps, and with no MSAA they aliased into a regular row of dots, one per pixel row. Full had 4× MSAA, so it did not show there. Lite now renders with **2× MSAA**, and the dots are gone. | `lite_counter.jpg`, `after_lite.jpg` |
| **Rim off the walls** | `rim.strength` is 0.06 (was 0.09), and the rim now shows **only on dark materials**: it fades out between albedo 0.07 and 0.16. The crowd's coats (0.01–0.07) and iron posts keep their outline; wood (0.2 and up) gets none. The moon-side wall measures lightness **0.03** (Cycles 0.01; pass 2 0.13). | `left_wall.jpg`, `market_home.jpg` |
| **Minor** | The dead `else if (frame === captureAt)` branch is gone, with `captureAt`. `dispose()` restores `renderer.toneMapping`, `toneMappingExposure`, `outputColorSpace`, `shadowMap.enabled` and `.type`, and the scene's fog, background and environment. It also gives back `castShadow` to the trimmed casters. | `index.js` |
| **Section stalls above landmarks** | `PRIORITY.landmark` is 1, the same as the tree and below section stalls (0). The lite market's four lights are the four section interiors; the market report confirms it. | `market_home_lite.jpg` |
| **Fascia and lambrequin** | `glow.bulbs` went from 0.6 to **0.25** and its reach from 1.1 m to **0.9 m**. The bloom mip weights are tighter (`[1, .3, .09, .03, .01]`, lite `[1, .15, .03, .006, 0]`), so the bulbs read more as crisp dots. The lambrequin patch measures lightness **0.35** (Cycles 0.26; pass 2 0.44). Part of what is left is the bulbs' own bloom over the patch, which sits right under the bulb row. | `bulbs_garland.jpg` |
| **BUILD.md `--palette false`** | This is still a request to the market owner; BUILD.md is not mine to edit. The standard `gltf-transform optimize` step in BUILD.md should add `--palette false`. By default it merges `bulb_warm` into `PaletteMaterial00x` and the copper pot into the wires' material. The probes and the glows cope with palettised files, but `tuneEmissives` and the bulb-string glows find bulbs by the `bulb_` names. | – |

## Colour against the Cycles reference

`site/src/lighting/measure.py` averages patches of the 1280×720 frames (same camera). The values are sRGB means, then hue in degrees, saturation and lightness.

| Patch | Cycles | Pass 2 (full) | Pass 3 (full) | Pass 3 (lite) |
|---|---|---|---|---|
| Counter top | (127, 80, 38) h28 s.54 l.33 | (147, 99, 58) h28 s.43 l.40 | (148, 100, 59) h28 s.43 l.40 | (155, 107, 67) h28 s.40 l.43 |
| Counter front | (62, 31, 7) h26 s.79 l.14 | (68, 35, 11) h25 s.72 l.15 | (67, 34, 10) h26 s.74 l.15 | (67, 35, 12) h25 s.70 l.15 |
| Sign board | (66, 34, 5) h29 s.85 l.14 | (84, 45, 15) h26 s.70 l.19 | (84, 45, 14) h26 s.71 l.19 | (84, 45, 14) h26 s.71 l.19 |
| Front planks | (59, 30, 4) h28 s.86 l.12 | (65, 32, 9) h25 s.75 l.15 | (64, 31, 8) h25 s.79 l.14 | (65, 32, 9) h25 s.75 l.14 |
| Back wall | (193, 128, 79) h26 s.48 l.53 | (197, 143, 99) h27 s.46 l.58 | (196, 142, 96) h27 s.46 l.57 | (188, 132, 87) h27 s.43 l.54 |
| Shelf wall | (162, 93, 39) h27 s.61 l.39 | (130, 76, 36) h26 s.57 l.33 | (149, 92, 47) h26 s.52 l.39 | (217, 167, 124) h28 s.55 l.67 |
| Lambrequin | (110, 67, 24) h30 s.64 l.26 | (153, 110, 73) h28 s.35 **l.44** | (126, 88, 55) h28 s.39 **l.35** | (128, 93, 61) h29 s.36 l.37 |
| Copper pot | (157, 89, 43) h24 s.57 l.39 | (184, 119, 83) h21 s.42 l.52 | (182, 115, 79) h21 s.41 l.51 | (175, 110, 76) h21 s.40 l.49 |
| Moon-side wall | (4, 2, 2) l.01 | (25, 25, 41) h238 **l.13** (blue rim) | (10, 5, 5) h356 **l.03** | (11, 5, 5) l.03 |
| Ground right of the stall | (141, 119, 102) h26 s.16 l.48 | (122, 110, 103) h21 s.08 l.44 | (122, 110, 103) h21 s.08 l.44 | (119, 107, 101) h20 s.08 l.43 |

The wood hue still matches within 1–3°. The shelf wall on full now matches (0.39): with the shadowed interior light at the right place, the shelf shades the wall below it as in Cycles. Lite has no shadows, so the shelf cannot shade the wall and that patch stays bright there (0.67, the same as pass 2's 0.65). The sky is brighter than the reference's near-black, by design: the stars, the moon's halo and the clouds are part of the brief.

## Performance

**Real GPU: not measured.** There is no GPU in this container. Please run these on the M3 laptop and paste both output lines here:

```sh
cd site
node src/lighting/perf.mjs --gpu --headed --fixed --dpr 1.75   # the full profile as is
node src/lighting/perf.mjs --gpu --headed --dpr 1.75           # where the adaptive step-down settles
```

What to do with the numbers:

- If the fixed run's p50 is at or under 16.7 ms, nothing to do.
- If it is over 16.7 ms, set `PROFILES.full.msaa = 2` in `settings.js`. That is the step the adaptive run takes first, now made the default.
- If it is still over 18 ms at level 0 after that, set `moonShadowEvery: 4`. The cheaper moon shadow (every 3rd frame, 1536²) is already the default.

`main.js` caps the full market's pixel ratio at 1.5, so the composer never renders above 1.5× even with `--dpr 1.75`.

Draw calls are the one number here that carries over to a real GPU. Counted per frame on the full market (software GL, `diag-market.mjs`):

| Frame | 1 | 2 | 3 | 4 | 5 | 6 | Average |
|---|---|---|---|---|---|---|---|
| Pass 3, full, draw calls | 2177 | 2177 | 2876 | 2179 | 2179 | 2878 | **~2410** |
| Pass 2, full (from its notes) | 2290 | 2290 + ~700 | … | | | | ~2640, plus ~950 on each of 6 frames every 30 s |

The moon's shadow pass is about 700 calls and now lands on every 3rd frame. The trim of small props took about 20 casters out of it (697 casters remain; most are figures and larger parts), so the frame-rate gain comes mostly from every 3rd frame and the smaller map. The periodic refresh hitch is gone. Main pass: 1124 meshes, 24 of 24 glow slots in use (13 stall interiors, 11 bulb strings nearest the camera).

The module adds: the moon's shadow pass on every 3rd frame (the scene's casters, minus the trimmed small props), bloom (12 calls), the grade pass, the sky and three snow layers (1 call each), and the four shadow-only shells (1 call each in the main pass, drawing nothing). The interior shadows, the probes and the environment capture are drawn at load, and the capture again only after a snow toggle.

## Images in this folder

| Image | What it shows |
|---|---|
| `side_by_side.jpg`, `side_by_side_full.jpg` | The Cycles reference beside pass 3 (half size, and stacked at full size). |
| `pass2_vs_pass3.jpg` | The reference, pass 2 full, pass 3 full and pass 3 lite. |
| `ground_artifacts.jpg` | The ground left of the stall: Cycles, pass 2 (dashed streaks, pale strip at the wall base), pass 3. |
| `lite_counter.jpg` | The lite counter top: pass 2 (rows of dots), pass 3 (2× MSAA). |
| `left_wall.jpg` | The moon-side wall: Cycles, pass 2 (blue rim), pass 3. |
| `bulbs_garland.jpg` | The bulb row, fascia and garland: Cycles, pass 2, pass 3. |
| `market_home.jpg`, `market_home_snow.jpg`, `market_home_lite.jpg` | The real market home view with this module: full, snow, lite. |
| `market_pass2_vs_pass3.jpg` | The home view, pass 2 against pass 3, with and without snow. |
| `before_after.jpg`, `before.jpg`, `after.jpg` | Before is the engine's stand-in lighting (`lighting-fallback.js`); after is this module. |
| `after_lite.jpg` | The lite profile: 4 lights, no shadows, 2× MSAA. |
| `after_capture.jpg` | Full with `?capture=1`. |
| `bloom_full_vs_lite.jpg`, `sky_moon_stars.jpg` | The moon's halo on full and lite; the sky with the moon, halo, stars and clouds. |
| `wide.jpg`, `snow_on.jpg`, `snow_toggle.jpg` | Fog and ground mist; snow off and on, lite snow, and a close view showing the depth layers. |
| `pot_closeup.jpg`, `pass1_vs_pass2.jpg` | Kept from pass 2 for the history (pass 1 against pass 2). |

## Budgets

| Item | Size |
|---|---|
| Models and textures | None shipped. The sky, stars, snow, environment and probes are generated. |
| Code | About 90 KB of unminified JS in 9 module files, plus the test and tool scripts |
| Sky dome | 4k triangles |
| Snow | 28.5k points on full, 8k on lite |
| Post | 1 half-float MSAA target (4× full, 2× lite), 5 bloom mips, 1 grade pass |
| Shadows | Moon 1536², redrawn every 3rd frame, plus 4 × 512² interior cube maps drawn once and 4 shadow-only shells (full); none on lite |
| Real-time warm lights | 14 on full, 4 on lite, minus the engine's reserved lights (12 in the market report) |
| Reflections | Global 256² PMREM, captured once (and again only after a snow toggle); 6 probes at 128² (full), 2 at 64² (lite), captured once |
| Local glows | 24 (full) / 12 (lite) slots in one shared uniform of 75 / 39 vec4 |

## Open issues and requests

- **Real-GPU frame times** are still to be measured on Mac's laptop (see Performance). Everything else in the panel's list is done.
- **BUILD.md: `--palette false`** (market owner). See the table above.
- **The interior shadow kernel is wide**, so the mugs' contact shadows on the counter are softer than in pass 2. That is the price of the smooth gap-free walls; `warm.shadowMap.radius` 5 → 3 sharpens them again.
- **Glows ignore walls within their reach.** A bulb-string glow (0.9 m) or an interior glow (2.6 m, one-sided) has no shadow. One-sided and clipped by height, neither lights a wall's outside or the ground, but a neighbouring model within 2.6 m that faces into a stall would catch a little of its light.
- **The shadow-only shell is found by ray casts.** It needs a stall whose origin is its footprint at ground level with the front at +Z (the contract), and three closed sides. If a side has no wall, the shell is skipped for that stall.
- **Snow does not settle** on the ground or roofs yet.
- **The fog, shading and shadow chunk patches are global** to three's `ShaderChunk`. Custom `ShaderMaterial`s with `fog: true` must define `mvPosition`, as stock three already requires. `dispose()` restores the chunks.
