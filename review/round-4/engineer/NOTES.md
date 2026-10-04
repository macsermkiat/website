# Engineer, round 4: Bier framing, the sax stand, narrow-screen checks

A short polish round on the cloud machine (software GL, shared 4 CPUs). Nothing is committed; the session that
started me commits. There is no round-3 engineer folder, so the open points come from
`review/round-3/market/JUDGES.md`, `review/round-2/engineer/JUDGES.md` and the round-4 brief.

## What changed

1. **The Bier item close-up shows the tap, the vendor and a full pint** (`src/interaction/itemFrame.js`, new; it is
   called from `focusItem` in `main.js`). A glass or tap used to bring the camera 1.7 m from the spout, so the
   empty glasses filled the frame (round 3 `item_bier_prost.jpg`). The Bierstand now builds a box from the
   tap tower, the clicked glass (with room for a full pint and its head) and the vendor
   (`crowd.people()`, from the counter to his hat, with his shoulders). It frames that box square to the stall
   front with `frameRegion`, in the part of the picture the panel leaves free, like the Glühwein panel view. The
   camera sits low (lift 0.08) so the front bunting does not cut across the vendor's head. Other stalls keep their
   close-ups as they were. See `item_bier_pouring.jpg` and `item_bier_prost.jpg`: tap tower, vendor with his
   hat and the full glasses with their heads are all in frame.
2. **The Bier stall close-up is pulled back** (`engine/market.js` `VIEW_NUDGE.bier = { dolly: 1.2 }`), so the tap
   tower to the right of the vendor clears the side panel (`panel_bier.jpg`).
3. **`instr_sax_stand.glb` is wired up** (`engine/instruments.js`, `actions/band.js`). With the organizer's sax
   player (who has both `play` and `rest` clips), the engine also loads the stand (or its `.lite`) at
   `slot_sax`. While the band rests, the tenor stands on its floor stand and the held sax is hidden. When the
   ballad plays, the sax goes back into the player's hands. Both are kept out of the static merge
   (`userData.live`), so the toggle works. The stand-in figure, used when the organizer's file is missing, still
   holds the sax. `__market.saxStand()` reports the state; at rest the run gave
   `{"stand":true,"standVisible":true,"heldVisible":false}`.
   `scripts/budget.mjs` now counts the stand's bytes with the bandstand. It counts only the triangles beyond
   the held sax's, because the two are never drawn together. Bandstand: **48.4k triangles, 1.12 MB**, inside
   50k / 2 MB. First loads: 19.77 MB full (aim 25) and 7.47 MB lite (aim 8).
4. **Bookshop outer bays on narrow screens.** The carpenter has not shipped `cam_cat_<key>` empties yet:
   `stall_buecher.glb` has only `cam_view`/`cam_target`. The engine already reads them (`engine/conventions.js`,
   `actions/items/books.js`, BUILD.md "Scene conventions") and will use them as soon as they exist. Until then
   the "Look along a shelf" buttons frame each section from its own books in the free part of the screen. In
   round 2 the smoke run asserted that every physics and craft spine fits at 960 px and on a phone. No change
   was needed this round.
5. **Reading view at 960 px and below.** It is already a bottom sheet (`styles/main.css`
   `@media (max-width: 960px), (max-aspect-ratio: 1/1)`), and the camera lifts the open book above it
   (round 2, `item_books_sheet_960.jpg` and `phone_books_reading.jpg`). No change was needed this round.

## Verification

- `npm ci && npm run build` in `site/`: passes. `npm run test:unit`: all unit checks pass, including both budget
  checks.
- `tests/shoot-r4.mjs` (new, a small check run): full market at 1280 × 860, with the Bier panel, a pint mid-pour,
  Prost, and the bandstand at rest. **No console errors.**
- `tests/smoke.mjs --only shots,plain,missing`: home view, stall panels, snow, plain.html, and every model
  missing (falls back to stand-ins): **38/38 checks passed, no console errors** (`smoke.log`). The screenshots
  `home_full.jpg`, `panel_gluehwein.jpg`, `panel_buecherstand.jpg`, `panel_bandstand.jpg`, `home_full_snow.jpg`,
  `plain_html.jpg` and `missing_models_standins.jpg` in this folder come from this run. The machine's load
  average was 3 to 11 during the run.

## Still open (other roles)

- Carpenter: optional `cam_cat_<key>` empties for the Bücherstand (the engine is ready).
- Lighting: the Bier vendor's white sleeves still glare under light_1 in close-ups (round 3 market judges).
- Vendor: clearer golden beer in the counter glasses.
- Mac: the content gate (`npm run content:check`) still blocks a strict deploy until the review markers are
  cleared. Frame time on a real GPU (`npm run perf`) is still unmeasured.
