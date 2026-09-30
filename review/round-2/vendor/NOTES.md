# Vendor, round 2 notes

All goods are modelled in code under `blender/props/` and textured from two procedural atlases (goods and books). No third-party models or images are used; the fonts are OFL and already credited (CREDITS.md, Vendor section), so **CREDITS.md is unchanged** this round. Everything below was rebuilt on the cloud machine in this round: both atlases, all 19 sets (full and lite, with the AO bake), props.json, items.json and every preview in this folder.

Rebuild and check:

```
python3 blender/props/vendor_atlas.py                                   # atlases -> blender/out/vendor/
NM_DEVICE=CPU NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/props/build_props.py \
    [--only a,b] [--no-render] [--no-lite] [--no-ao] [--samples 48] [--res 1280x720] \
    [--render-only a,b] [--shots wide,hero,stall] [--sheet-only]
python3 blender/props/check_props.py [--notes]     # contract checks, exit 1 on FAIL; --notes rewrites the tables below
node blender/props/grill_probe.mjs                  # where the Bratwurst stall's grill seat is (set_wurst runs it)
```

bpy may segfault on exit after `build_props.py` has written everything; the outputs are complete.

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

## Sets, slots and budgets

The tables between the markers are written by `check_props.py --notes` from the glbs on disk (the carpenter's current stalls and my sets), so they cannot go stale: rerun it after any stall or prop rebuild.

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->
<!-- check_props:end -->

## Animation nodes and pivots

Every act_ / rot_ node is an empty with the pivot as its origin; its geometry is a `<name>_mesh` child, because the optimiser rewrites mesh-node transforms. items.json gives each node's display name and `pivot`.

- **Glühwein counter (`slot_counter`):** `act_pot` (kettle, origin at the burner's foot), `act_pot_lid` (hinged at the back rim, ships 14° ajar), `act_ladle`, `act_steam`, `act_mug_0..9` (0 and 5 are boots; 0, 1, 3, 4 full with `act_steam_<i>`; 6–9 upside down on the drying board, origin on the rim).
- **Glühwein shelf (`slot_shelf_1`):** `act_bottle_12..17` (Winzer-Glühwein red ×2, white Riesling Glühwein, blueberry Glühwein, rum for a Schuss, Kinderpunsch; items carry grape and region where there is one), spare mugs `act_mug_10..15` (15 is a boot), spices, orange slices, anise bowl.
- **Wine shelf (`slot_shelf_2`):** `act_bottle_0..11`, `act_wineglass_0..4` (see row 8 above).
- **Bier counter:** `act_tap_0..2` (pivot at the handle's base on the faucet; rotating X tips it forward), `act_glass_0..8` (Maß, Willibecher and a Weizenglas; 8 stands on the drip tray under the middle tap), each with a `foam_<n>` child holding only the foam.
- **Bier shelf:** `act_glass_10..18`, clean glasses upside down (origin on the rim), including three Weizen glasses.
- **Bratwurst:** `act_grill` (origin on the counter at the carpenter's `slot_grill`, under the bowl's centre), `act_grill_swing` (grate, pivot at the hook), `act_sausage_0..9` on the grate as children of the swing, `act_sausage_10..15` in the warming tray, `act_roll_0..15`, `act_served_0` (Bratwurst) and `act_served_1` (Currywurst), `act_smoke`. The coals are a child of the grill with material `coal_glow`.
- **Sausage pivots:** base, as the brief asks: origin under the middle of the sausage where it rests, long axis along the node's X. Every sausage's items.json entry has `turn_axis: {axis: "node X", offset_blender_z: 0.0125, offset_threejs_y: 0.0125}`: the axis it should turn about lies 12.5 mm above the origin. **Request to the engineer:** `turnSausages` in `site/src/actions/stalls.js` currently rotates the node itself about X, which with a base pivot would roll each sausage round its underside (it dips about 2.5 cm and pops back). Either rotate about the offset axis (translate by +offset in local Y, rotate, translate back), or wrap each sausage in a pivot group at load time. Until that lands the sausages turn slightly off-centre.
- **Bücher:** `act_book_0..` shelf 1 (43 books), `act_book_100..` shelf 2 (50), `act_book_200..212` counter (13). Standing books have their origin at the foot of the spine (a pull-out moves along −Y toward the visitor); lying books under the middle of their lowest face. Each has material `book_cover_<n>`, and title, author and cover material in its glTF node extras and in items.json.
- **Deco:** `rot_pyramid` on the Holzspielzeug counter.

The five reading-list titles stand together on shelf 1, left of the middle brace, as **`act_book_10..16`** (the same ids in the lite set): `act_book_10` The Order of Time (Carlo Rovelli); `act_book_11` Gödel, Escher, Bach (Douglas R. Hofstadter); `act_book_12..14` The Feynman Lectures on Physics, Vol. I–III (Feynman, Leighton, Sands); `act_book_15` Being You (Anil Seth); `act_book_16` The Book of Why (Judea Pearl and Dana Mackenzie). `prop_books_shelf_1_hero.jpg` shows the spines.

## Previews

All in `review/round-2/vendor/`, rendered on this machine in this round (Cycles, CPU, 1280×720, 48 samples).

**Staging.** Every counter, shelf and deco shot stands the set on a **generic plain wooden counter or shelf board** built by `vstage.env_counter()` at night with two warm point lights where the stall's light_ empties are, not in the carpenter's stall glb. The exception is the Bratwurst counter, where the grill has to prove it sits in the stall: `prop_wurst_counter_in_stall.jpg` and `prop_wurst_counter_in_stall_grill.jpg` load the carpenter's shipped `site/public/models/stall_bratwurst.glb` and put the set at its `slot_counter` (`vstage.stall_scene`), lit by the stall's own light_ empties plus an ember light in the bowl.

- One close-up per section set: `prop_gluehwein_counter_hero.jpg` (kettle, ladle, mugs), `prop_gluehwein_shelf_hero.jpg`, `prop_gluehwein_wine_hero.jpg` (labels), `prop_bier_counter_hero.jpg` (tap handles and foam), `prop_bier_back_hero.jpg` (barrels), `prop_bier_shelf_hero.jpg` (clean glasses), `prop_wurst_counter_hero.jpg` (grill, warming tray, raw sausages), `prop_books_shelf_1_hero.jpg` (the five titles), `prop_books_shelf_2_hero.jpg`, `prop_books_counter_hero.jpg`
- No wide shots this round: the machine was shared (load average near 19 on 4 cores, about 8 minutes per 1280×720 frame), so I rendered what the brief asks for: the close-ups, the two in-stall shots and the deco frames. `build_props.py --shots wide` renders the wide shots when there is time.
- In the real stall: `prop_wurst_counter_in_stall.jpg`, `prop_wurst_counter_in_stall_grill.jpg`
- Deco: `deco_lebkuchen.jpg`, `deco_mandeln.jpg`, `deco_kerzen.jpg`, `deco_spielzeug.jpg`, `deco_schmuck.jpg`, `deco_kaese.jpg`, `deco_crepes.jpg`, `deco_maroni.jpg`, `deco_puffer.jpg`, and all nine in `deco_goods_contact_sheet.jpg` (built only from the vendor's own frames in `blender/out/vendor/renders/prop_deco_*.png`). These frames show the goods on the plain counter, not in the carpenter's deco stalls.

## Contract questions for the market owner

- **Reading lamp without a light_ empty.** The brief asks for a reading lamp with a light_ empty on the Bücher counter. docs/BUILD.md caps a section stall at 2 light_ empties, and `stall_buecher.glb` already carries both, so the lamp in `prop_books_counter` is modelled (a banker's lamp: brass base and stem, green cased-glass shade, warm emissive bulb) but has **no light_ node**, and check_props fails any prop set that adds one. Question: should the lamp take one of the stall's two lights (the carpenter would drop one of his and I would add `light_lamp` at the bulb), or stay unlit as now?
- **2048 px textures.** The contract's standard step is 1024. The goods atlas is 2048 × 2048 because wine labels, tin lids and the price tags need it to be legible in close-up; the books colour atlas is 2048 × 3584 so every spine title reads (its normal and roughness maps are cut to 1024 × 1792, which read the same). Lite glbs use 512-wide versions of all of them. Shared textures total about 1.3 MB (full) and are loaded once for all sets. The books atlas height (3584) is not a power of two; three.js on WebGL2 mips it fine, but a KTX2/Basis step would need it padded to 4096. Please confirm 2048 is acceptable, or I drop the goods atlas to 1024 and accept softer labels.
- **Engine change for the sausages** (see *Sausage pivots*): rotate about `turn_axis`, not the node origin.

## Open issues

- **Headroom depends on the carpenter's stalls.** The tables above are measured against the stall glbs on disk today. Bier is the tightest section stall; if it grows, the first cuts are the shelf glasses and the bottle crate on the back shelf.
- **Grill seat follows the carpenter.** `set_wurst` reads `slot_grill` from `stall_bratwurst.glb` at build time (falling back to a probe of the counter and hood). If the carpenter moves `slot_grill`, rebuild `prop_wurst_counter`; the whole serving line then shifts to start right of the grill.
- **Lite glass.** Full glbs use transmission glass; lite keeps the same material names with alpha blending. The site's lite path must not expect KHR_materials_transmission.
- **Lite ratios.** A few small deco sets and the Bier back shelf are just above the 38 % lite target (small figures and bags have few segments to cut); these are WARNs, not FAILs.
- **Seat-check limits.** `seat_check.mjs` flags prop triangles crossing stall triangles and objects buried under a stall top; it does not flag a prop floating above a surface.
