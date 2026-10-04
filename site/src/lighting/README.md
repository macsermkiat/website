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
| `focusPlace(id)` | Gives the entered place (a place id such as `'glueh'`, or a layout id) the real lights it lacks, borrowed from other models; `null` gives them back. The module does this by itself from the camera unless the engine calls it (see "The entered place gets the lights"). |
| `placeLights(spots, { focus, reserved, shadowed, budget })` | Turns `light_` empties into warm lights within the profile's budget, gives every section and deco stall an interior glow (and, where it has a front `light_`, a roof glow and a ground spill), and clips every unshadowed interior light to its stall. It takes the engine's spot shape `[{ obj, kind, id }]` and returns `{ lights, pools, cap, interiors, glows, clips, clipEntries, blockers, refreshShadows(), dispose() }`, a superset of `engine/lights.js`. It logs one `[lighting] placed …` line. |
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
| Moon | Disc of **0.02 rad** (about 1.7× the real size; 0.03 in round 1), limb darkening, noise maria, HDR **2.8** (was 4.2), so only its core blooms. Two-lobe halo in `#5d6fa8` × **0.3** (was 0.55) and a faint 22° ice ring. It sits low over the town roofs in the home view. | A soft-haloed moon that frames the market without being the brightest, largest thing in it (Codex round 1: "reduce glare and moon dominance"). |
| Clouds | Thin fbm clouds lit silver near the moon and warm from the town below. Off on lite. | Depth in the sky. |
| Moonlight | Directional `#9ab0f0` at 0.36, from high left and slightly toward the viewer (not the disc's direction: a moon that low would put every stall front in silhouette). | Cool, grazing light on wood and cobbles. |
| Moon shadows | 1536² map (5.5 cm a texel over the market's ±42 m box), PCF `radius` 4, bias -0.0004, normal bias 0.025, intensity 0.85. Redrawn every 3rd frame (`moonShadowEvery`). Meshes of placed models smaller than 0.15 m (`minMoonCaster`) stop casting it once the interior shadows are drawn. | Soft, readable shadows. The town and stalls are still, and walking people's shadows read the same at 20 Hz. On average the shadow pass now costs about a third of a pass a frame, and the trim takes the small props out of it. |
| Hemisphere fill | Sky `#4a5c90`, ground **`#3a2c22`** (was `#14161c`), **0.4** | The ground colour is the warm bounce off the lit square. It lifts what faces sideways and down (the crowd's coats and faces, the facades, the undersides of eaves) toward warm grey, while what faces up (roofs, cobbles) keeps the cool sky fill, so the night keeps its blue tops and is not flattened (Codex: "lift crowd and facade detail"). |
| Moon rim | `#9fb4ff`, radiance **0.09** at the edge (0.06 in round 1), Fresnel power 1.6, on steep faces (× (1 − n.y²)) facing the moon disc, added as radiance rather than multiplied by albedo, and only on dark materials: it fades out between albedo 0.07 and 0.16 (`shading.js`) | The crowd's coats have albedo 0.01–0.07, so no amount of light on them shows. A grazing sheen, the way wool catches light, outlines the figures and iron posts in front of the stalls. Wood (albedo 0.2 and up) gets none, so a stall's moon-side wall stays near-black as in Cycles (lightness 0.03 against 0.01; pass 2 had 0.13 with the rim on everything). |
| Fog | `FogExp2` `#0a1630`, density **0.0115** (0.0135 in round 1), plus a ground mist: density × (1 + 1.1·e^(−h/3.2 m)). Patches three's fog chunks. | The facades 50–60 m out keep their timbering and windows (transmittance there 0.67, was 0.58) while the church and the far town still sink into blue haze. |
| Town wash (round 2) | Walls of the town ring (world radius from 36 m, full from 46 m; the market, the deco rows and the Ferris wheel all sit inside 30 m) get warm diffuse light `(1, .74, .5)` × 0.22 (`shading.js`, `NIGHT.town`). 70 % of it goes only to walls that face the square, and it falls off over 9 m up the facade. | The market's glow and the town's own street lamps on the facades: the timbering, doors and lower storeys read from the home view, while the roofs and upper storeys stay in the blue night (Codex: "lift facade detail without flattening the night"). It is one term in the glow loop, so it costs nothing measurable, and `intensity: 0` turns it off. |
| Global environment | PMREM 256. The synthetic night at start; on full, the real market captured once on frame 3 from `[0, 1.6, 2]` (`environmentIntensity` 0.45). **No periodic refresh.** It is re-captured, one cube face per frame into the same texture, only 0.5 s after the snow blend has settled following a toggle, or when the engine calls `refreshEnvironment()`. | Wet cobbles and glass reflect the actual bulbs. The market is static apart from the rides and the crowd, which are too small in a 256² reflection to matter, so a periodic refresh (pass 2: six frames of about 950 extra draw calls every 30 s) only caused a hitch. |
| Local probes | On frame 3, the 6 nearest stalls (lite: 2) that hold copper, glass or glaze get their own 128² probe (lite 64²), captured from the middle of those props with the props hidden, as their material's `envMap` at intensity 1.0. | The copper pot reflects the lit back wall, the bulbs and the dark market in front, as in Cycles, instead of a dark synthetic sky. |
| Bloom | `UnrealBloomPass`, threshold 1.6 (knee 1.2), strength **0.34** (round 2, pass 3; 0.32 before, with the dimmer bulbs below), mip weights `[1, .2, .07, .025, .01]`, radius 0. Input clamped to **5** by the brightest channel (hue kept). | Only emissives bloom (bulbs at 6, windows at 1.5, the moon at 4.2); lit wood (< 1.5) does not. The clamp means a specular glint on copper enters the bloom no brighter than a bulb, so glints cannot become glare stars. The weights keep a crisp core with a short tail. Pass 4 (0.40 and `.3` before): the bulbs measure 12–19 px wide, median 16 (Cycles 13–16, median 14; pass 3 median 18). See "Bulb row" below for what is left. |
| Bloom, half resolution | Lite, and full after the third adaptive step: weights `[1, .1, .025, .005, 0]`, strength 0.34 | At half resolution every mip is twice as wide on screen; shifting weight to the tight mips keeps the moon halo and lamp glows the same size as on full. |
| Light size | For direct light only, roughness is floored at 0.32 and clear-coat roughness at 0.30 (`shading.js`) | three's lights are points, so a mirror clear coat (the reference mugs and pot have clear-coat roughness 0) reflects them as one blazing pixel. Real lamps have a size. Reflections of the environment stay sharp. |
| Bulbs | `bulb_warm` emissive (1, .55, .24) × **3.9** (round 1: (1, .62, .30) × 6; round 2 pass 1: × 4.8). AgX turns any channel past about 4 to white, so close up, at 2–3 m, every bulb was a white disc with an orange rim, and the cores and halos read as glare. At 3.9 with the deeper amber only the red channel is far above the bloom threshold: the core reads warm cream and the halo amber. On the bench the bulbs now measure median 13 px (Cycles 14) and the band under them luma 151 (pass 1: 161), `bulb_cold` (.62, .76, 1) × 5, also written to `userData.baseEmissive` | The same brightness across everyone's models. |
| Bulb-string glow | Each short, level string of bulbs on a stall is a line light: **0.18** × bulb colour, 0.9 m reach, half-wrapped diffuse (`shading.js`). Strings longer than 5 m or taller than 1 m (wheel, carousel, tree, festoons) are skipped. | The garland and the lambrequin are lit by their bulbs, as in Cycles, at the cost of a small loop per pixel instead of more three.js lights. The lambrequin measures lightness 0.28 (Cycles 0.26; 0.35 at 0.25 in pass 3, 0.44 at 0.6 in pass 2). |
| Stall interior glow | Every section and deco stall: a one-sided point glow 0.3 m below its interior `light_` empty, reach 2.6 m, clipped below 0.3 m over the stall's base and above 0.15 m over the empty. Intensity **7** where the stall has a shadowed light (9 in pass 3), 6 with an unshadowed one, 16 with none. | Every stall front reads warm from the home view, including the stalls the light budget cannot reach. One-sided, so it cannot shine out through the walls; clipped, so it lights no halo on the ground and no roof. |
| Roof glow (`glow.eave`) | Every stall with a front `light_`: a one-sided glow 0.6 m in front of and 0.5 m above that empty, intensity 38, reach 3 m, clipped below 5 cm under the empty, **or above the top of a sign board in front of it** (round 2: on the market's Glühwein stall the board on the fascia caught this glow and washed out to 240/255, with pale pink letters). | It lights what faces it above the eave line: the front slope of the roof (or the soffit, where the lamp hangs under the eave). The downward front-fill spot cannot reach it. The strip of roof above the bulbs measures lightness 0.23 (Cycles 0.24; pass 3 0.06). |
| Ground spill (`glow.spill`) | Every stall with a front `light_`: a one-sided glow where the front fill hangs, intensity **7.5**, reach **6 m** (11 and 8 m in round 1), clipped above 0.2 m over the base, so it lights only the ground. From the home view the round-1 pools were the brightest ground in the frame and read as glare. | The warm pool Cycles' omnidirectional front light spreads around the stall. The cobbles beside the stall, in its moon shadow, were blue (hue 250°) and are now warm grey (hue ~350°; Cycles 4°). A spot strong enough to reach them also lit the sign and the lower front wall to 0.24 against 0.14. |
| Windows | `window_warm` × 1.5 | They read as lamplight, not as light sources. |

### Bulb row

**Fix pass: baked AO.** The carpenter's stalls ship a baked AO map (glTF `occlusionTexture` on uv1) since round 3. three applies it only to the hemisphere and the environment. `shading.js` now also applies it (`lightingAO()`, settings `ao`) to every local glow, in full (`ao.glow` 1.0: they stand in for bounce light), and to the short-reach interior lamps, in part (`ao.point` 0.6, point lights with a reach under 6 m only, so not the rides' washes or the bandstand). On the shipped Glühwein stall, in the bench camera, the wall just under the bulb row goes from luma 131 to 129 and the upper back wall from 152 to 148. There the bulbs hang in front of the red lambrequin and already stand apart: 15 runs, the widest 16 px (`ao_stall.jpg`, `ao_bulb_row.jpg`). The 120 px run below is a property of the old bench glb (`review/reference/gluehwein_stall_web.glb`), which has no AO map and hangs its bulbs in front of the pale back wall. On that glb I tried a lamp radius for diffuse light (I / (d² + r²), r 0.3–0.7 m), a shade over the lamp's horizon, lowering the interior glow's ceiling, and turning that glow off. None of them separated the bulbs without darkening the shelves too: the wall right behind the bulbs sits 0.85 m from the lamp, just under its horizon, so its direct light is what lights it. None of these changes are kept. The bench would need the same AO bake as the shipped stalls.

**Round 2 (before the fix pass):** `measure.py` also measures the bulb row: the width of each bright run along it (luma > 200) and the mean luma of the band just under it. Against Cycles (13–16 px, median 14; band 111), pass 3 had median 18 px, one 143 px run where the left bulbs merged, and band 177. Pass 4's bloom (strength 0.32, second level 0.2) gives median 16 px and band about 160; the merged run is down to about 120 px. What is left is not bloom: the top of the back wall right behind the bulbs is lit almost white by the interior light 0.3 m above it (Cycles' area light is shaded there by the fascia), so the gaps between the left bulbs stay above the threshold. Lowering the whole interior would darken the counter and shelves, which now match. A baked lightmap or AO on the carpenter's stalls would fix it properly.

### Warm lights at `light_` empties

The light colour is linear (1.0, 0.6, 0.3), the colour of the Cycles previews' lights (`nmlib/render.py`). Pass 1 used 2900 K through a black-body fit, which is (1, 0.42, 0.13) in linear and pushed the wood toward red. The front fill is a little paler, (1.0, 0.7, 0.36), so the snow in front of a stall reads cream, not pink.

| Kind | Interior point | Front fill (spot under the front eave) | Spot | Reach (point / front / spot) |
|---|---|---|---|---|
| Section stall | **34** (40 in pass 3) | **9**, cone 1.4 rad, penumbra 0.25 | 34 | 4.2 / 9 / 8 m |
| Deco stall | 18 | 6, cone 1.4 rad, penumbra 0.25 | 20 | 3.6 / 6 / 7 m |
| Landmark | 26 | – | 40 (stage lights above 2.8 m point down) | 10 / – / 12 m |
| Landmark wash (a `light_` above 8 m: the Ferris wheel's hub light) | **56**, hung a further **6 m** out along the model's +Z (`washOut`; fix pass, was 70 and 3 m) | – | – | **30 m** (fix pass, was 18 m) |
| Lamp (`light_lamp_*`) | 7 | – | – | 10 m |
| Tree (`light_tree_*`) | 16 | – | – | 10 m |

How the helper places them:

- **Front or interior.** A `light_` empty more than 0.9 m in front of its model's origin (model +Z) is the front fill: a wide spot hung 0.4 m above and 0.8 m in front of the empty (`frontLift`, `frontOut`) and aimed at the ground 1.7 m out (`frontAim`), which lights the counter front, the sign and the cobbles but not the fascia (outside its 80° cone). Its core is wide (penumbra 0.25), so its pool reaches about a metre further than pass 3's. Anything else inside the model is the interior light.
- **The Ferris wheel's wash (round 2, pass 3 and fix pass).** The rides builder's `light_2` sits 3.2 m in front of the hub. From there the steel round the hub took 13 times the light of the 11 m rim and, with the hub's own bulbs, bloomed into a white star in the home view. Pass 3 hung it 3 m further out, but the judges still saw the star. The reason was three's distance window, (1 − (d/D)⁴)², which at an 18 m reach cut the rim (12.8 m away) to 55 % but the hub (6.2 m) only to 97 %, so the hub still took 7.5 times the rim's light. The fix pass hangs the wash **9.2 m** in front of the hub (`washOut` 6), with a **30 m** reach and intensity **56**. The rim gets the same light as before (0.24) and the hub 63 % less (2.7 times the rim).
- **The hub's bulbs (fix pass).** The 16 spokes carry bulb strings that converge on the hub, and their last 3–4 m overlap into one bloom. `hubFade` (`lights.js`, `emissive.hubFade`) gives every `bulbs_` mesh under a `rot_wheel` a per-vertex `nmEmit`, computed from the distance to the wheel's axis: **0.15** at the hub's rim (1.2 m), full from **5 m** out. Its bulb material is cloned with a one-line shader patch that multiplies the emissive by it. At 0.15 × 3.9 the inner bulbs sit under the bloom threshold, so they read as small amber dots on the spokes, and the wheel reads as rim and spokes (`review/round-2/lighting/wheel_hub_bench.jpg`, `market_hub.jpg`). The gondolas' bulbs, out on the rim, are left alone. It adds no draw calls.
- **Spots.** A spot is used when an empty's `userData.type` is `'spot'`, when its name contains `spot`, or for high landmark lights. `userData.intensity`, `userData.distance`, `userData.color` and `userData.aim` override the defaults.
- **Interior shadows.** On the full market, the interior lights of the **4 section stalls** get a 512² cube shadow map, drawn **once** (`shadow.autoUpdate = false`), with shadow intensity **0.95**. Only stall interiors get these slots (pass 2 gave one to the tree). The kernel is wide (radius **8** texels, taken with **16** taps instead of three's 5; a lamp has a size). Round 2, pass 3 (radius 5, 12 taps before): close up, the shelf boards threw shadows with a hard 2–3 px edge onto the back wall; a stall lamp is a 10 cm bulb about a metre from the shelf, so the penumbra should be a few centimetres wide. The four maps are drawn once, so the wider kernel costs only the 4 extra taps per shaded fragment, the near plane is 0.15 m and the bias -0.0003. The bias is in perspective depth: pass 2's -0.002 with a 5 cm near plane was about 0.3 m at the wall base, which let the light out onto a pale strip of ground around the stall.
- **Shadow-only shell.** Each of those stalls also gets a shadow-only shell (`shadowBlocker`): a floor 5 cm over the base and planes 12 mm outside the side walls, the back wall and the lower front wall, found by casting rays at the stall from outside. It draws nothing on screen and nothing into the moon's shadow (its depth material culls every vertex). It closes the hairline gaps between wall planks, which a 512² cube map otherwise lets through as sharp streaks across the ground.
- **The light the walls bounce** comes from the stall's interior glow (below), not from a see-through shadow.
- **Unshadowed interiors** (every stall on lite) are **clipped to the stall's interior** (`interiorBox` in `lights.js`, the clip in `shading.js`). Rays cast from the light find the inner faces of the side walls, the back wall and the lower front wall, and the roof's underside as a tent (its ridge and its steepest slope). The light then reaches nothing outside that box: its faces sit 1 cm into the boards (1 cm fade), so the planks' edges in the wall gaps stay dark; the floor is 0.3 m over the base, so no ground; and in front there is 0.3 m of extra room only below the fascia, for the counter top and the mugs. Pass 3 had no clip: the light shone through the walls onto the barge boards, the eave, the ground and the plank edges (bright slits). The light stays at its empty (no drop), with a 3.2 m reach and **50 %** intensity; the interior glow carries the rest. If a model has no closed interior, the light falls back to pass 3's 0.3 m drop.
- **The clip** is keyed by the light's world position, so it does not depend on three's light order. It costs one loop of up to 4 clips per point light per pixel, and returns at once when there are none (the full market normally has none).
- **Budget.** The full market has 14 real-time lights, the lite market 4, minus the engine's reserved bandstand spots. A model's first light is its interior; its front fill is second. Ranking is by kind (section stalls, then landmarks and the tree, then deco stalls, then lamps), then first lights before second ones, then distance to the focus. So the full market lights the four section interiors and their four front fills before any landmark, and the lite market's four lights are the four section interiors. A light that misses the budget becomes a soft additive warm pool on the ground, and its stall keeps its interior glow.

### Sign lamps (round 2)

Every stall with a `slot_sign` gets a **sign lamp**, so the painted boards read in the browser (Glühwein, Bratwurst and the rest):

- **Finding the board.** `signRect` casts rays at the `slot_sign` empty from 1.2 m in front of the stall (its +Z) and walks left, right, up and down in 2 cm steps until the surface steps back (the board's edge: its thickness, or the gap to the wall behind). Anything proud of the board, such as raised letters, is walked over, and a slightly tilted board is followed (each step may differ from the last by 8 mm). That gives the board's centre, width and height, whatever the carpenter or vendor built. With no hit it assumes a 1.2 × 0.35 m board at the empty.
- **The light.** A one-sided **line glow** (`glow.sign`, a small area light) along a bar `out` = 0.3 m in front of the board and `up` = 0.1 m over its top edge, 75 % of the board's width (at most 2 m), intensity 1.5, reach 1.1 m. At 3 (the first try) a pale board went flat and its light letters lost contrast; 1.5 lifts a dark board to about lightness 0.35 and leaves the market's cream boards short of white. It is clipped from 8 cm under the board to just under the bar, so it lights the board and the fascia around it and never the roof. One-sided means only faces turned toward it are lit. Falloff from the top edge to the bottom gives the gradient of a real picture light.
- **The fixture.** A picture-light hood (round 2, pass 2; pass 1 had a flat 24 × 40 mm bar that read as a black line over the board). The hood is a 3.5 cm-radius arc over the tube, open back and down onto the board, with end plates, in dark bronze (`lighting_sign_lamp_iron`). Inside it is a warm reflector (`lighting_sign_lamp_reflector`, emissive 0.35), and the tube itself (`lighting_sign_lamp_glow`, emissive 2.2) blooms slightly, so the light has a visible source from below. Two angled arms run down to small mounting plates on the board's top edge. All the lamps of one `placeLights` call are merged into one mesh with three materials (3 draw calls, 112 triangles a lamp). It casts no shadow and cannot be picked. `glow.sign.hoodRadius` and `reflectorEmissive` tune it.
- **Cost.** It is a glow, not a three.js light, so it costs the same on full and lite and does not touch the lite market's four real lights. Section stall signs share slot priority with the stall interiors (1). Deco stall signs get 60 % and priority 0, so the nearest ones win the remaining slots. Glow slots went from 24 to 28 (full) and from 12 to 16 (lite).
- **Bench:** `?sign=0` removes the bench's `slot_sign`, for comparison.

### The entered place gets the lights (round 2)

The Codex judge asked that the lite light allocation should favour the stall or landmark the visitor has entered. `focusPlace(id)` does this, and the module also calls it by itself:

- **The engine should call it (fix pass).** The request in BUILD.md form: *Engine: `openPlace(id)` calls `lighting.raw.focusPlace(id)` before the camera flight starts, and closing the panel or `resetView()` calls `lighting.raw.focusPlace(null)`.* The first explicit call turns the camera detection off for good (pass 3 turned it back on after `focusPlace(null)`), so from then on the allocation never depends on the camera settling, and the lights are in place while the camera flies in instead of a third of a second after it lands.
- **Detection (fallback until the engine calls it).** Every 10 frames the module checks whether the camera has settled (moved less than 5 cm since the last check) at a place's `cam_view` (within 1.5 m, or 12 % of the distance from `cam_view` to `cam_target` for the rides' far views), looking toward `cam_target`. A flight that passes near another place's view on its way therefore moves no lights. If so, that place is entered. When the camera leaves, focus is cleared. If the engine calls `lighting.raw.focusPlace(id)` (from `openPlace` and on close, with `null`), the automatic detection stops and the engine's call decides.
- **Borrowing.** The entered place's `light_` spots that have no real light borrow one, up to `focusLights` (2) and never beyond 2 real lights per model. Donors are unshadowed lights of other models: deco stalls first, then landmarks and the tree, then section stalls, and the farthest first. On the lite market that is how the bandstand, the Ferris wheel and the carousel get a real light when entered, and an entered section stall gets its front fill.
- **No recompile, no pop.** A light is moved, not created, so the count of point and spot lights in the scene never changes and no material recompiles. A moved light fades in over about 0.3 s. The interior glows of both stalls switch between `unshadowed` and `only`, and an interior clip box moves with the light. Leaving the place puts every light back.
- `focus` and `focusMoves` report the current state (for tests).

### At most two real lights per stall (round 2)

BUILD.md allows two `light_` per section stall. The Bücherstand's counter prop brings a third (`light_lamp`). `placeWarmLights` now gives any model at most `warm.perModel` (2) real lights. A stall's further `light_` becomes a small two-sided glow (`glow.lamp`: intensity 2.5, reach 1.3 m), with no ground pool.

### Figures in close-ups (round 4)

The whole-market judge found the Bier vendor's white sleeves blown out to glare and the Glühwein vendor's face a dark smudge under a white scarf. The cause is where a vendor stands: at `slot_vendor`, right under the stall's interior lamp (`light_0`, 0.7 m over his head). Per unit of albedo, his shoulders, sleeves and a pale scarf (albedo 0.79, 0.69, 0.53) took 30 to 50 times the light the back wall gets, so they rendered at a linear radiance of about 13 and AgX turned them white. His face is vertical and turned away from the lamp, so it got grazing light only.

Every material of a figure gets the define `LIGHTING_FIGURE`. A figure is a skinned mesh under the crowd's `crowd` group, or a material the crowd lifted (`userData.crowdLift`) or flagged `userData.figure`. `markFigures()` runs every 2 s of wall time, because the crowd loads after the lighting. With the define, `shading.js` adds two terms to the figure's shader. Nothing else in the scene changes.

- **Highlight shoulder** (`figure.knee` 0.9, `figure.range` 1.5): the direct light on a figure is linear up to the knee (linear radiance, by luminance, hue kept) and rolls off softly toward knee + range above it. A sleeve under the lamp now reads as lit cloth, about 2.2 in place of 13, and stays the brightest thing on the figure. The direct specular on cloth is scaled by `figure.spec` (0.35).
- **Close-up fill** (`figure.fill`: warm `[1, .72, .5]`, irradiance 1.7): a soft light from the viewer's side (`0.25 + 0.75 × N·V`). It stands for the light that the counter, the cobbles and the crowd bounce back at a face. It is full within 4.5 m of the camera and gone past 9 m, so faces read in close-ups and the crowd in the home view is unchanged.

### Bücherstand rack canopies (round 4)

The Bücherstand's side racks hang their own bulb strings from small canopies. The canopy shadowed the upper boards from the stall's front light, and the canopy bulbs lit nothing in the browser. The reason was `bulbStrings`: it joins strings that are up to a cell (0.35 m) apart in height, so the rack strings, 0.4 m under the eave string, became part of it, and their glow sat at the eave.

`canopyGlows` (in `index.js`) clusters the bulbs of each stall's `bulbs_` mesh again, with cells 0.2 m wide and 0.1 m tall, so strings more than about 0.2 m apart in height stay separate. A cluster gets a **canopy wash** when it meets three conditions: it hangs at least `canopy.below` (0.15 m) under the model's top string, it is at least `canopy.minLength` (0.6 m) long, and no `light_` reaches it (its middle is more than `canopy.minAway`, 1.6 m, from every `light_` empty in plan). The wash is a one-sided segment glow `canopy.down` (0.3 m) under the bulbs and `canopy.out` (0.3 m) toward the model's front, with its ends drawn in by 12 %. It has intensity 7 and reach 1.8 m, and it lights only between 0.25 m over the base and 0.28 m under the bulbs. The first try lit everything up to the bulbs, and the canopy fascia and the section signs, which hang right under them, blew out.

It lights the upper boards, the green backs and the book spines under the canopy, coming from where the bulbs hang. It is a glow, not a third three.js light, so full and lite get the same light and lite keeps its four real lights. No `light_3` empty was needed. The Glühwein lambrequin string and the Bücherstand's eave string are the top strings of their models, so they are left alone. Only section stalls get washes, at most `canopy.perModel` (4) each. The first market run also gave the tree 23 washes for its short, low strings, and each would have taken a priority slot. The washes take slot priority 1, like the stall interiors, so the racks are lit in the home view too. The Bücherstand gets two (`[lighting] 2 canopy washes under the bulb strings of …` in the console).

### Local glows (`shading.js`)

three.js evaluates every light for every pixel, so each extra light costs across the whole frame. The glows are a cheaper, diffuse-only light for the short-reach jobs:

- one shared `Float32Array` uniform (`lightingGlow`, 28 glows on full, 16 on lite, 3 vec4 each, then 4 interior clips of 4 vec4), added to every built-in lit material through the `lights_pars_begin`, `lights_fragment_begin` (the clip) and `lights_fragment_end` chunks, and kept by reference by `UniformsUtils.clone`, so one write updates every material;
- each glow is a segment (a point when both ends match) with a colour × intensity, a reach (with a smooth window to zero), a floor and a ceiling in world y (15 cm fades), and a side: two-sided glows wrap (bulbs), one-sided glows are plain Lambert (interiors);
- every 15 frames the slots are filled: stall interiors and section stall signs first, then the bulb strings, roof glows, ground spills, deco signs and prop lamps nearest the camera;
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
| Near | 14 m | 3500 / 1200 | 1.8–3 cm | Softer, a little out of focus |
| Mid | 36 m | 18000 / 5000 | 2–3 cm | Sharp |
| Far | 90 m | 7000 / 1800 | 1.9–3 cm | Dust that fades into the fog |

The sizes and softness are the engine's cap (`capFlakes` in `main.js`: 3 cm at most, softness 0.45 at most). Pass 3's bigger, softer near flakes read as grey discs in front of the market, so the engine capped them; settings.js now matches, so the cap changes nothing and the test page shows what the market shows.

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
| Local glows | 28 | 16 |
| Lights borrowed by the entered place | up to 2 (unshadowed only) | up to 2 |
| Sign lamps | glow + fixture on every stall sign | the same |
| Sky clouds | On | Off |
| Grain | On | Off (the 1-code-value dither stays) |
| Snow flakes | 28,500 | 8,000 |

### Adaptive quality (full only)

After the first 200 frames, the module measures wall-clock frame times over windows of 150 frames. If the median frame is too slow, it steps down one level per window and never steps back up. The thresholds are `adaptiveMs`: **16.7 ms** for the first step (MSAA 4× → 2×; fix pass, was 18.2) and 18.2 ms (about 55 fps) for the rest. The first threshold is the judges' rule ("if p50 is over 16.7 ms, set `msaa = 2`"), so any GPU that cannot hold 60 fps at 4× settles at 2× by itself, without anyone having to measure it first:

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
| `?figure=/models/people_vendor_bier.glb` | A person at the stall's `slot_vendor`, in a `crowd` group as in the market (round 4: vendors in close-ups) |

Tools (software GL on this machine):

- `node src/lighting/shoot.mjs` shoots the bench views (after, before, lite, snow, snow_lite, wide, wide_snow, sky, sky_lite, capture, plus `--var name='?query'` experiments). The bench can load any glb: `?glb=/models/ferris.glb&tune=1&own=landmark` runs the engine's per-model tuning (`tune`: bulb bounce, hub fade) and places the glb's own `light_` empties as that kind.
- `node src/lighting/shoot-market.mjs` shoots the real market through the site's dev server with `vite.market.config.js` (live reload off). `--shot "name=quality=lite&snow=0@open=glueh"` opens a place (the engine's short ids: `glueh`, `wurst`, `bier`, `books`, `band`, `ferris`, `carousel`) and calls `focusPlace` as the engine would; `@cam=x,y,z,tx,ty,tz` sets any view; `@front=place_bratwurst,7.5,1.7` views a model's sign from 7.5 m in front at eye height. `@snap=name` captures the current view mid-sequence and `@home` goes back to the home view, so one page load gives several views (a shot name starting with `-` writes only its `@snap` views). Loading the full market takes most of the 45 minutes a full-market shot needs on the shared 4-CPU machine; a lite one takes about 2.
- `node src/lighting/diag-market.mjs [--q ...] [--places id,...]` dumps the market's placed lights, pools, glows and shadow casters to `diag.json`, and can shoot close views of places.
- `node src/lighting/perf.mjs [--gpu --headed] [--fixed]` profiles the real market: rAF frame times, GPU time of the composer (timer queries), draw calls and the adaptive level. Run it with `--gpu --headed` on a machine with a real GPU.

### Real-GPU frame time (fix pass)

**Not measured.** The judges asked for p50 from `perf.mjs --gpu`. The cloud machine that builds the site has no GPU (no `/dev/dri`, no driver; Chromium falls back to SwiftShader), and this session cannot reach Mac's laptop. A software-GL p50 would measure the CPU, not the site, so I have not recorded one. Two things cover the gap:

- the first adaptive step now comes at 16.7 ms (see "Adaptive quality"), so on any GPU slower than 60 fps the full profile drops to MSAA 2× within about 5 s, which is the judges' rule applied at run time;
- on the M3 laptop, `cd site && node src/lighting/perf.mjs --gpu --headed --fixed --dpr 1.75` measures the fixed full profile. If p50 is over 16.7 ms, set `PROFILES.full.msaa = 2` in `settings.js` so the first seconds are smooth too, and write the number here.
- `python3 site/src/lighting/measure.py <shot.png>` compares patch colours (counter, sign, walls, pot, roof strip, ground beside and in front, sky) with the Cycles reference, and measures the bulb row. Compare 1280×720 shots only: bloom is sized in pixels.
- `python3 site/src/lighting/compose.py` (from the repo root, `RAW=<dir>` for the PNGs) builds the review JPEGs.
