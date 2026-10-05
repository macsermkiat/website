# Engineer, round 9: the ornament shop's three moments (ADR 0004 revision)

## Pass 2: the judges' fixes

1. **One clean full smoke run, with the Bratwurst plate ported and tested instead of skipped.** `smoke.log` (16:42-17:53 UTC, every
   section, served from a frozen copy of today's `dist/`, against the shop and plate files now on disk): **291/291
   checks passed, no console errors, nothing skipped.** After the run had started I made two edits to `tests/smoke.mjs` that change no check:
   I deleted the unused skip helper, and I renamed the wave-frame check (its logic, with the ground band, was already
   in the run). So the log shows that check's old name.
   - The two half-finished plate ports left by the interrupted pass are now one, in `src/actions/items/wurst.js`
     (with `grillSausages.js` beside it). `src/actions/items/plate.js` is deleted, and nothing in `src/` refers to
     `act_sausage_`, `act_bun` or the old stand-in rows any more.
   - It follows the ADR 0004 revision "Bratwurst plate instead of many sausages" and the vendor's round-10 set
     (`prop_wurst_counter*.glb`, `items.json`):
     - Tap a kind (`act_wurst_thueringer`, `_nuernberger`, `_krakauer`, `_curry`) or the Brötchen (`act_roll`):
       a fresh copy arcs onto `act_plate` at the next free `plate_spot_0..3`, four at most. The one on the board
       stays. A fifth gets "The plate is full". A Thüringer or Krakauer tapped while an empty Brötchen waits goes
       into it.
     - The three bottles (`act_sauce_senf`, `_ketchup`, `_curry`) lift, turn over above the plate and pipe a glossy
       squiggle from their `fx_sauce_` nozzle. The squiggle is a tube draped over the food and drawn in as it is
       piped. The tin (`act_shaker_curry`) dusts curry powder from `fx_shaker_curry`.
     - Tap the plate to hand it over the counter: "Guten Appetit", and a fresh plate is set out.
     - The buttons stay: "One in a bun, please" (a roll, a Thüringer into it, Senf) and "Mix me a plate" (a kind and
       a sauce).
   - **Turning the sausages still works.** The vendor merged the ten grill sausages into one mesh
     (`sausages_grill`, riding `act_grill_swing`). At load, `grillSausages.js` cuts that mesh into its sausages
     (connected pieces welded by position, small touching pieces joined to their sausage). Each piece shares the
     merged vertex buffers and has its own index, so the GPU holds the vertices once. The "Turn the sausages" button
     turns the whole grate in a ripple, each sausage hopping over about its own long axis as tongs would turn it.
     They are not clickable one by one (ADR 0004).
   - The smoke test now checks all of this in the `interact` section (14 Bratwurst checks, in place of the 2 that
     skipped in pass 1):
     - the plate set is present and the three buttons are there;
     - turn the sausages: every sausage on the grate turns over exactly once, and none is clickable on its own;
     - a sausage in a bun;
     - a click in 3D on the Krakauer puts a fresh one on the plate;
     - sauces and curry powder, and the sauce squiggle's geometry;
     - four at most;
     - a click in 3D on the plate clears it ("Guten Appetit");
     - mix me a plate.
     The `phone` section taps a Thüringer onto the plate in reduced motion. Screenshot: `stop_bratwurst_plate.jpg`.
2. **The market light wave reads in a still frame.** Three changes in `src/shop/lightWave.js`:
   - **The light runs over the ground.** The square's cobbles, setts, granite bands and puddles (the architect's
     `square.glb` materials, or a stand-in `ground` mesh) get a shader patch. Where the wave is passing, it adds
     warm light to their own colour, so the setts keep their pattern. It is a band about 8 m across that peaks
     7 m behind the front, with a slightly ragged edge, as light finds its way between the stalls. Behind it the
     ground keeps a faint warmth while the candles burn. The band fades out by the square's edge and does not light
     the ground under the arch. Reduced motion: one gentle rise everywhere at once.
   - **The market waits in the dark.** While the candles light, the market's bulbs dim to 30 % and its lamps to
     45 %, with the town. The wave then relights them as it passes, so a frame shows lit behind the front and dim
     ahead of it. (This went in at the start of this pass, before the restart.)
   - **A bigger bloom swell:** up to 3.1x at its height (pass 1: 1.9x), rising and settling over 6 s. The bulbs
     flare to 3.6x as the front passes (pass 1: 2.6x), and the front moves at 7 m/s (pass 1: 11), slow enough to
     follow.
   - **The screenshot is timed by the wave itself.** `schwib_3_light_wave.jpg` is taken 3.1 s after the wave
     starts. The front is then 22 m out and the warm band on the cobbles lies across the square at the stalls. The
     near ground is back to a glow, the far ground and the far strings are still dim, and the bloom is near its
     height. Compare it with `schwib_2_town_waking.jpg`, where the market is hushed, and `schwib_4_settled.jpg`.
   - New checks:
     - `schmuck`: the wash reaches the cobbles, peaks, settles to a faint warmth and is zero before the wave.
     - `moments`: the wave frame has the band on the ground at 14 m, the near bulbs flaring and the far ones dim.
3. **Committing:** my brief from the session that started me says not to run git commit or push, because that
   session does it. Everything the judges listed is on disk for it: `tests/smoke.mjs`, this file, the logs and the
   screenshots. The pass-1 logs are moved to `pass1/` (staged as renames) so that `smoke.log` is this pass's clean
   run.
4. **Real-GPU numbers** need Mac (see Open issues). I can't measure them on this machine: it has no GPU.

---


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
    swells (pass 2: up to 3.1x) and then settles. Pass 2 adds the hush and the warm band on the cobbles (see above).
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
- **Full smoke run (pass 2), today's code, shop and plate files on disk** (`smoke.log`, 16:42-17:53 UTC, served
  from a frozen copy of `dist/`): **291/291 checks, no console errors, nothing skipped**. Per section:
  - interact: 40, including the 14 Bratwurst checks;
  - schmuck: 38, including the new wash check;
  - moments: 8;
  - the rest as in pass 1, all passing: unit, stroll, reading, cabinet, lite, phone (with the plate tap and the
    reduced-motion moments), plain, missing, audio.
  - First load: full market 7.29 MB (limit 9 MB), lite 5.19 MB.
- Pass-1 runs, kept for the record in `pass1/`:
  - `pass1/smoke.log`: 277/279. The two sausage clicks failed against the vendor's round-10 plate set, which landed
    mid-round.
  - `pass1/smoke_rerun_interact_phone.log`: 38/38 with 2 skipped.
  - `pass1/smoke_killed_run.log`: killed from outside after 100 checks, all passing.
  - `pass1/smoke_run2_crash.log`: 244/245, then the reduced-motion dive crashed on its way out. That was fixed in
    `dive.js` in pass 1.
  - `pass1/smoke_shop.log`: `schmuck,moments` 44/44.
- Bench (judge note), re-run with today's code: `perf.log` and `perf/2026-10-05-11-55.json`. Software GL only, so
  these are not GPU numbers:
  - Full market: first load **7.26 MB**, with the deco stalls lite-only (round 8: 7.25 MB). The triangle count is
    **finite on every frame** (the round-8 Infinity counts are gone). The crowd has 87 people, 69 of them drawn as
    far instances in 14 draws, and its update takes 0.35 ms per frame. Draw calls at home: 1372 (round 8: 642,
    measured at 05:43 before the deco goods and the shop went in).
  - Lite market: first load 5.10 MB, 609-633 draws, about 300k triangles, 40 people in 11 draws.
  - The bench's own stdout was cut off by `process.exit()` before its lines were written (fixed in
    `tests/perf.mjs`), so `perf.log` was rebuilt from the JSON.
- Screenshots (full market, 1280x720, from the `moments` section of the pass-2 full run):
  - `shop_stop.jpg`: the shop at its stop.
  - The Schwibbogen: `schwib_1_town_dark.jpg` (the town gone quiet over unlit candles), `schwib_2_town_waking.jpg`,
    `schwib_3_light_wave.jpg` (pass 2: 3.1 s into the wave, the warm band on the cobbles across the square at the
    stalls, the near strings flaring, the far ones still dim, bloom 3.1x) and
    `schwib_4_settled.jpg`.
  - `harmonica_mid_phrase.jpg`: the camera leaned in, the fifth note just struck and the fourth still glowing.
  - The dive: `dive_1_approach.jpg`, `dive_2_reflection.jpg` (the lit market curving in the mercury glass),
    `dive_3_into_glass.jpg` (the iris opening) and `dive_4_inside.jpg` (the market from inside the ball).
  - Lite and phone: `stop_schmuck.jpg` (the lite shop at 960 px with the folded bar), plus the usual home, stall,
    reading, plain.html, missing-models and phone screenshots from the full run.

## Open issues

- **For Mac (judges' item 4): real-GPU frame times.** On his laptop, run `cd site && npm ci && npm run build &&
  npx playwright install chromium && npm run perf`. It writes `perf.log` and a JSON file to
  `review/round-9/engineer/perf/`. Three things need a real GPU to judge:
  - the 1372 draws at the full market's home view;
  - the 640 px mirror target drawn every frame near the shop;
  - the dive's 512 px cube capture per tap.
  The bench on this machine is software GL and can't stand in for it. If the mirror is costly, the fix is ready to
  make: refresh it every few frames, as the lite market does.
- The ground wash patches the square's materials by name (`cobble*`, `setts*`, `granite_bands`, `puddle*`). If the
  architect renames them, the wave still runs over the bulbs and lamps, but not over the ground; the `schmuck`
  wash check will then fail and say so.
- The grill's sausages turn by cutting the vendor's merged `sausages_grill` mesh into its connected pieces at load.
  If a later export welds two sausages together, they turn as one, and the check that every sausage turns once
  still passes.
- The clear harmonica shells are made see-through by the engine. The vendor's file has `vendor_glass` as an opaque
  white, which reads as porcelain in any other viewer. If the vendor exports it as glTF transmission or BLEND, the
  engine's override becomes a fallback.
- The town's window wake is a shader on the architect's `window_warm` atlas (dark cells 10, 12 and 14, lit cells
  0-8). If the architect re-lays the atlas, `shop/townWindows.js` needs the new cell numbers.
- The machine is shared. One full run was killed from outside, and each full-market screenshot takes 25-110 s on
  software GL, so the `moments` section holds the live loop and draws only the frames it saves.
