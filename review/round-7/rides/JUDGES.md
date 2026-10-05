# Judges on rides, round 7 pass 1

## Ship

Failed:
- Browser shot reflects the real site: The shot comes from a scratch copy with engine_ticket_glow.patch applied. surfaces.js is unpatched, so readGlow resets the ticket glow to 0.04 and the real site may look cooler under the night light

Fixes:
- Engineer: apply review/round-7/rides/engine_ticket_glow.patch to site/src/world/surfaces.js, then re-shoot read_carousel_ticket.jpg on the real site. Confirm the card still reads cream, not grey-beige, under the night light.
- Writer and Mac: fill the empty contact field in content/contact.md ('The best way to reach me is .').
- Optional: use some of the 7k spare triangles to smooth the horse's rump outline, which is visible from the ride seat.

## Ship

Failed:
- The browser shot reflects the shipped engine (no unapplied dependency): The shot was taken on a scratch copy with engine_ticket_glow.patch; the real site/src/world/surfaces.js readGlow still overwrites emissive with 0xfff0d8 x map at 0.04, so the read view on the real site is dimmer than shown. The patch applies cleanly (git apply --check) and is one hunk, but it is the engineer's to accept.

Fixes:
- Engineer: apply review/round-7/rides/engine_ticket_glow.patch (single hunk in readGlow, applies cleanly) and re-shoot read_carousel_ticket.jpg on the real site so the shipped read view matches the round-7 browser shot.
- Writer/Mac: fill the empty contact field in content/contact.md ('The best way to reach me is .') before launch; it shows on the ticket.
- Optional: spend some of the 7k spare carousel triangles on the horse rump silhouette seen from horse_seat_2, since the rump still shows a polygonal outline at a metre.
- Run check_clash.py and the architect's stroll check once more before the final merge, even though the booth footprint did not change, so round 7 has its own record.
