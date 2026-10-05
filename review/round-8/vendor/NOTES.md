# Vendor, round 8 (ADR 0004)

This round delivers the vendor's three parts of ADR 0004, in Mac's order: the deco stalls as cheap scenery, the ornament shop's goods, and the Bücherstand's face-out covers for the new cabinets. `python3 blender/props/check_props.py` passes with no failures (16 warnings, all about lite ratios; see below).

## 1. Deco stalls: full shelves, cheap scenery (Mac, 2026-10-05)

> "There's no need to fully render object in side stores, because there will be no interaction to save the loading time."

- **One glb per stall, one mesh.** `prop_deco_<key>.glb` (+ `.lite.glb`) holds all of a stall's goods as a single merged mesh, `prop_deco_<key>_goods`, on the shared atlases (`prop_tex_atlas_*`, `prop_tex_market_*`). It has no textures of its own and no per-set AO map. The builder is `blender/props/set_decoscene.py`.
- **No interaction left.** There are no `act_` nodes, no `fx_` empties and no `items.json` entries for the eight deco stalls. check_props now fails a deco stall that has any of these, or more than two meshes.
- **One slot.** The set is authored at `slot_counter`, and its geometry reaches the other places through fixed offsets from that slot. All nine huts share `blender/stalls/deco.py`, so the offsets are the same everywhere (taken from `deco_slots.json` and the hut glbs):
  - counter goods at the slot itself;
  - goods hung from the carpenter's new **`slot_rail_1`** at (x, -0.18, +0.97). The old in-set rods are gone, and every string ties to the carpenter's rail and is clamped to its length;
  - **both back shelves** at `slot_shelf_1` = (0, +1.96, +0.35), shelf 2 0.40 m higher;
  - a **crate, sack or basket on the carpenter's slatted bench** at `slot_crate` = (x, -0.51, -0.71), standing on the bench without its old stand.
- **Fully stocked.** The old goods were spaced out so each could be clicked, which left bare board between them. After merging them, a stocking pass finds every bare stretch and fills it with the stall's own cheap stock, 8 to 40 triangles a piece:
  - each shelf gets a tall back row wherever nothing tall stands yet, and a low front row on bare board;
  - the rail gets a piece every 11 to 16 cm;
  - the counter gets a back row and a low middle row, and the front 12 cm stay clear for paying;
  - the bench crate gets a row of stock.

  The shelf braces at x = 0 and ±(W/2 - 0.25) are kept clear. Nothing passes through the back wall, a board or the counter top, and every piece stands 3 mm proud of its board. The seat check runs every scenery glb against its hut and finds no collisions.
- **Cost.** Everything is built at the lite level of detail. The full file is capped at 4,000 triangles (3,033 to 3,879 in practice). The lite file drops the smallest pieces first (strings, tags, wicks), then collapse-decimates to at most 1,500 triangles (1,408 to 1,455) and uses 512 px textures. Each full glb is 54 to 72 kB, and each lite glb is 31 to 41 kB.
- **Removed this round:** the round-8 `prop_deco_lebkuchen_shelf` / `_front` files and every old deco `act_` item with its `items.json` entry. Earlier today items.json held 309 entries; it now holds 231 (books, section goods and the ornament shop).
- `prop_deco_schmuck` (the old Christbaumschmuck counter) is rebuilt the same way, as scenery with no `act_` nodes. It stays listed under `retired` in props.json, for use only if `deco_schmuck.glb` is shown instead of `stall_schmuck.glb`. So nine `prop_deco_<key>` sets exist; eight are placed.

Previews: `deco_goods_contact_sheet.jpg` shows all eight stalls from the lane (camera 4.6 m out, 30 mm), and `stall_<key>.jpg` shows each one at 960×540. `stall_kerzen_lite.jpg` shows a lite file in its lite hut.

## 2. Ornament shop goods (`prop_schmuck_<group>`, in `stall_schmuck.glb`)

The carpenter's `stall_schmuck.glb` exists now, so the goods stand at its slots (`schmuck_slots.json`), not at deco_schmuck's.

| set | slot | what |
|---|---|---|
| prop_schmuck_rail_1 | slot_rail_1 | 16 glass baubles (`act_orn_bauble_0..15`, two octaves of notes) and the lit Herrnhut star `act_orn_herrnhut` (emissive `bulb_warm` core) |
| prop_schmuck_rail_2 | slot_rail_2 | `act_orn_pickle` hidden among green baubles (`act_orn_bauble_16..21`), pine cone, clip-on bird, mushroom, icicles, straw and carved stars, angels |
| prop_schmuck_rail_3 / _4 | slot_rail_3 / _4 | straw stars, carved wooden stars, an angel and icicles over the glass case and the tree |
| prop_schmuck_counter | slot_counter | nutcracker `act_orn_nutcracker` with `act_orn_nutcracker_jaw` (hinge origin), Räuchermännchen `act_orn_smoker` with `fx_smoke_1` at its mouth, Schwibbogen `act_orn_schwibbogen` with `act_orn_candle_0..6`, bauble trays |
| prop_schmuck_shelf | slot_shelf_1 (tiers 2 and 3 by offset) | ornament cartons, standing angels, straw stars on stands, menu board, two soldier nutcrackers (scenery) |
| prop_schmuck_case | slot_cabinet | velvet tray of mirror baubles, angels on the glass shelf (scenery) |
| prop_schmuck_tree | slot_tree | a 1.27 m display fir in a tub with 13 `hook_tree_<n>` empties |

There are 57 `act_orn_*` nodes, each with `name`, `label` and `action` in items.json: ring with a `note` (C5 upward), light, jaw, smoke, candles, hang, find, plus a reward flag on the pickle. Ornaments are pivoted at their hanging point; standing pieces are pivoted at their base. Changes this round:
- The rail-4 clip-on birds sat into the header, so rail 4 now carries icicles. The one clip-on bird is `act_orn_bird_0` on rail 2.
- The ribbon knots are now in the lite file too, so full and lite bounds match.
- The tree uses 12 segments in both files.
- The straw-star stands on tier 2 moved off the middle brace.
- The AO maps are 256/128 px, which keeps the shop at 1.97 MB of its 2 MB.

Shop total with goods: 39,785 of 40,000 triangles.

Previews: `stall_schmuck.jpg` (lane view) and `stall_schmuck_close.jpg` (counter and rails).

## 3. Bücherstand: face-out covers for the cabinets

Each `prop_books_<key>` (six sets, at `slot_cat_<key>`) reads the carpenter's `buecher_sections.json` and stands one `act_book_<nn>` per title face-out on the angled boards, at `cover_slots_x`. The top board is filled first, so any free place is at the bottom right. Each cover is designed in-house as one family per category: a colour, a pattern, the German category name, the title on a panel and the author in capitals. There is no publisher art.

Each book also keeps a spine and its `book_cover_<nn>` material. items.json carries name, title, author, slug, category, cover UV, lean and size. A cover's foot stands 4 mm in front of the backboard and leans with it at 15°.

This round:
- All six sets were rebuilt against the final cabinets, and the shelf and counter sets against the final books atlas.
- The filler spines on each cabinet's top board are now at most 0.16 m tall, so they stay clear of the cabinet's bulb strip.
- A price card on the counter moved off the stall's new counter frame.

Previews from the engine's `cam_cat` cameras: `prop_books_physics_cam_cat.jpg` (10 books), `prop_books_lives_cam_cat.jpg` (6) and `prop_books_people_cam_cat.jpg` (14, the fullest). Every title and author reads at that view.

## Section sets (unchanged this round)

The Glühwein, Bier and Wurst sets and the Bücherstand back shelves and counter keep their round-6/7 geometry and names (`act_mug_*`, `act_pot_lid`, `act_tap_0..2` pivoting at their base, `act_glass_*` with foam, `act_grill`, `act_sausage_*`, `act_bottle_*`, `act_wineglass_*`). To save Mac's usage, I did not render them again. Their latest close-ups are copied in as `section_<set>_r3.jpg` and `section_<set>_r6.jpg`, named after the round they were rendered in. The book shelves and counter were rebuilt, but their layout did not change.

## Budgets

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2610 (35%) | 183 / 99 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 6254 | 2051 (33%) | 164 / 82 | 2.29 × 0.24 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 5428 | 2194 (40%) | 144 / 98 | 2.33 × 0.23 × 0.42 |
| prop_bier_counter | bierstand | slot_counter | 8628 | 3266 (38%) | 185 / 114 | 2.37 × 0.45 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 4356 | 1812 (42%) | 102 / 53 | 2.33 × 0.25 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3194 | 1566 (49%) | 56 / 33 | 1.91 × 0.23 × 0.26 |
| prop_wurst_counter | bratwurst | slot_counter | 18324 | 5630 (31%) | 435 / 217 | 3.42 × 0.48 × 0.64 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1624 | 464 (29%) | 61 / 24 | 1.86 × 0.22 × 0.28 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1588 | 440 (28%) | 59 / 23 | 1.86 × 0.19 × 0.27 |
| prop_books_counter | buecherstand | slot_counter | 2144 | 900 (42%) | 66 / 38 | 2.09 × 0.45 × 0.40 |
| prop_books_physics | buecherstand | slot_cat_physics | 862 | 256 (30%) | 59 / 37 | 0.78 × 0.14 × 0.68 |
| prop_books_lives | buecherstand | slot_cat_lives | 514 | 184 (36%) | 42 / 27 | 0.47 × 0.13 × 0.68 |
| prop_books_mind | buecherstand | slot_cat_mind | 916 | 272 (30%) | 60 / 35 | 0.78 × 0.13 × 0.68 |
| prop_books_people | buecherstand | slot_cat_people | 946 | 312 (33%) | 69 / 45 | 0.78 × 0.13 × 0.94 |
| prop_books_decisions | buecherstand | slot_cat_decisions | 790 | 248 (31%) | 59 / 37 | 0.62 × 0.13 × 0.94 |
| prop_books_craft | buecherstand | slot_cat_craft | 694 | 224 (32%) | 46 / 26 | 0.78 × 0.13 × 0.41 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 3814 | 1455 (38%) | 72 / 41 | 2.54 × 2.76 × 1.76 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 3612 | 1448 (40%) | 70 / 37 | 3.07 × 2.72 × 1.76 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3879 | 1408 (36%) | 65 / 34 | 2.09 × 2.76 × 1.74 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 3872 | 1444 (37%) | 71 / 35 | 2.72 × 2.76 × 1.77 |
| prop_deco_kaese | deco-kaese | slot_counter | 3880 | 1436 (37%) | 54 / 32 | 2.23 × 2.76 × 1.75 |
| prop_deco_crepes | deco-crepes | slot_counter | 3752 | 1446 (39%) | 56 / 33 | 2.40 × 2.76 × 1.82 |
| prop_deco_maroni | deco-maroni | slot_counter | 3033 | 1455 (48%) | 66 / 34 | 2.24 × 2.74 × 1.78 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 3862 | 1433 (37%) | 63 / 34 | 2.91 × 2.76 × 1.77 |
| prop_schmuck_rail_1 | deco-schmuck | slot_rail_1 | 2378 | 1674 (70%) | 114 / 95 | 2.23 × 0.22 × 0.37 |
| prop_schmuck_rail_2 | deco-schmuck | slot_rail_2 | 2067 | 1525 (74%) | 115 / 99 | 2.31 × 0.08 × 0.33 |
| prop_schmuck_rail_3 | deco-schmuck | slot_rail_3 | 404 | 343 (85%) | 30 / 27 | 0.60 × 0.05 × 0.27 |
| prop_schmuck_rail_4 | deco-schmuck | slot_rail_4 | 252 | 204 (81%) | 24 / 21 | 0.51 × 0.02 × 0.19 |
| prop_schmuck_counter | deco-schmuck | slot_counter | 2668 | 1543 (58%) | 84 / 61 | 2.35 × 0.37 × 0.39 |
| prop_schmuck_shelf | deco-schmuck | slot_shelf_1 | 1910 | 1632 (85%) | 55 / 47 | 2.48 × 0.24 × 0.91 |
| prop_schmuck_case | deco-schmuck | slot_cabinet | 1358 | 1053 (78%) | 42 / 33 | 0.63 × 0.28 × 0.46 |
| prop_schmuck_tree | deco-schmuck | slot_tree | 744 | 480 (65%) | 30 / 21 | 0.66 × 0.66 × 1.27 |

All prop glbs together: 2.80 MB full and 1.67 MB lite. Shared textures (`prop_tex_*`): 1.94 MB full and 0.28 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2000 headroom):

| stall | stall tris | + props | total / budget | headroom | MB / budget |
|---|---|---|---|---|---|
| gluehwein | 38780 | 19132 | 57912 / 60k OK | 2088 | 2.32 / 3 |
| bierstand | 41453 | 16178 | 57631 / 60k OK | 2369 | 2.27 / 3 |
| bratwurst | 38378 | 18324 | 56702 / 60k OK | 3298 | 2.27 / 3 |
| buecherstand | 51428 | 10078 | 61506 / 80k OK | 18494 | 3.19 / 4 |

Deco stalls, stall plus its one scenery goods set against 20k (the ornament shop, stall_schmuck.glb, with its eight goods sets against 40k and 2 MB; check_props fails over):

| deco stall | stall tris | goods | total / budget | room | act_ nodes (0: scenery) | MB with goods |
|---|---|---|---|---|---|---|
| lebkuchen | 8813 | 3814 | 12627 / 20k OK | 7373 | 0 | 1.09 |
| mandeln | 9098 | 3612 | 12710 / 20k OK | 7290 | 0 | 1.08 |
| kerzen | 8372 | 3879 | 12251 / 20k OK | 7749 | 0 | 1.07 |
| spielzeug | 9633 | 3872 | 13505 / 20k OK | 6495 | 0 | 1.10 |
| schmuck | 28004 | 11781 | 39785 / 40k OK | 215 | 57 | 1.97 |
| kaese | 7023 | 3880 | 10903 / 20k OK | 9097 | 0 | 1.01 |
| crepes | 7507 | 3752 | 11259 / 20k OK | 8741 | 0 | 1.04 |
| maroni | 7336 | 3033 | 10369 / 20k OK | 9631 | 0 | 1.08 |
| puffer | 8921 | 3862 | 12783 / 20k OK | 7217 | 0 | 1.08 |

<!-- check_props:end -->

## Open issues and next steps

- **Engine:** the deco `act_` goods are gone. Any deco click code in `site/src/actions/items/deco.js` (the engineer's) should be removed or left inert. The scenery sets load like any other set at `slot_counter`.
- **Lite ratio warnings:** some lite files are above 38 % of their full file, so check_props warns:
  - the deco scenery, because the full file is already built at lite detail;
  - the ornament shop's shelf (85 %), case (78 %) and counter (58 %), where cartons and boxes cannot lose much;
  - the long-standing bier back and shelf.

  All are warnings, not budget failures.
- **Deco "MB with goods" column:** it reads 1.01 to 1.10 MB against the 1 MB budget, but the column is conservative. It adds the six shared `prop_tex_atlas_*` / `prop_tex_market_*` maps (0.77 MB) to each stall, even though the browser loads them once for the whole market and the section stalls already need them. What a deco stall actually costs is its hut glb (0.19 to 0.26 MB) plus its goods glb (54 to 72 kB), so 0.24 to 0.33 MB.
- **Ornament shop headroom:** the shop has 215 triangles of headroom (39,785 / 40,000) and 0.03 MB (1.97 / 2 MB). Any new ornament needs a trim elsewhere.
- **Lite rail goods:** in the lite file the smallest rail goods (some braids, tapers) are pruned. From the lane the rail then reads thinner than in the full file.
- **Section previews:** they are copies from rounds 3 and 6. A fresh set of section close-ups should be rendered once there is usage to spare.
- No contract breaks. One note for BUILD.md: a deco stall's goods are now one set at `slot_counter` that reaches `slot_rail_1`, the shelves and `slot_crate` through fixed offsets. props.json marks these sets `"seat": "span"`.
