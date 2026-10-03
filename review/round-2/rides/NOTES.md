# Ride builder: round 2 notes

Everything was rebuilt and re-exported on the cloud machine (CPU, `NM_THREADS=2`, load 10 to 15 from other builders) from the current scripts, through `node blender/lib/optimize.mjs` (called by `nmlib.export.export_glb`). Every image in this folder was rendered in this round.

## Round 2 priorities

**1. Re-export with the carpenter's current paint kit (gold metallic 0.5).**
- All 14 files, plus the new `instr_sax_stand`, were exported against kit v11, so the paint band `gold` is half metallic.
- My own `gilt` material (hub star, finials, rounding-board frames, horse harness) was fully metallic too. It went near black in three.js for the same reason. It is now half metallic with a deeper gold base colour (0.90/0.60/0.21, roughness 0.30), matching the carpenter's fix.

**2. Shared kit textures (new, for the download budget).**
- AO now bakes at 768 px (lite 384) for the landmarks and 384 (lite 192) for the instruments. At the old sizes (1024 and 512, the same as the kit maps), the exporter packed AO into each kit roughness map, so every file carried its own copies.
- A new step, `rcommon.share_kit_textures`, moves every kit map out of the glb:
  - A map that is byte-identical to one of the carpenter's `deco_kit_*.webp` / `*.lite.webp` files points at that file, which the market loads anyway. All wood and paint maps matched.
  - The rest go to `rides_kit_<map>_<px>.webp`, one set shared by all ride files: the `rsteel` kit (8 KB) and the 256 px wood maps for the lite instruments (16 KB).
- Result: the three landmarks with the instruments went from 4.93 MB to 3.36 MB (desktop) and from 1.96 MB to 1.47 MB (lite), not counting the shared deco kit files.

## Judges' points (Opus, Fable) and Codex

| Point | What I did | Where to see it |
|---|---|---|
| Carousel: one sculpted master horse shared by the 12 nodes, painted per horse (Opus, Fable) | New `blender/rides/horse.py`. A sculpt source of about 60 overlapping solids, each tagged with a paint region, is fused with a voxel remesh (8.5 mm), smoothed so every joint becomes a soft carved crease, and collapsed to 2,000 triangles (lite 720). The solids are the barrel, neck crest, shoulder, forearm, quarter, gaskin, chest, belly, skull, jowls, brow ridges, flared nostrils, open jaw, legs with knee, hock and fetlock bulges, nine flame locks of mane plus inner locks, a three-strand tail, a carved saddle cloth with a scalloped edge, saddle and breast collar. Each vertex takes the region of the nearest solid. There are six coats: gilt or painted mane and tail, dapples on the grey, a blaze on two, socks on three, a blush on the white muzzle, belly shading, glossy black eyes, a red mouth, and the cloth and collar in the coat's colours. Horses k and k + 6 share one mesh, and the gilt harness (bridle, reins, stirrups, jewels, cloth cord, teeth) is one mesh for all twelve. The glb stores 6 horse meshes for 12 `horse_` nodes. | `carousel_horses.jpg` (close up), `carousel_preview.jpg`, `engine_lite_ride_carousel.jpg` |
| Carousel: light under the canopy that turns with `rot_platform` (Opus, Fable) | `light_2` is a child of `rot_platform`, hung from the sweeps between horse_2 and horse_3 (radius 3.18 m, 3.08 m up). The lighting module adds its lights as children of the empties, so it turns with the horses. Being over 2.8 m on a landmark, it becomes a downward spot. In the lite ride shot the horses round the seat are lit (in round 1 they were near black). I did not isolate whether this light or another one lights them. | `engine_lite_ride_carousel.jpg` |
| Gondola glass dark at grazing angles (Opus, Fable) | The gondolas have their own `gondola_glass`: alpha 0.08 (was 0.22), roughness 0.18 (was 0.04), and a lighter base colour, so two panes behind each other no longer stack into a dark band. The booth keeps the kit `glass`. | `engine_lite_ride_ferris.jpg` (from the top: no dark pane) |
| Double bass reads as a gourd; f-hole eyes and nicks (Opus) | The outline is now three smooth runs joined at four sharp corners: a full lower bout (0.69 m), real C-bouts (waist 0.37 m), an upper bout (0.54 m) with the viol's curved sloping shoulders, and a body 1.11 m long. The inner arching rings are softened toward the corners, so the top flattens out there instead of creasing. The f-holes, their round eyes (the lower one 3.1 cm across) and the nicks (1.3 cm) are laid on the top by ray casts against the loft's own surface. Before, the lower eye sat 7 mm under the arched top, which is why it could not be seen. | `instr_bass_preview.jpg`, `instr_bass_close.jpg` |
| Sax floats when no player holds it (Opus) | New `instr_sax_stand.glb` (and `.lite`): the tenor standing on its floor stand, root `instr_sax_stand` with the same origin as `instr_sax`, for a "band on a break" state. The organizer's sax player now stands at the slot in the engine, so the held sax does not float there today. | `instr_sax_stand_preview.jpg`, `bandstand_stage.jpg` |
| Longer tenor body (Fable) | The body, bow and bell tube are 10 % longer (a 0.70 m straight body), done as a warp in the sax's build frame, so every key cup moves with the body. The neck and mouthpiece move up with it, and the mouthpiece stays at the player's mouth. | `instr_sax_preview.jpg` |
| Riesenrad booth: queue rails, window grille, posters (Opus, Fable) | The ticket window has 13 iron bars, an arched crown, a brass speaking ring and a brass money dish on the sill. Two posters are drawn in code (`blender/rides/art.py`, Pillow, aged paper, a torn corner): "Riesenrad" with the wheel at night, and "Nachtmarkt" with a lit tree. There is a painted "Fahrpreise" price board under the window. Red steel queue rails with gilt knobs make a lane from the entrance sign out 3.9 m toward the square, and a rail keeps the ticket queue along the booth front. | `ferris_booth.jpg`, `ferris_preview.jpg` |
| Piano walnut too coarse, drum shells read as barrel staves (Opus) | Instrument wood repeats the kit 3.3x finer (`FinePart`). The drum shells use a veneer part whose grain runs round the shell. | `instr_piano_preview.jpg`, `instr_drums_preview.jpg` |
| My own open issue: bandstand garland read as holly | New `rcommon.needle_garland`: rope with needle sprigs (three thin cones each, some lighter new tips), and few, larger glass baubles every 0.62 m instead of many small beads. It uses fewer triangles than before. | `bandstand_preview.jpg` |
| Bandstand stage looked empty | A worn oriental rug under the drum kit (a drawn texture on 2 triangles) and a music stand with two sheets beside the sax slot. | `bandstand_stage.jpg`, `engine_lite_view_band.jpg` |
| Codex: download budgets | See the shared kit textures above: the rides now take 1.57 MB less on desktop and 0.49 MB less on lite. | table below |
| Wheel steel reads black in the engine (Opus, Fable: lighting designer / engineer) | Not mine to fix. `light_2` in front of the hub is still there. In `engine_lite_view_ferris.jpg` the steel is still dark and only the bulbs read. | request 1 |

## Node contract (unchanged except where marked)

Front faces −Y in Blender (+Z in three.js), and every origin is on the ground at the footprint centre.

| File | Nodes |
|---|---|
| ferris | `rot_wheel` at the axle, 14.70 m up. It spins about three.js local Z. Under it are `gondola_0..15`, each at its hanging point on the gondola axle, 11.2 m from the hub, with the pivot as the origin of its meshes. `gondola_seat_0` is inside `gondola_0`. Also `bulbs_*`, `snow_*`, `light_0/1/2`, `cam_view` and `cam_target`. |
| carousel | `rot_platform` carries `horse_0..11`: each horse sits at mid-travel (1.30 m), and its meshes (`h<k>_carved`, `h<k>_gilt`, `h<k>_teeth`) are children at identity. It also carries `horse_seat_2` in `horse_2`, **`light_2` (new, canopy light)**, `bulbs_carousel` and `snow_canopy`. Also `bulbs_gate`, `light_0/1`, `cam_view` and `cam_target`. |
| bandstand | `slot_sax`, `slot_piano`, `slot_bass` and `slot_drums` on the deck at 0.95 m, each rotated to face its player. Also `light_0/1`, `bulbs_bandstand`, `snow_roof`, `cam_view` and `cam_target`. |
| instr_* | Root `instr_<name>` at the player's floor spot, with the player facing −Y. Also `act_sax`, `act_bass`, `act_brush_l` and `act_brush_r`. **New: `instr_sax_stand`** (root only, no act_ node). |

`gltf-transform validate` reports no errors for any of the 16 files. The external URIs resolve (the engine loaded all of them in the lite shots with no console errors).

## Triangles and file sizes (after `optimize.mjs`, glb only; shared kit maps listed below)

| File | Triangles | Size | Lite triangles | Lite size | Lite share | Budget |
|---|---|---|---|---|---|---|
| ferris | 70,761 | 1.41 MB (was 1.82) | 24,529 | 0.66 MB (was 0.73) | 35 % | 80k / 3 MB |
| carousel | 78,608 | 0.90 MB (was 1.48) | 29,496 | 0.35 MB (was 0.61) | 38 % | 80k / 3 MB |
| bandstand | 29,384 | 0.72 MB (was 1.12) | 10,154 | 0.29 MB | 35 % | |
| instr_sax | 6,346 | 0.06 MB | 1,556 | 0.02 MB | 25 % | |
| instr_piano | 3,616 | 0.10 MB | 1,524 | 0.05 MB | 42 % | |
| instr_bass | 2,674 | 0.07 MB | 874 | 0.04 MB | 33 % | |
| instr_drums | 6,136 | 0.10 MB | 2,092 | 0.06 MB | 34 % | |
| **bandstand + 4 instruments** | **48,156** | **1.05 MB** | **16,200** | **0.46 MB** | 34 % | 50k / 2 MB |
| instr_sax_stand (alternative to instr_sax, not loaded by default) | 6,600 | 0.07 MB | 1,690 | 0.03 MB | | |

- **Shared files:**
  - `rides_kit_rsteel_{color,normal,rm}_512.webp`: 8 KB, used by all three landmarks, full and lite.
  - `rides_kit_wood_*_256.webp`: 16 KB, lite instruments.
  - The wood and paint maps are the carpenter's `deco_kit_*` files.
- **Each horse** costs 2,000 carved triangles plus 940 of harness (old horse: 2,971). So the carousel's triangle count held, but its file shrank by 40 %: 6 coat meshes and one harness serve 12 horses.
- **The engineer's `npm run budget`** shows "bandstand 66.8k / 1.97 MB, over 50k / 2 MB". That line also counts the organizer's four `people_band_*` players (about 18.7k triangles). BUILD.md budgets those as person variants (5k each), and it counts the shared deco kit maps again. My part of that line (bandstand plus instruments) is 48.2k and 1.05 MB.

## Previews in this folder

- Cycles, 1280x720, 48 samples, OIDN:
  - `ferris_preview.jpg`, `carousel_preview.jpg` and `bandstand_preview.jpg`: the three night renders.
  - `bandstand_stage.jpg` (40 samples): the stage close up, with the four instruments at their slots. The sax is on its stand, as in the preview no player holds it.
- Cycles, 960x540, 32 samples:
  - `carousel_horses.jpg`: the sculpted master horse, near the front of the platform.
  - `ferris_booth.jpg`: booth grille, posters, price board and queue rails.
  - `instr_*_preview.jpg`, `instr_bass_close.jpg`, and `instruments_contact_sheet.jpg` (all six in one sheet).
- Engine, lite market, 1280x720, SwiftShader, from a scratch `vite build`, driven through `window.__market` (the site's panel covers the right third):
  - `engine_lite_view_ferris.jpg`, `engine_lite_view_carousel.jpg` and `engine_lite_view_band.jpg`: cam_view flights.
  - `engine_lite_ride_carousel.jpg`: 4 s into the ride from `horse_seat_2`.
  - `engine_lite_ride_ferris.jpg`: the view from the top.
- Snow caps are hidden in the Cycles renders so the roofs show. The light strings and poles in the Ferris preview are render-only.

## Rebuild

- `NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/rides/<ferris|carousel|bandstand>.py [--no-render] [--no-lite]` takes 3 to 5 min on the loaded machine, plus about 4 min for the 1280x720 render.
- `.../instruments.py [--only sax,piano,bass,drums,sax_stand]`.
- `--preview-only` renders without the bake and export. Pass `--cam=x,y,z,tx,ty,tz,lens` with `=` because of the leading minus sign. Other flags: `--res`, `--samples`, `--preview-name`.
- Previews go to `review/round-$NM_ROUND/rides/` (default 2).
- The posters and the rug are drawn at build time into `blender/out/rides_art/`, which is gitignored.
- bpy segfaults at exit (code 139) after writing everything. This is harmless.

## Requests to other roles

1. **Lighting designer:** the Riesenrad's cream steel is still near black in the engine (`engine_lite_view_ferris.jpg`). Please put a warm wash at `light_2` in front of the hub on full, and a ground pool or a low-cost fill on lite. This is the landmark's biggest gap between Cycles and the browser.
2. **Engineer:**
   - `instr_sax_stand.glb` exists for when no sax player stands at `slot_sax` (same slot, same origin).
   - A pitch clamp of about −35° on the Riesenrad ride look would still help near the top, but the softer glass removes the dark pane without it.
   - `scripts/budget.mjs` counts the band players in the bandstand line (see above).
3. **Organizer:** the tenor body is 10 % longer, and the mouthpiece is where it was. Relative to the mouthpiece, the right-hand keys moved down about 4 cm and the left-hand keys about 2 cm. Check the sax player's hands if they were fitted to round 1.
4. **Market owner:** new file prefix `rides_kit_*` in `site/public/models/`, for shared ride textures. The ride files also reference the carpenter's `deco_kit_*` maps by URI, so those files must stay, and stay byte-stable, while the rides use them. `share_kit_textures` falls back to its own files when they differ.

## Open issues and what I would improve next

- **Lite horses** are 720 carved triangles and look faceted from the ride seat (`engine_lite_ride_carousel.jpg`). 1,000 would be smoother, but the lite carousel is already 38 % of full.
- **The carousel is 1.4k under its 80k cap.** The master horse gave carving, not triangle savings. A normal map baked from the 58k-quad sculpt onto a 1.4k master would free about 8k triangles and keep the carving.
- **Saddle:** it is still a smooth leather blob with a cantle and pommel. It needs a seat dip, skirt and stitching.
- **Booth "Kasse" sign** is in shadow under the eave in Cycles. The price board is legible.
- **Music stand** at the sax partly covers the saxophonist from the default band view (`engine_lite_view_band.jpg`). It could move 20 cm further to the player's right.
- **Instruments + players over the engineer's 50k line.** The sax (6.3k) and drums (6.1k) could lose about 1.5k each, but the key work and hardware the judges look for are where the triangles are.
- **The full-market engine shots were not retaken this round.** Software GL is too slow on the loaded machine, so only lite was shot.
