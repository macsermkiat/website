# Judges on organizer, round 6 pass 1

## Ship

## Ship

Failed:
- Browser capture reflects the current engine build: shoot_vendors.mjs runs the engineer's 17:54 site/dist with vendor glbs copied in and hand-placed cameras; the stroll's own cam_* framing and the guided walk were never exercised, so the actual visitor view of the stalls is still unverified.

Fixes:
- Rebuild people_anims.glb with a full build.py run so the shared serve/wipe clips match the vendor files' new head pose (currently stale, though never played for vendors).
- Once the engineer's site/src settles, re-run shoot_vendors.mjs against a fresh build and, if walkTo works there, capture the Bücherstand and Bier views from the stroll's own cam_* spots to confirm the counter-distance framing visitors actually get.
- Consider a tiny eye-white or lighter iris dot on the full vendor figures: the painted dark eyes read at counter distance but the Glühwein vendor's sockets look a little hollow in the engine shot.
- Low priority: the Bier trilby in the browser close-up sits very high and slightly floats above the hairline; a 1-2 cm drop would seat it while keeping the face clear.
