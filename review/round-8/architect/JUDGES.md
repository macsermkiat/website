# Round 8 judges: architect

Final: Ship / Ship after 1 pass(es).

## Pass 1

### Judge Opus: Ship

### Judge Fable: Ship
- FAIL NOTES.md numbers agree with the shipped files: NOTES says the ornament-shop stop eye is [17.56, 1.8, 10.23], but layout.json and the check output give [17.963, 1.8, 10.23]; triangle/size tables match exactly.
- Fix: Correct the ornament-shop stop eye in NOTES.md (shipped value is [17.963, 1.8, 10.23], not [17.56, ...]).
- Fix: Organizer to re-plan crowd.json for the moved lanes, back row and carousel, then re-run CHECK_ONLY=1 blender/square/stroll.py; group_square_10 at 0.84 m on Riesenrad -> Bratwurst should move to the 0.95 m reserve.
- Fix: Note for the engineer: site/src/places.js and layout.js already carry the 'schmuck' place and liteOnly handling, so the 'engine does not know the shop yet' open issue is stale; a browser pass of the new stroll and signpost arm is the remaining verification.
- Fix: Optional: shorten the 3 m Bratwurst approach double-back by nudging the Bratwurst cam_view toward the lane in a later carpenter round.
- Fix: Market owner: update BUILD.md's 'Layout (starting point)' deco/back-row/carousel positions and add the proposed signpost and tree budget rows.

Open issues from the builder:
- Engineer: site/src/places.js does not know the ornament shop yet. It needs a place such as 'schmuck' (matching 'deco-schmuck', 'schmuck', 'christbaumschmuck'). Until then stroll.js drops it from the stop list and signpost.js ignores act_sign_schmuck. Also, layout.js inferKind() makes any entry with a place a landmark, so the shop needs to stay a deco stall that is also a stop.
- Engineer: the engine does not read the new "stream": "lite" field on the 8 plain deco stalls yet.
- Organizer: the layout moved (deco lanes, back row, Kartoffelpuffer, Karussell, poles 3, 9, 10, 12, 13, 15, 16, 17), but crowd.json is still the round-7 plan. Please re-run crowd_plan.py, keep standing people 0.95 m off the stroll legs and counter customers within about 1 m of the counter, then run `CHECK_ONLY=1 python3 blender/square/stroll.py`, which must exit 0.
- Riesenrad → Bratwurst carries one warning: group_square_10 stands 0.84 m from the path, which is under the 0.95 m reserve but over the 0.6 m rule.
- The walk into the Bratwurst stop and out toward home covers about 3 m of the same ground twice. Fixing it would mean moving the Bratwurst's camera point in the carpenter's glb.
- Not checked in the browser: the new stroll and signpost arm need the engine's ornament-shop place first. The signpost lettering is checked in Cycles only.
- BUILD.md's 'Layout (starting point)' section is now out of date for the deco, back-row and carousel positions; layout.json is the source. The proposed budget rows for the signpost and tree still need adding.
- tree.jpg is copied from round 5, because tree.glb has not changed.
