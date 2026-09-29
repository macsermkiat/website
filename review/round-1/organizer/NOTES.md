# Organizer, round 1 pass 2: people, crowd and choreography

Pass 2 answers the judges' fixes (JUDGES.md, CODEX_JUDGE.md) and finishes the partial Mac work. Everything was rebuilt on the cloud machine: `build.py` (all 16 figures, full and lite, plus the clip library), `crowd_plan.py`, the Cycles previews and the three.js checks.

## What changed in pass 2

| Judges asked for | Done |
|---|---|
| Lite files about a third of full (lite was 0.82 of full, 1.72 MB for 16 files) | Lite is now 0.32 to 0.40 of full: 35 to 52 kB each, 0.71 MB for all 16 (was 1.72 MB). The lite market loads 13 of them (5 crowd figures after crowd.js's alias, 4 vendors, 4 band), about 0.56 MB, down from about 0.95 MB. How it was done is under Budgets below. |
| AO in the glTF occlusion texture | Every material (coat, body, hat, scarf, mug) of every full and lite file has an `occlusionTexture`. The AO is baked in Cycles in the rest pose onto a second UV set (`pao.py`), 256 px full and 128 px lite. It is contact shading only (collar, under the hem, arms at the torso, the hat brim), remapped to [0.42, 1]. Base colour stays unlit, so recolouring still works. |
| Seated long coats flatten into a disc | The skirt is split at the hip line: below it each vertex rides the thigh on its own side, and below the knee it blends onto the shin, so a seated coat lies on the lap and the front hem drops over the knees. See `bench_sit.jpg` (Cycles) and `threejs_sit.jpg` (the shipped glbs in three.js). What remains is under open issues. |
| lineup.jpg must show all 16 figures | `lineup.jpg` has two strips: the 8 crowd figures on top, and the 4 vendors in aprons (`serve`) plus the 4 musicians below, each labelled. |
| Keep people out of the stalls' cam_view sight lines | `crowd_plan.py` reads `cam_view` and `cam_target` from each placed glb. It keeps clear a near wedge in front of the camera and a 1.1 m corridor to the target (the counter and vendor, the band). Cameras above 3.5 m, which look over the crowd, are skipped. The grey wedges in `crowd_map.jpg` are those areas. |
| crowd.json tidy-ups | `mug` always matches the clip (a `_free` clip hides the mug), and `crowd_plan.py` now fails loudly if they disagree. Single browsers moved from `groups` to `browsing`, so every group holds 2 to 5 people. No two people in a group, queue or bench share a coat colour (the Karussell children are now blue, plum and amber). The group radius is 0.72 m (0.62 before), and `group_chat.jpg` is posed at that spacing. |
| Walk loop seam (0.014) | `rig.bake_clip` scales time so the last key is exactly t = duration. The walk loops closed. |
| Walker paths 0.2 m from lamp poles | Lamp and string-light poles are 0.45 m obstacles. The left-lane walker runs at x = -18.45, and no clearance warnings remain. |
| Beanie read as a helmet | The knit sits loose over the crown with a slight back slouch and soft folds (`hat_beanie`). |
| Stale NOTES hand-offs | Removed. crowd.js now plays `clip` and `phase`, applies `colors`, keeps vendor y = 0.13, and instruments.js loads the `people_band_*` glbs. The hand-offs that remain are listed below. |

Also fixed this pass:
- **Saxophonist's hands.** The ride builder re-proportioned the tenor sax (the mouthpiece tip moved from local z 0.79 to 0.896, and the key stacks moved). `anims.py` now uses the new mouthpiece and stack positions (left stack centred at z 0.615, right at 0.37), so the mouth stays on the mouthpiece and the hands sit on the stacks. The bass, piano and drum geometry is unchanged.
- **Lite distance level for sitters.** In the full market, people farther than 18 m switch to their lite figure. The bench sitters are about 45 m from the home camera, and pass 1's lite files had no `sit`, so far sitters would have stood up. Lite crowd files now carry `sit`.

## Figures (unchanged in design, rebuilt)

- **8 crowd figures:**
  - `people_man_coat`: long double-breasted coat and flat cap.
  - `people_woman_coat`: belted camel coat and bobble hat.
  - `people_man_parka`: hooded parka, beard and beanie.
  - `people_woman_older`: glasses, beret and handbag.
  - `people_man_older`: glasses and trilby.
  - `people_woman_young`: quilted jacket, striped scarf and snow boots.
  - `people_child_boy`: 1.18 m, puffer and earflap hat.
  - `people_child_girl`: 1.28 m, duffle coat and pigtails.
- **4 musicians:** `people_band_sax`, `_piano`, `_bass` and `_drums`. Their poses are solved against the ride builder's instruments at `slot_sax`, `slot_piano`, `slot_bass` and `slot_drums`.
- **4 vendors in aprons:** `people_vendor_gluehwein`, `_bier`, `_wurst` and `_buecher`, standing at `slot_vendor`.
- **Materials.** Every figure has `coat`, `scarf`, `hat`, `body` and `mug`. The engine recolours `coat`, `scarf` and `hat` through `material.color`, which is multiplied with COLOR_0. Full files carry the knit and wool normal maps (256 px), and every material has the AO occlusion texture.
- **Skeleton.** 20 joints, 4 influences per vertex, all bone names shared across figures.

### Clips per file

| file | full | lite |
|---|---|---|
| crowd | idle, walk, chat, drink, laugh, sit, idle_free, walk_free, chat_free | idle, walk, chat, drink, sit |
| band | play, rest, idle, walk, chat, drink | play, rest |
| vendor | serve, wipe, idle, walk, chat, drink | serve, wipe |

- Every full file has `walk`, `idle`, `chat` and `drink` (check with `gltf-transform inspect`).
- Lite files carry only what a lite figure actually plays: in the lite market, and for far people in the full market. For a missing crowd clip, `site/src/crowd.js` already falls back to `idle` (or `walk` for walkers), and it hides the mug mesh when the clip name ends in `_free`. So a far `idle_free` person plays `idle` with the mug hidden and the right hand at the coat front.
- `crowd.json` records this under `clips.lite` and `clips.notes.fallback`. `crowd_plan.py` checks that every person's clip is either in the lite file or has a fallback.
- `people_anims.glb` (68 kB, not loaded by the engine today) holds all 13 crowd and vendor clips on the reference skeleton, with every rotation explicit, for an engine that retargets by bone name.

## Budgets (from `blender/out/people/report.json`)

The budget is 5,000 triangles and 0.4 MB per person; lite is about a third.

| figure | tris | size | lite tris (ratio) | lite size (ratio) | clips full / lite |
|---|---|---|---|---|---|
| people_man_coat | 4560 | 125 kB | 1484 (0.33) | 49 kB (0.39) | 9 / 5 |
| people_woman_coat | 4864 | 129 kB | 1652 (0.34) | 51 kB (0.39) | 9 / 5 |
| people_man_parka | 4972 | 129 kB | 1774 (0.36) | 52 kB (0.40) | 9 / 5 |
| people_woman_older | 4836 | 129 kB | 1649 (0.34) | 51 kB (0.40) | 9 / 5 |
| people_man_older | 4536 | 127 kB | 1532 (0.34) | 50 kB (0.39) | 9 / 5 |
| people_woman_young | 4708 | 125 kB | 1584 (0.34) | 49 kB (0.39) | 9 / 5 |
| people_child_boy | 4980 | 130 kB | 1800 (0.36) | 52 kB (0.40) | 9 / 5 |
| people_child_girl | 4756 | 126 kB | 1708 (0.36) | 50 kB (0.40) | 9 / 5 |
| people_band_sax | 4532 | 116 kB | 1550 (0.34) | 41 kB (0.35) | 6 / 2 |
| people_band_piano | 4836 | 121 kB | 1669 (0.35) | 42 kB (0.34) | 6 / 2 |
| people_band_bass | 4656 | 117 kB | 1600 (0.34) | 41 kB (0.35) | 6 / 2 |
| people_band_drums | 4576 | 119 kB | 1544 (0.34) | 40 kB (0.34) | 6 / 2 |
| people_vendor_gluehwein | 4804 | 113 kB | 1644 (0.34) | 37 kB (0.32) | 6 / 2 |
| people_vendor_bier | 4263 | 109 kB | 1639 (0.38) | 36 kB (0.33) | 6 / 2 |
| people_vendor_wurst | 3801 | 106 kB | 1409 (0.37) | 35 kB (0.33) | 6 / 2 |
| people_vendor_buecher | 4374 | 115 kB | 1550 (0.35) | 38 kB (0.33) | 6 / 2 |
| **all 16** | 3801 to 4980 | **1.94 MB** (was 2.07) | 1409 to 1800 | **0.71 MB** (was 1.72) | |
| people_anims.glb | – | 68 kB | | | 13 |

Triangle counts include the mug (about 100 triangles). Every file passes `gltf-transform validate` with no errors. The warnings are the usual ones for Blender skinned exports: tangents generated at runtime for the normal-mapped fabrics, and the skinned mesh sitting under the armature node.

### How lite got small (`blender/people/pack.mjs`)

In a 5k-triangle figure, the clips' glTF JSON was most of the file: each animation channel costs a channel, a sampler and one or two accessors, about 300 bytes. `pack.mjs` replaces the old slim step followed by `optimize.mjs`. It runs the same web passes (dedup, weld, prune, sparse, WebP, meshopt, with names kept) and also does the following:

- **Baked keys only.** It keeps just the keys `rig.bake_clip` wrote (every 3rd frame, every 2nd for walks, and every 6th for lite's slow clips). All channels of a clip then share one time accessor, where resample() gave each its own.
- **Bone defaults moved to the most common still pose (`--rest-opt`).** Held poses then drop out. The skin's bind pose (inverseBindMatrices) is untouched, and every clip plays exactly as before. Only standing clips may set a default, so an unanimated figure stands with its arms down instead of in a T-pose.
- **Coarser lite thresholds.** Lite drops channels that stay within about 1.6° or 8 mm.
- **One vertex buffer per mesh.** The four material primitives share their attribute accessors and differ only in their indices, merged after quantize.
- **Trimmed JSON.** Default values are dropped, and node transforms are rounded to 6 decimals.

## Rebuild

```
/home/claude/tools/bpy-venv/bin/python blender/people/build.py [--only people_man_coat,...] [--no-lite] [--no-ao]
/home/claude/tools/bpy-venv/bin/python blender/people/build.py --repack        # re-pack the raw exports only (seconds)
python3 blender/people/crowd_plan.py                                           # after layout.json or stall changes
/home/claude/tools/bpy-venv/bin/python blender/people/preview.py lineup|band|group|bench --samples 48 --res 1280x720
node blender/people/web/shoot.mjs --figs people_man_coat:sit:1,... [--lite] [--cam x,y,z,tx,ty,tz,fov] --out file.jpg
```

- A full build takes about 7 minutes on the cloud machine.
- Renders honour `NM_DEVICE` and `NM_THREADS`, defaulting to CPU with 2 threads. Each 1280x720 preview at 48 samples takes about 6 to 9 minutes.

## Previews

- `lineup.jpg` (Cycles): all 16 figures in two labelled strips.
- `band.jpg` (Cycles): the four musicians at their slots on the ride builder's current bandstand, with the current instruments, `play` at t = 1 s.
- `group_chat.jpg` (Cycles): four adults at crowd.json spacing (chat, drink, laugh, idle) and a child.
- `bench_sit.jpg` (Cycles): seated long coats on a bench at the square's seat height.
- `threejs_full.jpg`, `threejs_lite.jpg` and `threejs_sit.jpg`: the shipped glbs in three.js (SwiftShader), played the way crowd.js plays them. `threejs_lite.jpg` shows the lite clip fallbacks.
- `crowd_map.jpg`: a top-down plan of crowd.json over the layout, with the kept-clear view wedges.

## crowd.json

- **90 people plus 4 musicians,** most important first. The lite market keeps the first 40.
  - 4 vendors at `slot_vendor`, with world `pos` [x, y, z] (y = 0.13, the stall floor) and `rotY`.
  - 3 queues with 12 people: Glühwein 5, Bier 4, Riesenrad ticket booth 3.
  - 10 walkers plus 2 in `walkers_more`.
  - 19 groups of 2 to 5, placed at the stalls, the tree (including a family), the bandstand listeners and the Karussell children.
  - 4 `browsing` entries.
  - 2 `benches`: a couple and a single, using `sit`.
- **The 4 `musicians`** are listed by slot only. instruments.js places them.
- **Per person:** `variant`, `model`, `clip`, `mug`, `colors` {coat, scarf, hat} and `phase`.
- **Checks in `crowd_plan.py`:** clearance against stalls, landmarks, poles, benches and view wedges; mug against clip; every clip in the full file, and either in the lite file or covered by a fallback.

## Hand-offs to the engineer (still open)

1. **Shared clips (the real lite fix).** Load `people_anims.glb` once and retarget its clips onto each figure by bone name. Rotations are explicit on every bone. For `hips.position`, add (figure hips rest − reference hips rest). With that in place, lite figures could ship without clips at about 30 kB each, and full figures at about 80 kB. `crowd.json` `shared_anims` says the same.
2. **Instrument sway.** `act_sax` sway and `act_brush` sweep are not synced to the players' `play` clips. Either move the player with the instrument or switch the instrument animation off.
3. **Draw calls.** Each person is 2 meshes with 5 materials, about 5 draw calls, so 90 people make about 450. The primitives now share one vertex buffer, which makes a later merge or instancing per variant easier.

## Contract notes

- **AO and base colour.** The AO lives only in the occlusion texture (BUILD.md) and none is in base colour. Lite keeps it too, as a 128 px texture of about 3 kB.
- **Clips in lite files.** Lite band and vendor files carry only their role clips (play/rest and serve/wipe). The brief's check that walk, idle, chat and drink exist holds for every full file and for the lite crowd files.
- **Ownership.** I wrote only in `blender/people/`, `site/public/models/people_*`, `site/src/crowd.json`, `review/round-1/organizer/` and my section of `CREDITS.md`. The bandstand and instruments are read-only inputs from `blender/out/raw/`.

## Open issues and next steps

- **Seated coats.** They now lie on the lap and the front hem drops over the knees. Seen from above in three.js (`threejs_sit.jpg`), though, the lap part of a long coat still reads as a stiff, slightly wide tray, because the sides of the skirt stay horizontal. The fix is a pair of skirt bones that `sit` and the seated `play` rotate halfway down, costing 2 joints and a few channels.
- **Lite's missing _free clips.** A far mug-less person in the lite level stands with the right hand at the coat front, because it plays `idle` with the mug hidden. Hand-off 1 removes this.
- **Faces** are still simple: a nose wedge, with eyes and brows in vertex colour.
- **Child sit without a bench** reads as a crouch. crowd.json only seats children on benches, and none are seated there today.
- **`slot_vendor`** sits about 1 m behind the counter on some stalls, so the `serve` reach toward the counter is approximate.
