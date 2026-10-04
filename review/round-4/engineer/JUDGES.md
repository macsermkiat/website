# Judges on engineer, round 4 pass 1

## Improve

Failed:
- Bier close-up shows tap, vendor and a full pint in frame: In item_bier_pouring.jpg the tap tower, the vendor and the glasses are all in frame and the head is clear. But the glass under the tap and the counter glasses read pale or empty, not as a full golden pint, and the bunting still fills the top third.
- Smoke results left current (round-4 priority 5): The builder admits the items, interaction, lite and phone parts were not re-run since round 2, and smoke.log only covers shots, plain and missing. That misses the brief's 'leave the smoke results current'.

Fixes:
- Re-run the full smoke run (items, interaction, lite, phone) and commit nothing. This round changed focusItem, band.js and instruments.js, so the round-2 results are stale.
- Make the Bier item shot show a full golden pint: shoot after the pour completes, or fix the beer material and opacity with the vendor. Both shots still read as empty glass.
- Lower or tilt the item camera a little further so the bunting takes less of the top third of the frame.
- Capture a narrow-screen (960 px or less) screenshot of the bookshop bottom-sheet reading view, and of the physics and craft framing, as evidence for priorities 2 and 3.
- Ask lighting to tame the glare on the vendor's white sleeves under light_1.
