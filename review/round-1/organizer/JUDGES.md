# Judges on organizer, round 1 pass 1

## Fable: Improve

Failed checks:
- Lite variants meet the contract's intent (about a third of the size for the lite market): Lite triangles are a third, but lite files are 100–114 kB vs 124–138 kB full because 11–13 clips (~60 kB of JSON/accessors) are repeated in every file; people are 1.7 MB of the lite model download, which the engineer measures at 10.4 MB against the 8 MB target.
- Sitting and seated-playing poses deform the long coats cleanly: In my three.js renders of the shipped files (s_sit.jpg, s_band_play.jpg) the long coat's skirt on people_man_coat and the pianist stretches into a flat disc across the thighs when seated; the bench couple and pianist use these poses in crowd.json.
- Preview set covers what the brief asked for (line-up of all figures, band, group): band.jpg and group_chat.jpg are good; lineup.jpg shows only the 8 crowd figures, so the 4 vendors appear in no preview and the builder's claim 'vendors and band behind' is not visible in the image. My own render (s_vendors_serve.jpg) shows the vendors are fine (aprons, serve pose).

Fixes, in priority order:
- Cut the lite (and full) download: move the clips into one shared rotation-only people_anims.glb retargeted by bone name (the skeletons are identical), or at least strip the *_free twins and the band/vendor-only clips from the crowd figures' lite files; target ~40 kB per lite figure so the people stop being 1.7 MB of an over-budget 10.4 MB lite market.
- Fix the seated deformation of long coats: weight the coat skirt to the thighs with a split at the hip line (or add a seated skirt correction in the sit/play_piano poses) so the hem drapes over the knees instead of flattening into a disc; re-render the bench couple and pianist to confirm.
- Re-render lineup.jpg so all 16 figures (8 crowd, 4 vendors in aprons, 4 musicians) are actually visible, as the brief asks and NOTES claims.
- Keep people out of the stall cam_view sight lines: in crowd_plan.py add each stall's cam_view→cam_target segment as an obstacle for queues and groups (panel_gluehwein.jpg shows a queue member filling the right edge of the Glühwein view; the engineer flagged the same for the bandstand steps).
- Small crowd.json tidy-ups: set mug:false on browsing_lebkuchen (clip idle_free), and keep single-person entries out of 'groups' or give them kind 'browsing' so the 2–5 rule holds; also relax the tight chat spacing (hand grazes a neighbour's coat in group_chat.jpg) by ~0.1 m.
- Optional polish for later rounds: bake a small AO/occlusion texture into the figures per BUILD.md's lighting approach, soften the beanie dome so it reads as knit rather than a helmet, and give the child figures a non-bench 'sit' alternative (crouch reads wrong).

## Opus: Improve

Failed checks:
- BUILD.md material contract: AO baked into the glTF occlusion texture: No material in any people_*.glb has an occlusion texture (the inspect output shows only normalTexture). Close up in the engine, the figures look flat under the coat hems, collars and arms. NOTES.md admits there is no AO bake.
- Lite versions meaningfully lighter for the 8 MB lite market: Lite files are 100 to 114 kB against 124 to 138 kB full, about 0.82 of full size. The 16 lite files total 1.72 MB, about 21% of the whole 8 MB lite-market budget, because about 60 kB of animation JSON is duplicated in every file.
- crowd.json internal consistency and variety: browsing_lebkuchen has man_older with mug:true but clip idle_free. Three of the four kids_karussell children share coat #2f5f9e, so the carousel reads as a uniformed group in the engine shot. The open issues about crowd.js ignoring clip, colour and y are stale: the engine now honours them.

Fixes, in priority order:
- Bake ambient occlusion for each figure (body-part contact at collars, under the coat hem, arms against the torso, hat brim) into the glTF occlusionTexture, or at least darken the COLOR_0 multiplier on coat, scarf, hat and body, as BUILD.md's material rule requires. Re-check in the engine that the close-ups no longer look flat.
- Make lite actually light: move the 11 to 13 clips into one shared people_anims.glb (rotation-only, retargeted by bone name), or strip the unused crowd clips from the band and vendor files. The target is lite files around a third of full so the people take far less of the 8 MB lite market.
- Fix the crowd.json data: set mug:false for man_older in browsing_lebkuchen (clip idle_free), and give the kids_karussell children varied coat colours. Add a check to crowd_plan.py that mug matches the clip's _free suffix.
- Re-render lineup.jpg so all 16 figures are visible side by side (two rows spaced apart, or a wider frame), with no figure hidden behind another, so vendors and band can be reviewed.
- Update NOTES.md open issues: crowd.js now plays person.clip and phase, applies colours and keeps vendor y = 0.13, and instruments.js already loads the people_band glbs. Remove or reword those items and keep only the remaining engine hand-offs (act_sax and act_brush sync, instancing/draw calls).
- Polish: close the 0.014 walk loop seam, widen group spacing so chat gestures don't clip neighbours, and move the two walker paths that pass 0.2 m from lamp poles.

