# Judges on rides, round 1 pass 1

## Fable: Improve

Failed checks:
- The Riesenrad ride camera at gondola_seat_0 gives a view of the market in the engine: Headless-Chromium ride shots at +1 s, +8 s and +12 s show the gondola's own opaque body filling about 60%, 90% and 100% of the frame; the glass band is only 0.72-1.46 m above the cabin floor while the engine looks at a ground-level target, so from 19.6 m up the view drops 36 deg through the lower body. The panel says 'The whole market opens out below you' over a black frame.

Fixes, in priority order:
- Make the Riesenrad ride see out. Raise the gondola glazing so the glass runs from about 0.9 m above the cabin floor up to the roof header (glaze the door too), and move gondola_seat_0 to the cabin centre (about (0,-1.35,0) in the gondola frame) or to the market-facing side with the eye just below the window head. Then verify in the engine: window.__market.act('ferris','ride'); advance(1/8/12) and screenshot #stage at each time. In NOTES.md ask the engineer to clamp the ride look pitch (about -20 deg) so the target stays inside the window band from the top of the wheel.
- Check every landmark in the engineer's scene before the next round, not just the validator: cam_view flights, both rides at three times, and the band view, with the screenshots dropped in review/round-2/rides/. The smoke harness (site/tests/smoke.mjs, or a 40-line Playwright script using window.__market) already does this on software GL.
- Fix the tenor sax proportions: lengthen the body and bow relative to the bell, shrink the bell flare, and flatten the key cups along the body with visible rods; at present it reads as a stubby alto with beads glued on.
- Rounding board: give the mirrors a slightly rough, warm-tinted mirror material or bevelled facets that catch the bulbs so they stop reading as black holes, and enlarge the gilt 'Karussell' lettering (or back it with a dark panel) so it is legible from the rail.
- Ferris hub: put bulbs on the sunburst rays or give the star a gilt face with a real profile; from the square it currently reads as a flat red disc.
- Report to the architect: change the two layout.json asset names (riesenrad.glb -> ferris.glb, karussell.glb -> carousel.glb) or rename the files, so the engine stops relying on its key-search fallback.
- Second pass on the horses: one sculpted master horse (muscle line, open mouth, cut saddle-cloth edge) shared by the 12 nodes with per-horse paint, which also frees triangles; trim instr_bass.lite (62% of full) toward the one-third target.

## Opus: Improve

Failed checks:
- (added) Moving parts clear the structure: gondolas and spokes do not pass through steel as the wheel turns: Wheel steel runs through 13 of the 16 gondola cabins even at rest; only gondolas 0, 1 and 15 at the bottom are clear. With every triangle edge sampled, gondola_4 and gondola_12 contain 424 wheel-steel points, and gondola_8 is crossed by the inner tie at y 24.6 (RI 10.05, 1.15 m below its axle). ferris.py lines 100-108 draw inner ties, mid ties and X-braces at |z| < YR 1.42 inside each gondola's 3 m swing. Relative to the wheel, a gondola passes through steel for wheel angles 42-318 degrees, up to 0.83 m deep. A side view in the browser shows the tie through the window band.
- (added) Static frame stays out of the rotating wheel: ferris.py lines 287-288 run rods from the feet to (+-4.2, 7.6, 0), which is on the wheel's mid-plane 8.1 m from the axle. The front rod crosses the rim at about r 11.9, z 2.17, and the wheel's own members come within 2 mm of the rod axis as it turns, so the spokes sweep through it.
- (added) Lite versions keep the same features: instr_piano.lite.glb has no bulbs_piano and no bulb_warm material, so the lit candles go dark in the lite market (minor). The other lite files keep every named node.

Fixes, in priority order:
- Ferris (blocking): clear each gondola's swing space. Every point within about 3.1 m of a gondola axle and with |z| < 1.40 must be empty. Remove or move the inner ties at RI (ferris.py line 101), and the mid ties and X-braces between the rims (lines 103-108). For example, put the transverse bracing at radii above RO + 0.2 only, move it outside the rim planes, or widen YR so the gondola slab stays empty. Then rerun a clash test that samples edges, like the one used here, over wheel angles 0-360 degrees, for full and lite.
- Ferris: point the back-stay rods (ferris.py lines 287-288) at the A-frame legs or the axle bearings, outside |z| > YR + 0.1, so the spokes and rim no longer sweep through them.
- Ferris: after the clash fix, make a second preview with the wheel turned about 90 degrees, and a ride-seat view from gondola_seat_0 at the top of the wheel. This shows that the gondolas and the rider's view are clear while the wheel turns. The round-1 check only covered the rest pose.
- Piano lite: keep the candle flames as bulbs_piano (bulb_warm) in instr_piano.lite.glb, so the lite market has the same lit candles.
- Update NOTES.md: engine/instruments.js now places instr_* at the slots with musicians, and rides.js already uses gondola_seat_0 and horse_seat_2. Keep the note asking the architect to rename riesenrad.glb and karussell.glb in layout.json.
- Polish, not blocking: give the carousel mirrors a warmer, rougher material, or facets that catch the bulbs, so they stop reading as black ovals. Add bulbs or emissive gilt to the hub sunburst so it stops reading as a red disc. Sharpen the bass f-holes so they read as f's, not brackets.

