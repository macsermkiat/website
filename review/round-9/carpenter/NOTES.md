# Carpenter: round 9 notes (ADR 0004 revision: ornament shop sparkle)

Mac: "Ornament shop should have more sparkle decoration and goods. No need to be interactive in everything, but the one that interactive must be wow. not slop."

This round ran on the cloud machine (CPU, 2 threads, `NM_ROUND=9`). I only rebuilt the ornament shop, `blender/stalls/schmuck.py` → `stall_schmuck.glb` (+ lite). The library changes are additive and keep every default, so the other stall files are unchanged. All numbers below were measured in `site/public/models` after `optimize.mjs`.

## The idea

The shop sparkles because of a few strong lights and reflections against dark wood. I did not add more stuff. The interior (wall lining, ceiling, upper front wall, shelf tiers) changed from pale pine to dark walnut, so goods and bulbs read as points of light, with wood showing between the clusters. There is one hero star instead of two stacked ones, and the counter-bay fir garland went to make room for the harmonica rail and the vendor's tinsel.

## 1. Mirror on the back wall: `mirror_0`, material `mirror_foxed`

- **Size and frame.** An antique pier glass covers the upper two thirds of the back wall (x ±1.5 m, z 1.10 to 2.62 m), behind the tiers. Its frame is walnut with a gilt inner moulding. Two gilt glazing bars mark where three old plates meet, with gilt rosettes at their ends.
- **Mesh.** `mirror_0` is one flat, front-facing grid (16 x 8 cells, 256 triangles) at Blender y = 1.234, facing -Y (three.js +Z). It suits a planar reflector if the engineer wants a real one.
- **New library material `mirror_foxed`** (`mats.MIRRORS`, generated with numpy, version m5). It has three textures, about 19 KB as WebP:
  - **Base colour:** dark-tinted silver (linear about 0.30).
  - **Roughness/metal:** roughness about 0.05 and metal 1.0 on clean glass. Foxing spots are rougher (up to 0.45) and less metallic.
  - **Normal map:** carries the foxing spots only.

  The foxing is brown-grey desilvered spots in loose clusters, with darker rims, plus a few milky patches.
- **Edge desilvering.** A vertex-colour shade on the grid (`schmuck.mirror_shade`) darkens a ragged band along the frame.
- **Flat glass.** I tried a glass-waviness term in the normal map (versions m1 to m4). Any strength that survives 8-bit and WebP turned the reflections into squiggles at the grazing angles this mirror is seen at, so the glass stays flat and only the spots have relief.
- See `stall_schmuck_mirror.jpg`. The doubled canopy bulbs, the pendant lamp and the foxing are visible there.

## 2. Bulbs inside the canopy (`bulbs_1`) and `light_0`

- **Three rows of small warm rice bulbs** (`bulb_warm`, no sockets, 2.8 cm):
  - **Header fringe.** A tight row just under the header's inner edge across the counter bay. This is the row you see from the lane, a line of points lighting the goods from above.
  - **Tie-beam row.** A row swagged along the tie beam.
  - **Mirror row.** A row low across the top of the mirror, which doubles it.
- **Why the fringe.** From the lane the header hides everything inside above about 2.25 m. I worked this out from `cam_view` and checked it in renders. A row under the front wall plate was invisible from the lane and from its reflection, so it moved to the header fringe.
- **`light_0`** is near the ceiling centre at (0, -0.5, 2.8), Blender coordinates. Its reflection in the mirror stays behind the header from the lane. It hangs in a small brass pendant lamp whose bulb is part of `bulbs_1`, so the light has a visible source.
- **`light_1`** is unchanged, outside in front.

## 3. Ridge star (`bulbs_2`) and a ring of bulbs round the roof

- **Ridge star.** A faceted eight-point star, 0.6 m across, stands on a turned walnut post at the middle of the ridge, with its top at 4.95 m. Its glass core is an emissive `bulb_warm` double pyramid (`bulbs_2`). Gilt ribs run round the outline and from the centre to every point, so it reads as a lantern star, not a flat glow.
- **Pediment finial.** The pediment's old gold star became a gold ball, so there is one hero star.
- **Bulb ring (`bulbs_0`).** The bulbs now run right round the roof edge: the front eave as before, plus both rakes of both slopes and the back eave. The new strings have no sockets and a thin wire, to save triangles. The roof outline now reads from every lane, including the home view, which sees the shop's right side.

## 4. Slots for the vendor's new goods (`blender/stalls/schmuck_slots.json`)

- **`slot_harmonica_rail`.** The front rail, moved to 2.00 m at y = -1.45 (it was 2.08 m). Twelve brass curtain rings mark the hanging points for `act_orn_harmonica_0..11`, left to right.
  - The json gives `hooks_x` (0.17 m pitch, offsets from the empty along +X) and `hook_drop` 0.022 m, which is the ring's bottom below the rail axis.
  - It is the same rail as `slot_rail_1`, which I kept so nothing that references it breaks.
  - It is inside the 4.3 m `cam_view` frame.
- **`slot_mirrorball`.** The open hook under a forged wrought-iron bracket (Ausleger) that projects 0.74 m forward from the left front post, the way an old shop hangs its sign. The bracket has an arm with a curled end, a diagonal brace, a C-scroll and riveted wall plate.
  - The hook is at 2.10 m. The 18 cm ball hangs clear of every other ornament (0.4 m clear radius) and close to the lane.
  - The json suggests a `cam_dive` placement. The cameras themselves are the vendor's, per BUILD.md.
- **`slot_pyramid`.** On the counter right of the Schwibbogen, at x +0.12 from `slot_counter` and toward the back. The pyramid can be up to 0.34 m across and 0.62 m tall.
- **`slot_tinsel_1..3`.** The left anchors of three swags. The json lists every anchor and a sag for each:
  1. along the canopy edge, under the valance across the counter bay;
  2. draped over the harmonica rail, above the rings;
  3. along the tie beam inside, which doubles in the mirror.
- **`slot_window_l` / `slot_window_r` (new, optional).** See section 5.
- **The vendor uses them already.** The final preview shows `prop_schmuck_harmonica`, `_mirrorball`, `_pyramid`, `_garland`, `_tinsel_1` and `_tinsel_3` hanging and standing at these slots.

## 5. Round-8 open point fixed: plain shop sides

Each side wall now has a lit, glazed shop window (Schaukasten) between the red rails:

- a red case with a gilt bead, a glass front and a carved crest with a gold star;
- two small warm bulbs under its top;
- a cream `paint_lit` back board, so in the browser it glows like a lit display.

The right one faces the home view and the left one faces the lane toward the Karussell. `slot_window_<l|r>` is on each sill. The json gives the inner size and asks for something sparse, such as a few baubles or a spun-glass bird. Until the vendor fills them, the windows show only their glow.

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size |
|---|---|---|
| `stall_schmuck.glb` | 31,564 (round 8: 28,004) | 0.77 MB (+ 0.66 MB shared deco-kit textures, as before) |
| `stall_schmuck.lite.glb` | 13,994 (round 8: 10,716) | 0.33 MB |

- **The shop with the vendor's goods** (13 sets on disk at 07:57):
  - Full: 31.6k + 24.2k = **55.7k triangles**, and 0.77 + 0.61 = **1.4 MB** of own bytes. With the shared kit it is 2.0 MB. That is inside the 60k / 3 MB budget.
  - Lite: 14.0k + 14.8k = 28.8k triangles.
- **How I got near 30k.** The first round-9 build was 36.3k triangles. I trimmed it back:
  - socket-free, thin-wire bulb strings for everything new (`carpentry.bulb_string(socket=False, wire_detail=1)`);
  - shingles 0.36 x 0.23 m (they were 0.32 x 0.21) and 12-column snow;
  - a lighter mirror frame;
  - fewer fir tufts;
  - no chamfers on the small window boards.
- **Counter top.** It is still 1.05 m (`slot_counter`).
- **Check.** `python3 blender/lib/glb_tools.py check site/public/models/stall_*.glb site/public/models/deco_*.glb` passes on all files. For the shop it now also requires:
  - `slot_harmonica_rail`, `slot_mirrorball` and `slot_pyramid`;
  - at least one `slot_tinsel_*` and one `mirror_*`;
  - the `mirror_foxed` material, used by every `mirror_` mesh;
  - at least two `bulbs_` meshes.

**Other stalls, unchanged since rounds 7 and 8:**

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 38,780 | 0.97 MB | 8,676 | 0.23 MB |
| stall_bratwurst | 38,378 | 0.92 MB | 8,534 | 0.25 MB |
| stall_bier | 41,453 | 1.08 MB | 11,171 | 0.30 MB |
| stall_buecher | 51,428 | 1.42 MB | 13,865 | 0.41 MB |
| deco_* (9) | 7,023-9,633 | 0.19-0.26 MB | 3,765-5,031 | 0.12-0.14 MB |

Their previews are in `review/round-6/carpenter/` (Glühwein, Bratwurst, Bierstand), `review/round-8/carpenter/` (Bücherstand, deco contact sheet) and `review/reference/`.

## Previews in this folder

All renders are Cycles at night.

- **Bloom.** The review JPEGs get a soft glow round the brightest pixels (`--bloom 0.9`, new `render.bloom`). It stands in for the site's UnrealBloom on the emissive bulbs. The PNGs in `blender/out/renders/` have no bloom.
- **`stall_schmuck_preview.jpg`.** A 3/4 front view at night, 1280x720 at 48 samples, with the vendor's goods as they were on disk at 07:57.
- **`stall_schmuck_view.jpg`.** The shop seen from its `cam_view`, at the site's 42° vertical field of view. It shows the dark-wood interior, the mirror behind the tiers, the header fringe, the harmonica row, the mirror ball on its bracket and the pyramid on the counter.
- **`stall_schmuck_right.jpg`.** A 3/4 view from the right, the side the home view sees. It shows the lit side window, the rake bulbs and the star.
- **`stall_schmuck_mirror.jpg`.** A close-up of the foxed mirror from behind the counter.

## Library (`blender/lib`, documented in `README.md`)

Everything is additive; no existing default changed.

- `mats`:
  - the `mirror_foxed` material (`MIRRORS`, `MIRROR_VERSION`, `mirror_material`);
  - `geo.TILE["mirror_foxed"]` = 0.85 m.
- `carpentry.bulb_string(..., socket=True, wire_r=0.004, wire_detail=2)`:
  - `socket=False` leaves out the socket sleeve;
  - `wire_detail=1` gives a lighter wire.
- `render.render(..., bloom=0.0)` and `render.bloom(png, out, strength, threshold)`, plus `pipeline --bloom`.
- `glb_tools`: the round-9 shop checks (`SCHMUCK_REQUIRED`, `SCHMUCK_PREFIXES`, `SCHMUCK_MATERIALS`).

## For the other roles

- **Architect.**
  - The shop's `cam_view` moved back to 4.3 m in front of the hut (it was 4.05 m), at 1.8 m, so the mirror ball on the left bracket stays in frame. Please re-derive the `deco-schmuck` stroll stop from `cam_view` / `cam_target` (`stroll.py`).
  - The bracket and ball reach 0.74 m in front of the left front post, about 2.0 to 2.2 m up.
- **Engineer.**
  - `mirror_0` is planar, so a reflector or a cube-camera probe would make the "doubling" real in the browser. Without one it shows the environment map.
  - `bulbs_1` (canopy) and `bulbs_2` (star core) are new `bulb_warm` meshes. `light_0` moved to three.js (0, 2.8, 0.5) in shop space.
  - The `slot_window_*` empties are new.
- **Vendor.**
  - The new slots are in `schmuck_slots.json`.
  - The goods budget left is about 28k triangles full (the hut is 31.6k), and you are at 24.2k.
  - The lite total is 28.8k, which is higher than "a third" of 60k. The lite harmonica, shelf and rail sets are the heavy ones.
  - The side windows are optional.
- **Lighting designer.** The preview lights are:
  - `light_0` and `light_1` as 150 W points of 6 cm radius, small on purpose so the glass gets sharp highlights;
  - a 45 W fill panel that the mirror does not see (`visible_glossy` off);
  - small lights in the two side windows and at the star.

## Contract notes

- **`slot_rail_1` and `slot_harmonica_rail`** are the same physical rail with the same left-end position. I kept both so nothing that references `slot_rail_1` breaks.
- **`slot_window_l/_r`** are new slot names. They are not in BUILD.md yet.
- **Codex judge.** `review/round-8/CODEX_JUDGE.md` does not exist on disk, so I worked from the round-8 Opus and Fable verdicts. Both were Ship, and neither failure concerned my role: the one failure is the engineer's `STREAMED` deco loading. I also worked from my own open issues.

## Open issues

- **The browser can only approach the preview's sparkle.** The doubled baubles need a reflector on `mirror_0`, and the sharp glints need the environment map and point lights. The hut gives all of these a place, but I could not check them in three.js this round (no WebGL check run; the machine was shared).
- **Goods were still changing.** The vendor's sets were still being written while I rendered (the last change I saw was at 07:56). The previews show the 07:57 state. If the harmonica or mirror-ball sets change look, the preview needs a re-render: `NM_ROUND=9 /home/claude/tools/bpy-venv/bin/python blender/stalls/schmuck.py --bloom 0.9`.
- **Lite total.** 28.8k triangles with goods, against the "about a third" guide.
- **Exterior 3/4 view.** The interior reads clearly as dark wood with points of light. The white-painted front boards are still the largest bright area at night.
- **Carried over:**
  - the emissive stand-ins (`paint_glow`, `paint_lit`, `iron_matte`, `rauten`);
  - bevels as real geometry on the section stalls;
  - no scorch decal on the Bratwurst;
  - the Glühwein reading view is 12° oblique;
  - the Bücherstand cabinet signs are small from the home view.
