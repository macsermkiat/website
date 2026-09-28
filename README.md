# Mac's Nachtmarkt

Personal website of Mac, built as a 3D German Christmas night market. Each stall is a section of the site.

- `prototype/` is the first working mockup (three.js, procedural shapes, live-generated jazz ballad). Serve the folder with any static server and open `index.html`.
- `blender/` holds the scripts that build the detailed stalls in Blender. Run a stall script with Blender 4.2 (or `pip install "bpy==4.2.*"` in Python 3.11): `python blender/stalls/gluehwein.py`.
- `CONTEXT.md` is the glossary. `docs/adr/` records the decisions that are hard to reverse.
