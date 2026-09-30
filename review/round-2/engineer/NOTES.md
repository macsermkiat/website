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
  - The phone home view is moved so the string-light pole is off the centre line.
  - The flake cap is removed from main.js.
  - Stripped book lists now have a fallback.
  - `lfs: true` is gone from pages.yml.
  - The lite light count is documented.
  - The Bücherstand's third light marker is resolved.

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
    atlases are separate `.webp` files. Each shared texture is counted once per market.
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
- **Strict content.** `STRICT_CONTENT=1` fails the build on `[[notes]]`, `<!-- check -->` comments and
  `[check]` tags in content/*.md. Unit tests cover the gate.
- **Smoke checks.** They assert that the node moves (ladle, bottle, glass, sausage), that the neighbour
  sausage does not, that the opened book is the one clicked (title and author), that the mug and glass end
  full, and that a roll gets its sausage.

## Round 1 judge points

- **Crowd in close-ups.** `crowd.inCloseUp()` hides anyone who is not a vendor inside a 46° cone from the
  camera, closer than the target plus 0.8 m, whenever the camera is within 12 m. The Glühwein check "nobody
  between the camera and the vendor" stays in the smoke run.
- **Phone home.** The view is moved to position [2.3, 5.0, 19.5] and target [0.6, 2.7, −4], so the
  string-light pole is off the centre line (`phone_home.jpg`).
- **Flake cap.** `capFlakes` and `SNOW_FOG_MAX` are removed from main.js. The lighting designer's settings.js
  already holds both caps.
- **Stripped book list.** When a notes-hidden build strips the list in content/reading.md, the build appends
  "On the shelf in the market" from the front-matter `books`. The same list goes in the panel and on
  plain.html.
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

Measured on the files in `site/public/models` at the end of this round. Each row covers the glb, its props
and every external texture it references, counted in full for that row.

| | First load | Everything | Aim |
|---|---|---|---|
| Full market | 19.05 MB | 26.29 MB | 25 MB |
| Lite market | 6.80 MB | 9.55 MB | 8 MB |

Site code, styles and fonts come to 1.29 MB.

Over their per-asset budgets (full glb, props and textures):

| Asset | Size | Budget | Triangles |
|---|---|---|---|
| gluehwein | 3.11 MB | 3 MB | 56.6k |
| bierstand | 3.03 MB | 3 MB | 57.3k |
| buecherstand | 5.47 MB | 3 MB | 39.3k (its spine and cover textures) |
| bandstand with instruments and players | 2.12 MB | 2 MB | 67.3k, against a 50k budget |
| each deco stall | 1.29–1.38 MB | 1 MB | under 20k |

- Every deco stall counts the whole shared deco kit. In the market that kit loads once, which is why the
  first-load totals are well under their aims.
- Everything else is inside its budget: square, town, tree, bratwurst, both rides and the 12 people variants.
- `npm run budget -- --strict` passes and runs in CI.

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
