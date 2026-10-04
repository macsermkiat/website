# blender/lib: shared Blender helpers (`nmlib`)

Owner: carpenter. Other roles may import these modules and may add their own files as
`blender/lib/<role>_*.py`. The API below is meant to stay stable. New optional arguments
may be added, but existing names and defaults will not change without a note in the round notes.

Run everything with the team's bpy on the cloud machine (4 CPUs, no GPU; see "Where things run"
in `docs/BUILD.md`):
`NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python your_script.py`
`NM_DEVICE` (default `CPU`) and `NM_THREADS` (default 2, 0 = all cores) apply to every Cycles job the
library starts: kit bakes, AO bakes and preview renders (see `state.configure_cycles`). Iterate renders
at 960x540 and 32 samples; final review renders are 1280x720 and 48 samples. bpy may segfault at exit
after writing everything; that is harmless when the outputs exist. `optimize.mjs` loads the
gltf-transform libraries of the globally installed `@gltf-transform/cli` (`npm root -g`; set
`NPM_CONFIG_PREFIX` if your global npm lives elsewhere). The AO
post-process needs numpy, scipy and Pillow in the bpy environment (all present in the cloud venv).

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy                      # import bpy before mathutils
from nmlib import state, geo, mats, carpentry as cp, bake, export, render
from nmlib.geo import Part

state.reset(seed_value=7, lite_mode=False)   # empty file, Cycles per NM_DEVICE/NM_THREADS, seeded RNG, LOD
wood = Part("myprop_wood", "wood")            # one Part = one mesh object = one material
wood.box((0, 0, 0.5), (1.2, 0.14, 0.03), tint="honey")            # a plank, grain along X
cp.plank_wall(wood, -1, 1, 0.0, 2.0, axis='x', at=0.0, tint="grey")
objs = [wood.finish()]
export.empty("slot_counter", (0, -0.3, 1.05))
bake.bake_ao(objs, "myprop", res=1024)       # AO in UV map "AO" -> glTF occlusion (TEXCOORD_1)
export.export_glb("myprop", texture_size=1024) # -> site/public/models/myprop.glb (optimised)
```

## How materials work

The textured materials do not use one unique bake per asset. They use **tiling kit textures**:
procedural Blender shaders baked once into seamless tiles. The noise is sampled on a 4D torus,
so the tiles repeat without seams. The bakes are cached in `blender/out/kit/`. Each primitive
gets its own UV window into the tile, so every plank shows different grain. A per-primitive
tint in `COLOR_0` (the glTF vertex colour, which three.js multiplies into the base colour)
turns the one light, neutral wood into pine, honey, oak, dark, grey or soot boards. On a
3 m stall this gives about 10 px/cm, where a unique 1024 bake would give about 1.5 px/cm.

| key | kind | notes |
|---|---|---|
| `wood` | kit, 1 m tile, 1024 px | spruce: growth rings with hard latewood, fibre, resin pores, knots with ring deflection, cracks, dents, silvering |
| `oak` | kit, 1 m tile, 1024 px | ring-porous oak for counter tops: pore bands, ray flecks, cross-grain scratches, a few mug rings; `hut.OAK_TINT` holds multipliers |
| `paint` | kit atlas, 8 bands | chipped paint over wood. Bands (`geo.PAINT_BANDS`): `red gold blue white green cream black rauten`. `gold` is half metallic (0.5), like bronze-powder paint, so it still reads under warm lights without a bright environment map. `rauten` is the Bavarian blue-and-white lozenge pattern |
| `iron` | kit, 0.5 m tile, 512 px | forged iron, mid-grey: hammer dents, scattered rust blooms and runs, soot, pitting |
| `iron_matte` | kit variant of `iron` | sheet iron for hoods: its own lighter base colour (`kit_iron_matte_color`, the iron colour x1.7 in linear light, ~10 KB) and metal x0.35 as `metallicFactor`, so it reads grey under point lights without an environment map, plus a faint warm emissive copy of that colour (`emissiveFactor` 0.12/0.08/0.045) standing in for the bulbs and fire beside the hood, which no site light reaches. Vertex soot (`shade`) darkens only the base colour, so soot shows in lit areas while the stand-in keeps the shape readable. Roughness and normal maps are the iron kit's |
| `paint_glow` | kit variant of `paint` | the paint atlas (use `band=` as with `paint`) plus a faint warm emissive copy of it (`emissiveFactor` 0.13/0.09/0.07, emissive texture = the shared paint colour map, so no extra bytes). For outward trim that faces out and down under an eave (bargeboards, carved valances, gable boards): under the site's moonlight plain red paint there goes near-black |
| `paint_lit` | kit variant of `paint` | (round 4) a main sign board lit by its own gooseneck lamps: the paint atlas with a stronger warm emissive copy of it (`emissiveFactor` 0.55/0.44/0.32, same shared colour map, no extra bytes). A cream board glows and dark letters stay dark, so the sign reads from the site's home view. Used for the Glühwein and Bratwurst main signs. Pair it with `Hut.sign_lamps` so the glow has a visible source |
| `copper_old` | kit variant of `iron` | old copper sheet for small roofs and hoods: the iron kit's dents, streaks and pitting with a copper-brown colour (`kit_copper_old_color`, the iron colour x1.35 x (1.25, 0.66, 0.42)), metal x0.6. Use it instead of the flat `copper` on architecture |
| `rauten` | pattern, 0.26 m tile, 256 px | dedicated two-colour Bavarian lozenge texture (`mats.PATTERNS`, made with numpy, no bake): four big lozenges per repeat so the pattern survives mipmapping, a Bavarian blue (sRGB about 12/105/188; pattern version p2) and a warm white, and a faint, nearly neutral emissive copy of the pattern (`emissiveFactor` 0.22/0.20/0.17) standing in for the eave bulbs that hang beside the pennants. Embedded in the glb (6.4 KB as WebP in the decoded `stall_bier.glb`). Use `uv_off=` to place a lozenge |
| `snow bulb_warm bulb_cold wire glass fir brass copper ember ash ornament_red ornament_gold fabric_* lamp_glass bookcloth` | simple | flat PBR values (still multiplied by `COLOR_0`; `bookcloth` is a light neutral binding cloth meant to be coloured by `tint=`) |

**Emissive stand-ins.** `iron_matte`, `paint_glow`, `paint_lit` and `rauten` carry a faint emissive copy of their
colour because the browser's bulbs glow but light nothing (`mats.STANDIN_EMIT`). A Cycles preview has
that light, so call `mats.standin_emission(False)` before rendering (the stall pipeline and `deco.py`
do); the glb export keeps them on.

Metal is 0 wherever a kit's metal is a constant 0 (wood, oak); only gold paint (0.5) and iron are metallic.
Every kit material, kit variant and pattern gets baked AO (`bake.ao_targets`); in round 1 the variants
were skipped, which is why `iron_matte` shipped without an occlusion texture.
`mats.KIT_VERSION` is stamped next to the cached bakes, and any script that calls `mats.ensure_kit()`
rebakes the kit when the version changes. **After a version bump, re-export every asset that uses a
kit material**, because the glb files embed (or, for the deco kit, reference) copies of the kit maps.

Maps per kit: base colour (sRGB), roughness in G and metal in B, and a tangent normal map.
No lighting is baked into base colour. Ambient occlusion is baked per asset with
`bake.bake_ao` into a second UV map. The AO atlas is post-processed so it is safe in three.js:
tiny islands (rivets, letters, bulb sockets) get no texels and point at a light patch, empty texels
are filled from the nearest island (no black bleeding through mipmaps), and values are remapped to
`[bake.AO_FLOOR, 1]` (0.32) so no surface goes black under the site's lights. If the AO resolution equals the kit roughness texture's,
the Blender exporter packs both into one ORM image. Use a size no kit map has (kits are 1024,
iron 512; lite kit maps 512): the section stalls bake AO at 768 (lite 384) and the deco stalls
at 448 (lite 256), so every stall references the shared kit roughness maps.

Named tints (`geo.TINTS`): `pine honey oak dark walnut grey soot shingle white`, or any linear RGB tuple.

## Modules

### `state`
- `reset(seed_value=1, lite_mode=False)`: factory-empty file, Cycles set up by `configure_cycles`, seeds `state.rng`, sets the LOD.
- `configure_cycles(scene=None)`: device from `NM_DEVICE` (CPU, or METAL/CUDA/OPTIX/HIP/ONEAPI for the GPU) and threads from `NM_THREADS` (0 = all cores, default 2).
- `lite()`: True while building a `*.lite.glb`. The helpers then drop bevels, shingles become one strip per course, and spheres, text and garlands get fewer segments.
- `rng`: the only random stream the helpers use. Seed it for repeatable builds.
- `font(name)`: bundled OFL fonts: `fraktur` (UnifrakturMaguntia), `fraktur_bold` (UnifrakturCook), `fell_sc`, `fell_italic` (IM Fell English), `alegreya_sc` (Alegreya SC ExtraBold). The stall signs use `fraktur_bold`, `fell_italic` and `alegreya_sc`.
- Paths: `REPO`, `MODELS_DIR` (`site/public/models`), `OUT_DIR` (`blender/out`, gitignored), `KIT_DIR`.
- `export_collection()` / `env_collection()`: what is exported vs render-only.

### `geo.Part(name, mat, shade=None, smooth=False, tint=None, var=0.08, bevel=None)`
Accumulates primitives into one mesh with `UVMap`, `Col` and flat or smooth shading.
- `shade(p)` → factor or RGB, evaluated per vertex at its world position. Use it for grime near the ground or soot above a grill (see `stalls/hut.grime` and `stalls/bratwurst.soot_shade`).
- Every primitive accepts `tint=`, `var=` (random per-primitive brightness), `band=` (paint only), `grain=` (0/1/2: local axis the grain runs along, default: the longest) and `uv_off=`.
- `box(center, size, rot=(0,0,0), bevel=None, segs=1, bevel_segments=1, jitter=0, drop=None)`: a chamfered board or beam. The default bevel is 4 mm on kit materials, and it is off in lite. `segs` subdivides along the grain so vertex shading can vary along a long plank; `segs=(nx, ny, nz)` subdivides each local axis (the counter's wear grid). `drop=("-z",)` leaves out faces that are never seen (a shingle's underside).
- `mbox(M, size, ...)`: the same with any 4x4 matrix. `slab(p0, p1, width, thick, up=)` is a board from p0 to p1.
- `cyl(center, r1, r2, depth, seg, rot, caps)`, `sphere(center, r, seg, rings, scale, rot)`, `ico(...)`, `torus(center, R, r, seg, tseg, rot, arc)`, `tube(points, radius, tseg)`, `lathe([(r, z), ...], seg, M)`, `loft(rings, closed)`.
- `shape(outer, holes=[], depth, M, bevel=0)`: extrudes a 2D polygon with cut-outs (stars, hearts, scallops).
- `text(body, font_path, size, depth, M, resolution=2, bevel=None, max_width=None)`: 3D lettering with the outline simplified. Returns (width, height). A `\n` in `body` starts a second line (centred block). Set `part.flat_text = True` for painted lettering: each glyph is one front face `depth/2` in front of `M` (no sides or back, about a quarter of the triangles); lite builds always do this. `part.curve_simplify` (degrees, default 6) thins glyph outlines.
- `finish(collection=None)` → the Blender object, or None if empty. `tris` gives the running triangle count.
- Helpers: `star_polygon`, `circle_polygon`, `heart_polygon`, `catenary`, `look_rot`.

### `carpentry` (all sizes in metres, front = -Y)
- Walls: `plank_wall(part, a, b, z0, top, axis, at, pw, th, gap, lean, tint, band, bevel, skip)`, where `top` may be a function (gables). Also `lap_siding(...)` (overlapping horizontal boards), `floor_boards(...)` and `nails(part, pts, normal)`.
- Roofs: `Slope(eave, along, down, length, a0, a1)` describes one roof plane (right-handed basis, `point(a, s, n)`), and `gable_slopes(W, D, eave_z, ridge_z, ov_eave, ov_gable, ridge_axis)` returns the two planes of a gable. Covering and trim: `roof_deck`, `shingles(part, slope, sw, sh, st, expo, tint)`, `board_roof`, `barge_boards` and `fascia`.
- `snow_cap(part, slope, thick=0.05, lip=0.05, cover=1.0, ridge_clear=0.24, courses=None, butt_gap=0.024, base=0.03, ridges=None, ridge_cover=0.012, ridge_soft=0.05, drifts=0)`: thin snow with a lip curling over the eave and a wind-scoured band under the ridge (its lower edge wanders, so the top courses and the ridge show). Pass `courses=(expo, first_butt)` for a shingle roof: the snow then lies in one strip per course and sinks below each butt, so every shingle row shows as a dark line through the snow. `cover < 1` adds melted patches (off by default). Pass `ridges=` (the batten list `board_roof` returns) for a board roof: the snow drapes over each batten as one continuous soft ridge down the whole slope, so the battens read under the snow and never poke through as dashes. The snow edge sinks into the roof instead of ending in a wall. `drifts=n` adds n lumpy mounds (80 tris each, full builds only) slid down against the eave lip, so a long straight roof edge is not one ruled strip. Lite: one coarse blanket. Put it in a Part named `snow_<n>` (material `snow`). `Hut.build_snow()` passes the right values for shingle and board roofs.
- `valance(part, x0, x1, y, z_top, h, drop, n, style, holes, band, M=None)`: a carved eave board. Styles: `scallop point wave step straight`. Holes: `star circle heart`. Pass `M` to run it along a rake.
- `sign(board, letters, text, font, center, w, h, board_band, text_band, frame_band, board_shape, text_size, resolution, text_bevel)`: a painted board (`rect arch banner oval`) with raised letters facing -Y.
- `bulb_string(bulbs, wire, anchors, sag, spacing, bulb_r, seg=None, rings=None)`: fairy bulbs on a sagging wire (bulb detail 7x5 by default; lite caps it at 5x3 even when the caller asks for more). Use a Part named `bulbs_<n>` with material `bulb_warm` or `bulb_cold`.
- `fir_garland(fir, beads, a, b, sag, radius)`: fir rope with baubles. `beads` is `{"ornament_red": Part, "ornament_gold": Part}`.

### `bake`
- `bake_ao(objs, name, res=1024, samples=24, distance=0.6, ground=True, hide=[], margin_px=None, tiny_area=0.0006, floor=0.32)` adds UV map `AO` to every kit-material object and packs them into one layout (islands under `tiny_area` m² get no texels). It then bakes Cycles AO (with a temporary ground plane), post-processes it (see "How materials work") and wires the result into the `glTF Material Output` group, so the exporter writes `occlusionTexture` with `texCoord: 1`. Hide snow caps and bulbs from the bake. It prints island coverage and the mean before and after the remap.

### `export`
- `empty(name, loc, rot=(0,0,0), look_at=None)`: a named empty in the export collection. It raises an error if the name is already taken.
- `stall_markers(counter_top, counter_y, shelf_1, shelf_2, vendor, sign, front, cam_view, cam_target, lights)`: all the `slot_*`, `cam_*` and `light_<n>` empties from docs/BUILD.md.
- `export_glb(name, texture_size=1024, externalize=None)`: exports the Export collection to `blender/out/raw/<name>.glb` and runs `blender/lib/optimize.mjs` into `site/public/models/<name>.glb`. `externalize=(match(name), uri_for(name))` moves shared kit textures out of the glb (the deco kit uses it). Returns a report (bytes, triangles, nodes, images).

### `render`
- `night_scene()`: night world, moon, sky fill and trodden-snow ground. It is render-only and goes in the Env collection.
- `add_light(name, kind, loc, energy, color, size, rot, spot_size=None, spot_blend=None, size_y=None, target=None)` (`target` aims a spot/area light), `lights_at_markers(energy)` (a point light at each `light_*`), `camera(loc, target, lens, dof)`, `render(png, samples=48, res=(1280,720), jpeg=...)` on the `NM_DEVICE` device with OIDN, `contact_sheet(items, out_jpg)`.
- `import_glb(path, at="slot_counter", offset=(0,0,0), rotate=False)`: imports a shipped (meshopt) glb into the render-only Env collection at a named empty. `rotate=True` also applies the empty's rotation (round 3, for rotated slots such as the Bücherstand's `slot_cat_<key>`).
- Sign lamps in previews: aim a narrow spot (34-38 degrees, blend 0.35) from the lamp head at the upper half of the board, so the lower cone edge ends on the board; wide cones leave bright ovals on the roof snow below (round 2 judges).

### Stall helpers (`blender/stalls/hut.py`, `pipeline.py`)
- `Hut.build_roof(..., barge_part=None)`: painted bargeboards go into `barge_part` (e.g. a `paint_glow` Part) instead of the hut's paint Part.
- `Hut.build_counter(..., extra_shade=None)`: a shade function multiplied into the counter's edge wear (the Bratwurst scorch under its grill).
- `Hut.build_snow(**kw)`: passes `drifts=`, `cover=` and the rest to `snow_cap`.
- `pipeline.vendor_props([(name, slot), ...], rotate=False)`: imports the vendor's shipped prop glbs into a Cycles preview (render-only); `rotate=True` for rotated slots. Previews go to `review/round-$NM_ROUND/carpenter/` (default round 4).
- `stalls/buecher_sections.py` (plain Python, no bpy): the Bücherstand's six category sections (side racks and carts). `buecher.py` builds from it, and `python3 blender/stalls/buecher_sections.py` writes `blender/stalls/buecher_sections.json` for the vendor, so the json always matches the model.
  - Each section also has `cam_position` / `cam_target_position` (round 4): `buecher.py` exports them as the empties `cam_cat_<key>` (rotated to look at its target) and `cam_cat_<key>_target`, a close-up 1.75 m in front of the section at eye height. The two inner rack bays stand behind the carts, so their cameras swing 40° toward the lane.
  - `python3 blender/stalls/buecher_sections.py --check [file.glb ...]` is read-only: it compares the json with the module (in memory) and every `slot_cat_`, `cam_cat_` and `cam_cat_*_target` node of the glbs (default: both Bücherstand LODs) with the json, and exits 1 on any mismatch. Only the plain command (no `--check`) writes the json.

## Checking a stall in the browser

`node blender/stalls/web/shoot.mjs [--only stall_bier] [--ao both|on|off] [--lite] [--out dir]
[--props prop_wurst_counter@slot_counter] [--signspot] [--home] [--tag name]` loads a
glb from `site/public/models` under the lighting designer's `site/src/lighting` module (Vite dev
server on port `NM_SHOT_PORT`, default 4397, because the lighting designer's own tools use 4395; `three` from `site/node_modules`, so run `npm ci` in `site/` first) and saves a
screenshot framed like the Cycles preview, with and without the AO map. Set `PLAYWRIGHT_MODULE` to a
Playwright `index.mjs` if Playwright is not installed next to the script. On the cloud machine it
renders with SwiftShader (2-4 min per shot). `--props` attaches vendor glbs at their slots,
`--signspot` adds the proposed warm spot at `slot_sign`, and `--home` frames the stall from the
site's home camera where `site/src/layout.json` places it.

## Command-line tools (plain Node / Python, no bpy)

- `node blender/lib/optimize.mjs in.glb out.glb [--texture-size 1024]`. This is the web step. Use it instead of `gltf-transform optimize`: that CLI prunes every empty leaf node, which would delete `slot_*`, `light_*` and `cam_*`, and its palette/join passes rename or merge materials such as `bulb_warm`. This script runs dedup, weld, prune (keeping leaves), sparse, WebP at `--texture-size` and meshopt, and leaves the node and material names alone.
- `python3 blender/lib/glb_tools.py report file.glb ...` lists nodes, materials, images, triangles and size.
- `python3 blender/lib/glb_tools.py check file.glb ...` checks the stall node contract: `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `cam_view`, `cam_target`, `light_*`, `bulbs_*`, `snow_*` and a `bulb_warm`/`bulb_cold` material. For `stall_buecher*.glb` it also requires `slot_cat_<key>`, `sign_cat_<key>`, `cam_cat_<key>` and `cam_cat_<key>_target` for every key in `content/books/categories.json`.

## Stall scripts built on this

`blender/stalls/hut.py` is a parametric market hut (carcass, oak counter at exactly 1.05 m with a
worn front edge from `hut.counter_wear`, shelves, roof, bulbs, snow, markers). `blender/stalls/pipeline.py` runs full build → AO → export → lite
build → AO → export → Cycles preview. The four section stalls and `deco.py` show how to use them.
`Hut(..., lap_segs=N)` gives lap-siding boards N vertex columns across the stall width (full
build only), so a `shade` function such as the Bratwurst soot plume can vary along a board.

## Fonts

`blender/lib/fonts/` holds SIL Open Font License fonts from github.com/google/fonts
(UnifrakturMaguntia, UnifrakturCook, IM Fell English, Alegreya SC). See CREDITS.md.
