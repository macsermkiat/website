# Vendor, round 2 notes

All goods are modelled in code under `blender/props/` and textured from two procedural atlases (goods and books). No third-party models or images are used; the fonts are OFL and already credited (CREDITS.md, Vendor section), so **CREDITS.md is unchanged** this round. All 19 sets (full and lite, with the AO bake), both atlases, props.json and items.json were rebuilt on the cloud machine in round 2; pass 2 (below) rebuilt the atlases again and the sets it changed. *Previews* lists which preview comes from which pass, with each file's timestamp.

Rebuild and check:

```
python3 blender/props/vendor_atlas.py                                   # atlases -> blender/out/vendor/
blender/props/run_build.sh <log-tag> [--only a,b] [--no-render] [--no-lite] [--no-ao] [--samples 48] \
    [--res 1280x720] [--render-only a,b] [--shots wide,hero,stall] [--sheet-only]
    # runs build_props.py with NM_DEVICE / NM_THREADS (default CPU / 2); log in blender/out/vendor/logs/<tag>.log
python3 blender/props/check_props.py [--notes]     # contract checks, exit 1 on FAIL; --notes rewrites the tables below
node blender/props/grill_probe.mjs                  # where the Bratwurst stall's grill seat is (set_wurst runs it)
```

bpy may segfault on exit after `build_props.py` has written everything; the outputs are complete.

**Build launches are guarded.** In the interrupted round-2 run a build was launched as `... > $LOG/books_deco.log` with `$LOG` empty, so the log landed at `/books_deco.log`, outside the repo. Two guards now stop that: `run_build.sh` derives every path from its own location (no caller variables), refuses a log tag that is empty or holds anything but letters, digits, `.`, `_`, `-`, and checks the log folder is `blender/out/vendor/logs` inside the repo. `build_props.py` itself (`guard_paths()`) refuses to start unless the repo root holds `docs/BUILD.md` and each output folder (review/round-2/vendor, site/public/models, blender/out, blender/out/vendor and its renders) resolves to exactly the vendor's path inside it.

## What changed in round 2

| # | Judges' fix / brief item | What I did | Checked by |
|---|---|---|---|
| 1 | NOTES had the wrong reading-list node ids and claimed the previews stood in the carpenter's stall | The ids below are read from the new items.json (`act_book_10..16`). This file now says plainly which previews use the generic plain counter (all counter/shelf/deco shots, from `vstage.env_counter()`) and which use the carpenter's shipped stall glb (only the two `prop_wurst_counter_in_stall*` shots). | items.json, this file |
| 2 | Bier hero cut off the tap handles | New hero camera further back and higher: the three tap handles, the tower, the drip tray glass and the foam heads of the front glasses are all in frame (`prop_bier_counter_hero.jpg`). | the shot |
| 3 | Foam read as white caps | `goods.beer_fill`: the head sits inside the rim (crown rings start just inside the glass wall, cream colour `#f3e6c8`, not white), rises into a domed crown (dome ≤ 2 cm, 0.36 × rim radius; Weizen 2.4 cm), and every other glass has a spill: a tapering foam tube running down the outside toward the visitor and ending in a bead. The foam stays its own `foam_<n>` child of `act_glass_<n>`. | hero shot |
| 4 | Reading lamp has no light_ empty and NOTES did not say so | Recorded below under *Contract questions*, with the question to the market owner. | this file |
| 5 | Repeated book titles (55 unique of 108, The Mind's I twice) | The books atlas now holds 135 generic titles plus the named five (86 new real titles, each with its full author list). Shelf 1 and shelf 2 draw from two disjoint pools (`set_books.shelf_pools()`), the counter from its own list, and the builder raises if any pool runs out, so no title can repeat. **106 books, 106 different titles** (checked in items.json). The atlas grew in height to fit the covers: 2048 × 3584. | items.json |
| 6 | Deco counters sparse; deco headroom thin | Cheap flat and instanced goods on every deco counter: kraft price tags (one atlas tile, 8 prices) on all nine; Lebkuchen: slanted display board of hearts, stacks of red-and-gold Elisen tins, gift boxes; Mandeln: bag pile, crate of paper cones; Kerzen: basket of beeswax candles; Spielzeug: extra blocks, plywood stars; Schmuck: three open cartons of baubles with their lids up, a tabletop tree, a glass spire, loose baubles; Käse: wheel tower, slate of cubes with toothpicks, wedge basket; Crêpes: banana bowl, apple jar, plate stack, fork cup; Maroni: lying bags, burlap sack of chestnuts, charcoal bucket; Puffer: potato crate, oil bottle, salt shaker, jars. Headroom was bought back at the same time (Schmuck carton baubles lost their caps, cheaper Spielzeug tops, train, Spanbäume and pyramid): see the deco table for what is left under 20k. | deco table, contact sheet |
| 7 | Bratwurst counter middle empty | The carpenter's round-2 stall has one continuous counter with the grill standing on it under the hood (`slot_grill`). Left to right: charcoal sack and ash bucket, the grill, the warming tray with six sausages, a steel tray of raw Bratwurst (new), the basket of 14 rolls and a bag with two more, mustard and ketchup pots, fork cup, paper trays, a Bratwurst and a Currywurst served, squeeze bottles, napkins, tip jar, bread board and the chalk sign. | hero and in-stall shots |
| 8 | Brief: Glühwein wine shelf, 8–12 bottles with legible labels and wine glasses | `prop_gluehwein_wine`: **12 bottles** (`act_bottle_0..11`) with their own labels (two new: a Baden Weißherbst rosé and a Nahe Riesling Auslese), on a rack of 8, in a crate and in a box; **5 wine glasses** (`act_wineglass_0..4`, one rosé). Each bottle's items.json entry has `wine`, `grape`, `region`, `vintage`, `producer`, `colour` and `country`. | items.json, wine hero |
| 9 | Brief: Bratwurst grill with coal_glow seated in the stall's grill opening | The carpenter removed his built-in grill and ships a `slot_grill` empty. `grill_probe.mjs` reads the stall glb at build time (slot_grill, counter extent, hood, floor under the hood) and `set_wurst.seat()` stands `act_grill` on that point: three splayed legs, fire bowl (rim 18 cm above the counter), 44 coals with `coal_glow`, gallows post on the left with `act_grill_swing` (15-bar grate on three chains, 5 cm over the rim) and `act_smoke`. `prop_wurst_counter_in_stall*.jpg` show it inside the real stall under the hood. | in-stall shots, seat check |
| 10 | Brief: base pivots for every clickable item | Mugs, glasses (foam as child), bottles, wine glasses, books, rolls, served trays and now **sausages** have their origin at the point they rest on (check_props enforces this, including `act_sausage_*` and `act_grill`). See *Sausage pivots* for what that means for the engine's turn. | check_props |
| 11 | Brief: props.json machine-readable per set | props.json keeps the `sets` list the engine reads and adds `by_set`: `{set: {slot, stall, model, lite, asset}}`. check_props fails if the two disagree. | check_props |
| 12 | Close-ups must show glowing coals (brief: emissive `coal_glow`) | The coal bed read as dull lumps with a few orange lines (2.5 % of the emission map lit). `atlas_goods.coal_emit` now lights wider cracks on more of the lumps and adds a dull ember glow over the hot patches the ash has not covered (about 28 % of the map above 0.3). Same material name, same small 256 px texture pair (`prop_tex_coal_*`). | `prop_wurst_counter_hero.jpg`, `prop_wurst_counter_in_stall_grill.jpg` |
| 13 | Warming-tray sausages poked through the tray's front wall in the last hero | They now lie along the tray's long side (x), five side by side and one on top; the raw-sausage tray does the same. The glb and every Bratwurst shot were rebuilt after the fix. | hero and in-stall shots, seat check |

## Round 2, pass 2: the panel's fixes

| # | Panel's fix | What I did | Checked by |
|---|---|---|---|
| P1 | Lite beer foam rose into a 65 cm column on all nine glasses (lite bbox height 0.92 m against 0.63 m) | The bug was in `goods.beer_fill`: lite keeps crown rings 0, 2, 4, 6, and the height branch keyed off the position in the trimmed list, so old ring 4 (a dome fraction, 0.66) was read as metres. The loop now carries each ring's original index (`orig`), so only old rings 1–2 use their height as metres. The lite head also gets a coarser spill on the same glasses as the full one, so both have the same reach. `prop_bier_counter.lite.glb` was rebuilt: its bbox height is now **0.628 m**, the same as the full set, and each `foam_<n>` sits inside its glass: the lite heads' top heights match the full ones within 1 mm (0.224–0.281 m). The worst full/lite difference in the whole set is now 1.4 cm, on a mesh, under the 2 cm limit. | check_props bounds parity |
| P2 | check_props must catch a lite set whose shapes diverge | New check `check_bounds_parity`: for every set it compares each **act_ node's subtree** world bbox, full against lite (fails over **1 cm**), and each **named mesh node's** bbox (fails over **2 cm**). It reads the glTF accessor min/max through the node transforms, so the quantised positions are handled. On the round-2 glbs it caught the foam (64 cm) and four smaller ones: the ladle's hook dropped in lite (2.4 cm), the 10-sided lite kettle lid (1.0 cm), the books-counter cash box losing two loose coins (3.6 cm) and the 7-sided lite almond kettle (2.3 cm). All four are fixed: the lite hook is kept, and the lid and kettle use 12 and 8 sides (multiples of 4 keep the front, back and side extremes). The worst difference per set is printed on every run. | check_props |
| P3 | Re-render the Bratwurst hero from the final glb; grilled sausages browned and charred, raw ones pale | The grilled skins are darker (base `#72361a`, the warming tray's `#4a1e0c`), with heavier black grate stripes, a wider scorched halo round them and black flecks where fat flared. The raw tray now uses a pale, pinkish-beige satin skin (`goods.sausage(raw=True)`) with no browning and no marks. The hero, wide and both in-stall shots were rendered from the glb written in the same run. | `prop_wurst_counter_hero.jpg` |
| P4 | Coals should read as embers | The coal maps are split in two. The left half is the burning sides: bright cracks and a red ember glow on the char between them. The right half is ash: grey-white, dark, with only faint lines. `set_wurst.coal_lump` maps each lump's side faces into its own random window of the hot half and its upward faces into a window of the ash half (one lump in five burns through its top). Every lump is different: bright cracks, dark ash tops. The bed also has six grey dead coals near the rim (plain charcoal under ash, no glow), a ring of pale ash drifted against the bowl wall and seven flat ash flakes on top. Measured emission coverage (`coal_emit.png`, red above 0.3): **36 % of the map; 71.5 % of the hot half, 0.4 % of the ash half**. (The round-2 note claimed about 28 %; this is the measured figure for the new map.) The in-stall grill close-up is rendered with the stall lamps and fill at 20 % (`stall_dim` in set_wurst) so the bed's own glow shows. The full-lit wide in-stall shot is unchanged. | `prop_wurst_counter_hero.jpg`, `prop_wurst_counter_in_stall_grill.jpg` |
| P5 | Foam looked like felt pads | Each head has its own dome height (±25 %), a peak pushed off centre and broad swells on top of the fine lumps, so no two heads match. The foam has its own material `vendor_foam`: the atlas bubbles, subsurface scatter in the Cycles previews, and a soft sheen that is exported (KHR_materials_sheen). The foam region of the atlas now holds two textures. The crown has three sizes of bubbles, with darker rims, highlights, glossier large bubbles, burst craters and slightly amber thin spots. The **wet edge** strip is used by the band against the glass and the run over the rim: darker yellow cream, big glossy bubbles and lacing streaks. | `prop_bier_counter_hero.jpg` |
| P6 | Fill the middle of the Maroni, Käse and Kerzen counters (and Crêpes and Kartoffelpuffer); win back Maroni's margin | **Maroni:** a red-enamelled shop scale with a brass pan of chestnuts, a wooden stand of four kraft cones heaped with chestnuts, and a stack of flat folded bags beside the bowl. The roaster's ribbed chestnuts were replaced by a smooth, flattened five-sided nut with a pale base (about 33 triangles, was 70), and the striae that read as ribs were toned down in the atlas. The roaster went from 32 to 24 segments and from 10 to 6 hidden coal lumps, and the pan holds 19 chestnuts instead of 24. Maroni is now under its old count with the new goods on it (see the deco table). **Käse:** three wedges wrapped in wax paper (the paper up the rind, the cut face showing) and a round board with a piece of Bergkäse and a cheese knife. **Kerzen:** an open white box of dinner candles with its lid leaning behind, and five ribboned gift boxes of tealights along the front of the risers. **Crêpes:** a little board with sugar and cinnamon shakers and two lemon halves, and a stack of paper napkins. **Kartoffelpuffer:** a served paper plate of three Puffer with applesauce and a wooden fork, and a spatula by the pan. | contact sheet, deco frames, deco table |
| P7 | NOTES: drop the turn_axis request; make preview recency match the files | The request is gone: `site/src/actions/items/wurst.js` `turnCentre()` already turns each sausage about `turn_axis`. *Previews* now gives every file's timestamp and the pass it comes from. | this file |
| P8 | Ask the market owner to delete /books_deco.log; guard build launches | See *Requests to the market owner*, and the guard note at the top. | `run_build.sh`, `build_props.guard_paths()` |
| P9 | Optional: lite ratios near 35 %; the remaining wide shots | Lebkuchen lite hearts drop their back face (every heart faces the visitor) and use 10 sides, and the Schmuck lite cartons keep 5 baubles of 12. Lebkuchen lite went from 41 % to **34 %**. Schmuck only went from 45 % to 43 %. Bier back, Mandeln and Spielzeug are unchanged (see *Open issues*). New wide shots: `prop_bier_counter.jpg`, `prop_wurst_counter.jpg`, `prop_books_counter.jpg`. | table, previews |

## Sets, slots and budgets

The tables between the markers are written by `check_props.py --notes` from the glbs on disk (the carpenter's current stalls and my sets), so they cannot go stale: rerun it after any stall or prop rebuild.

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2610 (35%) | 183 / 99 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 6254 | 2051 (33%) | 164 / 82 | 2.29 × 0.24 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 5268 | 1856 (35%) | 111 / 66 | 2.33 × 0.23 × 0.42 |
| prop_bier_counter | bierstand | slot_counter | 9498 | 3442 (36%) | 183 / 108 | 2.01 × 0.39 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 4356 | 1812 (42%) | 102 / 53 | 2.33 × 0.25 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3746 | 1380 (37%) | 58 / 33 | 1.91 × 0.23 × 0.26 |
| prop_wurst_counter | bratwurst | slot_counter | 20946 | 5808 (28%) | 427 / 197 | 3.42 × 0.48 × 0.64 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1300 | 408 (31%) | 132 / 102 | 1.86 × 0.23 × 0.30 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1444 | 464 (32%) | 150 / 116 | 1.86 × 0.22 × 0.30 |
| prop_books_counter | buecherstand | slot_counter | 2078 | 796 (38%) | 91 / 60 | 2.05 × 0.43 × 0.40 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 5102 | 1750 (34%) | 127 / 53 | 2.20 × 0.45 × 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 2774 | 1184 (43%) | 78 / 41 | 1.98 × 0.48 × 0.44 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3790 | 1428 (38%) | 95 / 44 | 2.11 × 0.48 × 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 2836 | 1196 (42%) | 102 / 49 | 2.01 × 0.46 × 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 2788 | 1188 (43%) | 79 / 39 | 2.16 × 0.39 × 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 4556 | 1768 (39%) | 92 / 46 | 2.02 × 0.48 × 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 3648 | 1386 (38%) | 83 / 45 | 2.06 × 0.47 × 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4104 | 1656 (40%) | 110 / 51 | 2.18 × 0.47 × 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 4220 | 1413 (33%) | 99 / 47 | 2.06 × 0.48 × 0.27 |

All prop glbs together: 2.47 MB full and 1.33 MB lite. Shared textures (`prop_tex_*`): 1.33 MB full and 0.20 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use; check_props fails under 2k headroom):

| stall | stall tris | + props | total / 60k | headroom | MB / 3 |
|---|---|---|---|---|---|
| gluehwein | 37603 | 18972 | 56575 OK | 3425 | 1.89 |
| bierstand | 39745 | 17600 | 57345 OK | 2655 | 1.85 |
| bratwurst | 36391 | 20946 | 57337 OK | 2663 | 1.80 |
| buecherstand | 34583 | 4822 | 39405 OK | 20595 | 2.62 |

Deco stalls, stall plus goods against 20k (check_props fails over):

| deco stall | stall tris | goods | total / 20k | room |
|---|---|---|---|---|
| lebkuchen | 13433 | 5102 | 18535 OK | 1465 |
| mandeln | 15985 | 2774 | 18759 OK | 1241 |
| kerzen | 14143 | 3790 | 17933 OK | 2067 |
| spielzeug | 15938 | 2836 | 18774 OK | 1226 |
| schmuck | 15799 | 2788 | 18587 OK | 1413 |
| kaese | 13380 | 4556 | 17936 OK | 2064 |
| crepes | 13283 | 3648 | 16931 OK | 3069 |
| maroni | 14346 | 4104 | 18450 OK | 1550 |
| puffer | 14978 | 4220 | 19198 OK | 802 |

<!-- check_props:end -->

## Animation nodes and pivots

Every act_ / rot_ node is an empty with the pivot as its origin; its geometry is a `<name>_mesh` child, because the optimiser rewrites mesh-node transforms. items.json gives each node's display name and `pivot`.

- **Glühwein counter (`slot_counter`):** `act_pot` (kettle, origin at the burner's foot), `act_pot_lid` (hinged at the back rim, ships 14° ajar), `act_ladle`, `act_steam`, `act_mug_0..9` (0 and 5 are boots; 0, 1, 3, 4 full with `act_steam_<i>`; 6–9 upside down on the drying board, origin on the rim).
- **Glühwein shelf (`slot_shelf_1`):** `act_bottle_12..17` (Winzer-Glühwein red ×2, white Riesling Glühwein, blueberry Glühwein, rum for a Schuss, Kinderpunsch; items carry grape and region where there is one), spare mugs `act_mug_10..15` (15 is a boot), spices, orange slices, anise bowl.
- **Wine shelf (`slot_shelf_2`):** `act_bottle_0..11`, `act_wineglass_0..4` (see row 8 above).
- **Bier counter:** `act_tap_0..2` (pivot at the handle's base on the faucet; rotating X tips it forward), `act_glass_0..8` (Maß, Willibecher and a Weizenglas; 8 stands on the drip tray under the middle tap), each with a `foam_<n>` child holding only the foam.
- **Bier shelf:** `act_glass_10..18`, clean glasses upside down (origin on the rim), including three Weizen glasses.
- **Bratwurst:** `act_grill` (origin on the counter at the carpenter's `slot_grill`, under the bowl's centre), `act_grill_swing` (grate, pivot at the hook), `act_sausage_0..9` on the grate as children of the swing, `act_sausage_10..15` in the warming tray, `act_roll_0..15`, `act_served_0` (Bratwurst) and `act_served_1` (Currywurst), `act_smoke`. The coals are a child of the grill with material `coal_glow`.
- **Sausage pivots:** base, as the brief asks: origin under the middle of the sausage where it rests, long axis along the node's X. Every sausage's items.json entry has `turn_axis: {axis: "node X", offset_blender_z: 0.0125, offset_threejs_y: 0.0125}`: the axis it turns about lies 12.5 mm above the origin. The engine already honours it (`turnCentre()` in `site/src/actions/items/wurst.js`).
- **Bücher:** `act_book_0..` shelf 1 (43 books), `act_book_100..` shelf 2 (50), `act_book_200..212` counter (13). Standing books have their origin at the foot of the spine (a pull-out moves along −Y toward the visitor); lying books under the middle of their lowest face. Each has material `book_cover_<n>`, and title, author and cover material in its glTF node extras and in items.json.
- **Deco:** `rot_pyramid` on the Holzspielzeug counter.

The five reading-list titles stand together on shelf 1, left of the middle brace, as **`act_book_10..16`** (the same ids in the lite set): `act_book_10` The Order of Time (Carlo Rovelli); `act_book_11` Gödel, Escher, Bach (Douglas R. Hofstadter); `act_book_12..14` The Feynman Lectures on Physics, Vol. I–III (Feynman, Leighton, Sands); `act_book_15` Being You (Anil Seth); `act_book_16` The Book of Why (Judea Pearl and Dana Mackenzie). `prop_books_shelf_1_hero.jpg` shows the spines.

## Previews

All in `review/round-2/vendor/`, rendered on this machine (Cycles, CPU, 1280×720, 48 samples). The times are the files' modification times (UTC).

**Staging.** Every counter, shelf and deco shot stands the set on a **generic plain wooden counter or shelf board**, not in the carpenter's stall glb. The board is built by `vstage.env_counter()`, shot at night with two warm point lights where the stall's light_ empties are. The exception is the Bratwurst counter, where the grill has to prove it sits in the stall. `prop_wurst_counter_in_stall.jpg` and `prop_wurst_counter_in_stall_grill.jpg` load the carpenter's shipped `site/public/models/stall_bratwurst.glb` and put the set at its `slot_counter` (`vstage.stall_scene`). They are lit by the stall's own light_ empties plus an ember light in the bowl. The grill close-up has the lamps and fill at 20 %.

**Pass 2 (2026-10-04), rendered from the glbs written in the same build run:**

| file | time | shows |
|---|---|---|
| `prop_bier_counter.jpg` | 00:23 | wide: the whole Bier counter (new) |
| `prop_bier_counter_hero.jpg` | 00:36 | close-up: tap handles, the new foam heads with wet edges and spills |
| `prop_wurst_counter.jpg` | 00:49 | wide: the whole Bratwurst counter (new) |
| `prop_wurst_counter_hero.jpg` | 01:00 | close-up: ember bed, charred sausages on the grate, warming tray, pale raw tray |
| `prop_wurst_counter_in_stall.jpg` | 01:16 | the set in the carpenter's stall, full stall light |
| `prop_wurst_counter_in_stall_grill.jpg` | 01:34 | grill close-up in the stall, lamps dimmed so the coal glow reads |
| `prop_books_counter.jpg` | 01:41 | wide: the whole Bücher counter (new) |
| `prop_books_counter_hero.jpg` | 01:45 | close-up: open books, banker's lamp, cash box (unchanged set, re-rendered) |
| `deco_lebkuchen.jpg`, `deco_mandeln.jpg`, `deco_kerzen.jpg`, `deco_schmuck.jpg`, `deco_kaese.jpg`, `deco_crepes.jpg`, `deco_maroni.jpg`, `deco_puffer.jpg` | 00:21–01:38 | the eight deco frames whose sets were rebuilt this pass |
| `deco_goods_contact_sheet.jpg` | 01:45 | all nine deco frames (built only from the vendor's own frames in `blender/out/vendor/renders/`) |

**From round 2, pass 1 (2026-09-30).** These sets were not changed in pass 2. The atlas regions pass 2 repainted (foam, sausage skin, coal, chestnut) do not appear in these shots.

| file | time | shows |
|---|---|---|
| `prop_gluehwein_counter.jpg` | 00:36 | wide: the whole Glühwein counter |
| `prop_gluehwein_counter_hero.jpg` | 00:48 | kettle, ladle, mugs. In pass 2 the full set is unchanged; only its lite lid and ladle hook changed. |
| `prop_gluehwein_shelf_hero.jpg` | 00:59 | bottles, spices, oranges |
| `prop_gluehwein_wine_hero.jpg` | 01:08 | wine labels |
| `prop_bier_back_hero.jpg` | 01:27 | barrels and chalkboard |
| `prop_bier_shelf_hero.jpg` | 01:36 | clean glasses |
| `prop_books_shelf_1_hero.jpg` | 02:43 | the five reading-list spines |
| `prop_books_shelf_2_hero.jpg` | 02:58 | shelf 2 |
| `deco_spielzeug.jpg` | 03:37 | Holzspielzeug (set unchanged) |

There are still no wide shots for the Glühwein shelves, the Bier back and shelf, and the two Bücher shelves. Their hero shots already frame most of each shelf.

## Requests to the market owner

- **Reading lamp without a light_ empty.** The brief asks for a reading lamp with a light_ empty on the Bücher counter. docs/BUILD.md caps a section stall at 2 light_ empties, and `stall_buecher.glb` already carries both, so the lamp in `prop_books_counter` is modelled (a banker's lamp: brass base and stem, green cased-glass shade, warm emissive bulb) but has **no light_ node**, and check_props fails any prop set that adds one. Question: should the lamp take one of the stall's two lights (the carpenter would drop one of his and I would add `light_lamp` at the bulb), or stay unlit as now?
- **2048 px textures.** The contract's standard step is 1024. The goods atlas is 2048 × 2048 because wine labels, tin lids and the price tags need it to be legible in close-up; the books colour atlas is 2048 × 3584 so every spine title reads (its normal and roughness maps are cut to 1024 × 1792, which read the same). Lite glbs use 512-wide versions of all of them. Shared textures total about 1.3 MB (full) and are loaded once for all sets. The books atlas height (3584) is not a power of two; three.js on WebGL2 mips it fine, but a KTX2/Basis step would need it padded to 4096. Please confirm 2048 is acceptable, or I drop the goods atlas to 1024 and accept softer labels.
- **Please delete `/books_deco.log` by hand.** It is a 1.4 MB build log from the interrupted round-2 run, at the root of the filesystem and outside the repo. A shell variable was empty when that build was launched. The vendor session cannot remove it (Claude Code's safety check blocks deleting files in `/`). It has no other effect, and the launch guards above stop it from happening again.

## Open issues

- **Headroom depends on the carpenter's stalls.** The tables above are measured against the stall glbs on disk today. Bier and Bratwurst are the tightest section stalls (2655 and 2663 triangles of headroom). If Bier grows, the first cuts are the shelf glasses and the bottle crate on the back shelf; if Bratwurst grows, the raw-sausage tray and the paper-tray stack.
- **Grill seat follows the carpenter.** `set_wurst` reads `slot_grill` from `stall_bratwurst.glb` at build time (falling back to a probe of the counter and hood). If the carpenter moves `slot_grill`, rebuild `prop_wurst_counter`; the whole serving line then shifts to start right of the grill.
- **Lite glass and foam.** Full glbs use transmission glass; lite keeps the same material names with alpha blending, so the site's lite path must not expect KHR_materials_transmission. `vendor_foam`'s subsurface scatter shows only in the Cycles previews (glTF has no subsurface); the glb carries its atlas textures and KHR_materials_sheen.
- **Lite ratios (WARN, not FAIL).** Lebkuchen is now at 34 %. Still above the 38 % warning line: Bier back 42 %, Mandeln 43 %, Spielzeug 42 %, Schmuck 43 % (its cartons were trimmed, but the hanging baubles and the tree are already at their minimum segments), and Käse 39 % and Maroni 40 %, because the new middle goods are boxes and low-segment lathes that lite cannot cut further.
- **Raw sausages may read too white** in the warm wide shots. They are a pale pinkish beige (`#dcc4b0`, satin), which the warm key light pushes toward white; a slightly pinker tone is a one-line change in `goods.sausage(raw=True)`.
- **Maroni room** is back to about 1550 triangles under 20k (it was 468), with the new middle goods on the counter. Puffer is now the tightest deco stall (802 left).
- **Build process.** `build_props.py` merges each set's entry into `blender/out/props_report.json` on write (re-read, atomic replace), so two builds for different sets can run side by side, as they did in this pass. Launches go through `run_build.sh` (see the guard note at the top).
- **Seat-check limits.** `seat_check.mjs` flags prop triangles crossing stall triangles and objects buried under a stall top; it does not flag a prop floating above a surface.
