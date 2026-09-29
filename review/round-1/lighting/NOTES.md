# Round 1: lighting and atmosphere (lighting designer)

## What was built

`site/src/lighting/` is the night. `index.js` exports `createLighting({ scene, renderer, camera, lite })`, which returns `{ composer, update(dt, t), setSnow(on), dispose() }`.

The engine already loads it through `engine/lighting.js`, and the market runs with it: its report says `lighting: "lighting"`, and there are no warnings. The engine needs no code changes.

| File | Contents |
|---|---|
| `settings.js` | Every tunable number: `NIGHT` for the look, and `PROFILES.full` and `PROFILES.lite`. |
| `sky.js` | A sky dome drawn at infinite depth around whichever camera renders it. It has a three-stop blue gradient with a faint warm glow of town light on the horizon, three hashed star layers (anti-aliased with `fwidth`, twinkling, fading at the horizon and near the moon), a faint Milky Way, thin fbm clouds lit silver by the moon, and a limb-darkened moon with grey maria, a soft two-lobe halo and a faint 22° ring. The moon sits low over the town roofs in the home view. |
| `fog.js` | `FogExp2` in the night blue, plus a **ground mist**: density rises near the cobbles and falls off with height. It works by patching three's fog chunks, so every built-in material gets it; `dispose()` restores the chunks. |
| `env.js` | PMREM reflections. The synthetic night is available immediately. On the full market, the real scene is captured once after it has loaded, so copper, glaze and wet cobbles reflect the actual bulbs. |
| `grade.js` | The final pass. It does AgX with a blend toward Blender's *Punchy* look (the view transform of every Cycles preview here), sRGB encoding, a vignette, and grain that also dithers the dark sky against 8-bit banding. |
| `lights.js` | Helpers for warm lights and emissives, described below the table. |
| `snow.js` | GPU snow in three depth layers (near out-of-focus flakes, sharp mid flakes, far flakes fading into the fog). Each flake falls at its own speed with flutter. Wind drifts all flakes with gusts. Flakes catch the warm light of the nearest stall lights. |

The helpers in `lights.js`:

- `placeWarmLights` turns `light_` empties into warm point or spot lights within a budget. It takes the engine's spot shape `[{ obj, kind, id }]`, so it can replace the call to `engine/lights.js`.
- `adoptEngineLights` re-tunes the lights the engine has already placed.
- `tuneEmissives` sets the emissive level of `bulb_warm`, `bulb_cold` and `window_warm`, including `userData.baseEmissive`, which the engine's flicker multiplies.

### Lights

- **Interior and front fill.** A `light_` empty inside a stall is an interior point light. An empty under the front eave (more than 0.9 m in front of the model's origin) is a front-fill point light that lights the garland, the counter front, the sign and the cobbles, like the Cycles previews' front light.
- **Spots.** A spot is used when `userData.type = 'spot'`, when the empty's name contains "spot", or for high landmark lights.
- **Static interior shadows.** On the full market, the interior lights of the 4 section stalls nearest the view get a shadow map that is drawn once (`autoUpdate = false`). Without it, an interior light leaks through the walls onto the cobbles. The per-frame cost is almost zero.
- **Budget and pools.** Lights beyond the budget become soft warm pools on the ground, as the engine already does.
- **Lite profile.** 4 lights, **no shadows at all**, no MSAA, bloom at half resolution, a synthetic 128 px environment, no clouds, and about 8k snowflakes instead of 28.5k.

**Tone mapping: AgX.** The full reasoning is in `site/src/lighting/README.md`. In short:

- AgX is the same curve family as Blender's AgX, so the browser and the Cycles targets agree.
- It desaturates very bright warm bulbs toward a white core, where ACES skews them to orange or yellow blobs.
- It holds detail in the deep blues that make up most of the frame.

### Test bench

- `site/src/lighting/test.html` loads `review/reference/gluehwein_stall_web.glb` on a plain ground plane, framed with the Cycles camera (32 mm lens, same position and target).
- Serve it with `npx vite --config src/lighting/vite.test.config.js`. That config also serves `/review`.
- `shoot.mjs` takes the bench screenshots on SwiftShader, `shoot-market.mjs` shoots the real market through the site's own dev server (via `vite.market.config.js`, which turns live reload off) without building, and `compose.py` makes these JPEGs. The raw PNGs are not kept in the review folder.

## Images in this folder

| Image | What it shows |
|---|---|
| `side_by_side.jpg` and `side_by_side_full.jpg` | The Cycles reference beside the three.js result (half size, and stacked at full size). |
| `before_after.jpg`, `before.jpg`, `after.jpg` | Before is the engine's stand-in lighting (`lighting-fallback.js` plus the engine's light values). After is this module. |
| `after_lite.jpg` | The lite profile. |
| `sky_moon_stars.jpg` | The sky with the moon, halo, stars and clouds. |
| `wide.jpg` | Fog and ground mist. |
| `snow_on.jpg` and `snow_toggle.jpg` | Snow off and on, the lite snow, and a close view showing the depth layers. |
| `market_home*.jpg` | The real market home view with this module, in full, snow and lite. |

## Budgets

The module ships no models or textures, and the sky, stars, snow and environment are all generated.

| Item | Size |
|---|---|
| Code | About 52 KB of unminified JS in 8 files |
| Sky dome | 4k triangles |
| Snow | 28.5k points on full, 8k on lite |
| Post | 1 half-float MSAA target, 5 bloom mips and 1 grade pass |
| Warm-light shadows | 4 × 512² cube maps on full, drawn once |
| Moon shadow | 2048² |

## What I would improve next

- **Bulbs do not light what is around them.** In Cycles the bulbs light the garland and the lambrequin; in three they only glow. My candidate is a baked "bulb glow" lightmap: the contract already allows a lightmap step from lighting. The cheaper option is a tiny emissive-weighted AO term. For now the front fill carries the garland.
- **The reference's left wall is almost black.** Ours shows cool moonlit wood, which reads better but departs from the reference's contrast.
- **Snow does not settle.** Snow-cover blending on the ground and roofs (a height-and-normal snow mask in the cobble shader) would pair with `snow_` caps.
- **Environment capture timing.** The capture happens once on frame 3. The Ferris wheel and carousel keep moving, so a slow re-capture every ~30 s on strong GPUs would keep reflections honest.
- **Lite bloom.** The lite market's half-resolution bloom spreads the moon's halo twice as wide on screen. Lite needs tighter mip weights.
- **Performance.** I have only measured on SwiftShader. A real-GPU profile of the full market is needed, especially 4× MSAA with bloom on a 1.75× pixel ratio.

## Contract notes and requests

- **Engine snowfall.** `engine/snowfall.js` also draws flakes. To avoid double snow, this module masks the engine's `engine_snowfall` points out of rendering (`layers.disableAll()`; the engine only toggles `.visible`). You can turn this off with `options.replaceEngineSnow = false`. **Request to the engineer:** skip `createSnowfall` when the lighting source is `'lighting'`; that also saves its 8k-point CPU update.
- **Light placement.** The engine places its own `light_` lights before `createLighting` runs. I re-tune them in place (`adoptEngineLights`). The cleaner path is for `main.js` to call `lighting.raw.placeLights(market.lightSpots, { focus, reserved })` after `createLighting`. It returns the same `{ lights, pools, cap }` shape.
- **Material names.** `gltf-transform optimize` with defaults palettises `bulb_warm` into `PaletteMaterial00x`. That is how the reference glb shipped, and the test page renames it. The architect and the carpenter already use `--palette false`. BUILD.md should require it, or `tuneEmissives` cannot find the bulbs.
- **Bulb emissive level.** Bulb emissive strength in the glbs varies (the reference ships 25). The lighting now sets one level for every bulb, so modellers do not need to tune it.
- **Global fog.** The fog chunk patch is global to three's `ShaderChunk`. Custom `ShaderMaterial`s with `fog: true` must define `mvPosition` in the vertex shader, as three's own chunks already require.
- **Nothing else breaks the contract.** I wrote only in `site/src/lighting/`, `review/round-1/lighting/` and my section of `CREDITS.md`.
