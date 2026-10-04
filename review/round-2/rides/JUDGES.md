# Judges on rides, round 2 pass 1

## Ship

Failed:
- (added) Ride views in the engine look right on lite: engine_lite_ride_carousel.jpg: the 720-tri lite horses read as faceted, origami-like blocks right in front of the ride camera. engine_lite_view_ferris.jpg: the wheel is still a black silhouette with only bulbs (lighting role). engine_lite_view_band.jpg: the music stand covers the saxophonist. No full-market engine shots were taken this round.
- (added) Every round-1 JUDGES.md point addressed: Canopy light_2 under rot_platform, softer gondola_glass (alpha 0.08, rough 0.18), bass C-bouts/eyes, instr_sax_stand, longer tenor, finer grain, and booth rails, grille and posters are all done. But the master horse was meant to free about 15k tris, and the carousel is still 78.6k (1.4k under the cap).

Fixes:
- Lighting designer (cross-role, biggest visible gap): light the Riesenrad at light_2 on full and add a ground pool or fill on lite. In engine_lite_view_ferris.jpg the cream steel is still a black silhouette.
- Lite carousel horses: raise the lite master to about 1,100 tris and pay for it by cutting lite car_gilt (4.4k) and car_paint (3.6k). The ride-seat view (engine_lite_ride_carousel.jpg) is the carousel's main close-up on phones, and it currently looks faceted.
- Free carousel headroom as round 1 asked: bake a normal map from the sculpt onto a lighter master horse (about 1.4k tris), and trim bulbs_carousel (5.4k) and car_poles (3.6k on 12 poles). Aim for 10-15k under the 80k cap.
- Move the music stand about 20 cm to the saxophonist's right so it stops covering the player in the default band view.
- Double bass: add more outline segments to the bouts and corners so the silhouette is not faceted in close-up, and give the top a straight, fine spruce grain instead of the wavy walnut-like grain.
- Shape the horse saddle with a seat dip and skirt edge. Light or raise the booth 'Kasse' sign so it reads.
- Take full-market engine shots of the three landmarks and the band once the machine allows, to confirm the externalised deco_kit/rides_kit maps load and look right at full.

## Ship

Failed:
- (added) Lite horses hold up from the ride seat: engine_lite_ride_carousel.jpg: the 720-triangle lite horses one metre from horse_seat_2 are visibly faceted along the neck and barrel, and the saddle is a flat-shaded blob; this is the closest a visitor ever gets to a ride model and it is the weakest frame in the set (the full horses in carousel_horses.jpg are fine apart from the smooth saddle).
- (added) Full-market engine evidence for this round: No full-market engine screenshots were retaken (NOTES.md says software GL was too slow); only lite shots exist, so the gilt-at-0.5 fix, the new gondola_glass and the booth art are verified in Cycles and lite only. Not blocking given the lite shots load and texture correctly, but the full market's wheel steel and gold still need an engine check once the lighting pass lands.

Fixes:
- Carousel lite horses (the one view where a visitor is 1 m from a ride model): give the lite carved mesh about 1,000-1,200 triangles, or bake a normal map from the sculpt onto a lighter master and ship it on both tiers; either way carve the saddle (seat dip, skirt, stitching) since it is a smooth blob in carousel_horses.jpg and a flat blob in engine_lite_ride_carousel.jpg. The lite carousel is at 29.5k, so there is room.
- Move the music stand about 20 cm to the saxophonist's right: in engine_lite_view_band.jpg it sits in front of the player from the default band view.
- Retake the three full-market engine views (and the Ferris ride frame) after the lighting designer's rot_wheel bulb-bounce and light_2 wash land, so the gilt at metallic 0.5, the lighter gondola_glass and the cream steel are confirmed in three.js at desktop quality, not only in Cycles and lite.
- Protect the shared-texture dependency: add a small check (in rcommon or scripts/budget.mjs) that every URI referenced by the ride glbs exists in site/public/models, so a carpenter re-export of the kit cannot silently restyle or break the rides.
- Cross-role, already requested in NOTES.md and worth the market owner's push: lighting designer lights light_2 on the Riesenrad (steel is still near black in engine_lite_view_ferris.jpg); engineer loads instr_sax_stand.glb when no player is at slot_sax and excludes people_band_* from the bandstand budget line; organizer refits the sax player's hands to the 10 % longer tenor.
- Use the 1.4k headroom under the carousel's 80k cap by baking the horse normal map (about 8k triangles freed) before adding any more carousel detail.

