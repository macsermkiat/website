# Judges on carpenter, round 6 pass 1

## Ship

## Ship

Failed:
- Board sizes follow the brief: Brief asked for the Glühwein board at about 0.9 x 1.2 m; built 1.10 x 0.80 m (landscape). Defensible for a 16:9 reading frame (fill 0.74) but a deviation the builder should state in NOTES.
- Board surfaces are usable by the engine as shipped: site/src/world/sections.js still keys surfaces as glueh.board, bier.vomfass, wurst.menu; the models ship write_about, write_projects_board, write_writing_menu per the brief, so the engine draws stand-ins until the engineer renames. The carpenter followed BUILD.md and flagged it; the fix belongs to the engineer.

Fixes:
- Engineer (not carpenter): rename the surface roles in site/src/world/sections.js (and surfaces.js) from glueh.board / bier.vomfass / wurst.menu to about / projects_board / writing_menu so the model write_ nodes are used instead of stand-ins, and skip drawing a second header on these three boards.
- Carpenter: note in NOTES.md that the Glühwein board is 1.10 x 0.80 m landscape rather than the brief's 0.9 x 1.2 m, and why (16:9 reading fill).
- Carpenter/vendor: the pot lid intrudes on the lower-left of the Glühwein reading view; either move the pot left of x +0.55 from slot_counter or raise the board a few cm so the reading camera can be square-on.
- Carpenter: the two outdoor boards read dark at night in the browser (lantern/lamp are emissive only); consider aiming light_1 or adding a brighter emissive rim so the chalk text stays legible without the engine's reading glow.
