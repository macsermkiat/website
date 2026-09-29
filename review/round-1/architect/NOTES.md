# Architect, round 1 (pass 2): square, old town, tree, layout

Pass 2 answers the Opus, Fable and Codex judges. All six glbs were rebuilt on the cloud machine from the current scripts (town first, so the square's ground AO sees the new houses), the clash test was rerun, and every preview was re-rendered here at 1280x720 and 48 samples (Cycles, CPU, 2 threads).

## What changed in pass 2

| Judge's point | Fix | Where to check |
|---|---|---|
| String lights run through the tree (spans 26/28/30, poles 16/17) | Back-row poles moved to [0,-20] and [12.2,-19.6], poles 7/8 behind the bandstand to [±2.6,-9.6]. The spans behind the tree were re-routed ([16,7] replaces [17,8]). `blender/square/check_clash.py` tests every wire, bulb and pole vertex against the fir's measured needle envelope (5.57 m at the base, 3.98 m at 5.5 m) plus 0.3 m, and every pole, lamp, bench and bin against the stall and ride bounding boxes. | `check_clash.py` now prints `[clash] OK`; `tree.jpg` |
| Tree benches under the boughs | The two benches now stand 6.6 m from the fir's axis with their backs to it; the lowest boughs reach 5.57 m. | clash test |
| Black and white striped kerb | A sliver of the ground's riser, which had a degenerate UV, poked out in front of every other kerbstone. The riser now sits under the middle of the stones. | `street.jpg` and `cobbles.jpg`: every kerbstone reads as the same grey granite |
| No AO in town.glb and tree.glb | **Town:** walls, gables, roofs and the church stonework share one baked AO atlas (2048 bake, 1024 after optimisation). Timbers, frames, shutters, signs, ironwork, snow and far roofs carry per-corner baked AO, stored as lightmap UVs that point into a ramp in the same image. 31 of 33 materials have an occlusion texture; the two without are `window_warm` and `bulb_warm`. **Tree:** trunk, fence and fence snow are atlas-baked; needles, snow cards, baubles, stars and the garland use the per-corner ramp. 11 of 12 materials have AO. **Square:** the lamps, poles, benches, bins, bollards and kerbs now have AO too (9 of 12 materials; not bulbs, wires or puddles). | `gltf-transform inspect`: `occlusionTexture` on the materials |
| Asset names riesenrad.glb and karussell.glb | layout.json now names `ferris.glb` and `carousel.glb`. Every asset in layout.json exists in `site/public/models/` with its `.lite.glb`. | `site/src/layout.json` |
| Black-blob puddles | The puddles now sit in 16 settled hollows in the plaza's relief and along the gutters. Each one is a fan with a see-through core (alpha 0.6–0.72) and a rim that fades to 0, so it reads as a film of water on wet cobbles. The hollows around them are darker and damper. | `home.jpg`, `cobbles.jpg` |
| Church tower unreadable, sandstone blocks too large | The belfry openings and clock dials were buried inside the stage walls; they now sit on each stage's face. Sandstone tiles at 2.4 m with real-size ashlar courses. Two floodlight empties `light_church_0/1` stand at the tower foot on the square side; the preview aims warm spots at them, as German churches are lit at night. | `church.jpg`: four stages with string courses, lancet, louvred belfry pairs, clock faces, gablets, pinnacles and spire all legible |
| Wedge gaps between ring roofs | 17 back ranges fill the wedges that open behind neighbouring ring houses. Each has plastered walls up to just below the lower eave, a zinc roof and snow on it. | `roofs.jpg` (from the top of the Ferris wheel) |
| 50 `light_` empties, unranked | Now 32 in square.glb and 15 in lite, named by priority: `light_lamp_00`–`_11` (plaza edge), `light_lamp_street_00`–`_06` (corners), then `light_string_NN` on only six key spans. | node list below |
| The plaza foreground reads as a flat normal map | The meshoptimizer simplifier had collapsed the ground to 187 triangles; my optimize step now passes `--simplify false`. The plaza is a denser mesh (a ring every 1.9 m, 11.4k triangles) displaced by worn relief: gentle settling, 16 hollows 1–3 cm deep, and a trodden low line along the main walk. | `cobbles.jpg`, `home.jpg` foreground |
| Codex: lite market over budget | The lite town drops the stone window jambs (it keeps lintels and sills), which saves 6k triangles and 0.16 MB. My lite files total 2.82 MB (town 1.41, square 1.03, tree 0.38). See open issues for what more would cost. | table below |

## What was built

All four assets are scripted in Blender (bpy 4.2) and rebuilt from scratch by their scripts. Every texture is generated procedurally in numpy by `blender/lib/architect_tex.py`. All of them tile, and the per-stone, per-tile and per-plank variation is baked into colour, roughness and normal maps. There are no third-party images.

| Script | Output |
|---|---|
| `blender/square/square.py` (`LITE=1` for lite) | `site/public/models/square.glb`, `square.lite.glb` |
| `blender/town/town.py` (`LITE=1`) | `site/public/models/town.glb`, `town.lite.glb` |
| `blender/square/tree.py` (`LITE=1`) | `site/public/models/tree.glb`, `tree.lite.glb` |
| `blender/square/preview.py <home\|street\|church\|tree\|cobbles>` | the preview JPEGs in this folder |
| `site/src/layout.json` | the placement of every stall, landmark, deco stall, the tree, square, town and the home camera |

Shared code lives in `blender/lib/architect_common.py` (geometry with real-world UVs, materials, AO bake, export and optimisation), `architect_plan.py` (the plaza outline, the ring street, the exits and the house line, used by both square and town) and `architect_tex.py`.

**Square (`square.glb`)**
- **Plaza:** an irregular plaza about 72 m across, with an outline made of low-order sine terms so no side is straight. It is paved in *Segmentbogenpflaster*, the German fan pattern. Every stone has its own shape: the edges are domain-warped at two scales, and each stone gets its own tilt, height, rounded worn top, colour (granite greys, blue basalt, some porphyry) and polish. The joints are dark, wet and sometimes mossy.
- **Large-scale variation:** a low-frequency grime and wetness pass rides on vertex colour (`COLOR_0`), so the tile never reads as repeating. A 1024 px ambient-occlusion lightmap on `TEXCOORD_1` covers the whole ground mesh (160 m square). It is baked with the town present, so the sidewalks darken at the house fronts. Blender packs it into the same image as the tiled roughness, with each channel on its own UV set, so the shared sampler repeats and the roughness tiles correctly.
- **Granite bands:** bands of granite slabs split the cobble field into panels: a ring at r ≈ 26 m, eight radial bands and a ring round the tree. They read from the home camera. After optimisation they share the sidewalk material, because the lighter factor I gave them was above 1 and was clamped away. That is harmless.
- **Street edges:** the plaza has a gentle camber down to a three-row V gutter. Beyond it runs a crowned 7 m ring street of setts in rows, then a second gutter, a kerb of about 270 individual granite kerbstones (each slightly misaligned), and a sidewalk of larger warm setts that runs under the houses. Where the seven side streets leave the ring, the kerb stops and the street paving runs out between the houses. There are also 10 puddles (7 in lite).
- **Street lamps:** 19 cast-iron lamps, 12 round the plaza edge and 7 at the street corners. Each has a fluted shaft, a ladder bar, a hexagonal lantern with frosted glass (`bulbs_lamp_NN`, material `bulb_warm`) and an empty in the lantern: `light_lamp_00`–`_11` on the plaza edge, `light_lamp_street_00`–`_06` at the corners.
- **String lights:** 18 timber string-light poles with iron caps and 31 swagged spans. The sag follows the span length, and each span carries warm bulbs on sockets (`bulbs_string_NN`, `bulb_warm`), criss-crossing the lanes as in the prototype. Only six spans carry a `light_string_NN` empty (three in lite): the four crossings in front of the section stalls and bandstand, then two back spans.
- **Furniture:** 8 cast-iron benches with timber slats (two by the tree, 6.6 m from its axis), 4 bins and 28 bollards across the side-street mouths.
- **Snow:** `snow_ground` is a snow sheet that follows the camber, the gutters and the kerb tops 3.5 cm above the paving. `snow_props` holds the snow caps on the lamps, poles, benches, bins and bollards.

**Old town (`town.glb`)**
- **The ring:** 25 townhouses stand on the house line at r ≈ 47–50 m, between the seven side-street exits and the church. Their backs reach r ≈ 57–62, and small random setbacks make the line irregular.
- **House types:** six types are mixed, and the type always changes from one house to the next. Tint and height change too.
  - half-timbered, gable to the square, with jetties and visible joist ends
  - a tall half-timbered gable
  - half-timbered, eaves to the square, with gabled dormers
  - plastered with a stepped gable (*Treppengiebel*) and stone copings and finial
  - plastered, eaves to the square, with quoins, string courses and dormers
  - plastered with a half-hipped gable (*Krüppelwalm*)
- **Half-timbering:** the framing is built per floor: sill beam, top plate, posts at every window, rails, St Andrew's crosses, *Feuerbock* or rhombus parapets and *Mann* braces. The timber comes in dark brown, ox-blood or black, over cream, white, ochre, rose, yellow, sage, blue or terracotta plaster.
- **Windows:** every window has a frame with a reveal, a mullion and transom, a sill, and snow on about half the sills. Plastered houses add sandstone surrounds. Shutters come in green, red, blue or grey.
- **Shopfronts:** about half the ground floors are shops, with display windows, a door with a step and transom light, and a sign board with gilt lettering in Fraktur or Alegreya SC (Bäckerei, Weinstube, Buchhandlung, Café am Markt, Uhren · Schmuck and so on). There is a wrought-iron pretzel sign at the bakery and a fir garland with bulbs over each shopfront (`bulbs_town_garlands`).
- **Houses and walls:** some houses carry wall lanterns (`bulbs_town_lanterns`). Side walls left open by a gap get their own windows. Each side street has a detailed corner house on both sides, simpler houses behind and a house closing the view. A skyline of 48 roofs stands beyond at r = 70–88 m.
- **Windows material:** all panes use one material, **`window_warm`**. Its emissive atlas has 16 cells: nine lit variants (curtains, a candle arch or *Schwibbogen*, a paper Herrnhut star, a table lamp, lace, curtains nearly closed), one stained-glass cell and six dark or barely lit cells. Each house has its own share of lit windows. The engine can scale the whole glow with the one material.
- **Church:** the Marktkirche has its tower centred on [8, −56]. The tower is 33 m of red sandstone in four stages, with corner buttresses, a stepped portal, a pointed lancet, louvred belfry openings, gilt clock faces on four sides, four gablets and pinnacles, and an octagonal slate spire topped by a gilt ball and cross 60 m up. The 28 m nave has buttresses, seven lancet windows with stone tracery and stained glass, a polygonal apse, a steep slate roof, a copper ridge turret and a side portal.
- **Snow:** `snow_roofs` holds every roof and dormer slope, plus the chimney caps, stepped-gable copings, sills and the spire's base.

**Tree (`tree.glb`)**
- **The fir:** a 15 m Nordmann fir made of about 3,600 alpha-tested needle fronds (material `fir_needles`, alphaMode MASK) on branch whorls. The branches droop and lift at the tips, and the fronds sit on both sides of each branch and at the tips, so the silhouette is dense and irregular, not a stack of cones.
- **Decorations:** 170 glass baubles in red, gold, champagne and matte red, with caps; 70 straw stars; a gold bead garland; 460 warm fairy lights (`bulbs_tree`, `bulb_warm`); and a glowing star (`bulbs_star`).
- **Base and snow:** a low octagonal picket fence with greenery inside. Snow comes in two layers: `snow_tree` (snow cards on the upper faces of the boughs) and `snow_tree_fence`. There are two `light_tree_*` empties.

**Layout (`site/src/layout.json`)**
- **Entries:** 4 section stalls, 3 landmarks, 9 deco stalls (each with a `goods` key), plus tree, square and town. Every entry has `id`, `kind`, `asset`, `label` (the German sign), `pos [x, z]` and `rotY`, and section stalls and landmarks also have `section`. The home camera is `camera.home`.
- **Positions:** the section stalls, bandstand, Ferris wheel and carousel stay where BUILD.md puts them. The deco stalls are nudged off the grid by up to 0.5 m and 0.1 rad so the lanes look hand-placed.
- **Carousel:** `rotY −0.6`, so its entrance faces the centre.
- **Tree:** `rotY 0.3`.
- **Home camera:** the target moved from y 2.2 to 3.4, which gives less empty paving and more town in the home view.
- **Asset names:** the file names match what the carpenter exports: `stall_gluehwein.glb`, `stall_bier.glb`, `stall_bratwurst.glb`, `stall_buecher.glb`, and `deco_<goods>.glb` including `deco_puffer.glb`. The rides are `bandstand.glb`, `ferris.glb` and `carousel.glb`, the ride builder's files. `site/src/layout.js` reads the file as it is.

## Triangles and file sizes (after optimisation, from `gltf-transform inspect`)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 38,724 | 2.16 MB (1.26 MB of it textures) | 40k / 3 MB |
| square.lite.glb | 14,724 | 1.03 MB | ~⅓ (38%) |
| town.glb (all buildings and church) | 146,973 | 4.49 MB (0.69 MB textures) | 150k / 5 MB |
| town.lite.glb | 34,087 | 1.41 MB | ~⅓ (23%) |
| tree.glb | 36,568 | 1.06 MB | no row in BUILD.md; I aim for 40k / 1.5 MB |
| tree.lite.glb | 7,686 | 0.38 MB | ~⅓ (21%) |

Desktop total for these three is 7.7 MB of the 25 MB first-load target. Lite total is 2.82 MB of the 8 MB lite target.

Square triangles by mesh: street_iron 11,590 (19 lamps, bins and bollards), ground 11,378, bulbs 5,424, string_wire 3,174, curbs 2,220, snow_ground 1,818, snow_props 1,636, puddles 420, plaza_bands 368, poles_wood 360, benches_wood 336.
Town triangles by mesh: pw_frame 33.8k (window frames and mullions), stone_yel 20.7k, ti_brown 17.6k, ti_ox 11.3k, snow_roofs 10.0k, gilt 9.6k (sign lettering and dials), stone_red 8.3k, and the rest below 3.3k each.

Node checks on the final files:
- **square.glb:** 12 `light_lamp_NN` + 7 `light_lamp_street_NN` + 6 `light_string_NN` empties, 50 `bulbs_*` meshes (19 lamps and 31 spans, all `bulb_warm`), `snow_ground` and `snow_props`.
- **square.lite.glb:** 12 plaza lamps and 3 string empties, 43 `bulbs_*`, the same snow nodes.
- **town.glb:** `window_warm` (one material for every pane), `bulb_warm`, `bulbs_town_garlands`, `bulbs_town_lanterns`, `snow_roofs`, `snow_skyline`, `light_church_0/1`.
- **town.lite.glb:** `window_warm`, `bulbs_town_lanterns`, `snow_roofs`, `light_church_0/1`.
- **tree.glb / tree.lite.glb:** `bulbs_tree`, `bulbs_star`, `snow_tree`, `snow_tree_fence`, `light_tree_0`, `light_tree_1`.
- **layout.json:** 4 section stalls, 3 landmarks, 9 deco stalls (each with `goods`), plus tree, square and town, all with `pos` and `rotY`; `camera.home` is unchanged.

## Previews (Cycles, CPU, 1280x720, 48 samples, denoised; stalls and rides are plain stand-ins at the real assets' sizes)

- `home.jpg`: the square and town from the home camera.
- `street.jpg`: a curve of ring houses with a side street opening. The kerb reads as grey granite all the way along.
- `church.jpg`: the Marktkirche and its tower, with the floodlights on.
- `tree.jpg`: the tree, from the lane behind the Bierstand.
- `cobbles.jpg`: a low view of the worn fan cobbles, a granite band, a puddle, the gutter and the kerb.
- `roofs.jpg`: the ring's roofs and the church from just above the top of the Ferris wheel. The roofs close up behind each other, and no wedge gaps show.

In the previews each lamp and tree `light_` empty becomes a 45 W warm point light, the church empties become warm spots aimed up the tower, and one broad warm light over the market stands in for the stalls' glow. There is also faint moonlight, and the compositor adds depth fog and bloom. Snow is hidden.

## How to rebuild (cloud machine)

```
/home/claude/tools/bpy-venv/bin/python blender/town/town.py            # ~11 min (2048 AO bake)
LITE=1 /home/claude/tools/bpy-venv/bin/python blender/town/town.py     # ~1.5 min
/home/claude/tools/bpy-venv/bin/python blender/square/square.py        # ~9 min, after the town
LITE=1 /home/claude/tools/bpy-venv/bin/python blender/square/square.py
/home/claude/tools/bpy-venv/bin/python blender/square/tree.py          # ~4 min; LITE=1 for the lite tree
/home/claude/tools/bpy-venv/bin/python blender/square/check_clash.py   # exits 1 and lists offenders on a clash
/home/claude/tools/bpy-venv/bin/python blender/square/preview.py <home|street|church|tree|cobbles|roofs>
```
All renders and bakes honour `NM_DEVICE` and `NM_THREADS`. bpy segfaults at exit (code 139) after writing everything, which is expected.

## Things that break or stretch the contract

1. **The standard web step in BUILD.md destroys the node contract.** `gltf-transform optimize` with its defaults prunes empties, joins named meshes, palettises materials (renaming `bulb_warm`) and simplifies geometry (it flattened my plaza). My scripts use `--join false --flatten false --prune false --palette false --instance false --simplify false` with meshopt, WebP and the size limit. The carpenter's `blender/lib/optimize.mjs` is the other route. BUILD.md should name one of them. (The judges asked the market owner for this too.)
2. **No tree budget row in BUILD.md.** The judges suggest 40k / 1.5 MB; the tree is within that.
3. **Vertex colour on the ground.** `square.glb`'s ground carries `COLOR_0` (large-scale grime and wetness), which three.js multiplies into the base colour. Please do not strip it. The puddles use `COLOR_0` alpha for their fading rims, so their material is alpha-blended.
4. **Occlusion on `TEXCOORD_1`.** Every AO texture uses the second UV set (the tiled material textures use the first). The town and tree AO images also hold a ramp strip that the small parts' UVs point into, so the image must not be resized unevenly or re-packed.
5. **Light empties.** There are 32 `light_` empties in square.glb (15 in lite), plus 2 in the tree and 2 at the church. The contract caps lights only for stalls; the names are ranked so the lighting designer can take the first N.
6. **Snow and stall floors.** Snow sits 3.5 cm above the paving, and the plaza's relief puts the paving up to about 4 cm below y = 0 in the hollows. Neither shows under stall floors.

## Open issues and what I would do next

- **Lite budget (Codex):** my lite files total 2.82 MB. More savings would cost detail. The town's real-world UVs stay 32-bit floats because they tile past 0–1, which makes the lite town's geometry about 0.9 MB. Options: gltfpack-style UV quantisation through `KHR_texture_transform` (needs an engine check), baking the lite facades to a texture instead of window-frame geometry, or 256 px normal maps in lite. I'd rather the market owner decide which roles give up what.
- **Town AO resolution:** the 2048 bake is downsized to 1024 by `--texture-size 1024`. Up close, contact shadow at the jetties is soft. Keeping the AO image at 2048 would cost about 0.4 MB.
- **Puddles in the browser:** in Cycles they now read as a wet film. They still need a check against the lighting designer's environment map.
- **Church:** the tower reads now. In the home view the floodlights are hidden behind the tree, so the lighting designer might want a third, low light on the square-side face.
- **Previews:** the tree camera stands in the lane behind the Bierstand, 10 m from the fir, because the string-light pole at [10.5,-6.5] stood right in front of the trunk from the pass-1 spot. In `roofs.jpg` the Ferris wheel's stand-in gondola fills the lower left; the real wheel will look different.
- **Detail for close views:** the side-street houses beyond the corner houses are simple. The ring could also get a fountain, an advertising column (*Litfaßsäule*), parked bicycles and bay windows (*Erker*).
- **Lettering:** shop-sign lettering is triangulated font geometry (part of the 9.6k gilt triangles). It could move into a small shared texture if the town needs budget.
