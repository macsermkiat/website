# Carpenter: round 2 notes

Built on the cloud machine (CPU, `NM_THREADS=2`–3, load 10–18 from other builders). Every glb, kit texture, Cycles preview and three.js shot in this folder was regenerated in this round from the current scripts. The machine restarted after the Cycles previews were written and before the three.js shots were taken; after the restart I checked every glb again (`glb_tools.check`, node names, materials), took all the three.js shots, and rebuilt the Bratwurst (sign-spot preview) and the Bücherstand (cabinet books) once more.

## What changed in round 2

| Point (source) | What I did | How to check |
|---|---|---|
| Remove the Bratwurst's built-in grill (round 2 priority 2) | The firebox trough, rolled rim, apron, legs, draught door, rivet rows, hearth plate and ash are gone. The counter now runs the full width. The hood, stovepipe and the opening under the hood stay. The counter under the hood is scorched and ash-ringed (vertex shade `scorch_shade`) around the vendor's fire bowl (x −0.9 from `slot_counter`). New empty `slot_grill` on the counter top under the hood centre marks where the grill stands; the clear height to the hood skirt is 0.71 m. | `stall_bratwurst_preview.jpg` (with the vendor's current `prop_wurst_counter`), `stall_bratwurst_threejs.jpg` (bare glb: no grill at all), `stall_bratwurst_threejs_props.jpg` |
| Bratwurst hood reads clean and light (Opus) | `hood_shade`: soot is heaviest on the skirt and lip (0.38) and lightens up the hood, with a heat-blued band and a straw band just above the skirt seam and soft smoke streaks. `iron_matte` is darker (colour gain 1.7, was 2.1) and its emissive stand-in is lower (0.12/0.08/0.045, was 0.2/0.14/0.08). Cycles previews now switch every emissive stand-in off (`mats.standin_emission(False)`), so the preview hood is soot-black iron. | `stall_bratwurst_preview.jpg` (black sooty hood), `stall_bratwurst_threejs.jpg` (hood still readable) |
| `iron_matte` had no occlusion texture (Opus, Fable) | Root cause: `bake.ao_targets` only took the base kit keys (`wood oak paint iron`), so kit variants and patterns were never AO-baked. It now takes every kit key, kit variant and pattern. The decoded `stall_bratwurst.glb` shows `iron_matte occlusionTexture = stall_bratwurst_ao`, and `rauten` and `paint_glow` have AO too. | `python3 blender/lib/glb_tools.py report site/public/models/stall_bratwurst.glb`, or the material dump below |
| Glühwein red-and-gold trim goes black in the browser (Opus) | New kit variant `paint_glow`: the paint atlas plus a faint warm emissive copy of it (0.13/0.09/0.07), with the shared paint colour map as the emissive texture, so it costs no texture bytes. The bargeboards (new `Hut.build_roof(barge_part=)`), the carved rake scallops, the scalloped lambrequin with its star cut-outs, the gable star board, the gold strips and the finial now use it. The star cut-outs are larger (radius 5.6 cm). | `stall_gluehwein_threejs.jpg`: the red gable, bargeboards and scalloped valance with stars read as red and gold. The Cycles preview has the stand-in switched off. |
| Bier pennant Rauten must read in three.js (priority 1) | Rauten pattern p2: a deeper Bavarian blue (sRGB about 12/105/188, was 30/140/215) and a nearly neutral emissive stand-in (0.22/0.20/0.17, was a warm 0.26/0.21/0.15 that turned the blue grey). There are still four large lozenges per 0.26 m repeat. | `stall_bier_threejs.jpg` (blue-and-white lozenges on every pennant, the fascia, the strip under the sign and both flags), `stall_bier_threejs_home.jpg` |
| Bier sign low contrast (Fable) | A warm cream board, with the Fraktur letters in the blue band darkened to deep navy by their tint, no letter bevel. | `stall_bier_threejs.jpg` |
| Bier headroom (Opus, Fable) | Barrel front 9 staves x 7 rings (was 11 x 9), the garland 34 tufts/m with baubles every 0.28 m. The stall went from 43,429 to 39,745 triangles. | table below |
| Bücher copper roof flat salmon in three.js (Fable) | New kit variant `copper_old`: the iron kit's dents, streaks and pitting with a copper-brown colour (its own 10 KB shared colour file), metal x0.6. It replaces the flat `copper` on the bay roof. | `stall_buecher_threejs.jpg`: dark, dented old copper |
| Bücher glazed cabinets empty (Opus) | Low-poly book spines (new simple material `bookcloth`, coloured by vertex tint, underside and back faces dropped, about 10 tris a book) fill the upper three shelves of both cabinets, with a lying stack at each end of the bottom shelf. The middle of the bottom shelf stays free at `slot_cabinet_l/r`. A small warm bulb under each cabinet top lights the spines. The glass alpha went from 0.22 to 0.14. The first cloth colours were too dark to read behind the glass (no engine light reaches inside the cabinet), so the binding tints are now about 1.6x lighter, and the Cycles preview lights each cabinet from its bulb. | `stall_buecher_preview.jpg`, `stall_buecher_threejs.jpg`: red, green, blue and ochre spines behind the glazing bars |
| Holzspielzeug sign board darker (priority 3) | The board is the blue band tinted to a deep navy (`board_tint` 0.36/0.40/0.52); the letters stay cream. | `deco_contact_sheet.jpg` |
| Bratwurst sign lamps lit the roof snow (Opus) | The lamp heads hang only 0.3 m in front of the board, so the first 62° cones still left a bright oval on the snow under the sign. The preview spots are now 38° (blend 0.35), aimed at the upper half of the board, so the lower cone edge ends at the board's foot. | `stall_bratwurst_preview.jpg`: the board is lit and the snow under it is not |
| Snow on straight roofs looked ruled (Opus, optional) | `snow_cap(drifts=n)`: lumpy mounds slid down against the eave lip, 80 tris each. Each section stall has 3 per slope. | eaves in `stall_bier_preview.jpg`, `stall_buecher_preview.jpg`, `stall_bratwurst_preview.jpg` |
| Bratwurst board-roof snow, no black dashes (priority 1) | Unchanged from round 1 pass 3: the snow drapes over each batten as one continuous ridge. I checked it again in the new preview. | `stall_bratwurst_preview.jpg` |
| Deco AO packing (priority 1) | Unchanged and checked: deco AO bakes at 448 px (lite 256), so no kit roughness map gets packed. Every deco glb embeds only its own AO image (28–35 KB, lite 12–13 KB) and references all kit maps by URI. | `glb_tools.py report deco_*.glb` |
| CREDITS fonts (priority 1) | I checked each sign's font against `CREDITS.md`: UnifrakturCook (Glühwein, Bier vom Fass, Lebkuchen, Käse), IM Fell English Italic (Bücher, Kerzen, Crêpes), Alegreya SC (Bratwurst, Gebrannte Mandeln, Holzspielzeug, Christbaumschmuck, Heiße Maroni, Kartoffelpuffer). Round 2 adds no third-party assets. | `CREDITS.md`, carpenter section |
| Web step (priority 4) | Every export goes through `node blender/lib/optimize.mjs raw.glb out.glb --texture-size N` (`export.export_glb`); nothing calls `gltf-transform optimize`. `gltf-transform validate` reports no errors. | `blender/lib/nmlib/export.py` |
| Previews show the real goods | The four section previews now import the vendor's shipped prop glbs at their slots (`pipeline.vendor_props`) instead of my render-only stand-in mugs, glasses and books. The stand-ins remain only as a fallback when a prop file is missing. | all four `*_preview.jpg` |

## Triangles and file sizes (measured on `site/public/models` after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size | Lite / full |
|---|---|---|---|---|---|
| stall_gluehwein | 37,603 | 0.94 MB | 8,066 | 0.21 MB | 21 % |
| stall_bratwurst | 36,391 | 0.86 MB | 7,467 | 0.21 MB | 21 % |
| stall_bier | 39,745 | 1.01 MB | 9,641 | 0.26 MB | 24 % |
| stall_buecher | 34,583 | 0.94 MB | 7,209 | 0.20 MB | 21 % |
| deco_lebkuchen | 13,433 | 0.38 MB | 3,986 | 0.13 MB | 30 % |
| deco_mandeln | 15,985 | 0.41 MB | 4,653 | 0.13 MB | 29 % |
| deco_kerzen | 14,143 | 0.39 MB | 4,046 | 0.13 MB | 29 % |
| deco_spielzeug | 15,938 | 0.42 MB | 5,041 | 0.15 MB | 32 % |
| deco_schmuck | 15,799 | 0.42 MB | 4,315 | 0.13 MB | 27 % |
| deco_kaese | 13,380 | 0.36 MB | 4,354 | 0.13 MB | 33 % |
| deco_crepes | 13,283 | 0.37 MB | 3,699 | 0.12 MB | 28 % |
| deco_maroni | 14,346 | 0.37 MB | 4,949 | 0.14 MB | 34 % |
| deco_puffer | 14,978 | 0.40 MB | 4,519 | 0.14 MB | 30 % |
| shared kit `deco_kit_*.webp` (all 13 stalls; new `copper_old` colour) | | 0.46 MB | | 0.20 MB (`*.lite.webp`) | |

- **Deco stalls are 0.9–1.5k lighter than round 1** (bigger deco shingles 0.29 x 0.20 m, and lighter interior bulbs on every stall), which gives the vendor more room.
- **With the vendor's props as they are on disk now** (the vendor is rebuilding this round, so these move):
  - Glühwein 37,603 + 18,972 = 56.6k (3.4k headroom).
  - Bier 39,745 + 17,600 = 57.3k (2.7k).
  - Bratwurst 36,391 + 20,646 = 57.0k (3.0k).
  - Bücher 34,583 + 4,822 = 39.4k.
  - Deco stall plus goods: Lebkuchen 18.5k, Mandeln 18.8k, Kerzen 17.5k, Spielzeug 19.0k, Schmuck 18.9k, Käse 17.5k, Crêpes 16.4k, Maroni 19.5k, Puffer 18.9k.

  Everything is under 60k / 3 MB and 20k / 1 MB. I cut Bier by 3.7k this round, and the vendor's new sets took that room.
- **Proposed split (market owner / vendor):** section stall at most 40k and its props at most 20k; deco stall at most 16k and its goods at most 4k. My stalls meet it (the largest section stall is 39.7k, the largest deco stall 16.0k). The vendor's current Bratwurst set (20.6k), Maroni goods (5.2k) and Lebkuchen goods (5.1k) are over their share, but the totals still fit.
- **First-load share for my 13 stalls:** 7.7 MB desktop (7.26 MB of glb + 0.46 MB kit) and 2.3 MB lite (2.08 + 0.20).
- **Texture sharing:** every glb embeds only its own AO atlas (section 70–96 KB at 768 px; deco 28–35 KB at 448 px), plus the 6 KB Rauten pattern in the two Bier files. All kit maps, including the variants' colour files (`deco_kit_iron_matte_color.webp`, `deco_kit_copper_old_color.webp`), are referenced by URI.
- **Contract checks:** `glb_tools.check` passes on all 26 files. Each has `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `light_*` (2 per section stall, 1 per deco stall), `bulbs_*`, `snow_*`, `cam_view`, `cam_target` and material `bulb_warm`. `slot_counter` is at 1.050 m in every file, and the counter top faces are exactly 1.05 m.
- **Materials with occlusion:** wood, oak, paint, iron, `iron_matte`, `paint_glow`, `copper_old` and `rauten` all ship an `occlusionTexture` (TEXCOORD_1).
- **Sign text (3D letters):** Glühwein, Bratwurst, Bier vom Fass, Bücher, Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer.

## Previews in this folder

- `stall_*_preview.jpg`: Cycles, 1280x720, 48 samples, OIDN, 3/4 front view at night, with the vendor's shipped props at their slots and the emissive stand-ins switched off.
- `deco_contact_sheet.jpg`: the nine deco stalls (structures only, 840x600 tiles, 48 samples).
- `stall_*_threejs.jpg`: the bare shipped glbs in three.js under the current `site/src/lighting` (SwiftShader, AO on, snow off as on the site), same camera as the Cycles preview. The lighting module now adds its own sign lamp over every `slot_sign`, so my round-1 sign-spot request is covered.
- `stall_bratwurst_threejs_props.jpg`: the Bratwurst glb with `prop_wurst_counter` attached.
- `stall_bier_threejs_pennants.jpg`: a x2 crop of the eave in `stall_bier_threejs.jpg` (same pixels, enlarged): every pennant carries blue-and-white Rauten.
- `stall_bier_threejs_home.jpg`: the Bierstand where `layout.json` places it, seen from the site's home camera, with a x3 inset of the same pixels. At that distance a pennant is about 5 px wide and the Rauten merge into a pale blue-and-white fringe; they resolve from lane and preview distance.
- `shoot.mjs` writes raw PNGs to `review/round-2/carpenter/web/`; I removed them after converting to JPEG, as BUILD.md asks for JPEG previews.

## Rebuild

`NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/stalls/<stall>.py [--no-render] [--no-lite] [--samples N] [--res WxH]`, and `.../deco.py [--only kaese,crepes] [--no-render]`. Previews go to `review/round-$NM_ROUND/carpenter/` (default 2). On the loaded machine a stall takes about 2 min to build, AO-bake and export both LODs, and 10–14 min to render. The nine deco builds and renders take about 65 min. bpy segfaults at exit (code 139) after writing everything; this is harmless. Three.js shots: `node blender/stalls/web/shoot.mjs --ao on [--only ...] [--props prop@slot] [--home] [--tag t]`. My shot server now uses port 4397 (`NM_SHOT_PORT`), because the lighting designer's tools use 4395.

## Notes for other roles and the market owner

1. **Vendor (Bratwurst):** the stall has no firebox, grate, hearth plate or coals any more. The counter top is flat oak at 1.05 m across the whole width, and your grill stands on it. `slot_grill` is at x −0.9 on the counter top under the hood centre (the hood spans x −1.83..−0.07 and its skirt is 0.71 m above the counter). The hearth plate your round-1 bowl sat on (2.6 cm up) is gone, so set the bowl's feet on the counter (GZ = 0). The warming tray and the rest of the counter set are unaffected.
2. **Vendor (Bücher):** the cabinets now hold their own book spines on the upper three shelves. The middle of each bottom shelf is still free at `slot_cabinet_l/r` if you want a feature book there. These spines are scenery (no `act_book_` nodes).
3. **Lighting designer:** three materials carry a faint emissive stand-in for light the engine does not cast: `rauten`, `iron_matte` and the new `paint_glow` (Glühwein outward trim). They are listed in `mats.STANDIN_EMIT`. If the bulbs ever light nearby surfaces, lower their `emissiveFactor` (one line each in `mats.KIT_VARIANTS` / `mats.PATTERNS`). Your new sign lamp works well on the cream boards. The Glühwein board is close to clipping under it at the preview distance.
4. **Codex judge, Bücher third light:** the stall has exactly two `light_` empties. The third light came from a `light_lamp` in the vendor's round-1 `prop_books_counter`, and the current prop has none (checked).
5. **Market owner:** BUILD.md now names `optimize.mjs` as the web step, which closes my round-1 request. New optional nodes: `slot_grill` (Bratwurst). `smoke_origin` (Bratwurst) and `slot_cabinet_l/r` (Bücher) are unchanged.
6. **Ride builder / architect (library users):** `nmlib` gained, without changing any existing name or default:
   - `mats.KIT_VARIANTS` entries `paint_glow` and `copper_old`, and a `tint=` option for variants;
   - `mats.standin_emission(on)`;
   - the simple material `bookcloth`;
   - `snow_cap(drifts=)`;
   - `Hut.build_roof(barge_part=)` and `Hut.build_counter(extra_shade=)`;
   - `pipeline.vendor_props`.

   `bake.ao_targets` now also bakes kit variants and patterns. The simple `glass` alpha is 0.14 (was 0.22). See `blender/lib/README.md`.
7. Footprints are unchanged: Glühwein 3.4 x 2.5 m; Bratwurst 3.9 x 2.5 m plus a 0.8 m lean-to on +X; Bier 4.2 x 2.6 m; Bücher 3.7 x 2.5 m plus a 0.35 m bay on −X; deco stalls 2.6–3.4 x 2.2 m.

## Open issues and what I would improve next

- **Section headroom depends on the vendor's growth.** At 2.7–3.4k it is tight again because the props grew this round. The split proposed above would settle it. My next cuts would be the eave bulb detail (7x5 → 6x4, about 600 tris a stall) and the fir garland tufts.
- **Emissive stand-ins are a workaround.** They keep trim, pennants and hood readable under moonlight, but a lighting pass that lights the eaves (or a baked lightmap) would let me drop them.
- **Glühwein sign under the site's new sign lamp** is bright at close range. That is a lighting setting, so I left the board colour alone.
- **Rauten at the home view.** From the home camera a pennant is about 5 px wide, so the lozenges merge into a pale blue-and-white fringe (`stall_bier_threejs_home.jpg`). Fewer, bigger lozenges would read from further away but would no longer look like real Rauten, so I kept four per repeat.
- **Cabinet books have no titles.** They are coloured spines only; the vendor's clickable books stay on the back shelves and counter.
- **Bevel cost:** chamfers are still real geometry. A baked edge-normal trim sheet could halve the wall triangles.
- **Scorch under the grill** is vertex shading on the counter's wear grid, so it is soft. A decal would be crisper.
