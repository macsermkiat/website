# Engineer, round 2: every item on the counters is clickable

The previews in this folder come from the production build (`npm run build`, notes hidden), served from a
copy of `dist/` by `tests/smoke.mjs`. Software GL (SwiftShader) drew them on a shared 4-CPU machine with a
load average of 9 to 14. The market owner should commit them.

## Summary

- **Items.** Every book, glass, mug, wine bottle, sausage and roll in the four section stalls is its own
  clickable object (`src/actions/items/`). Each one lifts and gets an outline under the pointer, and each
  answers a tap on a phone, on both the full and the lite market. A click brings the camera in close to where
  the little scene plays out. The one exception is a book, which comes to the visitor instead.
- **Books (last pass).** The 55 books of Mac's shelf are clickable on the six category shelves. Each one opens with a
  reading view that shows its `content/books/<slug>.md`, fetched only when that book opens. It has a close button and
  keyboard access. plain.html carries the same 55 pages. See "Last pass".
- **Exact bindings.** The engine no longer guesses filenames. `layout.json` `asset` and `props.json`
  `stall`/`asset`/`slot`/`model`/`lite` must match exactly, and every mismatch is listed in
  `__market.report.bindings`. The smoke run asserts that list is empty.
- **Codex fixes.**
  - A budget script that counts external textures, and fails CI when a first load is over its aim.
  - Credits with source URLs on both index.html and plain.html.
  - A plain-HTML fallback when WebGL fails.
  - An accessible name for the canvas.
  - A mute button that covers every sound.
  - A strict build that also rejects `<!-- check -->` markers.
  - Smoke checks that assert node movement and book identity.
- **Round 1 judge points.**
  - The crowd steps out of close-ups.
  - The phone home view now stands between two string-light poles, so no pole is in the frame (see "Codex round 2").
  - The flake cap is removed from main.js.
  - The unconfirmed book list is no longer written back into the panel (see "Codex round 2").
  - `lfs: true` is gone from pages.yml.
  - The lite light count is documented.
  - The Bücherstand's third light marker is resolved.

## Judges' fixes (4 October, pass 2)

The panel asked for six fixes. Two of them are engineer work and are done. For the other four, the engineer side
is done and the rest waits on the role that owns it.

1. **The content gate (writer and Mac).** Still closed, on purpose: 18 `[[Mac: ...]]` notes, 15 check markers
   (last pass's NOTES said 18 check markers; the gate counts 15) and 35 book pages marked `review: check`. Clearing
   them means confirming facts about Mac, so only Mac and the writer can do it. The engineer side: a new
   `npm run content:check` lists every marker with its file and line, using the same rules as the build's gate
   (`plugins/market.js` `contentMarkers`). `-- --books` adds the 35 book pages by name. The list ends at 0 when
   the deploy can run. A unit check covers it.
2. **The bandstand budget.** `scripts/budget.mjs` counted the bandstand's four players (people_band_*, 18.6k
   triangles) inside "Bandstand with instruments". BUILD.md budgets players as person variants: 5k triangles and
   0.4 MB each. They are now charged that way, and each one fits (4.5k–4.8k triangles, 0.12 MB). The bandstand and
   its four instruments come to **48.2k triangles and 1.05 MB, inside 50k / 2 MB**. No asset is over budget now.
   *Market owner: please confirm this reading of the table. If the players were meant to count with the bandstand,
   the ride builder still needs to cut about 17k triangles.* `instr_sax_stand.glb` is in public/models, but the
   engine never loads it, so it is not counted.
3. **The reading view at 960 px and below.** It is now a sheet along the bottom (at most 44% of the screen height,
   46% on a phone), not a panel over the right side. This applies at 960 px wide and below, and on any screen taller
   than it is wide. Once the book is out, the camera comes to it (`main.js` `frameRegion`), and the picture moves up
   so the book stands in the free part above the sheet. There it can be clicked again to put it back. While the
   sheet is open the side panel steps aside (`html.reading`), so nothing covers the book. The reading view is modal,
   so the panel's buttons could not be used at that moment anyway. When the book
   closes, the camera goes back to where it was. Above 960 px nothing changes: the open book stands beside the
   reading view. The smoke run now asserts this at 960 × 640 (`item_books_sheet_960.jpg`) and on a phone
   (`phone_books_reading.jpg`). The run no longer falls back to the close button.
4. **Close-ups of each bookshop section.** BUILD.md belongs to the market owner, so I have not written the rule
   into it. The engine supports the rule proposed below, and works without the empties until they exist. The
   Bücherstand panel has a new row, "Look along a shelf", with one button per category, labelled in German. A button
   flies to `cam_cat_<key>` when the stall has one. Without one, the view is worked out from the section's own
   books: square to the shelf, from the side the stall's close-up looks from, and far enough back that every spine
   of the section fits the part of the screen the panel leaves free. On the lite market the close-up key light
   turns to that shelf, because the side racks face away from the stall's own lights. The smoke run checks that every physics and
   craft spine is in that free part at 960 px, and every craft spine above the sheet on a phone
   (`item_books_shelf_craft_960.jpg`, `phone_books_shelf_craft.jpg`). Proposed text for BUILD.md, "Scene
   conventions":
   > - `cam_cat_<key>` (Bücherstand only, optional): an empty where the camera goes to look along the category
   >   section `slot_cat_<key>`. It looks toward `cam_cat_<key>_target` when present, else at the middle of that
   >   section's books. Place it so the whole section fills a 4:3 view with a little room. Without it, the engine
   >   frames the section from its books.
5. **Frame time on a real GPU.** This machine has no GPU, so I cannot take this measurement. The engineer side is
   ready: `?perf=tour` now starts the tour by itself, and `npm run perf` (`tests/perf.mjs`) does the whole
   measurement on Mac's own machine. It opens a visible Chromium on that machine's GPU, tours both markets, prints
   one line per view and writes `review/perf/<date>.json`. It exits 0 when every view meets its target, 1 when one
   misses and 2 when the browser fell back to software GL. The targets are written in the script: full market at a
   60 fps median and 40 fps at p95, lite market at 30 fps and 20 fps. The market owner may change them. Steps for
   Mac: `cd site && npm ci && npm i --no-save playwright && npx playwright install chromium && npm run build &&
   npm run perf`.
6. **Deco goods and deco texture budgets (vendor).** The vendor has not yet added `act_` nodes for the deco
   goods: items.json has none. `deco.js` already makes any `act_` node in a deco set clickable, showing its
   `detail`, and it drops the code-made Lebkuchen hearts as soon as there is one. No engine change is needed when
   they arrive. On the texture budget: `budget.mjs` used to charge the whole shared deco kit (0.93 MB) to every
   stall that uses it. Each asset now carries an equal part of each shared texture it uses (unit-checked). The kit
   is still counted in full, once, in each market's total. On that measure the deco stalls come to 0.52–0.58 MB
   against 1 MB. Smaller kit textures from the vendor would still help the lite total.

## Codex round 2 (`review/round-2/CODEX_JUDGE_WIP.md`), last pass of the round

- **The content gate is on for every deploy.** `pages.yml` sets `STRICT_CONTENT: '1'`; it is no longer a repository
  variable. The build fails while content/*.md holds a `[[Mac: ...]]` note, a `<!-- check -->` or `[check]` marker, or a
  book page marked `review: check`. **Today that stops the deploy**: about, contact, music, projects, questions, reading
  and writing carry 18 notes and 15 check markers (pass 2, `npm run content:check`), and 35 book pages are still `review: check`. This is the
  intended state: nothing unconfirmed reaches the public site. The writer and Mac clear the markers to publish.
  `npm run build` without the variable still builds locally, with the notes left out.
- **The unconfirmed book list is not reinstated** (`plugins/market.js`). Round 1's "On the shelf in the market"
  fallback is gone. A notes-hidden build also keeps only the front-matter `books:` that are on Mac's own shelf
  (`content/books/categories.json` since the last pass): today the five physics titles in the writer's reading.md.
  "Pick a book for me" goes on to his shelf's other books after those. With no front-matter book left, it picks from his shelf (`content.js` `bookPicks`).
  Two unit checks cover this: no "On the shelf" block in the production panel, and every 3D pick is on Mac's shelf.
- **Budgets** (`scripts/budget.mjs`, rewritten):
  - It counts the deferred part of each market as well: the deco stalls, both rides and, on the full market, the
    crowd's distance level (each figure's `.lite.glb`, loaded after the first frame).
  - It counts the shared clips (`people_anims.glb`).
  - Textures are deduped by content hash, so two names with the same bytes count once. In the per-asset rows, a
    texture two or more assets use is charged once, to a "shared textures" row, and not to every stall.
  - It fails (exit 1) when `dist/assets` is missing, because the site's own code counts towards each first load.
  - Five new unit checks cover these.
- **Phone framing.** `PHONE_HOME` is now position [3.75, 5.6, 16] and target [3.4, 2.4, −4]. That is between the front
  row's poles at [0, 7.5] and [7.5, 6.5] and close enough that both stand more than 20° off the axis, outside a
  portrait frame. A new smoke check projects every string-light pole into the phone's home camera and fails if one is
  in the frame within 14 m.
- **Ride framing.** On the Riesenrad the rider leans 0.5 m out over the gondola's front rail toward the view, and the
  camera's near plane goes from 0.1 to 0.45 m while riding (`camera.js` `startRide`, restored on `endRide`/`flyTo`).
  The gondola's roof edge and the rim no longer draw as a dark beam across the top corner.
- **Shared clips** (`crowd.js` `loadSharedAnims`, `clipsFor`). The crowd loads `people_anims.glb` once, as
  crowd.json `shared_anims` describes. Every figure plays its own clips plus every shared clip it lacks, retargeted
  to its hips: each `hips.position` key moves by the figure's hips rest minus the reference's. So a lite figure gains
  laugh, the `_free` set, serve and wipe, and a figure shipped with no clips at all plays the whole shared set.
  The organizer can now drop the repeated clips from the figure files with no engine change.
  `__market.crowd().sharedAnims` reports the file, the clip count and how many retargets were made.
- **Clones no longer copy keyframes.** `Object3D.copy()` clones `userData` through JSON. Every clone of a figure
  used to serialise all its keyframe arrays. The loader now keeps the clips on a non-enumerable
  `userData.animations` (`engine/loader.js` `setClips`).
- **VERIFY_PLACEHOLDER** is replaced by the results of this pass's smoke run (see "Verification").

## After the restart (3 October): snow caps merged, everything re-verified

- **Snow caps** (`engine/merge.js` `mergeSnow`, called from `compact()` in `main.js`). The round 1 judges asked
  for this: turning the snow on used to add one draw per `snow_` cap. Caps that do not ride on a moving body
  are now merged across all the models of a load pass, in world space, into one mesh per look
  (`snow_merged_*` in the `snow_row_merged` group). The snow toggle drives the merged meshes, and caps on a
  gondola, a turning platform or an animated node keep their own meshes. On the lite market the toggle now drives
  23 entries, three of them merged meshes, and snow on costs 27 fewer draws than before; `__market.snowCaps()` reports it, and the smoke run checks
  that every cap shows with snow on and none with it off.
- **Assets.** The newest exports on disk (the vendor's deco goods sets `prop_deco_*`, the carpenter's
  Bücherstand and Bratwurst stalls, the ride builder's instruments, Riesenrad and Karussell, props.json and
  items.json of 30 September 04:01) all bind exactly: `report.bindings` is empty. The deco goods sets carry no
  `act_` nodes yet (only `rot_pyramid`), so the Lebkuchen hearts made in code stay.
- The whole smoke suite was run again on this build, and every preview in this folder was retaken from it.

## Last pass (4 October, after the second restart): the six category shelves and the reading view

BUILD.md's new "Bücherstand categories" section and the vendor's and carpenter's round-3 exports landed during the
restart. The engine now follows them.

- **One source for books.** `plugins/market.js` `buildLibrary` reads only `content/books/categories.json`, as BUILD.md
  says: 55 books in six categories (physics 10, lives 6, mind 9, people 14, decisions 11, craft 5). `bookshelf.json` is
  no longer read. Each book gets its one-line summary and its page from `content/books/<slug>.md`. All 55 pages exist.
- **The six category sets bind exactly.** These are `prop_books_physics`, `_lives`, `_mind`, `_people`, `_decisions` and
  `_craft`, on the carpenter's `slot_cat_<key>` empties. That gives 55 clickable `act_book_00..54` on both the full and
  the lite market, with `report.bindings` and `report.contract` both empty. Each spine is matched to its book by its
  items.json `slug`, falling back to its title. The paper bands and the guesswork about which spine stands for which
  of Mac's books are gone (`books.js`). Every titled spine now is one of his books.
- **Reading view** (`src/ui/reading.js`, `#reader` in index.html). When a book is clicked, it slides out, flies to the
  counter and opens with its title and author on the pages. Beside it, a reading view shows that book's
  `content/books/<slug>.md`: the category in German, title, author, In short, Summary, Key ideas, If you read one
  chapter, and the sources as links.
  - **Fetched on demand.** The build emits one fragment per book (`dist/reading/<slug>.html`, 5–7 kB each), and the
    view fetches it only when that book opens. The 55 summaries add nothing to the first load. The dev server serves
    the same fragments.
  - **If the fetch fails,** the view shows the one-line summary and a link to the book's notes on plain.html.
  - **Keyboard.** Focus goes to the title and Tab stays inside the view. Escape or the close button closes the view,
    puts the book back and returns focus. Escape on the canvas closes the view before the panel.
  - **The open book stays out while the view is open.** It goes back by itself after 14 s only once the view is closed.
- **The panel's bookshelf list.** Each title is a link (`data-book`). In the market, clicking one opens that book on its
  shelf, with its page. Without the 3D market (or with a modifier key) the link goes to `plain.html#book-<slug>`. The
  panel's "goods, one by one" list names all 55 books as buttons, so every book can also be reached from the keyboard.
- **plain.html** lists the same 55 books by category, each title linked to its own `<article id="book-<slug>">` with
  the full notes (headings shifted to fit the page). The page is 423 kB uncompressed. It is plain text, so it is still
  fast.
- **Strict gate.** Book pages marked `review: check` are counted, as before. A local build includes them and warns
  (35 pages today). A deploy (`STRICT_CONTENT=1`) stops until the writer and Mac clear them.
- **Budget.** `budget.mjs` applies BUILD.md's Bücherstand budget, 80k triangles and 4 MB. It is at 59.0k and 2.45 MB of
  its own files, plus 0.93 MB of shared atlases.
- **Sausages.** The vendor's raw sausages (`act_sausage_16..23`, `raw: true`) and the warm tray turn in place, with
  no flare or sparks: only a sausage over the coals flares. "Turn the sausages" turns the ones on the grill. A raw one
  says it goes on the grill when there is room.
- **Stall clicks in 3D (a bug found by the smoke run).** The picker skipped every mesh flagged `merged`, which was
  meant for the merged shelf goods, whose items answer for them. But `mergeStatic` sets the same flag on each
  stall's merged body. So a click on a stall's boards could fall through to nothing: the smoke check "clicking a stall
  in 3D opens its panel" found the Bierstand front dead at the home view. The merged goods now carry their own flag
  (`userData.mergedItems`), and only those are skipped (`engine/merge.js`, `interaction/picking.js`).
- **The bookshop view** pulls back a little from the carpenter's `cam_view` (`VIEW_NUDGE.books.dolly` 0.8 → 1.12), so
  the wider stall's side racks stand clear of the panel. The 0.8 dolly dated from the small round-1 stall.
- **Tests.** Five new unit checks cover the library from categories.json, the linked list, a book's page fragment,
  the articles on the text page, and all 55 books with pages in the production content. The smoke run checks:
  - the reading view shows the clicked book's page;
  - Tab is trapped inside it;
  - Escape and the close button put the book back;
  - a bookshelf link opens its book;
  - plain.html has one article per book.

### Mac's bookshelf, as built before the categories (superseded)

The round's earlier pass read `content/bookshelf.json` and matched the vendor's spines by printed title. Only seven
matched, and the rest of Mac's books wore paper bands on stock spines. All of that is replaced by the section above.
Sausages still turn about their own axis, at items.json `turn_axis.offset_threejs_y` over the base pivot (`wurst.js`).

## What each item does

All of this is in `src/actions/items/`. `index.js` finds the items, handles hover, and hands each click to the
stall's module. `common.js` holds the shared pieces: frames, streams, liquid surfaces and sparks.

| Item | Click | Module |
|---|---|---|
| Book (all 55 of Mac's books, on the six category shelves) | Slides out, flies to a lectern pose in front of the counter and opens. The left page carries its own title and author, the right page its one-line summary, and the outside its cover texture. The reading view beside it shows its whole page from content/books/<slug>.md. Clicking the open book or another spine, closing the view or pressing Escape puts it back. | `books.js`, `ui/reading.js` |
| Glass (18) | An empty glass slides under its own tap (items.json `beer` names the tap). The tap handle tips, a stream runs, the beer rises and the head grows, then the glass slides home. A full glass is picked up; click a second full glass and the two meet and clink (Prost), with a line from the crowd. An upside-down glass from the back shelf is turned upright first. The tap itself pours the next empty glass. | `beer.js` |
| Mug (16) | The ladle rises out of the copper pot, moves over that mug and tips. The mug fills with a stream and gets its own steam, and the pot lid lifts. An upside-down mug is turned upright first. | `gluehwein.js` |
| Wine bottle `act_bottle_*` (18) | Comes toward the visitor, tilts and turns once to show its label. A tag and the panel give its name and a tasting note (items.json `note`/`tasting`, then about.md `bottles:`, then a note matched to its grape). A second click, or 10 s, puts it back. Wine glasses swirl; the kettle opens and steams. | `gluehwein.js` |
| Sausage (24) | Turns half over about its own long axis with a hop and a sizzle. One on the grill also brings a flare of the coals and a burst of sparks. The raw ones and the warm tray just turn. "Turn the sausages" turns those on the grill, staggered. | `wurst.js` |
| Roll (16) | A sausage from the grill flies into the roll along its length, and a zigzag of mustard is drawn on. It is handed over after 12 s or on a second click. | `wurst.js` |
| Deco goods | In the deco stalls, `act_` nodes lift under the pointer. A click shows their `detail` on a tag with a small swing. The Lebkuchen stall has no act_ nodes yet, so it gets three iced hearts made in code, hanging on ribbons. Their icing reads "Frohe Weihnachten", "Für Dich" and "Süßer Schatz", and a click shows the text and what it means. | `deco.js` |

- **Hover.** The item eases up 1.8 cm under the pointer, gets the outline, and a tooltip gives its own name.
  On a touch screen the tap does the lift and the name for 1.4 s. A tap may move up to 12 px and still count.
- **Range.** Items answer only within 11 m, or at the stall that is open. From further away the pointer means
  the whole stall, as before.
- **Keeping the merge.** The shelf goods stay merged (one mesh per look per set). The engine takes an item out
  of the merged mesh only while it is hovered or moving, and puts it back when it is home.
- **Panel list.** The panel's "The goods, one by one" list names each item as a button, which gives keyboard
  and screen-reader users the same actions.
- **Messages.** Each message combines the item's own text with the writer's `actionNote` and `item_hint`.
- **Camera.** A click flies the camera to 1.7 m from the action, keeping the visitor's direction: the glass
  under the tap, the ladle over the mug, the sausage on the grill. On a phone the item sits in the upper part
  of the picture, above the panel sheet. The flight is instant with reduced motion; with reduced motion every
  animation jumps to its end.
- **Stand-ins.** A stall with no items falls back to the round 1 stand-ins (`stalls.js`), so the panel
  buttons still work with missing models.

### Found in the vendor's lite Bierstand set

The head of foam in `prop_bier_counter.lite.glb` (00:14 build) is about 0.68 m tall: `foam_N_mesh` has scale
0.34 on a mesh that spans the full quantised range. The full glb's head is 3.7 cm tall. In the lite market it
stood as a cream column over every full glass. The engine now checks each head against its glass: it must be
under half the glass's height, with its top not far above the rim. A head that fails is dropped from the
merged mesh and replaced by one made in code. `__market.handlers.badFoam()` lists the glasses affected, so
the vendor can check their rebuild against it.

## Exact bindings (`layout.js`, `engine/props.js`)

- **Layout.** `findModelByKeys` and every filename guess are gone. A layout entry loads `asset` (or `model`)
  exactly. Its lite file is `<asset>.lite.glb` when that file exists.
- **Fallback layout.** `FALLBACK_LAYOUT` names exact assets too.
- **Reported problems.** Each of these goes into `report.bindings`, with the missing model drawn as a
  placeholder:
  - a missing asset or lite file;
  - a props.json set whose `stall` is not a layout id;
  - a set whose `asset` does not match the entry's model;
  - a set with no such slot;
  - a set whose `model` or `lite` file is missing.
- **Checks.**
  - The smoke run asserts `bindings` is empty for the real files.
  - The `?missing` run asserts that the simulated gaps are listed.
  - The lite probe gives `bindings: []`.

## Codex fixes

- **Budgets** (`scripts/budget.mjs`, `npm run budget`, and a CI step `npm run budget -- --strict`).
  - The script counts each glb and every external texture it references, since the deco kit and the vendor
    atlases are separate `.webp` files. Each shared texture is counted once per market (rewritten again in the last
    pass, see "Codex round 2").
  - It adds the site's own js, css and fonts from `dist/assets`.
  - First loads follow what the engine actually defers: the deco stalls and both rides.
  - Only the first-load totals fail the strict run. The per-asset rows are reported for the owning roles.
- **Credits.** The build reads every table in CREDITS.md and renders it, grouped by role, into
  `<details class="credits-all">` with links, on both index.html and plain.html.
- **WebGL fails.** `showPlainFallback` renders every section's content inside the stage and hides the 3D
  controls. `?nowebgl` forces it for testing.
- **Canvas.** It gets `role="img"` and an `aria-label` that says what the scene is and that the places are also listed as buttons below it.
- **Mute.** A "Sound: on/off" button drives one master gain that the band, the generative bed, the stems and
  every stall sound pass through. It is remembered in localStorage (in try/catch).
- **Strict content.** `STRICT_CONTENT=1` (always on in `pages.yml` since the last pass) fails the build on `[[notes]]`, `<!-- check -->` comments and
  `[check]` tags in content/*.md. Unit tests cover the gate.
- **Smoke checks.** They assert that the node moves (ladle, bottle, glass, sausage), that the neighbour
  sausage does not, that the opened book is the one clicked (title and author), that the mug and glass end
  full, and that a roll gets its sausage.

## Round 1 judge points

- **Crowd in close-ups.** `crowd.inCloseUp()` hides anyone who is not a vendor inside a 46° cone from the
  camera, closer than the target plus 0.8 m, whenever the camera is within 12 m. The Glühwein check "nobody
  between the camera and the vendor" stays in the smoke run.
- **Phone home.** See "Codex round 2": the view now stands between two poles, and a smoke check keeps poles out of it.
- **Flake cap.** `capFlakes` and `SNOW_FOG_MAX` are removed from main.js. The lighting designer's settings.js
  already holds both caps.
- **Stripped book list.** Round 1 appended the front-matter `books` when the body list was stripped. Codex round 2
  asked for that to stop, because the list is not confirmed. It is gone (see "Codex round 2").
- **pages.yml.** `lfs: true` is dropped, and the budget step is added.
- **Lite light count.** The lite market runs **5 real-time lights**: one inside each of the four section
  stalls, plus the close-up key spot. The key spot is always in the scene, fades in under the open stall's
  eave, and fades out at home.
- **The Bücherstand's third light marker.** BUILD.md allows 2 light markers per section stall and 1 per deco
  stall. The engine lights the stall's own `light_` markers first, then prop lights, up to that cap. Any
  marker over it is not lit and is listed in `__market.report.contract` with a message, so the
  vendor/lighting designer can remove or merge it. It no longer counts as a binding error.
- **Screenshots.** All are retaken from the production build.

## Verification

Pass 2 (4 October, 09:45–11:15). Every run used the production build (`npm run build`, notes hidden), served from a
copy of `dist/` by `tests/smoke.mjs` on SwiftShader. The machine was shared, with a load average of 3 to 9.
`npm ci && npm run build` succeeds. `npm run test:unit` passes 58/58, and `npm run budget -- --strict` passes.
`STRICT_CONTENT=1 npm run build` fails on the content gate, as intended.

| Smoke section | Result | Console errors |
|---|---|---|
| shots, items, audio (full market, 1280 px) | 45/45 | none |
| interact (lite, 960 × 640: every panel action, both rides, snow, reset, keyboard, clicks in 3D, the reading sheet, both shelf views) | 54/54 | none |
| phone (reduced motion, touch, the craft shelf and a tapped book above the sheet) | 10/10 | none |
| lite | 5/5 | none |
| missing models | 6/6 | none |
| plain.html and the 3D page's links and credits | 14/14 | none |

The interact and phone sections ran again on the final build, after the last two changes (the panel steps aside
while the sheet is open, and the key light goes back to the counter when a book opens). The full-market section
ran on the build before those two changes. Neither change touches the full market at 1280 px.

New in pass 2:

- at 960 px the reading view is a bottom sheet, and the open book stands above it, where it can be clicked again to
  put it back (no fallback to the close button any more);
- the Bücherstand panel has one shelf button per category, and the physics and craft views put every spine of
  their section in the free part of the picture;
- on a phone, the craft shelf is framed above the panel, and a tapped book opens above its reading sheet;
- unit checks for `content:check`, the bandstand players charged as person variants, and shared textures charged in
  equal parts.

What the smoke run asserts for the items (unchanged):

- the ladle, bottle, glass and sausage nodes move, and the neighbouring sausage does not;
- the opened book is the one clicked (title, author, slug), and its reading view shows its own page;
- the mug and glass end full, and a roll gets its sausage.

Previews in this folder:

- retaken this pass: the home view (full, snow, lite); the Glühwein, Bücherstand and bandstand panels; one
  close-up per item action (ladle, bottle, pouring, Prost, turning, bun, an open pick, an open category book, a
  Lebkuchen heart); both rides; the phone views; the missing-models stand-ins; plain.html;
- new this pass: `item_books_sheet_960.jpg`, `item_books_shelf_craft_960.jpg`, `phone_books_shelf_craft.jpg` and
  `phone_books_reading.jpg`.

## Budgets (`npm run budget`)

These were measured on the files in `site/public/models` on 4 October at 09:30, after the vendor's and carpenter's
round-3 exports. Shared textures are charged once. "Deferred" means loaded just after the first frame.

| | First load | Deferred | Everything | Aim (first load) |
|---|---|---|---|---|
| Full market | 19.69 MB | 7.23 MB | 26.92 MB | 25 MB |
| Lite market | 7.44 MB | 2.62 MB | 10.06 MB | 8 MB |

- The site's own code, styles and fonts are 1.49 MB of each first load. The 55 reading pages (5–7 kB each) are
  fetched only when a book opens and are not counted.
- The 32 shared textures (the deco kit and the vendor atlases) are 1.20 MB, charged once.
- The full market's "everything" includes the crowd's distance level (the 12 figures' `.lite.glb`).
- The lite total counts every crowd figure, although the lite market aliases three of them away. It is an upper bound.

Each asset is judged on its own files plus an equal part of every shared texture it uses (pass 2). On that
measure every asset is inside its triangle and byte budget:

- section stalls: 56.6k–57.3k triangles;
- Bücherstand: 59.0k triangles and 2.45 MB, against its 80k / 4 MB;
- bandstand with its four instruments: 48.2k triangles and 1.07 MB, against 50k / 2 MB;
- four band players: 4.5k–4.8k triangles each, against 5k for a person variant;
- deco stalls: 16.9k–19.6k triangles and 0.52–0.58 MB, against 20k / 1 MB.

Until pass 2 the bandstand row also counted the players, and came to 66.8k (see "Judges' fixes", point 2).

`npm run budget -- --strict` passes and runs in CI after the build.

## For the other roles

- **Vendor.**
  - Please give the deco stalls `act_` nodes for their goods, each with an items.json `detail` field. The
    Lebkuchen hearts in `deco.js` are stand-ins and are skipped as soon as the stall has `act_` nodes.
  - The lite Bierstand foam is fixed in your round-3 export. The engine's check still guards it.
  - Deco texture budgets: with each stall carrying its part of the shared kit, every deco stall is under 1 MB.
    Smaller kit textures would still lower both totals.
- **Writer.** A `note` field for each bottle in items.json would replace the grape-based tasting notes. The books need
  nothing more: their notes come from content/books/<slug>.md.
- **Carpenter.** The engine reads an optional `cam_cat_<key>` empty per Bücherstand section, and
  `cam_cat_<key>_target` if you add one. It uses them for the panel's "Look along a shelf" buttons. Without them it
  frames each section from its books, which already passes the smoke checks. Add them only if you want a
  hand-picked angle, once the market owner adds the rule to BUILD.md (text in "Judges' fixes", point 4).
  The Bücherstand's light marker count is fine now (2).
- **Organizer.** The figures can now ship without their own clips: the engine plays `people_anims.glb` on every
  figure. Dropping the repeated clips from the 24 figure files saves their bytes (Codex round 2, point 9).
- **Ride builder / organizer.** Nothing is needed for the budget if the market owner agrees the players count as person
  variants. The bandstand with instruments is 48.2k. `instr_sax_stand.glb` is not loaded by anything. Remove it, or tell
  me where it goes.
- **Market owner.** Please add the `cam_cat_<key>` rule to BUILD.md, and confirm that the band players count as person
  variants in the budget table ("Judges' fixes", points 2 and 4).

## Still open

- Frame time on a real GPU is still unmeasured. Mac runs `npm run perf` on his own machine before launch
  ("Judges' fixes", point 5). This is a launch gate.
- The content gate stops the deploy until the writer and Mac clear the markers: 18 notes, 15 check markers and 35
  book pages. `npm run content:check` lists them. This is intended.
- The Lebkuchen hearts stay code-made until the vendor ships deco `act_` nodes.
- Two calls for the market owner: the `cam_cat_<key>` rule in BUILD.md, and whether band players count as person
  variants.
- The full market on SwiftShader takes tens of seconds a frame under this machine's load, so the full-market
  item shots are driven with `freeze`/`advance`. The real mouse and touch clicks are tested on the lite market.
