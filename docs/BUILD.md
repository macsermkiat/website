# Build contract

This file is how the specialists building the market fit their work together. The market owner (the orchestrating session) keeps it current. If your work needs a change here, say so in your report instead of changing it yourself.

## Decisions already made

- The site is hosted on GitHub Pages from this repo, built with Vite and the current `three` npm package.
- Desktop gets the full market. Phones and weak GPUs get the **lite market**, which has the same content with fewer lights, no shadows and `*.lite.glb` models.
- The look is a **realistic miniature**: real materials, warm light, believable wear. It is not near-photoreal and not cartoon.
- The band plays a **pre-mixed recorded ballad**, shipped as separate stems so the page can place instruments in space and feature one player. Stall sounds stay live.
- A plain HTML version of all content ships next to the 3D market.
- Content is drafted by the writer, and every factual claim about Mac is marked for him to check.
- Theme rule: no lab, pathology or clinical imagery in the scene. Research tools appear only as content.

## Repo layout and ownership

Only write inside the paths your role owns. You may read anything.

| Path | Owner |
|---|---|
| `site/` (Vite app, except the rows below) | engineer |
| `site/src/layout.json` | architect |
| `site/src/crowd.json` | organizer |
| `site/src/lighting/` | lighting designer |
| `site/public/models/` | whoever built the model (file-name prefix below) |
| `site/public/audio/` | music writer |
| `blender/lib/` (shared Blender helpers: materials, baking, export) | carpenter; others may add their own files `blender/lib/<role>_*.py` |
| `blender/square/`, `blender/town/` | architect |
| `blender/stalls/` | carpenter |
| `blender/props/` | vendor (brewer, cook, bookseller) |
| `blender/rides/` | ride builder (Ferris wheel, carousel, bandstand, instruments) |
| `blender/people/` | organizer |
| `music/` | music writer |
| `content/` | writer |
| `review/round-N/<role>/` | everyone: your preview images (JPEG, 1280 px wide at most) |
| `docs/BUILD.md`, `docs/adr/`, `CONTEXT.md` | market owner |

On the cloud machine, don't commit; the market owner commits. On the Mac, the Blender roles commit their own paths to the round branch as described above.

## Where things run

- **Blender work (architect, carpenter, vendor, ride builder, organizer) runs on Mac's MacBook Air (Apple M3, 24 GB) from round 1 pass 2 on.** A Cycles preview renders there in about 7 s on the Metal GPU, against about 3.5 min on the cloud machine. The repo clone is `/Users/admin/Project_Chatbot_research/website`.
  - Blender: `~/nachtmarkt-tools/bpy-venv/bin/python your_script.py` (bpy 4.2 LTS, headless, with Pillow).
  - gltf-transform: `NPM_CONFIG_PREFIX=~/nachtmarkt-tools/npm`.
  - Every render must honour two environment variables: `NM_DEVICE` (CPU, or METAL for the GPU) and `NM_THREADS` (0 means all cores). `blender/lib/nmlib/render.py` shows how. On the Mac, run with `NM_DEVICE=METAL NM_THREADS=0`.
  - With the GPU, previews can use 128 samples at 1920x1080. Keep a 1280 px JPEG for review.
  - bpy on macOS segfaults at interpreter exit (code 139) after writing everything. Treat that as success if the outputs exist.
- **Site, lighting, music and writing run on the cloud machine** (4 CPUs, no GPU). The repo is `/home/claude/website`. Blender there is `/home/claude/tools/bpy-venv/bin/python`.
- Both machines exchange work through git on the `build/round-N` branch. Pull before starting, and commit only your own paths with a message naming your role.

## Tools on both machines

- glTF optimisation: `gltf-transform`. The standard web step is:
  `gltf-transform optimize in.glb out.glb --compress meshopt --texture-compress webp --texture-size 1024`
  Draco is not available. The loader uses `MeshoptDecoder`.
- Python 3 with numpy and scipy, and Node 22. On the cloud machine, Playwright with Chromium: launch with `executablePath: '/opt/pw-browsers/chromium'` if the version differs, and for WebGL use args `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`. Software GL is slow, so allow long timeouts.
- Network on the cloud machine: npm, PyPI, GitHub and raw.githubusercontent.com work, and many other hosts are blocked. Only use assets whose licence allows use on a public website (CC0, CC-BY, MIT and similar). Record every third-party asset with its source URL and licence in `CREDITS.md` under your role's heading.

## Scene conventions

- Units are metres. three.js is Y-up. Blender is Z-up, and the glTF exporter converts, so model in Blender normally.
- Each asset's origin is on the ground at the centre of its footprint. Its **front** (the side visitors approach) faces Blender **-Y**, which becomes three.js **+Z**.
- The market square is centred on the origin. The main view looks from +Z toward -Z.
- Named nodes inside a glb tell the engine where things are. Use these exact prefixes:
  - `light_<n>`: an empty where the engine may place a real-time warm light. Use at most 1 per deco stall and 2 per section stall.
  - `bulbs_<n>`: a mesh of fairy bulbs. Its material is named `bulb_warm` or `bulb_cold` and is emissive. The engine makes it glow with bloom.
  - `slot_<name>`: an empty where props go. Stalls must provide `slot_counter` (on the counter top, centred), `slot_shelf_1` and `slot_shelf_2` (back shelves), `slot_vendor` (standing spot behind the counter), `slot_sign` and `slot_front` (ground in front of the counter).
  - `cam_view`: an empty where the camera goes when a visitor enters this place. It looks toward `cam_target`.
  - `act_<name>`: a node that an action animates (for example `act_tap_0`, `act_pot_lid`, `act_book_12`, `act_grill`).
  - `rot_<name>`: a part that the engine spins (for example `rot_wheel` or `rot_platform`). Gondolas are `gondola_<n>` and horses are `horse_<n>`.
  - `snow_<n>`: snow caps that the engine shows only when snow is on.
- The standard counter top is 1.05 m high. The stall front opening sits between 1.05 m and 2.2 m.

## Lighting approach

- Materials are baked from Blender procedurals to base colour, roughness and normal maps. Also bake **ambient occlusion** into the glTF occlusion texture. No lighting goes into base colour.
- The browser supplies the lighting:
  - a moonlit sky and hemisphere fill;
  - warm real-time lights at `light_*` empties;
  - emissive bulbs with bloom;
  - fog;
  - an environment map for reflections.

  The lighting designer owns this and may add a baked-lightmap step later.
- Each section stall and landmark ships a Cycles preview render as the visual target for what the browser should approach.

## Budgets (after `gltf-transform optimize`)

| Asset | Triangles | File |
|---|---|---|
| Section stall with its props | 60k | 3 MB |
| Deco stall | 20k | 1 MB (shares the kit's textures where possible) |
| Ferris wheel / carousel | 80k each | 3 MB each |
| Bandstand with instruments | 50k | 2 MB |
| Square ground, lamps, string-light poles | 40k | 3 MB |
| Town ring (all buildings) and church | 150k | 5 MB |
| One person variant | 5k | 0.4 MB (the engine instances them) |

Aim for 25 MB total on first load for the desktop market and 8 MB for the lite market. The `*.lite.glb` versions have about a third of the triangles and 512 px textures.

## Layout (starting point, from the prototype; the architect owns changes)

Positions are `[x, z]` in metres, and rotation is Y in radians.

- Section stalls:
  - Glühwein (About): `[-7.4,-1.4]`, rotation 0.42
  - Bratwurst (Writing): `[-12.8,2.6]`, rotation 0.8
  - Bierstand (Projects): `[7.4,-1.4]`, rotation -0.42
  - Bücherstand (Reading): `[12.8,2.6]`, rotation -0.8
- Landmarks:
  - Bandstand (Music): `[0,-5]`
  - Riesenrad (Big questions): `[-22,-17]`, rotation 0.65
  - Karussell (Contact): `[19,-12]`
- Tree: `[6.5,-15]`.
- Deco stalls:
  - Left lane at x = -21: Lebkuchen, Gebrannte Mandeln, Kerzen.
  - Right lane at x = 21: Holzspielzeug, Christbaumschmuck, Käse.
  - Back row at z ≈ -21: Crêpes, Heiße Maroni, Kartoffelpuffer.
- Town ring: radius 47–64 behind the market, with the church at `[8,-56]`.
- Home camera: position `[3,9,33]`, looking at `[0,2.2,-3]`.

## Review

At the end of each round, every specialist leaves:

1. the assets in place;
2. preview images in `review/round-N/<role>/`;
3. a short `review/round-N/<role>/NOTES.md` covering:
   - what was built;
   - triangle counts and file sizes;
   - what they would improve next;
   - anything that breaks this contract.

The judging panel sees only the repo, the images and those notes.
