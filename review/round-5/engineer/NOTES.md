# Engineer, round 5: the guided stroll, words written in the market, streaming

Mac asked for this: *"Market signpost is interesting, the camera just follow along the path. Also I don't want the
text as a separate component windows from the market. It should be in the environment. For example, when click
the book, it show the book with written text inside. Same as wineshop, beer shop."* The work follows ADR 0003.
Nothing is committed by me; the session that started me commits.

## What changed

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
  - Every other surface is still a stand-in.

New files: `src/world/text.js`, `surfaces.js`, `sections.js` (the pieces from `content/*.md`, with the built-in
fallback), `reader.js` and `materials.js`.

### 3. Streaming: the still first, detail when you get there

- A still of the home view (`public/stills/home.webp`, 61 KB, captured from this build) is preloaded and shown at
  once. It fades into the live market on the first frame.
- **The full market opens with the lite files** of the four section stalls, the bandstand, the town and the tree.
  - A stall comes in at full detail only when it is the stop being walked to or the next one (`guide.walkTo` →
    `streamer.want`). The first stop, the town and the tree come in just after the first frame.
  - The upgrade is a **graft** (`src/engine/stream.js`). The full model's geometry and materials move onto the
    lite model's nodes, so every node an action, item, light or slot holds stays the same object.
  - The town's and the tree's full files add a few detail nodes, which are moved over whole; their snow caps join
    the Snow button.
  - `tests/unit.mjs` checks that each stall's lite and full node trees match.
- **The crowd** loads just after the first frame (`main.js` `loadCrowd`). A stand-in with the same API answers
  until it arrives. `?crowd=first` restores the round-4 order.
- **The 3D text** (troika's chunk and the faces it draws with) loads just after the first frame too
  (`text.js` `loadText`, `reader.start()`). A page or label is an empty group that fills itself when they arrive.

## Budgets (`npm run budget`, this build)

| | Round 4 | Round 5 |
|---|---|---|
| Full market, first load | 19.70 MB | **9.29 MB** |
| Lite market, first load | 7.44 MB | **7.21 MB** |

Breakdown:

- Full market: first load 9.29 MB, deferred 10.26 MB, full detail on demand 13.39 MB, everything 32.94 MB.
- Lite market: first load 7.21 MB, deferred 3.90 MB, everything 11.11 MB.
- Site code, styles and fonts: 1.46 MB in the first load. Another 0.34 MB (troika and the text faces) loads after
  the first frame. The home still is 0.06 MB.
- `node scripts/budget.mjs --no-stream --crowd-first` counts the way round 4 did: 20.55 MB full, 7.96 MB lite. The
  models grew in between: the new signpost, and the vendor's deco props roughly doubled.

The full listing is in `budget.txt`. The smoke run also measures the bytes the browser fetched before the
market's first frame (see Verification).

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

- New:
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
- Removed: `src/ui/panel.js`.
- `CREDITS.md` (engineer table): troika-three-text with its utils, webgl-sdf-generator and bidi-js (MIT), and
  Caveat (OFL).
- Not touched: `.github/workflows/pages.yml`. The Vite base stays `/website/` (or `PAGES_BASE`).

## For the other roles

- **Architect.** Your stroll data is used as delivered. Moving the overview eye 4.5 m out could be folded into
  `stroll.py`, if you agree the gondola's own eye is too deep inside the rim.
- **Carpenter and vendor.** The coasters and the Marktblatt are in use. `book_open.glb` is not yet: the procedural
  open book (pages, turning leaf) is kept this round. The other roles the engine looks for:
  - glueh `board`
  - bier `vomfass`
  - wurst `menu` (`paper` is covered by the Marktblatt)
  - books `card`
  - band `sheet`
  - ferris `notice`
  - carousel `ticket`

  A plane with UVs is enough: the area is recovered from the UVs, with v running down the text. The stand-ins
  then go away by themselves.
- **Writer.** `content/site.md` `ui.hint` still describes the round-4 orbit ("drag to look around… click a
  stall to go inside"). The build keeps the stroll's own hint until `ui.stroll_hint` exists, and then uses that.
- **Lighting.** The still (`public/stills/home.webp`) is a frame of the live home view. Re-capture it after a
  lighting change (`tests/dev-r5.mjs` with `snap:`, or ask me).

## Open issues

1. **`book_open.glb` is not used yet.** The vendor's open book (`write_page_left/right`, `act_page_turn` with
   `write_page_turn_front/back`, `cam_read_book`) arrived at 17:00. The procedural book (its pages and turning
   leaf, `src/actions/items/books.js`) works and is kept; swapping in the model is a contained change for round 6.
2. **Most writing surfaces are still stand-ins.** Only the coasters and the Marktblatt come from models. The
   others go away by themselves when `write_<role>` nodes arrive (roles listed above).
3. **The spare coasters stay blank.** The vendor made five (`act_coaster_0..4`); there are three projects.
   Coasters 3 and 4 lie on the counter with their print and no words, and are not clickable.
4. **Only books turn pages today.** Every section's text fits one page of its surface at the current sizes. The
   pagination is exact and tested on books; a longer section will page by itself.
5. **The lite margin is small.** The lite first load is 7.21 MB against round 4's 7.44 MB, and it moves with
   the models: it read 7.09, 7.20 and 7.28 MB at different points this afternoon as deliveries landed. The lite stalls, the signpost and the deco props
   are where it would go.
6. **The still must be recaptured after a lighting or layout change**, or the fade into the live market shows
   a jump.
7. **Writer's hint.** `ui.hint` still describes the orbit; the build uses its own hint until `ui.stroll_hint`
   exists.
8. **Testing on swiftshader is slow** (a full smoke run takes about an hour; one frame at 1280 px can take over a
   minute). The tests freeze the loop and advance it by hand. Text appears a moment after a page is drawn
   (troika builds its glyphs in a worker), so a screenshot taken right after a flip can miss it; the tests wait
   for it.
9. **Audio levels are checked by sampling**, and once read zero for one stem on a slow run (passed on rerun).
