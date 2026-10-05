# Round 8 judges: vendor

Final: Ship / Ship after 2 pass(es).

## Pass 1

### Judge Opus: Improve
- FAIL Books face-out with title and author legible at cam_cat, no publisher art: In prop_books_lives_cam_cat.jpg the left column (Elon Musk, Einstein) is lit so dimly that the author line 'Walter Isaacson' is barely readable. The covers are in-house designs with no publisher art
- Fix: Fix the dim left column in the books cabinets: raise cover brightness/emissive or the cabinet lighting so title and author read at cam_cat on every face-out book, then re-render all six cam_cat previews
- Fix: Re-render the section close-ups for round 8 instead of reusing copies from rounds 3 and 6
- Fix: Change check_props so the deco MB column leaves out the shared textures, so the 1 MB budget check is meaningful
- Fix: Free some triangle and MB headroom in the ornament shop (for example decimate the tree's lite file or the box props)

Open issues from the builder:
- Any deco click code in the engine (site/src/actions/items/deco.js, engineer) is now dead and should be removed or left inert. The deco sets load as plain scenery at slot_counter.
- The deco 'MB with goods' column in NOTES reads 1.01–1.10 MB against the 1 MB budget. This happens because check_props adds the shared prop textures to every stall; the stall's own files are 0.24–0.33 MB.
- Lite-ratio warnings (above 38%): the deco scenery (its full file is already built at lite detail), the ornament shop's shelf, case, counter and tree, the bier back and shelf, the glühwein wine shelf and the books counter.
- The ornament shop has only 215 triangles and 0.03 MB of headroom left. Any new ornament needs a trim elsewhere.
- In the lite deco files the smallest rail goods (some braids and tapers) are pruned, so the rails read thinner than in the full files.
- The section-set close-ups in round-8 are copies from rounds 3 and 6; the sets are unchanged and were not re-rendered to save usage. A fresh set should be rendered when usage allows.
- The carpenter rebuilt the deco hut glbs during this run. The seat check passes against the current files, but it should be rerun if the huts change again.
- Contract note for BUILD.md: each deco stall's goods are now one set at slot_counter that reaches slot_rail_1, both shelves and slot_crate by fixed offsets; props.json marks these sets seat 'span'.

## Pass 2

### Judge Opus: Ship

### Judge Fable: Ship
- Fix: Optional: add one wurst close-up framed on the grill itself (coals, sausages on the grate) so the charred-sausage and coal_glow materials are shown directly rather than at the frame edge of the Marktblatt shot.
- Fix: Optional: re-render stall_schmuck.jpg and stall_schmuck_close.jpg from the pass-2 geometry so the review set matches the shipped glbs (the builder notes they are from pass 1).
- Fix: For the writer/Mac, not the vendor: decide whether the 'Transfusion Audit' coaster title from content/projects.md belongs in the scene.

Open issues from the builder:
- The Bier coaster close-up prints Mac's project names from content/projects.md, as the engine will. One of them, 'Transfusion Audit', reads as clinical, which the brief keeps out of the scene. This is for the writer or Mac to decide; content is not the vendor's.
- stall_schmuck.jpg and stall_schmuck_close.jpg are from pass 1. They were not rendered again after the small segment trims (baubles 9 to 8 sides, angels 6 to 5), which barely show at lane distance.
- The cover glow (vlib.BOOK_GLOW = 0.3) is the one setting to retune if the carpenter or lighting designer changes the cabinet lamps.
- Lite-ratio warnings remain (16): the deco scenery (its full file is already built at lite detail), the ornament shop rails, shelf, case, counter and tree, the bier back and shelf, the Glühwein wine shelf and the books counter.
- Any deco click code in the engine (site/src/actions/items/deco.js, the engineer's) is dead now that the deco stalls are scenery, and should be removed or left inert.
- Contract note for BUILD.md: each deco stall's goods are one set at slot_counter that reaches slot_rail_1, both shelves and slot_crate through fixed offsets. props.json marks these sets seat 'span'.
