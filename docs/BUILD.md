# Build contract

This file is how the specialists building the market fit their work together. The market owner (the orchestrating session) keeps it current. If your work needs a change here, say so in your report instead of changing it yourself.

## Decisions already made

- The site is hosted on GitHub Pages from this repo, built with Vite and the current `three` npm package.
- Desktop gets the full market. Phones and weak GPUs get the **lite market**, which has the same content with fewer lights, no shadows and `*.lite.glb` models.
- The look is a **realistic miniature**: real materials, warm light, believable wear. It is not near-photoreal and not cartoon.
- The band plays a **pre-mixed recorded ballad**, shipped as separate stems so the page can place instruments in space and feature one player. Stall sounds stay live.
- A plain HTML version of all content ships next to the 3D market.
- Content is drafted by the writer, and every factual claim about Mac is marked for Mac to check.
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

Don't commit; the market owner commits and pushes.

## Where things run

- **All roles run on the cloud machine** (4 CPUs, no GPU). The repo is `/home/claude/website`. (Blender briefly ran on Mac's MacBook, but its usage limit made that impractical.)
  - Blender: `/home/claude/tools/bpy-venv/bin/python your_script.py`.
  - Every render must honour `NM_DEVICE` and `NM_THREADS` (0 = all cores), as `blender/lib/nmlib/render.py` does. The default is CPU with 2 threads.
  - Renders are slow here (about 3 min for a 1280x720 stall preview). Render only what you need to check, iterate at 960x540 and 32 samples, and make the final review renders at 1280x720 and 48 samples.
  - bpy may segfault at interpreter exit after writing everything. Treat that as success if the outputs exist.

## Tools

- glTF optimisation: `gltf-transform`. The standard web step is:
  `node blender/lib/optimize.mjs in.glb out.glb [--texture-size 1024]`
  This runs meshopt and WebP but keeps the named nodes. Plain `gltf-transform optimize` deletes the named empties, so don't use it.
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
  - `cam_cat_<key>` / `cam_cat_<key>_target`: optional close-up camera and target for one Bücherstand category section, used on narrow screens and when a book in that section opens.
  - `act_<name>`: a node that an action animates (for example `act_tap_0`, `act_pot_lid`, `act_book_12`, `act_grill`).
  - `rot_<name>`: a part that the engine spins (for example `rot_wheel` or `rot_platform`). Gondolas are `gondola_<n>` and horses are `horse_<n>`.
  - `snow_<n>`: snow caps that the engine shows only when snow is on.
  - `write_<name>`: a flat rectangular mesh (a chalkboard face, a coaster face, a book page, a ticket, a sheet of music) where the engine draws text. Its UVs run 0–1 across the writing area, with +V up the text. Give it a plain surface material (chalk, card, paper) and keep it unlit by baked text.
  - `cam_read_<name>`: an empty for the reading camera in front of `write_<name>`, with `cam_read_<name>_target` on the surface's centre. The writing area should fill most of a 16:9 frame from there.
  - `path_<n>`: ordered empties along the lane that the guided-stroll camera follows between stops (architect, in `square.glb`). See docs/adr/0003-guided-stroll-navigation.md.
- The standard counter top is 1.05 m high. The stall front opening sits between 1.05 m and 2.2 m.
- A reading lamp or other small glow inside a stall that already has its two `light_` empties gets an emissive `bulb_warm` material, not another `light_`.
- 2048 px atlases are fine in the desktop glb as long as the stall stays inside its file budget. Lite files use 512 px.

## Bücherstand categories

The Bücherstand (Reading) holds Mac's 55 Audible books, grouped into the six categories in `content/books/categories.json`. That file is the only source for titles, authors, slugs and categories.

- Carpenter: enlarge the stall with side racks and book carts so it has six labelled category sections, one per category key. Each section has a sign with its German label (`label_de`) and an empty `slot_cat_<key>` at the left end of its lowest usable shelf board. Size each section for its book count plus some room. Write the section dimensions (board widths, number of boards, board spacing, depth) to `blender/stalls/buecher_sections.json` so the vendor can fill them.
- Vendor: one prop set per category, `prop_books_<key>`, parented to `slot_cat_<key>`, with one book per title in that category. Each book is a separate `act_book_<nn>` node pivoted at its base, with a spine that shows the short title and author legibly in a close-up. Untitled filler books are allowed but are not `act_` nodes. Every book's entry in `site/public/models/items.json` carries `name` (title), `author`, `slug` and `category`. The invented titles from earlier rounds go.
- Engineer: clicking a book opens a reading view that shows `content/books/<slug>.md` (summary, key ideas) with a close button and keyboard access, and the plain HTML version lists the same summaries.
- Budget: the Bücherstand with all its props may use 80k triangles and 4 MB.

## Ornament shop, deco goods and book cabinets (ADR 0004)

- Ornament shop (carpenter builds the hut, vendor the goods): `stall_schmuck.glb` (+ lite) replaces `deco_schmuck.glb` for the `deco-schmuck` place. It has the usual slots, two `light_` empties, `cam_view`/`cam_target`, hanging rails as `slot_rail_<n>` empties, `slot_tree` for the display tree and `slot_cabinet` for a glass case. Vendor goods are `prop_schmuck_<group>.glb`, each ornament an `act_orn_<kind>_<n>` node pivoted at its hanging point (baubles: `act_orn_bauble_<n>`, pickle: `act_orn_pickle`, Herrnhut star: `act_orn_herrnhut` with an emissive `bulb_warm` inner, nutcracker jaw: `act_orn_nutcracker_jaw`, smoker: `act_orn_smoker` with `fx_smoke_<n>` empty at its mouth, Schwibbogen: `act_orn_schwibbogen` with `act_orn_candle_<n>` flames, display tree hooks: `hook_tree_<n>` empties). Every ornament has an `items.json` entry with `name`, `label` and `action`. Budget: see the round 9 revision below.
- Ornament shop, round 9 revision (ADR 0004 revision, Mac approved): only three things are interactive. `act_orn_harmonica_<n>` (n = 0..11, left to right): twelve glass baubles in one row on the front rail, the glass harmonica; the engine tunes them to the ballad's melody. `act_orn_mirrorball`: one large (about 18 cm) mercury-glass bauble hung where the camera can reach it, with `cam_dive` / `cam_dive_target` empties for the dive. `act_orn_schwibbogen` with `act_orn_candle_<n>` flames. Everything else is decoration with no `act_` prefix and no `items.json` entry (the nutcracker, smoker with its ambient `fx_smoke_1`, Herrnhut stars, pickle, display tree and its hooks). New node rules: `rot_pyramid` is the turning Erzgebirge pyramid (the engine spins rot_ about Y); `tinsel_<n>` meshes get the engine's glint shader; the back-wall mirror is a mesh named `mirror_<n>` with material `mirror_foxed`. Budget raised to 60k triangles and 3 MB with goods. Further shop slots: `slot_window_l` / `slot_window_r` (lit side windows), `slot_tinsel_<n>` (swag ends); `slot_rail_1` and `slot_harmonica_rail` are the same rail.
- Bratwurst plate (vendor, round 10, ADR 0004 revision): the old `act_sausage_<n>` and `act_roll_<n>` rows become merged scenery. Clickable: `act_wurst_thueringer`, `act_wurst_nuernberger` (a trio), `act_wurst_krakauer`, `act_wurst_curry` (sliced), `act_roll`, the bottles `act_sauce_senf`, `act_sauce_ketchup`, `act_sauce_curry` (each with an `fx_sauce_<name>` empty at its nozzle), `act_shaker_curry`, and the paper plate `act_plate` with `plate_spot_0..3` empties where items land. Each has an `items.json` entry with `name`, `label` and `action`.
- Deco goods (vendor): scenery only (Mac, 2026-10-05). Each deco stall's props fill its counter, both shelves, a hanging rail or eave hooks and one crate or basket at `slot_front`, as one or two merged low-detail meshes on the shared atlas, at most about 4k triangles of goods (1.5k lite), with no `act_` nodes, `fx_` empties or `items.json` entries. Deco stalls are not clickable. The deco budget (20k, 1 MB) includes its goods.
- Book cabinets (carpenter and vendor): six glazed cabinets replace the racks and carts. Each has its sign, `slot_cat_<key>`, `cam_cat_<key>`/`_target` and a door or glass front that is an `act_cab_<key>` node. Inside are angled face-out boards for up to five covers per row, sized for the category's count (write the boards to `blender/stalls/buecher_sections.json`). Books stay `act_book_<nn>` nodes with a designed front cover (title and author legible at the `cam_cat` view, category colour and pattern) and a spine. No publisher cover art.
- People (organizer): about 80 people in `crowd.json` for the full market, with the first 40 entries a good lite crowd. One vendor at every deco stall and the ornament shop (`slot_vendor`), customers at deco counters, and walkers and groups on every lane and at the square's edges.

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

## Budgets (after `optimize.mjs`)

| Asset | Triangles | File |
|---|---|---|
| Section stall with its props | 60k | 3 MB |
| Deco stall with its goods | 20k | 1 MB (shares the kit's textures where possible) |
| Ornament shop with its goods | 60k | 3 MB |
| Ferris wheel / carousel | 80k each | 3 MB each |
| Bandstand with instruments (band players count as person variants, not against this) | 50k | 2 MB |
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
