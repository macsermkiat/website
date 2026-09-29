# Vendor — round 1 notes

All goods are modelled in code under `blender/props/` and textured from one procedural atlas. No third-party models or images are used; the fonts are OFL (see CREDITS.md, Vendor section).

Rebuild:

```
python3 blender/props/vendor_atlas.py                                   # atlas -> blender/out/vendor/
/home/claude/tools/bpy-venv/bin/python blender/props/build_props.py      # all sets, lite + full, section previews
    [--only prop_bier_counter,...] [--no-render] [--samples 40] [--sheet]   # --sheet = deco contact sheet
    [--render-only prop_wurst_counter,...]                                # rebuild all, re-render only these previews
python3 blender/props/check_props.py                                    # contract checks
```

(bpy can segfault on exit after `build_props.py` has written everything; the outputs are complete.)

## Files

| file | what it is |
|---|---|
| `blender/props/vendor_atlas.py` | 2048 atlas (color, rm = G roughness / B metal, normal) plus coal_color / coal_emit and regions.json |
| `blender/props/vlib.py` | mesh builder, materials, PropSet (named empty + `<name>_mesh` child), export, preview scene |
| `blender/props/goods.py` | shared goods: mugs, bottles, jars, crates, glasses and foam, barrels, sausages, rolls, trays |
| `blender/props/set_*.py` | one module per stall family (gluehwein, bier, wurst, books, deco) |
| `blender/props/build_props.py`, `check_props.py` | build, report and contract check |
| `site/public/models/prop_*.glb`, `prop_*.lite.glb` | 17 prop sets |
| `site/public/models/prop_tex_*.webp` (`.lite.webp`) | the shared atlas, externalised once and referenced by every prop glb (2048 full / 1024 lite) |
| `site/public/models/props.json` | set -> {slot, stall, model, lite, asset}, plus the same data as a `sets` list |

## Sets, slots and budgets

Triangles are for the full glb, with lite in brackets. kB is the glb without the shared atlas. The atlas is 0.61 MB full and 0.22 MB lite, and it loads once for all 17 sets.

| set | stall | slot | tris (lite) | kB (lite) | size x·y·z m |
|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 10566 (5760) | 108 (83) | 2.11 · 0.50 · 0.67 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 9216 (5192) | 76 (50) | 2.28 · 0.22 · 0.34 |
| prop_bier_counter | bierstand | slot_counter | 8836 (4402) | 82 (60) | 2.06 · 0.36 · 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 4724 (2804) | 46 (32) | 2.27 · 0.36 · 0.35 |
| prop_wurst_counter | bratwurst | slot_counter | 15810 (4296) | 172 (74) | 2.22 · 0.47 · 0.64 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1580 (544) | 83 (68) | 1.97 · 0.23 · 0.30 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1652 (584) | 90 (73) | 1.97 · 0.23 · 0.30 |
| prop_books_counter | buecherstand | slot_counter | 2014 (1502) | 31 (27) | 1.97 · 0.36 · 0.40 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 6226 (3632) | 62 (42) | 2.20 · 0.30 · 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 3844 (2032) | 32 (23) | 1.97 · 0.46 · 0.45 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 7452 (5500) | 62 (52) | 2.10 · 0.45 · 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 5312 (4104) | 57 (49) | 2.07 · 0.31 · 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 7592 (5320) | 66 (53) | 2.16 · 0.30 · 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 3040 (1488) | 24 (16) | 1.95 · 0.43 · 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 2072 (1302) | 25 (21) | 1.97 · 0.46 · 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4956 (1620) | 49 (24) | 1.87 · 0.46 · 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 2674 (1450) | 32 (22) | 1.86 · 0.48 · 0.26 |

Every set is at most 0.5 m deep.

Section stalls, carpenter stall plus my props, full detail:

| stall | stall tris | + props | total / 60k | MB incl. atlas / 3 MB |
|---|---|---|---|---|
| gluehwein | 38649 | 19782 | 58431 OK | 2.25 OK |
| bierstand | 44973 | 13560 | 58533 OK | 2.32 OK |
| bratwurst | 26713 | 15810 | 42523 OK | 1.98 OK |
| buecherstand | 31895 | 5246 | 37141 OK | 2.25 OK |

Deco stalls, stall plus goods against 20k: kaese 14.8k, crepes 17.0k, maroni 18.4k and puffer 18.9k are OK. Lebkuchen 20.9k, mandeln 22.9k, kerzen 23.0k, spielzeug 24.4k and schmuck 26.1k are over. See the contract issues.

## Animation nodes and pivots

The glTF exporter's quantisation rewrites mesh-node transforms. So every act_ / rot_ / light_ node is an **empty** with the pivot as its origin, and the geometry sits in a `<name>_mesh` child. The engine animates the empty.

- **Glühwein:** `act_pot`, `act_pot_lid` (hinged at the back rim, modelled open at −0.62 rad about X), `act_ladle`, `act_steam`, and `act_mug_0..9`. Mugs 0, 5 and 9 are boots. Mugs 0, 1, 3 and 4 are filled, with `act_steam_<i>` just above the rim. Mugs 6–9 sit upside down on the drying tray.
- **Bier:** `act_tap_0..2` pivot at the handle base (z 0.46, local z 0 to 0.168), so the handle tilts forward. `act_glass_0..6` (3 Maß, 4 Willibecher), each with a `foam_<i>` child node that holds only the foam head.
- **Bratwurst:** `act_grill` is the fire bowl, origin at the bowl centre on the counter. Its `coals` child uses the emissive `coal_glow`. `act_grill_swing` is the round grate on three chains, pivoted at the hook, for a gentle swing. `act_sausage_0..7` have their origin at each sausage's centre, long axis X. There is also `act_smoke`.
- **Bücher:** `act_book_0..` on shelf 1, `act_book_100..` on shelf 2 and `act_book_200..203` stacked on the counter. Each book's origin is at its spine foot, so a pull-out moves along +Y. The counter set has `light_lamp` at the lamp's bulb.
- **Deco:** `rot_pyramid` is the Weihnachtspyramide on the Spielzeug counter.

The five reading-list titles are individual books with legible spines, grouped in the middle of shelf 1 (see prop_books_shelf_1.jpg): The Order of Time; Gödel, Escher, Bach; The Feynman Lectures on Physics (3 volumes); Being You; The Book of Why. The other spines use 48 generic real titles drawn from physics, philosophy and literature.

## Previews

These are in `review/round-1/vendor/`. They are Cycles renders at 1280x720 with 40 samples and the denoiser, on a plain wooden counter at night. The key lights are placed where the stall's light_0 and light_1 sit relative to the slot.

- Sections: prop_gluehwein_counter.jpg, prop_gluehwein_shelf.jpg, prop_bier_counter.jpg, prop_bier_back.jpg, prop_wurst_counter.jpg, prop_books_shelf_1.jpg, prop_books_shelf_2.jpg, prop_books_counter.jpg
- Deco: deco_goods_contact_sheet.jpg, a 3×3 grid of 640x360 tiles at 32 samples, scaled to 1280 px wide. Some tiles crop the outermost goods.

## Open issues and contract questions

1. **The deco budget is not achievable as stated.** The carpenter's deco stalls are already 11.8–19.0k triangles, so at 20k for stall plus goods Mandeln leaves under 1k for goods. I trimmed the goods to 2–7.6k. Could the deco budget be 20k for goods, or 25k for stall plus goods? Otherwise the carpenter needs to cut the stalls.
2. **Lite ratio.** Lite props are about 27–75% of full, not a third. Books and small deco goods are already near their floor, because boxes and low-segment lathes cannot shrink much further. The largest saving is on the grill.
3. **The Bücher stall has three lights.** `light_lamp` on the counter adds to the stall's two lights. If the engine caps lights per stall, drop it or reuse light_1.
4. **The Bratwurst firebox.** The carpenter's stall has a built-in firebox under slot_counter x −1.75..−0.15. My fire bowl sits at x −0.9 on top of it. If the firebox moves, `GX` in set_wurst.py follows it.
5. **Slot widths.** The Bücher shelves and counter are about 2.1 m, so the book rows stay within ±0.98 m. The Bier counter is 0.82 m deep and the props use only the front 0.5 m.
6. **Empty shelf_2 on Glühwein and Bier.** Only slot_shelf_1 is filled there. It is easy to add a set if the art director wants it.
7. **No AO bake on the props.** The contact shadows come from the engine. A small baked AO in vertex colour would help mugs and books sit down.
8. **props.json has two forms.** It carries both the `{set: {...}}` map the task asked for and a `sets` list, which the engine currently reads. One should go once the engine settles.
9. **Transmission glass.** Beer glasses and bottles use transmission, with alpha blend in lite. On low-end GPUs the engine may want to force the lite glass material.

## Next I would

- Bake AO into vertex colours, and add a second LOD for the deco goods to hit the budget.
- Give the steins and bottles embossed or printed detail through the normal atlas.
- Add a few sold-out and price tags per stall.
- Add a slight wind sway on the hanging deco goods, grouped under `act_hang_*`.
