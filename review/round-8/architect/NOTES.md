# Architect, round 8: the stroll walks the whole market (ADR 0004)

Nothing is committed. Everything below was built and checked on the cloud machine. Mac's note that side stalls are cheap, non-interactive scenery ("There's no need to fully render object in side stores…") is followed in two ways. The layout marks those stalls lite-only, and my previews load them that way too.

## What changed

### 1. The guided stroll is re-routed (`site/src/layout.json` → `stroll`, `blender/square/stroll.py`)

**The new loop has nine stops, the ornament shop being the eighth place:**
home → Glühwein → Musikpavillon → Bierstand → Bücherstand → **Christbaumschmuck** → Karussell → Riesenrad → Bratwurst → home.

| Loop leg | What it walks past |
|---|---|
| Bücherstand → Christbaumschmuck (11 m) | Out along the front-right lane to the ornament shop at the south end of the right deco lane. |
| Christbaumschmuck → Karussell (18 m) | North up the **right deco lane**, past Käse and Holzspielzeug. The walk arrives at the Karussell stop from the south, facing the ride. |
| Karussell → Riesenrad (54 m) | Through the gap between the tree and the carousel, then west along the **back row**: Kartoffelpuffer, Heiße Maroni, Crêpes. |
| Riesenrad → Bratwurst (35 m) | South down the **left deco lane**, past Lebkuchen, Gebrannte Mandeln and Kerzen. |

- **No lane is walked twice.** The Riesenrad and the Karussell are no longer out-and-back spurs, because the loop now runs round the back of the market. Loop length: 209.6 m (round 5: 193.9 m).
- **Distance from each deco counter front** (`stroll.deco_pass` in layout.json):

  | Stall | Distance |
  |---|---|
  | Lebkuchen | 2.4 m |
  | Mandeln | 2.4 m |
  | Kerzen | 3.2 m |
  | Holzspielzeug | 2.9 m |
  | Käse | 2.0 m |
  | Crêpes | 3.0 m |
  | Maroni | 2.0 m |
  | Kartoffelpuffer | 2.3 m |

  That is close enough to see the goods at walking pace, and leaves room for one or two customers at each counter.
- **How the deco lanes are enforced.** The three legs above go through via points about 2.2 m in front of each counter, plus the tree/carousel gap. Each stretch between via points is planned and string-pulled on its own, so the walk cannot cut across and skip a stall. Jumps between the Karussell and the front of the market also walk up the right deco lane, where the loop goes.
- **Arriving at a stop.** Loop legs now swing the arrival point up to 55° toward the side the walk comes from, so the camera does not walk past a stop and hook back. Every approach point is checked for clearance.
- **Result: 0 failures on all 36 legs** (9 loop legs, 27 direct legs), checked on centripetal, uniform and chordal Catmull-Rom curves. The checks are the same as before:
  - 0.7 m from every stall, ride and tree surface in the 0.05–2.2 m band;
  - 0.5 m from every pole, lamp, bench, bin and bollard;
  - 0.6 m from every standing person in the current `crowd.json`.
- **One WARN.** On Riesenrad → Bratwurst, `group_square_10` stands 0.84 m from the path. That passes the 0.6 m rule but is under the 0.95 m reserve. Per-leg figures are in `blender/square/out/stroll_check.txt`.
- **Stop sources.** Every stop's eye and target come from its glb's `cam_view` / `cam_target`.
  - The ornament shop's stop comes from `stall_schmuck.glb` (eye [17.56, 1.8, 10.23]).
  - The Bücherstand stop moved to [8.32, 1.85, 6.95] because the carpenter's round-8 cabinets put `cam_view` 6.25 m out.
- **`stroll.order`** is now `["home","gluehwein","bandstand","bierstand","buecherstand","deco-schmuck","karussell","riesenrad","bratwurst"]`.

### 2. The ornament shop gets its room (`places` in layout.json)

| Place | Old pos | New pos | Why |
|---|---|---|---|
| deco-schmuck (`stall_schmuck.glb`, 5.4 m wide) | [21.0, 3.5] | **[23.3, 10.6]**, rotY −1.64 | South end of the right lane. Its stop eye (5.35 m out) would have stood inside the Bücherstand's back corner at the old spot. Here it stands in open lane, with 2.6 m to pole 14. |
| deco-kaese | [20.5, 10.2] | [23.0, 3.9] | Swapped into the middle of the right lane. |
| deco-spielzeug | [21.1, −3.4] | [22.9, −2.4] | Right lane, 2.8 m clear of the moved carousel. |
| deco-lebkuchen / mandeln / kerzen | x ≈ −21 | x ≈ −22.3 to −22.7 | Moved 1.4 m out, so the walk fits between the lane poles and the counters. |
| deco-crepes / maroni | z ≈ −21.5 | [−10.2, −21.6] / [−3.6, −22.6] | The back lane runs in front of them. |
| deco-kartoffelpuffer | [15.6, −21.3] (behind the carousel) | **[5.6, −26.1]** | Behind the tree, so the back lane passes between the tree and its counter. At the old spot no lane could reach it. |
| karussell | [19, −12] | **[21, −13.5]**, rotY unchanged | Opens a 3 m gap between the tree and the carousel for the back lane. The stop moves with the ride: the eye is derived from carousel.glb's local `cam_view`, now at [16.72, 1.75, −3.71]. |

The four section stalls, the bandstand, the Riesenrad, the tree, the town and the home camera are unchanged, so the home view keeps all four section stalls and the bandstand.

- **Deco entries** now carry `"stream": "lite"`. This follows Mac's note and ADR 0004: these stalls never stream beyond their lite file. The engine needs to honour it (see below).
- **`deco-schmuck`** carries `"stop": true, "interactive": true` and keeps `kind: "deco"`. The layout still lists exactly 9 deco stalls, 4 section stalls and 3 landmarks, plus the tree, square, town and signpost.

### 3. Signpost: a Christbaumschmuck arm (`signpost.glb` + lite, `blender/square/signpost.py`)

- **New board.** An eighth board, `act_sign_schmuck`, reads "CHRISTBAUMSCHMUCK" (Alegreya SC) with "Ornaments" under it. It points right toward the shop. The word is long, so the board is 2.3 m (the others are 1.6 m) and takes a whole atlas row per face. Its letters are about as tall as the other boards'.
- **Board order, top to bottom:** Riesenrad, Karussell, Glühwein, Christbaumschmuck, Bratwurst, Musikpavillon, Bierstand, Bücherstand.
- **Spacing.** The stack starts a little higher (4.42 m) with 6 cm gaps, so eight boards fit on the same post.
- **Checked from the shipped files.** Both files carry the 8 `act_sign_*` nodes, `light_sign_0`, `bulbs_sign` and `snow_sign`. `signpost.jpg` is rendered from the shipped glb (`signpost_preview.py`).

### 4. Square (`square.glb` + lite, `blender/lib/architect_plan.py`)

**String-light poles moved so they keep out of the new lanes:**

| Pole | Old | New | Why |
|---|---|---|---|
| 3 | [7.5, 6.5] | [6.3, 8.4] | The new Bücherstand stop eye was 0.95 m from it. |
| 9 | [−17.5, −3] | [−16.6, −1.2] | Out of the left lane. |
| 10 | [−17.5, 5] | [−16.9, 6.4] | Out of the left lane. |
| 12 | [17.5, −3] | [16.9, −0.2] | Out of the right lane. |
| 13 | [17.5, 5] | [18.2, 5.4] | Clear of the people at the Bücherstand's flank. |
| 15, 16, 17 (back row) | in the back lane | [−6.9, −22.8], [0.8, −24.6], [14.5, −22.5] | Now behind the stall fronts, clear of the back lane. |

- **Span 29** now hangs from pole 16 (`[16, 5]`). From pole 15's new spot it passed through the Riesenrad's footprint.
- **Path empties.** `path_000`–`path_106` (107 empties) are the new loop legs, with max error 0.000 m against layout.json in both files.
- **Ground AO** was re-baked with the moved poles. The span-29 fix afterwards reused that bake, because wires are hidden during the bake.
- **`check_clash.py`: OK.**
  - Nothing stands in a stall or ride.
  - No wire or bulb is in the fir.
  - Every wire and bulb keeps at least 0.15 m from every stall, ride and bandstand surface.
  - Wires over the bandstand roof have 0.88 m or more to spare.

### 5. Previews (Cycles, CPU, 1280x720, 48 samples)

- `stroll_topdown.jpg`: the required top-down check, regenerated.
  - Red loop with walking-direction arrows.
  - Deco stalls in brown, each labelled with its distance from the loop.
  - The ornament shop in gold, with its stop as a star.
  - The signpost arms, read from the shipped `signpost.glb` (Christbaumschmuck starred).
  - Standing people with their 0.6 m rings, and furniture rings.
- `home.jpg`: the square and town from the home camera with the new layout. Stalls and rides are the shipped glbs.
  - New this round: the vendor's prop sets (`props.json`) sit on their slots.
  - Deco stalls and their goods use the lite files, as the market will load them (`preview.py`).
- `street.jpg`: a street of houses in the town ring, rendered fresh.
- `signpost.jpg`: the shipped signpost with the new arm.
- `tree.jpg`: copied from round 5. `tree.glb` has not changed since then, so there was no point spending another render on it.

## Triangles and sizes (gltf-transform inspect, after optimize.mjs)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 39,282 | 2.20 MB | 40k / 3 MB |
| square.lite.glb | 12,652 | 0.68 MB | |
| town.glb (unchanged) | 133,979 | 4.41 MB | 150k / 5 MB |
| town.lite.glb | 32,261 | 1.20 MB | |
| tree.glb (unchanged) | 39,944 | 1.05 MB | proposed 40k / 1.5 MB |
| tree.lite.glb | 9,684 | 0.33 MB | |
| signpost.glb | 2,380 | 0.47 MB | proposed 5k / 0.5 MB |
| signpost.lite.glb | 1,208 | 0.19 MB | |

**Node checks:**

| File | Nodes |
|---|---|
| `square.glb` | 25 `light_`, 49 `bulbs_*` on `bulb_warm`, `snow_ground`, `snow_props`, 107 `path_` |
| `square.lite.glb` | 15 `light_`, 42 `bulbs_`, 107 `path_` |
| `town.glb` | `window_warm`, `snow_roofs`, `snow_skyline` (unchanged) |
| `tree.glb` | `bulbs_` and `snow_` (unchanged) |

## For other roles

- **Engineer**
  - Add the ornament shop as a place, for example `schmuck` with aliases `schmuck`, `deco-schmuck`, `christbaumschmuck`, `ornaments`. Put it in the stroll and signpost order, so `stroll.js` keeps it (it filters `layout.stroll.order` by your `ORDER`) and `signpost.js` finds `act_sign_schmuck`.
  - Careful: `layout.js inferKind()` turns any entry that has a `place` into a landmark. Keep deco-schmuck a deco stall that is also a stop.
  - Honour `"stream": "lite"`: never upgrade those stalls (or their prop sets) to the full file.
  - The stroll format is unchanged apart from a new `deco_pass` key. Legs are found by `from`/`to`, so the 36 legs need no code change.
- **Organizer**
  - The layout moved: deco lanes, back row, the Kartoffelpuffer, the carousel (2 m east, 1.5 m back) and poles 3, 9, 10, 12, 13, 15, 16 and 17. Re-run `crowd_plan.py`; it reads `POLES_THREE`.
  - The loop now runs along the deco lanes about 2–3 m off the counters, and along the back row between the tree and the back stalls. Keep counter customers within about 1 m of the counter front.
  - Keep standing people 0.95 m off `layout.stroll.legs`, then run `CHECK_ONLY=1 python3 blender/square/stroll.py` (it must exit 0).
  - The current crowd still stands at the round-7 spots. It passes the check, but `group_buecherstand_7` and the carousel watchers belong to the old layout.
- **Lighting designer:** the carousel moved, but its `cam_view` is local, so place focus still finds it. The home view is unchanged.
- **Market owner:** BUILD.md's "Layout (starting point)" section no longer matches the new deco, back-row and carousel positions. layout.json is the source. The proposed budget rows for the signpost and tree from round 5 still stand.

## Open issues / next

- **Not checked in the browser.** The re-routed stroll and the new signpost arm have not been tried in the browser, because the engine needs the `schmuck` place first.
- **Walkers still cross legs.** Every leg crosses some walker path (they are reported, not failed). Making them yield is the organizer's job.
- **The Bratwurst arrival doubles back for about 3 m.** The walk comes in from Kerzen and then leaves for home over nearly the same ground. I could fix it by moving the Bratwurst stop toward the lane, but that would mean changing `cam_view` in the carpenter's glb.
- **The home preview's deco stalls are lite files** with lite goods. That is on purpose, but it means they read softer than the section stalls up close.
- **Signpost lettering** is checked in Cycles only. From home, the boards are small at 1280x720.
