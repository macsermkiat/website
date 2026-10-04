# Round 4: lighting and atmosphere (lighting designer)

This was a polish round. It covers the two round-4 priorities and the lighting fixes the round-3 judges asked for:

- the whole-market judge: "Tame the glare on the stall vendors' light clothing … fill the faces so they read";
- the carpenter judges: "canopy shadow on the upper rack boards, and canopy bulbs that light nothing in three.js".

No round-3 lighting folder exists, because lighting was not judged in round 3. The last lighting verdicts are in `review/round-2/lighting/JUDGES.md`. Their only open point is the real-GPU frame time. I still cannot measure it: this machine has no GPU and this session cannot reach Mac's laptop. The adaptive MSAA step at 16.7 ms is still in place. `review/round-3/CODEX_JUDGE.md` does not exist; the round-2 Codex points were closed in round 2.

`site/src/lighting/index.js` still exports `createLighting({ scene, renderer, camera, lite })` and returns `{ composer, update(dt, t), setSnow(on), dispose() }` plus the engine helpers. This round adds one helper, `markFigures()`. All settings and the reasons for them are in `site/src/lighting/settings.js` (`figure`, `canopy`) and `site/src/lighting/README.md` (the two "round 4" sections).

## 1. Vendors' clothes and faces

**Cause.** A vendor stands at `slot_vendor`, right under the stall's interior lamp (`light_0`, 34 cd, about 0.7 m over his head). Per unit of albedo, his shoulders, sleeves and a pale scarf took 30 to 50 times the light the back wall gets. A white sleeve came out at a linear radiance of about 13, and AgX turns that white. His face is vertical and turned away from the lamp, so it got grazing light only and read as a dark smudge.

**Fix (figures only; the rest of the scene is unchanged).** Every material of a figure gets the define `LIGHTING_FIGURE`. A figure is a skinned mesh under the crowd's `crowd` group, or a material the crowd lifted (`userData.crowdLift`) or flagged `userData.figure`. `markFigures()` runs every 2 s of wall time because the crowd loads after the lighting. The shared shader patch (`shading.js`) then adds two terms:

- **Highlight shoulder:** the direct light on a figure is linear up to `knee` 0.9 and rolls off softly toward knee + `range` 1.5 above it, measured by luminance with the hue kept. A white sleeve under the lamp now sits at about 2.2 in place of 13. It is still the brightest part of the figure, but it reads as lit cloth. Cloth keeps 35 % of its direct specular.
- **Close-up fill:** a soft warm light from the viewer's side, `[1, .72, .5]` at irradiance 1.7, weighted `0.25 + 0.75 × N·V`. It stands for the light the counter, the cobbles and the crowd bounce back at a face. It is full within 4.5 m of the camera and gone past 9 m. The entered views (`cam_view` is about 5 m from the vendor) get it, and the crowd in the home view does not.

The stall itself is not touched: no light was dimmed, and the bulbs, back wall, shelves and counter keep their round-2 values, so the warm look stays.

**Where to see it:**
- `vendors_bench.jpg`: the real `stall_bier` and `stall_gluehwein` glbs with their own `light_` empties and the real vendor glbs at `slot_vendor`, before and after, on the test bench (new option `?figure=`).
- `market_bier.jpg` and `market_glueh.jpg`: the real market, entered through `openPlace`, before (round-3 code) and after. `vendor_crops.jpg` crops both vendors from them.
  - **Bier:** before, the white sleeves glow and bloom. After, they read as white cloth with shading, the green waistcoat and brown apron read, and the face is lit.
  - **Glühwein:** before, the pale scarf blooms over the coat. After, it reads as a cream scarf and the face reads under the hat.
  - The bulbs, shelves, back wall and counter are unchanged.
  - The Bier camera is further back in the "after" frame. The engineer's round-4 camera change landed between my two runs; the before run had loaded the code about 100 minutes earlier.

## 2. Bücherstand side racks

**Cause.** There were two. (1) The rack canopies shadow the upper boards from the stall's front light (`light_1`). (2) The canopy bulbs did light something, but in the wrong place. `bulbStrings` joins strings that are up to a cell (0.35 m) apart in height, so each rack string, 0.4 m under the eave string, became part of the eave string's glow and lit the eave.

**Fix.** `canopyGlows` (in `index.js`) clusters each stall's bulbs again with finer cells (0.2 m wide, 0.1 m tall). A cluster gets a **canopy wash** when it meets three conditions: it hangs at least 0.15 m under the model's top string, it is at least 0.6 m long, and it is more than 1.6 m in plan from every `light_` empty. The wash is a one-sided segment glow 0.3 m under the bulbs and 0.3 m toward the stall's front, with intensity 7 and reach 1.8 m. It lights only between 0.25 m over the base and 0.28 m under the bulbs.

An earlier version lit right up to the bulbs, and the canopy fascia and the section signs, which hang right under the bulbs, blew out. That is why the wash stops 0.28 m under them.

The wash is the light those bulbs would throw onto the boards and the spines. On the bench it finds exactly the two rack strings, and the Glühwein lambrequin and the Bücherstand eave are left alone. It is a glow, not a three.js light, so full and lite get the same light, lite keeps its four real lights, and no third `light_` empty (or carpenter change) was needed. The washes take slot priority 1, like the stall interiors, so the racks are lit from the home view as well.

**Where to see it:**
- `books_bench.jpg`: the shipped `stall_buecher.glb` on the bench, without books (props are placed only in the market), before and after.
- `market_books.jpg`: the entered Bücherstand in the market, with the books, and `books_racks.jpg` (a crop): the top boards and the books on them under both canopies are lit warm now, and the section signs stay readable.
- The first "after" market run also put 23 washes on the Christmas tree's short, low strings. Each would have taken a priority glow slot. Washes are now limited to section stalls, at most 4 each (`canopy.perModel`). The second run logs only `2 canopy washes under the bulb strings of place_buecherstand`.

## Standing checks (test bench, re-shot this round)

- `side_by_side.jpg`: the Cycles reference against the bench at the Cycles camera. None of this round's changes reach the reference glb (it has no figure and no canopy string), so the bench matches round 2: warm interior, cool moonlit snow, readable wood grain, bulbs as soft dots, stars, and fog on the horizon.
- `snow_toggle.jpg`: `setSnow(false)` against `setSnow(true)`: near, middle and far flake layers drifting with the wind, thicker fog, and fewer stars.
- The lite profile is unchanged: 4 real lights, no shadows, 2× MSAA and half-resolution bloom. The new figure terms and canopy washes run on lite too, at no cost in lights.

## Files

- `site/src/lighting/shading.js`: two header vec4s (figure fill and shoulder), the `LIGHTING_FIGURE` block and `setFigure()`.
- `site/src/lighting/index.js`: `markFigures()` (run from `update`, removed in `dispose`) and `canopyGlows()` (called from `addBulbGlows`, so from `tune()` as well).
- `site/src/lighting/settings.js`: `NIGHT.figure` and `NIGHT.canopy`.
- `site/src/lighting/test.html`: `?figure=<glb>` puts a person at the stall's `slot_vendor` inside a `crowd` group.
- `site/src/lighting/README.md`: the sections "Figures in close-ups (round 4)" and "Bücherstand rack canopies (round 4)", and the new URL option.
- This folder: `vendors_bench.jpg`, `vendor_crops.jpg`, `books_bench.jpg`, `books_racks.jpg`, `market_bier.jpg`, `market_glueh.jpg`, `market_books.jpg`, `side_by_side.jpg`, `snow_toggle.jpg`, and the PNGs in `raw/` (after) and `raw_before/` (market, round-3 code).

## Open

- The real-GPU frame time is still not measured (no GPU here). The cost added this round is two glow slots and a few ALU operations on figure fragments. It adds no lights, no passes and no draw calls.
- The vendors' faces read, but they are a little grey and cool next to the warm stall. The figure glbs give skin a low-saturation albedo. Warming the fill further would start to flatten the figures. If the judges want warmer skin, the vendor or organizer could raise the skin albedo's saturation.
- The racks are lit, but the stall interior is still clearly brighter. That is deliberate: the racks stand outside, under small canopies with a few bulbs.
- The bench "before" figures are darker than the market's, because the bench has no crowd lift (crowd.js) and no focus lights. The market pairs are the like-for-like comparison.
