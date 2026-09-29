# Lighting: the night

`site/src/lighting/` is the lighting designer's module. It supplies the sky, moonlight, fill light, fog,
reflections, tone mapping, bloom, the warm lights at `light_` empties, and the snow.

```js
import { createLighting } from './lighting/index.js';

const lighting = createLighting({ scene, renderer, camera, lite });
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
| `placeLights(spots, { focus, reserved, shadowed, budget })` | Turns `light_` empties into warm lights within the profile's budget. It takes the engine's spot shape `[{ obj, kind, id }]` and returns `{ lights, pools, cap, refreshShadows(), dispose() }`, a superset of `engine/lights.js`, so it can replace that call. |
| `tune(root)` | Applies this module's emissive levels to bulbs and windows in a model that loads late. |
| `captureEnvironment(position)` | Re-captures the reflection map from the real scene. |
| `fitShadow(center, radius)` | Moves the moon's shadow box. |
| `settings`, `profile`, `sky`, `hemi`, `moonLight`, `bloom`, `grade` | The parts, exposed for tuning from the console. |

`createLighting` also accepts `options`: `{ shadowCenter, shadowRadius, envCapture, envCapturePosition, adoptEngineLights, profile }`.

The engine needs no changes. `engine/lighting.js` already loads this module when it exists. When `createLighting` runs it:

- finds the engine's `engine_light_*` point lights and re-tunes them (colour, interior or front fill, reach, and static shadows for the nearest section stalls);
- finds every `bulb_warm`, `bulb_cold` and `window_warm` material and sets its emissive level, including `userData.baseEmissive`, which the engine's flicker multiplies.
- masks the engine's own `engine_snowfall` points out of rendering, because this module's snow replaces them (turn this off with `options.replaceEngineSnow = false`).

All numbers are in `settings.js` (`NIGHT` for the look, `PROFILES` for full and lite).

## Tone mapping: AgX, with part of Blender's "Punchy" look

The module uses **AgX**, not ACES, for three reasons:

1. **It matches the reference.** Every Cycles preview in this project is rendered with Blender's AgX view transform and the *Punchy* look. three.js's AgX is the same curve, ported from Blender via Filament. The browser and the visual targets therefore share a tone curve, and tuning becomes a matter of lights and exposure, not of fighting a different film response.
2. **It handles saturated lights better.** The scene is dark and blue with small, very bright, saturated warm sources: bulbs, lanterns and lit windows. ACES pushes bright oranges toward yellow and pink and holds too much saturation, so bulbs turn into orange blobs. AgX desaturates toward white as a light gets brighter, the way a real incandescent bulb looks in a photograph: a white-hot core with a warm fringe.
3. **Its shadows hold detail.** ACES crushes the deep blues that carry most of this frame. AgX keeps detail in the dark blues, so moonlit wood stays readable.

three's built-in `AgXToneMapping` has no look. `grade.js` replaces three's `OutputPass` with one pass that does the following:

- exposure;
- a vignette of 0.28;
- AgX, with the look applied between the sigmoid and the outset, where Blender applies it. The look is Punchy, which is power 1.35 and saturation 1.4, blended in at `punch = 0.45`. At full strength it over-saturated the warm wood next to the reference.
- sRGB encoding;
- about 1 to 3 code values of animated triangular grain, which also dithers the dark sky gradient against 8-bit banding.

**Colour management:**

- `ColorManagement` is on, and all colours in `settings.js` are sRGB hex that three converts to linear.
- The scene renders linear HDR into a half-float target (4× MSAA on the full market), then goes through bloom, then the grade.
- `renderer.toneMapping` is set to AgX as well, so anything drawn straight to the screen matches.
- `renderer.toneMappingExposure` is read by the grade every frame, so there is one exposure control.

**Units:**

- Intensities are three.js physical units: a point light's intensity is roughly Blender watts ÷ 4π, and a directional light's is roughly Blender sun strength.
- The Glühwein preview's 60 W front fill is therefore about 5 in three.js, and the front fill here is 7.

## Key settings (full market)

| Part | Setting | Why |
|---|---|---|
| Sky | Zenith `#01030d`, mid `#02081d`, horizon `#0a1836`, a faint warm horizon glow (`#221a12` × 0.35) | Deep blue, like the reference, with a gradient and a hint of town glow. |
| Stars | Three hashed star layers in the sky shader: 60, 150 and 320 cells per radian, with 7 %, 2.5 % and 1.2 % filled. Magnitudes follow a power law, colour temperature varies, stars twinkle, and they fade near the horizon and the moon. | Each star is about 1.5 px wide at any resolution because its size uses `fwidth`. There are enough stars to read as a clear winter night without looking like glitter. |
| Moon | Disc of 0.03 rad (about 2.5× the real angular size, for the miniature look), limb darkening, noise maria, HDR 4.2 so it blooms. Two-lobe halo in `#5d6fa8` × 0.55 and a faint 22° ice ring. It sits low over the town roofs in the home view. | A soft-haloed moon that frames the market. |
| Clouds | Thin fbm clouds lit silver near the moon and warm from the town below. Off on the lite market. | Depth in the sky. |
| Moonlight | Directional light `#86a0ff` at 0.30, from high left and slightly toward the viewer. The direction is not the disc's: a moon that low would put every stall front in silhouette. | Cool, grazing light on wood and cobbles. |
| Moon shadows | 2048² map, PCF with `radius` 4 (three r18x PCF is a Vogel-disk soft filter), bias -0.0004, normal bias 0.025, shadow intensity 0.85, box ±42 m around the square. | Soft, readable shadows. |
| Hemisphere fill | Sky `#2a4a9a`, ground `#0e1322`, 0.35 | Blue ambient that keeps dark sides readable without flattening them. |
| Fog | `FogExp2` `#0a1630`, density 0.0135, plus a ground mist: density × (1 + 1.1·e^(−h/3.2 m)). It works by patching three's fog chunks for all built-in materials. | The town ring (47–64 m) sinks into blue haze while roofs and the wheel stay crisp against the sky. |
| Environment | PMREM, 256 (lite 128). It starts as a synthetic night (sky, dark wet ground, a ring of warm and cool glows, overhead string-light dots). On frame 3 of the full market it re-captures the real scene from `[0, 1.6, 2]`, and again after a snow toggle. `environmentIntensity` 0.4. | Wet cobbles, glazed mugs, glass and copper reflect the actual bulbs and lamps. |
| Bloom | `UnrealBloomPass` with threshold 1.6 (knee 1.2), strength 0.65, custom mip weights `[1, .7, .38, .16, .06]` with radius 0, and input clamped at 14. The lite market blooms at half resolution. | Only emissives bloom (bulbs at 6, windows at 1.5, the moon at 4.2). Lit wood (< 1.5) does not. The weights keep a crisp core with a short soft tail. The default weights put most of the energy in the widest mip, which washed a warm haze over the whole stall; that is fixed. |
| Bulbs | `bulb_warm` emissive (1, .62, .30) × 6, `bulb_cold` (.62, .76, 1) × 5. Also written to `userData.baseEmissive`. | The same brightness across everyone's models. The reference glb ships 25, which bloomed into blobs. |
| Windows | `window_warm` × 1.5 | They read as lamplight, not as light sources. |

### Warm lights at `light_` empties

The light colour is 2900 K. Intensities are in three.js units.

| Kind | Interior point | Front fill (point under the front eave) | Spot | Reach (point / front / spot) |
|---|---|---|---|---|
| Section stall | 40 | 7 | 34 | 4.2 / 7 / 8 m |
| Deco stall | 18 | 5 | 20 | 3.6 / 6 / 7 m |
| Landmark | 26 | – | 40 (stage lights above 2.8 m point down) | 10 / – / 12 m |
| Lamp (`light_lamp_*`) | 7 | – | – | 10 m |
| Tree (`light_tree_*`) | 16 | – | – | 10 m |

How the helper places them:

- **Front or interior.** A `light_` empty more than 0.9 m in front of its model's origin (model +Z) is the front fill. It lights the garland, the counter front, the sign and the cobbles, like the Cycles previews' front light. Anything else inside the model is the interior light.
- **Spots.** A spot is used when an empty's `userData.type` is `'spot'`, when its name contains `spot`, or for high landmark lights. `userData.intensity`, `userData.distance`, `userData.color` and `userData.aim` override the defaults.
- **Interior shadows.** On the full market, the interior lights of the **4 section stalls nearest the view** get a shadow: a 512² cube map with shadow intensity 0.78, where the remainder stands in for bounce light. Stalls do not move, so these maps are drawn **once** (`shadow.autoUpdate = false`) and cost almost nothing per frame. Without a shadow, an interior light leaks through the walls onto the cobbles. Unshadowed lights keep a short reach (3.6–4.2 m) so any leak stays close.
- **Budget.** The full market has 14 real-time lights, the lite market 4, minus the engine's reserved bandstand spots. Ranking puts section stalls and landmarks first, then the tree, deco stalls and lamps, nearest the focus first, one light per model before any second light. A light that misses the budget becomes a soft additive warm pool on the ground.

### Snow

`setSnow(on)` blends over about 2 s. It changes the following:

- The fog thickens (density 0.0135 → 0.024) and lightens (to `#222c4a`).
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

How the flakes move and look:

- Each flake falls at its own speed (0.85 m/s mean ± 40 %) and flutters on its own.
- All flakes drift with a wind of (0.9, 0.35) m/s with slow gusts, integrated in scene time, so reduced motion freezes the snow.
- Flakes pass through the warm light of the four nearest stall lights, so snow glitters in front of the stalls.
- The CPU does no per-flake work.

## Profiles

| | Full | Lite |
|---|---|---|
| Real-time warm lights | 14 | 4 |
| Shadows | Moon 2048² PCF, plus 4 static interior shadows | **None** (shadow map off) |
| MSAA | 4× | Off |
| Bloom resolution | Full | Half |
| Environment | 256, captured from the real scene | 128, synthetic only |
| Sky clouds | On | Off |
| Grain | On | Off (the 1-code-value dither stays) |
| Snow flakes | 28,500 | 8,000 |

## Test bench

`test.html` loads `review/reference/gluehwein_stall_web.glb` on a plain ground plane and frames it with the Cycles camera: Blender (-3.4, -5.6, 1.9) → (0.1, 0, 1.45), with a 32 mm lens on a 36 mm sensor, which is a vertical FOV of 35.1° at 16:9. The reference glb predates the naming contract, so the page names its emissive mesh `bulbs_0` with material `bulb_warm`. It also adds `light_0` inside and `light_1` under the front eave, where the carpenter's current stalls carry them.

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
| `?capture=1` | Capture reflections from the real scene |
| `?lights=0` | Keep only `light_0` |
| `?set=moon.lightIntensity:0.2,bloom.strength:0` | Override any value in `NIGHT` |
| `?shot=1` | Hide the HUD |

Screenshots on software GL:

- `node src/lighting/shoot.mjs` covers the bench views (after, before, lite, snow, snow_lite, wide, wide_snow and sky, plus `--var name='?query'` experiments).
- `node src/lighting/shoot-market.mjs` shoots the real market through the site's dev server, without building. It uses `vite.market.config.js`, the site config with live reload off, so a teammate's save cannot reload the page mid-shot.
- `python3 site/src/lighting/compose.py` (run from the repo root) builds the review JPEGs.
