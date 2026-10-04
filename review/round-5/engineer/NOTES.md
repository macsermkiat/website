# Engineer, round 5: the guided stroll, words written in the market, streaming

Mac asked for this: *"Market signpost is interesting, the camera just follow along the path. Also I don't want the
text as a separate component windows from the market. It should be in the environment. For example, when click
the book, it show the book with written text inside. Same as wineshop, beer shop."* The work follows ADR 0003.
Nothing is committed by me; the session that started me commits.

## Pass 2: the panel's fixes

All five are done. Previews re-rendered; the old ones are replaced.

1. **The Bierdeckel back is printed on the coaster.** The grey rectangle was the vendor's `write_coaster_<i>_back`
   card (material `write_card`, its own grain texture) lying over the coaster, which is one double-sided surface.
   From behind it showed the front's print mirrored, with that card on top.
   - The back now gets a round card face of its own (`engine_coaster_back`), as round as the coaster and just
     inside its rim. It uses the coaster's own material, with every UV at one plain point of its print, so it is
     the same card, unprinted. The `write_` back card is hidden.
   - The front's `write_` card filled the opening the vendor left in the print. It now takes the print itself:
     at each corner, the UVs (both sets, colour and baked occlusion) of the coaster's vertex there. The print
     runs on unbroken under the words (`world/surfaces.js` `printOnto`, `cardBack`).
   - The words are centred inside the disc (`fitRound`). The front stays inside the printed ring, the back inside
     the rim. Type on the back shrinks, within a range, so a description fits on one side.
   - When the full model is grafted on (`engine/stream.js`), the coaster dresses itself again from the full print
     (a new `afterGraft` hook).
   - The smoke test checks it: front printed, back card hidden, round back face, and words reaching at most 0.71
     (front) and 0.91 (back) of the radius.
   - The reading camera frames the whole coaster, so its round edge is in the picture.
2. **The text sits on crafted props.**
   - **`book_open.glb` is the book that opens** (`src/actions/items/bookOpen.js`).
     - The model is fetched once: on the way to the Bücherstand, or 12 s after the market opens.
     - Its static mesh is split at the spine, and the left half (with its page and cover) is hinged, so the
       vendor's book flies closed from the shelf, opens on the counter, and closes again.
     - The clicked book's own cover goes onto `book_open_cover`, from `cover_uv` in items.json.
     - The words go on `write_page_left/right`. A turn swings `act_page_turn`, carrying the old right page on
       its front and the new left page on its back (`write_page_turn_front/back`).
     - The reading camera comes from `cam_read_book`, drawn back as far as the screen's shape needs.
     - The pages had the coaster's problem: a lighter, then (without the occlusion UVs) a darker card in the
       page's opening. They now take the paper's own print the same way.
     - If the model is missing or late (5 s), the engine's own book opens as before.
   - **The models' `write_`/`cam_read_` nodes carry the words wherever they exist.** The engine knew different
     names from the ones the carpenter and the ride builder chose, so the table now has aliases:
     - Glühwein `about`
     - Bier `projects_board`
     - Bratwurst `writing_menu` and the vendor's `writing_paper`
     - Bandstand `music`
     - Riesenrad `questions_board`, and `question_1..3` on the gondolas (the placards)
     - Karussell `contact`

     Seven of eight surfaces are now the models' own, and the placards are the wheel's own. Only the Bücherstand
     reading card is still a stand-in: no `write_` node for it exists yet.
     - A model surface gets type fitted to its size (the largest size, between a twelfth and a thirtieth of its
       height, that fits one page; `reader.js` `pagesFor`).
     - The camera comes from the maker's `cam_read_` side, aimed at the middle of the writing, and steps back
       if a narrow screen needs it.
     - A paper surface brightens a little while read.
     - The tests list which surfaces are the models' own (`unit.mjs`, `smoke.mjs`).
3. **The hover label stays inside the canvas.** `picking.js` slides it in from an edge, drops it below the pointer
   near the top, and caps its width (with an ellipsis) at the canvas width. The smoke test hovers the signpost
   arm nearest the right edge and checks the label's box.
4. **The lite first load has a wide margin, and a gate keeps it.**
   - The town ring is not in the first load any more. It comes just after the first frame with the rides and the
     deco stalls (`main.js` defer), on both markets.
   - Its three `light_` empties stay glows, as before, so the rides keep the two real-time lights held for them.
   - The home still now stays up until that part is in (at most 4 s), so the fade shows no gap where the town and
     rides will stand.
   - Lite first load: **6.12 MB** (round 4: 7.44 MB, margin 1.32 MB; pass 1 counted the same way today: 7.32 MB).
     Full: **8.20 MB** (round 4: 19.70 MB).
   - **Gate:** `npm run budget -- --strict` now also fails when either first load is not below round 4's. The
     Pages workflow already ran it before upload; the step is now named "Budget gate", so a regression stops the
     deploy. `--town-first` counts the old way.
5. **The still is recaptured, and the hint.**
   - `public/stills/home.webp` is a new frame of this build (the current lighting, the delivered models, the town
     and rides in). `npm run still` (`tests/capture-still.mjs`) recaptures it in one command after the next
     lighting or layout change; then build again.
   - The writer's hint I could not change: `content/` is the writer's (BUILD.md ownership). The page shows the
     stroll's own hint, and `plugins/market.js` skips the old orbit hint. When the writer adds `ui.stroll_hint`
     to `content/site.md`, it wins. Suggested text: *"Choose a place on the signpost, or press 1 to 7, and walk
     there; the arrows walk on to the next stall. Every stall's words are written in it: click a board, a
     Bierdeckel or a book, or press Enter, to read. Sound starts only when you press play."*


## What changed (pass 1, updated where pass 2 changed it)

### 1. A guided stroll; the free orbit is gone

- **No orbit** (`src/interaction/camera.js`, rewritten). The camera rig has five modes: `home`, `walk`, `fly`,
  `stop` and `ride`.
  - The home view sways slowly, like someone at the edge of the square shifting their weight.
  - At a stop, or at home, a drag turns the head at most ±15° (±9° up and down). The wheel or a pinch zooms only
    within 0.82–1.12.
  - Reduced motion turns every walk into a cut, and the home view holds still.
- **The signpost walks the camera.** Clicking an arm (`act_sign_<id>`) on the carpenter's new `signpost.glb` walks
  the camera along the architect's path to that stop. So do the on-screen copy of the signpost (top left, folded
  into one button on phones) and keys 1–7.
  - The walk follows a centripetal Catmull-Rom curve through the architect's leg (`layout.json`
    `stroll.legs`, one leg for every pair of stops).
  - Walking speed is 3.2 m/s, with ease in and out, and a walk lasts 2.2–9 s.
  - The eyes look ahead along the path and slightly down. Over the last 45% of the walk they turn toward the
    stop's target.
  - A walk that starts from a close-up, a page or the top of the wheel joins the leg from wherever the camera is.
- **The loop.** ← and → (and the small arrows in the stop bar) walk to the previous and next stop, in the
  architect's order: Glühwein, Riesenrad, Bratwurst, Musik, Bier, Karussell, Bücher. Esc steps back, and 0 or
  Home returns to the overview.
- **The Riesenrad stop is the overview.** The walk ends at the foot of the wheel, and the camera then rises over
  about 4 s to the architect's `overview`, the view from the top gondola.
  - I move that eye 4.5 m out along its view, because at the exact spot the rim and spokes filled the picture
    (`stroll.js` `OVERVIEW_OUT`).
  - Above 12 m the exposure opens up, as it already did on the ride (`main.js`).
- **The architect's stroll format is read as delivered** (`src/nav/stroll.js`).
  - It reads `order`, `stops[{id, eye, target, overview}]` and `legs[{from, to, points}]`, with layout ids mapped
    to place ids.
  - Fallbacks, in order: the `path_` empties in `square.glb`, then a temporary lane round the square.
- **The carpenter's signpost.** The engine's wooden signpost now shows only when no `act_sign_` boards exist.
  - The boards are named by layout id (`act_sign_gluehwein`) and mapped to places.
  - They are kept out of the static merge (`merge.js` SKIP now includes `act_sign_`, `write_` and `cam_read_`)
    so each one stays clickable.

New files:

- `src/nav/stroll.js`
- `src/nav/signpost.js`
- `src/nav/guide.js`: the stop the visitor is at, walking, arriving, reading, stepping back
- `src/ui/signboard.js`: the on-screen signpost
- `src/ui/stopbar.js`: things to do at a stop, no section text
- `src/ui/note.js`: the vendor's word as a small paper note above the counter, plus the live region

Rewritten: `src/interaction/keyboard.js`.

### 2. Every section's words are written in the market; no HTML side panels

The panel and the reading aside are deleted. Each section is drawn as crisp 3D SDF text (troika-three-text) on
something that belongs to its stall:

| Stop | Writing surface | What is on it |
|---|---|---|
| Glühwein | a chalkboard standing on the counter's free end ("Heute am Stand") | About me |
| Bier | the "Frisch vom Fass" chalkboard on the counter, and a stack of **Bierdeckel** | the projects as a tap list (with the GitHub link); each coaster has a project's name and style on the front and its description on the back. A click picks the coaster up, and the next page **flips it over** |
| Bratwurst | the "Speisekarte" counter board, and **wrapping paper** on the counter | the writing, as dishes ("Noch nichts vom Grill" for now) |
| Bücher | a reading card on the counter, and **any book**: click a spine and it opens with its words on its own 3D pages, title page on the left, "In short" and the summary page after page, a leaf turning over | the reading list and every book's page from `content/books/` |
| Musik | sheet music on a stand at the front of the bandstand | music |
| Riesenrad | a cork noticeboard by the foot of the wheel, and placards on the gondolas | the big questions |
| Karussell | a ticket in the ticket booth ("Kasse · Fahrkarten") | contact, with links |

- **Reading.** A click on the surface, the stop bar's *Read* button, or Enter at a stop brings the camera square to
  the surface. Coasters and books need the near plane at 0.02 m. The surface glows a little.
- **Turning pages.** Long text turns pages and never scrolls: → / ← / PageUp / PageDown, the small page bar, or a
  click on the right or left half.
  - On a board or paper the pages crossfade.
  - A coaster flips about its vertical axis.
  - A book turns its leaf.
- **Pagination is exact.** The engine measures every word on a canvas in the same woff files troika draws
  with, so a page is known to fit before it is drawn (`src/world/text.js`). Text is reduced to the fonts' latin
  subset, so troika never fetches a fallback font from a CDN.
- **Access.**
  - `#readCopy` holds a visually hidden HTML copy of what is being read, with real links. A focused link shows
    as a chip.
  - The page bar's title takes focus.
  - Link quads in 3D are clickable.
  - plain.html is unchanged and still linked from the 3D page.
- **Writing surfaces in models.** When a model has `write_<role>` or `cam_read_<role>` nodes (BUILD.md), the
  engine writes on the model's own surface, using an area recovered from its UVs. Otherwise it builds the
  stand-in in code (`src/world/surfaces.js`, materials in `src/world/materials.js`).
  - The vendor's 17:00 models are the first with such nodes, and they are used: the Bierdeckel on
    `prop_bier_counter.glb` (`act_coaster_0..4`, `write_coaster_<i>_front/back`) carry the projects, and the
    Marktblatt on `prop_wurst_counter.glb` (`write_writing_paper`, `cam_read_writing_paper`) carries the writing.
    The coaster pick-up and flip now work from the model's own axes, whatever they are.
  - Two things the vendor's planes taught the area finder (`areaFromWriteMesh`): the area covers only the UVs
    the plane really has (a plane mapped into a corner of a print atlas no longer gives a metre-wide area), and
    the words go on the side facing away from the body the plane is printed on (the coaster's back plane has
    its UVs mirrored against that side, and its material is double-sided, so winding cannot tell).
  - A coaster held up to read turns its face from the stall's lamps, so it gets a soft light of its own (its
    print as emissive, on its own copy of the material, faded in and out with the pick-up).
  - In pass 1 every other surface was a stand-in. In pass 2 all but the Bücherstand reading card are the models' own (see Pass 2, item 2). The table above lists the stand-ins, which still stand in when a model is missing.

New files: `src/world/text.js`, `surfaces.js`, `sections.js` (the pieces from `content/*.md`, with the built-in
fallback), `reader.js` and `materials.js`.

### 3. Streaming: the still first, detail when you get there

- A still of the home view (`public/stills/home.webp`, 81 KB, recaptured in pass 2 with `npm run still`) is
  preloaded and shown at once. It fades into the live market once the part loaded after the first frame is in
  (the town ring, the rides, the deco stalls), at most 4 s after the first frame.
- **The full market opens with the lite files** of the four section stalls, the bandstand and the tree. The town
  ring (pass 2) is not in the first load at all: its lite file comes with the rides just after the first frame.
  - A stall comes in at full detail only when it is the stop being walked to or the next one (`guide.walkTo` →
    `streamer.want`). The first stop, the town and the tree come in at full detail just after that.
  - The upgrade is a **graft** (`src/engine/stream.js`). The full model's geometry and materials move onto the
    lite model's nodes, so every node an action, item, light or slot holds stays the same object.
  - The town's and the tree's full files add a few detail nodes, which are moved over whole; their snow caps join
    the Snow button.
  - `tests/unit.mjs` checks that each stall's lite and full node trees match.
- **The crowd** loads just after the first frame (`main.js` `loadCrowd`). A stand-in with the same API answers
  until it arrives. `?crowd=first` restores the round-4 order.
- **The 3D text** (troika's chunk and the faces it draws with) loads just after the first frame too
  (`text.js` `loadText`, `reader.start()`). A page or label is an empty group that fills itself when they arrive.

## Budgets (`npm run budget`, final build of pass 2)

| | Round 4 | Round 5, pass 1 | Round 5, pass 2 |
|---|---|---|---|
| Full market, first load | 19.70 MB | 9.29 MB | **8.20 MB** |
| Lite market, first load | 7.44 MB | 7.21 MB | **6.12 MB** |

Breakdown:

- Full market: first load 8.20 MB, deferred 11.79 MB, full detail on demand 13.58 MB, everything 33.56 MB.
- Lite market: first load 6.12 MB, deferred 5.20 MB, everything 11.32 MB.
- Site code, styles and fonts: 1.47 MB in the first load, plus 0.34 MB after the first frame (troika and the
  text faces). The home still is 0.08 MB. `book_open.glb` (26 KB, lite 23 KB) is fetched on the way to the
  Bücherstand; its textures are the vendor's print atlas, which the props already load.
- Counted as in pass 1 (`--town-first`) the models delivered since then would put the lite first load at
  7.32 MB: the margin pass 1 had was nearly gone, which is why the town moved.
- Counted the way round 4 did (`--no-stream --crowd-first --town-first`): 20.84 MB full, 7.87 MB lite. The models
  grew since round 4.
- `npm run budget -- --strict` (the Pages workflow's gate) fails if either first load is over its aim (25 / 8 MB)
  or not below round 4's.

The full listing is in `budget.txt`.

## Verification

`npm run test:unit`: all unit checks pass, including the new ones (stroll legs for every pair of stops, stop
eyes and the Riesenrad overview, lite/full node parity for the streamed stalls, both first loads below round 4).

`node tests/smoke.mjs` (swiftshader, the final build with the vendor's 17:00 models; log in `smoke.log`):
**192/193** on the full run, no console errors. The one failure was *Prost: the crowd raises a glass*: at the
Glühwein close-up nobody in view stood within 12 m, so nobody answered. Fixed in `src/crowd.js` (the nearest
people in view a little further off answer instead) and the check now gives the voices a few seconds. The
interaction phase was rerun on the rebuilt site: **30/30**, no console errors (appended to `smoke.log`).

Phases: unit; the full market at 1280 px (the still, signpost, walks, ← →, the Riesenrad overview, streaming,
no orbit, no side panel); reading every surface on the lite market (words drawn in 3D, the hidden copy, the page
bar, links, Escape, the coaster flip, a book opening and turning a page); every action and both rides; the lite
market; a phone with reduced motion and touch; plain.html; every model missing; audio.

Bytes the browser fetched before the market's first frame (`encodedBodySize`, JS gzipped by the preview server):
**8.34 MB** for the full market (round 4: 18.73 MB measured the same way) and **6.26 MB** for the lite market.

The vendor's coasters and Marktblatt were also checked by eye (`tests/dev-r5.mjs`): the front and back of a
Bierdeckel and the Marktblatt are in `read_bier_coaster_0.jpg`, `read_bier_coaster_back.jpg` and
`read_wurst_paper.jpg`.

## Files (engineer-owned)

- New in pass 2:
  - `src/actions/items/bookOpen.js`: the vendor's open hardback
  - `tests/capture-still.mjs` (`npm run still`)
- New in pass 1:
  - `src/nav/{stroll,signpost,guide}.js`
  - `src/world/{text,surfaces,sections,reader,materials}.js`
  - `src/ui/{signboard,stopbar,note}.js`
  - `src/engine/stream.js`
  - `public/stills/home.webp`
  - `tests/dev-r5.mjs`, `tests/tools/glb-nodes.mjs`, `tests/tools/glb-region.mjs`
- Rewritten:
  - `src/main.js`
  - `src/interaction/camera.js`, `src/interaction/keyboard.js`
  - `src/ui/reading.js`: down to the library lookup and page fetch
  - `tests/smoke.mjs`
- Changed:
  - `src/engine/{market,loader,props,instruments,merge}.js`, `src/layout.js`, `src/crowd.js`
  - `src/interaction/picking.js`
  - `src/actions/items/books.js`
  - `index.html`, `src/styles/main.css`
  - `plugins/market.js`
  - `scripts/budget.mjs`, `tests/unit.mjs`
  - `package.json` and the lockfile: troika-three-text, @fontsource/caveat
- Changed in pass 2:
  - `src/world/{surfaces,reader,text}.js`: model surfaces by alias, printed coasters and pages, fitted type
  - `src/engine/stream.js`: the `afterGraft` hook
  - `src/actions/items/books.js`: uses `bookOpen.js`
  - `src/nav/guide.js`: fetches the book on the way
  - `src/interaction/picking.js`, `src/styles/main.css`: the hover label kept inside
  - `src/main.js`: the town deferred, its lights, the still held, test probes
  - `scripts/budget.mjs`, `.github/workflows/pages.yml`: the round-4 gate
  - `tests/unit.mjs`, `tests/smoke.mjs`, `tests/dev-r5.mjs`, `package.json`
- Removed: `src/ui/panel.js`.
- `CREDITS.md` (engineer table): troika-three-text with its utils, webgl-sdf-generator and bidi-js (MIT), and
  Caveat (OFL).
- `.github/workflows/pages.yml`: the budget step is named "Budget gate" (it already ran `--strict`). The Vite base
  stays `/website/` (or `PAGES_BASE`).

## For the other roles

- **Architect.** Your stroll data is used as delivered. Moving the overview eye 4.5 m out could be folded into
  `stroll.py`, if you agree the gondola's own eye is too deep inside the rim.
- **Carpenter, vendor and ride builder.** Your `write_`/`cam_read_` nodes are all in use, under the names you
  chose: Glühwein `about`, Bier `projects_board`, Bratwurst `writing_menu`, Marktblatt `writing_paper`, bandstand
  `music`, Riesenrad `questions_board` and `question_1..3`, Karussell `contact`, the Bierdeckel and
  `book_open.glb`. Still missing: the Bücherstand reading card (`write_card`, or any of `reading_card` and
  `books_card`); it stays a stand-in until then.
  - A request for next round: a `write_` card that fills a hole in a print (the coasters, the book's pages) shows
    its own grain texture and no baked occlusion, so it reads as a different card. The engine now gives it the
    print's own UVs. If the cards carried the print themselves, nothing would need fixing.
  - The vendor's wine bottles have `write_label_0..11`. The ADR mentions a tasting note on a turned label. There
    is no text for them yet, so they are left as printed.
- **Writer.** Please add `ui.stroll_hint` to `content/site.md` (suggested text in Pass 2, item 5). The old
  `ui.hint` describes the round-4 orbit and is not shown.
- **Lighting.** After a lighting change: `cd site && npm run build && npm run still && npm run build`.

## Open issues

1. **The Bücherstand reading card is the one stand-in left.** It goes away by itself when a `write_card` (or
   `reading_card`) node arrives.
2. **The spare coasters stay blank.** The vendor made five (`act_coaster_0..4`), and there are three projects.
   Coasters 3 and 4 lie on the counter with their print and no words, and cannot be clicked. Their write_ cards
   are left as delivered.
3. **The lite coaster is a 12-sided disc.** Close up its rim shows corners on the lite market. The round back face
   sits just inside them. The full model is round.
4. **Pages turn on books and on a long coaster back.** Every other section fits one page of its surface at the
   current sizes. Model surfaces fit their type to one page when they can; a longer text pages by itself.
5. **The town arrives a moment after the first frame.** The still covers that moment (at most 4 s). On a very slow
   connection, the fade can still happen before the town is in.
6. **The vendor's book needs a few seconds to fetch.** It is fetched on the way to the Bücherstand. A click that
   comes before it arrives (5 s) opens the engine's own book.
7. **The still must be recaptured after a lighting or layout change** (`npm run still`).
8. **Writer's hint:** see "For the other roles".
9. **Testing on swiftshader is slow:** a full smoke run takes over an hour. Text appears a moment after a page is
   drawn (troika builds its glyphs in a worker), so the tests wait for it.
10. **Audio levels are checked by sampling.** On a slow run the check once read zero for one stem; it passed on
    rerun.
