# Carpenter: round 7 notes (the Bücherstand reading card)

This was a short fix round on the cloud machine (CPU, `NM_THREADS=4`, low load). I changed only the Bücherstand. I did not rebuild the other three section stalls or the deco kit; their files on disk are the same as in round 6. All numbers below were measured in `site/public/models` after `optimize.mjs`.

## 1. `write_reading_card` on the Bücherstand counter

- **The piece.** It is a cream card clipped into a small walnut frame, standing on a table-top easel at the front-right corner of the counter. The easel has a ledge along its foot, a back leg down to the counter, a hinge block, and a small brass bulldog clip at the top.
  - **Placement.** I measured the vendor's `prop_books_counter` set and found a free strip at x 0.64-0.95 in the front 0.25 m of the counter. The card stands in that strip, so it touches no prop.
  - **Angle.** It is turned 10° toward the middle of the stall and leans back 14°.
  - It stays clear of the main sign, the cabinets and the counter edge.
- **Writing surface.** The mesh `write_reading_card` follows BUILD.md:
  - The writing area is 0.26 x 0.19 m: one flat quad, with UVs 0-1 across it and +V up the text.
  - The material is the plain `paper_card` (flat cream, roughness 0.85). It has no vertex colour and no AO, and it is never merged with other meshes.
  - The card carries no painted header, so the engine's text is the only text on it.
- **Reading camera.**
  - `cam_read_reading_card_target` is on the centre of the card.
  - `cam_read_reading_card` stands 0.33 m out along the card's normal, 3 cm higher, and looks at the target.
  - At the site's 42° field of view (16:9), the card fills 76% of the frame height. `stall_buecher_read_reading_card.jpg` shows the view from that camera.
  - Glb positions (three.js, Y-up): card centre (0.79, 1.17, 1.32), camera (0.73, 1.27, 1.63). The engine's stand-in was at (0.66, 1.05, 1.24), so the model card is close to where the engine already expects it.
- **Light.** The card uses no new `light_` empty. The stall's `light_1` under the front eave and the green banker's lamp (vendor) light it. In the reading view, the engine's reading glow does the rest.
- **Lite file.** `stall_buecher.lite.glb` has the same card, write surface and camera pair. The full and lite files have identical node names, which the stream graft needs.
- **Checks.** `glb_tools.WRITE_REQUIRED` now includes `stall_buecher: ["reading_card"]`. `glb_tools.py check` passes on all 8 section-stall files and all 18 deco files.

## 2. Library

- **New `boards.easel_card(...)`.** Signature: `boards.easel_card(name, F, w, h, frame, back, clip=None, base_z=None, rail=0.022, depth=0.016, leg_angle=24, surface="card", tint="walnut")`. It is documented in `blender/lib/README.md` under `boards`, with a new row in the boards table.
- No existing name or default changed.

## 3. Round 6 judge points

- **Glühwein board size (noted, as the judges asked).**
  - The brief asked for about 0.9 x 1.2 m. The board is 1.10 x 0.80 m, landscape.
  - The reason is the reading view: the engine reads in a 16:9 frame. A portrait board 1.2 m tall fills only about 40% of the frame width at the distance where it fits the frame height, so the text would be small. The landscape board fills 0.74 of the frame and stays readable.
- **Pot lid in the Glühwein reading view.** Not changed this round.
  - The clean fix is the vendor's: put the pot left of x +0.55 from `slot_counter`.
  - The reading camera is still 12° oblique.
- **Outdoor boards dark at night.** Not changed this round. That fix would mean rebuilding and re-rendering two stalls, and this round was limited to the reading card.
  - For legibility, the engine's reading glow is the intended mechanism.
  - A brighter `paint_lit` frame rim on the Speisekarte and Frisch vom Fass boards is the next step if the browser views still read dark.
- No `review/round-6/CODEX_JUDGE.md` exists, so there were no Codex points to fix.

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 38,780 | 0.97 MB | 8,676 | 0.23 MB |
| stall_bratwurst | 38,378 | 0.92 MB | 8,534 | 0.25 MB |
| stall_bier | 41,453 | 1.08 MB | 11,171 | 0.30 MB |
| stall_buecher | 48,428 (was 48,098; the card is +330) | 1.32 MB | 14,435 (was 14,297) | 0.41 MB |
| deco_* (9, unchanged) | 13,283-15,985 | 0.36-0.42 MB | 3,699-5,041 | 0.12-0.15 MB |

- **Bücherstand with all of the vendor's book props** (counter, two shelves, six categories):
  - Full: 59,334 triangles. The glbs total 1.86 MB, plus 0.98 MB of shared textures (kit and books).
  - Lite: 17,967 triangles. The glbs total 0.71 MB, plus 0.29 MB of shared textures.
  - Both are well inside the 80k / 4 MB Bücherstand budget.
- The shared kit textures are unchanged (0.44 MB, lite 0.18 MB). The card has no texture.
- `slot_counter` is still at 1.050 m. The sign text is unchanged and correctly spelled.

## Previews in this folder

- `stall_buecher_preview.jpg`: Cycles, 1280x720, 48 samples. A 3/4 front view at night, with the vendor's props and the new card at the counter's right end. It replaces the round 3 copy.
- `stall_buecher_read_reading_card.jpg`: the view from `cam_read_reading_card` (960x540, 32 samples, 42° vertical field of view). It shows the blank card that the engine will write on.
- `stall_buecher_card_closeup.jpg`: the card as a counter piece, next to the vendor's lamp, price cards and books (960x540, 32 samples).
- **Not re-rendered.** The other three stalls and the deco kit did not change, so their round 6 previews still apply: `review/round-6/carpenter/` (stall previews, read views) and `deco_contact_sheet_round3.jpg`.

## For the other roles

- **Engineer.** `write_reading_card` / `cam_read_reading_card` now ship in both Bücherstand files. The engine's `books.card` surface lists `reading_card` among its aliases, so the stand-in should disappear with no code change. Please draw no header on it.
- **Vendor.** Keep the counter's front-right strip (x > +0.62 from `slot_counter`, the front 0.25 m) free of new props.

## Open issues

- The card's reading camera is close to the card (0.33 m), so the near plane must be under about 0.3 m. On phones (55° portrait), the engine may need to move back along the camera-target line.
- The Glühwein reading view is still 12° oblique because of the pot (see the vendor fix above).
- The outdoor boards (Bratwurst, Bierstand) rely on the engine's reading glow at night.
- Carried over from round 6:
  - The emissive stand-ins (`paint_lit`, `paint_glow`, `iron_matte`, `rauten`) are a workaround.
  - Bevels are real geometry.
  - The Bratwurst has no soft scorch decal.
  - The Bücherstand cart signs sit low.
