# Engineer, round 8: the fuller market, the ornament shop, the book cabinets (ADR 0004)

This pass continues the earlier round-8 engineer pass, which stopped early. Its work is in `fa3da3d`, and its last
smoke run passed 26 of 29 checks. I finished the work from there and did not start over. I committed nothing; the
session that started me commits.

## Pass 3: the judges' fixes

Result: **the full smoke run passed 242/242 checks with no console errors** (`smoke.log`). This run comes after every
fix in this pass and in the last one, and it covers every section. It ran against the models on disk now, which
include the vendor's round-9 ornament shop (more on that below). `npm run build` succeeds. I committed nothing myself.
While I worked, the session that started me committed pass 2 as `3e645c8` and this pass's site changes in
`fa50fa8`. The only thing left uncommitted is this review folder: these notes, the logs and the screenshots.

1. **The stop bar folds away on small screens** (`ui/stopbar.js`, `index.html #stopFold`, `main.css .stopbar.folded`).
   - When the screen is 640 px wide or less, or 720 px tall or less, and a stop's bar would take more than a fifth
     of the view's height, its buttons fold into one **Things to do (n)** button. The bar then shows back,
     the stop's name, that button and on.
   - It uses `aria-expanded` and `aria-controls`. Once a visitor opens it, it stays open at later stops.
   - On the round-8 ornament set at 960×640, the bar starts folded and is 50 px high. Before, it covered the
     lower third of the shop. See `stop_schmuck_round8_set_folded.jpg`.
   - The vendor's round-9 set has only two buttons here, so its bar fits on one row and does not fold
     (`stop_schmuck.jpg`).
   - The smoke test checks four things: the bar stays under 15 % of the view, it starts folded when there are six
     or more buttons, Things to do opens every button, and it folds again. Clicks on the stop bar go through
     a `tapAct` helper, which opens a folded bar first.
2. **Step back from an open cabinet keeps the view turned toward that cabinet.**
   - `books.js backView()` gives the view from the stop, aimed at the open cabinet. `guide.back()` flies there
     instead of to the straight-on view.
   - That cabinet then counts as the one faced, so ‹ › carry on from it.
   - New smoke check at 390 px: after Step back, the same cabinet is faced, on screen (x = 228 of 390), and the view
     is no longer a close-up.
3. **Why three.js counted infinite triangles, now fixed.**
   - troika's glyph geometry is an `InstancedBufferGeometry`, and its `instanceCount` starts at `Infinity` until
     the text's first glyph sync.
   - three caps a draw's instance count with `_maxInstanceCount`. That value comes from the geometry's instanced
     attributes, and the geometry has none until the first sync. So the first draw of a new text block calls
     `info.update(6, TRIANGLES, Infinity)`, and the frame's count becomes Infinity. Nothing is drawn: WebGL turns
     Infinity into 0.
   - I traced it by wrapping `renderer.info.update` in the page. The culprit was the `engine_text_label` meshes
     made by `label()` (stand-in labels, the pickle's words). The write_ surface texts had the same problem.
   - Fix: `world/text.js newText()` makes every troika Text with `geometry.instanceCount = 0`. Each glyph sync sets
     the real count.
   - The bench no longer hides a bad count. `perf.js` counts non-finite frames (`badTriangles`), the bench prints
     them, and a new smoke check needs 0 (it got 0 in 8 frames, with streaming and a text opened and closed).
4. **The full run after the phone fixes**: 242/242 (see above). The cabinet section includes the stop bar hiding
   with a cabinet open, the softer light and the stricter cover check.
5. **The vendor's round-9 ornament shop arrived during this pass.**
   - Under the ADR 0004 revision, only three things in the shop are interactive: `act_orn_harmonica_0..11`, a
     row of twelve baubles; `act_orn_mirrorball`; and the Schwibbogen. Its files replaced the round-8 set in
     `site/public/models`.
   - I did not start round 9's features. `schmuck.js` now works with either set:
     - the harmonica baubles ring like the round-8 baubles, each with its own note, and the button reads "Play
       the glass harmonica"
     - the mirror ball spins and rings a low G4 until the round-9 camera dive is built
     - the stop bar offers only the interactions whose parts the set has
   - The smoke test follows the set: every interaction whose parts exist must pass, the bar must offer nothing the
     set lacks, and it logs what is missing. On the round-9 set, ring and candles run. Star, nut, smoke, hang and
     pickle are not in it.
   - So that the round-8 interactions are still proven, I ran the shop section against the round-8 models from
     `fa3da3d` on today's code: **19/19, no console errors** (`smoke_schmuck_round8_set.log`). That covers ring,
     nut, smoke, candles, hang (now on an ornament that can hang, since that set's baubles cannot) and the
     pickle, plus the fold checks. The Herrnhut star is not in that set.

## Pass 2 results



- `npm ci && npm run build` in `site/` succeeds.
- **Smoke run** (`smoke.log`): **245/245 checks passed with no console errors.** It covered every section: unit,
  stroll, reading, interact, schmuck, cabinet, lite, phone, plain, missing and audio. The run served a copy of
  `dist/` (`--dist`), so a rebuild during the run could not change it.
- After that run I made two small phone fixes (listed below). I re-ran the cabinet section on the new build:
  `smoke_cabinet_rerun.log`, **15/15 passed with no console errors**.
- **First load** (bytes fetched before the market opens, measured in the browser):

  | Market | Smoke run | Bench | Aim | `scripts/budget.mjs` estimate |
  |---|---|---|---|---|
  | Full | 7.33 MB | 7.25 MB | about 8 MB | 8.32 MB |
  | Lite | 5.23 MB | 5.14 MB | about 6 MB | 6.22 MB |

- **Bench** (`perf.log`, `perf/2026-10-05-05-43.json`, run with `npm run perf -- --software --size 960x600`):
  - Full market: 87 people. At the last view (home), 5 of them were drawn as far instances. 27 skinned mixers ran
    and 55 were throttled. The crowd's own update took 0.74 ms per frame.
  - Lite market: its 40 people, all drawn as far instances at the home view, in 11 draws. The crowd update took
    0.29 ms per frame.
  - Frame times were logged for every view. They come from SwiftShader on a shared 4-CPU machine (load average
    6 to 10), so they are **not a GPU measurement**, and the bench exits with code 2 to say so. The real frame-time
    check is still `npm run perf` on Mac's laptop.

## What this pass changed

1. **Ornament shop, the one failing check.** The check that `stall_schmuck.glb` is loaded for `deco-schmuck` read
   `report.models` the moment the market opened. On a fast load the shop had not been placed yet, because it is one
   of the models placed just after the first frame. The check now reads the report once the visitor has arrived at
   the shop. The model and the stop were already correct.
   - The hang-on-the-tree check, which failed in `r8_new.log`, passes now.
   - All seven interactions pass:
     - ring: each bauble has its own note, C5 to C8
     - the Herrnhut star lights
     - the nutcracker's jaw opens
     - the Räuchermännchen puffs smoke
     - the Schwibbogen candles light one by one
     - an ornament hangs on a free hook and goes back to its rail
     - finding the pickle plays a chime and shows a line of words in the scene, which goes after about 7 s
   - A click in 3D on an ornament works.
2. **Book cabinets on a 390 px phone.**
   - From the Bücherstand stop, the stall's front is about three screen-widths wide on a phone. None of the six
     cabinets was on screen, so a cabinet could not be tapped. That was the cause of the failing tap check.
   - New: on narrow screens (640 px or less), **‹ › buttons beside the stall** (44×56 px) turn the visitor's head
     from where they stand to the next or previous cabinet, left to right. The cabinet then sits above the bar of
     things to do. One tap on the cabinet or its sign opens it.
   - Code: `books.js turnCabinets` / `facedCabinet`, `main.js` `stopEye` / `turnTo`, `index.html` `#cabTurnL/R`,
     `main.css .cabturn`.
   - A cabinet opened by a tap or a stop-bar button no longer puts keyboard focus on its first book. ↓ / ↑ still
     focus the first book. This fixes the failing ← → check.
   - With a cabinet open on a phone, the stop bar steps aside (`html[data-cabinet] .stopbar`). Before, it hid the
     bottom row of covers. Step back stays on screen.
   - The lite key light, when turned to a cabinet, is now softer (30 %) and further off. The pale face-out covers
     had been washing out to white. Compare `phone_cabinet_open.jpg`: the titles now read.
   - The smoke test checks all of this:
     - the turn buttons are there
     - the cabinet is in view after the turn and at least 44 px
     - the tap lands on the canvas, not on a bar over it
     - each cover is at least 44 px and in view, now also not under the stop bar, the read bar or the signpost
     - ← →, ↓ ↑, a tapped cover opens its book, Escape, Step back
     - with the cabinet shut, its books no longer answer the pointer
3. **The bench could not finish on software GL.** The perf tour only counted frames shorter than 2 s, so on
   SwiftShader it never gathered its 10 samples per view. It now keeps every frame during the tour (`perf.js`).
   - three.js reports `Infinity` triangles on a frame where a troika text block draws before its glyph count is
     known. The meter now keeps the last finite count instead.
4. **Already done in `fa3da3d` and checked again this pass:**
   - Crowd: about 80 people (`crowd.json`, 87 plus 4 musicians), a vertex-animation far crowd beyond about 25 m
     (`crowdFar.js`), and skinned people beyond 12 m / 18 m updated every 2nd / 3rd frame.
   - Deco stalls are scenery:
     - `actions/items/deco.js` and the deco fly-to are removed
     - a deco stall only stops the pointer
     - there is no deco stop and no close-up
     - only their lite files load, even on the full market, and they never stream
     - the smoke test's stroll section checks all of this
   - The ornament shop is a stroll stop between the Bücherstand and the Karussell, with signpost arm 8.

## Screenshots (this folder)

- `home_signpost.jpg`: the home view on the full market.
- `stop_schmuck.jpg`: the ornament shop stop on the vendor's round-9 set: a one-row bar with the harmonica and
  the candles, and the Schwibbogen's note.
- `stop_schmuck_round8_set_folded.jpg`: the same stop on the round-8 set at 960×640. The bar is folded to
  "Things to do (6)" and the pickle's words are in the scene.
- `phone_cabinet_open.jpg`: an open cabinet on a 390 px phone.
- `plain_html.jpg`: the text version of the site.
- The rest are from the same run: the reading views, both rides, the lite home, the phone, and every model
  missing (stand-ins).

## Open issues

- **Mac: please run `npm run perf` on your laptop.** That is the only way to get real GPU frame times for the
  87-person crowd. Every frame time in `perf.log` comes from SwiftShader on a shared CPU. The bench now also says
  whether the triangle count stayed finite.
- Round 9 interactions are not built yet: harmonica baubles tuned to the ballad's melody, the mirror-ball camera
  dive (`cam_dive`), the `rot_pyramid` spin, the tinsel glint and the foxed mirror. Today the harmonica rings
  a scale and the mirror ball spins.
- The vendor's round-9 shop files were committed in `fa50fa8` after this run started. If they changed after the
  run, which used the files on disk at about 08:20, the shop section (`node tests/smoke.mjs --only schmuck`) should
  be run again.
