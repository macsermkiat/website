# Judges on engineer, round 2 pass 2

## Improve

Failed:
- Deploy is actually shippable: By design, the strict content gate blocks every deploy: 18 notes, 15 markers and 35 book pages are still marked review: check. Frame time on a real GPU has not been measured.

Fixes:
- Writer and Mac: clear the 18 notes, 15 check markers and 35 book pages marked review: check, using npm run content:check, so the strict gate lets the deploy through.
- Mac: run npm run perf on a real GPU and fix any view that misses its target before launch.
- Market owner: confirm in BUILD.md that band players count as person variants, or have the ride builder cut about 17k triangles from the bandstand. Also add the cam_cat_<key> rule.
- Vendor: ship act_ nodes for the deco goods to replace the Lebkuchen hearts the code makes as stand-ins.
- Ride builder: wire up or remove the unused instr_sax_stand.glb. Lighting designer: light the dark side racks in the full market's bookshop.
- Engineer: commit the uncommitted changes to books.js, main.js, NOTES.md and the previews.
