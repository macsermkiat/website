# Round 9: architect (square, town, tree, layout)

This was a small round. The carpenter moved the ornament shop's `cam_view` back to 4.3 m in front of the hut (it was 4.05 m), so the `deco-schmuck` stroll stop had to follow it. Nothing else in the square, town or tree changed.

## What changed

1. **The ornament shop stop moved to the new `cam_view`.** `blender/square/stroll.py` re-read `stall_schmuck.glb`'s `cam_view` (local [0, 1.8, 5.6]) and `cam_target` (local [0, 1.62, 1.0]). It then placed both in the world at pos [23.3, 10.6], rotY -1.64.
   - Eye: [17.963, 1.8, 10.23] became **[17.713, 1.8, 10.213]**, 0.25 m further back.
   - Target: [22.302, 1.62, 10.531], the same as before.
   - The stop has 2.11 m of spare clearance.
2. **Every leg was re-planned.** The run kept all nine stops and the same loop order (home, Glühwein, Musikpavillon, Bierstand, Bücherstand, Christbaumschmuck, Karussell, Riesenrad, Bratwurst). The other eight stops are identical to round 8. `places`, `camera` and the rest of `layout.json` are byte-for-byte the same; only the `stroll` key changed.
   - The planner re-ran against the current `crowd.json` and furniture, so most legs moved slightly. Most got shorter. The loop is 194.5 m (round 8: 209.6 m).
   - Riesenrad → Bratwurst went from 34.9 m to 27.2 m. It still walks down the left deco lane past Lebkuchen (2.76 m from the counter), Gebrannte Mandeln (2.38 m) and Kerzen (3.24 m).
   - All nine deco stalls are still passed by a loop leg, between 2.1 and 3.8 m from their counters.
3. **The round 8 organizer note (`group_square_10` 0.84 m from Riesenrad → Bratwurst) is cleared.** `crowd.json` no longer has a `group_square_10`; the organizer re-planned the crowd at the end of round 8. On the new leg the nearest standing person is `browsing_mandeln#0`, 1.83 m away. That clears the 0.95 m reserve (0.6 m rule + 0.35 m robustness). I didn't need to touch `crowd.json`, which is the organizer's file.
4. **The `path_` empties in `square.glb` and `square.lite.glb` now follow the new loop.** The square carries the loop legs as `path_000…` empties. The new loop has 100 points (round 8: 107), so the old empties were stale.
   - Rather than spend a full Blender rebuild and AO bake, `blender/square/refresh_paths.py` (new, plain Python) rewrites only the glTF JSON chunk. It drops the old `path_` nodes and adds the new ones as scene roots in walking order. Meshes, textures and buffers are untouched.
   - Both files pass `gltf-transform validate` with no errors.
   - `square.py` writes the same empties from `layout.json` whenever it next runs.
5. `stroll.py` now writes its map to `review/round-9/architect/`, and the map is titled round 9.

## Stroll check

`CHECK_ONLY=1 python3 blender/square/stroll.py`: **0 failures and 0 legs below the 0.35 m robustness target**, across all 36 legs (9 loop + 27 signpost jumps). Every leg was checked on centripetal, uniform and chordal Catmull-Rom curves. The round 8 run had one WARN; it is gone. Per-leg figures are in `blender/square/out/stroll_check.txt`, and the full planning log is in `blender/square/out/stroll_run9.log`.

Loop legs:

| Leg | Length | Spare clearance | Nearest standing person |
|---|---|---|---|
| home → Glühwein | 33.7 m | 2.10 m | 1.22 m |
| Glühwein → Musikpavillon | 9.8 m | 1.15 m | 2.34 m |
| Musikpavillon → Bierstand | 4.7 m | 2.34 m | 3.01 m |
| Bierstand → Bücherstand | 5.5 m | 1.02 m | 3.01 m |
| Bücherstand → Christbaumschmuck | 10.8 m | 1.71 m | 3.81 m |
| Christbaumschmuck → Karussell | 15.9 m | 0.62 m | 1.75 m |
| Karussell → Riesenrad | 53.7 m | 0.67 m | 1.07 m |
| Riesenrad → Bratwurst | 27.2 m | 0.89 m | 1.83 m |
| Bratwurst → home | 33.2 m | 0.84 m | 3.01 m |

## Previews

- `stroll_topdown.jpg` is new this round. It is the top-down stroll map, with the ornament shop stop (gold star, 5) at its new eye.
- `home.jpg`, `street.jpg`, `tree.jpg` and `signpost.jpg` are copied from round 8. The square, town, tree and signpost geometry did not change, so I didn't spend renders on them. The view from the new stop is the carpenter's `stall_schmuck_view.jpg` (review/round-9/carpenter).

## Triangles and sizes (gltf-transform inspect)

| Asset | Triangles | File | Budget |
|---|---|---|---|
| square.glb | 39,282 | 2.19 MB (2,193,480 B) | 40k / 3 MB |
| square.lite.glb | 12,652 | 0.68 MB (675,540 B) | |
| town.glb (unchanged) | 133,979 | 4.41 MB | 150k / 5 MB |
| town.lite.glb | 32,261 | 1.20 MB | |
| tree.glb (unchanged) | 39,944 | 1.05 MB | 40k / 1.5 MB |
| tree.lite.glb | 9,684 | 0.33 MB | |
| signpost.glb (unchanged) | 2,380 | 0.47 MB | 5k / 0.5 MB |

The square files are about 4 KB smaller than in round 8 because they have seven fewer `path_` nodes. Their triangle counts are unchanged.

**Node checks:**

| File | Nodes |
|---|---|
| `square.glb` | 25 `light_`, 49 `bulbs_*` on `bulb_warm`, `snow_ground`, `snow_props`, 100 `path_` |
| `square.lite.glb` | 15 `light_`, 42 `bulbs_`, 100 `path_` |
| `town.glb` | `window_warm`, `snow_roofs`, `snow_skyline` (unchanged) |
| `tree.glb` | `bulbs_` and `snow_` (unchanged) |

## For other roles

- **Engineer:** the `deco-schmuck` stop in `layout.json` `stroll.stops` now matches the shop's 4.3 m `cam_view`. `path_nodes` indices for the loop legs changed with the re-plan, so read them from `layout.json` rather than caching them.
- **Organizer:** no crowd changes needed. The closest standing person on any loop leg is 1.07 m away (`group_lane_right#0`, Karussell → Riesenrad).

## Open issues

- The legs were re-planned rather than patched, so the camera paths differ a little from round 8 even away from the shop (mostly shorter). Every leg passes the check, but the engineer's smoke test should walk the loop once to confirm it feels the same.
- Standing people sit off the stop eyes. The closest standing person on any loop leg is 1.07 m away (Karussell → Riesenrad); that passes the 0.95 m reserve, but not with much to spare.
- Walker paths still cross most legs, as in earlier rounds. Walkers move, so the check only reports them.
- `square.glb`'s `path_` empties were patched in the JSON. If the square is ever rebuilt with `square.py`, it regenerates the same empties from `layout.json`.
