# Ride builder: round 1 notes

## What was built

All scripts are in `blender/rides/`. They use the carpenter's `nmlib` for the wood and paint kits, AO baking and export. The web step is `blender/lib/optimize.mjs`, which keeps empties and material names intact.

- `rcommon.py` holds the shared pieces:
  - **`rsteel`**, a new tiling kit texture of painted steel: orange-peel paint and roller marks, grime along each member, rust bleeding round chips, and chips down to red-oxide primer. It is a 0.5 m tile at 512 px, tinted by `COLOR_0` like the other kits. It is added at import time without editing any carpenter file.
  - Simple materials for the instruments and trim (chrome, mirror, enamel, gilt, ebony, ivory, bronze, lacquered brass, drum head, felt, leather, black metal, paper, strings).
  - Rod, sweep and pipe helpers.
  - Pivot and parenting helpers that bake a mesh's offset so its origin sits on the node pivot.
  - The full → AO → optimise → lite → Cycles preview pipeline.
- `ferris.py` builds **ferris.glb**, the Riesenrad, 26 m tall:
  - The wheel has twin rims, each an outer and an inner ring joined by a zig-zag truss. Each side has 16 main spokes and 32 crossing tension rods to a hub drum with flanges, bolt heads and a gilt 16-point sunburst.
  - The two rims are tied at each gondola axle with X-braces.
  - It stands on two lattice A-frames (four box-truss legs with lacing) on timber cribbing, with cross ties and back stays.
  - At the base are a plank boarding deck with steps and red rails, an arched "Riesenrad" Fraktur sign on gilt-capped posts, and a "Kasse" ticket booth with a green pyramid roof.
  - There are about 850 bulbs on the rims, the spokes (the star you see from the square), the hub, the sign and the booth.
  - The 16 enclosed octagonal gondolas come in four colours. Each has an ogee roof with a gilt finial, a hanger yoke, cream window posts with glass, gilt bands, a door with a handle, gilt stars, a plank floor, two facing benches, a ceiling lamp and eight eave bulbs.
- `carousel.py` builds **carousel.glb**, the Karussell, 12.6 m across the rail. It is a two-tier galloper:
  - A radial plank platform with a painted skirt and brass nosing.
  - 12 lofted horses in the jumper pose on brass barley-twist poles, six outer and six inner, in six coats: white, dapple grey, cream, chestnut, black and palomino. Each horse has a carved mane and tail (gilt on some), ears, eyes, a saddle cloth with gilt edging, saddle, cantle and pommel, stirrups, bridle, reins and a jewelled breast collar.
  - Two green chariot benches.
  - A centre column with arched mirrors and painted panels between gilt pilasters, plus sweeps and a boarded ceiling.
  - A 16-panel red rounding board with oval mirrors in gilt frames, "Karussell" in gilt Fraktur on the front and back panels, gilt stars and scrolls, shell cresting, a scalloped valance, pilasters and two rows of bulbs.
  - A red-and-cream striped canopy with fabric droop, a scalloped fabric edge and bulbs on gilt ribs. The second tier is a mirrored drum with its own striped roof, a gilt finial and a red pennant.
  - Static parts: a plank step ring, a stone kerb and a green iron rail with scroll loops, an entrance and two gate lamps.
- `bandstand.py` builds **bandstand.glb**, the Musikpavillon. It is an octagon 7.4 m across:
  - The plinth is painted, with white diamond lattice panels. The plank deck sits at 0.95 m, with five front steps and iron hand rails.
  - Eight cast-iron columns with flared capitals and gilt rings carry cream fretwork spandrels with round cut-outs. Iron railings with ring motifs run on seven sides.
  - Above them are a red frieze, a scalloped valance with round holes and a gilt lyre over the steps.
  - The ceiling is boarded and radial. The bell roof has red and cream stripes, gilt hip ribs with bulbs and a louvred lantern with a gilt finial and a lyre vane.
  - Fir garlands with baubles and red bows hang across the three front bays.
- `instruments.py` builds four glbs, each with a root node `instr_<name>`:
  - **instr_sax**: a tenor sax as held by a standing player. It is one continuous conical tube for body, bow and bell, with a rolled bell rim. It has about 16 key cups with pads, left- and right-hand stacks with pearl touches, palm keys, key rods on posts, low C/E♭ and low B/B♭ cups with wire guards, and a thumb rest, thumb hook and strap ring. The neck has an octave key, cork, ebonite mouthpiece, ligature and reed. The `act_sax` pivot is at the strap ring.
  - **instr_piano**: an upright piano in walnut with the full 88 keys (52 white, 36 black in the right pattern), an open fallboard, and moulded panels on the upper and lower fronts. The music desk holds sheet music, and two brass candle sconces hold lit candles (the flames use the `bulb_warm` material). It also has turned legs on toe blocks, three brass pedals and a bench with a red cushion.
  - **instr_bass**: a double bass in playing position. The body is lofted with an arched top and purfling. It has two f-holes (an S slot with round eyes), a maple bridge with heart and kidney cut-outs, an ebony tailpiece with a tail gut, four strings (tailpiece → bridge → nut → pegbox), an ebony fingerboard, an ivory nut, a pegbox with a scroll, brass machines, and an endpin. The `act_bass` pivot is at the endpin. A black floor stand beside it holds the French bow (stick, frog, hair) in its bow cup.
  - **instr_drums**: a small jazz kit:
    - an 18" kick with wooden hoops, spurs, pedal and beater, and a red front head with a gilt star;
    - a 14" snare on a stand, a 12" rack tom on the kick and a 14" floor tom on legs;
    - shells in the wood kit tinted mahogany, with chrome hoops, lugs and tension rods;
    - a 14" hi-hat with pedal and a 20" ride on a boom, both lathed in bronze;
    - a throne, and a pair of wire brushes resting on the snare (`act_brush_l` and `act_brush_r` pivot at the handle ends).

**Previews** in this folder are Cycles renders at 1280x720, 48 samples, 2 threads and OIDN:
- `ferris_preview.jpg`, `carousel_preview.jpg` and `bandstand_preview.jpg` are one night render each.
- `bandstand_stage.jpg` is a close view of the stage with the four instruments at their slots (40 samples).
- `instruments_contact_sheet.jpg` has four close-ups (960x540, 32 samples).

Snow caps are hidden in the previews so the roofs show. The market light strings in the Ferris preview are render-only. The sax in the bandstand renders stands on a render-only stand, because no player is holding it.

## Node contract

All nodes follow the prefixes in docs/BUILD.md. Front faces -Y in Blender, which is +Z in three.js. Every origin is on the ground at the footprint centre.

| File | Nodes |
|---|---|
| ferris | `rot_wheel` at the axle, 14.55 m up. It spins about three.js local Z, and the engine's name hint gives `z`. It has 16 child empties `gondola_0..15`, each **at its hanging point** on the gondola axle, 11.2 m from the hub. `gondola_0` hangs at the bottom, level with the deck. Each gondola's meshes are children with the pivot as origin. `gondola_seat_0` sits inside `gondola_0` at a seated eye height. Also `bulbs_wheel`, `bulbs_g0..15`, `bulbs_base`, `snow_g0..15`, `snow_base`, `light_0` (deck), `light_1` (booth), `cam_view` and `cam_target`. |
| carousel | `rot_platform` at the origin, spinning about three.js Y. It carries everything that turns: the platform, poles, column, rounding board, canopy and upper tier, plus `bulbs_carousel`, `snow_canopy` and 12 empties `horse_0..11`. Each horse is its own node at mid-travel, 1.30 m, with its pole staying on the platform, so the engine's ±0.2 m bob slides the horse along the pole. `horse_seat_2` is inside `horse_2` at rider eye height. Also `bulbs_gate`, `light_0/1`, `cam_view` and `cam_target`. |
| bandstand | `slot_sax`, `slot_piano`, `slot_bass` and `slot_drums` sit on the deck at z = 0.95. Also `light_0/1` (stage wash under the front eave), `bulbs_bandstand`, `snow_roof`, `cam_view` and `cam_target`. |
| instr_* | Root `instr_<name>` at the player's floor position. The player faces -Y (three.js +Z). Also `act_sax`, `act_bass`, `act_brush_l` and `act_brush_r`. |

**Slots and instruments:** place each `instr_<name>.glb` with the matching `slot_<name>`'s world transform (position and yaw). The slot's local three.js +Z is the way the player faces, which is the same convention as an asset's front. The organizer's musicians can use the same transform.

| Slot | Blender xy on the deck | Facing |
|---|---|---|
| sax | (0.9, -1.0) | toward the audience, slightly inward |
| piano | (-2.05, 0.35) | toward the left side, with the upright's back to the railing and the pianist in profile to the square |
| bass | (-0.55, 1.35) | front |
| drums | (1.45, 1.35) | front-left |

These are close to the engineer's `DEFAULT_PLAYERS` in `site/src/actions/band.js`.

`gltf-transform validate` reports no errors for any of the 14 files. The warnings are the same as the carpenter's: runtime-generated tangents, empty marker nodes, and the unvalidated meshopt extension.

## Triangles and file sizes (after `blender/lib/optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size | Budget |
|---|---|---|---|---|---|
| ferris | 63,511 | 1.66 MB | 22,917 | 0.69 MB | 80k / 3 MB |
| carousel | 78,678 | 1.65 MB | 27,288 | 0.65 MB | 80k / 3 MB |
| bandstand | 30,690 | 1.17 MB | 10,446 | 0.41 MB | |
| instr_sax | 4,358 | 0.05 MB | 1,028 | 0.02 MB | |
| instr_piano | 3,536 | 0.16 MB | 1,244 | 0.06 MB | |
| instr_bass | 2,810 | 0.13 MB | 1,734 | 0.07 MB | |
| instr_drums | 6,664 | 0.16 MB | 3,028 | 0.08 MB | |
| **bandstand + instruments** | **48,058** | **1.67 MB** | **17,480** | **0.64 MB** | 50k / 2 MB |

- Lite versions use 512 px textures (256 px for the instruments), no bevels, fewer segments, octahedron bulbs and simpler horses and gondolas. They have 34–36 % of the full triangles for the three landmarks and 36 % for the bandstand with instruments.
- Desktop first-load share for the rides is about 5.0 MB (lite about 2.0 MB).
- Rebuild commands, one at a time (the build and AO bake take about 1.5 min for the wheel):
  - `/home/claude/tools/bpy-venv/bin/python blender/rides/<ferris|carousel|bandstand>.py`
  - `.../instruments.py [--only sax,drums]`
  - Flags: `--no-render`, `--no-lite`, `--samples N`, `--res WxH`, and `--cam x,y,z,tx,ty,tz,lens` for a debug camera.
  - Build the instruments before the bandstand preview (the bandstand preview builds them from the same code).
  - bpy sometimes segfaults at interpreter exit after all files are written. This is harmless, and the carpenter reports the same.

## Contract notes for other roles

1. **File names:** the task names the files `ferris.glb` and `carousel.glb`, but `site/src/layout.json` (architect) lists `riesenrad.glb` and `karussell.glb`. The engine falls back to its key search (`ferris`, `carousel`) and finds my files, with a "not found" note. The architect could change the two `asset` fields to match.
2. **Ride seats:** `rides.js` currently picks the seat from bounding boxes. The engineer can switch it to `gondola_seat_0` and `horse_seat_2`, which are in place.
3. **Carousel direction:** the horses and chariots face **clockwise travel seen from above**, which is the engine's default `rot_platform` speed (−0.32). If the speed is made positive, the horses ride backwards.
4. **Instruments are not placed by the engine yet.** `band.js` looks for `act_<player>` in the bandstand model. My slots are `slot_*` as the brief asks. The sax is modelled in the held pose, so it floats until the organizer's sax player stands at the slot, and the engine may want to hide it when no player is shown.
5. `rsteel` kit images are cached in `blender/out/kit/kit_rsteel_*` and rebake automatically if the carpenter bumps `KIT_VERSION`. No carpenter file was changed. A few extra material names ship: `rsteel`, `enamel`, `gilt`, `mirror`, `chrome`, `saxbrass`, `bronze`, `drumhead`, `ebony`, `ivory`, `felt`, `leather`, `blackmetal`, `paper`, `strings`, `hole` and `canvas`. The lighting designer may want to tune mirror and chrome reflections against the environment map.

## Open issues and what I would improve next

- **Not yet checked in the browser.** I validated the files and checked the node hierarchy (16 gondolas under `rot_wheel`, 12 horses under `rot_platform`, both seats in place). I have not watched the spin and bob in the engineer's scene.
- **Mirrors** on the rounding board read as dark ovals in Cycles, because they reflect the night sky. In three.js they depend on the environment map. Next I would try a warm, slightly rough mirror, or bevelled mirror facets that catch the bulbs.
- **The Ferris hub sunburst** reads as a red disc from the square. It needs its own light, or bulbs on the star rays.
- **Horse carving** is lofted and smooth: there is no muscle definition, open mouth or carved teeth, and the manes are rows of locks. The next pass would be a sculpted master horse shared by the 12 nodes with per-horse paint, which would also free about 15k triangles.
- **The saddle cloth** is an ellipsoid round the barrel, so its lower edge is soft rather than a cut fabric edge.
- **The Riesenrad booth** is a simple plank box. The deck has no queue rails or ticket window detail, and there are no people.
- **Gondola interiors** have benches and a lamp only; there are no cushions or door hinges.
- **The fir garland tufts** on the bandstand read a little like holly leaves up close; they come from the carpenter's `fir_garland`.
- **Brushes** lie on the snare. If the organizer wants the drummer holding them, the `act_brush_*` nodes can be re-parented to the hands.
- **The sax on its stand** in the bandstand renders is render-only. A real `instr_sax_stand` variant could be exported if the band should look "on a break".
