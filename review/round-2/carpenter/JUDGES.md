# Judges on carpenter, round 2 pass 1

## Ship

Failed:
- (added) Claimed cabinet spines read behind the glass in both renderers: In stall_buecher_threejs.jpg the left cabinet shows coloured spines, but in the Cycles stall_buecher_preview.jpg both cabinets look nearly empty: one faint row in the left cabinet and a few pale blobs in the right. The claim is overstated for Cycles.
- (added) Preview free of sign-lamp hotspots on roof snow: Fixed on the Bratwurst, but stall_bier_preview.jpg still has bright ovals on the roof snow and eave drifts under the crest-sign lamps. Several deco tiles (Mandeln, Holzspielzeug, Maroni) show the same.

Fixes:
- Optional: apply the Bratwurst sign-spot fix (narrower cone, aimed at the upper board) to the Bier crest-sign lamps and the deco sign lamps, so the Cycles reference renders lose the bright ovals on the roof snow and eave drifts.
- Optional: in the Bücher Cycles preview, raise the cabinet light or the spine tint until the books read as clearly as they do in three.js. Otherwise correct the NOTES claim that they read in both renderers.
- Market owner: decide on the proposed 40k stall / 20k props split now. Glühwein, Bier and Bratwurst have only 2.7k-3.4k headroom, and the vendor's Bratwurst set (20.6k) is already over its share.
- Housekeeping: the README says the rauten texture is embedded at 'about 3 KB', but the decoded glb shows 6.4 KB. Update the figure.

## Ship

Failed:

Fixes:
- Optional, next round: the section-stall headroom with the vendor's props is only 2.7k–3.4k on Glühwein, Bier and Bratwurst; the market owner should adopt the proposed 40k stall / 20k props split in BUILD.md so the vendor's next change cannot break the 60k budget.
- Optional: the Bücher cabinet spines are barely visible in three.js (stall_buecher_threejs.jpg); if the lighting designer cannot light the cabinets, give bookcloth a faint emissive stand-in like rauten/paint_glow or lighten the tints another step.
- Housekeeping: stall_bratwurst.lite.glb (01:00) predates the last full rebuild (02:49); the node set and counts match, but re-export the lite once so both LODs come from the same script run.

