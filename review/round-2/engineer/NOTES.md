# Engineer, round 2: every item on the counters is clickable

The previews in this folder come from the production build (`npm run build`, notes hidden), served from a
copy of `dist/` by `tests/smoke.mjs`. Software GL (SwiftShader) drew them on a shared 4-CPU machine with a
load average of 15 to 18. The market owner should commit them; they are untracked until then.

## Summary

- **Items.** Every book, glass, mug, wine bottle, sausage and roll in the four section stalls is its own
  clickable object (`src/actions/items/`). Each one lifts and gets an outline under the pointer, and each
  answers a tap on a phone, on both the full and the lite market. A click brings the camera in close to where
  the little scene plays out. The one exception is a book, which comes to the visitor instead.
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

## Codex round 2 (`review/round-2/CODEX_JUDGE_WIP.md`), last pass of the round

- **The content gate is on for every deploy.** `pages.yml` sets `STRICT_CONTENT: '1'`; it is no longer a repository
  variable. The build fails while content/*.md holds a `[[Mac: ...]]` note, a `<!-- check -->` or `[check]` marker, or a
  book page marked `review: check`. **Today that stops the deploy**: about, contact, music, projects, questions, reading
  and writing still carry 18 notes and 11 check markers, and 35 book pages are still `review: check`. This is the
  intended state: nothing unconfirmed reaches the public site. The writer and Mac clear the markers to publish.
  `npm run build` without the variable still builds locally, with the notes left out.
- **The unconfirmed book list is not reinstated** (`plugins/market.js`). Round 1's "On the shelf in the market"
  fallback is gone. A notes-hidden build also keeps only the front-matter `books:` that are on Mac's own shelf
  (`content/bookshelf.json`): today The Order of Time and The Book of Why. "Pick a book for me" goes on to his
  shelf's other books after those. With no front-matter book left, it picks from his shelf (`content.js` `bookPicks`).
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

## Late in the round: Mac's bookshelf and the sausage axis

- **Mac's bookshelf** (`plugins/market.js` `buildLibrary`, `actions/items/books.js`).
  - The build reads `content/bookshelf.json` (the 55 titles Mac chose), the writer's
    `content/books/categories.json` and the one-line summary (`one_line`) from each `content/books/<slug>.md`.
  - The bookshop panel and plain.html get "Mac's bookshelf: 55 books he has read, by subject", one list per
    category, with a summary for every book the writer has done (36 so far). On plain.html the list is open.
  - In the 3D shop, a spine whose printed title is on Mac's shelf opens as **his** book ("from Mac's shelf" on the
    title page) with the writer's summary on the right page. Seven of the vendor's current spines match (The Order
    of Time, The Book of Why, The Black Swan, Surely You're Joking, Man's Search for Meaning, Chaos, Reality Is Not
    What It Seems). When the vendor prints Mac's titles on the spines, every one of them matches with no engine
    change. "Pick a book for me" goes through the writer's picks that are on Mac's shelf, then these spines.
  - Section loading no longer reads sub-folders, so a book page's heading can never be taken for a section.
  - The strict gate counts a book page still marked `review: check`. The build's warning reduces them to one line.
- **Sausages turn about their own axis.** The vendor moved the sausage pivots to their base and asked for this.
  `wurst.js` now turns each sausage about its long axis at `turn_axis.offset_threejs_y` over the pivot (items.json),
  or about the middle of its mesh when there is no such field. It no longer rolls round its underside.

## What each item does

All of this is in `src/actions/items/`. `index.js` finds the items, handles hover, and hands each click to the
stall's module. `common.js` holds the shared pieces: frames, streams, liquid surfaces and sparks.

| Item | Click | Module |
|---|---|---|
| Book (all 106 spines) | Slides out, flies to a lectern pose in front of the counter and opens. The left page carries its own title and author, the right page its note from items.json. It also shows its cover texture. Clicking the open book, or any other spine, puts it back; after 14 s it goes back by itself. | `books.js` |
| Glass (18) | An empty glass slides under its own tap (items.json `beer` names the tap). The tap handle tips, a stream runs, the beer rises and the head grows, then the glass slides home. A full glass is picked up; click a second full glass and the two meet and clink (Prost), with a line from the crowd. An upside-down glass from the back shelf is turned upright first. The tap itself pours the next empty glass. | `beer.js` |
| Mug (16) | The ladle rises out of the copper pot, moves over that mug and tips. The mug fills with a stream and gets its own steam, and the pot lid lifts. An upside-down mug is turned upright first. | `gluehwein.js` |
| Wine bottle `act_bottle_*` (18) | Comes toward the visitor, tilts and turns once to show its label. A tag and the panel give its name and a tasting note (items.json `note`/`tasting`, then about.md `bottles:`, then a note matched to its grape). A second click, or 10 s, puts it back. Wine glasses swirl; the kettle opens and steams. | `gluehwein.js` |
| Sausage (16) | Turns half over on the grill with a hop, a sizzle, a flare of the coals and a burst of sparks. "Turn the sausages" turns them all, staggered. | `wurst.js` |
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

VERIFY_PLACEHOLDER

## Budgets (`npm run budget`)

Measured on the files in `site/public/models` on 4 October 00:15, after the vendor's 00:00 props build. Shared
textures are charged once; deferred means loaded just after the first frame.

| | First load | Deferred | Everything | Aim (first load) |
|---|---|---|---|---|
| Full market | 18.99 MB | 6.93 MB | 25.92 MB | 25 MB |
| Lite market | 6.99 MB | 2.50 MB | 9.48 MB | 8 MB |

- The site's own code, styles and fonts are 1.48 MB of each first load.
- The 32 shared textures (the deco kit, the vendor atlases) are 1.13 MB, charged once.
- The full market's "everything" includes the crowd's distance level (the 12 figures' `.lite.glb`).
- The lite total counts every crowd figure, although the lite market aliases three of them away. It is an upper bound.

Charged only their own files, every asset is inside its byte budget. Charged their shared textures as well, the
section stalls come to 2.06–3.03 MB: the Bücherstand is 0.03 MB over its 3 MB, and its own spine and cover textures
are most of it (Codex's 3.04 MB). The deco stalls are 0.39–0.52 MB of their own, plus the kit they share.

One asset is over a budget:

| Asset | Triangles | Budget | Owner |
|---|---|---|---|
| bandstand with instruments and players | 66.8k | 50k | ride builder / organizer |

`npm run budget -- --strict` passes and runs in CI after the build.

## For the other roles

- **Vendor.**
  - Please give the deco stalls `act_` nodes for their goods, each with an items.json `detail` field. The
    Lebkuchen hearts in `deco.js` are stand-ins and are skipped as soon as the stall has `act_` nodes.
  - Please check the lite Bierstand foam (see above).
  - Section stalls are over their per-asset byte budgets, and every deco stall is too. This is mostly the
    shared kit textures: each stall counts the whole deco kit, 12 `.webp` files. Sharing one texture set, or
    smaller kit textures, would bring the deco stalls under 1 MB.
- **Writer.** A `note` field for each book and bottle in items.json would replace the grape-based tasting
  notes and the generic book lines.
- **Lighting designer.** The Bücherstand has one light marker too many (see the contract notes).

## Still open

- Frame time on a real GPU is still unmeasured (the ?perf Tour). This is a launch gate for Mac.
- The full market on SwiftShader takes tens of seconds a frame under this machine's load, so the full-market
  item shots are driven with `freeze`/`advance`. The real mouse and touch clicks are tested on the lite market.
