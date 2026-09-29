# Latest judges on architect, end of round 1

## Opus (pass 3): Ship

Failed checks:
- Home-view foreground and hero roofs read believably (puddles, church nave): In a 2x crop of home.jpg, the puddles in the foreground still read as dark smudges rather than water. The church nave roof reads as a flat, nearly black slab from the home camera (the builder admits this). The bottom ~40% of the hero frame is dark, featureless paving.
- NOTES claims match the file timeline: NOTES says the build order was tree, town, then square, with the ground AO baked with the new town in place. But square_ao.png is dated 17:55 and square.glb 18:01, while town.glb was rebuilt at 18:23 (town.py edited 18:15). The effect is minor because the new nave dormers do not shade the ground, but the claim is wrong.

Fixes:
- Non-blocking, round 2: rework the three home-view puddles so they read as water and not as dark stains. Raise their roughness toward the wet-cobble value, fade their rims into the damp COLOR_0, and check them in the browser with the lighting designer's environment map (the puddle issue raised in pass 1 is still only partly addressed).
- Non-blocking: give the church nave roof some read from the home camera. Either add a low warm light_ empty grazing the square-side slope (coordinate with the lighting designer) or lift the slate albedo and roughness contrast so it stops reading as a black slab behind the tree.
- Non-blocking: break up the empty dark foreground of the home view (the bottom ~40% of the frame). Consider a fountain, Litfassaeule or benches in the camera-side third of the plaza, within square.glb's remaining budget or town.glb's 16k free triangles, so it doesn't rely on the crowd alone.
- Housekeeping: correct NOTES.md on the build order and AO (the square AO was baked at 17:55, before the final town rebuild at 18:23), or re-bake the square AO with REUSE_AO unset against the current town and re-export square.glb and square.lite.glb.
- For the market owner, not the architect: update BUILD.md to name blender/lib/optimize.mjs (or the non-pruning flag set) in place of the default gltf-transform optimize, and add a tree budget row (40k / 1.5 MB).

## Fable (pass 3): Ship

Failed checks:

Fixes:

