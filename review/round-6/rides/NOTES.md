# Ride builder: round 6 notes (pass 2)

Pass 2 works through the panel's five fixes for pass 1. Everything ran on the cloud machine (CPU, `NM_THREADS` 2 to 3). ferris, carousel and bandstand were re-exported, full and lite, through `optimize.mjs`. The instruments did not change. `python3 blender/rides/check_rides.py` exits 0. Nothing is committed.

## 1. The Fahrkarten booth: moved, and its sign is lit

- **Where it is now.** Right of the entrance, round the outer rail, at carousel-local (5.0, -5.5). In three.js local terms that is (5.0, 0, 5.5); in the world it is about (20.0, -4.6). The booth is turned −0.54 rad, so its window still faces the stroll stop. It was at (3.1, -6.75).
- **Sightline.** Seen from the stop's eye (three.js local (2, 1.75, 10.5)), the booth roof covers plan angles 50° to 68°. The canopy's edge is at 71° and the platform's edge at 75°, so the booth covers no horse and none of the platform. It sits at the right edge of the stroll frame. `browser_stop_karussell.jpg` shows this in the engine.
- **Clearances.** 1.3 m from the end of walker_6/7's path, 0.3 m from the outer rail, and well clear of the watching children by the entrance.
- **Sign lamps.** Two small brass lamps hang under the eave over the "Fahrkarten" sign. Each has a bracket from the top rail, a shade and a `bulb_warm` bulb in `bulbs_booth`.
- **Ticket lamp.** The old gooseneck over the window crossed in front of the sign. A new gooseneck comes off the right pilaster instead and lights the ticket from the side.
- **No new lights.** No `light_` empties were added (BUILD.md: small glows are emissive).
- **Previews.** The sign reads lit in `carousel_preview.jpg`, and the ticket reads in `carousel_read_contact.jpg`.

## 2. Carousel headroom: normal-mapped horses, bulbs restored

`horse.py` builds one master horse, now made this way:
- **Sculpt.** The sculpt is fused with a fine voxel remesh, the same for both LODs (about 120k triangles). It is then collapsed to a light master: **1,298 triangles full (was 1,998) and 558 lite (was 1,050)**.
- **Normal map.** A Cycles selected-to-active bake carries the carving onto the master as a tangent-space **normal map**: 1024 px full, 512 lite, shared by all six coats.
- **Colour maps.** Each coat is painted on the dense sculpt (coat with belly shading, dapples, blaze, socks, eyes, nostrils, mouth, saddle, cloth, collar) and baked to a **base-colour map**: 512 px full, 256 lite. This keeps eyes and markings sharp, which per-vertex colour cannot do on so few vertices. The masters carry no vertex colours now.
- **Gilt manes.** Gilt manes stay on a gilt material that uses the same normal map.
- **Bake details.** The bake cage starts 3 cm (lite 4 cm) outside the master, so the mane locks that the collapse flattened are still found. Any texel that missed is filled from its neighbours. The collapsed mesh is validated before export, which cleared the glTF exporter's "mesh not valid" warning.
- **Harness.** Full harness 916 → 764 triangles: fewer segments on the stirrups, pommel knob, jewels and medallion. Lite harness 344 → 196: no jewels, a lighter stirrup and medallion, straight reins.
- **Lite cuts elsewhere.** 24 ceiling boards (was 32), 3-sided rail tubes, and fewer boards on the lite booth.
- **Bulbs restored.** The rounding board's pilaster bulbs and both bulb rows are full icospheres in the full file again. That puts back the 2.7k triangles cut in pass 1: bulbs_carousel is 5,440 full.
- **Bytes.** The horse maps add about 0.31 MB to the full file (normal map 67 KB, six coat maps 32 to 38 KB each) and about 0.1 MB to the lite.

| | Pass 1 | Pass 2 |
|---|---|---|
| carousel.glb | 77,114 tris / 0.89 MB | **69,444 / 1.21 MB** (cap 80k / 3 MB) |
| headroom under 80k | 2.9k | **10.6k** |
| carousel.lite.glb | 32,658 / 0.39 MB (42 % of full) | **24,416 / 0.49 MB (35 %)** |

`carousel_horses.jpg` is the close-up from round 2, rendered again. Saddle, flaps, cloth, gilt mane and harness all read. At this distance, about a metre from the nearest horse, the outline of the 1.3k master shows some corners at the neck and hind leg (see open issues).

## 3. write_ names and the wheel

- **Names are agreed.** The engineer has adopted this round's names in `site/src/world/surfaces.js`:
  - the stand-in roles carry aliases: `sheet` ← `music`, `notice` ← `questions_board`, `ticket` ← `contact`;
  - `hangPlacards()` uses the model's `write_question_1..3` when the wheel has them.

  So the engine already finds all six of my surfaces, and the browser shots below show it.
- **What the engine does not do yet:**
  - The placards are still decorative. A click on one reads the noticeboard, and `cam_read_question_N` is never used.
  - Nothing pauses `rot_wheel` (main.js `step()` updates every ride all the time).
- **Suggested patch.** I wrote a three-hunk patch, **`engine_placards.patch`** in this folder, against `site/src` as of 19:54. I did not apply it to `site/src`. It does three things:
  1. A model placard gets a `readView` from its own `cam_read_question_<k>` (world position at fly-in) and `holdsWheel`.
  2. A click on a placard with its own camera reads that placard.
  3. `step()` passes dt 0 to a ride with a wheel while a `holdsWheel` surface is open.
- **Tested in a copy.** I applied the patch to a scratch copy of the site, and that copy took the browser shots. While `ferris.placard_1` was open, `rot_wheel`'s quaternion stayed exactly the same over 3 s of market time, (0, 0, 0.678, 0.735) before and after.
- **Engineer to decide.** The wheel was about 85° round when the placard was read, so the reading camera rode up with gondola_0. If the engineer would rather read the placards only near the ground, the wheel could instead turn on until the gondola is at the bottom, then stop.

## 4. Browser screenshots (six surfaces with text, three ride stops)

`site/src` is still being edited by the engineer, so I left it alone:
- **Setup.** I copied the site to my scratchpad, symlinking `node_modules` and `public`, so the copy uses the delivered glbs. I applied `engine_placards.patch` to the copy and served it with the Vite dev server.
- **Capture.** Playwright drove it on SwiftShader, using the market's own test API (`walkTo`, `read`, `snapshot`), at `?quality=lite&snow=0`. Every place had streamed to full detail before the stop shots.

| Shot | What it shows |
|---|---|
| `browser_read_band_sheet.jpg` | `write_music`: "The Nachtmarkt Quartett" programme on the music stand |
| `browser_read_ferris_notice.jpg` | `write_questions_board`: "View from the top" and the three questions with their notes |
| `browser_read_ferris_placard_0/1/2.jpg` | `write_question_1/2/3` from their `cam_read_question_N` inside the gondolas: "What is a cause?", "Is time something the brain makes?", "Why does improvisation feel inevitable afterwards?" |
| `browser_read_carousel_ticket.jpg` | `write_contact`: "Come round again" with the GitHub links, on the ticket in the booth window |
| `browser_stop_karussell.jpg` | The Karussell stop: the platform and horses unobstructed, the booth at the right edge |
| `browser_stop_riesenrad.jpg` | The Riesenrad stop (the engine's overview from the top gondola) |
| `browser_stop_bandstand.jpg` | The Musikpavillon stop with the band and instruments |

**New this pass: writing margins.** The first shots showed the words running to the very edge of the ticket and the sheet music. `rwrite.surface()` now takes a `margin`:
- The `write_` quad (the writing area, UVs 0–1, as BUILD.md says) is the sheet less the margin all round, raised 0.6 mm over a full-size plain card `card_<name>` of the same paper.
- The margins are ticket 18 mm, music 24 mm, noticeboard 45 mm and placards 25 mm.
- The reading cameras still frame the whole sheet.
- One side effect: while a surface is read, the engine's `readGlow()` lightens only the `write_` mesh, so the writing area shows as a slightly lighter panel on the sheet (see the music and ticket shots). For the engineer: glowing the `card_<name>` sibling too would remove it. Without the margin, the text touches the edge.

## 5. Messages for other roles

- **Architect.** Please re-run `CHECK_ONLY=1 python3 blender/square/stroll.py` with the new booth and noticeboard footprints. The booth moved to carousel-local (5.0, -5.5), 1.3 × 1.05 m plus a 0.18 m roof overhang.
  - **What I already checked.** I ran the same check from a copy of `stroll.py` that writes only to my scratchpad, with the delivered glbs. It found **no stall, ride or furniture failures**. Every leg ending at the Karussell has 0.35 m or more of spare clearance, and the tightest point, (16.0, 5.5), is nowhere near the booth (about (20.0, -4.6)).
  - **What failed.** The 29 failures are all standing people within 0.6 m of a leg: group_square_9 and group_bratwurst_4. Those come from the crowd placement, not the rides.
- **Carpenter and vendor.** A `write_` quad on a material with no texture (the flat `paper_card`) loses its `TEXCOORD_0` in `optimize.mjs`, because `gltf-transform prune` drops the UVs of an untextured material. The engine then cannot place text on it. Give the quad any small texture; mine use `write_card`, a plain 128 px paper map from `art.paper_plain()`. Also: the engine lays text to the edges of the `write_` UV area, so inset the writing area if the sheet should keep a margin.
- **Engineer.** See section 3 and `engine_placards.patch`.

## Triangles and file sizes (after optimize.mjs; `check_rides.py`)

| File | Triangles | MB | Budget |
|---|---|---|---|
| ferris.glb | 72,615 | 1.49 | 80k / 3 MB |
| ferris.lite.glb | 25,003 | 0.73 | (34 %) |
| carousel.glb | 69,444 | 1.21 | 80k / 3 MB (10.6k spare) |
| carousel.lite.glb | 24,416 | 0.49 | (35 %) |
| bandstand.glb | 29,834 | 0.73 | |
| bandstand.lite.glb | 10,398 | 0.30 | |
| instr_sax / .lite | 6,346 / 1,556 | 0.06 / 0.02 | |
| instr_piano / .lite | 3,616 / 1,524 | 0.10 / 0.05 | |
| instr_bass / .lite | 2,994 / 922 | 0.08 / 0.05 | |
| instr_drums / .lite | 6,136 / 2,092 | 0.10 / 0.06 | |
| instr_sax_stand / .lite | 6,600 / 1,690 | 0.07 / 0.03 | |
| **Bandstand + 4 instruments** | **48,926** (lite 16,492) | **1.07** (lite 0.47) | 50k / 2 MB |

The carousel's horses are 12 × (1,298 carved + 764 harness) in full, and 12 × (558 + 196) in lite.

## Previews in this folder

- **Rendered this pass (Cycles):**
  - `carousel_preview.jpg` (1280 × 720, 48 samples): from just behind the Karussell stop, with the booth beside the entrance, its sign lit, and the bulbs restored.
  - `carousel_horses.jpg` (960 × 540, 24 samples): the normal- and colour-mapped horses close up.
  - `carousel_read_contact.jpg` (960 × 540, 24 samples): from `cam_read_contact`, through the window of the moved booth.
- **Browser this pass:** the nine `browser_*.jpg` shots above.
- **From pass 1, still current:**
  - `ferris_preview.jpg` and `bandstand_preview.jpg` (1280 × 720, 48 samples) and `instr_bass_preview.jpg`.
  - The 640 × 360 framing checks `ferris_read_question_2.jpg`, `ferris_read_questions_board.jpg` and `bandstand_read_music.jpg`.
  - The only change to the Riesenrad and bandstand this pass is the writing margin: the paper card under each smaller write_ quad looks the same. To keep within Mac's usage limit I did not re-render them.

## Rebuild

```
NM_ROUND=6 NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/rides/<ferris|carousel|bandstand>.py [--no-render]
NM_READ=contact NM_ROUND=6 .../python blender/rides/carousel.py --preview-only --res 960x540 --samples 24
python3 blender/rides/check_rides.py
```

`NM_ROUND` must be set, or previews go to `review/round-2/rides/`. bpy segfaults at exit (139) after writing everything, which is harmless. A carousel build now takes about 13 s (lite) and 23 s (full) before AO and export, most of it the horse bakes.

## Open issues

- **Horse outline up close.** The 1.3k master's outline shows corners at the neck and hind legs from about a metre away, the ride-seat distance. The shading comes from the normal map, so it no longer looks faceted. With 10.6k spare, the full master could go back up to about 1,600 triangles if the judges prefer that.
- **Engine.** `engine_placards.patch` (placard reading cameras and holding the wheel) is a suggestion, tested only in my copy of the site. Until the engineer adopts it, clicking a placard opens the noticeboard and the wheel never pauses.
- **Read glow.** The writing area shows as a lighter panel while it is being read, because the engine glows only the `write_` mesh (section 4).
- **Ticket stub colour.** In the browser at night the orange stub on the ticket looks grey-blue: the stub is vertex-tinted paper under the engine's moonlight.
- **Architect's check.** The architect's own `stroll.py` check has not been re-run. Mine passed for every footprint, but the crowd groups fail it (section 5).
- **Clash check.** `check_clash.py` was not re-run. The only Riesenrad change is the backing card, which sits where the old write quad was.
