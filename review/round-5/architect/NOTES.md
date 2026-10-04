# Architect, round 5: guided stroll, signpost, round-1 leftovers

## Pass 2 (judges' fixes), read this first

| Judges' fix | What I did | Result |
|---|---|---|
| Re-render `signpost.jpg` from the shipped file | New `blender/square/signpost_preview.py` imports the delivered `site/public/models/signpost.glb` (meshopt stripped by the new `decode_glb.mjs`), puts the lantern light on the glb's own `light_sign_0`, and renders with signpost.py's camera and lights. Nothing is rebuilt. | `signpost.jpg` now shows exactly the file being delivered: vertical oak grain, one iron band round the post per board plus the board's two clamp straps, and the snow on the board tops. All seven names and English labels read. |
| Widen the tight lane near (-16, 3) | That pinch was the curve hugging the Bratwurst's back corner, not a pole. `stroll.py` now asks for a 0.35 m reserve on top of every clearance (`ROBUST`). `push_clear` aims for 0.7 m and re-checks the curve with three tensions: centripetal, uniform and chordal Catmull-Rom. The check also runs on all three. I moved two poles I own (`blender/lib/architect_plan.py`). Pole 1 went from [-7.5, 6.5] to [-7.8, 5.6], which widens the front lane at (-7.3, 7.2): the Bratwurst legs had 0.13–0.20 m to spare there. Pole 4 went from [15, 4] to [15.1, 5.2], because the new Bücherstand roof eave came within 0.35 m of its axis and `check_clash.py` flagged it. | Re-planned all 28 legs: **0 failures**. The least spare on any leg went from 0.12 m to 0.35 m. At (-16, 3) it went from 0.12–0.21 m to 0.38–0.40 m, and at (-7.3, 7.2) from 0.13 m to 0.75 m. That holds on all three curve tensions. The nearest standing person is 0.91 m from any leg (0.6 m required). On 3 jump legs (Riesenrad→Musikpavillon, Riesenrad→Bücherstand, Bratwurst→Karussell) that is under 0.95 m, so they carry a WARN for the person reserve only. |
| `cam_view` in `carousel.glb` and `ferris.glb` to match the stops | The ride files are not mine. No other session could be reached from here (`ListAgents` showed none), so the request is below under "For other roles", with exact local values. I also checked the engine. `site/src/nav/stroll.js` already takes the stop's `eye`/`target` from `layout.stroll` and never flies to the glb `cam_view`, **so the camera does not jump**. What still depends on `cam_view` is the lighting designer's place focus (`lighting/index.js enteredPlace()`). It only finds a place when the camera rests within 1.5 m of the glb's `cam_view`, so at these two stops it misses unless the engine sets the focus. | Open, needs the ride builder (values below). |
| Engineer wires `layout.stroll` (centripetal Catmull-Rom) and clickable `act_sign_*`; check letters in browser | Already done by the engineer this round. `interaction/camera.js` uses `CatmullRomCurve3(pts, false, 'centripetal', 0.5)`. `nav/signpost.js` finds the `act_sign_<placeid>` nodes in signpost.glb and tags their meshes for picking. Browser check: I ran the site under vite dev in Playwright on SwiftShader at 1280x720. The market did not reach `data-ready` within 15 min: load average was 13 on 4 cores with the polish round running, so there is no browser screenshot of the letters. | **Open.** From the Cycles home view the German names are about 10 px tall at 1280x720, and they read in `signpost.jpg` under `light_sign_0` alone. Still to do: the engineer's `npm run test:e2e -- --only stroll` home still on a quiet machine, cropped to the signpost at night. |
| Budget rows for `signpost.glb` and `tree.glb` in BUILD.md | `docs/BUILD.md` belongs to the market owner ("say so in your report instead of changing it yourself"), so I did not edit it. Proposed rows: `Market signpost: 5k triangles, 0.5 MB` and `Christmas tree with decorations: 40k triangles, 1.5 MB`. Lite files are about ⅓ with 512 px textures, as for the others. | For the market owner to paste. |
| Re-run `check_clash.py` and `CHECK_ONLY=1 stroll.py` after the crowd re-plan; walkers step aside | `crowd.json` has not changed since 29 Sep, so the organizer has not re-planned yet. I re-ran both against the current crowd and the rebuilt square: `check_clash.py` printed **OK**, after the pole 4 move cleared the Bücherstand flag. The stroll check gives 0 failures (`blender/square/out/stroll_check.txt`). Walkers still cross every leg. Making them yield is the organizer's job, and the request is below. | Re-run both again once `crowd_plan.py` is re-run. |

**Rebuilt this pass:** `square.glb` and `square.lite.glb`, with the moved poles and wires and the re-planned `path_000`–`path_093`. All 94 empties match `layout.json` (max error 0.0 m) in both files. The ground AO was **reused** (`REUSE_AO=1`) to spare the shared CPU, so the faint AO under pole 1's and pole 4's old spots remains. Each moved under 1.3 m and the contact shadow of a 0.2 m pole is tiny. A full re-bake is on the open list. The town, tree and signpost files are unchanged.

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 39,464 | 2.20 MB | 40k / 3 MB |
| square.lite.glb | 12,690 | 0.68 MB | |
| town.glb | 133,979 | 4.41 MB | 150k / 5 MB |
| town.lite.glb | 32,261 | 1.20 MB | |
| tree.glb | 39,944 | 1.05 MB | proposed 40k / 1.5 MB |
| tree.lite.glb | 9,684 | 0.33 MB | |
| signpost.glb | 2,228 | 0.43 MB | proposed 5k / 0.5 MB |
| signpost.lite.glb | 1,152 | 0.17 MB | |

**Previews this pass:** `signpost.jpg` (re-rendered from the shipped glb) and `stroll_topdown.jpg` (re-drawn with the new paths and poles). `home.jpg` and `stroll_eye.jpg` are from pass 1. The moved poles are 0.9 m and 1.2 m shifts at the frame edges.

**For the ride builder (exact values).** These put `cam_view` and `cam_target` on the stroll stops. They are in each asset's local frame, three.js metres, before layout placement.
- `ferris.glb`: `cam_view` [0.0, 1.7, 12.5], `cam_target` [0.0, 9.0, 0.0]. In Blender that is (0, -12.5, 1.7) and (0, 0, 9).
- `carousel.glb`: `cam_view` [2.0, 1.75, 10.5], `cam_target` [0.0, 2.3, 0.0]. In Blender that is (2.0, -10.5, 1.75) and (0, 0, 2.3).

**For the organizer.** Poles 1 and 4 moved (above). No standing person is within 1.2 m of either new spot. When `crowd_plan.py` is re-run (it reads `POLES_THREE`), keep people 0.95 m off `stroll.legs`: 0.6 m clearance plus the 0.35 m reserve. Let the walkers pause or step aside within about 3 m of the camera on a leg. Then run `CHECK_ONLY=1 python3 blender/square/stroll.py`, which must exit 0.

**New and changed scripts:** `blender/square/signpost_preview.py`, `blender/square/decode_glb.mjs`, `blender/square/stroll.py` (ROBUST reserve, three-tension check, WARN lines) and `blender/lib/architect_plan.py` (poles 1 and 4).

---

## Pass 1

There was no round-4 architect folder. The open points I worked from are the round-1 judges' non-blocking fixes (`review/round-1/architect/JUDGES.md`) and the round-5 brief: the guided stroll from ADR 0003, plus Mac's note that text should live in the market, not in panels.

Everything here was rebuilt on the cloud machine: signpost, square (with a fresh ground AO bake against the current town), town, and the lite files. Nothing is committed.

## What was built

### 1. The guided stroll (`site/src/layout.json` → `stroll`, written by `blender/square/stroll.py`)

**Stops, in walking order:** home → Glühwein → Riesenrad → Bratwurst → Musikpavillon → Bierstand → Karussell → Bücherstand → back home.

**Why this order.** `stroll.py` measured the loop length of all 5,040 orders over the planned lane paths.
- The shortest loop is 175.5 m. This one is 179.9 m, the shortest that starts with Glühwein (About), which works as the host's welcome.
- The middle of the back is closed: the bandstand, the tree, the tree benches and the people around them leave no lane there. So the Riesenrad and the Karussell are spurs. You walk each side out and back once.
- No other lane is walked twice, and no loop leg is longer than 34 m.

**Stop poses.** Each stop has `eye` and `target` in three.js metres.
- The four stalls and the bandstand use their own `cam_view` / `cam_target`, transformed by layout.json.
- **Riesenrad:** `ferris.glb`'s `cam_view` sits 31 m out, in the middle of the market. The stop is instead at the foot of the wheel by the boarding queue, looking up at it. It also carries `overview` (eye 23 m up in the top gondola, looking over the market), which is the ADR's overview.
- **Karussell:** `carousel.glb`'s `cam_view` is boxed in between the bandstand and the Bierstand (no 1 m path reaches it). The stop is 10.5 m in front of the carousel, beside the watching children.

**Legs.** There are 28: the 8 loop legs (`loop: true`) and a direct leg for every other pair, so a signpost choice walks straight to any stop.
- Points are about 2 m apart, from `from`'s eye to `to`'s eye. Walk a leg backwards by reversing it.
- On the lanes the eye is at 1.6 m. Over the last 4 m it eases into the stop's own camera height.
- Home legs come down from the 9 m home camera onto the front lane by z ≈ 17, passing the signpost.
- Each leg arrives along its stop's view direction, so the camera faces the stall when it stops.

**`path_000`–`path_093` in `square.glb` and `square.lite.glb`.** These are the loop legs in order. Each loop leg's `path_nodes` gives its first and last empty, and a stop's eye appears twice (it ends one leg and starts the next). Checked: all 94 empties match the layout points (max error 0.0 m).

**How the paths are made and checked.**
- `stroll.py` decodes every placed glb and rasterises each triangle that reaches into the walking band (0.05–2.2 m above the ground) onto a 0.1 m grid. These are real footprints, not bounding boxes.
- It adds the poles, lamps, benches, bins and bollards that `square.py` now writes to `blender/square/out/furniture.json`, and every standing person in `crowd.json`.
- It plans with A* on a clearance-weighted cost (keeping to the middle of the lanes), string-pulls, smooths, resamples, and nudges points uphill on the clearance field.
- It then checks a centripetal Catmull-Rom through the points (what the engine should use).

**Result: 0 failures on all 28 legs.**
- Every point keeps 0.7 m from any stall, ride or tree surface, 0.5 m from any furniture and 0.6 m from any standing person's centre.
- The tightest loop leg still has 0.21 m to spare.
- `stroll_topdown.jpg` is the top-down check. `blender/square/out/stroll_check.txt` has per-leg clearances.
- Walkers move, so they are only reported: every leg crosses some walker path.

### 2. The signpost (`signpost.glb`, `signpost.lite.glb`, `blender/square/signpost.py`)

**Structure.** A 4.75 m weathered oak post on a granite plinth with seven finger boards.
- **Boards:** 1.6 × 0.32 m each, cream paint over oak, chipped at the edges, with a red border line. The German name is carved and painted in oxblood capitals (Alegreya SC). A small English label sits underneath in IM Fell italic, with a little arrow.
- **Lettering:** painted into one 2048 px atlas (1024 in the glb, 512 in lite). Both faces carry it, so there are 14 cells.
- **Clickable nodes:** each board is a node `act_sign_<placeid>` (`riesenrad`, `karussell`, `gluehwein`, `bandstand`, `bratwurst`, `bierstand`, `buecherstand`). Its origin is on the post axis at the board's height, so the engine can wiggle it on hover. Its iron clamps are child nodes.
- **On top:** a shingled cap and ball finial, and an iron bracket with a lantern. The lantern carries `bulbs_sign` (`bulb_warm`) and `light_sign_0`, so the boards can be lit and read at night.
- **Also:** a fir wreath with a red bow, and `snow_sign` on the cap, the board tops, the wreath and the plinth. Occlusion is per vertex through a ramp image, on `TEXCOORD_1`.
- **Board directions:** boards point left or right (toward the side of the market the place lies on) and turn up to 22° toward it. Pointing them truly (mostly away from the camera) would show them edge-on.

**Placement:** `[-4.0, 19.5]`, rotY 0.47, facing the home camera. It sits in the lower left of the home frame, below the Bratwurst and clear of the four section stalls and the bandstand. It is also in `stroll.py`'s obstacle set, and no leg passes under its boards.

### 3. Round-1 leftovers

| Round-1 point | Fix |
|---|---|
| Puddles read as dark smudges | `puddle_water` base colour is now close to the wet cobbles (0.075 against 0.035) and its roughness goes from 0.05 to 0.12. A puddle is now a darker, glossier patch of the same paving with a soft smear of the lamps, instead of a black mirror of the sky. |
| Church nave roof is a black slab from home | The slate albedo goes up about a third (factor 1.32/1.34/1.40). A third, lower-ranked empty `light_church_2` grazes the square-side slope from across the lane (the lighting designer decides whether to use it). `preview.py` lights it as a wide spot. |
| Empty dark foreground in the home view | The signpost now stands in it. |
| Square AO baked before the final town (NOTES timeline) | `square.glb` was rebuilt with `REUSE_AO` unset, after the town, and the ground AO was re-baked against the current town. |

## Triangles and file sizes (after optimisation)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 39,038 | 2.19 MB | 40k / 3 MB |
| square.lite.glb | 12,798 | 0.68 MB | ~⅓ |
| town.glb | 133,979 | 4.41 MB | 150k / 5 MB |
| town.lite.glb | 32,261 | 1.20 MB | ~⅓ |
| tree.glb | 39,944 | 1.05 MB | 40k / 1.5 MB (unchanged this round) |
| tree.lite.glb | 9,684 | 0.33 MB | |
| signpost.glb | 2,228 | 0.43 MB | no row; most of the bytes are the lettering atlas |
| signpost.lite.glb | 1,152 | 0.17 MB | |

Desktop total for my files is 8.08 MB; the lite total is 2.38 MB.

**Node checks:**
- `square.glb`: 25 `light_`, 94 `path_`, and the same `bulbs_*` (`bulb_warm`) and `snow_ground` / `snow_props` as before. The lite file has 15 `light_` and 94 `path_`.
- `town.glb`: `light_church_0/1/2`, `window_warm`, `snow_roofs` / `snow_skyline`.
- `signpost.glb`: 7 `act_sign_*`, `light_sign_0`, `bulbs_sign`, `snow_sign`.

## Previews (Cycles, CPU, 1280x720, 48 samples)

- `stroll_topdown.jpg`: the top-down path check.
  - Red: loop legs, with their points. Green: direct legs.
  - Grey: real footprints in the walking band.
  - Orange: standing people with their 0.6 m rings. Blue rings: furniture plus 0.5 m. Dotted: walker routes.
- `signpost.jpg`: the signpost close up at night, lit by its own lantern and the market glow. It was rendered one build before the shipped file. Since then the post's oak grain runs vertically (in the render it shows as horizontal stripes), and each board has one iron band round the post instead of two (in the render the pairs look like ladder rungs). `home.jpg` uses the shipped build.
- `home.jpg`: the home view with the shipped stalls and rides, the rebuilt square and the rebuilt town.
  - The signpost stands in the lower left. All seven German names can be read at full size.
  - The church nave roof now shows its slate tone and the three dormers instead of a black slab.
  - The plinth and wreath fall just below the frame.
- `stroll_eye.jpg`: eye height on the Bratwurst → Musikpavillon loop leg, looking along the path. The lane is open, the bandstand steps are close on the left, and the Bierstand and Bücherstand are ahead.

The town, tree, cobbles and church views from round 1 (`review/round-1/architect/`) still show those assets. I did not re-render them this round to save machine time. The town geometry is unchanged, and only the slate tone and one empty differ.

## How to rebuild

```
/home/claude/tools/bpy-venv/bin/python blender/square/signpost.py      # LITE=1 for lite; PREVIEW=1 renders signpost.jpg
/home/claude/tools/bpy-venv/bin/python blender/town/town.py            # LITE=1 for lite
STATS_ONLY=1 /home/claude/tools/bpy-venv/bin/python blender/square/square.py   # writes out/furniture.json in 10 s
python3 blender/square/stroll.py                                       # plans + checks the stroll, writes layout.json "stroll"; exit 1 on a failure
/home/claude/tools/bpy-venv/bin/python blender/square/square.py        # then LITE=1: adds the path_ empties from layout.json
CHECK_ONLY=1 python3 blender/square/stroll.py                          # re-check the shipped legs after crowd or stall changes
/home/claude/tools/bpy-venv/bin/python blender/square/preview.py <home|stroll|street|church|tree|cobbles|roofs> [samples] [out.jpg]
```

## For other roles

- **Engineer:**
  - Read `layout.stroll`: `order`, `stops[].eye/target` (plus `overview` on the Riesenrad) and `legs[].points`.
  - Prev and next follow `order` cyclically. A signpost click walks the direct leg from the current stop.
  - Use a centripetal Catmull-Rom; the clearance check is made on that curve.
  - The signpost is a `scenery` entry. `layout.js` infers kind `other` for it and loads it as a static model.
- **Organizer:**
  - Re-running `crowd_plan.py` can put people on the paths. Please keep people 0.6 m off `stroll.legs` and then run `CHECK_ONLY=1 python3 blender/square/stroll.py`, or send me the new `crowd.json`.
  - Walkers cross every leg; letting them yield near the camera would help.
  - Two stops moved off their glb `cam_view`: the Karussell (to [14.7, −2.2]) and the Riesenrad (to [−14.4, −7.0]). Nobody stands there now.
- **Ride builder:** `ferris.glb`'s and `carousel.glb`'s `cam_view`s are wide panel-era views. They could move to the stroll's stops (or the ticket booths where the ADR puts the contact ticket and the essays).
- **Lighting:** `light_sign_0` (the signpost lantern) and `light_church_2` (the nave roof) are new. The signpost reads best with its light on.

## What breaks or stretches the contract

1. **Stop poses differ from the glb `cam_view` for the Karussell and the Riesenrad**, for the reasons above. `stroll.stops[].source` says where each pose comes from.
2. **No BUILD.md budget row for the signpost or the tree.** I hold the signpost to under 5k triangles and 0.5 MB.
3. **`layout.json` now also holds `stroll`.** The engine's tolerant reader skips it, since no object in it has a `pos`.

## Open issues and what I would do next

- The home view still has no crowd in my Cycles preview. The browser adds it.
- Checking the signpost lettering at the browser's home framing (software GL) is still to do. At 1280x720 the German names are about 10 px high, and the boards need their lantern light to read at night.
- The puddle change is judged in Cycles only. In the browser it depends on the environment map.
- The middle of the back is closed. Moving the tree 2 m back (with its benches and the bench sitters) would open a back lane and make the loop a true circle. That needs the organizer, so I left it.
- `check_clash.py` was not re-run. Square geometry, poles, wires and furniture are unchanged from round 1, where it printed OK.
