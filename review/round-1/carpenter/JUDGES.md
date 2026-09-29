# Latest judges on carpenter, end of round 1

## Opus (pass 3): Improve

Failed checks:
- (added) Signature trim survives under the site's lighting: Side-by-side crop of stall_gluehwein_preview vs _threejs: in three.js the red gable pediment and barge boards go near-black and the scalloped red valance behind the sign disappears. The Glühwein brief's defining feature is lost in the browser; Bratwurst and Bier got fixes for this, Glühwein did not.
- (added) Shipped materials are complete (AO on every kit material): Decoded stall_bratwurst.glb: material iron_matte has occlusionTexture = none (iron, oak and paint have it). The hood and firebox, the stall's focal surfaces, ship without AO. The builder admits this.
- (added) Bratwurst reads as sooty at its grill: The Cycles grill crop shows a clean, light galvanised-looking hood and firebox with scattered rust dots. The emissive stand-in lifts them in Cycles too, so the brief's 'sooty' reads only on the siding.

Fixes:
- Glühwein in the browser: make the red-and-gold gable, barge boards and scalloped valance read under the site lighting. Use the same approach already used for iron_matte and rauten: a lighter red paint variant with a faint warm emissive for the outward-facing trim and valance, and/or aim the second light_ empty at the gable. Re-shoot stall_gluehwein_threejs.jpg and show the valance and star cut-outs clearly.
- Fix the missing occlusionTexture on iron_matte: bake the metal as a plain value or texture instead of going through a multiply node, so the exporter keeps the glTF Material Output AO link. Check that the decoded stall_bratwurst.glb shows occlusion on iron_matte.
- Bratwurst sootiness: darken the upper hood and firebox face with a soot gradient (shade/COLOR_0) and heat-staining around the bowl, and switch off the iron_matte emissive in the Cycles preview so the grill reads as blackened iron there. Also remove or explain the round light spots on the firebox top.
- Correct NOTES.md: Bier with vendor props is 43,429 + 13,656 = 57.1k (2.9k headroom, not 3.9k), so trim the barrel staves now. Drop the stale __pycache__ request, since nothing is tracked any more.
- Coordinate with the vendor: the Bücher glazed cabinets (slot_cabinet_l/r) are empty in the browser because no prop targets them. Either ask for cabinet props or put a few low-poly book spines behind the glass in the stall itself.
- Optional polish: add a few slipped or drifted snow patches at the eaves on the straight board and shingle roofs. On the Bratwurst, re-aim the sign gooseneck lamps so their hotspot lands on the board, not on the roof snow.

## Fable (pass 3): Ship

Failed checks:
- No browser-only material defects on the section stalls (added): In stall_buecher_threejs.jpg the bay window's copper hip roof renders as a flat, unshaded salmon-orange plane (material `copper`: metallic 1, roughness 0.30, no texture) while it reads as dark patinated metal in the Cycles preview; iron_matte also ships without an occlusionTexture (confirmed in the glb).

Fixes:
- Bücher bay window roof: the `copper` material (metallic 1, roughness 0.30, untextured) renders as a flat salmon plane in three.js. Give it a darker oxidised/verdigris colour, roughness around 0.55 and either the iron kit normal map or metal 0.6 so it shades under point lights; re-shoot stall_buecher_threejs.jpg.
- Give `iron_matte` its occlusion texture: the KIT_VARIANTS multiply node on metal breaks the exporter's ORM wiring, so route color_gain/metal through the material's factors instead of node maths (or bake a separate iron_matte rm), and verify occlusionTexture is present on the hood in stall_bratwurst.glb.
- Bier sign in the browser: the cream board picks up the sky and the dark-blue Fraktur letters sit at low contrast; darken the letters toward navy/black or give the board a warm cream tint so it matches the Glühwein sign's legibility without the optional sign spot.
- Add a render-only override that zeroes the `rauten` and `iron_matte` emissive stand-ins in Cycles previews, so the Bratwurst hood reads as soot-blackened iron in the visual target and the preview stays the reference for the lighting designer.
- Bier headroom with the vendor's current props is 57,085 of 60,000 (2.9k, not the 3.9k in NOTES.md): pre-emptively cut the barrel stave/ring count so the next vendor change cannot break the budget.
- NOTES.md housekeeping: `git ls-files` shows no tracked __pycache__/*.pyc files, so drop that request to the market owner; keep the BUILD.md optimize.mjs request.

