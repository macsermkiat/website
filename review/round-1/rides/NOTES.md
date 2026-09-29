# Ride builder: round 1 notes (pass 2)

## What changed in pass 2

Everything was rebuilt, re-exported and re-rendered on the cloud machine from the current scripts. The pass-2 edits made on the Mac were checked, finished and kept. Each fix below is matched to the judges' notes in `JUDGES.md` and `../CODEX_JUDGE.md`.

**Riesenrad (blocking fixes)**
- **Gondolas swing clear of the wheel steel.** The inner ties, mid ties and X-braces that ran between the rims inside each gondola's swing are gone. The rims are now tied only by the gondola axles themselves and by a tie ring at r = 7.4 m, with X-braces between the two spoke planes. That ring is 3.8 m from the nearest axle, and a gondola swings out to 3.0 m. `blender/rides/check_clash.py` samples every mesh edge every 4 cm and turns the wheel through 360° in 1° steps. It checks three cases: wheel steel against each gondola turning on its axle, gondolas carried round against the static frame, deck, sign and booth, and the wheel's solid of revolution against the static frame. The result is **CLEAR for both full and lite** (303k wheel points and 196k static points on full).
- **Back-stay rods** no longer cross the wheel. They run from the ground beams at |y| = 1.9 m up to the A-frame legs, and the clash test above checks them.
- **The main spokes now meet the inner ring midway between the gondolas**, not at the gondola axles. This change is new in this pass. The engine ride showed a spoke running straight down past the front window of the top gondola, filling the middle of the view (see "Engine check" below). The crossing tension rods now run from each spoke's hub end to the neighbouring spokes. From the square the wheel looks the same. The clash test passes after the change.
- **The ride sees out.** The glass band now runs from 0.52 m to 1.52 m above the cabin floor, up to a thin header under the roof. The door's upper half is glazed as part of that band, and the window posts are slimmer (about 5 cm). `gondola_seat_0` puts a rider leaning at the front pane: the eye is 1.32 m above the floor, 0.20 m below the window head and 0.20 m back from the glass, on the line to the market. From that eye the glass covers +45° to −76° of pitch and ±63° round the pane centre. So the engine's 42° camera sees glass and the market at every point of the ride, including the −41° look down to the market centre from the top. No pitch clamp is needed. It would still help, because the 12 s shot shows the next pane darkening at a grazing angle.
- **Hub:** the sunburst is now a stepped gilt 16-ray star with a raised 8-point star. It has 3 bulbs along each ray (1 in lite), a ring of 24 bulbs outside it, and a gilt domed axle cap ringed with 12 bulbs. The hub drum is dark iron, so it no longer reads as a red disc.
- **New `light_2`** in front of the hub (0, −3.2, 14.7 in Blender). In the engine's cam_view the cream steel read almost black against the sky. This empty lets the engine or lighting designer put a warm wash on the wheel face, the same as the Cycles preview's hub glow.
- The hub was raised to 14.70 m, so the lowest gondola clears the boarding deck by 9 cm. The deck's side rails now stop either side of the gondola's path. A two-step boarding stair leads up to the gondola floor.

**Karussell**
- **Mirrors:** the rounding-board mirrors are bevelled, and they use a warm, slightly rough silvered material (`mirror`: base colour 0.97/0.84/0.64, roughness 0.16). They now show the bulbs' glow instead of black ovals, in both Cycles and the engine (see `engine_lite_view_carousel.jpg`).
- **Name:** "Karussell" in gilt Fraktur sits on a dark green cartouche with a gilt frame, on four sides. It reads from the rail in the engine view.
- **Horses:** these are the second-pass horses with carved muscle (shoulder, forearm, quarters, chest). Each has an open mouth with a dark mouth and teeth, a dropped jaw, knee and hock bulges, and a cut saddle cloth with a scalloped gilt-corded edge instead of the ellipsoid. Horses k and k+6 share a coat and are built in their own frame, so their meshes come out identical. A sculpted master horse is still the next step (see open issues).

**Instruments**
- **instr_sax** has tenor proportions: a 0.64 m straight body, the bell rim at 54% of the body height, a 15 cm bell with a short flare, and the tenor's neck hump. Each key cup has a chimney, a leather pad edge, a cup wall and a flattened dome lying on the body. Hinge rods run on posts along the body. There are low C/E♭ guards, low B/B♭ cups on the bell tube, palm keys, and a thumb rest, thumb hook and strap ring.
- **instr_bass** f-holes are now italic f's. Each has an S stem that swells into wings, with a round upper and lower eye and two nicks at the waist, laid on the arch of the top. Also new in this pass, the body grain is 3× finer: the top read as coarse planks before.
- **instr_piano.lite** keeps its candle flames as `bulbs_piano` with `bulb_warm`.
- **Lite trims:** instr_bass.lite is 34% of full (it was 62%). instr_drums.lite is now 34% (it was 49%), with 10-sided shells, one-band hoops and five-point cymbal profiles.

**Other**
- `blender/rides/rcommon.py` defaults are back to the cloud contract: 1280x720 and 48 samples. The docstring and `check_clash.py` point at `/home/claude/tools/bpy-venv/bin/python`.
- The architect has already changed `layout.json` to `ferris.glb` and `carousel.glb`. Nothing more is needed there.

## Engine check (new this pass)

The page was built with Vite into a scratch folder and served with `vite preview`. I drove it in headless Chromium on SwiftShader through `window.__market`: `openPlace`, `act('ferris'|'carousel', 'ride')` and `advance(1 / 8 / 12)`. The screenshots use the lite market at 1280x720. The site's own panel covers the right third of the frame.

| File | What it shows |
|---|---|
| `engine_lite_ride_ferris_1s.jpg`, `_8s.jpg`, `_12s.jpg` | The Riesenrad ride from `gondola_seat_0`. At 1 s the camera is still easing up from the ground. At 8 s and 12 s the whole square is visible below through the front glass: the bandstand, stalls, strings and town. The gondola's own body is not in view. At 12 s the next pane darkens the right edge at a grazing angle. |
| `engine_lite_ride_carousel_1s.jpg`, `_4s.jpg`, `_8s.jpg` | The carousel ride from `horse_seat_2`: the neighbouring horses, the poles and the market turning past. |
| `engine_lite_view_ferris.jpg`, `_carousel.jpg`, `_band.jpg`, `engine_lite_band_sax.jpg` | The cam_view flights, and the band view with the sax featured. |
| `engine_full_view_ferris.jpg`, `_carousel.jpg`, `_band.jpg` | The same cam_view flights on the full market. The wheel reads as a lattice of lit bulbs, but its steel is still dark: the engine does not light `light_2` yet (see requests). |

Before the spoke change, the 12 s shot had a steel spoke running down the middle of the view. After the change it is gone, and the seat render `ferris_seat.jpg` shows the same thing.

The engine finds every node: `rot_wheel`, `gondola_0..15`, `gondola_seat_0`, `rot_platform`, `horse_0..11`, `horse_seat_2`, the four `slot_*`, and the four `instr_*` placed by `engine/instruments.js`. It reports no warnings.

## Previews (Cycles; 2 threads, OIDN)

- `ferris_preview.jpg`, `carousel_preview.jpg` and `bandstand_preview.jpg`: one night render each at 1280x720, 48 samples.
- `bandstand_stage.jpg` (1280x720, 48 samples): the stage close up, with the four instruments at their slots. The sax is on a render-only stand because no player is holding it.
- `ferris_turned.jpg` (960x540, 32 samples): the wheel turned 90°, with the gondolas hanging upright and clear between the rims.
- `ferris_seat.jpg` (960x540, 24 samples): the view from `gondola_seat_0` at the top of the wheel, with the engine's camera (42° vertical, looking at the market centre). The market in this render is render-only stand-in boxes and light strings.
- `instr_*_preview.jpg` (960x540, 32 samples) and `instruments_contact_sheet.jpg`.

Snow caps are hidden in the renders so the roofs show. The light strings in the Ferris preview are render-only.

## Node contract

These are unchanged from pass 1, except for the new `light_2` on the Riesenrad. Front faces −Y in Blender (+Z in three.js), and every origin is on the ground at the footprint centre.

| File | Nodes |
|---|---|
| ferris | `rot_wheel` at the axle, 14.70 m up. It spins about three.js local Z. Under it are `gondola_0..15`, each at its hanging point on the gondola axle, 11.2 m from the hub, with the pivot as the origin of the gondola's meshes. `gondola_seat_0` is inside `gondola_0`. Also `bulbs_wheel`, `bulbs_g0..15`, `bulbs_base`, `snow_*`, `light_0` (deck), `light_1` (booth), `light_2` (wheel face), `cam_view` and `cam_target`. |
| carousel | `rot_platform` carries the platform, poles, column, rounding board, canopy, `bulbs_carousel`, `snow_canopy` and `horse_0..11`. Each horse sits at mid-travel (1.30 m) and slides along its pole. `horse_seat_2` is in `horse_2`. Also `bulbs_gate`, `light_0/1`, `cam_view` and `cam_target`. |
| bandstand | `slot_sax`, `slot_piano`, `slot_bass` and `slot_drums` on the deck at 0.95 m. Also `light_0/1` (stage wash), `bulbs_bandstand`, `snow_roof`, `cam_view` and `cam_target`. |
| instr_* | Root `instr_<name>` at the player's floor spot. The player faces −Y (+Z in three.js). Also `act_sax`, `act_bass`, `act_brush_l` and `act_brush_r`. `engine/instruments.js` places them at the slots. |

`gltf-transform validate` reports no errors for any of the 14 files. The lite files keep every named node and the `bulb_warm` material.

## Triangles and file sizes (after `blender/lib/optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size | Lite share | Budget |
|---|---|---|---|---|---|---|
| ferris | 67,723 | 1.80 MB | 23,127 | 0.73 MB | 34% | 80k / 3 MB |
| carousel | 79,004 | 1.48 MB | 28,764 | 0.61 MB | 36% | 80k / 3 MB |
| bandstand | 29,730 | 1.12 MB | 10,374 | 0.39 MB | 35% | |
| instr_sax | 6,346 | 0.06 MB | 1,556 | 0.02 MB | 25% | |
| instr_piano | 3,616 | 0.16 MB | 1,524 | 0.07 MB | 42% | |
| instr_bass | 2,910 | 0.14 MB | 984 | 0.06 MB | 34% | |
| instr_drums | 6,136 | 0.17 MB | 2,092 | 0.08 MB | 34% | |
| **bandstand + instruments** | **48,738** | **1.65 MB** | **16,530** | **0.62 MB** | 34% | 50k / 2 MB |

- Desktop first-load share for the rides is about 4.9 MB, and about 2.0 MB for lite.
- The carousel is 1k triangles under its budget. Any new carousel detail has to be paid for elsewhere, and the master-horse idea below would free about 15k.
- Rebuild one script at a time. Each takes 3–6 minutes on the shared machine.
  - `/home/claude/tools/bpy-venv/bin/python blender/rides/<ferris|carousel|bandstand>.py [--no-render]`
  - `.../instruments.py [--only sax,drums]`
  - `.../check_clash.py`. It exits 0 when the wheel is clear.
  - `--preview-only` renders without the bake and export. `NM_POSE=seat|turned` sets the extra Ferris poses. The other flags are `--res`, `--samples`, `--cam x,y,z,tx,ty,tz,lens` and `--preview-name`.
  - bpy can segfault at exit after writing everything. This is harmless.

## Requests to other roles

1. **Engineer (`actions/rides.js`):** the seat now sees out from the bottom to the top of the wheel without help. A pitch clamp of about −35° on the ride look (the target stays the market) would still keep more of the view on the pane centre near the top.
2. **Lighting designer:** please put a warm light at the Riesenrad's `light_2` in the full market, and a ground pool in lite. In the engine's cam_view the wheel's cream steel reads nearly black; only the bulbs show. The carousel's inside (the horses under the canopy) is also very dark from the ride seat in lite. A light under the canopy, attached to the platform, would help. I can add a `light_` empty there if the engine will move it with `rot_platform`. The `glass` material on the gondolas goes dark at grazing angles, which could be toned down.
3. **Organizer:** the sax is modelled in the held pose at `slot_sax`, so it floats when no player stands there. `instruments.sax_on_stand` could be exported as `instr_sax_stand` for a "band on a break" state if you want one.

## Open issues and what I would improve next

- **Horses:** they are still lofted rather than sculpted. A single sculpted master with per-horse paint would give real carving and free about 15k triangles.
- **Riesenrad base:** the booth is still a plank box with a pyramid roof. There are no queue rails, ticket window grille or posters.
- **Gondola interiors:** they have benches, a lamp and door hinges, but no cushions.
- **Piano case:** the walnut grain is at the kit's plank scale and reads coarse up close. The bass got the finer scale this pass.
- **Bandstand garland:** the carpenter's `fir_garland` tufts read a little like holly up close.
- **The ride shots were taken on the lite market only.** Software GL takes about a minute a frame on the full market, so only the three cam_view flights were shot there.
