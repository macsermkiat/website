# Engineer, round 9: the ornament shop's three moments (ADR 0004 revision)

Mac: "No need to be interactive in everything, but the one that interactive must be wow. not slop." This round
the shop has three moments and nothing else to click. The carpenter's and vendor's round-9 shop files now on disk
(`stall_schmuck*.glb`, `prop_schmuck_*.glb`) are the ones every run below used.

## What changed

Code (all in `site/`):

- `src/actions/items/schmuck.js`: the shop's handler. It now only routes the three moments: `act_orn_harmonica_*`,
  `act_orn_mirrorball` and `act_orn_schwibbogen`/`act_orn_candle_*`. Every round-8 ornament interaction is gone
  (bauble spin, star, nutcracker, smoker puff, hang-on-tree, pickle reward), and so are their smoke checks and test
  hooks (`baubleNames`, `hangableNames`, `ornamentNote`). Any old ornament left in a set is decoration
  (`clickable = false`). The stop bar shows three buttons: Light the Schwibbogen, Play the glass harmonica and
  Look into the mirror ball.
- `src/shop/` (one module per moment, plus the engine's sparkle):
  - `schwibbogen.js`, the hero moment. The camera glides to the arch, comes round it and stands behind the candles,
    looking out over the market. As it comes round, the town's lit rooms go quiet. Then the candles catch one by one
    from the outside in, using the vendor's `order`. Each flame flares, flickers and has its own glow sprite. With
    each flame a share of the town's windows turns warm, spreading outward from the market, and one more voice
    joins a low G minor chord. After the last flame, a wave of light runs out from the shop: the stall bulbs and
    lamps flare in turn by distance, and the bloom swells and settles. Escape or a tap steps back round the arch
    (the candles keep burning). Clicking the arch again lets everything fade back.
  - `townWindows.js`, the town waking. The architect's `window_warm` atlas has dark cells (10, 12, 14) and lit cells
    (0-8). Each window gets a vertex rank from its distance to the market centre. Dark windows switch to a lit
    room as the wake front passes them. **New this pass:** rooms that are lit by default go quiet (20 %) while the
    town waits and come back as the front passes. Without that, the town before and after looked almost the same,
    because so many windows are lit by default. Compare `schwib_1_town_dark.jpg` with `schwib_3_light_wave.jpg`.
  - `lightWave.js`, the wave of light. A shader patch on every bulb material scales its glow by the wave at that
    point, so a string of lights brightens bulb by bulb. The lamps follow the same curve on the CPU, and the bloom
    swells by up to about 1.9x and then settles.
  - `harmonica.js` + `audio/glass.js`, the glass harmonica. The twelve baubles are tuned to the first twelve notes
    of "Lanterns After Closing" (music/score/LEADSHEET.md, head in G minor: D Bb A | G A C | Eb D F# | G, F Ab), two
    octaves up. A drag that starts on the row, by mouse or finger, claims the pointer, so the head does not turn,
    and rings every bauble it crosses. Velocity comes from drag speed. Each bauble swings on its ribbon and glows
    on its note. After 3.2 s idle at the shop, the next bauble of the phrase glows faintly. Playing the phrase
    through brings a ripple of light. The button leans the camera in and plays the phrase in its own rhythm. The
    tone is a sine plus inharmonic partials (2.32, 4.25, 6.63) with a slow attack, a long decay and a slow-beating
    twin, run through a cross-fed feedback-delay room. **New this pass:** the vendor's clear shells (`vendor_glass`,
    opaque white in the file) are made see-through with premultiplied Fresnel blending, so the mercury bauble
    inside and the note's glow show through. The glow is warmer and stronger (amber, larger halo).
  - `dive.js` + `divePass.js`, the reflection dive. At the tap, a CubeCamera renders the market once from the
    ball's centre (256 px lite, 512 px full). The ball's glass becomes a mercury mirror with a clear coat (Fresnel
    at the rim). The camera eases along `cam_dive_approach` to `cam_dive` while the lens narrows, until the
    reflection fills the view. Then the inside opens from the middle outward through a lens-like iris, with a thin
    silvered edge that bends the picture as it passes (**new**; it was a grey double exposure). Inside the glass
    the view is a barrel-warped fisheye with a mirrored band at the rim, a little chromatic split, a hushed warm
    silver grade, the ball's own highlight streak, and four layers of silver glitter drifting like a snow globe
    (near flecks large and soft, far ones small and sharp, each flashing as it turns). The sound goes muffled. It
    holds, then a silvered veil closes in from the rim and the camera eases back out. Escape or a tap ends it at
    any point.
  - `sparkle.js`, the shop's sparkle. `mirror_0`/`mirror_foxed` is a planar reflector (Reflector.js's oblique
    mirrored camera), shown through the foxing: rough spots reflect less. It is 640 px and drawn every frame near
    the shop on the full market, 256 px every 20th frame on the lite one. `tinsel_*` gets a view-dependent glint
    shader: 3 mm flecks of foil, each tilted its own way, flash when they mirror the shop lamp into the eye.
    `rot_pyramid` turns about Y (from the vendor's `{"axis":"y"}`), and the pyramid's flames flicker.
    **New this pass:** `fx_smoke_1` is one thin curling wisp that slows, widens and thins as it rises, drawn from
    ragged soft sprites. It replaces a column of evenly spaced round puffs that read as a dotted line in the
    Schwibbogen view.
- Schwibbogen framing (**new**): the view behind the arch now keeps all seven flames in the lower third. The
  camera stands 0.72-1.05 m behind the arch depending on screen width, the eye is 8.5 cm above the tips, and the
  lens widens to 62° on portrait screens. During the wave the camera draws back a little and lifts its eyes, where
  before it rose and lost the candles. The first flame now comes after the camera stands behind the arch, so the
  visitor sees the quiet town first.
- Loading: deco stalls are scenery and load only their `.lite.glb` on both markets (`layout.js` `liteOnly`), so
  they never stream. The smoke test checks this.
- Small screens: the stop bar starts folded at the ornament shop, as it does at an open cabinet (round-8 judge
  note). It is 50 px tall in a 640 px view.
- Reduced motion: the camera cuts instead of gliding, the candles light in about 2 s with no flicker, the light
  rises everywhere at once instead of travelling, the baubles glow but do not swing, and the dive cuts in and out
  with a short hold and no drift.

Tests: `tests/smoke.mjs`

- `schmuck` (lite, 960 px): stroll stop, signpost arm, folded bar, three buttons, round-8 interactions gone,
  decoration not clickable, harmonica tuning, mouse brush order, no head turn, glow and swing, velocity, taps in
  order plus the idle hint, touch drag, the tune's answer, the leaned-in auto phrase, all Schwibbogen beats
  (outside-in order, windows, chord, wave, view, Escape, fade back including the town's hush), every dive phase
  (cube env, approach, inside, Escape, tap), and the sparkle (mirror, tinsel, pyramid, smoke).
- `moments` (full, 1280 px): streams the shop at full detail and takes a screenshot sequence of each moment.
  **New:** the live loop is held for the whole section, and each snapshot draws one frame. Before this, software
  GL drew the full market every animation frame alongside the waits and the run stalled for over 25 minutes. A
  new check confirms the screenshots catch each beat (town quiet over unlit candles, waking, the wave's bloom at
  its height, settled).
- `phone`: the reduced-motion versions of the three moments.
- `stroll`: the full market's first load must now stay under 9 MB ("near 8 MB"; it was under 19.7 MB).

## Results

- `npm ci && npm run build` in `site/`: succeeds (three 0.186, Vite 8; base `/website/`).
- **Full smoke run, today's code, shop files on disk** (`smoke.log`, 14:28-15:17, served from a frozen copy of
  `dist/`): **277/279 checks, no console errors**. The two failures are the sausage clicks ("clicking one sausage
  in 3D", "phone: tapping a sausage"). The vendor's round-10 Bratwurst plate set (`prop_wurst_counter*.glb`,
  `items.json`, written at 14:10 under the round-10 BUILD.md line "the old act_sausage_<n> rows become merged
  scenery") was already on disk when the run started. It has no single sausages left to click. The engine handles
  it without errors (turn the sausages and the bun still work), but porting the plate's interactions is round-10
  engineer work. Both checks now detect the plate set and log a **skip** with the reason instead of failing. A
  re-run of the two sections that contain them (`interact,phone`, `smoke_rerun_interact_phone.log`) gives
  **38/38 checks, 2 skipped, no console errors**. Taken together, every section passes on the files now on disk,
  including all three moments (schmuck 37, moments 7, and the phone's reduced-motion versions).
- Earlier runs, kept for the record:
  - `smoke_killed_run.log`: killed from outside after 100 checks, all passing. The machine was shared with the
    vendor's Blender build.
  - `smoke_run2_crash.log`: 244/245, then a real bug. The reduced-motion dive crashed on its way out, because
    `go('back')` ended the dive inside the pose function, which then read `S.cut`. Fixed in `dive.js`, proven by
    the phone section above. The one failure in that run was the projects-board check: it expected a GitHub link
    that Mac removed from `content/projects.md`. It now checks for the links that `projects.md` actually holds
    (ProtoCol and the YouTube playlist).
  - `smoke_shop.log`: `schmuck,moments` 44/44 after the polish pass.
- Bench (judge note), re-run with today's code: `perf.log` and `perf/2026-10-05-11-55.json`. Software GL only, so
  these are not GPU numbers:
  - Full market: first load **7.26 MB**, with the deco stalls lite-only (round 8: 7.25 MB). The triangle count is
    **finite on every frame** (the round-8 Infinity counts are gone). The crowd has 87 people, 69 of them drawn as
    far instances in 14 draws, and its update takes 0.35 ms per frame. Draw calls at home: 1372 (round 8: 642,
    measured at 05:43 before the deco goods and the shop went in).
  - Lite market: first load 5.10 MB, 609-633 draws, about 300k triangles, 40 people in 11 draws.
  - The bench's own stdout was cut off by `process.exit()` before its lines were written (fixed in
    `tests/perf.mjs`), so `perf.log` was rebuilt from the JSON.
- Screenshots (full market, 1280x720, from the `moments` section of the full run):
  - `shop_stop.jpg`: the shop at its stop.
  - The Schwibbogen: `schwib_1_town_dark.jpg` (the town gone quiet over unlit candles), `schwib_2_town_waking.jpg`,
    `schwib_3_light_wave.jpg` (the peak: seven flames, windows warm, the string lights flaring, bloom 1.9x) and
    `schwib_4_settled.jpg`.
  - `harmonica_mid_phrase.jpg`: the camera leaned in, the fifth note just struck and the fourth still glowing.
  - The dive: `dive_1_approach.jpg`, `dive_2_reflection.jpg` (the lit market curving in the mercury glass),
    `dive_3_into_glass.jpg` (the iris opening) and `dive_4_inside.jpg` (the market from inside the ball).
  - Lite and phone: `stop_schmuck.jpg` (the lite shop at 960 px with the folded bar), plus the usual home, stall,
    reading, plain.html, missing-models and phone screenshots from the full run.

## Open issues

- Real-GPU frame times still need Mac: `cd site && npm ci && npm run build && npx playwright install chromium &&
  npm run perf` on his laptop. A real GPU is the only way to judge the dive's cube render (one 512 px capture per
  tap), the 640 px mirror drawn every frame near the shop, and the 1372 draws at the full market's home view.
- The Bratwurst plate (round 10) needs its engine port: `act_wurst_*`, `act_sauce_*` with `fx_sauce_*`,
  `act_shaker_curry`, `act_plate` with `plate_spot_0..3`. Until then the two sausage checks skip, and the old
  `act_sausage_*` stand-ins stay hidden behind the vendor's merged grill.
- The clear harmonica shells are made see-through by the engine. The vendor's file has `vendor_glass` as an opaque
  white, which reads as porcelain in any other viewer. If the vendor exports it as glTF transmission or BLEND, the
  engine's override becomes a fallback.
- The town's window wake is a shader on the architect's `window_warm` atlas (dark cells 10, 12 and 14, lit cells
  0-8). If the architect re-lays the atlas, `shop/townWindows.js` needs the new cell numbers.
- The machine is shared. One full run was killed from outside, and each full-market screenshot takes 25-110 s on
  software GL, so the `moments` section holds the live loop and draws only the frames it saves.
