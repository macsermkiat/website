# Organizer, round 4 (polish)

Inputs: `review/round-3/market/JUDGES.md` (the only round-3 verdict that names the organizer), `review/round-4/lighting/NOTES.md` (vendor glare and faces). There is no `review/round-3/organizer/` folder and no `review/round-3/CODEX_JUDGE.md` on disk, so the market judges' notes were the only list to work from.

## 1. Bücherstand browsers stand in front of the carts and racks

**Cause.** `crowd_plan.py` stood the two Bücherstand browsers at three.js local z 1.95 (Blender stall frame y -1.95). The carpenter's book carts have their front edge at Blender y -2.26 (`buecher_sections.json`), so both browsers stood inside the carts. The planner's checks missed this for two reasons. The generic section obstacle stops at local z 1.6. And browsers are not checked against their own stall.

**Fix (`blender/people/crowd_plan.py`, re-run, `site/src/crowd.json` regenerated):**
- The browsers now stand at Blender y **-2.60** (local z 2.6, `BUECHER_BROWSE_Z`), at x -1.5 and +1.5: in front of the Lebenswege and Entscheidungen carts, about 0.34 m clear of the carts' front edge. Each has an explicit `rotY` so he faces his own cart (2.24 and 2.45 rad; the stall's rotY is -0.8).
- New obstacle **"buecher carts and racks"** covers the carts and the angled wing racks: two rects, local z 1.85 to 2.33 at x ±2.95, and z 1.1 to 1.85 at x ±2.6. It has its own name, so the stall's browsers are checked against it too. Every free group is nudged clear of it. Before, the group at local (-2.4, 2.9) could have a member inside the left wing rack.
- Walker path 1 (in front of the section stalls) now ends at (11.2, 6.6), short of the right-hand browser. It also bends under the string-light pole at (-7.8, 5.6). That pole clipped walkers 2 and 3 in the round-3 file, after the architect moved the poles.
- `crowd_plan.py` reports **no problems** (round 3 reported 4 pole clearances). Everyone near the Bücherstand, in the stall's Blender frame: the browsers at (-1.51, -2.60) and (1.50, -2.60); a Bier queue member at (-3.03, -1.48), outside the left wing; and one member of `group_buecherstand_6` at (-3.06, -0.58), beside the booth. Nobody stands inside a cart, rack or booth.
- `crowd_map.jpg` is the new top-down plan.

The engine's close-up rule (crowd.js: people on the sight line of a close camera step out of the shot) still applies. A browser on the `cam_cat_lives` or `cam_cat_decisions` line is hidden while that close-up is open.

## 2. The Bier vendor's hat, and vendor faces and light clothing

**Hat.** The round-3 hat was a trilby with a 4 cm brim, a short straight crown and a grey-green felt (#3f4a39) that was almost the coat's colour. Under the stall lamp it read as a grey cylinder. It is now a Bavarian felt hat (`figures.py` `hat_trilby`, with new optional spec keys, so the other trilby wearers are unchanged):
- deep bottle-green felt `#1f3a26`, darker than and distinct from the waistcoat;
- a taller crown (11.2 cm) that narrows to the top (`taper`), with the front sides pinched in (`pinch`);
- a 5.8 cm brim, turned up at the back and dipped at the front (`back_up`);
- a brown cord band `#6e5232` and a pale Gamsbart-style brush with a brass clasp at the back left (`brush`, `clasp`): 9 thin tufts in a cone (5 in lite).

`bier_hat_before_after.jpg` shows the round-3 hat, the new hat from the front, and the new hat from the back left.

**Faces and light clothing (with the lighting notes).** The lighting designer's shader handles the glare: it puts a highlight shoulder on figures and adds a close-up fill. Their open point was that faces read "a little grey and cool" because the skin albedo has little saturation. On my side:
- Vendor skin is warmer and a touch deeper: Glühwein #eec3a8 → #e8b495, Bier #e7b69a → #e0a888, Bücher #e9c2ad → #e2b397. The Bratwurst vendor's skin was already #caa084.
- Light cloth is pulled off pure white, so it has less to blow out under `light_0`: the Bier sleeves #e8e2d6 → #d9cfbc (linen), the Glühwein scarf #e6d8c0 → #d6c4a4 (cream wool), the Bratwurst apron #e8e4dc → #d8d1c2.
- `vendors_closeup.jpg` (Cycles, 1280x560, 32 samples, under the preview's market lights, `serve` at 2.6 s) shows all four vendors from the chest up. The faces read with their features, and the light cloth keeps its shading.

Only the four vendor figures were rebuilt (`build.py --only people_vendor_* --no-anims`). The crowd figures, the band and `people_anims.glb` are unchanged.

## Budgets (after the web passes; budget 5k triangles and 0.4 MB per variant)

| figure | tris | size | clips |
|---|---|---|---|
| people_man_coat | 4560 | 125 kB | chat, chat_free, drink, idle, idle_free, laugh, sit, walk, walk_free |
| people_woman_coat | 4864 | 129 kB | same |
| people_man_parka | 4972 | 129 kB | same |
| people_woman_older | 4836 | 129 kB | same |
| people_man_older | 4536 | 127 kB | same |
| people_woman_young | 4708 | 125 kB | same |
| people_child_boy | 4980 | 130 kB | same |
| people_child_girl | 4756 | 126 kB | same |
| people_band_sax / piano / bass / drums | 4532 / 4836 / 4656 / 4576 | 116 / 121 / 117 / 119 kB | chat, drink, idle, play, rest, walk |
| people_vendor_gluehwein | 4804 | 113 kB | chat, drink, idle, serve, walk, wipe |
| people_vendor_bier | 4371 | 110 kB | same |
| people_vendor_wurst | 3801 | 106 kB | same |
| people_vendor_buecher | 4374 | 115 kB | same |
| lite crowd (8) | 1484 to 1800 | 49 to 52 kB | chat, drink, idle, sit, walk |
| lite band (4) | 1544 to 1669 | 40 to 42 kB | play, rest |
| lite vendors (4) | 1409 to 1699 | 35 to 38 kB | serve, wipe |
| people_anims.glb | 0 | 68 kB | 13 shared clips |

Every figure has the materials `coat`, `scarf`, `hat`, `body` and `mug`. The full files carry walk, idle, chat and drink (checked with `gltf-transform inspect` on `people_vendor_bier.glb`). `crowd.json` has 90 people and 4 musicians: 4 vendors, 3 queues, 10 walkers plus 2 more, 19 groups, 4 browsing entries and 2 benches.

## Files changed

- `blender/people/crowd_plan.py`: browser spots, cart/rack obstacle, walker path 1.
- `blender/people/figures.py`: `hat_trilby` gains taper, pinch, back_up and brush.
- `blender/people/specs.py`: Bier hat; vendor skin and light-cloth colours.
- `site/public/models/people_vendor_{gluehwein,bier,wurst,buecher}{,.lite}.glb`: rebuilt.
- `site/src/crowd.json`: regenerated.
- `review/round-4/organizer/`: these notes, `crowd_map.jpg`, `bier_hat_before_after.jpg`, `vendors_closeup.jpg`.

No third-party assets were used, so `CREDITS.md` is unchanged.

## Open issues

- **No in-engine vendor close-up this round.** `__market.openPlace` is now the guided stroll's `walkTo`, so the lighting designer's `shoot-market.mjs @open=` stays on the home view. The machine was at load 10 with other builders' Chromium instances, and one software-GL snap took about 9 minutes. The 50-minute capture run ended before it reached the Bücherstand browser view. So the vendor check is the Cycles close-up, and the browser check is the planner's clearance report and `crowd_map.jpg`. The three.js check of the new hat and skin is for the next full-market capture: the engineer's panel shots, or the lighting designer's.
- Faces are still simple: a nose wedge, with eyes and brows in vertex colour. They read at panel distance, not in an extreme close-up.
- Carried over from round 1: seated long coats read a little stiff from above; far mug-less lite figures stand with the hand at the coat front until the engine retargets `people_anims.glb`.
