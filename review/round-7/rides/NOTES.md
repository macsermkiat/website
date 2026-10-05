# Ride builder, round 7 (short fix round)

Everything ran on the cloud machine (CPU, `NM_THREADS` 2 to 4). Only the Karussell changed: `carousel.glb` and `carousel.lite.glb` were re-exported. The Riesenrad, bandstand and instruments did not change this round. `python3 blender/rides/check_rides.py` exits 0. Nothing is committed.

## 1. The Karussell ticket (round 7 priority)

In round 5 and 6 the browser showed the ticket as a flat grey-mauve card with a pale pink stub (`review/round-5/engineer/JUDGES.md`). The ticket is now a printed paper ticket.

- **Stub.** `rides_ticket_stub.patch` is applied: the stub box and the ticket roll on the counter use the deeper orange tint `(1.0, 0.40, 0.14)`. On top of the stub sits a printed face, `ticket_stub` (material `ticket_stub_card`). It is deep ticket orange with a dark-brown double rule, a carousel mark (pennant, striped scalloped canopy, three horses on poles, platform), FAHRKARTE printed up its length, and the number 0427. The perforation is still there.
- **Card.** The backing sheet `card_contact` is now a printed card (material `ticket_card`, 1024 × 648). It is warm cream `(244, 222, 174)` with a red double border and a fine inner rule. Four small carousel marks sit in red corner boxes. "Karussell · Fahrkarte · Nachtmarkt" is printed along the top, between two printer's diamonds, and "Nr. 0427 · Einmal rund · gilt für eine Fahrt" along the bottom. It all sits inside the 18 mm margin, so none of it runs under the words. The card has faint fibres, cloudiness and slightly darker handled edges.
- **The writing area matches the card.** `write_contact` now uses `ticket_write_card`, a plain texture in exactly the card's cream with no edge darkening. Even before any glow, the writing area does not show as an inset panel.
- **It stays warm at night.** All three ticket materials glow faintly in their own colours: a glTF emissive texture equal to the picture, with emissive factor 0.18. The booth's gooseneck lamp is only an emissive bulb in the browser, and the blue hemisphere light had turned plain paper grey. With the glow, the cream and orange keep their colour whether or not the visitor is reading.
- **Lower lip.** The wooden lip in front of the ticket is lower (12 mm instead of 20 mm), so the bottom border and its small print show.
- **Code.**
  - `art.py`: `ticket_card()`, `ticket_write()`, `ticket_stub()` and `carousel_mark()` (Pillow, drawn at build time with the bundled OFL fonts).
  - `rcommon.image_material(..., emit=)`.
  - `rwrite.surface(..., card=, paper=)` chooses the backing and writing materials; every other surface keeps `write_card`.
  - `carousel.build_booth()`.

### One engine line to review (engineer): `engine_ticket_glow.patch`

`readGlow()` in `site/src/world/surfaces.js` replaces each material's emissive with `0xfff0d8` × map at intensity 0.04. On the ticket that would cut the baked glow from about 0.18 to 0.04 at the moment the visitor reads it. The patch in this folder makes one change: when a material already has an emissive map and colour, its glow copy keeps them and multiplies the intensity by 1.25. Plain paper behaves exactly as before. I did not edit `site/src`. I tested the patch in a scratch copy of the site, and that copy took the browser shot.

**Without the patch:** the ticket still looks printed (the cream, red border, marks and orange stub are all in the albedo), but while it is read it is a little less warm than in the shot.

## 2. Other open points from round 6

- **Placard reading cameras and holding the wheel.** The engineer has adopted these (`surfaces.js` reads `cam_read_question_N`, with `holdsWheel`), so this point is closed for my role.
- **Inset panel while reading.**
  - The engine now glows the `card_<name>` backing along with the `write_` quad (`backingOf()`).
  - On the ticket, the writing area and card are now the same cream, so nothing shows as a panel (see the browser shot).
- **Stub grey-blue at night.** Fixed (section 1).
- **Horse outline.** The full master horse is back up to 1,600 triangles (`horse.FULL_TRIS`, was 1,300), as the judges suggested. That adds 3.6k triangles to `carousel.glb` (73.0k of 80k). Lite is unchanged at 560.
  - `carousel_horses.jpg` shows the neck and hind leg from about a metre.
  - The rump still shows a slight polygonal outline at that distance.
- **check_clash.py and the architect's stroll check.** Not re-run this round. The Riesenrad did not change, and the booth's footprint did not change.

## Previews (this folder)

| File | What |
|---|---|
| `browser_read_carousel_ticket.jpg` | The ticket being read in the browser (lite market, SwiftShader, scratch copy of the site with `engine_ticket_glow.patch`): orange printed stub, cream card, red border, corner marks, the words on matching paper |
| `carousel_read_contact.jpg` | Cycles, from `cam_read_contact`, 960 × 540, 24 samples |
| `carousel_preview.jpg` | Cycles night preview of the Karussell, 1280 × 720, 48 samples, rendered again this round |
| `carousel_horses.jpg` | The 1,600-triangle horses close up, 960 × 540, 24 samples |
| `ferris_preview.jpg`, `bandstand_preview.jpg` | Copied from round 6 (these models did not change) |

## Triangles and file sizes (after optimize.mjs; `check_rides.py`)

| File | Triangles | MB | Budget |
|---|---|---|---|
| ferris.glb | 72,615 | 1.49 | 80k / 3 MB |
| ferris.lite.glb | 25,003 | 0.73 | |
| carousel.glb | 73,046 | 1.26 | 80k / 3 MB (7k spare) |
| carousel.lite.glb | 24,418 | 0.50 | |
| bandstand.glb | 29,834 | 0.73 | |
| bandstand.lite.glb | 10,398 | 0.30 | |
| instr_sax / .lite | 6,346 / 1,556 | 0.06 / 0.02 | |
| instr_piano / .lite | 3,616 / 1,524 | 0.10 / 0.05 | |
| instr_bass / .lite | 2,994 / 922 | 0.08 / 0.05 | |
| instr_drums / .lite | 6,136 / 2,092 | 0.10 / 0.06 | |
| instr_sax_stand / .lite | 6,600 / 1,690 | 0.07 / 0.03 | |
| bandstand + 4 instruments | 48,926 (lite 16,492) | 1.07 (lite 0.47) | |

The named nodes did not change:
- rot_wheel, gondola_0..15 (pivot at the hanging point), gondola_seat_0, rot_platform, horse_0..11 and horse_seat_2;
- slot_sax/piano/bass/drums;
- cam_view/cam_target on all three;
- the write_ and cam_read_ nodes.

New nodes: `ticket_stub`; `card_contact` now uses `ticket_card`.

## Rebuild

```
NM_ROUND=7 NM_THREADS=4 /home/claude/tools/bpy-venv/bin/python blender/rides/carousel.py --no-render
NM_READ=contact NM_ROUND=7 NM_THREADS=2 .../python blender/rides/carousel.py --preview-only --res 960x540 --samples 24
NM_ROUND=7 .../python blender/rides/carousel.py --preview-only --res 960x540 --samples 24 \
    --cam 1.25,-5.0,1.85,0.05,-3.7,1.45,32 --preview-name carousel_horses
python3 blender/rides/check_rides.py
```

bpy segfaults at exit (139) after writing everything, which is harmless.

**Browser shot.**
- Make a scratch copy of `site/` inside a folder that also links `content/` (the market plugin reads `../content`). Symlink `node_modules` and `public`, and add the repo to `server.fs.allow` so the fonts load.
- Call `__market.settled()` before `freeze(true)`. If it is frozen before the rides stream in, `read('carousel.ticket')` returns false.

## Open issues

- **Engine patch.** Until `engine_ticket_glow.patch` (one hunk in `readGlow`) is applied, the ticket dims slightly while it is read. The engineer should re-shoot `read_carousel_ticket.jpg` on the real site after applying it.
- **Horse rump.** At the ride-seat distance it still shows a slight polygonal outline. There are 7k triangles spare if the judges want more.
- **Ticket text.** The "best way to reach me is ." sentence on the ticket has an empty contact field from `content/contact.md`. That is the writer's and Mac's to fill in, not the model's.
- **Checks not re-run.** `check_clash.py` and the architect's stroll check were not re-run, because the Riesenrad and the booth footprint did not change.
