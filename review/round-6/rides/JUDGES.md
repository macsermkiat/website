# Judges on rides, round 6 pass 2

## Improve

Failed:
- Text actually readable in the live site: grep of site/src finds cam_read_ only in bookOpen.js. The engine never uses cam_read_question_N and never pauses rot_wheel. The fix exists only as engine_placards.patch.
- Reading view looks clean: browser_read_ferris_placard_0.jpg is legible, but the writing area shows as a lighter inset panel on a darker sheet. The builder lists this as an open issue.

Fixes:
- Have the engineer apply review/round-6/rides/engine_placards.patch to site/src: placard click goes to cam_read_question_N, and rot_wheel pauses while reading (preferably with the gondola parked at the bottom). Then re-take the browser shots on the real site.
- While a surface is read, brighten the card_<name> backing sheet together with the write_ quad, or match their materials, so the inset no longer shows as a lighter panel.
- Fix the orange ticket stub that turns grey-blue at night in the browser.
- Re-run check_clash.py for the Riesenrad, and have the architect re-run the official stroll check.
- Optionally raise the full master horse to about 1,600 triangles to smooth the neck and hind-leg corners seen from the ride seat.
