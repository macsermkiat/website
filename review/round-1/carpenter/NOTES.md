# Carpenter: round 1 notes

## What was built

**Shared library `blender/lib/`** (API documented in `blender/lib/README.md`)
- `nmlib/geo.py`: `Part`, a builder that collects many primitives into one mesh with one material. The primitives are chamfered boxes, slabs, cylinders, spheres, lathes, lofts, tubes, tori, extruded 2D shapes with cut-outs, and 3D text. Each primitive gets its own tiling UV window and a tint in `COLOR_0`, and a per-vertex `shade(p)` hook adds grime and soot.
- `nmlib/mats.py`: three **tiling kit textures** baked once from Blender procedurals. The noise is sampled on a 4D torus, so every tile is seamless. `wood` has rings, knots with ring deflection, fibre, cracks, dents and silvering. `paint` is an atlas of 8 chipped-paint bands, with gold leaf and Bavarian Rauten among them. `iron` is forged iron with rust and soot. Each kit ships base colour, roughness/metal and normal maps, plus simple materials (`bulb_warm`, `snow`, `glass`, `fir`, …).
- `nmlib/carpentry.py`: plank walls, lap siding, floors, the `Slope` roof frame, shingles, board roofs, bargeboards, fascia, snow caps, carved valances (scallop / point / wave / step, with star, heart or circle holes), signs, bulb strings and fir garlands.
- `nmlib/bake.py`: AO bake into a second UV map, wired as the glTF occlusion texture (`texCoord: 1`).
- `nmlib/export.py` (named empties, `stall_markers`, `export_glb`), `nmlib/render.py` (night preview scene, contact sheet), `glb_tools.py` (report, contract check, texture externalisation) and `optimize.mjs` (the web step, see "Contract issues").
- Five OFL fonts are bundled in `blender/lib/fonts/` for the signs (credited in CREDITS.md).

**Stalls `blender/stalls/`**
- `hut.py` is a parametric hut: carcass, the 1.05 m counter, shelves, roof, bulbs, snow and markers. `pipeline.py` runs full build → AO → optimise, then the lite build, then the preview.
- `gluehwein.py` replaces the old worked example; the old script is in git history and its render is still in `review/reference/`. It is a tall front-gabled hut, 4.6 m to the gold star finial. It has red bargeboards with a carved scalloped edge, a scalloped lambrequin with star cut-outs across the 0.5 m front overhang, and a red star board in the gable lit from inside. The posts, rails and counter lip are red and gold, with gold stars under the counter and a fir garland with baubles. The arched sign reads "Glühwein" in gold Fraktur.
- `bratwurst.py` is low, broad and sooty. It has dark lap siding blackened above the grill by a soot plume shader and a board-and-batten roof. A riveted iron chimney hood hangs over a charcoal grill set into the left of the counter, with the stovepipe and rain cap going up through the roof. A firewood stack sits under a lean-to on the right. "Bratwurst" is on a black board standing on the roof, with two gooseneck lamps.
- `bier.py` is a wide Bavarian bar in light spruce board-and-batten with blue-and-white Rauten pennants along the eaves and rakes. The posts are ringed blue and white like a maypole and carry knee braces. The bar front is **four half-barrels built from separate staves with iron hoops**. The crest sign reads "Bier vom Fass", with Rauten flags on poles and gooseneck lamps.
- `buecher.py` is an antiquarian bookshop in bottle-green painted boards with cream trim. It has **two tall glazed display cabinets** (glass doors with glazing bars, inner shelves, brass knobs) on either side of the counter. A **small canted bay window** with a copper hood and corbels sits on the left wall, and an iron wall lantern hangs at the right corner. The hand-painted swallow-tail sign reads "Bücher" in IM Fell italic, with gold flourishes, and hangs on chains.
- `deco.py` holds the nine deco variants: Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni and Kartoffelpuffer. They come from one hut with different width, wall type, wall tint, trim colour, valance style and cut-outs, sign style (fascia or roof crest) and font, roof cover, awning flap and stovepipe. None of them has goods.

**Previews** (in this folder): `stall_*_preview.jpg` are Cycles renders, 1280x720, 48 samples, OIDN, 2 threads, a 3/4 front view at night. `deco_contact_sheet.jpg` has all nine deco stalls. The previews are rendered **with the same tiling textures that ship in the glb files**, not with the procedurals. The mugs, pot, sausages, rolls, glasses and books in the section previews are **render-only stand-ins** so the counters don't look bare; they are not in the glb files, because the vendor owns goods.

## Triangles and file sizes (after `blender/lib/optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 38,649 | 1.46 MB | 10,985 | 0.39 MB |
| stall_bratwurst | 26,713 | 1.21 MB | 10,037 | 0.43 MB |
| stall_bier | 44,973 | 1.59 MB | 12,749 | 0.42 MB |
| stall_buecher | 31,895 | 1.44 MB | 9,745 | 0.41 MB |
| deco_lebkuchen | 14,627 | 0.46 MB | 5,161 | 0.17 MB |
| deco_mandeln | 19,030 | 0.56 MB | 7,878 | 0.20 MB |
| deco_kerzen | 15,503 | 0.47 MB | 6,923 | 0.20 MB |
| deco_spielzeug | 19,040 | 0.56 MB | 7,972 | 0.21 MB |
| deco_schmuck | 18,471 | 0.58 MB | 7,573 | 0.20 MB |
| deco_kaese | 11,785 | 0.37 MB | 5,033 | 0.16 MB |
| deco_crepes | 14,905 | 0.45 MB | 6,185 | 0.18 MB |
| deco_maroni | 13,444 | 0.45 MB | 6,868 | 0.20 MB |
| deco_puffer | 16,197 | 0.53 MB | 6,273 | 0.18 MB |
| shared deco kit textures `deco_kit_*.webp` | | 0.14 MB | | 0.05 MB (`*.lite.webp`) |

- Section stalls are 27–45k triangles and at most 1.6 MB, which leaves 15–33k triangles and at least 1.4 MB of the 60k / 3 MB budget for the vendor's props. Deco stalls are at most 19k triangles and at most 0.6 MB each, plus 0.14 MB of kit textures shared by all nine.
- The lite versions have 512 px textures, no bevels, one shingle strip per course and fewer segments. Section lite files are 28–38 % of the full triangle count. Deco lite files are 35–51 %: their full versions are already lean, and the sign text and snow caps have a fixed floor.
- Desktop first-load share for the 13 stalls is about 5.7 MB for the section stalls plus 4.6 MB for the deco stalls (kit textures included). Lite is about 3.4 MB in total.
- Every file passes `python3 blender/lib/glb_tools.py check` (slot_counter, slot_shelf_1, slot_shelf_2, slot_vendor, slot_sign, slot_front, light_*, bulbs_*, snow_*, cam_view, cam_target, and material `bulb_warm`), and `gltf-transform validate` reports no errors. `slot_counter` sits at y = 1.050 in every file: the counter boards' top face is exactly 1.05 m.
- Sign text in the models: Glühwein, Bratwurst, Bier vom Fass, Bücher, Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer.

Rebuild: `/home/claude/tools/bpy-venv/bin/python blender/stalls/<stall>.py` (add `--no-render`, `--no-lite`, `--samples N`), and `.../deco.py [--only kaese,crepes]`. Each section stall takes about 20 s to build, AO-bake and export both LODs, plus the render (3–5 min at the current load). Kit textures bake once, in about 2 min, into `blender/out/kit/`. The bpy module sometimes segfaults at interpreter exit after all files are written. This is harmless.

## Contract issues and notes for other roles

1. **Do not use `gltf-transform optimize` on assets with empties.** The CLI prunes empty leaf nodes even with `--prune false`, so every `slot_*`, `light_*` and `cam_*` empty disappears. I tested this. Its palette and join steps also merge and rename materials such as `bulb_warm`. `node blender/lib/optimize.mjs in.glb out.glb --texture-size 1024` runs the same passes (dedup, weld, prune keeping leaves, WebP, resize, meshopt) without that damage. The market owner may want to put it into docs/BUILD.md as the standard step.
2. **COLOR_0 is intentional.** Kit materials multiply base colour by the vertex colour (plank tints, grime, soot), as the glTF spec defines. GLTFLoader enables `vertexColors` automatically, so the engineer should not strip it.
3. **Occlusion is on TEXCOORD_1** (`occlusionTexture.texCoord = 1`). three.js r151+ handles this through `texture.channel`.
4. **Deco textures are external:** `deco_*.glb` reference `deco_kit_*.webp` (lite: `deco_kit_*.lite.webp`) by relative URI in the same folder. With `THREE.Cache.enabled = true` they download once. Keep these files next to the glbs. The full-size iron roughness map is packed with each variant's AO, so it stays embedded (a few kB).
5. Extra named nodes: `grill_coals` (emissive `ember` mesh the engine may pulse) and `smoke_origin` on the Bratwurst stand; `slot_cabinet_l` and `slot_cabinet_r` (bottom cabinet shelves) on the Bücherstand.
6. Footprints and heights (origin at the footprint centre, front −Y):
   - Glühwein: 3.4 × 2.5 m, roof overhang 0.5 m at the front, 4.6 m tall.
   - Bratwurst: 3.9 × 2.5 m, plus a 0.8 m lean-to on the +X side; stovepipe 4.45 m.
   - Bier: 4.2 × 2.6 m, with pennants reaching 0.9 m past the walls; crest 4.3 m.
   - Bücher: 3.7 × 2.5 m, plus a 0.35 m bay on the −X side; 3.9 m tall.
   - Deco: 2.6–3.4 × 2.2 m.
   The prototype stalls were 4 × 2.8 m, so the layout spacing still holds.
7. The section stalls use two `light_` empties each (interior, and front/counter) and the deco stalls use one. Gooseneck sign lamps and the Bücher lantern are emissive (`bulb_warm` / `lamp_glass`), not lights.

## Open issues and what I would improve next

- **Wood close-ups:** the wood tile is a little smooth at counter distance. Next I would add stronger fibre and pore detail, a second wood tile (oak for counters), and worn, darkened counter edges from a per-stall edge-wear mask.
- **Bevel cost:** chamfers are real geometry, 44 triangles per plank. A baked edge-normal trim sheet could give the same highlight for 12 triangles.
- **The Bratwurst grill reads as a black box** in the render, because the coals sit under the grate. It needs a brighter ember bed, ash and heat staining.
- **Snow caps are separate meshes that cover the shingles completely.** The shingle detail shows only with snow off. A thinner, patchier cap would let some shingle rows show.
- **Bratwurst sign in the preview:** the render-only spotlights for its gooseneck lamps are too narrow, so the black board is lit in two hot circles. The word reads, but the lighting is uneven. The lamps themselves are just emissive bulbs in the glb.
- Running the stall scripts leaves `__pycache__/` folders in `blender/`. I deleted them, but `.gitignore` could list `__pycache__/`.
- **Deco stalls look bare in their previews** (no goods, by design). Their fascia signs are small at contact-sheet size.
- **Not yet checked in the browser.** I validated the files with the glTF validator but have not loaded them in the engineer's three.js scene. The lighting designer should check that the `COLOR_0` tints and the paint colours hold up under the real-time lights.
- **Glühwein text cost:** the Fraktur letters with bevel are about 2k triangles. `sign(..., text_bevel=0, resolution=1)` would cut that if the vendor needs the room.
