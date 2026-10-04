# Organizer, round 6

Inputs: `review/round-4/organizer/JUDGES.md` (Improve: vendor faces in close-up, no in-browser check), my round-4 `NOTES.md`, and the round-6 brief. There is no `review/round-4/CODEX_JUDGE.md` on disk. The only Codex notes that mention the crowd are in `review/round-2/CODEX_JUDGE_WIP.md` (repeated clips, `people_anims.glb` not loaded), and both were fixed in round 3.

Only the four vendor figures changed this round. The eight crowd figures, the four musicians, `people_anims.glb` and `site/src/crowd.json` are the round-4 files.

## 1. Vendor head pose: faces turn up to the customer

**Cause.** In `serve`, the trunk leans about 0.3 rad over the counter (hips, spine and chest), and the head pitched down a further 0.18 rad on top of that. `wipe` leaned about 0.2 rad and looked down 0.12 rad. In every close-up the vendors looked at the counter, and the Bier vendor's face was lost under his brim.

**Fix (`blender/people/anims.py`):**
- `serve`: the neck (−0.08·k − 0.02) and the head (−0.14·k + 0.02) take back most of the lean, so at the hand-over (k = 1) the face meets the customer and the camera. There is also a small neck turn toward the mug hand.
- `wipe`: neck −0.06 and head −0.06 (plus a slow nod of up to 0.04), so the vendor looks out at the square while the left hand wipes.
- **Bier hat:** `hat_trilby` has a new `tilt` spec key (default 0.08, so the other trilby wearers are unchanged). The Bier vendor's hat is set to −0.07, pushed back on the head. The front brim no longer shades the eyes.

## 2. Face definition (vendors only: spec key `face_detail`)

These are in `blender/people/figures.py`, and only figures with `face_detail=True` (the four vendors) get them. The crowd is seen from farther away and stays as it was.
- **Eye sockets:** a shallow lens of shaded skin (skin × 0.8/0.7/0.7) behind each eye, so the eye sits in a hollow instead of on a flat plane. The eyes sit slightly proud of the lens.
- **Brows:** a little thicker (6.5 mm instead of 5) and darker (hair × 0.6). They lie almost level (0.03 rad instead of 0.12), so the round-4 "worried" slant is gone.
- **Nose:** the wedge gets vertex shading: a cold-reddened tip, a darker underside (× 0.62) and darker wings. It reads as a form under the stall lamp.
- **Cheeks and jaw:** a vertex-colour flush on the cheeks (gaussian, tint 1.04/0.79/0.73) and a soft shade under the cheekbones. It is painted on the albedo, so no lighting is baked in.

## 3. Warmer vendor skin (the lighting judges found faces grey)

The crowd shader (`crowd.js` `liftMaterial`) adds a cool emissive lift, proportional to albedo, with a tint of 0.55/0.5/0.62. It cools low-saturation skin toward grey. I can't change site/src, so the albedo carries more warmth instead. Vendor skin, round 4 → round 6:

| vendor | round 4 | round 6 |
|---|---|---|
| Glühwein | #e8b495 | #e8a47d |
| Bier | #e0a888 | #e09a73 |
| Bratwurst | #caa084 | #d09a76 |
| Bücher | #e2b397 | #e4a47f |

`browser_vendors.jpg` shows the result in three.js: warm, not grey, and not orange. The cheek flush shows at close-up distance.

## 4. Browser (three.js) checks, the open point from round 4

`blender/people/shoot_vendors.mjs` is the capture script. It serves a copy of the engineer's current `site/dist` with the new vendor glbs swapped in, under Playwright with SwiftShader at `?quality=full&lod=300`, so every person draws the full figure. The market is frozen and the clips are stepped on 3 s with `advance()`, so the figures stand in animated poses rather than frame 0. Then the script places the camera itself and draws a frame with `__market.snapshot()`.

About the guided walk (`openPlace`/`walkTo`): in this build, `walkTo` from the frozen home view returns false, and an unfrozen walk did not arrive in 22 minutes of software-GL frames, the same failure as round 4. So I no longer use the walk. The script places the camera directly, which takes about 1 to 2 minutes per shot. The script is documented for the next capture.

- **`browser_vendors.jpg`:** all four vendors, from the chest up across their counters, in three.js under the lighting designer's stall lights. Every face reads: eyes, brows, nose and mouth, the Bücher vendor's glasses and beard, and the Bier vendor's face clear under the pushed-back hat. All four heads are up.
- **`browser_buecherstand.jpg`:** the open Bücherstand from a high three-quarter view, with every person shown (the close-up hiding rule is switched off for this shot). Both browsers stand **in front of** the book carts and face them: the left one at the Lebenswege cart, the right one at the Entscheidungen cart. Nobody stands inside a cart, a wing rack or the booth. The Bier queue stands outside the left wing.

## 5. Previews (Cycles, CPU, NM_THREADS=2)

- `lineup.jpg`: all 16 figures, 1280x720, 48 samples (the crowd on top; vendors and band below).
- `band.jpg`: the four musicians at the bandstand slots with the ride builder's instruments, 1280x720, 48 samples.
- `group_chat.jpg`: a group chatting with a child nearby, 1280x720, 48 samples.
- `vendors_closeup.jpg`: the four vendors, chest-up, `serve` at 2.6 s, 1280x560, 40 samples. `vendors_before_after.jpg` puts it under the round-4 close-up.

## Budgets (budget 5k triangles and 0.4 MB per figure)

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
| **people_vendor_gluehwein** | **4916** | 115 kB | chat, drink, idle, serve, walk, wipe |
| **people_vendor_bier** | **4483** | 111 kB | same |
| **people_vendor_wurst** | **3913** | 107 kB | same |
| **people_vendor_buecher** | **4486** | 116 kB | same |
| lite crowd (8) | 1484 to 1800 | 49 to 52 kB | chat, drink, idle, sit, walk |
| lite band (4) | 1544 to 1669 | 40 to 42 kB | play, rest |
| lite vendors (4) | 1409 / 1699 / 1409 / 1550 | 35 to 38 kB | serve, wipe |
| people_anims.glb | 0 | 68 kB | 13 shared clips |

The face detail costs each full vendor about 112 triangles. The Glühwein vendor is the closest to the cap, at 4916 of 5000. `gltf-transform inspect site/public/models/people_vendor_bier.glb` lists the animations chat, drink, idle, serve, walk and wipe, and the materials coat, body, hat, scarf and mug. Every figure has separate `coat`, `scarf` and `hat` materials for recolouring.

`crowd.json` is unchanged and parses: 4 vendors, 3 queues, 10 walkers plus 2 more, 19 groups, 4 browsing entries, 2 benches and 4 musicians.

## Files changed

- `blender/people/anims.py`: the serve and wipe head and neck pose.
- `blender/people/figures.py`: `face_col()`, eye sockets, brows, nose shading (behind `face_detail`), and the `tilt` key for `hat_trilby`.
- `blender/people/specs.py`: vendor skin, `face_detail`, and the Bier hat tilt.
- `blender/people/shoot_vendors.mjs`: new, the browser capture for vendor faces and the Bücherstand.
- `site/public/models/people_vendor_{gluehwein,bier,wurst,buecher}{,.lite}.glb`: rebuilt with `build.py --only people_vendor_* --no-anims`.
- `review/round-6/organizer/`: these notes and the previews listed above.

No third-party assets, so `CREDITS.md` is unchanged.

## Open issues

- **`people_anims.glb` was not rebuilt.** Its `serve` and `wipe` keep the round-4 head pose. Every vendor file, full and lite, carries its own `serve` and `wipe`, and crowd.js prefers a figure's own clips, so the shared copies are never played for vendors. A full `build.py` run (without `--only`) would refresh the library.
- **The browser shots come from the engineer's 17:54 `site/dist`**, with the new vendor glbs copied in. That build was not rebuilt from the engine sources the engineer is editing now. The capture used manual cameras because `walkTo` refused in the frozen harness. The views are the stall interiors at counter distance, but they are not the stroll's own `cam_*` framing.
- **The lite vendors have no eyes or brows** (by design: the lite set is for distance). The cheek flush and nose shading are in the lite files. With `?lod` at its default, a vendor more than about 14 m from the camera draws the lite figure.
- **The faces are still stylised:** painted eyes, a wedge nose, no eye whites. They read at counter distance, but not in an extreme macro shot.
- Carried over: seated long coats read a little stiff from above; far mug-less lite figures stand with the hand at the coat front.
