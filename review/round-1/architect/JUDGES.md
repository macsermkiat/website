# Judges on architect, round 1 pass 1

## Opus: Improve

Failed checks:
- String-light poles and wires stay clear of the tree and other placed objects: Vertex test with the tree at [6.5,-15], rotY 0.3: 468 string_wire verts, bulbs_string_26/28/30 and 20 poles_wood verts sit inside the fir's branch radius. The tree is 5.6 m wide at the base and 3.5 m at 5.5 m. Span 28 ([10,-18] to [3.5,-9.5]) passes about 0.95 m from the trunk, and pole [10,-18] stands 4.6 m from it, inside the lower boughs. The strand running into the tree can be seen in tree.jpg.
- Benches by the tree stand clear of the boughs: 81 of the 336 bench vertices within 7 m of the tree sit under needle geometry below 1.5 m height. The benches are about 4.9 m from the trunk, and the boughs reach about 5.4 m there.
- Kerbs read as granite, without artefacts: In a zoomed crop of town_street.jpg (and the right side of square_cobbles.jpg), the kerbstones alternate pale and pitch-black like painted racing kerbs, which suggests flipped normals, bad UVs or bad AO on every other stone.
- Baked ambient occlusion as the contract requires: In the materials check, only the square's cobble_fan and setts_* materials have an occlusion texture. town.glb and tree.glb have none, and the builder admits this for the town. The town facades in town_street.jpg look clean and CG-like without contact shadow.
- Puddles look believable: home_view.jpg shows the puddles as flat black blobs on the cobbles. The builder defers this to the browser's environment map, so it isn't proven yet.

Fixes, in priority order:
- Clear the tree of string lights. In blender/lib/architect_plan.py, move back-row poles 16 [1,-18] and 17 [10,-18] to at least 6.5 m from the tree axis at [6.5,-15]. Re-route spans [16,17], [17,8] and [17,6] (bulbs_string_26, _28, _30) so no wire or bulb passes within the fir's radius (about 5.6 m at the base, 3.5 m at 5.5 m). Re-export square.glb and square.lite.glb and re-run the vertex clash test.
- Fix the black/white striped kerb. Every other kerbstone renders pitch-black in town_street.jpg and square_cobbles.jpg. Check normals, UVs and the AO bake on the curbs mesh until all the stones read as the same granite.
- Bake AO for the town, at least on the wall and roof meshes (the plan in NOTES.md), and give the tree an occlusion texture as well. BUILD.md requires AO in the glTF occlusion slot.
- In layout.json, change the asset of riesenrad to ferris.glb and karussell to carousel.glb. Those files now exist in site/public/models, and the engine currently finds them only through its fallback keys, logging a 'not found' note.
- Move the two tree benches out to about 6 m or more from the tree axis so they are no longer under the lower boughs.
- Tone down the puddles, which read as black blobs from the home view. Give them some roughness or blend them with the wet cobble, and check them in the browser with the environment map before the next round.
- Close the wedge-shaped roof gaps between ring houses (trapezoid footprints or back fillers), since the Ferris wheel view will show them.
- Market owner: update BUILD.md to name blender/lib/optimize.mjs (or the flag set that keeps names and empties) instead of the default gltf-transform optimize, and add a budget row for the tree.

## Fable: Improve

Failed checks:
- layout.json asset names resolve to real files in site/public/models: riesenrad.glb and karussell.glb do not exist; the ride builder shipped ferris.glb and carousel.glb (plus .lite). The engine's key-search fallback finds them with a 'not found' note (rides NOTES.md item 1 already asked for the fix), but the file that is meant to be the single source of placement names two wrong assets. All other 17 assets resolve, with lite variants.
- Ambient occlusion is baked into the glTF occlusion texture (BUILD.md lighting approach): Only square.glb's four ground materials have an occlusion texture (square_ao-*_rough packed, 1024 px, baked with the town present). All 33 town.glb materials and all 12 tree.glb materials report occlusionTexture = none. The town's 146k triangles of jetties, dormers and reveals get no contact shadow, which is where AO would earn the most.
- Church tower reads as a detailed landmark in the preview: town_church.jpg shows the tower as a nearly unlit red block with a dark spire; the claimed four stages, corner buttresses, belfry louvres, clock faces, gablets and pinnacles are not legible, and the 3 m sandstone tile reads as oversized regular blocks at this distance. The nave's stained-glass lancets are the only part that sells the church.

Fixes, in priority order:
- Change the two ride `asset` fields in site/src/layout.json to the files that exist: `ferris.glb` and `carousel.glb` (the rides NOTES.md already asks for this). layout.json is the single source of placement; it should not depend on the engine's fuzzy fallback.
- Bake ambient occlusion for town.glb as the contract asks: give the big wall, roof and reveal meshes a lightmap UV and bake a 2048 AO (the NOTES.md plan), then verify with gltf-transform inspect that the plaster/timber/sandstone materials show an occlusion texture. Do the same at 512-1024 px for the tree trunk/fence at least.
- Make the church tower read: light or self-shade the tower so its stages, buttresses, belfry openings, clock dials and pinnacles are visible in the preview, and reduce the sandstone UV scale (3 m tile) or add ashlar coursing so the masonry stops looking like oversized regular blocks close up.
- Close the wedge gaps between neighbouring ring roofs (back-wall/roof filler or trapezoid footprints); they are visible from the Riesenrad, which the engine already lets visitors ride.
- Reduce or rank the 50 `light_` empties in square.glb: either export only the empties that matter (for example one per lamp on the plaza edge, none per string span) or name them so the lighting designer can pick a budgeted subset without guessing (e.g. `light_lamp_00` first ring, `light_string_*` optional).
- Add a little geometric relief to the plaza foreground where the home camera is close (a displaced or higher-poly inner disc within the 40k budget, currently only 187 triangles of cobbles), so the fan pattern does not read as a flat normal map at low angles.
- For the market owner, not the architect: BUILD.md should replace the default `gltf-transform optimize` command with either the architect's flag set or `blender/lib/optimize.mjs`, and add a tree budget row (40k / 1.5 MB is a reasonable default).

