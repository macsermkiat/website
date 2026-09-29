# blender/lib: shared Blender helpers (`nmlib`)

Owner: carpenter. Other roles may import these modules and may add their own files as
`blender/lib/<role>_*.py`. The API below is meant to stay stable. New optional arguments
may be added, but existing names and defaults will not change without a note in the round notes.

Run everything with the team's bpy: `/home/claude/tools/bpy-venv/bin/python your_script.py`.

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy                      # import bpy before mathutils
from nmlib import state, geo, mats, carpentry as cp, bake, export, render
from nmlib.geo import Part

state.reset(seed_value=7, lite_mode=False)   # empty file, Cycles 2 threads, seeded RNG, LOD
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
| `wood` | kit, 1 m tile, 1024 px | spruce: growth rings, fibre, knots with ring deflection, cracks, dents, silvering |
| `paint` | kit atlas, 8 bands | chipped paint over wood. Bands (`geo.PAINT_BANDS`): `red gold blue white green cream black rauten`. `gold` is metallic. `rauten` is the Bavarian blue-and-white lozenge pattern |
| `iron` | kit, 0.5 m tile, 512 px | forged iron with rust streaks and soot |
| `snow bulb_warm bulb_cold wire glass fir brass copper ember ornament_red ornament_gold fabric_* lamp_glass` | simple | flat PBR values (still multiplied by `COLOR_0`) |

Maps per kit: base colour (sRGB), roughness in G and metal in B, and a tangent normal map.
No lighting is baked into base colour. Ambient occlusion is baked per asset with
`bake.bake_ao` into a second UV map. If the AO resolution equals the kit roughness texture's,
the Blender exporter packs both into one ORM image. Use a different size (the deco kit uses
512) to keep the kit roughness texture shareable.

Named tints (`geo.TINTS`): `pine honey oak dark walnut grey soot shingle white`, or any linear RGB tuple.

## Modules

### `state`
- `reset(seed_value=1, lite_mode=False)`: factory-empty file, Cycles on CPU with 2 threads, seeds `state.rng`, sets the LOD.
- `lite()`: True while building a `*.lite.glb`. The helpers then drop bevels, shingles become one strip per course, and spheres, text and garlands get fewer segments.
- `rng`: the only random stream the helpers use. Seed it for repeatable builds.
- `font(name)`: bundled OFL fonts: `fraktur` (UnifrakturMaguntia), `fraktur_bold` (UnifrakturCook), `fell_sc`, `fell_italic` (IM Fell English), `alegreya_sc` (Alegreya SC ExtraBold).
- Paths: `REPO`, `MODELS_DIR` (`site/public/models`), `OUT_DIR` (`blender/out`, gitignored), `KIT_DIR`.
- `export_collection()` / `env_collection()`: what is exported vs render-only.

### `geo.Part(name, mat, shade=None, smooth=False, tint=None, var=0.08, bevel=None)`
Accumulates primitives into one mesh with `UVMap`, `Col` and flat or smooth shading.
- `shade(p)` → factor or RGB, evaluated per vertex at its world position. Use it for grime near the ground or soot above a grill (see `stalls/hut.grime` and `stalls/bratwurst.soot_shade`).
- Every primitive accepts `tint=`, `var=` (random per-primitive brightness), `band=` (paint only), `grain=` (0/1/2: local axis the grain runs along, default: the longest) and `uv_off=`.
- `box(center, size, rot=(0,0,0), bevel=None, segs=1, bevel_segments=1, jitter=0)`: a chamfered board or beam. The default bevel is 4 mm on kit materials, and it is off in lite. `segs` subdivides along the grain so vertex shading can vary along a long plank.
- `mbox(M, size, ...)`: the same with any 4x4 matrix. `slab(p0, p1, width, thick, up=)` is a board from p0 to p1.
- `cyl(center, r1, r2, depth, seg, rot, caps)`, `sphere(center, r, seg, rings, scale, rot)`, `ico(...)`, `torus(center, R, r, seg, tseg, rot, arc)`, `tube(points, radius, tseg)`, `lathe([(r, z), ...], seg, M)`, `loft(rings, closed)`.
- `shape(outer, holes=[], depth, M, bevel=0)`: extrudes a 2D polygon with cut-outs (stars, hearts, scallops).
- `text(body, font_path, size, depth, M, resolution=2, bevel=None, max_width=None)`: 3D lettering with the outline simplified. Returns (width, height).
- `finish(collection=None)` → the Blender object, or None if empty. `tris` gives the running triangle count.
- Helpers: `star_polygon`, `circle_polygon`, `heart_polygon`, `catenary`, `look_rot`.

### `carpentry` (all sizes in metres, front = -Y)
- Walls: `plank_wall(part, a, b, z0, top, axis, at, pw, th, gap, lean, tint, band, bevel, skip)`, where `top` may be a function (gables). Also `lap_siding(...)` (overlapping horizontal boards), `floor_boards(...)` and `nails(part, pts, normal)`.
- Roofs: `Slope(eave, along, down, length, a0, a1)` describes one roof plane (right-handed basis, `point(a, s, n)`), and `gable_slopes(W, D, eave_z, ridge_z, ov_eave, ov_gable, ridge_axis)` returns the two planes of a gable. Covering and trim: `roof_deck`, `shingles(part, slope, sw, sh, st, expo, tint)`, `board_roof`, `barge_boards` and `fascia`.
- `snow_cap(part, slope, thick, lip)`: a lumpy snow blanket with a lip curling over the eave. Put it in a Part named `snow_<n>` (material `snow`).
- `valance(part, x0, x1, y, z_top, h, drop, n, style, holes, band, M=None)`: a carved eave board. Styles: `scallop point wave step straight`. Holes: `star circle heart`. Pass `M` to run it along a rake.
- `sign(board, letters, text, font, center, w, h, board_band, text_band, frame_band, board_shape, text_size, resolution, text_bevel)`: a painted board (`rect arch banner oval`) with raised letters facing -Y.
- `bulb_string(bulbs, wire, anchors, sag, spacing, bulb_r)`: fairy bulbs on a sagging wire. Use a Part named `bulbs_<n>` with material `bulb_warm` or `bulb_cold`.
- `fir_garland(fir, beads, a, b, sag, radius)`: fir rope with baubles. `beads` is `{"ornament_red": Part, "ornament_gold": Part}`.

### `bake`
- `bake_ao(objs, name, res=1024, samples=24, distance=0.5, ground=True, hide=[])` adds UV map `AO` to every kit-material object and packs them into one layout. It then bakes Cycles AO (with a temporary ground plane) and wires the result into the `glTF Material Output` group, so the exporter writes `occlusionTexture` with `texCoord: 1`. Hide snow caps and bulbs from the bake.

### `export`
- `empty(name, loc, rot=(0,0,0), look_at=None)`: a named empty in the export collection. It raises an error if the name is already taken.
- `stall_markers(counter_top, counter_y, shelf_1, shelf_2, vendor, sign, front, cam_view, cam_target, lights)`: all the `slot_*`, `cam_*` and `light_<n>` empties from docs/BUILD.md.
- `export_glb(name, texture_size=1024, externalize=None)`: exports the Export collection to `blender/out/raw/<name>.glb` and runs `blender/lib/optimize.mjs` into `site/public/models/<name>.glb`. `externalize=(match(name), uri_for(name))` moves shared kit textures out of the glb (the deco kit uses it). Returns a report (bytes, triangles, nodes, images).

### `render`
- `night_scene()`: night world, moon, sky fill and trodden-snow ground. It is render-only and goes in the Env collection.
- `add_light(...)`, `lights_at_markers(energy)` (a point light at each `light_*`), `camera(loc, target, lens, dof)`, `render(png, samples=48, res=(1280,720), jpeg=...)` with 2 threads and OIDN, `contact_sheet(items, out_jpg)`.

## Command-line tools (plain Node / Python, no bpy)

- `node blender/lib/optimize.mjs in.glb out.glb [--texture-size 1024]`. This is the web step. Use it instead of `gltf-transform optimize`: that CLI prunes every empty leaf node, which would delete `slot_*`, `light_*` and `cam_*`, and its palette/join passes rename or merge materials such as `bulb_warm`. This script runs dedup, weld, prune (keeping leaves), sparse, WebP at `--texture-size` and meshopt, and leaves the node and material names alone.
- `python3 blender/lib/glb_tools.py report file.glb ...` lists nodes, materials, images, triangles and size.
- `python3 blender/lib/glb_tools.py check file.glb ...` checks the stall node contract: `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `cam_view`, `cam_target`, `light_*`, `bulbs_*`, `snow_*` and a `bulb_warm`/`bulb_cold` material.

## Stall scripts built on this

`blender/stalls/hut.py` is a parametric market hut (carcass, counter at exactly 1.05 m, shelves,
roof, bulbs, snow, markers). `blender/stalls/pipeline.py` runs full build → AO → export → lite
build → AO → export → Cycles preview. The four section stalls and `deco.py` show how to use them.

## Fonts

`blender/lib/fonts/` holds SIL Open Font License fonts from github.com/google/fonts
(UnifrakturMaguntia, UnifrakturCook, IM Fell English, Alegreya SC). See CREDITS.md.
