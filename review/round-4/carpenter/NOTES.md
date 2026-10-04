# Carpenter: round 4 notes (polish)

Built on the cloud machine (CPU, `NM_THREADS=2-3`, load about 14 from the other builders). I changed only what round 3's judges and the round 4 priorities asked for. Every number below was measured on `site/public/models` after `optimize.mjs`.

## 1. Glühwein and Bratwurst main signs read from the home view

Market judge, round 3: "Enlarge the Glühwein and Bratwurst main signs, or make them emissive, so they read from the home view the way 'Bier vom Fass' does." I did both.

- **New kit variant `paint_lit`** (`blender/lib/nmlib/mats.py`). It is the shared paint atlas with a warm emissive copy of its colour (`emissiveFactor` 0.55/0.44/0.32; the emissive texture is the shared paint colour map, so it adds no texture bytes). A cream board glows and dark or red letters stay dark. It is an emissive stand-in like `paint_glow`: the Cycles previews switch it off and light the board with the two gooseneck lamp spots instead.
- **Glühwein:** the arched board is now 2.05 x 0.64 m (was 1.55 x 0.44), and the Fraktur letters are about 1.6x taller (text size 0.72, was 0.34). It has a cream board, red letters and a gold frame, all in `paint_lit`, plus two new gooseneck lamps (`Hut.sign_lamps`). It hangs in front of the tie beam. The arch clears the carved rake valances, and the bulb string under the lambrequin moved down 6 cm so it hangs below the sign. The carved lambrequin with its star cut-outs still shows either side of the sign and along both rakes.
- **Bratwurst:** the roof sign is now 2.45 x 0.60 m (was 1.9 x 0.44), and the letters are about 2x taller (text size 0.62, was 0.30). It used to be a black board with cream letters, which read as a dark patch from the home view. It is now a lit cream board with soot-black Alegreya SC letters and a black frame, in `paint_lit`. The struts and lamps moved out with it, and it clears the stovepipe by 11 cm.
- **How to check:** `home_signs.jpg` shows each stall in three.js from `layout.json`'s home camera, at the place `layout.json` gives it, under the site lighting module (`shoot.mjs --home`). The bottom row is 1:1 and the top row is a 3x crop. Bier vom Fass is the reference. Both signs now read at least as well as "Bier vom Fass". The full frames are `stall_*_three_home.jpg`.

## 2. `cam_cat_<key>` close-up cameras on the Bücherstand

- `blender/stalls/buecher_sections.py` now computes a camera for each section, and `buecher.py` exports two empties per section into both LODs:
  - `cam_cat_<key>`, rotated to look at its target (-Z toward it, like `cam_view`);
  - `cam_cat_<key>_target`, at the centre of the section's boards and sign (z 0.86).
- The camera stands 1.75 m in front of the section at eye height 1.45 m. That frames a section of about 0.8 m with its sign in a portrait view at 45° vertical FOV.
- **The inner rack bays (mind, people) stand behind the carts** when you look along their own normal. Their cameras swing 40° toward the lane and stand at 1.55 m, so the line of sight passes outside the cart's outer end. `stall_buecher_three_cam_cat_people.jpg` is the three.js view from `cam_cat_people`, taken with a tighter 30 mm lens than the engine will use, with the vendor's book sets attached. The cart is at the frame edge and does not cover the section.
- The positions are also in `buecher_sections.json`, as `cam`, `cam_position`, `cam_target` and `cam_target_position` on each section. Nothing else in the json changed (I compared it with the round 3 file).

| key | cam_cat (Blender stall frame) | target |
|---|---|---|
| physics | -1.157, -3.029, 1.45 | -2.498, -1.904, 0.86 |
| mind | -1.815, -3.176, 1.55 | -2.118, -1.453, 0.86 |
| lives | -1.400, -3.920, 1.45 | -1.400, -2.170, 0.86 |
| decisions | 1.400, -3.920, 1.45 | 1.400, -2.170, 0.86 |
| people | 1.850, -3.218, 1.55 | 2.154, -1.495, 0.86 |
| craft | 1.192, -3.071, 1.45 | 2.533, -1.947, 0.86 |

## 3. `buecher_sections.py --check` is read-only; both Bücherstand LODs come from one run

- **`--check` never writes.** Before, `--check` with no file arguments fell through to `write_json()`. Now:
  - `--check` anywhere in the arguments makes the run read-only;
  - with no files it checks both Bücherstand LODs;
  - it compares the json with the module in memory (new `build_doc()` / `check_json()`), and every `slot_cat_`, `cam_cat_` and `cam_cat_*_target` node with the json;
  - it exits 1 on any mismatch.
- **Verified:** the json's md5 was the same before and after a `--check` run that reported it out of date. Only `python3 blender/stalls/buecher_sections.py` (no flag) writes the json.
- **One run:** `stall_buecher.lite.glb` (14:43) and `stall_buecher.glb` (14:44) were written by the same `buecher.py --no-render` run. `--check`: "matches buecher_sections.json" for both.
- `glb_tools.check` now also requires `cam_cat_<key>` and `cam_cat_<key>_target` on `stall_buecher*`. It passes on all 26 stall and deco files.

## Other round 3 points

- **Organizer:** move the Bücherstand browsers to y ≈ -2.6. This is the organizer's to do; it is still open from round 3.
- **Lighting:** the rack canopies shadow the upper boards, and the canopy bulbs light nothing. Not changed this round. It is for the lighting designer, and the market owner would need to approve a third `light_` empty.
- **Cart signs at knee height:** not changed; I kept to the listed fixes. The `cam_cat_lives` and `cam_cat_decisions` close-ups frame them.
- No `CODEX_JUDGE.md` exists for round 3, so there were no Codex points to fix.

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 37,858 (was 37,603) | 0.95 MB | 8,322 | 0.22 MB |
| stall_bratwurst | 36,402 (was 36,391) | 0.86 MB | 7,467 | 0.22 MB |
| stall_bier | 39,745 (unchanged) | 1.01 MB | 9,641 | 0.26 MB |
| stall_buecher | 48,098 (+12 empties, no tris) | 1.31 MB | 14,297 | 0.41 MB |
| deco_* (9) | 13.3k-16.0k (unchanged) | 0.36-0.42 MB | 3.7k-5.0k | 0.12-0.15 MB |

- Shared kit textures are unchanged (`paint_lit` reuses the paint colour map).
- Every stall is within 40k / 3 MB, the Bücherstand is within 80k / 4 MB with its props, and the deco structures are within the deco budget.
- `slot_counter` is still at 1.050 m.
- Sign text is unchanged and correctly spelled: Glühwein, Bratwurst, Bier vom Fass, Bücher, plus the nine deco signs and six category signs.

## Previews in this folder

- `stall_gluehwein_preview.jpg`, `stall_bratwurst_preview.jpg`: Cycles, 1280x720, 48 samples, 3/4 front view at night, with the new signs lit by their lamp spots (the stand-in emission is off).
- `home_signs.jpg` and `stall_{gluehwein,bratwurst,bier}_three_home.jpg`: three.js from the home camera.
- `stall_buecher_three_cam_cat_people.jpg`: three.js from `cam_cat_people`.
- I did not re-render the Bier, Bücherstand or deco previews (their geometry is unchanged). The round 3 renders still apply.

## Library changes (no existing name or default changed)

- `mats.KIT_VARIANTS["paint_lit"]`, added to `STANDIN_EMIT` and `geo.BAND_MATS`.
- `glb_tools.buecher_required()` now includes the `cam_cat_*` nodes.
- `pipeline.ROUND` defaults to 4.
- The README documents all of this, plus the `buecher_sections.py` camera fields and the read-only `--check`.

## Open issues

- `paint_lit` is a stand-in: the engine has no light for the sign lamps. If the lighting designer adds a real sign light at `slot_sign`, the emission can drop back to `paint_glow` level.
- In the Cycles 3/4 preview the Bratwurst sign touches the top edge of the frame. The preview camera is unchanged from round 3.
- The `cam_cat_*` distances assume a 45° vertical FOV. If the engine uses a much narrower lens, the engineer can move the camera along the camera-target line.
- Carried over: the cart signs sit low; there is a canopy shadow on the upper rack boards; the emissive stand-ins are a workaround; bevels are real geometry; the Bratwurst has no soft scorch decal.
