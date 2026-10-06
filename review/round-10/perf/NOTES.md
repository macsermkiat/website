# Round 10: smoother running (draw calls, KTX2 textures)

Mac asked how to make the market run smoother and said "Ok" to fewer draw calls and GPU-compressed textures (2026-10-06).

## Draw calls (bench, software GL, tests/perf.mjs)

| View | Full before | Full after | Lite before | Lite after |
|---|---|---|---|---|
| home | 1372 | 342 | 633 | 340 |
| Glühwein | 1362 | 426 | 617 | 382 |
| bandstand | 1581 | 416 | 610 | 382 |
| Bücherstand | 1224 | 572 | 610 | 510 |
| Riesenrad | 1132 | 566 | 609 | 508 |

Before: review/round-9/engineer/perf.log. After: bench of 2026-10-06 11:13 UTC. Main-pass probe at the home view: full 1550-2035 to 560-848, lite 721 to 499.

How: batched page text, one draw per steam emitter, reversible merges of static meshes per material (the lite-to-full graft still swaps by name), one draw per near crowd figure with skinned shadow stand-ins, lite figures and the band in one draw, flat glass panes in one pass, grill sausages baked at rest, thin vendor glass drawn by blending instead of the transmission pass.

## Textures

KTX2 (Basis) twins of every shipped texture (public/models/ktx2.json), loaded with KTX2Loader; the transcoder lives in public/basis/. A 4x4 probe must transcode first, else the engine keeps the webp files (checked with the wasm removed). First load: full 9.37 MB (+8.7% on webp), lite 7.15 MB (+9.7%); both pass the budget gate.

## Checks

- npm run test:unit: all passed. npm run budget -- --strict: passed.
- Full smoke (all sections): 300/300, no console errors (12:22 and 13:27 UTC runs; the second includes the probe commit).
- Before/after screenshots (this folder): no visible change except the ornament shop counter, where the snow globes and jars are now clear glass instead of white glare (2% of pixels).

## Open

- Real-GPU frame times: run `npm run perf` on Mac's laptop (or the Mac session's browser measurement).
