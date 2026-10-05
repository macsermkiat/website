# Vendor, round 10: the Bratwurst plate and the Bierstand's bottle shelves

> Mac: "There are too much interaction in sausages, no need to able to flip that lots sausages, just few different kind is enough. But if it's able to mix on plate and put on sauce must be nice."
>
> Mac (2026-10-05): "Beer stand should have more beer bottle decorated on shelf (non-interactive)."

## Pass 2 (the judges' fixes)

1. **The Bratwurst engine wiring is still the engineer's job.** I may not edit site/src, so the stall is not ready to go live until the engineer makes the changes listed under Open issues. The glb and items.json side is finished and has not changed since pass 1.
2. **The Bierstand shelves are fuller: 62 decorative bottles, up from 44.** Back rows now stand on low wooden risers behind the front rows at both ends of both shelves, so their shoulders, caps and label tops show over the front row:
   - upper shelf, left: six Sternwirt Weißbier longnecks behind the swing-tops;
   - upper shelf, right: four Laternen-Bräu Märzen behind the Klosterbräu row;
   - lower shelf, left: the green Tannenhof Pils go from four to six and stand on a riser;
   - lower shelf, right: a new row of six Klosterbräu Dunkel in dark green behind the Steinkrüge and longnecks.
   The middle of each shelf stays bare dark wood. None of it is clickable, and the act_ nodes and items.json are the same as in pass 1.
3. **The Krakauer has its own smoked casing.** The new print-atlas region `pr_smoked_casing` (192 × 72 px) shows mahogany red-brown skin, darker on the side that faced the smoke, fine shrink wrinkles along its length, pale specks of the coarse grind and a string tie at each end. It went into the free rows at the bottom of the print atlas (rows 1888–1967). I diffed the atlas: no earlier region moved and no other pixel changed. The Krakauer now uses the `print` material, not the grilled `sausage` skin with a red tint.

**Paying for the bottles.** 18 more bottles fit inside the 2,000-triangle headroom rule, with 2,005 to spare:
- back-row bottles use 4 facets and have no neck label (about 46 triangles each);
- crown caps have 3 facets, not 5;
- crate bottles behind the first row are back-row style;
- the casks lose their rear head and chime, which face the wall;
- the steins lose their hidden bottom and top discs, and their cobalt band is a lathe band, not a torus;
- the two counter pretzels have 6 sides and 11 salt crystals (were 7 and 16);
- the paper rims of the counter coasters have 8 sides (were 12).

No clickable node changed: the glasses, taps, Bierdeckel and vom Fass board are as they were.

## Pass 1

This round changes four sets: `prop_wurst_counter` (rebuilt around the plate), `prop_bier_back` and `prop_bier_shelf` (decorative bottles), and `prop_bier_counter` (trimmed by 240 triangles to make room for the bottles; nothing clickable changed). Every other set is unchanged since round 9. Its previews stay valid in `review/round-9/vendor/` and `review/round-8/vendor/`, and I did not copy them here.

## 1. Bratwurst: sausages and rolls are scenery now

- The 24 clickable sausages (`act_sausage_0..23`), the 16 rolls (`act_roll_0..15`) and the two served portions (`act_served_0/1`) are gone, along with their items.json entries. check_props now fails if any `act_sausage_` / `act_roll_<n>` / `act_served_` node or entry comes back.
- The grill still looks full: ten Bratwürste lie on the grate, five rows of two as before. They are now one merged mesh, `sausages_grill`, a child of `act_grill_swing`, so they still ride the swing.
- The warming tray (6 sausages), the raw tray (8) and the roll basket (14 rolls) are merged into the static mesh. Scenery sausages use 8 × 8 facets instead of 12 × 10 (from 260 to 144 triangles each).
- Unchanged: `act_grill`, `act_grill_swing`, the coal bed (`coals`, material `coal_glow`), `act_smoke` and the Marktblatt (`act_writing_paper` with `write_writing_paper` and `cam_read_writing_paper`).

## 2. The plate set (all origins at the item's base, slot_counter frame, metres)

A two-step wooden serving board (an Auslage) stands at the counter front, centred at x 0.66. The back step is raised 4 cm on two battens, so the back row shows over the front row from the stall's `cam_view`.

| node | what | origin (x, y, z) | items.json action |
|---|---|---|---|
| `act_wurst_thueringer` | Thüringer Rostbratwurst: 22 cm long and thin, dark grill-marked skin | 0.52, -0.093, 0.062 (back step) | `plate` |
| `act_wurst_krakauer` | Krakauer: 17 cm, 4 cm thick, curved, smoked red-brown | 0.82, -0.093, 0.062 (back step) | `plate` |
| `act_wurst_nuernberger` | three finger-sized Nürnberger (8.5 cm) side by side, one node (`count: 3`) | 0.44, -0.205, 0.022 (front step) | `plate` |
| `act_wurst_curry` | sliced Currywurst on a small paper tray: curry ketchup pooled between the slices and drizzled over, curry powder, wooden fork | 0.66, -0.205, 0.022 | `plate` |
| `act_roll` | a crusty Brötchen (14 × 5 facets) | 0.87, -0.205, 0.022 | `plate` |
| `act_sauce_senf` / `_ketchup` / `_curry` | soft squeeze bottles, yellow / red / dark orange, printed labels (SENF, KETCHUP, CURRY), screw caps and pointed nozzles; `fx_sauce_<key>` is a child empty at the nozzle tip (0.2165 m up) | x 1.04 / 1.118 / 1.196 at the front | `sauce` (+ `sauce`, `colour`, `fx`) |
| `act_shaker_curry` | a tin curry shaker with a printed label and a pierced domed lid; `fx_shaker_curry` sits at the lid top. This empty was not in the brief: the engine can use it for the powder, or ignore it. | 1.269, -0.2, 0 | `dust` (+ `colour`, `fx`) |
| `act_plate` | an empty white paper plate (23 cm, rolled rim, top and underside); `plate_spot_0..3` are child empties on its floor (z 0.0016) in a 2 × 2 grid at (±0.042, ±0.036), for items lying along X | 0.14, -0.148, 0 (left of the board, right of the Marktblatt) | `clear` (+ `spots`, `max_items: 4`, `clear_note: "Guten Appetit"`) |

Every entry has `name`, `label` (short German) and `action`. Each wurst entry also carries `wurst` (thueringer / nuernberger / krakauer / curry / roll) and a one-line `detail`. The mustard and ketchup pots, fork cup, paper-tray stack, napkins, tip jar, bread board and chalk sign stay as scenery, moved a little to clear the board. The set is 3.43 × 0.50 × 0.64 m, within the 0.5 m counter depth.

## 3. Bierstand: decorative beer bottles (no act_ nodes, no items.json entries)

- (Pass 2 added back rows on risers; see the Pass 2 section above. The lists below are pass 1's front rows.)
- Every bottle is merged into its set's static mesh. The act_ nodes on the two shelves are exactly round 9's: none on `prop_bier_back`, and `act_glass_10..18` on `prop_bier_shelf`. check_props checks this.
- The clickable glasses, taps, coasters and the carpenter's vom Fass board are untouched.
- Most groups stand at the shelf ends (x ±1.2 to ±1.9), where the 3.9 m boards were bare. Dark wood is left between the groups and in the middle.
- **Shelf 1** (`prop_bier_back`, 25 bottles):
  - left end: seven brown Euro bottles of Nachtmarkt-Bräu Helles in front of four green Tannenhof Pils;
  - a wooden crate of eight brown Eichwald Kellerbier with a burnt-in brand, where round 9's six swing-tops stood;
  - right end: three salt-glazed stoneware Steinkrug bottles (cream body with a cobalt Eichwald stamp, brown-dipped shoulders, corks) and three amber Sternwirt Weißbier longnecks.
- **Shelf 2** (`prop_bier_shelf`, 19 bottles):
  - left end: seven swing-top Bügelflaschen, Laternen-Bräu Märzen in brown and Klosterbräu Dunkel in dark green, with porcelain stoppers, red rubber rings and wire bails;
  - right end: a crate of eight green Tannenhof Pils with its brand, and four brown Klosterbräu Dunkel.
- **Labels.** Six invented breweries, each with a body label and a neck label: Nachtmarkt-Bräu (the market's own, with the brewer's star from the Bierdeckel), Klosterbräu St. Nikolaus, Tannenhof, Sternwirt, Laternen-Bräu and Eichwald. Crown caps are metallic in each brewery's colour, so they catch the lamps.
- **Making them cheap.** The bottles stand against the back wall, so each body is lathed over its front 240° only. From the lane it reads as a smooth 7.5-sided bottle for about two thirds of the triangles. Caps and stoppers are closed discs, because the lower shelf is seen from above.
- **Material.** The glass is opaque glossy `vendor_glaze` (atlas plus clear coat). A full, dark bottle shows no depth anyway, and 44 opaque bottles add no transparent draw sorting in the engine.
- **Buying the triangles back** (the Bierstand had 2,369 headroom):
  - casks with 14 single-faceted staves, 4 rings and flat hoops (about half of round 9's 744 each);
  - steins with 8 facets and a 4-sided handle;
  - pretzels with 7 sides and 16 salt crystals (were 8 and 24);
  - the coaster stack shows only its top coaster over the edge band.

### Shared print atlas: new label regions

The labels (beer bodies and necks, the stoneware stamp, two crate brands, three sauce labels, the curry tin) are new regions in the print atlas (`blender/props/atlas_labels.py`). They are pasted into its free rows 1752–1960, so no existing region moved:

- I diffed the atlas PNGs before and after: only rows 1752–1959 changed.
- Every other set that prints (coasters, Marktblatt, wine back labels, book_open) keeps its UVs.
- `prop_tex_print_*.webp` were rewritten with the new rows.
- `atlas_print.build()` now calls the patch at its end, so a full rebuild keeps the regions.

## Previews (this folder, Cycles CPU)

Pass 2 re-rendered all of these, plus `stall_bratwurst_board.jpg`: a closer view of the serving board, where the Krakauer's smoked casing reads next to the grilled Thüringer (1280×720, 48 samples).

These are stall renders with every prop set of the stall at its slot (`blender/props/render_stalls.py`, which now also handles the section stalls and the stall's own `cam_view` at the engine's 42° field of view):

- `stall_bratwurst_close.jpg`: the Bratwurst counter close-up, showing the board with the four kinds and the roll, the three bottles and the shaker, and the plate, with the Marktblatt and the roll basket at the left (1280×720, 48 samples).
- `stall_bratwurst_cam_view.jpg`: the whole Bratwurst stall from its `cam_view`, the framing a visitor gets on entering (1280×720, 48 samples). From 3.6 m away:
  - the three bottles, the plate, the roll and the two back-step sausages read by shape and colour;
  - the Nürnberger trio and the Currywurst are small, about 20–30 px across at 720p, but distinct;
  - the close-up shows them all clearly.
- `stall_bierstand_shelf.jpg`: both Bierstand back shelves end to end from over the counter (1280×720, 48 samples).
- `stall_bierstand_shelf_r.jpg`: the right-hand bottle groups closer, so the labels, the stoneware and the crates read (1280×720, 48 samples).

## Budgets

check_props passes, with 22 warnings: the lite-ratio warnings, the new bottle shelves among them, plus round 9's.

| stall | round 9 | round 10 | headroom | MB of 3 |
|---|---|---|---|---|
| Bierstand | 41,453 + 16,178 = 57,631 | 41,453 + 16,542 = 57,995 (pass 1: 16,520) | 2,005 | 2.38 |
| Bratwurst | 38,378 + 18,324 = 56,702 | 38,378 + 17,361 = 55,739 | 4,261 | 2.29 |

- `prop_wurst_counter` comes to 17,361 triangles (6,208 lite) and 377 / 191 kB.
- The Bier shelves come to 3,748 + 4,654 triangles (2,691 + 2,975 lite), and the counter to 8,140 (3,266 lite).
- The shared print textures grew by about 0.07 MB with the label rows.

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2610 (35%) | 183 / 99 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 6254 | 2051 (33%) | 164 / 82 | 2.29 × 0.24 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 5428 | 2194 (40%) | 144 / 98 | 2.33 × 0.23 × 0.42 |
| prop_bier_counter | bierstand | slot_counter | 8140 | 3266 (40%) | 179 / 114 | 2.37 × 0.45 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 3748 | 2691 (72%) | 104 / 71 | 3.81 × 0.25 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 4654 | 2975 (64%) | 92 / 64 | 3.72 × 0.23 × 0.30 |
| prop_wurst_counter | bratwurst | slot_counter | 17361 | 6208 (36%) | 377 / 191 | 3.42 × 0.50 × 0.64 |
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

All prop glbs together: 2.94 MB full and 1.80 MB lite. Shared textures (`prop_tex_*`): 2.00 MB full and 0.29 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2000 headroom):

| stall | stall tris | + props | total / budget | headroom | MB / budget |
|---|---|---|---|---|---|
| gluehwein | 38780 | 19132 | 57912 / 60k OK | 2088 | 2.39 / 3 |
| bierstand | 41453 | 16542 | 57995 / 60k OK | 2005 | 2.38 / 3 |
| bratwurst | 38378 | 17361 | 55739 / 60k OK | 4261 | 2.29 / 3 |
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

- **Engine (engineer): the Bratwurst actions need the new wiring.**
  - `site/src/actions/items/wurst.js` still looks for `act_sausage_*` and `act_roll_*`. With these glbs it finds none, so turning and the bun do nothing.
  - `site/src/engine/standinGoods.js` (line 68) adds stand-in sausages when the stall has no `act_sausage` node. That will now trigger on the real glb and must check for `act_wurst_` instead.
  - The new contract is in items.json: `plate` (a fresh copy flies to the next free `plate_spot_<n>`, up to 4), `sauce` (a squiggle of `colour` from `fx_sauce_<key>`), `dust` (`colour` from `fx_shaker_curry`) and `clear` on `act_plate` ("Guten Appetit").
  - The grate sausages are now inside `sausages_grill` (under `act_grill_swing`), so the swing still carries them.
  - I did not touch site/src, because the brief reserves it for the engineer. The smallest change that stops the stand-ins is to make line 68 `if (id === 'wurst' && !has(nodes, 'act_sausage') && !has(nodes, 'act_wurst_'))`. The Bratwurst stall should not go live until wurst.js has the four actions.
- **The brief and the judges' check differ on act_ names.** "Only the plate set plus the grill keep act_ names" is the judges' wording. The brief also says to keep the smoke source and the Marktblatt as they are, so `act_smoke` and `act_writing_paper` remain, and check_props allows exactly these 14 act_ nodes on the stall.
- **Bierstand headroom is thin:** 2,005 triangles, against the 2,000 that check_props asks for. If the carpenter's stall grows, the cheapest cuts are:
  - the Bügelflaschen's wire bails and rubber rings (about 100);
  - one back row on a riser (about 200–300);
  - one crate (about 450).
- **Lite ratios.** The lite bottle shelves keep 64–72 % of the full triangles. The bottles are already at 4 facets over 240° in lite, and the set's bounds must match the full set's. These are check_props warnings, not budget failures, and the lite files are small (66 and 56 kB).
- **Krakauer texture (fixed in pass 2).** It has its own smoked casing, `pr_smoked_casing`, on the print atlas. The print atlas now has 80 free rows left (1968 of 2048 used).
- **From earlier rounds, not mine:** the "Transfusion Audit" project title on a Bierdeckel and the vom Fass board reads clinical. This is for the writer or Mac.
- **Credits.** No third-party assets were used. The breweries, labels and stamps are invented and drawn procedurally with the bundled OFL fonts.
