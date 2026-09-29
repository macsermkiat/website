# Vendor, round 1, pass 2 notes

All goods are modelled in code under `blender/props/` and textured from two procedural atlases (goods and books). No third-party models or images are used; the fonts are OFL (see CREDITS.md, Vendor section). This pass ran on the cloud machine: every set was rebuilt from the scripts, every glb re-exported with its AO bake, and every preview re-rendered.

Rebuild:

```
python3 blender/props/vendor_atlas.py                                    # atlases -> blender/out/vendor/
/home/claude/tools/bpy-venv/bin/python blender/props/build_props.py       # all sets, lite + full, AO, previews
    [--only a,b] [--no-render] [--no-lite] [--no-ao] [--samples 40] [--res 1280x720]
    [--render-only a,b] [--shots wide|hero|wide,hero]
python3 blender/props/check_props.py                                     # contract checks (exit 1 on FAIL)
```

bpy may segfault on exit after `build_props.py` has written everything; the outputs are complete.

## What changed in pass 2 (judges' fixes)

| Judges asked | Done |
|---|---|
| Sausages ride the swinging grate | `act_sausage_0..7` are children of `act_grill_swing`. Pass 2's first cut had them double-offset 0.38 m below the grate; fixed and checked (the set now stands on its slot, z ≥ 0). |
| Grilled sausages, ember coals | New 256×448 sausage skin regions: browned skin, diagonal grate char marks on two sides, fat blisters, darker twisted ends. Coals are matt black with grey ash; `coal_glow` emits only in the cracks (`prop_tex_coal_emit.webp` is black elsewhere). |
| Beer foam and glass | Separate `foam_<n>` node per glass: domed, bubbly head with a slight spill over the rim on some glasses; no dark rim band; the glass has real wall thickness (2.5 mm Willibecher, 4.5 mm dimpled Maßkrug). |
| Barrels | Stave oak texture with grain, flecks and weathering, forged iron hoops. The head is now oak end grain on three boards with dark joints and a fire-branded mark; the painted crack lines are gone. |
| AO baked into the occlusion texture | Every set bakes Cycles AO (512 px full, 256 px lite) onto a second UV map and ships it as the glTF `occlusionTexture` on TEXCOORD_1, with the counter or shelf top as a ground plane so goods get contact shading. Glass, liquids, emissives and the cased-glass lamp shade are left out on purpose. check_props fails if any other material lacks it. |
| Fill the counters and shelf_2 | Bücher counter: two stacks, a row between bookends, an open book on a stand and one flat, a tray of bookmarks, three price cards, the lamp and cash box. Wurst counter: steel tray of done sausages, basket of rolls, served Bratwurst im Brötchen, mustard and ketchup pots, squeeze bottles, napkins, tray stack, A-frame price sign. New `prop_gluehwein_wine` (slot_shelf_2) and `prop_bier_shelf` (slot_shelf_2); the wine shelf also has a straw-packed crate in its middle gap. |
| Bücher third light | `light_lamp` is gone. The lamp keeps only its emissive `lamp_glow` bulb; check_props fails if any prop set adds a `light_` empty. |
| Books identify themselves | Each `act_book_<n>` now carries `{name, kind, title, author, cover_material}` in its glTF node extras (three.js `userData`), which `actions/stalls.js` already reads first. items.json has the same data plus the cover's UV rect. |
| One book_cover material per book | The web optimiser's `dedup()` merged all identical `book_cover_<n>` materials into `book_cover_0`. `vlib.split_book_materials` restores one material per book after optimisation (JSON only; textures stay shared). |
| props.json in one form | Only the `sets` list the engine reads (`site/src/engine/props.js`). |
| Honest checker | check_props FAILs on contract breaks, including a section stall total that leaves under 2k triangles headroom, and WARNs on the deco budget and lite ratio. |
| Close-ups and crops | Each section set has a wide shot, auto-framed to the set's bounding box, and most have a tight hero close-up (`*_hero.jpg`). Deco frames are auto-framed per set, so the contact sheet no longer crops anything. |
| Lite versions | Lower lathe, sphere and ring counts, dropped coasters, badges, loops and extra small goods; 512 px lite textures. See the table for the ratios. |
| Section budgets | Trimmed the Wurst (roll, chain, pot and tray detail), Glühwein (wine glasses, oranges, jars, capsules, shelf bottles) and Bier (hoops, shelf glasses) sets as the carpenter's stalls grew this pass. |
| Grill bowl seat, frame pegs | The bowl stands on the firebox grate at z 0.026. Book rows stop at x ±0.925, clear of the braces at ±0.95. |
| Bücherstand file size | The books' normal and roughness maps ship at 1024 px (colour and spine lettering stay 2048), which keeps the stall under 3 MB. |

## Sets, slots and budgets

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Every set is at most 0.5 m deep, stands on its slot (z ≥ 0) and stays under the 1.15 m front opening.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7266 | 3101 (43 %) | 180 / 108 | 1.99 × 0.50 × 0.67 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 5190 | 2314 (45 %) | 135 / 75 | 2.28 × 0.22 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 4360 | 2046 (47 %) | 98 / 62 | 2.32 × 0.25 × 0.46 |
| prop_bier_counter | bierstand | slot_counter | 6812 | 2486 (36 %) | 136 / 83 | 1.94 × 0.37 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 2840 | 1180 (42 %) | 84 / 39 | 2.27 × 0.33 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3052 | 1322 (43 %) | 55 / 29 | 1.69 × 0.23 × 0.22 |
| prop_wurst_counter | bratwurst | slot_counter | 11854 | 3530 (30 %) | 278 / 123 | 2.66 × 0.47 × 0.67 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1456 | 524 (36 %) | 138 / 111 | 1.86 × 0.23 × 0.30 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1498 | 554 (37 %) | 151 / 118 | 1.86 × 0.23 × 0.30 |
| prop_books_counter | buecherstand | slot_counter | 2078 | 1072 (52 %) | 91 / 63 | 2.05 × 0.43 × 0.40 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 4168 | 1428 (34 %) | 101 / 40 | 2.20 × 0.30 × 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 2404 | 940 (39 %) | 63 / 32 | 1.97 × 0.46 × 0.44 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3246 | 1168 (36 %) | 79 / 34 | 2.10 × 0.44 × 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 3680 | 1660 (45 %) | 110 / 55 | 2.07 × 0.31 × 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 3816 | 1500 (39 %) | 89 / 42 | 2.16 × 0.30 × 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 3040 | 1248 (41 %) | 60 / 32 | 1.95 × 0.43 × 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 2016 | 911 (45 %) | 52 / 33 | 1.97 × 0.46 × 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4036 | 1266 (31 %) | 96 / 39 | 1.87 × 0.46 × 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 2674 | 958 (36 %) | 63 / 32 | 1.85 × 0.48 × 0.26 |

All prop glbs together: 2.06 MB full and 1.15 MB lite, plus the shared textures.

Shared textures: 0.86 MB full and 0.12 MB lite, loaded once for all sets (`prop_tex_atlas_*`, `prop_tex_books_*`, `prop_tex_coal_*`).

Section stalls, the carpenter's current stall plus my props:

| stall | stall tris | + props | total / 60k | headroom | MB with shared textures / 3 |
|---|---|---|---|---|---|
| gluehwein | 41129 | 16816 | 57945 OK | 2055 | 1.85 OK |
| bierstand | 44871 | 12704 | 57575 OK | 2425 | 1.79 OK |
| bratwurst | 41727 | 11854 | 53581 OK | 6419 | 1.74 OK |
| buecherstand | 34841 | 5032 | 39873 OK | 20127 | 2.16 OK |

Deco stalls (stall + goods, WARN only; see open issue 1):

| deco stall | stall tris | goods | total / 20k |
|---|---|---|---|
| lebkuchen | 14837 | 4168 | 19005 OK |
| mandeln | 17433 | 2404 | 19837 OK |
| kerzen | 15463 | 3246 | 18709 OK |
| spielzeug | 17374 | 3680 | 21054 over |
| schmuck | 17311 | 3816 | 21127 over |
| kaese | 12366 | 3040 | 15406 OK |
| crepes | 14621 | 2016 | 16637 OK |
| maroni | 13492 | 4036 | 17528 OK |
| puffer | 16324 | 2674 | 18998 OK |

## Animation nodes and pivots

Every act_ / rot_ node is an empty with the pivot as its origin; its geometry is a `<name>_mesh` child, because the optimiser rewrites mesh-node transforms.

- **Glühwein counter:** `act_pot` (kettle on its burner), `act_pot_lid` (hinged at the back rim, modelled open), `act_ladle`, `act_steam` (empty just above the Glühwein), `act_mug_0..9`: eight classic mugs and two boots (0 and 5); mugs 0, 1, 3 and 4 are full, each with a steam empty `act_steam_<i>` above it; mugs 6–9 stand upside down on the drying board (origin on the rim, which is their base).
- **Glühwein shelf:** `act_bottle_12..17` (Heidelbeer-Glühwein, rum, Kinderpunsch and others), `act_mug_10..12` spare mugs, spice jars, orange slices, cinnamon bundles, star anise.
- **Wine shelf:** `act_bottle_0..9`: Riesling (Mosel, Rheingau, Pfalz, Eiswein), Spätburgunder (Baden, Ahr), Dornfelder (Rheinhessen, Pfalz), Silvaner (Franken Bocksbeutel, Rheinhessen), each with its own label, capsule and glass colour; `act_wineglass_0..2`.
- **Bier counter:** `act_tap_0..2` pivot at the handle's base on top of the faucet (local z 0 to 0.168), so the handle tilts forward. `act_glass_0..5` (three Maß, three Willibecher), each with a `foam_<n>` child holding only the foam head.
- **Bier shelf:** `act_glass_10..15`, clean glasses upside down (origin on the rim).
- **Bratwurst:** `act_grill` (fire bowl on the firebox grate, `coals` child with `coal_glow`), `act_grill_swing` (grate on three chains, pivot at the hook), `act_sausage_0..7` on the grate as children of the swing, origin at each sausage's centre, long axis X; `act_sausage_8..11` keeping warm; `act_roll_0..9` (origin at the base); `act_served_0`; `act_smoke`.
- **Bücher:** `act_book_0..` shelf 1, `act_book_100..` shelf 2, `act_book_200..212` counter. Standing books have their origin at the foot of the spine, so a pull-out moves along +Y; lying books have it under the middle of their lowest face. Each has material `book_cover_<n>`; its +X board carries the cover art.
- **Deco:** `rot_pyramid` on the Holzspielzeug counter.

The five reading-list titles stand together in the middle of shelf 1 (`act_book_21..27`): The Order of Time; Gödel, Escher, Bach; The Feynman Lectures on Physics (three volumes); Being You; The Book of Why. `prop_books_shelf_1_hero.jpg` shows all five spines legibly.

## Previews

Cycles, on a plain wooden counter (or shelf) at night, lit from where the stall's light_0 and light_1 sit relative to the slot. Section shots are 1280×720 at 40 samples with the denoiser (the shared machine ran at a load of 10–18, so 48 samples cost 12 minutes a frame); deco frames are 832×468.

- Wide: `prop_<set>.jpg` for all ten section sets.
- Hero close-ups: `prop_gluehwein_counter_hero`, `prop_gluehwein_shelf_hero`, `prop_gluehwein_wine_hero`, `prop_bier_counter_hero`, `prop_bier_back_hero`, `prop_wurst_counter_hero`, `prop_books_shelf_1_hero`, `prop_books_counter_hero`.
- Deco: `deco_<key>.jpg` per stall and `deco_goods_contact_sheet.jpg`.

## Open issues and contract questions

1. **Deco budget (needs a market-owner decision).** The carpenter's deco stalls grew again this pass (12.4–17.4k). I cut the goods to 2.0–4.2k, and seven of nine now fit 20k. Spielzeug (21.1k) and Schmuck (21.1k) are over because their stalls alone are 17.4k and 17.3k. Please decide: 20k for the goods alone, 25k for stall plus goods, or the carpenter trims those two stalls. check_props WARNs on this rather than failing.
2. **Section headroom is thin and moves with the stalls.** The Glühwein stall went from 38.0k to 41.1k and the Bierstand from 41.7k to 44.9k during this pass, so I trimmed my sets to keep 2k headroom: Glühwein 2,055 left, Bier 2,425, Bratwurst 6,419, Bücher 20,127. check_props FAILs below 2k, so a further stall change will show up immediately.
3. **Lite ratio.** The large sets are near a third (Wurst 30 %, Bier counter 36 %, the book shelves 36–37 %, several deco sets 31–39 %). The smaller sets are 41–52 %, because they are mostly boxes and low-segment lathes that cannot shrink much further (the Bücher counter is 1,072 lite triangles in all). The lite total is 1.15 MB of glb plus 0.12 MB of textures.
4. **The Bratwurst firebox.** The fire bowl sits at x −0.9 from slot_counter, on the carpenter's built-in firebox (x −1.75..−0.15). If the firebox moves, `GX` in set_wurst.py follows it. The price sign reaches x 1.54, inside the 1.85 m counter end.
5. **Transmission glass.** Beer glasses, bottles and wine glasses use transmission on desktop and alpha blend in lite. On weak GPUs the engine may want the lite glass everywhere.
6. **Renders at 40 samples.** The shared machine ran at a load of 10–18, so 48 samples cost about 12 minutes a frame. The section shots use 40 samples plus the denoiser (the Glühwein counter and Bier back shelf, re-rendered after fixes, use 48).

## Next I would

- Give the steins and bottles embossed detail through the normal atlas, and add a few sold-out and price tags per stall.
- Add a slight sway on the hanging deco goods, grouped under `act_hang_*`.
- A second, lower LOD of the deco goods for the far view, once the deco budget is settled.
