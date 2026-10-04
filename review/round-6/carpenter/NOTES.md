# Carpenter: round 6 notes (text lives in the market)

I built on the cloud machine with CPU and `NM_THREADS=3`. The other builders kept the load at 10-14, so a 1280x720 preview took 4-6 minutes. This round adds a writing board to each of three section stalls (ADR 0003, BUILD.md `write_` / `cam_read_`), a shared `boards` module in `blender/lib`, and fixes for the round 4 judge notes. No `CODEX_JUDGE.md` exists for round 4, so there were no Codex points to fix. All numbers below were measured on `site/public/models` after `optimize.mjs`.

## 1. The three writing boards

Each board is a believable market piece built round a blank writing area. The writing area is its own mesh `write_<name>`: one flat quad, UVs 0-1 across it with +V up the text, and the plain `chalk_slate` material (no vertex colour, no AO, never merged). Each board also has a `cam_read_<name>` empty, which looks at its target like `cam_view` does, and a `cam_read_<name>_target` empty on the centre of the writing area.

The reading camera stands on the board's normal. At the site's 42° vertical field of view at 16:9, the writing fills 76% of the frame height from there. That keeps the frame, the chalk tray and the crest in the picture (88% cut the frame off). `read_views_sheet.jpg` shows all three reading views in Cycles with the same lens.

| Stall | Surface | Writing area | The board | Reading camera |
|---|---|---|---|---|
| Glühwein (About) | `write_about` | 1.10 x 0.80 m | Behind the counter, right of the vendor, in front of the empty right half of the back wall. Red frame with a gold bead and a carved red crest with a gold star. Hangs on two short iron chains from a new cross beam between the side-wall plates. Nail heads, screw eyes, and a chalk tray with two chalk sticks and a felt eraser. | 1.37 m out, in front of the counter, level with the board. It is slid 0.3 m right (a 12° oblique view) so the vendor's pot on the counter stays out of the writing area. Only the pot lid's edge touches the tray corner. |
| Bratwurst (Writing) | `write_writing_menu` | 0.92 x 0.70 m | A "Speisekarte" board on its own stand at the front-left corner, where people queue for the grill. Soot-dark frame between two stout posts on cross feet with braces and a stretcher. Black header plank with cream Alegreya SC letters. An iron lantern on a bracket off the left post (its `lamp_glass` glows). Snow on the header and the post caps, and a chalk tray. Turned 25° toward the counter front. | 1.20 m out, 8 cm above the board's centre |
| Bierstand (Projects) | `write_projects_board` | 0.92 x 0.70 m | On a whole standing barrel at the front-left corner, the side that faces the middle of the square. 16 staves with gaps, four iron hoops, a boarded head and a snow cap. Blue-painted frame with a white bead, two posts, and an arched cream crest "Frisch vom Fass" in navy Fraktur with a Rauten strip. A gooseneck lamp over the crest (its bulb is in `bulbs_0`). Turned 30° toward the bar. | 1.20 m out, 10 cm above the board's centre |

- **Nothing is covered.** All three boards stay clear of the main signs and the 1.05 m counters.
  - The Glühwein board stands 0.36 m to the right of the vendor's spot (`slot_vendor` at x 0).
  - The two outdoor boards stand beyond the counters' left ends. From `cam_view` they appear just left of the counter end (checked by angle: board edge at 35-39°, counter end at 30-32°).
- **Light.** The boards use only the existing `light_` empties (two per stall, unchanged).
  - The Glühwein board faces `light_1` under the front overhang.
  - The two outdoor boards are reached by `light_1` (the grill light and the bar-front light). Their lantern and lamp glow in the browser through `lamp_glass` / `bulb_warm`, as BUILD.md asks for a small glow in a stall that already has its two lights.
  - The two headers are `paint_lit`, like the main signs, so their cream glows and the letters stay dark.
  - In the Cycles previews, a small point light at the lantern and a spot from the lamp stand in for that glow, as the sign lamps do.
- **German text** (3D, correctly spelled): Speisekarte, Frisch vom Fass. The boards themselves are blank; the engine writes on them.
- **Checks.**
  - `glb_tools.check` now requires each stall's write surface and reading-camera pair, in both LODs (`WRITE_REQUIRED`). It passes on all eight section-stall files and all 18 deco files.
  - The lite and full files of every section stall have identical node names, which the engineer's stream graft needs.

## 2. Round 4 judge points

- **Bratwurst preview camera re-framed:** pulled back and aimed higher. The roof sign no longer touches the top edge, and the new menu board is in the picture.
- **Glühwein letters:** the red Fraktur letters moved from `paint_lit` to the trim's `paint_glow`. They now stay a deeper red against the glowing cream board instead of glowing themselves.
- **Carried over (other roles, not changed):**
  - The Bücherstand cart signs sit low.
  - The canopy shadow on the upper rack boards needs the lighting designer.
  - The organizer's Bücherstand browsing spots should move to y ≈ -2.6.

## 3. Library (`blender/lib`)

- **New `nmlib/boards.py`**, documented in `blender/lib/README.md` under "`boards`":
  - `face_frame`, `at`, `frame_axes`, `local_box`
  - `write_surface(name, F, w, h, surface="slate"|"card")`
  - `chalkboard(...)`: frame, bead, backing, nails, screw eyes, tray, chalk, eraser
  - `read_distance` / `read_camera(name, F, w, h, fill=0.76, lift, side)`
  - `chain`, `barrel`, `lantern`
- **The slate texture** `kit_slate_color` is generated in numpy: a well-used blank blackboard with cloudy chalk haze, bowed eraser wipes with chalky rims, faint scratches and dust toward the tray. It stays dark (sRGB 41-73) so drawn chalk reads on it.
  - Because of its `kit_` name, the pipeline shares it as `deco_kit_slate_color.webp` and `.lite.webp`, 2.0 kB each. All three stalls point to the same file.
- **`pipeline.py`:**
  - `--read-views` renders the view from every `cam_read_` empty of the stall's own export (not the vendor's imported props, which carry their own), at the site's field of view.
  - Also new: `--read-only`, `--extra-view name=x,y,z,tx,ty,tz,lens` and `--extra-only`.
  - `NM_ROUND` now defaults to 6.
- **`glb_tools.py`:** `WRITE_REQUIRED` / `write_required()`, used by `check`.
- No existing name or default changed.

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 38,780 (was 37,858) | 0.97 MB | 8,676 | 0.23 MB |
| stall_bratwurst | 38,378 (was 36,402) | 0.92 MB | 8,534 | 0.25 MB |
| stall_bier | 41,453 (was 39,745) | 1.08 MB | 11,171 | 0.30 MB |
| stall_buecher | 48,098 (unchanged) | 1.31 MB | 14,297 | 0.41 MB |
| deco_* (9, unchanged) | 13,283-15,985 | 0.36-0.42 MB | 3,699-5,041 | 0.12-0.15 MB |

- **Shared kit textures:** 0.44 MB (lite 0.18 MB), referenced by every stall and deco file. The new slate map adds 2 kB.
- **With the vendor's current props:**
  - Glühwein 58,172
  - Bratwurst 59,354
  - Bierstand 59,181
  - All three are under the 60k section budget, and every stall plus props is under 2 MB with the shared kit.
- **Staying in budget.** Before trimming, the boards put the Bratwurst and the Bierstand about 1k over 60k with their props. I trimmed:
  - The header and crest lettering is painted (one face per glyph).
  - The Bier garland has fewer fir tufts (20 per m, was 34) and one roof drift fewer per slope.
  - The board barrel's hoops have fewer segments.
- The lite files are 22-27% of the full triangles.
- `slot_counter` is still at 1.050 m (Glühwein glb: `slot_counter` translation y 1.05).
- Sign text is unchanged and correctly spelled: Glühwein, Bratwurst, Bier vom Fass, Bücher, the nine deco signs and the six category signs, plus the new Speisekarte and Frisch vom Fass.

## Previews in this folder

- `stall_gluehwein_preview.jpg`, `stall_bratwurst_preview.jpg`, `stall_bier_preview.jpg`: Cycles, 1280x720, 48 samples, 3/4 front view at night, with the vendor's props and the new boards.
- `stall_gluehwein_read_about.jpg`, `stall_bratwurst_read_writing_menu.jpg`, `stall_bier_read_projects_board.jpg`: the view from each `cam_read_` empty (960x540, 32 samples, 42° vertical field of view). These are the blank boards the engine will write on.
- `stall_bratwurst_board.jpg`, `stall_bier_board.jpg`: close-ups of the two outdoor boards as market pieces (stand, header, lantern, barrel).
- `read_views_sheet.jpg`: those five views on one sheet.
- `stall_buecher_preview_round3.jpg` and `deco_contact_sheet_round3.jpg`: copies of the round 3 renders. The Bücherstand and deco geometry has not changed since, so I did not re-render them.

## For the other roles

- **Engineer: surface names.** Round 5's `surfaces.js` looks for the roles glueh `board`, bier `vomfass` and wurst `menu`. This round's brief names them `write_about`, `write_projects_board` and `write_writing_menu`, so the engine needs those three roles (`writeNodes()` lower-cases the part after `write_`).
- **Engineer: no painted header.** The model boards carry their own painted headers (Speisekarte, Frisch vom Fass, the Glühwein crest). Please do not draw a second header on a model surface.
- **Engineer: phones.** The `cam_read` distances assume the desktop 42° field of view at 16:9. On a phone (55°, portrait) the board will look smaller from the same point, so move along the camera-target line if needed.
- **Vendor.** The Bierstand is 0.8k triangles under 60k with your current props, and the Bratwurst is 0.6k under. A bigger counter set would push them over.
- **Vendor: the Glühwein pot.** Its lid sits in the lower-left corner of the reading view, over the tray but not the writing. Moving the pot further left than x +0.55 from `slot_counter` would clear it.

## Open issues

- The outdoor boards are lit in the browser only by `light_1` and the engine's reading glow. Their lantern and lamp glow but cast no light, and a third `light_` would need the market owner's approval.
- The Glühwein reading view is 12° oblique to dodge the pot. The text stays square to the board, but it is not a dead-on view.
- The reading views do not include the painted headers. The target must sit on the writing area's centre, and taking in the header as well would drop the fill below 65%.
- Carried over:
  - The emissive stand-ins (`paint_lit`, `paint_glow`, `iron_matte`, `rauten`) are a workaround.
  - Bevels are real geometry.
  - The Bratwurst has no soft scorch decal.
  - The cart signs sit low.
