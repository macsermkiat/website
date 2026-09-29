# Latest judges on engineer, end of round 1

## Opus (pass 2): Improve

Failed checks:
- Close-up and phone framings free of obstructions (further check): In panel_gluehwein.jpg (both the builder's and my re-run) a crowd figure is cut off at the left edge of the About-me close-up, and a white sliver shows at x≈17, y≈258. phone_home.jpg has a black lamp pole down the middle of the new phone home view. Near snowflakes still show as ~20 px grey discs in home_full_snow.jpg.
- Real-GPU frame time measured (further check): Frame time has only been measured on SwiftShader. The LOD distances of 18/14/12/8 m are guesses, as NOTES.md says. The governor and the ?perf Tour exist as mitigation, but no real-GPU number has been collected yet.

Fixes:
- Keep crowd walkers out of the camera frustum between cam_view and the counter while a section-stall panel is open. The Glühwein (About me) close-up currently has a figure cut off at its left edge. Hide or steer away anyone within ~2.5 m of the camera path, as the bookseller-aside logic already does for the Bücherstand, and add a smoke check that no crowd mesh projects into the close-up viewport.
- Re-frame PHONE_HOME in main.js ([0.8,5,19.5] → [0,2.7,-4]) so that no string-light pole lands on the vertical centre line of the 390×844 home view. Shift x by about a metre or pick a target that puts the pole off-axis, and check it with phone_home.jpg.
- Before announcing, get Mac's ?perf Tour lines from a mid-range laptop (quality=full, governor=0) and a phone (quality=lite). Then set LOD_BY_TIER and the default for integrated/unknown GPUs from the real medians. This is a launch gate, not something to do in code now.
- Make near snowflakes smaller still, or fade flakes within ~1 m of the camera: a few 15-20 px soft grey discs remain in home_full_snow.jpg. Hand the final cap to the lighting designer so capFlakes in main.js can be removed.
- Find and remove the white sliver at the left edge of the Glühwein close-up (about x=17, y=258 in panel_gluehwein.jpg). It is probably a tooltip or a bulb clipped by the frame.
- Re-shoot panel_buecherstand.jpg and ride_riesenrad.jpg after the writer's 22:26 content change. The review copies show book-list and question text that the current production build leaves out, so the panel sees text that no longer ships.

## Fable (pass 2): Improve

Failed checks:
- Review screenshots show what the production build ships: panel_buecherstand.jpg (22:13) and panel_bratwurst_lite.jpg (22:44) show the five-book list and the three essay titles, but the writer's content/reading.md and writing.md (changed 22:26) put those lists in the same block as a [[Mac:]] note, and a notes-hidden production build strips them: the built main JS has 0 hits for 'front shelf' and 'Sample size is a question'. The screenshots therefore come from an earlier content state, not the shipped build as NOTES.md claims.

Fixes:
- Retake panel_buecherstand.jpg and panel_bratwurst_lite.jpg (and re-run the smoke suite) against the current content/*.md so the review set shows the production build; the 22:26 writer change strips the book and essay lists, and NOTES.md's 'from the production build with notes hidden' claim is currently untrue for those two shots.
- Give the notes-hidden build a graceful fallback for a section whose list was stripped: the shipped Bücherstand panel and plain.html section are one sentence, while the 3D shelf still features five named books pulled from front matter. Either render the front-matter books list in the panel/plain page (it carries no note) or agree with the writer to move the note out of the list block.
- Measure frame time on a real GPU before launch (open ?perf and press Tour on a laptop and a phone) and set LOD_BY_TIER and the default quality from the numbers; the governor is a safety net, not a measurement.
- Hand the flake cap (capFlakes in main.js) and the instanced ground pools to the lighting module so main.js stops patching another role's uniforms and pools after the fact.
- Merge the snow_ caps and the remaining unique carousel horses to hold the draw-call gains when snow is on; document that the lite market now runs 5 real lights and get the lighting designer's sign-off in BUILD.md terms.
- Small clean-ups: drop the unused lfs: true from pages.yml (no .gitattributes), and note in NOTES.md that the review images were untracked at judging time so the market owner commits them.

