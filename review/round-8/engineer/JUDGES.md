# Round 8 judges: engineer

Final: Improve after 2 passes (Opus only; Fable is called only to confirm a Ship). The remaining failures come from the round-9 shop changeover and move to round 9.

## Pass 1

### Judge Opus: Improve
- FAIL Visual quality and phone usability: stop_schmuck.jpg: at 960x640 the stop bar and buttons cover the lower third of the shop and hide the counter goods. The phone cabinet view looks good: the covers are readable and large.
- FAIL Work committed: main.js, perf.js, main.css, smoke.mjs and the review folder are still uncommitted, as the builder said.
- Fix: Run the full smoke test again after the last phone fixes. The 245/245 run came before them; only the cabinet section was re-run.
- Fix: At the ornament shop on small screens, let the stop bar fold away or shrink, as it already does at the book stall with a cabinet open. Right now it covers the lower third of the shop.
- Fix: Commit the outstanding site changes (main.js, perf.js, main.css, smoke.mjs) and the review folder.
- Fix: Mac needs to run `npm run perf` on his laptop's real GPU to get true frame times for the 87-person crowd.
- Fix: When the visitor steps back from an open cabinet, return to the view turned toward that cabinet, not the stall's straight-on view.
- Fix: Find out why three.js sometimes counts infinite triangles for the text blocks. The bench currently keeps the last real count instead of fixing the cause.

Open issues from the builder:
- Frame times for the 80-person crowd have not been measured on a real GPU yet. Mac needs to run `npm run perf` on his laptop.
- The full 245/245 run came before the last phone fixes: the stop bar hiding when a cabinet is open, the softer light on the cabinet, and the stricter cover check. Only the cabinet section was re-run after them (15/15). Those changes only affect screens 640 px or narrower with a cabinet open, and the light when it points at a cabinet.
- At the ornament shop, the stop bar and the text notes cover the lower third of a 960x640 view. The bar could fold away on small screens, as it now does at the book stall while a cabinet is open.
- Step back from an open cabinet returns to the stall's straight-on view, not to the view turned toward that cabinet.
- three.js sometimes counts text blocks as infinite triangles for a frame. The bench now keeps the last real count instead of fixing the cause.

## Pass 2

### Judge Opus: Improve
- FAIL Smoke test covers the ornament interactions, the cabinet pick at 390 px, deco scenery, and the earlier sections: The shop files on disk are now the round-9 set, so the main run only tests harmonica baubles, the mirror ball and the Schwibbogen. The round-8 interactions were proven only by a side run against the fa3da3d models (19/19), and the Herrnhut star was never tested in any run. Also, the full run predates the round-9 glb commit at 08:40, while the files changed at 07:51 and 07:57.
- FAIL Bench reports frame time and first load with the larger crowd: perf.log is from 05:43 and was not re-run after the troika and crowd fixes. It uses software GL only, and no real-GPU frame time exists.
- FAIL In-scene pickle reward text is readable: In the folded-shop screenshot, the 'Weihnachtsgurke' toast covers the in-scene reward line ('Du hast ... für dich').
- Fix: Re-run the full smoke run against the shop files now on disk (committed in fa50fa8 at 08:40) and commit the review folder.
- Fix: Settle which shop set is final with the vendor. Then either build the round-9 interactions (harmonica melody, mirror-ball dive, turning pyramid, tinsel, foxed mirror) or restore the round-8 models. Make sure the smoke run covers every ornament interaction in the final set, including the Herrnhut star if it ships.
- Fix: Re-run npm run bench/perf with today's code, and get Mac's real-GPU frame times for the 87-person crowd.
- Fix: Move the pickle toast so it no longer covers the in-scene reward line, or drop one of the two.

Open issues from the builder:
- Real-GPU frame times for the 87-person crowd still need Mac to run `npm run perf` on his laptop.
- Round-9 shop features are not built: harmonica baubles tuned to the ballad's melody, the mirror-ball camera dive, the turning pyramid, the tinsel glint and the foxed mirror. For now the harmonica rings a scale and the mirror ball spins and rings a low note.
- The vendor's round-9 shop files were committed (fa50fa8) after the full run started. If they changed after about 08:20, the shop section should be run again.
- The review folder (NOTES.md, logs, screenshots) is not committed yet. The site code changes are already in fa50fa8.
