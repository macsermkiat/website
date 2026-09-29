# Architect, round 1: square, old town, tree, layout

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
- **Street edges:** the plaza has a gentle camber down to a three-row V gutter. Beyond it runs a crowned 7 m ring street of setts in rows, then a second gutter, a kerb of about 270 individual granite kerbstones (each slightly misaligned), and a sidewalk of larger warm setts that runs under the houses. Where the seven side streets leave the ring, the kerb stops and the street paving runs out between the houses. There are also 12 wet puddles.
- **Street lamps:** 19 cast-iron lamps, 12 round the plaza edge and 7 at the street corners. Each has a fluted shaft, a ladder bar, a hexagonal lantern with frosted glass (`bulbs_lamp_NN`, material `bulb_warm`) and an empty `light_lamp_NN` in the lantern.
- **String lights:** 18 timber string-light poles with iron caps and 31 swagged spans. The sag follows the span length, and each span carries warm bulbs on sockets (`bulbs_string_NN`, `bulb_warm`), criss-crossing the lanes as in the prototype. Each span also has a `light_string_NN` empty just below its lowest point (every second span in lite).
- **Furniture:** 8 cast-iron benches with timber slats (two by the tree), 4 bins and 28 bollards across the side-street mouths.
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
- **Asset names:** the file names match what the carpenter exports: `stall_gluehwein.glb`, `stall_bier.glb`, `stall_bratwurst.glb`, `stall_buecher.glb`, and `deco_<goods>.glb` including `deco_puffer.glb`. The ride files are assumed to be `bandstand.glb`, `riesenrad.glb` and `karussell.glb`. `site/src/layout.js` reads the file as it is.

## Triangles and file sizes (after optimisation)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 32,440 | 2.02 MB (1.20 MB of it textures) | 40k / 3 MB |
| square.lite.glb | 12,690 | 0.96 MB | ~⅓ (39%) |
| town.glb (all buildings and church) | 146,136 | 3.70 MB (0.54 MB textures, the rest geometry) | 150k / 5 MB |
| town.lite.glb | 39,901 | 1.25 MB | ~⅓ (27%) |
| tree.glb | 36,518 | 0.90 MB | no row in BUILD.md; I aimed for 40k / 1.5 MB |
| tree.lite.glb | 7,667 | 0.33 MB | ~⅓ (21%) |

Desktop total for these three is 6.6 MB of the 25 MB first-load target. The lite total is 2.5 MB of the 8 MB lite target.

Node checks on the final files:
- **square.glb:** 19 `light_lamp_*`, 31 `light_string_*`, 50 `bulbs_*` (19 lamps and 31 spans, all `bulb_warm`), `snow_ground` and `snow_props`.
- **square.lite.glb:** 12 lamps and 16 string empties.
- **town.glb:** `window_warm`, `bulb_warm`, `snow_roofs`, `bulbs_town_garlands` and `bulbs_town_lanterns`.
- **tree.glb:** `bulbs_tree`, `bulbs_star`, `snow_tree`, `snow_tree_fence`, `light_tree_0` and `light_tree_1`.

`gltf-transform inspect` reads all six files.

## Previews (Cycles, 2 threads, denoised; stalls and rides are plain stand-ins)

- `home_view.jpg`: the square and town from the home camera.
- `town_street.jpg`: a curve of houses on the ring street, with a side street opening.
- `town_church.jpg`: the Marktkirche and its tower.
- `tree.jpg`: the tree.
- `square_cobbles.jpg`: a low view of the fan cobbles, a granite band, the gutter, the kerb, lamps and bollards.

In the previews, each `light_` empty becomes a 45 W warm point light, and one broad warm light over the market stands in for the combined glow of the stalls (3.5 kW for the home view, 9 kW for the close views). There is also faint moonlight, and depth fog and bloom are added in the compositor. Snow is hidden.

## Things that break or stretch the contract

1. **The standard web step in BUILD.md destroys the node contract.** `gltf-transform optimize` with its defaults prunes every empty (`light_*`, `slot_*`, `cam_*`). It joins named meshes, and it palettises plain materials, which renames `bulb_warm` to `PaletteMaterial001`. I tested this on a small file. My scripts run optimize with `--join false --flatten false --prune false --palette false --instance false`, keeping meshopt, WebP and the size limit. The carpenter found the same problem and wrote `blender/lib/optimize.mjs`. BUILD.md should name one of these two routes.
2. **The town has no baked AO yet.** The contract asks for AO in the occlusion texture. The square ground has it, including the occlusion from the houses, but the town (146k triangles of mostly small boxes) does not. See next steps.
3. **Vertex colour on the ground.** `square.glb`'s ground carries `COLOR_0` (large-scale grime and wetness). three.js multiplies it into the base colour by default, which is what I intend. Please do not strip it.
4. **Many `light_` empties.** There are 19 lamp and 31 string-span empties in `square.glb` (12 and 16 in lite), plus 2 in the tree. The contract caps lights only for stalls. The lighting designer should choose which of these get real lights. The previews light only the lamps and the tree.
5. **No tree budget.** BUILD.md has no budget row for the tree. The numbers above are my own.
6. **Snow and stall floors.** Snow sits 3.5 cm above the paving, so stall floors and feet at y = 0 sink into it slightly when snow is on. The plaza's camber puts the paving 0–4 cm below y = 0 away from the centre, which is invisible under stall floors.

## Open issues and what I would do next

- **Town AO:** add a lightmap UV to the big wall and roof meshes only, and bake a 2048 AO (about 10 minutes with 2 threads). Small timbers and frames don't need it.
- **Roof gaps:** houses are rectangles on a ring, so thin wedge gaps open between neighbouring roofs toward the back. They cannot be seen from the square, but a Ferris wheel rider can see them. The fix is back-wall and roof fillers or a trapezoid footprint.
- **The engine's own ground:** the ground mesh's outer ring runs to r = 78 m. If the engine adds its own ground plane, it must sit below −0.15 m.
- **Puddles:** they are black-mirror discs (`puddle_water`). In Cycles, with a dark sky, they read darker than they will in three.js with an environment map. The lighting designer should judge them in the browser.
- **Detail for close views:** side-street houses beyond the corner house are simple. They could get timbering, and the ring could get a fountain, an advertising column (*Litfaßsäule*), parked bicycles and bay windows (*Erker*).
- **Lit windows:** the lit window fraction per house is random. A story pass could give specific windows content and tie their glow to the music.
- **Text lettering:** shop-sign lettering is flat, triangulated font geometry (about 6k triangles). If the town needs more budget, the lettering could move into a small shared texture.
- **Lite versions:** the lite town drops window frames. At phone distances that is fine, but a baked facade texture would look better.
