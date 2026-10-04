# Judges on vendor, round 6 pass 2

## Improve

Failed:
- Believable materials: prop_bier_counter_foam.jpg: the heads look soft now, but every lip has a hard dark 12-sided outline and the dimpled Maß shows black blotches. Engine screenshot: Lebkuchen still dark maroon
- Round-4 Lebkuchen fix visible in the live market: deco_lebkuchen_engine.jpg: the hearts are near-black maroon with dim icing; the warm brown only shows in the standalone three.js view
- Engine actually uses the new write_ meshes and book_open: Builder admits three site/src changes are still pending (skipping write_*_mesh, write_label_n, loading book_open.glb), so the back labels and the open book do not show yet

Fixes:
- Make the Lebkuchen read warm brown in the real engine view: work with the lighting designer or the engineer on light from the visitor's side, or brighten the albedo and icing, and verify with a new engine screenshot
- Remove the dark outline at the beer glass lips: raise the head's edge to the rim, or thin and fade the inner wall above the foam
- Fix the black blotches in the dimpled Maß glass (normals or refraction)
- Have the engineer apply NOTES.md Pass 2 fix 4 (skip write_*_mesh, show write_label_n, load book_open.glb), then confirm in the engine
- Give act_page_turn a real bend (shape keys or bones) so the page curls
