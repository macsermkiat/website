# Judges on carpenter, round 1 pass 1

## Opus: Improve

Failed checks:
- Signs are legible in the previews (added): Christbaumschmuck crest sign (green board, gold Fraktur) renders as a blank black board in the contact sheet. The Bratwurst sign reads 'B?ATWURST' with two hot discs over the letters. Most deco fascia signs are unreadable at sheet size.
- Kit PBR data is physically correct (added): The wood kit metal channel is identical to roughness (kit_wood_rm.png B==G, corr 1.0, mean 170), so every wood surface ships at metalness 0.67 with metallicFactor 1. Cause: mats.py bake() leaves the rough→emission link in place when metal is the constant 0.0. It affects every role that uses kit 'wood'.
- Baked AO map is usable in the browser (added): The Glühwein occlusion atlas is mostly black: 31% of texels are used and their mean is 0.28. In a three.js render of the shipped glb the side wall is darker and streaked black/orange compared with the same model with aoMap removed. The Cycles previews ignore this map, so they hide the defect.
- Iron kit texture has the claimed detail (added): deco_kit_iron_color.webp is 912 bytes with RGB std ~1/255 and the normal map std ~1: it is flat grey, with none of the claimed rust streaks or soot.
- Lite files are about a third of the triangles (added): Section lites are 28–38% (OK). Deco lites are 35–51% (Mandeln 7,878/19,030 = 41%, Maroni 51%), above the ~1/3 target, though small in absolute terms.

Fixes, in priority order:
- Fix the kit bake in blender/lib/nmlib/mats.py: in bake(), remove the existing links on emis.inputs['Color'] before setting a constant, so wood metal bakes to 0. Bump the kit version, rebake the kits, and re-export all stalls, the deco kit webp files and every other role's assets that use kit 'wood'. Check that B==0 in kit_wood_rm.png and in each glb.
- Fix the AO bake: the atlas averages 0.28 with black islands, which darkens and streaks the stalls in three.js. Likely causes are self-intersection or overlap between chamfered boxes, texels smaller than islands, or no bake margin. Raise ray distance/margin, give each island enough texel area or drop tiny pieces from the AO layout, and clamp to a sane floor. Verify with a three.js render with and without aoMap.
- Rebake the iron kit so it actually has rust, soot and a normal-map signal (the current colour and normal have std ~1/255). The Bratwurst hood and grill and the deco stovepipes depend on it.
- Make the signs legible: light the Christbaumschmuck crest (or give it a cream board) and widen or soften the Bratwurst sign lamps so no hotspot covers the letters. Enlarge the text on the small deco fascia signs.
- Bratwurst: add a visible ember bed, ash and heat staining on the grill, and stronger soot on the siding and hood so the 'sooty' brief reads in the preview.
- Wood realism: raise the grain/fibre contrast of the wood tile (colour std is ~8/255) and add edge wear and darkening on counters, so wear reads at counter distance. Thin or break the snow caps so some shingle rows show.
- Bring the deco lite files closer to 1/3 of the full triangles (currently 35–51%), for example with lower text resolution and simpler snow and valance meshes in lite.
- Re-render the previews after these fixes, and add one three.js screenshot per section stall under the site's actual lighting, since the Cycles previews ignore the shipped AO map.
- Market owner: adopt blender/lib/optimize.mjs as the standard web step in BUILD.md. The claim that the CLI's `optimize` strips the empties and renames bulb_warm is verified.

## Fable: Improve

Failed checks:
- The Bratwurst signature feature (hood over grill) reads well in the engine and preview: In the Cycles preview and in my three.js front and cam_view renders the grill body and chimney hood are near-black slabs with no readable rivets, grate depth or ember glow; the coals mesh is hidden under the grate and the iron kit is 512 px with a very dark base colour.
- Lite files are about a third of the full triangle count: Deco lite files keep 35-51 % of full triangles (e.g. kaese 5,033 of 11,785, mandeln 7,878 of 19,030); section lite files are 28-38 %. Sizes are fine (0.16-0.43 MB) but the lite market's 8 MB total is tight once other roles' lite files are added.

Fixes, in priority order:
- Bratwurst: make the grill and hood read as metal and fire. Raise the ember bed so grill_coals shows through the grate, add ash and heat staining, give the iron kit a lighter mid-tone with visible rivets and a stronger normal map, and widen the render-only sign spotlights so the preview shows the sign evenly. Re-render the preview.
- Wood at counter distance: add fibre/pore detail and a second oak tile for counter tops with darkened, worn front edges (an edge-wear mask per stall), since counters are what the visitor sees closest at cam_view.
- Deco signs: enlarge the fascia signs or use a bolder text band (e.g. Alegreya SC on a contrasting board) so 'Gebrannte Mandeln', 'Holzspielzeug' and 'Kartoffelpuffer' are readable at lane distance; the contact sheet currently shows them as blurred strips.
- Snow caps: make them thinner and patchier so a few shingle courses and the ridge show with snow on; today snow_0/snow_1 cover the whole slope and turn every roof into a smooth white blob.
- Lite deco files: drop sign text bevels (text_bevel=0, resolution=1) and simplify snow caps to bring lite deco stalls to roughly a third of full triangles, keeping the lite market inside its 8 MB budget.
- Ask the market owner to replace the `gltf-transform optimize` line in docs/BUILD.md with `node blender/lib/optimize.mjs in.glb out.glb --texture-size 1024`, since the standard step verifiably deletes every slot_/light_/cam_ empty and renames bulb_warm.
- Housekeeping: add `__pycache__/` to .gitignore (blender/lib/__pycache__ and nmlib/__pycache__ are present again) and note in NOTES.md that the preview stand-in goods are not in the glbs so the vendor knows what to supply for the counters.

