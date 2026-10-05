# Round 10 judges: vendor

Final: Improve after 2 passes. The only failing check is the engine wiring for the Bratwurst plate, which belongs to the engineer (round 10 engineer run).

## Pass 1

### Judge Opus: Improve
- FAIL Bratwurst stall works on the site: Builder says wurst.js and standinGoods.js line 68 still look for act_sausage, so nothing is clickable and stand-in sausages get added
- Fix: Engineer: update standinGoods.js line 68 and actions/items/wurst.js to use act_wurst_*/act_roll and add the plate, sauce, dust and clear actions; the Bratwurst stall should not go live before this
- Fix: Bierstand: Mac asked for 'more' bottles, and the shelves are still fairly sparse. Consider adding a row on the upper shelf ends if the budget allows
- Fix: Give the Krakauer its own smoked-skin look once space in the texture atlas is free

Open issues from the builder:
- Engineer: the Bratwurst stand won't work in the browser until the engine is updated. site/src/actions/items/wurst.js still looks for act_sausage_* / act_roll_*, and site/src/engine/standinGoods.js line 68 adds stand-in sausages when there is no act_sausage node, which now happens on the real model. It needs to check act_wurst_ instead and implement the plate, sauce, dust and clear actions described in items.json.
- act_smoke and act_writing_paper keep their act_ names because the brief says to keep the smoke source and the Marktblatt as they were; the judges' wording says only the plate set and the grill keep act_ names.
- The Bierstand has only 2,027 triangles spare (check_props wants at least 2,000). If the carpenter's stall grows, the cheapest cuts are the swing-tops' wire and rubber rings (about 100), the back row of green Pils (about 260) or one crate (about 450).
- The lite bottle shelves keep 59-65% of the full triangles (target is about a third). These are warnings only; the lite files are small (66 kB and 56 kB).
- The Krakauer uses the same grilled-skin texture as the Thüringer and is told apart by its red tint, thickness and curve. Its own smoked-skin texture would read better up close, but the main texture atlas is full.
- Not mine, from earlier rounds: the 'Transfusion Audit' project title on a Bierdeckel and the vom Fass board reads clinical; this is for the writer or Mac.

## Pass 2

### Judge Opus: Improve
- FAIL Bratwurst works in the engine: standinGoods.js line 68 still reads `if (id === 'wurst' && !has(nodes, 'act_sausage'))`, so the engine will add stand-in sausages on top of the real model. wurst.js line 45 still loops over act_sausage, and there are no handlers for the plate or sauces. The plate and sauce feature Mac asked for does nothing.
- Fix: Engineer: change site/src/engine/standinGoods.js line 68 to also skip when act_wurst_ nodes are present, so stand-in sausages stop being added to the real model.
- Fix: Engineer: rewrite site/src/actions/items/wurst.js to use act_wurst_*, act_roll, act_sauce_* (with fx_sauce_*), act_shaker_curry and act_plate (with plate_spot_0..3), following the action fields in items.json. Remove the act_sausage loop.
- Fix: Optional for Mac's request: put a small bottle group near the middle of the lower shelf as well. Right now the bottles are only at the shelf ends, so the shelf can still look sparse from the front.

Open issues from the builder:
- Engineer: the Bratwurst stall should not go live yet. site/src/actions/items/wurst.js still looks for act_sausage_* / act_roll_*, and standinGoods.js line 68 will add stand-in sausages to the real model. Changing line 68 to also check `!has(nodes, 'act_wurst_')` stops the stand-ins; wurst.js needs the plate, sauce, dust and clear actions described in items.json. My role can't edit site/src.
- The Bierstand now has only 2,005 triangles spare. If the carpenter's stall grows, the cheapest cuts are the swing-top wires and rubber rings (about 100), one back row on a riser (200 to 300) or one crate (about 450).
- The lite shelf files keep 64 to 72% of the full triangles (target is about a third). check_props only warns about this, and the files are small (71 kB and 64 kB).
- act_smoke and act_writing_paper keep their act_ names because the brief says to keep the smoke source and the Marktblatt as they were; the judges' wording says only the plate set and the grill keep act_ names.
- Not mine, from earlier rounds: the 'Transfusion Audit' project title on a Bierdeckel and the vom Fass board reads clinical. This is for the writer or Mac.
