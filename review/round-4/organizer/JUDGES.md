# Judges on organizer, round 4 pass 1

## Improve

Failed:
- Vendor faces hold up in close-up: In vendors_closeup.jpg all heads are bowed. The Bier vendor's face is almost entirely in brim shadow and the faces are flat nose-wedges, so features barely read at chest-up framing.
- Fixes verified in the real three.js scene: The builder says there was no in-browser capture. The checks are Cycles and the planner map only, and the browser spots and new hat are unconfirmed in-engine.

Fixes:
- Capture the Bücherstand open-stall view and the Bier stall close-up in the browser, and confirm the browsers stand in front of the carts facing them, not clipping or hidden.
- Lift the vendor head pose in serve/idle, or tilt the Bier hat back slightly, so the face is not lost under the brim at close-up distance. Re-render vendors_closeup with faces lit.
- Add slightly more face definition for the vendors (brow/cheek shading or a stronger painted eye/brow contrast), since they are seen in close-ups.
- Fix or document the capture script's openPlace behaviour so the next round's lighting/engine screenshots actually reach the stall views.
