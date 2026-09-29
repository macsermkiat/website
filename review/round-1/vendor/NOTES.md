# Vendor, round 1, pass 3 notes

All goods are modelled in code under `blender/props/` and textured from two procedural atlases (goods and books). No third-party models or images are used; the fonts are OFL (see CREDITS.md, Vendor section). Everything below was rebuilt on the cloud machine in this pass: atlases, all 19 sets (full and lite, with the AO bake), props.json, items.json and every preview.

Rebuild and check:

```
python3 blender/props/vendor_atlas.py                                   # atlases -> blender/out/vendor/
NM_DEVICE=CPU NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/props/build_props.py \
    [--only a,b] [--no-render] [--no-lite] [--no-ao] [--samples 48] [--res 1280x720] \
    [--render-only a,b] [--shots wide|hero|wide,hero] [--sheet-only]
python3 blender/props/check_props.py [--notes]     # contract checks, exit 1 on FAIL; --notes rewrites the tables below
```

bpy may segfault on exit after `build_props.py` has written everything; the outputs are complete.

## What changed in pass 3 (judges' fixes)

| # | Judges' fix | What I did | Checked by |
|---|---|---|---|
| 1 | Deco renders were overwritten by the carpenter's `deco.py` (same `blender/out/renders/deco_<key>.png`), so the contact sheet showed empty stalls | All my renders and AO maps now go to vendor-only paths: `blender/out/vendor/renders/prop_*.png` and `blender/out/vendor/ao/`. `deco_goods_contact_sheet.jpg` is built only from `blender/out/vendor/renders/prop_deco_*.png` (the frames this build rendered) and lists any missing frame; `build_props.py --sheet-only` rebuilds it alone. I looked at the rebuilt sheet: every tile shows its stall with the goods on it. | the sheet itself |
| 2 | Lite sets were missing named nodes (shelf 1 reading-list books, `act_book_149..151`, `act_roll_5..9`) | Layout and detail randomness are now two streams in `vlib.py`: `rng` places things and draws the same numbers in full and lite; `drng` only colours and garnishes. Lite no longer drops rolls or books. check_props compares every set's full and lite glb node by node (names, position within 1 mm, rotation, and the extras name, kind, title, author, cover_material) and FAILs on any difference; items.json entries that no glb has also FAIL. | check_props parity: all 19 sets pass |
| 3 | Bratwurst warming tray and `act_sausage_8..11` sat in the firebox and hearth plate | The warming tray with its four sausages stands on the counter at x 0.0 (right of the firebox rim at -0.13), followed by tongs, roll basket, mustard, the served tray, paper trays, squeeze bottles, napkins and the chalk sign up to x 1.62 (the counter ends at 1.89). New collision check `blender/props/seat_check.mjs`: every prop triangle is tested against every stall triangle at the slot (Möller triangle-triangle test, 3 mm tolerance), plus a height-field test that catches objects fully buried under a stall top. It found and I fixed: the Feynman volumes in shelf 1's middle brace, the Bier chalkboard in the brace and back wall, the wine box 4 mm into the back boards, Mandeln and Maroni hanging past the board. | check_props seat check: 0 collisions in 19 sets |
| 4 | Glühwein lid swung behind the counter | The kettle moved forward (y 0.0) and the lid ships just ajar (14°, `rotation.x = -0.25`); at the engine's full pour swing (+0.35 rad) its back edge stays inside the counter. | seat check, props.json bbox |
| 5 | Lite ratio at 41–52 % for several sets | Lite uses `seg(n) = max(min(lo, 6), round(n × 0.34))` for every lathe and ring, and lighter profiles for mugs, bottles, glasses, jars, oranges, baubles, barrels and books. See the ratio column below. | check_props WARN above 38 % |
| 6 | Polish | **Beer foam:** a lumpy domed crown per glass (own seed), a creamy band and a small spill drip, no black rim. **Barrels:** bellied staves with two facets each, on a visible rack of two rails with chocks, charcoal satin forged hoops, the tap low on the head so the brand is clear above it. **Ladle:** new `act_ladle` with a steel bowl holding Glühwein, resting on the plate with its handle against the kettle. **Density:** Schmuck has 14 hanging pieces, two crates of baubles, a tabletop tree and loose baubles; Mandeln has a burlap sack, a tray of cashews, five striped bags and paper cones lying in front; Spielzeug has Spanbäume on a riser, three nutcrackers, a train, spinning tops, blocks, a rocking horse and a crate of plywood stars and hearts. | previews below |
| 7 | Headroom guard and 48-sample section shots | check_props FAILs under 2k headroom for every section stall; all section wide and hero shots and the deco frames are 1280×720 at 48 samples. | tables below |
| 8 | Spielzeug and Schmuck deco totals had little room | Both goods sets are lighter (simpler figure heads, cheaper trees, fewer bauble rings), and check_props now FAILs when any deco stall plus its goods is over 20k. | deco table below |
| 9 | Stale NOTES budget tables | `check_props.py --notes` writes the tables below from the glbs on disk (the carpenter's current stalls and my sets). | generated block |
| 10 | Sausage pivots at the centre | Kept on purpose and documented under *Animation nodes and pivots*; items.json carries a `pivot` field for every node. | items.json |

## Sets, slots and budgets

The tables between the markers are written by `check_props.py --notes` from the glbs on disk (the carpenter's current stalls and my sets), so they cannot go stale: rerun it after any stall or prop rebuild.

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2546 (34%) | 183 / 98 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 5190 | 1732 (33%) | 133 / 67 | 2.27 × 0.22 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 4360 | 1448 (33%) | 98 / 60 | 2.32 × 0.23 × 0.46 |
| prop_bier_counter | bierstand | slot_counter | 6716 | 2384 (35%) | 134 / 81 | 1.94 × 0.40 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 3888 | 1004 (26%) | 87 / 37 | 2.28 × 0.24 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3052 | 1070 (35%) | 55 / 28 | 1.69 × 0.23 × 0.22 |
| prop_wurst_counter | bratwurst | slot_counter | 11854 | 3436 (29%) | 276 / 128 | 2.88 × 0.47 × 0.67 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1456 | 432 (30%) | 139 / 107 | 1.86 × 0.22 × 0.30 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1402 | 456 (33%) | 144 / 114 | 1.86 × 0.23 × 0.30 |
| prop_books_counter | buecherstand | slot_counter | 2078 | 756 (36%) | 90 / 59 | 2.05 × 0.43 × 0.40 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 3848 | 1380 (36%) | 94 / 39 | 2.20 × 0.30 × 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 2952 | 1122 (38%) | 76 / 37 | 1.98 × 0.48 × 0.44 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3090 | 1164 (38%) | 77 / 35 | 2.10 × 0.44 × 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 3014 | 1172 (39%) | 101 / 48 | 2.01 × 0.41 × 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 3142 | 1124 (36%) | 84 / 34 | 2.16 × 0.36 × 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 3040 | 1108 (36%) | 60 / 31 | 1.95 × 0.43 × 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 1990 | 742 (37%) | 52 / 31 | 1.97 × 0.46 × 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4036 | 1169 (29%) | 93 / 39 | 1.87 × 0.46 × 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 2674 | 729 (27%) | 63 / 28 | 1.85 × 0.48 × 0.26 |

All prop glbs together: 2.04 MB full and 1.10 MB lite. Shared textures (`prop_tex_*`): 0.86 MB full and 0.12 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use; check_props fails under 2k headroom):

| stall | stall tris | + props | total / 60k | headroom | MB / 3 |
|---|---|---|---|---|---|
| gluehwein | 37687 | 17000 | 54687 OK | 5313 | 1.80 |
| bierstand | 43429 | 13656 | 57085 OK | 2915 | 1.80 |
| bratwurst | 37715 | 11854 | 49569 OK | 10431 | 1.62 |
| buecherstand | 33567 | 4936 | 38503 OK | 21497 | 2.14 |

Deco stalls, stall plus goods against 20k (check_props fails over):

| deco stall | stall tris | goods | total / 20k | room |
|---|---|---|---|---|
| lebkuchen | 14277 | 3848 | 18125 OK | 1875 |
| mandeln | 16817 | 2952 | 19769 OK | 231 |
| kerzen | 14959 | 3090 | 18049 OK | 1951 |
| spielzeug | 16786 | 3014 | 19800 OK | 200 |
| schmuck | 16695 | 3142 | 19837 OK | 163 |
| kaese | 13516 | 3040 | 16556 OK | 3444 |
| crepes | 14089 | 1990 | 16079 OK | 3921 |
| maroni | 14482 | 4036 | 18518 OK | 1482 |
| puffer | 15736 | 2674 | 18410 OK | 1590 |

<!-- check_props:end -->

## Animation nodes and pivots

Every act_ / rot_ node is an empty with the pivot as its origin; its geometry is a `<name>_mesh` child, because the optimiser rewrites mesh-node transforms. items.json gives each node's `pivot`: `base` (the point it rests on) for every mug, glass, bottle, wine glass, book, roll, ladle and served tray, and the exceptions below.

- **Glühwein counter:** `act_pot` (kettle, origin at the burner's foot), `act_pot_lid` (hinged at the back rim; it ships just ajar, 14°, so it stays inside the counter; the engine's pour swings it 0.35 rad further open and back), `act_ladle` (bowl on the ladle-rest plate, handle leaning on the kettle), `act_steam`, `act_mug_0..9`: eight classic mugs and two boots (0 and 5); mugs 0, 1, 3 and 4 are full with a steam empty `act_steam_<i>`; mugs 6–9 stand upside down on the drying board (origin on the rim, which is their base).
- **Glühwein shelf:** `act_bottle_12..17`, `act_mug_10..12`, spice jars, orange slices, cinnamon, star anise.
- **Wine shelf (slot_shelf_2):** `act_bottle_0..9`: Riesling (Mosel, Rheingau, Pfalz, Eiswein), Spätburgunder (Baden, Ahr), Dornfelder (Rheinhessen, Pfalz), Silvaner (Franken Bocksbeutel, Rheinhessen), each with its own label, capsule and glass colour; `act_wineglass_0..2`.
- **Bier counter:** `act_tap_0..2` pivot at the handle's base on top of the faucet (local z 0 to 0.168), so the handle tilts forward. `act_glass_0..5` (three Maß, three Willibecher), each with a `foam_<n>` child holding only the foam head.
- **Bier shelf:** `act_glass_10..15`, clean glasses upside down (origin on the rim).
- **Bratwurst:** `act_grill` (fire bowl on the firebox's hearth plate, `coals` child with `coal_glow`), `act_grill_swing` (grate on three chains, pivot at the hook), `act_sausage_0..7` on the grate as children of the swing, `act_sausage_8..11` in the warming tray on the counter, `act_roll_0..9` (origin at the base), `act_served_0`, `act_smoke`.
- **Sausage pivots:** the brief asked for pivots at the base. The sausages keep theirs at the centre, long axis along X, on purpose: the engine's turn (`site/src/actions/stalls.js`, `turnSausages`) rotates each sausage about its long axis, and a base pivot would make it roll round its underside and jump off the grate. items.json says so in each sausage's `pivot` field, and check_props only requires a base pivot for mugs, glasses, bottles, wine glasses, books, rolls, taps and the served tray.
- **Bücher:** `act_book_0..` shelf 1, `act_book_100..` shelf 2, `act_book_200..212` counter. Standing books have their origin at the foot of the spine, so a pull-out moves along +Y; lying books have it under the middle of their lowest face. Each has material `book_cover_<n>`, and title, author and cover material in its glTF node extras.
- **Deco:** `rot_pyramid` on the Holzspielzeug counter.

The five reading-list titles stand together on shelf 1 (`act_book_21..27`), left of the middle brace: The Order of Time; Gödel, Escher, Bach; The Feynman Lectures on Physics (three volumes); Being You; The Book of Why. The same seven books, with the same titles, authors and covers, are `act_book_21..27` in the lite set too. `prop_books_shelf_1_hero.jpg` shows all five spines.

## Previews

All in `review/round-1/vendor/`, rendered on this machine in this pass (Cycles, CPU, 1280×720, 48 samples). Each set is shown in its slot on the carpenter's current stall glb, so the frames show exactly what the site will load.

- Section wide shots: `prop_gluehwein_counter.jpg`, `prop_gluehwein_shelf.jpg`, `prop_gluehwein_wine.jpg`, `prop_bier_counter.jpg`, `prop_bier_back.jpg`, `prop_bier_shelf.jpg`, `prop_wurst_counter.jpg`, `prop_books_shelf_1.jpg`, `prop_books_shelf_2.jpg`, `prop_books_counter.jpg`
- Close-ups (hero): `prop_gluehwein_counter_hero.jpg` (kettle, lid ajar, ladle, mugs), `prop_gluehwein_shelf_hero.jpg`, `prop_gluehwein_wine_hero.jpg`, `prop_bier_counter_hero.jpg` (foam heads, taps), `prop_bier_back_hero.jpg` (barrels on the rack), `prop_wurst_counter_hero.jpg` (grill, warming tray, rolls), `prop_books_shelf_1_hero.jpg` (the five reading-list titles), `prop_books_counter_hero.jpg`
- Deco stalls with their goods: `deco_lebkuchen.jpg`, `deco_mandeln.jpg`, `deco_kerzen.jpg`, `deco_spielzeug.jpg`, `deco_schmuck.jpg`, `deco_kaese.jpg`, `deco_crepes.jpg`, `deco_maroni.jpg`, `deco_puffer.jpg`, and all nine together in `deco_goods_contact_sheet.jpg` (built only from `blender/out/vendor/renders/prop_deco_*.png`)

## Open issues and contract questions

- **Headroom depends on the carpenter's stalls.** The budget tables above are measured against the stall glbs on disk today. Bier is the tightest section (about 2.9k headroom); if its stall grows by more than that, check_props fails and I would thin the shelf glasses or the barrel staves first.
- **Seat-check limits.** `seat_check.mjs` finds prop triangles that cross stall triangles, plus objects buried under a stall top. It does not flag a prop that floats above a surface or one that is fully inside a closed wall volume without crossing any face; the support-range check covers the one case that matters on these boards (goods past the back edge).
- **Glühwein lid.** Last pass's judge note gave the lid's back edge as -0.313; I measured 0.252 in the slot frame before this pass, so the two may use opposite y signs. The whole Glühwein counter set now spans y -0.246..0.222 in the slot frame, inside the counter board's -0.286..0.294. The lid is hinged at the kettle's back rim, so opening it the engine's extra 0.35 rad lifts the lid up and forward and moves only its knob and dome about 2 cm back. If the swing amplitude grows well past 90°, recheck.
- **Lite glass.** Full glbs use transmission glass; lite keeps the same material names with alpha blending. The site's lite path must not expect KHR_materials_transmission.
- **Firebox coupling.** The Bratwurst grill is placed for the firebox at slot-frame x -1.68..-0.25 (hearth plate at 2.6 cm, top at y 1.09). If the carpenter moves the firebox, `act_grill`, the swing and the warming tray have to move with it; the seat check will flag it.
- **Deco room is thin.** Spielzeug (19,800), Schmuck (19,837) and Mandeln (19,769) are under 20k with 160–230 triangles to spare. If the carpenter's deco stalls grow, check_props fails, and the first cuts would be the hanging baubles' rings and the cheap Spanbäume.
- **Mandeln and Spielzeug lite ratios** are 38 % and 39 % (small figures and bags have few segments to cut); they are WARNs, not a FAIL.
- **CREDITS.md** is unchanged: no third-party assets were added in this pass.
