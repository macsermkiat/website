# Judges on vendor, round 1 pass 1

## Fable: Improve

Failed checks:
- Deco stall + goods stay under the 20k deco budget: check_props.py and my own counts: Lebkuchen 20,853, Mandeln 22,874, Kerzen 22,955, Spielzeug 24,352, Schmuck 26,063 are over 20k; the carpenter's stalls alone are 11.8–19.0k so the goods (3.8–7.6k) cannot fit without a budget decision.
- Ambient occlusion baked into the glTF occlusion texture (contract 'Lighting approach'): No prop glb has an occlusionTexture on any material (parsed all 17); images are only atlas color/rm/normal (+coal). Vendor acknowledges this in NOTES issue 7.
- At most 2 light_ empties per section stall: prop_books_counter.glb adds light_lamp (T 0.52,0.305,-0.068) to stall_buecher which already has light_0 and light_1, giving three; engine/lighting only applies a global cap (14 desktop / 4 lite), no per-stall cap.
- Lite versions have about a third of the triangles (contract 'Budgets'): Lite/full ratios: gluehwein counter 55%, gluehwein shelf 56%, bier counter 50%, bier back 59%, books counter 75%, kerzen 74%, spielzeug 77%, schmuck 70%; only wurst (27%), books shelves (34–35%), maroni (33%) and kaese (49%) come close. All lite props + lite atlas still total only 0.99 MB.
- Previews are complete and readable: deco_goods_contact_sheet.jpg crops the outer goods on Spielzeug (nutcrackers, rocking horse), Mandeln (roaster) and Kerzen (right edge); the Bratwurst 'paper trays' read as a plain white cube and the tray stack is off-frame right.

Fixes, in priority order:
- Deco budget: get a market-owner decision (goods-only 20k, or 25k combined, or carpenter trims the deco stalls); until then cut Schmuck (7.6k), Kerzen (7.5k) and Lebkuchen (6.2k) goods toward ~4k each, e.g. fewer lathe segments on baubles and candles and instanced hearts, so at least Lebkuchen and Kerzen pass at 20k.
- Bake ambient occlusion into the glTF occlusion texture (or vertex colour as a stopgap) for all 17 sets, as the contract's lighting approach requires; mugs, books and barrels currently have no contact shading of their own.
- Bücher counter: drop light_lamp or document it as replacing light_1, so the section stall stays at 2 light_ empties; if the lamp glow should stay, keep only the emissive lamp_glow material.
- Lite versions: bring the section sets nearer the contract's one-third target (gluehwein counter/shelf, bier counter, books counter are 50–75%); use lower lathe/sphere segment counts and drop the coasters, badges and small caps in lite mode.
- props.json: agree the form with the engineer and ship one (the engine reads 'sets'); remove the duplicate map so the two cannot drift.
- Re-render the deco contact sheet with wider tiles (or per-stall frames) so no goods are cropped, and give the Bratwurst paper-tray stack a visible edge/rim so it does not read as a white cube.
- Fill slot_shelf_2 on the Glühwein and Bier stalls (even a light set: spare mugs, steins, folded cloths) so the back walls are not bare when the camera enters those places.
- Add a note or check in check_props.py that fails when the Glühwein and Bier stall totals (58.4k/58.5k) leave less than ~2k headroom, so future additions by either owner are caught.

## Opus: Improve

Failed checks:
- Animated hierarchy works with the engine's actions: act_sausage_0..7 are root children, not children of act_grill_swing. stalls.js swings act_grill_swing every frame by 0.035–0.1 rad about a pivot about 0.4 m above the grate. The grate moves 1–4 cm while the 8 sausages stay put, so they hover over or sink into it.
- Close-ups show believable materials: glazed ceramic, copper, glass with foam, charred sausages, worn book cloth: The mugs (glaze and prints) and the hammered copper kettle are convincing, and the book spines are good. But the sausages are uniformly pale tan with barely visible marks and look like raw hot dogs. The coals read as orange sponge lumps, not glowing embers. Beer foam is a flat white cylinder band with a black rim line. The bier_back barrels are cartoon orange with drawn crack lines.
- Contract: AO baked into the glTF occlusion texture: BUILD.md requires an AO bake. No prop material has occlusionTexture (checked in the JSON). The builder admits it, so mugs and books won't sit down on the counter in the browser.
- Contract checker is honest: check_props.py prints 'ALL CHECKS PASSED' while listing five deco stalls as 'over'. The budget miss does not fail the check.
- Previews are close-ups that sell the goods: The section renders are wide shots of the whole 2.2 m set, with goods filling about 20% of the frame, not close-ups. The counters read sparse: Bücher has 4 items on the counter, Wurst has large empty stretches, and the right-hand box on the Wurst render is cropped. Contact-sheet tiles crop the outer goods.

Fixes, in priority order:
- Parent act_sausage_0..7 under act_grill_swing, or under a child of it, keeping their world positions. Otherwise the engine's constant grate swing leaves the sausages floating over or sinking into the grate.
- Make the sausages look grilled: darker browned skin, clear diagonal char marks and blistered ends, and a larger atlas region than the current 256×64. Rebuild the coals so they are mostly black and grey ash, with emissive only in the cracks, so they read as embers.
- Bake AO as the contract requires: into the glTF occlusion texture (a per-set AO atlas or a second UV), or at least into COLOR_0. Check it in the engine at the Glühwein and Bücher counters.
- Fix the beer: a foam head with a domed, bubbly top and a slight spill over the rim, no black rim band, and visible glass thickness. Retexture the bier_back barrels with real stave wood and iron hoops, not orange with painted cracks.
- Fill the counters: add goods to the Bücher counter (more stacks, a tray of bookmarks, price cards) and to the empty stretches of the Wurst counter. Fill slot_shelf_2 on Glühwein and Bier, or confirm with the art director that the carpenter hides it.
- Re-render real close-ups: one tight hero shot per set (for example the pot and mugs, the grill, the tap and glasses) in addition to the wide shot. Fix the cropped Wurst box and the contact-sheet crops.
- Make check_props.py fail, or at least print WARN, when a deco total is over budget, and escalate the 20k deco question to the architect or carpenter instead of reporting ALL CHECKS PASSED.
- Bring the lite versions to spec: a 512 px lite atlas, and a lower lite triangle count on the glühwein, bier, deco kerzen, schmuck and spielzeug sets, which are 55–75% of full.
- Resolve the Bücher light count (3 lights against a cap of 2 per section stall): either drop light_lamp or tell the lighting designer to use it in place of one of the stall's lights.
- Minor: seat the grill bowl on the firebox top at y 0.026 instead of 0 so it no longer sinks into it. Check that the 3 cm frame pegs at shelf y 0.22 don't pierce books near x ±0.95.

