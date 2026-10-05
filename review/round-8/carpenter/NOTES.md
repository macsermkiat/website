# Carpenter: round 8 notes (ADR 0004: ornament shop, book cabinets, fuller deco stalls)

This round ran on the cloud machine (CPU, `NM_THREADS=3`, `NM_ROUND=8`). I built the three ADR 0004 parts:

- the new ornament shop;
- the Bücherstand cabinets;
- rails and crate spots on the deco stalls.

I did not rebuild the Glühwein, Bratwurst or Bierstand. Their files are unchanged since round 7, and their previews are in `review/round-6/carpenter/`. All numbers below were measured in `site/public/models` after `optimize.mjs`.

## 1. Ornament shop: `blender/stalls/schmuck.py` → `stall_schmuck.glb` (+ lite)

It replaces `deco_schmuck.glb` at the `deco-schmuck` place. `deco_schmuck.glb` still ships, so the deco kit keeps nine variants.

- **Character.**
  - A 4.5 x 2.6 m hut with white-painted boards, richly trimmed in red and gold under a dark shingled roof.
  - **Sign.** A carved red pediment (Ziergiebel) stands on the front eave, with scroll ends and star cut-outs. Its cream cartouche carries the carved sign **"Christbaumschmuck"** in UnifrakturCook. The cartouche is `paint_lit`, so it reads at night.
  - The pediment is outlined in fairy bulbs, crowned with an eight-point gold star, and has a snow strip on its coping.
  - **Trim.**
    - A scalloped valance with star cut-outs runs under the eave.
    - Carved scallops edge the red bargeboards.
    - Fretwork corbels sit under the header.
    - Each gable has a turned finial with a gold ball and a round red star board.
  - **Painted details.** Red-and-gold posts, rails and side-wall bands, gold stars on the counter front, and a fir garland with red and gold baubles along the header.
- **Three front bays.**
  - **Left bay: glass case.** A red panelled pedestal cupboard with a glazed display case on top. The case has glass on the front, sides, back and top, a glass shelf, a velvet floor, a carved crest, gold finials and its own warm bulb. `slot_cabinet` is on the velvet floor. I built the case as part of the hut, because it is carpentry.
  - **Centre: counter.** The counter top is at 1.05 m. Behind it, three stepped tiers on the back wall hold `slot_shelf_1`, `slot_shelf_2` and `slot_shelf_3`.
  - **Right bay: tree.** A low two-step dais for the display tree (`slot_tree`). The bay is open down to 0.42 m, so the tree shows from the lane.
- **Rails.** There are four brass hanging rails, `slot_rail_1` to `slot_rail_4`:
  - rail 1 hangs in front of the counter;
  - rail 2 hangs inside, over the counter's back edge, from a tie beam;
  - rails 3 and 4 hang across the two bays.

  Each empty sits at the rail's left end, with +X running along the rail.
- **Nodes.**
  - Slots and markers: `slot_counter`, `slot_shelf_1..3`, `slot_vendor`, `slot_sign`, `slot_front`, `slot_rail_1..4`, `slot_tree`, `slot_cabinet`.
  - Lights and camera: `light_0` and `light_1`, plus `cam_view`/`cam_target`.
  - Meshes: `bulbs_0` (`bulb_warm`) and `snow_0..2`.
  - `cam_view` stands 4.05 m in front of the hut at 1.8 m. It looks at the counter and rails, and the whole 4.5 m front fits a 16:9 frame.
- **For the vendor: `blender/stalls/schmuck_slots.json`.** It lists:
  - every slot's position;
  - each rail's length and free drop (rail 1: 0.58 m, rail 2: 0.31 m, rail 3: 0.52 m, rail 4: 0.21 m above the tree);
  - the glass case's inner size (0.70 x 0.34 x 0.56 m, glass shelf at 0.30 m);
  - the tree dais top (0.5 x 0.4 m) and the tallest tree it takes (1.45 m);
  - the tier sizes.
- **Preview goods.** `prop_schmuck_*` is not on disk yet, so the preview shows render-only stand-in ornaments. These are baubles on the rails, a lit tree, case figures and boxed baubles. None of them is exported.
- `pipeline.vendor_sets("stall_schmuck.glb")` imports the vendor's sets from `props.json` once they exist.

## 2. Bücherstand: six glazed category cabinets (`buecher.py`, `buecher_sections.py`)

- **The racks and carts are gone.** There is one glazed cabinet per key in `content/books/categories.json`:
  - **Hut cabinets.** `physics` and `people` stand in the hut front, either side of the counter. The hut is now 4.2 m wide (it was 3.7 m), and the counter keeps its 2.18 m.
  - **Wing cabinets.** `lives` + `mind` and `decisions` + `craft` stand in two wings splayed 40° out from the hut's front corners, under shingled canopies. The canopies have bulb strings and snow caps (`snow_2`, `snow_3`).
  - The bay window, the "Bücher" sign, the counter, `slot_vendor`, the lantern and `write_reading_card` / `cam_read_reading_card` are unchanged.
- **Sizing.** Each cabinet is sized for its category's count. There are up to five covers per row, rows = ceil(n/5) and covers per row = ceil(n/rows):

  | key | books | rows x covers | cabinet width | `cam_cat` distance |
  |---|---|---|---|---|
  | people (Menschen & Gespräche) | 14 | 3 x 5 | 0.89 m | 1.12 m |
  | decisions (Risiko & Entscheidungen) | 11 | 3 x 4 | 0.73 m | 1.12 m |
  | physics (Physik & Kosmos) | 10 | 2 x 5 | 0.89 m | 0.72 m |
  | mind (Geist & Körper) | 9 | 2 x 5 | 0.89 m | 0.72 m |
  | lives (Lebensgeschichten) | 6 | 2 x 3 | 0.57 m | 0.72 m |
  | craft (Handwerk & Gewohnheit) | 5 | 1 x 5 | 0.89 m | 0.67 m |

- **Inside each cabinet.**
  - **Face-out boards.** Each row has a walnut ledge with a lip and a honey backboard. Covers lean back 15°.
    - Cover pitch is 0.158 m, and covers can be up to 0.145 x 0.215 x 0.035 m.
    - Rows are 0.265 m apart, and the top ledge is at 1.36 m.
  - **Spine board.** A spine board at 1.62 m holds books at rest, as spines.
  - **Base cupboard.** The panelled base cupboard rises to just below the lowest row, so a 1-row cabinet looks like a vitrine and a 3-row one is mostly glass.
  - **Back and light.** The back is cream inside, and two small warm bulbs sit under the top.
- **Signs.** Each cabinet has an arched cream crest sign, `sign_cat_<key>`, with its `label_de` in green Alegreya SC:
  - a label with " & " splits onto two lines;
  - "Lebensgeschichten" is hyphenated onto two lines on the narrow board.
- **Doors (`act_cab_<key>`).** The door node is an empty on the hinge line, at the bottom corner on the door's front face, turned with its cabinet.
  - **Meshes.** The door frame (`cab_door_<key>`, paint) and the pane (`cab_glass_<key>`) are its child meshes.
  - **Glazing bars.** They sit only where a ledge or the spine board crosses, so they hide no cover.
  - **Opening.** Each door opens 170° and folds flat beside its cabinet: onto the open lane, the counter front, or the neighbouring cabinet's door. It is hinged on the side that allows this:
    - left hinge (`open_deg` -170): lives, mind, people;
    - right hinge (`open_deg` +170): physics, decisions, craft.

    Blender Z and three.js Y take the same sign. The json carries `hinge_side` and `open_deg`.
  - **Mind and decisions.** Their open doors lie over their neighbours, which is fine with one cabinet open at a time.
  - **Child-node transforms.** The child nodes carry meshopt's dequantisation offset and scale, so animate the `act_cab_` parent, not the children.
- **New material `glass_clear`.** It is used for the cabinet panes and the shop's glass case. Its alpha is 0.06 with a darker base (`glass` is 0.14), so the covers read through the glass instead of a milky sheet.
- **Cameras.** `cam_cat_<key>` / `cam_cat_<key>_target` stand on each cabinet's normal. The covers area fills 0.86 of a 16:9 frame at the site's 42° vertical field of view; see `stall_buecher_cam_cat_*.jpg`, rendered with that cabinet's door open.
- **For the vendor: `buecher_sections.json`.** It is now version 2. Per cabinet it gives:
  - the cabinet frame;
  - `slot_cat_<key>` (left end of the lowest board, on the ledge just behind its lip, rotated with the cabinet);
  - every board's offset, width, ledge depth, lean and `cover_slots_x`;
  - the spine board;
  - the door;
  - the sign;
  - the camera pair.
- `python3 blender/stalls/buecher_sections.py --check` now also checks the `act_cab_` hinges, and it passes on both LODs.
- `cam_view` moved back to 5.0 m (it was 4.2 m) at 1.85 m, to take in both wings. The stroll stop in `layout.json` is derived from it.
- `slot_cabinet_l` and `slot_cabinet_r` are gone with the old decorative cabinets. `site/src/engine/standinGoods.js` only uses them for stand-ins if they are present.

## 3. Deco stalls (`deco.py`): rail, crate spot and triangle room for the goods

- **Rail.** Every variant has a turned honey-wood hanging rail across the front opening, at 2.02 m, on two forged brackets screwed to the header. `slot_rail_1` is at its left end, with +X along the rail. On the awning variants the rail is shorter, so it clears the awning stays.
- **Crate bench.** Every variant has a low slatted bench at the front-left corner for one crate or basket. `slot_crate` is on its top, at 0.34 m. `slot_front` is unchanged.
- **`blender/stalls/deco_slots.json`** lists both per variant: rail length 2.0-2.8 m, free drop 0.52 m, and the bench top size.
- **Triangle room for the goods.** The deco budget (20k) now includes the goods, so I trimmed the huts by 1.7k-3.1k triangles each:
  - painted, flat sign lettering;
  - shingles 0.33 x 0.22 m (they were 0.29 x 0.20);
  - square-edged board roofs;
  - 14-column snow;
  - a coarser counter wear grid;
  - 5x3 bulbs;
  - one stand-in floor board (the floor is hidden behind the counter).

  The kit textures are unchanged (`deco_kit_*.webp`, still shared).

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| **stall_schmuck** (new) | 28,004 | 0.70 MB | 10,716 | 0.26 MB |
| **stall_buecher** | 51,428 | 1.42 MB | 13,865 | 0.41 MB |
| stall_gluehwein (unchanged) | 38,780 | 0.97 MB | 8,676 | 0.23 MB |
| stall_bratwurst (unchanged) | 38,378 | 0.92 MB | 8,534 | 0.25 MB |
| stall_bier (unchanged) | 41,453 | 1.08 MB | 11,171 | 0.30 MB |
| deco_lebkuchen | 12,105 | 0.36 MB | 4,016 | 0.13 MB |
| deco_mandeln | 12,830 | 0.36 MB | 4,631 | 0.13 MB |
| deco_kerzen | 11,598 | 0.34 MB | 4,076 | 0.13 MB |
| deco_spielzeug | 13,405 | 0.38 MB | 5,031 | 0.15 MB |
| deco_schmuck | 12,704 | 0.36 MB | 4,369 | 0.13 MB |
| deco_kaese | 11,097 | 0.29 MB | 4,356 | 0.13 MB |
| deco_crepes | 10,857 | 0.32 MB | 3,765 | 0.12 MB |
| deco_maroni | 11,460 | 0.29 MB | 5,003 | 0.14 MB |
| deco_puffer | 12,315 | 0.35 MB | 4,573 | 0.14 MB |

The deco files were 13,283-15,985 triangles in round 7.

- **Bücherstand with all book props on disk now:**
  - Full: 62,334 triangles. That is 2.94 MB including the shared kit (0.46 MB) and book textures (0.52 MB).
  - Lite: 17,397 triangles and 1.00 MB.
  - Both are inside the 80k / 4 MB budget, and the vendor's new cabinet sets have about 17k triangles of room.
- **Ornament shop.** The hut leaves about 12k triangles and 1.3 MB of the 40k / 2 MB budget for the goods. Its kit textures are the shared deco kit files.
- **Deco stalls.** The huts leave 6.6k-9.1k triangles of the 20k for the goods. The vendor's current deco sets are 2.8k-5.1k.
- **Counter height.** `slot_counter` is at 1.050 m on every stall and the shop.
- **Checks.**
  - `glb_tools.py check` passes on all 10 section-stall and shop files and all 18 deco files.
  - The check now also requires:
    - `act_cab_<key>` on the Bücherstand;
    - `slot_tree`, `slot_cabinet`, `light_0`, `light_1` and `slot_rail_*` on the shop;
    - `slot_rail_1` and `slot_crate` on the deco files.

## Previews in this folder

All renders are Cycles.

- `stall_schmuck_preview.jpg`: 1280x720 at 48 samples, a 3/4 front view at night with stand-in ornaments.
- `stall_buecher_preview.jpg`: 1280x720 at 48 samples, a 3/4 view with closed doors. It uses stand-in face-out covers in category colours and spines on the spine boards, because the vendor's cabinet sets are not finished yet.
- `stall_buecher_cam_cat_{people,physics,lives,craft}.jpg`: 960x540 at 32 samples, the view from each `cam_cat_<key>` with that cabinet's door open. `stall_buecher_cam_cat_sheet.jpg` puts all four on one sheet.
- `deco_contact_sheet.jpg`: the nine rebuilt deco variants, empty of goods. The rail shows as the bar under the header.

## Library (`blender/lib`, documented in `README.md`)

These are new, and no existing name or default changed:

- `Hut.build_carcass(floor=True)`;
- `pipeline.vendor_sets(asset)`;
- the `glass_clear` material;
- `NM_OPEN_DOORS` for the Bücherstand preview;
- the round-8 `glb_tools` checks.

## For the other roles

- **Engineer.**
  - Swap `deco-schmuck`'s asset to `stall_schmuck.glb`, which is 4.5 m wide.
  - The Bücherstand doors are `act_cab_<key>`: rotate the parent node by the json's `open_deg` before the covers come forward.
  - `cam_cat_*` are 0.67-1.12 m from the glass, so the near plane must be under about 0.3 m.
  - The Bücherstand `cam_view` moved (see above).
- **Vendor.**
  - Lay `prop_books_<key>` out on `buecher_sections.json` v2 (face-out boards and spine board). The round-3 rack sets no longer fit.
  - The ornament goods go on `schmuck_slots.json`.
  - Deco rail goods go on `slot_rail_1` and the crate on `slot_crate` (`deco_slots.json`).
- **Architect.**
  - The Bücherstand now spans about x ±3.65 m, and its wing ends reach about 1.3 m in front of the hut front.
  - In the market, the left wing's outer cabinet comes within about 1 m of the Bierstand's right front corner. Please check it in the scene.
- **Organizer.** The shop's `slot_vendor` is behind the counter centre. Customers stand at `slot_front`; keep the right bay clear for the tree.

## Contract notes

- The "Bücherstand categories" carpenter bullet in BUILD.md still describes side racks and carts. The ADR 0004 section supersedes it.
- The ADR's bookshelf design is still pending Mac's decision. If he picks another design, the cabinets are confined to `buecher_sections.py` and `category_cabinet()`.

## Open issues

- **Preview stand-ins.** The shop and cabinet previews use stand-in goods. They need a re-render once `prop_schmuck_*` and the new `prop_books_<key>` sets exist.
- **Cabinet signs.** At 0.26 m tall, the crest signs are legible in the stroll view but small from the home view. The engine's labels or a `paint_lit` board would help.
- **Open doors in the 3/4 view.** In a single 3/4 view the mind and decisions doors, fully open, cover their neighbours. This is not an issue while the engine opens one cabinet at a time.
- **Ornament shop sides.** The shop's sides are simpler than its front: white boards with red bands. A side window or pegboard display is the next step.
- **Carried over:**
  - the emissive stand-ins (`paint_lit`, `paint_glow`, `iron_matte`, `rauten`);
  - bevels as real geometry;
  - no scorch decal on the Bratwurst;
  - the Glühwein reading view is 12° oblique.
