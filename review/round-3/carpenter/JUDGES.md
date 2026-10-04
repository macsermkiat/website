# Judges on carpenter, round 3 pass 1

## Ship

Fixes:
- Make buecher_sections.py --check read-only. It currently rewrites buecher_sections.json while checking.
- Re-export stall_buecher.lite.glb in the same run as the full file, or confirm the cart-sign move is in it. The lite file is 22 minutes older.
- Organizer: move the browsing_buecherstand crowd spots to about y -2.6 so they clear the carts.
- Lighting pass: canopy shadow on the upper rack boards, and canopy bulbs that light nothing in three.js.

## Ship

Fixes:
- Organizer (not carpenter): move the two browsing_buecherstand crowd spots from about (±1.4, -1.95) to y ≈ -2.6 in the stall frame so they stand in front of the carts, not inside them.
- Cart signs sit at 0.35-0.59 m and are hard to read from the home camera; consider a second small label on the cart push bar or raising the apron board slightly without touching the slot positions.
- Lighting pass with the lighting designer: the rack canopies shadow the upper boards under light_1 and the canopy bulb strings light nothing in the browser; a faint emissive stand-in on the rack boards or a third light would help (needs market-owner approval for a third light_ empty).
- If the engineer wants per-section close-ups, agree a cam_cat_<key> prefix with the market owner; cam_view at 4.2 m leaves physics and craft at the frame edge.
