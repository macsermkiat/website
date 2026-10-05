# Round 9 judges: carpenter

Final: Ship / Ship after 1 pass(es).

## Pass 1

### Judge Opus: Ship
- Fix: Tone down the white front boards (e.g. warm off-white or walnut) so the goods, not the counter front, are the brightest area at night
- Fix: Make the mirror doubling more evident in the lane view (brighter bulb row near the mirror, or less dark tint)
- Fix: Add slot_window_l/_r and slot_tinsel_* to BUILD.md and note the slot_rail_1/slot_harmonica_rail alias
- Fix: Architect: re-derive the deco-schmuck stroll stop for cam_view at 4.3 m

### Judge Fable: Ship
- Fix: Tighten the foxing: in stall_schmuck_mirror.jpg the spots are large pale blotches that read as a dirty window more than faint foxing; shrink them and lower their contrast so the reflection dominates.
- Fix: Fix the README drift on mirror_foxed (line 56 still promises 'slight waviness' in the normal map; the shipped m5 map is flat except at the spots) and mention that slot_rail_1 and slot_harmonica_rail are the same rail.
- Fix: Lift the interior from the lane: the goods behind the counter are still dim in the 3/4 preview while the white front boards are the brightest area; a slightly stronger light_0 or a warmer paint on the front boards would move the eye inside.
- Fix: Bring the lite shop with goods nearer 20k (currently 27.8k measured); the cheapest wins are on the vendor's lite harmonica and shelf sets, so flag it jointly.
- Fix: Ask the market owner to add slot_window_l/_r and slot_tinsel_<n> to BUILD.md, and the architect to re-derive the deco-schmuck stroll stop from the moved cam_view.

Open issues from the builder:
- The browser can only get close to the preview's sparkle with engine work: doubled baubles need a reflector or probe on mirror_0, and glints need the environment map and point lights. I did not run a WebGL check this round.
- The vendor was still changing the shop's goods while I rendered (last change I saw was 07:56). The previews show the 07:57 state; re-render with: NM_ROUND=9 /home/claude/tools/bpy-venv/bin/python blender/stalls/schmuck.py --bloom 0.9
- cam_view moved back to 4.3 m (it was 4.05 m) so the mirror ball stays in frame. The architect needs to re-derive the deco-schmuck stroll stop with stroll.py.
- The lite shop with goods is 28.8k triangles, above the 'about a third' guide (20k). The vendor's lite harmonica, shelf and rail sets are the heavy ones.
- slot_window_l/_r and slot_tinsel_* are new slot names that are not in BUILD.md yet. slot_rail_1 and slot_harmonica_rail are the same physical rail.
- In the exterior 3/4 view at night, the white-painted front boards are still the largest bright area.
- review/round-8/CODEX_JUDGE.md does not exist on disk.
- Carried over from earlier rounds: the emissive stand-in materials (paint_glow, paint_lit, iron_matte, rauten); bevels as real geometry on the section stalls; no scorch decal on the Bratwurst; the Glühwein reading view is 12° oblique; the Bücherstand cabinet signs are small from the home view.
