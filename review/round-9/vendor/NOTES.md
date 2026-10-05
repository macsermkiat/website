# Vendor, round 9 (ADR 0004 revision: the ornament shop)

> Mac: "Ornament shop should have more sparkle decoration and goods. No need to be interactive in everything, but the one that interactive must be wow. not slop."

This round rebuilds the ornament shop's goods (`prop_schmuck_*`) from scratch around three interactions and a much richer, shinier dressing, and fixes the round-8 judges' book note. The other section sets and the deco scenery are unchanged since round 8. Their round-8 previews stay valid and are in `review/round-8/vendor/`. I did not copy them into this folder.

The carpenter published the round 9 slots during this run (`slot_harmonica_rail` with its twelve brass rings, `slot_mirrorball`, `slot_pyramid`, `slot_tinsel_1..3`, `mirror_0`). The goods stand at those slots. `set_schmuck.py` still has stand-ins (`STANDIN`) for any of the three hero slots a hut might lack, and props.json then carries `standin_position`. With the current hut it carries none.

## Pass 2: the judges' fixes

1. **Shelf tiers now read.** I did both: denser clusters and a staging fix.
   - Tier 1: the open boxes hold 6 baubles (were 4), and each footed bowl holds a ring of 5 with one on top, including a gloss teal (were 4).
   - Tier 2: five baubles on brass rings, graded l, m, xl, m, l (were 3). Two baubles now lie between the glass pine cones on the velvet runner, and the menu board moved down here under tier 3.
   - Warm fairy lights (`bulb_warm`, faceted bulbs every 9.5 cm on a fine dark wire) hang in shallow loops under the front lips of tiers 2 and 3. They glow among the goods of the tier below and are doubled in the mirror.
   - **The white sheet in the mirror was my preview's fault, not the carpenter's mirror.** In pass 1, `render_stalls.py` lit the shop with a 2.2 m lane fill panel standing right in front of the back-wall mirror, and the mirror showed it as a white sheet behind the shelves. The ornament shop's preview now uses the carpenter's own preview lighting from `blender/stalls/schmuck.py`: 150 W points with 6 cm sources at the `light_` markers, a soft fill inside the canopy that glossy rays cannot see, and the case and tree lights. The lane panels still light the goods, but Cycles light linking keeps them off `mirror_0`. The mirror now reads dark, foxed and full of reflected bulbs, and the shelf goods are no longer silhouettes. I did not ask the carpenter to darken the mirror: the engine has no such panel, so the change is not needed there. No other agent was reachable in this session anyway (ListAgents: none).
2. **Lametta rebuilt as twisted foil** (`set_schmuck.tinsel`).
   - Each swag is two crinkled foil strips twisted round each other: the width turns once every 4.5 cm (6 cm on the beam), the two strips sit a quarter turn apart, and every 1.5 cm station kinks the strip by up to ±40° and nudges it off the line.
   - Neighbouring facets therefore face different ways, and the foil glints in flecks.
   - Under it hangs a fringe of loose strands, one every 2.4 cm (4.5 cm on the beam). Each strand is 2.2 mm wide, kinked twice and twisted between its three facets, so no strand lights up along its whole length the way pass 1's straight strands did.
   - The tree's Lametta (`tinsel_2`) strands are kinked and twisted in the same way, 126 of them.
   - The `tinsel` material's roughness goes from 0.2 to 0.24, so more of the crinkled facets catch the lamps.
   - Lite: one strip at twice the step, and every second fringe strand plus the strands that set the bounds (bounds parity holds).
   - Cost: tinsel_1 960 → 1,604 triangles, tinsel_3 1,128 → 1,400, tree 2,792 → 3,060.
3. **Rauschgoldengel visible.** The four top-shelf angels (were three) are 1.36–1.42× scale, about 31 cm tall, and stand on 4.5 cm turned walnut plinths with brass caps.
   - Their foil (skirt, bodice, sleeves, hair, crown, wings) is a new flat material, `vendor_foil`: metallic, roughness 0.3, double-sided, with no AO. The pleats catch the hut lamp as broad gold highlights instead of mirroring the dark interior.
   - The inner rail's clusters (`prop_schmuck_rail_2`) moved so that, seen from the close-up camera, the gaps between them line up with the angels: clusters at 0.2 / 0.935 / 1.33 / 2.17 m along the rail and the Herrnhut stars at 0.5 / 1.72 m.
   - The angels' tops (2.19 m) stay under tier 3's clear height (2.30 m).
4. **instance.mjs naming bug fixed.** The Blender proto mesh is already named `inst_<key>`, so the batch was written as `inst_inst_<key>`. The batch name now strips any leading `inst_` before adding one. All 13 shop sets were rebuilt, and none of them has an `inst_inst_` node.
5. **Both shop previews re-rendered** at 1280×720 with 48 samples: `stall_schmuck_close.jpg` and `stall_schmuck.jpg`.

Budget after pass 2: the hut (31,564) plus the goods (27,539) come to **59,103 of 60k triangles (897 headroom)**, and 2.19 MB of 3 MB. check_props: PASSED with 21 warnings (the same lite-ratio and round-8 warnings as pass 1).

## 1. Three interactions, each a moment

All other former `act_orn_` nodes are renamed or merged into scenery, and their items.json entries are gone. The shop now has exactly 21 act_ nodes and 21 items.json entries:

| group | set @ slot | nodes | pivot | items.json action |
|---|---|---|---|---|
| Glass harmonica | `prop_schmuck_harmonica` @ `slot_harmonica_rail` | `act_orn_harmonica_0..11`, left to right, one per brass ring (`hooks_x`) | the ribbon's knot at the ring's bottom (`hook_drop`) | `harmonica`, with `index`, `radius_m` and `finish` |
| Reflection dive | `prop_schmuck_mirrorball` @ `slot_mirrorball` | `act_orn_mirrorball` + `cam_dive`, `cam_dive_target`, `cam_dive_approach` | top of its wire loop on the bracket hook; ball centre 0.119 m below | `dive`, with `cam` and `cam_target` |
| Schwibbogen | `prop_schmuck_counter` @ `slot_counter` | `act_orn_schwibbogen` + `act_orn_candle_0..6` (flames, origin at the wick) | base / wick | `candles`; each candle `light` with `order` (0 for the two outer candles, 3 for the middle one: they light from the outside in) |

- **Harmonica.** Twelve baubles hang with their ball centres on one level line, 0.25 m under the rail. Like the bowls of a glass harmonica, they are graded from 4.7 cm radius (left, lowest note) to 3.3 cm. The even-numbered ones are mercury glass, alternating silver and champagne. The odd ones are clear glass orbs, each with a small gold mercury core that catches the light through the clear shell. Each bauble is 12 segments round (10×7 sphere plus a lathed cap and ribbon), so the row reads smooth from the counter.
- **Mirror ball.** An 18 cm mercury-glass ball (24×16 smooth sphere, metallic, roughness 0.05) with a fluted gold crown and a short wire loop. It hangs straight from the forged bracket's hook, so no other ornament is within the carpenter's 0.4 m clear radius.
  - `cam_dive` stands 0.15 m from the ball's centre, level with it, toward the lane and a little toward the market (direction (0.34, -0.94, 0)).
  - At the site's 42° vertical field of view, a 16:9 frame's corners are 36.6° off axis. The ball spans asin(0.09 / 0.15) = 36.9° from there, so the reflection fills the frame.
  - `cam_dive_approach`, 0.7 m out on the same line, is the carpenter's suggested framing and gives the move a start point.
- **Schwibbogen.** Unchanged in shape. The candle `order` now encodes the ADR's outside-in lighting.

## 2. Sparkle in three tiers, dark wood between

New materials (vlib):
- `vendor_mercury`: metallic 1, roughness 0.05, tinted by COLOR_0 to silver, gold, copper, deep teal or champagne.
- `vendor_gloss`: high-gloss lacquered glass, roughness 0.06 with a clear coat.
- `tinsel`: metallic foil, roughness 0.24 (0.2 in pass 1), double-sided.
- `vendor_foil` (pass 2): the angels' crinkled gold foil, metallic, roughness 0.3, double-sided.

All four are flat factors with no texture, so they cost no bytes. They get no baked AO (`vstage.AO_SKIP`), because AO would dull the reflections.

| tier | piece | where |
|---|---|---|
| hero | glass harmonica | front rail |
| hero | 18 cm mirror ball | corner bracket |
| hero | **Erzgebirge candle pyramid** (`prop_schmuck_pyramid` @ `slot_pyramid`, 0.56 m) | counter, right of the Schwibbogen |
| medium | mercury-glass and high-gloss baubles, silver / gold / copper / deep teal, five sizes (2.2 to 5.5 cm radius) | inner rail clusters, velvet trays, footed glass bowls, ring stands, glass case, display tree |
| medium | twisted glass icicles (three-fluted, half a turn), glass pine cones (hanging and lying) | inner rail, rail 3, rail 4, shelf |
| medium | **Lametta** (pass 2: two crinkled foil strips twisted together with a fringe of twice-kinked strands): `tinsel_0` gold under the valance (`slot_tinsel_1`), `tinsel_1` silver along the tie beam (`slot_tinsel_3`, doubled in the mirror), `tinsel_2` kinked silver strands hanging from the display tree's skirts | canopy, beam, tree |
| medium | glass bead garlands: faceted octahedral beads, mercury gold / silver and clear | front: `prop_schmuck_garland` @ `slot_tinsel_2`, draped over the harmonica rail above the rings, with loose strands at the hangers; back: three curves across the back-wall mirror from its frame and glazing bars; tree: a gold spiral |
| medium | **Rauschgoldengel**: pleated gold-foil skirt and fanned foil wings (`vendor_foil`), wax face, zigzag crown | four (31 cm, on plinths) on the top shelf, one in the glass case, a large one topping the display tree |
| subtle | three snow globes (walnut base, glass ball, fir and house or church, floating flakes) | counter (2), shelf tier 1 |
| subtle | spun-glass birds with a fan of fine glass-fibre tails | inner rail (2), shelf tier 2 (2 on a birch log) |
| subtle | three lit Herrnhut stars, each with a `bulb_warm` core: red 21 cm and yellow 15 cm at different heights on the inner rail, white 12 cm over the tree | rails 2 and 4 |

The pyramid: the hexagonal base, six slanted turned posts with a top bearing ring and six candles (emissive `flame`) are static. `rot_pyramid` (origin on the axis) holds:
- the shaft;
- three tier discs carrying the nativity, shepherds with sheep, and angels;
- the eight-bladed propeller.

The node carries the glTF extras `{"axis": "y"}`. The engine's `spinAxis()` reads `userData.axis`, and without it would guess a horizontal axis from the propeller's width.

Fewer boxes: the shelves had 26 cartons in round 8 and now have 2 lids plus the counter's 2 cartons. The clusters are spaced with bare walnut between them, and the brace at x = 0 is kept clear.

Decoration without act_: the nutcracker (`nutcracker`), the smoker (`smoker`, with `fx_smoke_1` at his mouth for the ambient smoke), the pickle (hidden among the teal baubles on the inner rail), the display tree and its `hook_tree_<n>` empties.

**Instancing.** Every repeated bauble is one shared mesh per size, finish and colour (`PropSet.proto` / `inst`). The exporter writes one glTF mesh used by several `inst_*` nodes. `blender/props/instance.mjs` then folds each group under its set root into one `EXT_mesh_gpu_instancing` node named `inst_<key>` (pass 2 fixed a bug that named it `inst_inst_<key>`), which three.js loads as an InstancedMesh. Unlike gltf-transform's own `instance()`, the batch stays under the set root and no named empty is pruned. `seat_check.mjs` now expands instances, and triangle counts count every instance.

## 3. Books: the dim left column (round-8 judges)

- Every Bücherstand cover's glow is raised: `book_cover_<nn>` emissive strength goes from 0.3 in round 8 to 0.4.
- The outer columns get more, because the cabinet stiles shade them: the left column 0.54, the right 0.44 (`set_books.COVER_GLOW_*`). The value is per material, since every book has its own `book_cover_<nn>`.
- No texture is added and the cover designs are unchanged. The values are listed per book in props_report.json (`cover_glow`).
- All six `cam_cat` previews are rendered again: `prop_books_<key>_cam_cat.jpg`.

## Previews (this folder)

- `stall_schmuck_close.jpg`: the counter, the harmonica row, the pyramid, the inner rail, the Lametta, the shelf tiers with their fairy lights and the four angels, at night (1280×720, 48 samples, Cycles CPU, re-rendered in pass 2).
- `stall_schmuck.jpg`: the whole shop from the lane (1280×720, 48 samples, re-rendered in pass 2). The mirror ball hangs on the forged bracket at the far left edge of this frame. The close-up does not show it, because its dive is a camera move in the engine.
- `prop_books_{physics,lives,mind,people,decisions,craft}_cam_cat.jpg`: each cabinet from the engine's cam_cat camera.

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
| prop_books_physics | buecherstand | slot_cat_physics | 862 | 256 (30%) | 61 / 38 | 0.78 × 0.14 × 0.68 |
| prop_books_lives | buecherstand | slot_cat_lives | 514 | 184 (36%) | 43 / 28 | 0.47 × 0.13 × 0.68 |
| prop_books_mind | buecherstand | slot_cat_mind | 916 | 272 (30%) | 61 / 36 | 0.78 × 0.13 × 0.68 |
| prop_books_people | buecherstand | slot_cat_people | 946 | 312 (33%) | 71 / 47 | 0.78 × 0.13 × 0.94 |
| prop_books_decisions | buecherstand | slot_cat_decisions | 790 | 248 (31%) | 60 / 39 | 0.62 × 0.13 × 0.94 |
| prop_books_craft | buecherstand | slot_cat_craft | 694 | 224 (32%) | 47 / 27 | 0.78 × 0.13 × 0.41 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 3814 | 1455 (38%) | 72 / 41 | 2.54 × 2.76 × 1.76 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 3612 | 1448 (40%) | 70 / 37 | 3.07 × 2.72 × 1.76 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3879 | 1408 (36%) | 65 / 34 | 2.09 × 2.76 × 1.74 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 3872 | 1444 (37%) | 71 / 35 | 2.72 × 2.76 × 1.77 |
| prop_deco_kaese | deco-kaese | slot_counter | 3880 | 1436 (37%) | 54 / 32 | 2.23 × 2.76 × 1.75 |
| prop_deco_crepes | deco-crepes | slot_counter | 3752 | 1446 (39%) | 56 / 33 | 2.40 × 2.76 × 1.82 |
| prop_deco_maroni | deco-maroni | slot_counter | 3033 | 1455 (48%) | 66 / 34 | 2.24 × 2.74 × 1.78 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 3862 | 1433 (37%) | 63 / 34 | 2.91 × 2.76 × 1.77 |
| prop_schmuck_harmonica | deco-schmuck | slot_harmonica_rail | 2856 | 1764 (62%) | 73 / 68 | 1.95 × 0.09 × 0.30 |
| prop_schmuck_mirrorball | deco-schmuck | slot_mirrorball | 928 | 408 (44%) | 9 / 6 | 0.18 × 0.18 × 0.21 |
| prop_schmuck_pyramid | deco-schmuck | slot_pyramid | 1894 | 1236 (65%) | 54 / 38 | 0.32 × 0.33 × 0.56 |
| prop_schmuck_garland | deco-schmuck | slot_tinsel_2 | 1000 | 536 (54%) | 20 / 13 | 2.19 × 0.02 × 0.11 |
| prop_schmuck_tinsel_1 | deco-schmuck | slot_tinsel_1 | 1604 | 680 (42%) | 22 / 12 | 2.58 × 0.03 × 0.25 |
| prop_schmuck_tinsel_3 | deco-schmuck | slot_tinsel_3 | 1400 | 714 (51%) | 20 / 12 | 3.82 × 0.03 × 0.17 |
| prop_schmuck_rail_2 | deco-schmuck | slot_rail_2 | 2498 | 1562 (63%) | 75 / 60 | 2.20 × 0.21 × 0.38 |
| prop_schmuck_rail_3 | deco-schmuck | slot_rail_3 | 580 | 372 (64%) | 23 / 17 | 0.60 × 0.06 × 0.22 |
| prop_schmuck_rail_4 | deco-schmuck | slot_rail_4 | 402 | 322 (80%) | 28 / 21 | 0.51 × 0.12 × 0.18 |
| prop_schmuck_counter | deco-schmuck | slot_counter | 2848 | 2060 (72%) | 85 / 70 | 2.34 × 0.46 × 0.39 |
| prop_schmuck_shelf | deco-schmuck | slot_shelf_1 | 7069 | 4365 (62%) | 119 / 90 | 2.97 × 0.33 × 1.21 |
| prop_schmuck_case | deco-schmuck | slot_cabinet | 1400 | 826 (59%) | 37 / 30 | 0.54 × 0.22 × 0.51 |
| prop_schmuck_tree | deco-schmuck | slot_tree | 3060 | 1704 (56%) | 86 / 62 | 0.70 × 0.68 × 1.39 |

All prop glbs together: 2.96 MB full and 1.77 MB lite. Shared textures (`prop_tex_*`): 1.93 MB full and 0.28 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2000 headroom):

| stall | stall tris | + props | total / budget | headroom | MB / budget |
|---|---|---|---|---|---|
| gluehwein | 38780 | 19132 | 57912 / 60k OK | 2088 | 2.32 / 3 |
| bierstand | 41453 | 16178 | 57631 / 60k OK | 2369 | 2.27 / 3 |
| bratwurst | 38378 | 18324 | 56702 / 60k OK | 3298 | 2.27 / 3 |
| buecherstand | 51428 | 10078 | 61506 / 80k OK | 18494 | 3.18 / 4 |

Deco stalls, stall plus its one scenery goods set against 20k (the ornament shop, stall_schmuck.glb, with its 13 goods sets against 60k and 3 MB; check_props fails over). MB is the stall glb plus its goods glb against the 1 MB budget; the shared prop textures load once for the whole market and are listed apart (the ornament shop's MB includes them, against its 3 MB):

| deco stall | stall tris | goods | total / budget | room | act_ nodes (0: scenery) | MB stall + goods / budget | shared textures used (loaded once) |
|---|---|---|---|---|---|---|---|
| lebkuchen | 8813 | 3814 | 12627 / 20k OK | 7373 | 0 | 0.33 / 1 OK | 0.77 MB |
| mandeln | 9098 | 3612 | 12710 / 20k OK | 7290 | 0 | 0.31 / 1 OK | 0.77 MB |
| kerzen | 8372 | 3879 | 12251 / 20k OK | 7749 | 0 | 0.30 / 1 OK | 0.77 MB |
| spielzeug | 9633 | 3872 | 13505 / 20k OK | 6495 | 0 | 0.33 / 1 OK | 0.77 MB |
| schmuck | 31564 | 27539 | 59103 / 60k OK | 897 | 21 | 2.19 / 3 OK | 0.77 MB |
| kaese | 7023 | 3880 | 10903 / 20k OK | 9097 | 0 | 0.24 / 1 OK | 0.77 MB |
| crepes | 7507 | 3752 | 11259 / 20k OK | 8741 | 0 | 0.27 / 1 OK | 0.77 MB |
| maroni | 7336 | 3033 | 10369 / 20k OK | 9631 | 0 | 0.25 / 1 OK | 0.82 MB |
| puffer | 8921 | 3862 | 12783 / 20k OK | 7217 | 0 | 0.31 / 1 OK | 0.77 MB |

<!-- check_props:end -->

## Open issues

- **Shop triangle headroom (carpenter / lead).** After pass 2 the hut (31,564) plus the goods (27,539) come to 59,103 of 60k triangles: 897 headroom, and 2.19 MB of 3 MB. Pass 2 spent about 3.4k triangles on the judges' fixes. If the hut grows, the cheapest cuts on my side are:
  - the fairy-light loops, about 0.6k for both;
  - the beam Lametta's fringe (`tinsel_3`), about 0.4k;
  - the back-wall bead garland, about 0.5k.
- **Lametta in Cycles.** The twisted strips now read as foil with flecks of light. A few fringe strands still flash as single bright lines where a facet faces the lane fill. The engine's glint shader on `tinsel_<n>` should make them shimmer as the camera moves.
- **Mirror (carpenter / lighting designer, for information only).** The pass 1 complaint about silhouettes came from my preview's lane fill panel showing in `mirror_0`; it was not a fault in the mirror. The preview now keeps that panel out of the mirror, as the carpenter's own preview does. In the engine, the mirror's brightness depends on what the lighting designer's environment gives it. If it turns out bright there, a darker foxing would help the shelf goods, but nothing needs changing for the goods themselves.
- **Engine (engineer).**
  - The shop's items.json now has only the three groups. The old actions (ring, hang, find, jaw, smoke, light on the Herrnhut) have no nodes left.
  - New actions: `harmonica` (index 0..11 left to right) and `dive` (cam / cam_target).
  - The goods now use `EXT_mesh_gpu_instancing` nodes named `inst_<finish>_<colour>_<size>` (no longer `inst_inst_*`). three.js loads them as InstancedMesh, and the engine's merge and shadow passes already skip InstancedMesh.
- **Lite ratio.** The lite shop goods come to about 60 % of full. Smooth spheres and fine strands cannot lose much and still keep their bounds. These are warnings in check_props, not budget failures.
- **From round 8, not mine:** the Bier coaster "Transfusion Audit" title from `content/projects.md` reads clinical; this is for the writer or Mac. The optional grill close-up suggested by the Fable judge was not rendered, to save Mac's usage for the shop.
- **Codex judge.** `review/round-8/CODEX_JUDGE.md` does not exist on disk, so there were no Codex points to address.
- **check_props, round 9.** It passes with 21 warnings: the lite-ratio warnings above plus the round-8 ones. Two round 9 changes to the checker: instanced `inst_*` batches are skipped in the full and lite bounds-parity check, because a batch node's own box is its prototype's and not where its copies stand (`seat_check.mjs` expands the instances and finds no collisions); and the new `check_fill` test counts the 21 shop act nodes, the harmonica order, the dive camera, `rot_pyramid`, the tinsel swags and `fx_smoke_1`.
- **Credits.** No third-party assets were used this round; everything is procedural.
