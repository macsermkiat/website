# Engineer, round 8: the fuller market, the ornament shop, the book cabinets (ADR 0004)

This pass continues the earlier round-8 engineer pass, which stopped early. Its work is in `fa3da3d`, and its last
smoke run passed 26 of 29 checks. I finished the work from there and did not start over. I committed nothing; the
session that started me commits.

## Results

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
- `stop_schmuck.jpg`: the ornament shop stop, with its stop bar and the pickle's note.
- `phone_cabinet_open.jpg`: an open cabinet on a 390 px phone.
- `plain_html.jpg`: the text version of the site.
- The rest are from the same run: the reading views, both rides, the lite home, the phone, and every model
  missing (stand-ins).

## Open issues

- Real-GPU frame times for the 80-person crowd are not measured yet. Mac should run `npm run perf` on his laptop.
- The ornament shop's stop bar and its notes cover the lower third of a 960×640 view (see `stop_schmuck.jpg`).
  This is fine for play, but it could fold away on small screens the way the Bücherstand's does while a cabinet is
  open.
- A turn toward a cabinet is part of the stop view, so Step back from an open cabinet returns to the stall's
  straight view, not to the turned one.
