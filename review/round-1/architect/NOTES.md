# Architect, round 1 (pass 3): square, old town, tree, layout

Pass 3 answers the pass-2 judges. Every glb was rebuilt on the cloud machine from the current scripts, in this order: tree, town, square (its ground AO is baked with the new town in place), then the lite files. `check_clash.py` was rerun against the shipped files (the stalls rebuilt at 16:xx and 17:xx included). All six previews were re-rendered at 1280x720 and 48 samples. The stall, bandstand and ride stand-ins are gone: the previews now place the shipped glbs from `site/public/models`.

## What changed in pass 3

| Judges' point | Fix | Where to check |
|---|---|---|
| **1. Tree: the trunk shows through the upper crown from the home camera** (`tree.py`) | **Above 5 m:** the whorls are about 30% closer and carry two more branches each. The side fronds are pitched up and rolled 30–60° from horizontal. Every upper branch and tip carries outward-facing cross cards. Interwhorl shoots rise 30–60° from the leader between the whorls.<br>**From 2 m up:** part of the existing fronds are rolled 25–50° too, so the mid crown fills without extra triangles.<br>**Budget:** the doubled flat cards low down were thinned to pay for this, the baubles went from 8x5 to 7x4 segments, and the fairy bulbs are 3-sided. | `tree.jpg`, `home.jpg`, and `tree_home_crop.jpg` (a 110 mm crop from the home camera at [3, 9, 33]: no trunk shows above about 3 m). Browser: `browser_home.jpg` |
| **2. Spans 11, 12 and 19 through the bandstand roof** (`architect_plan.py`) | **Spans 11 and 12** run from pole 2 to poles 7 and 8 and pass 1.9 m from the bandstand's axis, where its roof stands 5.1–5.7 m high. Poles 7 and 8 behind the bandstand are now 9.2 m tall (and stouter), so those wires climb over the roof.<br>**Span 19** used to run 35 m from pole 9 to pole 12 across z = −3 and sagged into the roof. It now swags across the front lane from pole 0 to pole 4 (z = 4, 4 m in front of the bandstand).<br>**Poles 16 and 17** (the back row) moved another metre back, because the denser crown now reaches 4.3 m from the fir's axis at 5.5 m height.<br>**`check_clash.py` extended:** it decodes the shipped glbs and builds a BVH over every stall's, ride's and the bandstand's own triangles, placed from layout.json. Each wire and bulb vertex must stay 0.15 m from any of those surfaces, and no wire, bulb, pole, lamp or bench triangle may intersect one. It also reports each span's clearance over the bandstand. | `check_clash.py` prints OK. Clearances are in the clash section below |
| **3. Church nave, back and skyline roofs read as flat slabs** | **New slate map (`slate_courses`):** German scale slate (Schuppendeckung). Courses are about 17 cm, slates 18–34 cm wide with a curved cut on one lower corner, blue-grey to purple-grey with per-slate tone, gloss, and the odd rust or lichened slate. Soot and damp streaks run down the slope, and the exposed lower edges are lighter. It tiles at 2.4 m with a 1024 px map; the old map had 5 cm slates in near-black on a 1.2 m tile, which averaged to a flat slab. Normal strength is 8.<br>**Clay tiles:** normal strength goes from 5 to 8, and the per-tile colour spread from ±17% to ±30%.<br>**AO contrast:** the town AO lift drops from 0.3 to 0.2 (atlas) and 0.22 (per-vertex).<br>**Nave roof:** three slate-hung dormers on the square side give it scale. | `church.jpg`, `roofs.jpg` |
| **4. The home-view foreground doesn't read as worn and wet** (`square.py`) | **COLOR_0:** a 7 m damp/dry noise sits over the 27 m grime. The value range is 0.22–1.0 (it was 0.68–0.95). Gutters are darker (×0.72) and hollows darker still (×(1+12·depth)).<br>**Trodden walk and lane:** a walk (camera side to bandstand) and a lane (in front of the four section stalls) are 36% darker and 1.2 cm lower.<br>**Puddles:** three new settled hollows sit where the home camera looks, at three.js [3.2, 12.5], [−5.8, 8.2] and [−0.8, 17], each with a 0.95–1.25 m puddle.<br>**Wet films:** eight nearly clear films (alpha 0.28–0.4, roughness 0.05) lie along the walk and catch the lights as glossy streaks. | `home.jpg` foreground: patchy damp and dry paving, the pole and its bulbs reflected in the film, puddles with soft rims |
| **5. home.jpg uses stand-ins** | `preview.py` now decodes and places the shipped `stall_*.glb`, `deco_*.glb`, `bandstand.glb`, `ferris.glb` and `carousel.glb` from layout.json (16 assets). Their `light_` empties become point lights like mine. `STANDINS=1` restores the stand-ins. | `home.jpg`, `tree.jpg`, `roofs.jpg` |
| **6. The lite market's 8 MB target** | My lite files now total **2.21 MB** (they were 2.82).<br>**square.lite:** from 1.03 MB / 14.7k triangles to 0.67 MB / 12.8k. The lamps lose their lantern posts, ladder bar and finial neck, the pole caps lose a ring, and string bulbs are 1.35 m apart (were 1.0 m). All setts (street, gutter, sidewalk, bands) share one 256 px set, the kerb granite is 256 px without a normal map, and the bench and pole timber is 256 px colour only.<br>**town.lite:** from 1.41 MB to 1.20 MB. The timber, painted wood, yellow sandstone and plaster sets drop to 256 px, and the lite town now carries the shop-sign texture (2 triangles a sign).<br>**tree.lite:** from 0.38 MB to 0.33 MB (fence timber is 256 px colour only). | Table below and "For the market owner" |
| **7 and 9. NOTES said 32 `light_` empties in square.glb** | Corrected: square.glb has **25** (12 `light_lamp_NN` + 7 `light_lamp_street_NN` + 6 `light_string_NN`); square.lite has 15 (12 + 3). | Node checks below and contract item 5 |
| **8. Stained glass reads as a test pattern** | The chevron cell is gone. The church glass now has two tall regions in the window atlas (the bottom half of columns 1 and 3, each two cells high, 256x512 px), drawn in the lancet's own proportions as a leaded two-light window:<br>• pale amber and green grisaille quarries in an irregular, hand-cut lozenge lattice<br>• a jewel border to each light<br>• three medallions per light (roundels or quatrefoils, pieced by radial and ring leads) in muted ruby, sapphire, emerald and amber<br>• a painted sandstone tracery head with trefoils and a quatrefoil roundel<br>Its emission is about a third of a lit house window's. The lancets cycle through four looks (two variants, each mirrored), so no two neighbours match. The two transoms that made the barcode are gone; the stone mullion stays. | `church.jpg`, `home.jpg` |
| **10. Identical Schwibbogen cells side by side in shopfronts** | Each shop picks its display panes from six lit cells without repeats, and the second pane is mirrored. Every other window mirrors its cell at random, so neighbours that happen to share a cell still differ. The window atlas is now 1024 px (256 px cells). | `cobbles.jpg`, `street.jpg` |
| **11. town.glb at 146,973 of 150,000 triangles** | **Lettering:** shop-sign lettering is now one 1024 px texture atlas, `shop_signs`. It has a row per sign: dark green board, gilt letters with a cast shadow, raised in the normal map, metallic in the metal map, painted from the same two OFL fonts. Each sign's lettering is a single quad; gilt dropped from 9.6k to 3.3k triangles.<br>**End caps:** posts, rails, braces, parapet struts, mullions and transoms lost their end caps, which are hidden where they butt into another member.<br>**Result:** **133,979 triangles** (16k free for the Erker, fountain and Litfaßsäule), even with the three nave dormers added. | Table below |

## Triangles and file sizes (after optimisation, from `gltf-transform inspect`)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 39,038 | 2.18 MB | 40k / 3 MB |
| square.lite.glb | 12,798 | 0.67 MB | ~⅓ (33%) |
| town.glb (all buildings and church) | 133,979 | 4.41 MB | 150k / 5 MB |
| town.lite.glb | 32,261 | 1.20 MB | ~⅓ (24%) |
| tree.glb | 39,944 | 1.05 MB | no row in BUILD.md; I hold it to 40k / 1.5 MB |
| tree.lite.glb | 9,684 | 0.33 MB | ~⅓ (24%) |

Desktop total for these three: 7.64 MB of the 25 MB first-load target. Lite total: 2.21 MB of the 8 MB lite target.

**Square triangles by mesh:**

| Mesh | Triangles | Contents |
|---|---|---|
| street_iron | 11,590 | 19 lamps, bins, bollards, pole feet |
| ground | 11,378 | |
| bulbs | 5,408 | |
| string_wire | 3,168 | |
| curbs | 2,220 | |
| snow_ground | 1,818 | |
| snow_props | 1,636 | |
| puddles | 756 | 10 puddles and 8 wet films |
| plaza_bands | 368 | |
| poles_wood | 360 | |
| benches_wood | 336 | |

**Town triangles by mesh:**

| Mesh | Triangles |
|---|---|
| pw_frame | 31.4k |
| ti_brown | 16.8k |
| stone_yel | 16.6k |
| stone_red | 12.5k |
| snow_roofs | 9.9k |
| ti_black | 7.1k |
| pw_green | 4.6k |
| ti_ox | 3.9k |
| garland | 3.5k |
| gilt | 3.3k |
| bulbs_town_garlands | 2.6k |
| windows | 2.5k |

The house mix differs from pass 2: the new mirror flags draw from the seeded random stream, so the types and tints came out in a different order. The same no-repeat rule still holds.

**Tree triangles by mesh:**

| Mesh | Triangles |
|---|---|
| needles | 22.6k |
| baubles and caps | 8.2k |
| snow_tree | 2.8k |
| bulbs_tree | 2.8k |

## Node and material checks on the final files

- **square.glb:** 25 `light_` empties: `light_lamp_00`–`_11` (plaza edge), `light_lamp_street_00`–`_06` (corners) and `light_string_09/10/11/12/20/21`. 50 `bulbs_*` meshes (19 lamps and 31 spans), all `bulb_warm`. Snow nodes `snow_ground` and `snow_props`. 10 of 13 materials have AO; the three without are `bulb_warm`, `wire_black` and `puddle_water`.
- **square.lite.glb:** 15 `light_` empties (12 plaza lamps and `light_string_09/10/11`), 43 `bulbs_*`, the same snow nodes.
- **town.glb:** `window_warm` (one material for every pane, church glass included), `bulb_warm`, `bulbs_town_garlands`, `bulbs_town_lanterns`, `snow_roofs`, `snow_skyline`, `light_church_0/1` and the new `shop_signs`. 32 of 34 materials have AO; the two without are `window_warm` and `bulb_warm`.
- **town.lite.glb:** `window_warm`, `bulbs_town_lanterns`, `snow_roofs`, `light_church_0/1`, `shop_signs`.
- **tree.glb / tree.lite.glb:** `bulbs_tree`, `bulbs_star`, `snow_tree`, `snow_tree_fence`, `light_tree_0`, `light_tree_1`.
- **layout.json:** unchanged this pass: 4 section stalls, 3 landmarks, 9 deco stalls (each with `goods`), plus tree, square and town, all with `pos` and `rotY`, and `camera.home`. All 19 assets exist with their `.lite.glb`.

## Clash test (`blender/square/check_clash.py`, run on the shipped files)

`[clash] OK`. With the tree placed at [6.5, −15], rotY 0.3, and every stall and ride placed from layout.json:

- **Fir:** no wire, bulb or pole vertex lies within the fir's measured needle envelope (5.56 m at the base, 4.27 m at 5.5 m) plus 0.3 m. The two tree benches stand clear of the lowest boughs.
- **Footprints:** no pole, lamp, bench, bin or bollard stands inside a stall, ride or bandstand footprint. A plaza lamp that the new random draw put inside the Ferris wheel's footprint now steps round it.
- **Surfaces:** no string wire or bulb comes within 0.15 m of any stall, deco stall, ride or bandstand triangle, and no wire, bulb, pole, lamp or bench triangle intersects one.
- **Bandstand clearance** (to its mesh surface):

  | Mesh | Clearance |
  |---|---|
  | bulbs_string_12 | 0.93 m |
  | bulbs_string_11 | 0.94 m |
  | string_wire (all spans) | 0.98 m |
  | bulbs_string_09 | 2.61 m |
  | bulbs_string_10 | 2.62 m |

  All other spans stay more than 3 m from it. Span 19 no longer passes the bandstand.

## Previews (Cycles, CPU, 1280x720, 48 samples, denoised; the stalls and rides are the shipped glbs)

- **`home.jpg`:** the square and town from the home camera, with the real stalls, bandstand, Ferris wheel and carousel.
- **`tree_home_crop.jpg`:** a long-lens crop of the tree from the home camera position, to check the crown.
- **`street.jpg`:** a curve of ring houses with a side street opening.
- **`church.jpg`:** the Marktkirche with the new slate, dormers and leaded glass, floodlights on.
- **`tree.jpg`:** the tree from the lane behind the Bierstand.
- **`cobbles.jpg`:** a low view of the worn fan cobbles, a granite band, a puddle, the gutter, the kerb and a shopfront.
- **`roofs.jpg`:** the ring's roofs and the church from above the top of the Ferris wheel.
- **`browser_home.jpg`:** the real market in Chromium (software GL) through the site's dev server (`site/src/lighting/shoot-market.mjs`, `quality=full&snow=0`), with these glbs and the lighting designer's lights (10 real-time lights). The engine frames the home view a little wider than my camera. The tree's crown reads as solid fir with no trunk showing, and the church glass glows muted and well below the house windows.

The Cycles previews light the scene like this:
- Each lamp, tree and stall `light_` empty becomes a 45 W warm point light.
- The church empties become warm spots aimed up the tower.
- A broad warm light over the market stands in for the stalls' glow.
- There is faint moonlight.
- The compositor adds depth fog and bloom.
- Snow is hidden.

## How to rebuild (cloud machine)

```
/home/claude/tools/bpy-venv/bin/python blender/square/tree.py          # ~6 min; LITE=1 for the lite tree
/home/claude/tools/bpy-venv/bin/python blender/town/town.py            # ~12 min (2048 AO bake)
LITE=1 /home/claude/tools/bpy-venv/bin/python blender/town/town.py     # ~3 min
/home/claude/tools/bpy-venv/bin/python blender/square/square.py        # ~9 min, after the town (REUSE_AO=1 skips the ground bake)
LITE=1 /home/claude/tools/bpy-venv/bin/python blender/square/square.py
/home/claude/tools/bpy-venv/bin/python blender/square/check_clash.py   # tests the shipped files; exits 1 and lists offenders on a clash
/home/claude/tools/bpy-venv/bin/python blender/square/preview.py <home|street|church|tree|cobbles|roofs>
```

All renders and bakes honour `NM_DEVICE` and `NM_THREADS`. bpy segfaults at exit (code 139) after writing everything, which is expected. `preview.py` and `check_clash.py` decode other roles' glbs into `blender/square/out/decoded/` with `blender/lib/decode.mjs` whenever a shipped file is newer.

## Things that break or stretch the contract

1. **The standard web step in BUILD.md destroys the node contract.** `gltf-transform optimize` with its defaults does four things that break it:
   - it prunes empties
   - it joins named meshes
   - it palettises materials (renaming `bulb_warm`)
   - it simplifies geometry

   My scripts use `--join false --flatten false --prune false --palette false --instance false --simplify false`, with meshopt, WebP and the size limit. BUILD.md should name this flag set or `blender/lib/optimize.mjs`.
2. **No tree budget row in BUILD.md.** The tree holds to 40k / 1.5 MB (39,944 triangles, 1.05 MB).
3. **Vertex colour on the ground.** `square.glb`'s ground carries `COLOR_0` (large-scale grime, damp and the trodden walk). three.js multiplies it into the base colour, so please do not strip it. The puddles and wet films use `COLOR_0` alpha for their fading rims, so their material is alpha-blended.
4. **Occlusion on `TEXCOORD_1`.** Every AO texture uses the second UV set; the tiled material textures use the first. The town and tree AO images also hold a ramp strip that the small parts' UVs point into, so the image must not be resized unevenly or re-packed.
5. **Light empties.**
   - **Counts:** square.glb has **25** `light_` empties (12 `light_lamp_NN` + 7 `light_lamp_street_NN` + 6 `light_string_NN`), and square.lite has 15. There are 2 more in the tree and 2 at the church (29 in all from my files).
   - **Ranking:** the names are ranked so the lighting designer can take the first N (plaza lamps, then the corner lamps, then the string spans).
6. **Snow and stall floors.** Snow sits 3.5 cm above the paving. The plaza's relief puts the paving up to about 4 cm below y = 0 in the hollows (4.2 cm on the trodden walk). Neither shows under stall floors.
7. **The window atlas grew to 1024 px.** This is for the stained glass and the sharper panes, and costs about 30 KB. The church glass occupies UV v 0–0.5 in columns 1 and 3, so atlas cells 9, 11, 13 and 15 are no longer window cells.

## For the market owner: lite budget numbers

My lite files are now **2.21 MB** (square.lite 0.67, town.lite 1.20, tree.lite 0.33), which is 28% of the 8 MB lite target.

**What I cut this pass:** 256 px for every small-scale texture:
- square: setts, granite, timber
- town: timber, painted wood, yellow sandstone, plaster
- tree: fence timber

I also dropped normal maps on the kerb, bench, pole and fence timber, and cut the lamp and bulb geometry.

**What else can drop to 256 px in lite, with the measured WebP sizes at 512 px:**

| Texture | Now (512 px) | At 256 px (about) |
|---|---|---|
| town `roof_tiles_*` (colour, rough, normal) | 20 + 17 + 38 KB | ~20 KB |
| town `slate_*` | 14 + 24 + 30 KB | ~18 KB |
| square `cobble_fan_*` (colour, AO+rough, normal) | 56 + 73 + 76 KB | ~55 KB, but the cobbles fill the lite view, so I would keep them at 512 |
| tree `fir_frond` (512x256) | 61 KB | ~17 KB; the fronds would soften |

Dropping the roofs to 256 would save about 0.1 MB more. The town's remaining lite weight is geometry (about 0.8 MB, most of it 32-bit tiling UVs). UV quantisation would halve that, but it needs `KHR_texture_transform` support checked in the engine.

## Open issues and what I would do next

- **Puddles in the browser:** in Cycles the puddles and wet films read as dark, glossy water that reflects the poles and bulbs. From the home camera's height they mostly mirror the dark sky. In the browser they depend on the lighting designer's environment map.
- **Church roof at night:** the slate courses read up close (`church.jpg`) and from the Ferris wheel. From the home camera the nave roof is lit only by moonlight and the market glow, so it stays dark. A low light on the square-side roof, or snow (the `snow_roofs` layer), would bring it out.
- **Detail for close views (round 2):** a fountain, an advertising column (*Litfaßsäule*), bay windows (*Erker*) and bicycles. There is now 16k triangles of room in town.glb.
- **AO resolution:** the 2048 town AO bake is downsized to 1024 by the optimize step's `--texture-size 1024`. Keeping it at 2048 would cost about 0.4 MB.
- **Blender importer:** in my Cycles previews the real stalls use Blender's glTF importer. It may not show their `COLOR_0` tints exactly as three.js does, so judge the stalls' own look from the carpenter's previews.
