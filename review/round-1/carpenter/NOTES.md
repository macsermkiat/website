# Carpenter: round 1 notes (pass 2)

Pass 2 was built and judged on the cloud machine (CPU, 2 threads). All kit textures, glb files and previews in this folder were regenerated in this pass from the current scripts. Nothing here comes from the earlier Mac run.

## What changed in pass 2 (judge fixes)

| Judge fix | What I did | How to check |
|---|---|---|
| Wood metal = roughness (kit bake bug) | `mats.bake_kit` clears the old link before it bakes a constant. The kits were rebaked at `KIT_VERSION = "v11"`. | `deco_kit_wood_rm.webp` and `deco_kit_oak_rm.webp`: B mean is 1/255 (WebP chroma noise, max 18). Before, the mean was 170. |
| AO atlas black and streaky in three.js | `bake.bake_ao` drops tiny islands (rivets, letters) onto a light patch, fills empty texels from the nearest island so no black bleeds through mipmaps, and remaps AO to `[0.32, 1]`. | The embedded AO mean is 0.52–0.56 in every stall (was 0.28). See the `*_threejs.jpg` shots: no dark streaks. |
| Iron kit flat grey | New iron graph: mid-grey forged iron with hammer dents, small rust blooms and runs, soot and pitting, plus a real normal map. | `deco_kit_iron_color.webp` RGB std is about 7.5/255 (was 1). Normal std is 6. |
| Signs illegible | Deco signs are bigger boards with text at 0.8 of the board height and a 14 mm raised depth. The Bratwurst sign spotlights in the preview are wide and soft. Gold paint is now half metallic (0.5), so gold letters and stars no longer go black in three.js. | `deco_contact_sheet.jpg`; `stall_gluehwein_threejs.jpg` (gold stars now read) |
| Bratwurst not sooty, grill a black box | Lap boards get vertex columns (`Hut(lap_segs=8)`) so the soot plume, eave soot and soot runs actually reach the siding. The ember bed is raised under the grate. Heat staining (burnt, straw, bronze, blue) is on the firebox. The hood and stovepipe have riveted seams and soot. | `stall_bratwurst_preview.jpg`, `stall_bratwurst_threejs.jpg` (coals glow between the bars) |
| Wood realism at counter distance | The spruce tile has more contrast (colour std 18/255, was 8) with hard latewood, resin pores and fibre. A new `oak` tile for counter tops has pore bands, ray flecks, scratches and mug rings. Counters carry a vertex wear grid (`hut.counter_wear`) that darkens the front edge where hands rest. | The counters in every preview |
| Snow caps are white blobs | New `snow_cap(courses=...)`: on shingle roofs the snow lies in one strip per course and sinks below every butt, so each shingle row shows as a dark line. There is a bare, wandering band under the ridge. On board roofs the snow is thin enough for the cover battens to show. No more melt-hole patches. | All previews |
| Deco lite files at 35–51 % | In lite, bulb detail is capped at 5x3 even when a caller asks for more (that was the leak), lap boards are 1.6x taller and roof boards 1.8x wider. | Deco lite is now 27–35 % (table below). |
| three.js check under the site lighting | `node blender/stalls/web/shoot.mjs --ao on` loads each glb with `site/src/lighting` (SwiftShader). | `stall_*_threejs.jpg` (snow off, the site default) |
| Bücher third light (Codex) | The vendor's `prop_books_counter` no longer has `light_lamp`. The assembled stand has `light_0` and `light_1` only. | node listing |
| Download budget (Codex) | **Section stalls now share the kit textures** with the deco stalls (`deco_kit_*.webp`, by relative URI) instead of embedding their own copies. Section AO is baked at 768 px (lite 384) so the exporter never packs it into a kit map. | See "Budgets": the 13 stalls went from 10.3 MB to 8.6 MB desktop and from 3.4 MB to 2.3 MB lite. |

## What was built (unchanged scope)

- `blender/lib/` is the shared helper library: `nmlib.geo.Part` (the primitive builder), `mats` (baked tiling kits `wood oak paint iron` and simple materials), `carpentry` (walls, roofs, shingles, snow, valances, signs, bulb strings, garlands), `bake` (AO), `export` (named empties, glb export through `optimize.mjs`), `render` (night previews, contact sheet), and `glb_tools.py` (report, check, texture externalisation). The API is documented in `blender/lib/README.md`. The stall scripts use only this API.
- The four section stalls in `blender/stalls/`, built on the parametric `hut.py`:
  - **Glühwein**: tall front-gabled hut, red-and-gold painted trim, scalloped valance with star cut-outs, star board in the gable, gold star finial, fir garland. The sign "Glühwein" is in Fraktur.
  - **Bratwurst**: low and sooty, with dark lap siding blackened above the grill. A riveted iron chimney hood hangs over a charcoal grill set into the counter, and a stovepipe with a rain cap rises through the board-and-batten roof. There is a firewood lean-to and a black "Bratwurst" board on the roof.
  - **Bierstand**: Bavarian bar with blue-and-white Rauten pennants along the eaves, maypole-striped posts, and a counter front of four stave-built half barrels with iron hoops. The crest sign reads "Bier vom Fass".
  - **Bücherstand**: bottle-green antiquarian hut with two glazed display cabinets, a canted bay window with a copper hood, an iron lantern and a hand-painted swallow-tail sign "Bücher".
- `deco.py` builds the nine deco stalls: Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni and Kartoffelpuffer. Each has its sign, slots, one light, bulbs and snow, and none has goods.
- Previews: `stall_*_preview.jpg` are Cycles renders (1280x720, 48 samples, OIDN, 3/4 front view at night). `deco_contact_sheet.jpg` shows the nine deco stalls (840x600 tiles, 48 samples). `stall_*_threejs.jpg` are the same glb files in three.js under the site lighting.
- The mugs, pot, sausages, rolls, beer glasses and books in the Cycles previews are **render-only stand-ins**. They are not in the glb files. The vendor supplies goods at `slot_counter`, `slot_shelf_1`, `slot_shelf_2` (and `slot_cabinet_l`/`slot_cabinet_r` on the Bücherstand). The three.js shots show the bare glbs, so their counters are empty.

## Triangles and file sizes (after `blender/lib/optimize.mjs`, measured on the files in `site/public/models`)

| File | Triangles | Size | Lite triangles | Lite size | Lite / full |
|---|---|---|---|---|---|
| stall_gluehwein | 41,129 | 0.99 MB | 8,462 | 0.21 MB | 21 % |
| stall_bratwurst | 41,727 | 1.00 MB | 8,021 | 0.24 MB | 19 % |
| stall_bier | 44,871 | 1.07 MB | 10,181 | 0.25 MB | 23 % |
| stall_buecher | 34,841 | 0.94 MB | 6,609 | 0.19 MB | 19 % |
| deco_lebkuchen | 14,837 | 0.46 MB | 4,274 | 0.13 MB | 29 % |
| deco_mandeln | 17,433 | 0.49 MB | 4,941 | 0.13 MB | 28 % |
| deco_kerzen | 15,463 | 0.47 MB | 4,334 | 0.13 MB | 28 % |
| deco_spielzeug | 17,374 | 0.50 MB | 5,329 | 0.15 MB | 31 % |
| deco_schmuck | 17,311 | 0.50 MB | 4,603 | 0.13 MB | 27 % |
| deco_kaese | 12,366 | 0.41 MB | 4,054 | 0.13 MB | 33 % |
| deco_crepes | 14,621 | 0.45 MB | 3,987 | 0.12 MB | 27 % |
| deco_maroni | 13,492 | 0.42 MB | 4,709 | 0.14 MB | 35 % |
| deco_puffer | 16,324 | 0.48 MB | 4,807 | 0.14 MB | 29 % |
| shared kit `deco_kit_*.webp` (used by all 13 stalls) | | 0.44 MB | | 0.18 MB (`*.lite.webp`) | |

- **Budgets.** With the vendor's current props, the assembled section stalls come to Glühwein 58.8k triangles / 1.36 MB, Bratwurst 53.6k / 1.15 MB, Bier 57.5k / 1.20 MB and Bücher 39.9k / 1.19 MB, all within the 60k / 3 MB budget. Glühwein is close to the triangle limit. Every deco stall is under 20k triangles and 1 MB.
- **First-load share for my 13 stalls:** 8.6 MB desktop (4.0 section + 4.2 deco + 0.44 kit) and 2.3 MB lite (0.9 + 1.2 + 0.18).
- **Contract checks.** `glb_tools.check_stall` passes on every file: `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `light_*`, `bulbs_*`, `snow_*`, `cam_view`, `cam_target`, and material `bulb_warm`. There are 2 `light_` empties per section stall and 1 per deco stall. `slot_counter` is at y = 1.050 in every file, and the counter boards' top face is exactly 1.05 m. `gltf-transform validate` reports no errors.
- **Sign text:** Glühwein, Bratwurst, Bier vom Fass, Bücher, Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer.

## Rebuild

`/home/claude/tools/bpy-venv/bin/python blender/stalls/<stall>.py [--no-render] [--no-lite] [--samples N] [--res WxH]`, and `.../deco.py [--only kaese,crepes]`. With the machine shared (load 13–20), a stall takes about 1–2 min to build, AO-bake and export both LODs, and 5–6 min to render. The kit rebake after a version bump takes about 5 min. bpy segfaults at exit after writing everything; this is harmless.

## Notes for other roles and the market owner

1. **Kit version bump (v11).** Gold paint is now metallic 0.5 (was 1.0), and wood and oak metal is 0. **Ride builder:** carousel, Ferris wheel, bandstand and instruments use kit `paint`, and their glb files embed the old maps. Please re-export them (`mats.ensure_kit()` rebakes automatically).
2. **Shared kit textures.** All 13 stall glbs now reference `deco_kit_*.webp` (lite: `deco_kit_*.lite.webp`) in the same folder. Keep those files next to the glbs. The site's loader already has `THREE.Cache.enabled` and shares image sources.
3. **Lighting designer: signs at night.** In three.js the section signs are lit only by the hemisphere and the two `light_` empties inside the stall, so the Glühwein and Bratwurst boards stay dark (see the `*_threejs.jpg` shots). Every stall has a `slot_sign` empty 5 cm in front of its sign face. A small, unshadowed, short-range warm spot at `slot_sign`, aimed back at the sign (the gooseneck lamps in the models are where it would come from), would make all 13 signs legible.
4. **Market owner:** please replace the `gltf-transform optimize` line in docs/BUILD.md with `node blender/lib/optimize.mjs in.glb out.glb --texture-size 1024`. The CLI step deletes every `slot_`/`light_`/`cam_` empty and renames `bulb_warm`. `.gitignore` already lists `__pycache__/`, but `blender/props/__pycache__/*.pyc` files are tracked in git and should be removed from the index.
5. COLOR_0 (plank tints, soot, wear) is intentional. Occlusion is on TEXCOORD_1. Extra nodes: `grill_coals` (emissive ember mesh) and `smoke_origin` on the Bratwurst stall; `slot_cabinet_l` and `slot_cabinet_r` on the Bücherstand.
6. Footprints are unchanged: Glühwein 3.4 x 2.5 m; Bratwurst 3.9 x 2.5 m plus a 0.8 m lean-to on +X; Bier 4.2 x 2.6 m; Bücher 3.7 x 2.5 m plus a 0.35 m bay on -X; deco stalls 2.6–3.4 x 2.2 m.

## Open issues and what I would improve next

- **Sign lighting in the browser** depends on the lighting designer (note 3). In Cycles the signs read, but in three.js the Glühwein and Bratwurst boards are dim.
- **Rauten pennants in three.js:** at 1024 px the lozenges on the Bier pennants mip down to pale blue-white at preview distance. A dedicated 2-colour pennant texture, or bigger lozenges, would keep the pattern.
- **Glühwein plus props is at 58.8k of 60k triangles.** The bevelled Fraktur text (about 2k triangles) or the shingle bevels are the first things to cut if the vendor needs room.
- **Bratwurst ember bed** is visible between the grate bars in three.js (emissive plus bloom). In the Cycles preview the sausage stand-ins cover most of it. The vendor's `prop_wurst_counter` also has a grill and coals, so the two grills need to be reconciled: either the vendor's sits on mine, or I drop my grate.
- **Deco signs** now read at contact-sheet size, except Holzspielzeug (blue on white under dim light). It would read better on a darker board.
- **Bevel cost:** chamfers are real geometry. A baked edge-normal trim sheet could halve the wall triangles.
- The snow strips are regular on very straight roofs. A few slipped or drifted patches at the eaves would help.
