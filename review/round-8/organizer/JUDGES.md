# Round 8 judges: organizer

Final: Ship / Ship after 1 pass(es).

## Pass 1

### Judge Opus: Ship
- Fix: Optional: variants still lists the full people_vendor_deco_f.glb. Line 386 of crowd.js preloads every variant in the full market, so confirm only the ornament shop vendor needs it.
- Fix: Optional: ask the lighting designer to brighten the Mandeln, Lebkuchen and Maroni interiors so their vendors can be seen.

### Judge Fable: Ship
- Fix: Trim crowd.json variants to the files the crowd actually uses: people_man_parka.glb, people_woman_young.glb and the five *.lite.glb entries are preloaded by the full market for nothing (~330 kB).
- Fix: Nudge walker_lane_left_2_pair (the companion of walker_lane_left_2) off the loop: its median distance is 0.96 m and 41% of its path is within 0.8 m of the left-lane loop leg; give the companion the other side or a 0.3 m larger offset.
- Fix: Minor: add a second person to the Bier counter or move the two waiting past the barrel tables closer, so the queue reads as a queue from the stroll camera.

Open issues from the builder:
- Walkers cross stroll legs where lanes meet, and the front of the square is crossed by most signpost legs. They keep about 0.8 m or more off the loop where they run alongside it, but they do not step aside for the stroll camera; that would need an engine change from the engineer.
- The Bier queue has only one person at the counter. The other two wait just past the barrel tables on the stall's front right, because the front of the counter is inside the Bier close view and props fill its right end.
- The 18 people at the deco stalls use lite figures, which look softer at 2 to 3 m (no ears, simpler hands). The deco vendors keep their faces. Switching the customers back to full figures is a one-line change in crowd_plan.py.
- In the browser views the Mandeln, Lebkuchen and Maroni interiors are dark from the lane, so those vendors are hard to see at an angle. This is for the lighting designer.
- people_anims.glb was not rebuilt (same as round 6). Each figure carries its own clips, so this has no effect.
- The engine caps the full crowd at 90 and crowd.json has 87. Drawing the .lite.glb files as-is, with no distance swap, relies on current crowd.js behaviour; the 'lod: lite' field records that intent.
- Re-run crowd_plan.py and then check_stroll.py after any layout or stroll change.
