# Carpenter: round 1 notes (pass 3)

Pass 3 was built on the cloud machine (CPU, `NM_THREADS=2`, load 5–17 from other builders). Every glb, kit texture, Cycles preview and three.js shot in this folder was regenerated in this pass from the current scripts. The partial pass-3 edits left from the earlier session were finished, rebuilt and checked; nothing here is an older export.

## What changed in pass 3 (judge fixes)

| Judge fix | What I did | How to check |
|---|---|---|
| Bier pennants mip to pale blue-white in three.js | New dedicated `rauten` pattern material (`mats.PATTERNS`): a 256 px two-colour texture, 4 big lozenges per 0.26 m repeat (3–4 across each pennant), a lighter Bavarian blue (sRGB about 30/140/215) and a warm white. It carries a faint emissive copy of the pattern that stands in for the eave bulbs hanging right beside the pennants, so the pattern holds under hemisphere light alone. The pennants are 12 mm thick (lit faces on both sides, material double-sided) and tilted 0.22 rad so they face slightly up into the sky fill and the bulbs. The fascia board, the strip under the crest sign and the two roof flags use the same material. It is embedded in the Bier glb (6 KB). | `stall_bier_threejs.jpg` (preview distance: lozenges resolve). `stall_bier_threejs_home.jpg` (home view, with a x3 inset of the stall: the eave reads as a blue-and-white fringe; single lozenges are only 1–2 px there). `stall_bier_preview.jpg` |
| Bratwurst board-roof snow shows black batten dashes | `snow_cap(ridges=...)`: `board_roof` returns its battens, and the snow drapes over each batten as one continuous soft ridge running the full length of the slope (at least 6 mm of snow over the batten top, easing back to the normal depth over 7 cm). The snow grid gets columns on each batten's flanks and crest, so no batten pokes through anywhere. | `stall_bratwurst_preview.jpg`: soft continuous ridges, no dashes |
| Sign legibility in the engine | Model-side fallback, which works with no extra light: Glühwein is now a cream board with red Fraktur letters and a gold frame (was red with gold letters). Bratwurst is a black board with cream letters on its own un-sooted Part. Holzspielzeug is a blue board with cream letters (was blue on white). I also checked the proposed `slot_sign` spot (`shoot.mjs --signspot`: a small warm unshadowed spot 0.9 m out and 0.45 m up, aimed at `slot_sign`). | Without the spot: `stall_gluehwein_threejs.jpg`, `stall_bratwurst_threejs.jpg` (both signs read). With the spot: `*_threejs_signspot.jpg`. Holzspielzeug: `deco_contact_sheet.jpg` |
| Bratwurst hood and firebox go black in the browser | New kit variant `iron_matte` (`mats.KIT_VARIANTS`) for the firebox and hood only: its own lighter base colour (the iron colour x2.1 in linear light, mean about 120/255 instead of 84; shared file `deco_kit_iron_matte_color.webp`, 12 KB), metal x0.35 as `metallicFactor`, and a faint warm emissive copy of that colour (factor 0.2/0.14/0.08). The emissive stands in for the bulbs and the fire beside the hood, because no site light reaches a hood face that looks up and out under the eave. The hood soot is lighter (0.8–1.0). The stovepipe, rain cap and struts stay on plain forged iron, so nothing glows against the sky. | `stall_bratwurst_threejs.jpg`: the rivets, rust and seams read on the hood and firebox |
| Deco kit sharing (iron ORM) | Deco AO is baked at 448 px (lite 256), a size no kit map has, so the exporter never packs AO into iron roughness/metal. | Every deco glb embeds only its own AO image (28–35 KB, lite 12–13 KB) and references `deco_kit_iron_rm.webp` by URI. Listing below. |
| CREDITS.md fonts | Carpenter section corrected: UnifrakturCook (Glühwein, Bier vom Fass, Lebkuchen, Käse), IM Fell English Italic (Bücher, Kerzen, Crêpes), Alegreya SC (Bratwurst, Gebrannte Mandeln, Holzspielzeug, Christbaumschmuck, Heiße Maroni, Kartoffelpuffer). UnifrakturMaguntia and IM Fell English SC are listed separately as bundled for other builders but unused by any sign. | `CREDITS.md` |
| README header still gives the MacBook run line | The header now gives the cloud command (`NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python ...`), the render sizes and the segfault-at-exit note. It also documents `iron_matte`, the `rauten` pattern, `snow_cap(ridges=)`, the AO sizes that keep kit maps shareable, and the new `shoot.mjs` options. | `blender/lib/README.md` |
| Bratwurst grill vs `prop_wurst_counter` | Settled as the vendor's notes describe. The vendor's Schwenkgrill (fire bowl, coals, swinging grate) ships. My firebox has **no grate and no coals**, only a hearth plate 2.6 cm above the counter where the bowl stands, with temper colours around it and ash kept clear of the bowl. | `stall_bratwurst_threejs_props.jpg` (the glb with `prop_wurst_counter` at `slot_counter`: one bowl, one grate, no doubling or z-fighting). The Cycles preview imports the same vendor glb. |
| Glühwein triangle headroom | The Fraktur sign has no letter bevel (resolution 1), and the garland tufts are capped at 38/m. The stall went from 41,129 to 37,687 triangles. With the vendor's 16,816 it is 54,503 of 60,000, leaving 5.5k headroom. | table below |

## Triangles and file sizes (measured on `site/public/models` after `blender/lib/optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size | Lite / full |
|---|---|---|---|---|---|
| stall_gluehwein | 37,687 | 0.94 MB | 8,462 | 0.21 MB | 22 % |
| stall_bratwurst | 37,715 | 0.88 MB | 7,783 | 0.22 MB | 20 % |
| stall_bier | 43,429 | 1.07 MB | 10,181 | 0.26 MB | 23 % |
| stall_buecher | 33,567 | 0.93 MB | 6,609 | 0.19 MB | 19 % |
| deco_lebkuchen | 14,277 | 0.40 MB | 4,274 | 0.13 MB | 29 % |
| deco_mandeln | 16,817 | 0.43 MB | 4,941 | 0.13 MB | 29 % |
| deco_kerzen | 14,959 | 0.41 MB | 4,334 | 0.13 MB | 28 % |
| deco_spielzeug | 16,786 | 0.44 MB | 5,329 | 0.15 MB | 31 % |
| deco_schmuck | 16,695 | 0.44 MB | 4,603 | 0.13 MB | 27 % |
| deco_kaese | 13,516 | 0.36 MB | 4,618 | 0.13 MB | 34 % |
| deco_crepes | 14,089 | 0.39 MB | 3,987 | 0.12 MB | 28 % |
| deco_maroni | 14,482 | 0.37 MB | 5,213 | 0.14 MB | 35 % |
| deco_puffer | 15,736 | 0.42 MB | 4,807 | 0.14 MB | 30 % |
| shared kit `deco_kit_*.webp` (all 13 stalls, incl. the new `iron_matte` colour) | | 0.45 MB | | 0.19 MB (`*.lite.webp`) | |

- **With the vendor's props** (vendor's current counts): Glühwein 37,687 + 16,816 = 54.5k (5.5k headroom), Bier 43,429 + 12,704 = 56.1k (3.9k), Bratwurst 37,715 + 11,854 = 49.6k (10.4k), Bücher 33,567 + 5,032 = 38.6k. All are under the 60k / 3 MB section budget. Every deco stall is under 20k triangles and 1 MB.
- **First-load share for my 13 stalls:** 7.9 MB desktop (7.46 MB of glb + 0.45 MB kit) and 2.3 MB lite (2.09 + 0.19). Pass 2 was 8.6 / 2.3 MB.
- **Texture sharing:** every glb embeds only its own AO atlas (section 70–96 KB at 768 px; deco 28–35 KB at 448 px), plus the 6 KB Rauten pattern in the two Bier files. All kit maps, including `deco_kit_iron_rm.webp`, are referenced by URI in all 26 files.
- **Contract checks:** `glb_tools.check_stall` passes on all 26 files. Each has `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `light_*`, `bulbs_*`, `snow_*`, `cam_view`, `cam_target` and material `bulb_warm`. There are 2 `light_` empties per section stall and 1 per deco stall. `slot_counter` is at y = 1.050 in every file (the counter top faces are exactly 1.05 m). `gltf-transform validate` reports no errors on the section stalls.
- **Sign text (3D letters):** Glühwein, Bratwurst, Bier vom Fass, Bücher, Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer.

## Previews in this folder

- `stall_*_preview.jpg`: Cycles, 1280x720, 48 samples, OIDN, 3/4 front view at night. The Bratwurst preview imports the vendor's shipped `prop_wurst_counter.glb` at `slot_counter`. The mugs, pot, beer glasses and books in the other three are render-only stand-ins and are not in the glbs.
- `deco_contact_sheet.jpg`: the nine deco stalls (840x600 tiles, 48 samples).
- `stall_*_threejs.jpg`: the bare shipped glbs in three.js under `site/src/lighting` (SwiftShader, AO on, snow off as on the site), same camera as the Cycles preview.
- `stall_bratwurst_threejs_props.jpg`: the Bratwurst glb with `prop_wurst_counter` attached (the combined grill).
- `stall_gluehwein_threejs_signspot.jpg`, `stall_bratwurst_threejs_signspot.jpg`: with the proposed `slot_sign` spot.
- `stall_bier_threejs_home.jpg`: the Bierstand where `layout.json` places it, seen from the site's home camera, with a x3 inset.

## Rebuild

`NM_THREADS=2 /home/claude/tools/bpy-venv/bin/python blender/stalls/<stall>.py [--no-render] [--no-lite] [--samples N] [--res WxH]`, and `.../deco.py [--only kaese,crepes] [--no-render]`. On the loaded cloud machine a stall takes about 1–2 min to build, AO-bake and export both LODs, and 4–7 min to render. The nine deco renders take about 25 min. bpy segfaults at exit after writing everything; this is harmless. Three.js shots: `node blender/stalls/web/shoot.mjs --ao on [--only ...] [--props prop@slot] [--signspot] [--home] [--tag t]` (2–5 min per shot with SwiftShader).

## Notes for other roles and the market owner

1. **Lighting designer: sign spot at `slot_sign` (second measure).** The signs now read without it (see above), but a spot makes them warmer and clearly lit, as the gooseneck lamps in the models suggest. The version I checked is in `blender/stalls/web/stall_shot.html` (`?signspot=1`): a `SpotLight` with warm colour (1.0, 0.72, 0.42), intensity 7, distance 3.2, angle 0.62, penumbra 0.7, decay 2, no shadow, 0.9 m out along the model's front (+Z in three) and 0.45 m up from `slot_sign`, aimed at it. Every stall has `slot_sign` 5 cm in front of its sign face. I did not add a third `light_` empty to the stalls: the Bücher judge asked for two per section stall, and it would use up the light budget. If you would rather drive it from the model, say so and I will add a `light_sign` empty with `userData.type = "spot"` and `userData.aim`, which `placeWarmLights` already honours.
2. **Emissive stand-ins.** Two materials now carry a faint emissive copy of their base colour: `rauten` (Bier pennants, fascia, flags) and `iron_matte` (Bratwurst hood and firebox). The engine's bulbs glow but light nothing, and these surfaces hang right beside them. If the lighting pass ever makes the bulbs cast light, set their `emissiveFactor` lower (one line each in `mats.PATTERNS` and `mats.KIT_VARIANTS`).
3. **Vendor:** the firebox did not move. The hearth plate top is still `HEARTH_Z` = 0.026 above the counter, the grill runs x −1.75..−0.15, and the bowl sits at x −0.9 from `slot_counter`. The Glühwein stall dropped 3.4k triangles and now leaves 5.5k headroom with your current set. The Bierstand went from 44,871 to 43,429 triangles (the Rauten pennants are now one material), and the Bücherstand from 34,841 to 33,567.
4. **Market owner (not carpenter work):** please replace the `gltf-transform optimize` line in `docs/BUILD.md` with `node blender/lib/optimize.mjs in.glb out.glb --texture-size 1024`. The CLI step deletes every `slot_`/`light_`/`cam_` empty and renames `bulb_warm`. Please also remove the tracked `blender/props/__pycache__/*.pyc` files from the index (`.gitignore` already lists `__pycache__/`).
5. **Ride builder:** nothing new from me this pass. The kit is still v11; the `iron_matte` and `rauten` materials are new and optional.
6. COLOR_0 (plank tints, soot, wear) is intentional. Occlusion is on TEXCOORD_1. Extra nodes: `smoke_origin` on the Bratwurst stall (the grill_coals mesh is gone; the vendor's fire bowl has the coals), and `slot_cabinet_l` and `slot_cabinet_r` on the Bücherstand.
7. Footprints are unchanged: Glühwein 3.4 x 2.5 m; Bratwurst 3.9 x 2.5 m plus a 0.8 m lean-to on +X; Bier 4.2 x 2.6 m; Bücher 3.7 x 2.5 m plus a 0.35 m bay on -X; deco stalls 2.6–3.4 x 2.2 m.

## Open issues and what I would improve next

- **Rauten at the home view:** at the home camera a pennant is about 5 px wide, so the lozenges merge into a pale blue-and-white fringe. They resolve from preview and lane distance. Going further would mean bigger, fewer lozenges than real Rauten.
- **Bratwurst hood in Cycles** is a little light and clean for a "sooty" stand, because the emissive stand-in (meant for three.js) also shows in Cycles. The siding and roof carry the soot. A render-only override that switches off the stand-in emissive in previews would fix it.
- **The `iron_matte` hood material has no AO map.** The glTF exporter drops occlusion on that variant (its metal goes through a multiply node). It is not visible in the shots, but I have not chased the cause.
- **Bier headroom** with the vendor's set is 3.9k, the tightest of the four. The first cut would be the stave count on the barrel front (11 staves x 9 rings).
- **Bevel cost:** chamfers are real geometry. A baked edge-normal trim sheet could halve the wall triangles.
- The snow strips are regular on very straight roofs. A few slipped or drifted patches at the eaves would help.
