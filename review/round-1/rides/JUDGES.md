# Latest judges on rides, end of round 1

## Opus (pass 2): Ship

Failed checks:

Fixes:
- Cross-role (lighting designer, top priority for the landmark's look): light the Riesenrad at light_2 (full) and add a ground pool (lite). In engine_full_view_ferris.jpg and engine_lite_view_ferris.jpg the cream steel reads as a black silhouette with only bulbs showing. The asset's material is correct, so this is a scene-lighting fix.
- Cross-role (engineer): support a light_ empty parented under rot_platform so a canopy light can turn with the horses. The builder should then add it, because the horses are very dark from the ride seat in lite (engine_lite_ride_carousel_4s.jpg).
- Soften the gondola glass at grazing angles, for example with lower alpha or a Fresnel-limited reflection, or clamp the ride pitch to about -35 deg, so the dark pane at the right of the 12 s ride frame goes away.
- Double bass: give the body real C-bouts, upper and lower corners and a stronger lower bout, so it reads as a double bass rather than a gourd. Make the f-hole lower eyes and nicks visible at close range.
- Export instr_sax_stand, or have the engine hide instr_sax when no player is at slot_sax, so the held-pose sax never floats.
- Carousel: build one sculpted master horse shared by the 12 nodes with per-horse paint. This gives real carving and frees about 15k triangles under the 80k cap, which is 1k from full now.
- Polish: finer walnut grain on the piano case, finer grain on the drum shells (they currently read as barrel staves), and queue rails, a window grille and posters at the Riesenrad booth.

## Fable (pass 2): Ship

Failed checks:
- (added) The wheel's steel reads in the engine, not only its bulbs: engine_full_view_ferris.jpg and engine_lite_view_ferris.jpg: the lattice is visible only as bulbs; the cream steel is near black. The rsteel material is correct (base colour 0.86, metallic 0.00, roughness 0.39), so this is unlit geometry 15 m up; the builder added light_2 at (0,14.7,3.2) but nothing lights it yet. Owned by the lighting designer / engineer, but it is what visitors currently see.

Fixes:
- Lighting designer / engineer (not the ride builder): light the Riesenrad's light_2 in the full market and give the wheel a ground pool in lite, so the cream steel reads instead of only the bulbs (engine_full_view_ferris.jpg).
- Ride builder, cosmetic: soften the gondola glass at grazing angles (raise roughness from 0.04 or lower alpha below 0.22) or move gondola_seat_0 to the pane's centre line, so the right quarter of the 12 s ride view is no longer a dark pane; alternatively the engineer clamps the ride pitch at about -35°.
- Ride builder, next polish: the Riesenrad booth and deck (queue rails, ticket window grille, posters), a sculpted master horse shared by the 12 horse nodes to free about 15k carousel triangles (now 1k under budget), and a longer tenor body on instr_sax.
- Ride builder + engineer: a light_ empty under the carousel canopy that turns with rot_platform, so the horses are not near black from horse_seat_2 in lite (engine_lite_ride_carousel_4s.jpg).

