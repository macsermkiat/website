# Lighting: the night

`site/src/lighting/` is the lighting designer's module. It supplies the sky, moonlight, fill light, fog,
reflections, tone mapping, bloom, the warm lights at `light_` empties, and the snow.

```js
import { createLighting } from './lighting/index.js';

const lighting = createLighting({ scene, renderer, camera, lite });
lighting.placeLights(market.lightSpots, { focus, reserved }); // light_ empties -> warm lights
// every frame
lighting.update(dt, t);            // t = scene time (freeze it for reduced motion and the snow stops)
lighting.composer.render(dt);
// the snow button
lighting.setSnow(true);
// on teardown
lighting.dispose();
```

`createLighting` returns `{ composer, update(dt, t), setSnow(on), dispose() }`, which is the agreed shape.
It also returns these optional helpers:

| Member | What it does |
|---|---|
| `placeLights(spots, { focus, reserved, shadowed, budget })` | Turns `light_` empties into warm lights within the profile's budget, and gives every section and deco stall an interior glow. It takes the engine's spot shape `[{ obj, kind, id }]` and returns `{ lights, pools, cap, interiors, glows, blockers, refreshShadows(), dispose() }`, a superset of `engine/lights.js`. |
| `tune(root)` | Applies this module's emissive levels and bulb-string glows to a model that loads late. |
| `captureEnvironment(position)` | Re-captures the global reflection map from the real scene now (six faces in one frame). |
| `refreshEnvironment(delay)` | Re-captures it one cube face per frame, starting `delay` seconds from now (full only). Call it after changing the lights. The module calls it itself once the snow has settled after a toggle. There is no periodic refresh. |
| `trimMoonCasters(root)` | Stops meshes of a placed model smaller than `minMoonCaster` from casting the moon's shadow (run once on frame 5 for the whole scene). |
| `captureProbes(count)` | Captures local reflection probes for the nearest stalls with copper, glass or glaze. |
| `fitShadow(center, radius)` | Moves the moon's shadow box. |
| `stats()` | Wall-clock frame times (p50, p95, p99, fps) and the adaptive quality level. |
| `settings`, `profile`, `quality`, `sky`, `hemi`, `moonLight`, `bloom`, `grade`, `shading`, `probes` | The parts, exposed for tuning from the console. `globalThis.__lighting` points at the same object. |

`createLighting` also accepts `options`: `{ shadowCenter, shadowRadius, envCapture, envCapturePosition, probes, adaptive, profile, adoptEngineLights }`.

`dispose()` removes everything the module added, restores three's shader chunks, and puts back the renderer's tone mapping, exposure, output colour space and shadow-map settings, and the scene's fog, background and environment.

### How the engine uses it

`engine/lighting.js` loads this module when it exists, and `main.js` then:

- calls `lighting.raw.placeLights(market.lightSpots, { focus, reserved })` right after `createLighting`, so every `light_` empty is placed by this module (colour, interior or front fill, reach, static shadows for the section stall interiors, interior glows);
- skips `engine/snowfall.js` when this module is active (it checks for `snowAmount`), so there is one snowfall.

`createLighting` itself finds every `bulb_warm`, `bulb_cold` and `window_warm` material and sets its emissive level, including `userData.baseEmissive`, which the engine's flicker multiplies, and turns each string of bulbs on a stall into a local glow.

Two older paths are **legacy** and off: `adoptEngineLights` (re-tuning lights the engine had already placed; pass `options.adoptEngineLights = true` to use it) and the masking of `engine_snowfall` (removed; main.js no longer creates it).

All numbers are in `settings.js` (`NIGHT` for the look, `PROFILES` for full and lite).

## Tone mapping: AgX, with part of Blender's "Punchy" look

The module uses **AgX**, not ACES, for three reasons:

1. **It matches the reference.** Every Cycles preview in this project is rendered with Blender's AgX view transform and the *Punchy* look. three.js's AgX is the same curve, ported from Blender via Filament. The browser and the visual targets therefore share a tone curve, and tuning becomes a matter of lights and exposure, not of fighting a different film response.
2. **It handles saturated lights better.** The scene is dark and blue with small, very bright, saturated warm sources: bulbs, lanterns and lit windows. ACES pushes bright oranges toward yellow and pink and holds too much saturation, so bulbs turn into orange blobs. AgX desaturates toward white as a light gets brighter, the way a real incandescent bulb looks in a photograph: a white-hot core with a warm fringe.
3. **Its shadows hold detail.** ACES crushes the deep blues that carry most of this frame. AgX keeps detail in the dark blues, so moonlit wood stays readable.

three's built-in `AgXToneMapping` has no look. `grade.js` replaces three's `OutputPass` with one pass that does the following:

- exposure;
- a vignette of 0.28;
- AgX, with the look applied between the sigmoid and the outset, where Blender applies it. The look is Punchy (power 1.35, saturation 1.4), blended in at `punch = 0.35`. At 0.45 the dark wood of the stall fronts went red (hue 13–20° against the reference's 26–29°);
- sRGB encoding;
- about 1 to 3 code values of animated triangular grain, which also dithers the dark sky gradient against 8-bit banding.

**Colour management:**

- `ColorManagement` is on. Hex colours in `settings.js` are sRGB, which three converts to linear. Light colours given as `[r, g, b]` arrays are linear, like Blender's light colour.
- The scene renders linear HDR into a half-float target (4× MSAA on the full market), then goes through bloom, then the grade.
- `renderer.toneMapping` is set to AgX as well, so anything drawn straight to the screen matches.
- `renderer.toneMappingExposure` is read by the grade every frame, so there is one exposure control.

**Units:** intensities are three.js physical units. A point light's intensity is roughly Blender watts ÷ 4π, and a directional light's is roughly Blender sun strength.

## Key settings (full market)

| Part | Setting | Why |
|---|---|---|
| Sky | Zenith `#01030d`, mid `#020719`, horizon `#081430`, a faint warm horizon glow (`#221a12` × 0.35) | Deep blue with a gradient and a hint of town glow. |
| Stars | Three hashed star layers: 60, 150 and 320 cells per radian, with 7 %, 2.5 % and 1.2 % filled. Magnitudes follow a power law, colour temperature varies, stars twinkle, and they fade near the horizon and the moon. | Each star is about 1.5 px wide at any resolution because its size uses `fwidth`. |
| Moon | Disc of 0.03 rad (about 2.5× the real size, for the miniature look), limb darkening, noise maria, HDR 4.2 so it blooms. Two-lobe halo in `#5d6fa8` × 0.55 and a faint 22° ice ring. It sits low over the town roofs in the home view. | A soft-haloed moon that frames the market. |
| Clouds | Thin fbm clouds lit silver near the moon and warm from the town below. Off on lite. | Depth in the sky. |
| Moonlight | Directional `#9ab0f0` at 0.36, from high left and slightly toward the viewer (not the disc's direction: a moon that low would put every stall front in silhouette). | Cool, grazing light on wood and cobbles. |
| Moon shadows | 1536² map (5.5 cm a texel over the market's ±42 m box), PCF `radius` 4, bias -0.0004, normal bias 0.025, intensity 0.85. Redrawn every 3rd frame (`moonShadowEvery`). Meshes of placed models smaller than 0.15 m (`minMoonCaster`) stop casting it once the interior shadows are drawn. | Soft, readable shadows. The town and stalls are still, and walking people's shadows read the same at 20 Hz. On average the shadow pass now costs about a third of a pass a frame, and the trim takes the small props out of it. |
| Hemisphere fill | Sky `#4a5c90`, ground `#14161c`, 0.38 | A paler, less saturated blue ambient than pass 1, so snow reads grey-blue, not navy. |
| Moon rim | `#9fb4ff`, radiance 0.06 at the edge, Fresnel power 1.6, on steep faces (× (1 − n.y²)) facing the moon disc, added as radiance rather than multiplied by albedo, and only on dark materials: it fades out between albedo 0.07 and 0.16 (`shading.js`) | The crowd's coats have albedo 0.01–0.07, so no amount of light on them shows. A grazing sheen, the way wool catches light, outlines the figures and iron posts in front of the stalls. Wood (albedo 0.2 and up) gets none, so a stall's moon-side wall stays near-black as in Cycles (lightness 0.03 against 0.01; pass 2 had 0.13 with the rim on everything). |
| Fog | `FogExp2` `#0a1630`, density 0.0135, plus a ground mist: density × (1 + 1.1·e^(−h/3.2 m)). Patches three's fog chunks. | The town ring sinks into blue haze while roofs and the wheel stay crisp. |
| Global environment | PMREM 256. The synthetic night at start; on full, the real market captured once on frame 3 from `[0, 1.6, 2]` (`environmentIntensity` 0.45). **No periodic refresh.** It is re-captured, one cube face per frame into the same texture, only 0.5 s after the snow blend has settled following a toggle, or when the engine calls `refreshEnvironment()`. | Wet cobbles and glass reflect the actual bulbs. The market is static apart from the rides and the crowd, which are too small in a 256² reflection to matter, so a periodic refresh (pass 2: six frames of about 950 extra draw calls every 30 s) only caused a hitch. |
| Local probes | On frame 3, the 6 nearest stalls (lite: 2) that hold copper, glass or glaze get their own 128² probe (lite 64²), captured from the middle of those props with the props hidden, as their material's `envMap` at intensity 1.0. | The copper pot reflects the lit back wall, the bulbs and the dark market in front, as in Cycles, instead of a dark synthetic sky. |
| Bloom | `UnrealBloomPass`, threshold 1.6 (knee 1.2), strength 0.40, mip weights `[1, .3, .09, .03, .01]`, radius 0. Input clamped to **5** by the brightest channel (hue kept). | Only emissives bloom (bulbs at 6, windows at 1.5, the moon at 4.2); lit wood (< 1.5) does not. The clamp means a specular glint on copper enters the bloom no brighter than a bulb, so glints cannot become glare stars. The weights keep a crisp core with a short tail. |
| Bloom, half resolution | Lite, and full after the third adaptive step: weights `[1, .15, .03, .006, 0]`, strength 0.40 | At half resolution every mip is twice as wide on screen; shifting weight to the tight mips keeps the moon halo and lamp glows the same size as on full. |
| Light size | For direct light only, roughness is floored at 0.32 and clear-coat roughness at 0.30 (`shading.js`) | three's lights are points, so a mirror clear coat (the reference mugs and pot have clear-coat roughness 0) reflects them as one blazing pixel. Real lamps have a size. Reflections of the environment stay sharp. |
| Bulbs | `bulb_warm` emissive (1, .62, .30) × 6, `bulb_cold` (.62, .76, 1) × 5, also written to `userData.baseEmissive` | The same brightness across everyone's models. |
| Bulb-string glow | Each short, level string of bulbs on a stall is a line light: 0.25 × bulb colour, 0.9 m reach, half-wrapped diffuse (`shading.js`). Strings longer than 5 m or taller than 1 m (wheel, carousel, tree, festoons) are skipped. | The garland and the lambrequin are lit by their bulbs, as in Cycles, at the cost of a small loop per pixel instead of more three.js lights. At 0.6 the fascia board behind the bulbs measured lightness 0.44 against 0.26 in Cycles. |
| Stall interior glow | Every section and deco stall: a one-sided point glow 0.3 m below its interior `light_` empty, reach 2.6 m, clipped below 0.3 m over the stall's base and above 0.15 m over the empty. Intensity 9 where the stall has a shadowed light, 6 with an unshadowed one, 16 with none. | Every stall front reads warm from the home view, including the stalls the light budget cannot reach. One-sided, so it cannot shine out through the walls; clipped, so it lights no halo on the ground and no roof. |
| Windows | `window_warm` × 1.5 | They read as lamplight, not as light sources. |

### Warm lights at `light_` empties

The light colour is linear (1.0, 0.6, 0.3), the colour of the Cycles previews' lights (`nmlib/render.py`). Pass 1 used 2900 K through a black-body fit, which is (1, 0.42, 0.13) in linear and pushed the wood toward red. The front fill is a little paler, (1.0, 0.7, 0.36), so the snow in front of a stall reads cream, not pink.

| Kind | Interior point | Front fill (spot under the front eave) | Spot | Reach (point / front / spot) |
|---|---|---|---|---|
| Section stall | 40 | 13, cone 1.15 rad, penumbra 0.45 | 34 | 4.2 / 8 / 8 m |
| Deco stall | 18 | 8, cone 1.15 rad | 20 | 3.6 / 6 / 7 m |
| Landmark | 26 | – | 40 (stage lights above 2.8 m point down) | 10 / – / 12 m |
| Lamp (`light_lamp_*`) | 7 | – | – | 10 m |
| Tree (`light_tree_*`) | 16 | – | – | 10 m |

How the helper places them:

- **Front or interior.** A `light_` empty more than 0.9 m in front of its model's origin (model +Z) is the front fill: a wide spot aimed down and 0.6 m out, which lights the counter front, the sign and the cobbles but not the fascia right beside it. Anything else inside the model is the interior light.
- **Spots.** A spot is used when an empty's `userData.type` is `'spot'`, when its name contains `spot`, or for high landmark lights. `userData.intensity`, `userData.distance`, `userData.color` and `userData.aim` override the defaults.
- **Interior shadows.** On the full market, the interior lights of the **4 section stalls** get a 512² cube shadow map, drawn **once** (`shadow.autoUpdate = false`), with shadow intensity **0.95**. Only stall interiors get these slots (pass 2 gave one to the tree). The kernel is wide (radius 5 texels, taken with 12 taps instead of three's 5; a lamp has a size), the near plane is 0.15 m and the bias -0.0003. The bias is in perspective depth: pass 2's -0.002 with a 5 cm near plane was about 0.3 m at the wall base, which let the light out onto a pale strip of ground around the stall.
- **Shadow-only shell.** Each of those stalls also gets a shadow-only shell (`shadowBlocker`): a floor 5 cm over the base and planes 12 mm outside the side walls, the back wall and the lower front wall, found by casting rays at the stall from outside. It draws nothing on screen and nothing into the moon's shadow (its depth material culls every vertex). It closes the hairline gaps between wall planks, which a 512² cube map otherwise lets through as sharp streaks across the ground.
- **The light the walls bounce** comes from the stall's interior glow (below), not from a see-through shadow.
- **Unshadowed interiors** (every stall on lite) are moved 0.3 m down, below the eaves, so they cannot reach the top of the roof, and get a 3 m reach and 70 % intensity, so the leak through the walls stays a small pool at the stall's foot. The interior glow brings the warmth back.
- **Budget.** The full market has 14 real-time lights, the lite market 4, minus the engine's reserved bandstand spots. A model's first light is its interior; its front fill is second. Ranking is by kind (section stalls, then landmarks and the tree, then deco stalls, then lamps), then first lights before second ones, then distance to the focus. So the full market lights the four section interiors and their four front fills before any landmark, and the lite market's four lights are the four section interiors. A light that misses the budget becomes a soft additive warm pool on the ground, and its stall keeps its interior glow.

### Local glows (`shading.js`)

three.js evaluates every light for every pixel, so each extra light costs across the whole frame. The glows are a cheaper, diffuse-only light for the short-reach jobs:

- one shared `Float32Array` uniform (`lightingGlow`, 24 glows on full, 12 on lite; 3 vec4 each), added to every built-in lit material through the `lights_pars_begin` and `lights_fragment_end` chunks, and kept by reference by `UniformsUtils.clone`, so one write updates every material;
- each glow is a segment (a point when both ends match) with a colour × intensity, a reach (with a smooth window to zero), a floor and a ceiling in world y (15 cm fades), and a side: two-sided glows wrap (bulbs), one-sided glows are plain Lambert (interiors);
- every 15 frames the slots are filled: stall interiors first, then the bulb strings nearest the camera;
- the same chunk adds the moon rim, and `shadowmap_pars_fragment` gets the 12-tap point-light shadow.

The chunk patches are global to three's `ShaderChunk` (like the fog) and are restored by `dispose()`.

### Snow

`setSnow(on)` blends over about 2 s **of wall-clock time**, so a slow machine (whose `dt` is clamped to 0.1 s) fades the weather in as quickly as a fast one. It changes the following:

- The fog thickens (density 0.0135 → **0.017**) and lightens (to `#273250`). 0.017 is the engine's cap too (`SNOW_FOG_MAX` in `main.js`), so the test page and the market agree and the engine's override changes nothing. Past it the stall lights and bulbs drown; the paler fog colour keeps the snowy air readable at the lower density.
- The sky goes overcast, and 88 % of the starlight goes behind cloud.
- The moon dims, and moonlight drops to 55 %.
- Hemisphere fill rises × 1.35, because snow cover bounces light.
- Bloom spreads a little, for scattering in the snowy air.

The flakes are GPU points in three layers wrapped around the camera:

| Layer | Box | Flakes (full / lite) | Size | Look |
|---|---|---|---|---|
| Near | 14 m | 3500 / 1200 | 3–5 cm | Out of focus, soft |
| Mid | 36 m | 18000 / 5000 | 3–4.5 cm | Sharp |
| Far | 90 m | 7000 / 1800 | 4–6.5 cm | Clumps that fade into the fog |

Each flake falls at its own speed (0.85 m/s mean ± 40 %) and flutters on its own. All flakes drift with a wind of (0.9, 0.35) m/s with slow gusts, integrated in scene time, so reduced motion freezes the snow. Flakes passing the four nearest stall lights catch their warm light. The CPU does no per-flake work.

## Profiles

| | Full | Lite |
|---|---|---|
| Real-time warm lights | 14 | 4 |
| Shadows | Moon 1536² PCF, every 3rd frame, plus 4 static interior shadows | **None** (shadow map off) |
| MSAA | 4× (2× after the first adaptive step) | 2× (with none, the hairline gaps between counter boards aliased into rows of dots) |
| Bloom resolution | Full (half after the third adaptive step) | Half, with its own tighter weights |
| Global environment | 256, captured from the scene once, again only after a snow toggle | 128, synthetic only |
| Local probes | 6 stalls, 128² | 2 stalls, 64² |
| Local glows | 24 | 12 |
| Sky clouds | On | Off |
| Grain | On | Off (the 1-code-value dither stays) |
| Snow flakes | 28,500 | 8,000 |

### Adaptive quality (full only)

After the first 200 frames, the module measures wall-clock frame times over windows of 150 frames. If the median frame is slower than 18.2 ms (about 55 fps), it steps down one level per window and never steps back up:

1. MSAA 4× → 2× on the composer targets;
2. the composer's pixel ratio capped at 1.5 (the grade pass upsamples to the canvas, which keeps its own ratio, so text and UI stay sharp);
3. bloom at half resolution, with the half-resolution weights;
4. the moon's shadow map redrawn every 4th frame instead of every 3rd.

`main.js` still offers the lite market when frames stay slower than 45 ms. `?lighting-adaptive=0` in the page URL, or `options.adaptive = false`, turns the step-down off. `stats()` reports the level reached.

## Test bench

`test.html` loads `review/reference/gluehwein_stall_web.glb` on a plain ground plane and frames it with the Cycles camera: Blender (-3.4, -5.6, 1.9) → (0.1, 0, 1.45), with a 32 mm lens on a 36 mm sensor, which is a vertical FOV of 35.1° at 16:9. The ground is `#d6dbe4`, close to the Cycles preview's snow (linear 0.66–0.78).

The reference glb predates the naming contract, so the page names its emissive mesh `bulbs_0` with material `bulb_warm`. It also adds `light_0` inside and `light_1` under the front eave, where the carpenter's current stalls carry them.

The reference glb's metals are palettised: `PaletteMaterial002` carries the wires, the hinges and the copper pot, with metalness 1 and roughness 0.25 from a 64×4 palette texture (copper is `#ffc287`). `PaletteMaterial003` and `004` (garland and mugs) add a clear coat of roughness 0. The probe picks these up by their small palette maps; the light-size floor tames the clear coat.

```sh
cd site
npx vite --config src/lighting/vite.test.config.js   # then open http://localhost:4390/src/lighting/test.html
```

URL options:

| Option | Effect |
|---|---|
| `?lite=1` | Lite profile |
| `?snow=1` | Snow on |
| `?mode=before` | The engine's stand-in lighting, for comparison |
| `?view=wide` or `?view=sky` | Other camera views |
| `?capture=1` | Also capture the global environment from the scene (from `[2.5, 2.2, 7]`, out in front, so the snow is not tinted by the stall filling half the view) |
| `?lights=0` | Keep only `light_0` |
| `?cam=x,y,z,tx,ty,tz` | Any camera (close-ups for checking artifacts) |
| `?set=moon.lightIntensity:0.2,bloom.strength:0` | Override any value in `NIGHT` |
| `?shot=1` | Hide the HUD |

Tools (software GL on this machine):

- `node src/lighting/shoot.mjs` shoots the bench views (after, before, lite, snow, snow_lite, wide, wide_snow, sky, sky_lite, capture, plus `--var name='?query'` experiments).
- `node src/lighting/shoot-market.mjs` shoots the real market through the site's dev server with `vite.market.config.js` (live reload off).
- `node src/lighting/diag-market.mjs [--q ...] [--places id,...]` dumps the market's placed lights, pools, glows and shadow casters to `diag.json`, and can shoot close views of places.
- `node src/lighting/perf.mjs [--gpu --headed] [--fixed]` profiles the real market: rAF frame times, GPU time of the composer (timer queries), draw calls and the adaptive level. Run it with `--gpu --headed` on a machine with a real GPU.
- `python3 site/src/lighting/measure.py <shot.png>` compares patch colours (counter, sign, walls, pot, ground, sky) with the Cycles reference.
- `python3 site/src/lighting/compose.py` (from the repo root, `RAW=<dir>` for the PNGs) builds the review JPEGs.
