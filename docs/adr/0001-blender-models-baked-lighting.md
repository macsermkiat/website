# 1. Model in Blender, bake materials, ship glTF to three.js

The prototype builds everything from primitive shapes in code, which caps how detailed it can look. The real market is modelled in Blender by script, with procedural materials baked to textures and exported as compressed glTF (meshopt geometry, WebP textures) that three.js loads.

A test build of the Glühwein stand showed the route works in this environment: bpy 4.2 runs headless, Cycles renders a lit preview in about 90 s on CPU, and the stall exports to a 2.3 MB web file. Lights, sky and camera do not export; the browser scene supplies its own lighting and bloom.

## Considered options

- **Keep building in code.** Cheap to change but will not reach the detail wanted.
- **Hand-model in the Blender GUI.** Highest ceiling, but nothing here can drive a GUI and the result is not reproducible.
- **Scripted Blender (chosen).** Reproducible, reviewable in git, and each stall can be rebuilt after feedback.

## Consequences

Every asset needs a triangle and texture budget, because one detailed stall is about 133k triangles before simplification. Draco compression is not available in the bpy wheel, so meshopt is used and the loader needs `MeshoptDecoder`.
