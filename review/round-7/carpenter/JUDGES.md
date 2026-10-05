# Judges on carpenter, round 7 pass 1

## Improve

Failed:
- write_reading_card follows BUILD.md write_ contract (UVs 0-1, plain material): write_reading_card in both stall_buecher.glb and .lite.glb has only NORMAL and POSITION attributes, no TEXCOORD_0. BUILD.md line 71 requires 0-1 UVs, and write_about in gluehwein does have TEXCOORD_0, so the engine cannot place text on the card.
- glb_tools write check actually validates the contract: The builder says the check passes, yet the card has no UVs, so WRITE_REQUIRED checks names only and not the UV requirement.

Fixes:
- Give the write_reading_card mesh a 0-1 UV map across the card face with +V up the text (fix boards.easel_card to emit UVs). Re-export the full and lite glbs and confirm TEXCOORD_0 is present after optimize.mjs, which may be stripping it.
- Extend the glb_tools write check to fail when a write_* mesh has no TEXCOORD_0 or its UVs do not span 0-1, then re-run it on all stalls and deco files.
- Check that the round 7 git diff contains only carpenter files. Unrelated blender/rides and carousel.glb changes show in the working tree and belong to another builder.

## Market owner follow-up

The missing UVs come from optimize.mjs pruning unused attributes on a texture-less material. The engine now derives planar UVs for a flat write_ mesh that has none (site/src/world/surfaces.js planarUV), and the reading smoke run shows books.card on the model's own node with no stand-ins.
