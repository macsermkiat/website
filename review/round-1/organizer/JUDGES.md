# Latest judges on organizer, end of round 1

## Opus (pass 2): Ship

Failed checks:
- Seated long coats deform cleanly: The disc is gone, but in threejs_sit.jpg the lap panel of man_older and man_coat still reads as a flat, hard-edged tray jutting past the knees. It is milder in bench_sit.jpg (Cycles). Only 3 bench sitters and the pianist are affected, about 45 m from the home camera.

Fixes:
- (Polish, next round) Add the planned pair of skirt bones, rotated by sit and the seated play clips, so the long coat's lap panel drapes instead of forming the flat tray visible on man_older and man_coat in threejs_sit.jpg.
- (Polish) Give faces a bit more at close range: eyes and brows that show in three.js (they are nearly blank in threejs_full.jpg), perhaps a slight cheek or chin form. People seen close up in the stall panel views are where the 'realistic miniature' bar is weakest.
- (Engineer hand-off, keep tracking) Retarget people_anims.glb by bone name so the figures can drop their per-file clips (lite about 30 kB, full about 80 kB). That also brings _free and laugh back to far or lite figures.
- (Engineer hand-off) Sync or disable the act_sax sway and act_brush sweep against the players' play clips, and look at merging or instancing each variant to cut the roughly 450 people draw calls.

## Fable (pass 2): Ship

Failed checks:
- The lite market (first 40 people) still covers the brief's scenes: By file order the lite market keeps 4 vendors, 12 queue members, 10 walkers and 14 people from the first stall/square groups only: no bench couple, no kids at the carousel, no family at the tree and no bandstand listeners appear on phones. Reordering crowd.json so one bench, the Karussell children, the tree family and two listeners sit inside the first 40 (in place of a few square groups) would fix this without touching the models.

Fixes:

