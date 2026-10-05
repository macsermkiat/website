# Round 9 judges: vendor

Final: Ship / Ship after 2 pass(es).

## Pass 1

### Judge Opus: Improve
- FAIL Shop sparkle inventory incl. rot_pyramid, tinsel, within budget: rot_pyramid, tinsel_0/1 and the inst_merc_* batches exist. But in both renders the shelf sparkle is lost as silhouettes against the bright mirror, the Lametta reads as sparse straws, and the top-shelf angels are not visible. Node names inst_inst_merc_* are double-prefixed.
- FAIL Shop reads as 'realistic miniature' richness: The whole-shop render looks sparse. There is large empty dark wood, and the three tiers barely read as sparkle beyond the harmonica row.
- Fix: Make the shelf tiers read: increase the bauble density per cluster, or ask the carpenter or lighting designer to darken the foxed mirror so the shelf goods stop showing as silhouettes.
- Fix: Rebuild the Lametta as denser twisted foil ribbons that glint (there are 4.3k triangles of headroom), so the swags read as tinsel rather than straws.
- Fix: Make the Rauschgoldengel on the top shelf visible in the close-up. Raise them or light them.
- Fix: Fix the instance.mjs naming bug that produces inst_inst_* node names.
- Fix: Re-render both shop previews after these fixes.

Open issues from the builder:
- Shop headroom is 4,279 triangles: the hut (31,564) plus the goods (24,157) come to 55,721 of 60k. If the hut grows, the easiest cuts on my side are tinsel_3 (1.1k) and the back-wall garland (about 0.5k).
- Engine (engineer): the shop's items.json now holds only the three groups, with the new actions 'harmonica' (index 0..11, left to right) and 'dive' (cam / cam_target). The candles have an `order` for lighting from the outside in. The goods use EXT_mesh_gpu_instancing inst_* nodes, and rot_pyramid carries userData.axis = 'y'.
- In Cycles the Lametta reads as thin bright straws rather than shimmering foil. It should glint more in the engine; a denser version would cost about 0.5k triangles per swag.
- The carpenter's foxed back-wall mirror is bright behind the shelves, so the shelf goods read mostly as silhouettes. A darker mirror is the carpenter's or lighting designer's call.
- The lite shop goods are about 61% of full: smooth spheres and fine strands cannot lose much and still keep their bounds. check_props flags this as a warning, not a failure.
- Carried over from round 8 (not mine): the Bier coaster title 'Transfusion Audit' from content/projects.md reads clinical; this is for the writer or Mac.

## Pass 2

### Judge Opus: Ship
- Fix: Optional: only 2 snow globes are clearly visible in the previews; check that 3-4 exist (the brief asks for 3-4)
- Fix: Optional: brighten or add highlights on shelf tier 3 so the bottom row sparkles as much as the top
- Fix: Keep the 897-triangle headroom in mind; trim the fairy-light loops if the hut grows

### Judge Fable: Ship
- Fix: Headroom is only 897 triangles; agree with the carpenter now which side gives if the hut grows (vendor already named the fairy-light loops, beam fringe or back-wall garland as the cheapest cuts).
- Fix: A few Lametta fringe strands still flash as single bright lines in Cycles; confirm in the engine that the glint shader on tinsel_0..2 breaks them up, otherwise add one more kink per strand.
- Fix: Bier coaster title 'Transfusion Audit' (round 8 carry-over) still reads clinical; hand to the writer or Mac.

Open issues from the builder:
- Shop headroom is only 897 triangles (59,103 / 60k). If the hut grows, the cheapest cuts on my side are the fairy-light loops (about 0.6k), the beam Lametta fringe (about 0.4k) or the back-wall bead garland (about 0.5k).
- A few Lametta fringe strands still flash as single bright lines in Cycles where a facet faces the lane fill. The engine's glint shader on tinsel_<n> should make them shimmer as the camera moves.
- Mirror, for information only (carpenter / lighting designer): the pass 1 silhouettes came from my preview's fill panel showing in the mirror. In the engine, the mirror's brightness depends on the lighting designer's environment; if it reads bright there, a darker foxing would help the shelf goods.
- Engine (engineer): batch nodes are now named inst_<finish>_<colour>_<size>, no longer inst_inst_*. A new vendor_foil material is used on the angels.
- The lite shop goods are about 60% of full (a lite-ratio warning in check_props, not a failure).
- Carried over from round 8, not mine: the Bier coaster title 'Transfusion Audit' reads clinical; this is for the writer or Mac.
