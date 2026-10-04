# Carpenter: round 3 notes

Built on the cloud machine (CPU, `NM_THREADS=3`, shared with the engineer and lighting designer). Every number below was measured on `site/public/models` after `optimize.mjs`.

## Round 3 priority: the Bücherstand category sections

Mac asked for more bookshelves, grouped by category. The Bücherstand now has six labelled sections, one per key in `content/books/categories.json`:

| Visitor's left to right | Section (`label_de`) | Books | Boards | Capacity at 4.2 cm a spine |
|---|---|---|---|---|
| left side rack, outer bay | physics: Physik & Kosmos | 10 | 2 x 0.56 m | 26 |
| left side rack, inner bay | mind: Geist & Körper | 9 | 2 x 0.54 m | 25 |
| left book cart | lives: Lebensgeschichten | 6 | 2 x 0.52 m (stepped) | 24 |
| right book cart | decisions: Risiko & Entscheidungen | 11 | 2 x 0.60 m (stepped) | 28 |
| right side rack, inner bay | people: Menschen & Gespräche | 14 | 2 x 0.65 m | 30 |
| right side rack, outer bay | craft: Handwerk & Gewohnheit | 5 | 2 x 0.45 m | 21 |

What was built:

- **Two side racks ("wings").** Each is an open green bookcase with two bays. They stand at the hut's front corners, splayed 50° so their faces turn toward a visitor in front of the counter.
  - Construction: walnut boards with worn edges, plank backs, a framed plinth, cream edge strips and cornice.
  - Each rack has a little shingled pent roof on back posts with knee braces, a cream fascia, a bulb string (`bulbs_0`) under the front edge, and its own snow cap (`snow_2`, `snow_3`).
- **Two wheeled book carts** in front of the glazed cabinets. Each has two stepped tiers (the upper tier stands behind the lower tier's books), stepped oak side panels, iron corner straps, two spoked wheels with iron tyres, front legs, a push bar, and a sign on two iron rods with finials.
- **One sign per section, as its own mesh `sign_cat_<key>`.**
  - A cream board with a thin gold border and deep-green Alegreya SC lettering.
  - Labels with " & " are set on two lines ("Physik &" / "Kosmos") so the letters stay large: 15 cm text block, about 6.6 cm a line. "Lebensgeschichten" is a single line on a wider cart sign (85 x 6.3 cm).
  - The letters are painted (flat front faces, the new `Part.flat_text`). The board material is `paint_glow`, so the signs stay legible under the site's moonlight (see `stall_buecher_threejs.jpg`).
  - Spelling comes straight from `label_de`.
- **One empty `slot_cat_<key>` per section,** at the left end of its lowest board, on the board's top surface at its front edge, rotated with its rack (+X along the board, -Y toward the visitor).
- **`blender/stalls/buecher_sections.json`** describes every section: slot position and rotation, board count, width, depth, thickness, spacing, per-board offsets and clear heights, capacity and the sign.
  - It is written by `blender/stalls/buecher_sections.py`, the module `buecher.py` builds from, so the two cannot drift apart.
  - I wrote it before the long renders, and the vendor has already shipped `prop_books_<key>` against it. The final Bücherstand preview shows those sets on the racks and carts.
  - `python3 blender/stalls/buecher_sections.py --check site/public/models/stall_buecher.glb site/public/models/stall_buecher.lite.glb` compares every `slot_cat_` node in the glb with the json. Result: "matches buecher_sections.json" for both LODs (positions within 2 mm, rotations ±50°/0°).
- **Kept:**
  - `slot_shelf_1`, `slot_shelf_2`, `slot_counter`, `slot_vendor`, `slot_sign`, `slot_front`, `cam_view`/`cam_target`, `slot_cabinet_l/r` and exactly two `light_` empties.
  - `light_1` moved 15 cm further out (to `yF - 0.85`, z 2.3) so it reaches both carts and wings.
  - `cam_view` stands back 4.2 m from the front (was 3.4 m) to take in the wider front.
- **The lantern** that hung at the front-right corner (where the right rack now stands) moved to the right side wall, with its bracket pointing back to the wall.

### Footprint and the lane (`site/src/layout.json`)

- **New footprint** in the stall frame (front = -Y):
  - x from -2.87 to +2.87; it was -2.2 to +1.9 with the bay window.
  - y from -2.40 (rack canopy edges and cart fronts) to +1.45 (roof overhang).
  - The racks and carts only extend the front, as BUILD.md allows. The hut itself is unchanged: 3.7 x 2.5 m plus the bay window.
- **Clearances I measured** (stall at `[12.8, 2.6]`, rotY -0.8):
  - **Lane in front.** The crowd's walker paths pass 2.9 m or more in front of the stall centre (y ≤ -2.85 in the stall frame), so nothing reaches into the lane. The closest path end (walker_2/3) stops 0.45 m in front of the right rack.
  - **Bierstand.** Its front-right roof corner (with 0.4 m roof padding) is at stall-frame (-3.68, -1.74), 0.9 m from the outer end of the left rack.
  - **String-light pole 4** is at (2.54, +0.6), behind the right rack and clear of it by more than 1.8 m.
- **Organizer:** `browsing_buecherstand` places its two browsers at about stall-frame (±1.4, -1.95), which is where the carts now stand. Please re-run `crowd_plan.py`: they belong in front of the carts or at the racks (y ≈ -2.6).

## Round 2 open points

| Point (source) | What I did | How to check |
|---|---|---|
| Bier crest-sign lamps left bright ovals on the roof snow (Opus) | Narrow spots (36°, blend 0.35) from the lamp heads, aimed at the upper half of the board, as on the Bratwurst. | `stall_bier_preview.jpg`: the board is lit, with no ovals under it (the soft glow on the eave snow is the stall's front light, `light_1`) |
| Deco sign lamps did the same (Mandeln, Holzspielzeug, Maroni) | Same fix in `deco.py`: 34° spots aimed at the upper board, energy 45. The nine structures were rebuilt and re-rendered. | `deco_contact_sheet.jpg` |
| Bücher cabinet spines barely read in Cycles and three.js (Opus, Fable) | Binding tints are one step lighter (about 1.25x). The Cycles preview lights each cabinet with three small lights (top 16 W, middle 7 W, low 6 W; it was 7 + 3). I did not add an emissive stand-in: glTF emission ignores vertex colour, so every spine would glow the same tint. Note that the carts now stand in front of the cabinets' lower half. | `stall_buecher_preview.jpg`, `stall_buecher_signs.jpg` |
| Codex #5: cabinet books are one merged untitled mesh and should be clickable | Not done, on purpose. Under BUILD.md's new 'Bücherstand categories', the 55 real titles live in the vendor's `prop_books_<key>` sets as `act_book_<nn>`, and untitled filler books "are allowed but are not act_ nodes". The cabinet spines are that kind of filler (`buecher_books`, 816 tris). | BUILD.md, 'Bücherstand categories' |
| Codex #4: the Bücherstand with props was 3.04 MB against 3 MB | Its budget is now 80k / 4 MB. With all its props it is about 59k tris and 1.9 MB (table below). | below |
| README: the rauten figure said "about 3 KB" (Opus) | Corrected to 6.4 KB. | `blender/lib/README.md` |
| `stall_bratwurst.lite.glb` predated the last full build (Fable) | Rebuilt both Bratwurst LODs in one script run this round (geometry unchanged). | file times |
| 40k stall / 20k props split (both judges) | Market owner's call. BUILD.md now gives the Bücherstand 80k / 4 MB with props. The Bücherstand is 48k because the racks, carts and signs are carpentry; its props are 11k. | |

## Triangles and file sizes (after `optimize.mjs`)

| File | Triangles | Size | Lite triangles | Lite size |
|---|---|---|---|---|
| stall_gluehwein | 37,603 | 0.94 MB | 8,066 | 0.21 MB |
| stall_bratwurst | 36,391 | 0.86 MB | 7,467 | 0.21 MB |
| stall_bier | 39,745 | 1.01 MB | 9,641 | 0.26 MB |
| **stall_buecher** | **48,074** | **1.30 MB** | **14,185 (30 %)** | **0.40 MB** |
| deco_lebkuchen | 13,433 | 0.38 MB | 3,986 | 0.13 MB |
| deco_mandeln | 15,985 | 0.41 MB | 4,653 | 0.13 MB |
| deco_kerzen | 14,143 | 0.39 MB | 4,046 | 0.13 MB |
| deco_spielzeug | 15,938 | 0.42 MB | 5,041 | 0.15 MB |
| deco_schmuck | 15,799 | 0.42 MB | 4,315 | 0.13 MB |
| deco_kaese | 13,380 | 0.36 MB | 4,354 | 0.13 MB |
| deco_crepes | 13,283 | 0.37 MB | 3,699 | 0.12 MB |
| deco_maroni | 14,346 | 0.37 MB | 4,949 | 0.14 MB |
| deco_puffer | 14,978 | 0.40 MB | 4,519 | 0.14 MB |
| shared kit `deco_kit_*.webp` | | 0.46 MB | | 0.20 MB |

- **Where the Bücherstand's 48k goes:**
  - hut and cabinets (as in round 2): about 34.6k;
  - six signs with flat painted letters: 3.9k (raised letters were 14.4k, so I switched to painted ones);
  - rack carcasses, boards and canopies, carts with spoked wheels: about 7k;
  - canopy snow: 1.4k;
  - bulbs: about 0.6k.
- **The Bücherstand with the vendor's current sets** (`prop_books_<key>` x6: 5,550 tris; shelf_1, shelf_2 and counter: 5,356) comes to **59.0k tris** against 80k. Its size is about 1.3 + 0.6 MB of glb plus the shared atlases, against 4 MB. Lite: 14.2k + about 3.5k.
- The other three section stalls and the nine deco structures are unchanged in geometry (the deco and Bratwurst glbs were re-exported from the same scripts), so the round-2 headroom figures still apply.
- **Contract checks:** `glb_tools.check` passes on all 26 stall and deco files. For `stall_buecher*` it now also requires `slot_cat_<key>` and `sign_cat_<key>` for every category key.
  - Every stall has `slot_counter`, `slot_shelf_1`, `slot_shelf_2`, `slot_vendor`, `slot_sign`, `slot_front`, `light_*`, `bulbs_*`, `snow_*`, `cam_view`, `cam_target` and material `bulb_warm`.
  - `slot_counter` is at 1.050 m in every file.
- **Sign text (3D):**
  - Main signs: Glühwein, Bratwurst, Bier vom Fass, Bücher, Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer.
  - Category signs: Physik & Kosmos, Lebensgeschichten, Geist & Körper, Menschen & Gespräche, Risiko & Entscheidungen, Handwerk & Gewohnheit.

## Previews in this folder

- `stall_buecher_preview.jpg`: Cycles, 1280x720, 48 samples, 3/4 front view at night. It shows the vendor's shipped `prop_books_<key>` sets on the racks and carts (imported at their rotated slots), plus the shelf and counter sets. The emissive stand-ins are off.
- `stall_buecher_signs.jpg`: Cycles, 1280x720, 48 samples, from about the stall's `cam_view`. It shows the six category signs.
- `stall_buecher_threejs.jpg`: the bare shipped glb in three.js (SwiftShader, AO on, snow off as on the site), same camera as the Cycles preview. The `paint_glow` signs read under moonlight. The racks are empty because no props are attached.
- `stall_bier_preview.jpg`: re-rendered with the narrow sign-lamp spots.
- `stall_gluehwein_preview.jpg`, `stall_bratwurst_preview.jpg`: re-rendered this round with the vendor's current props (geometry unchanged).
- `deco_contact_sheet.jpg`: the nine deco structures, re-rendered with the narrow sign-lamp spots (32 samples).

## Library (`blender/lib/`) changes this round (no existing name or default changed)

- `geo.Part.flat_text`: painted lettering, one front face per glyph in full builds too. A `\n` in `text()` starts a second line.
- `render.import_glb(..., rotate=False)` and `pipeline.vendor_props(..., rotate=False)`: `rotate=True` applies a rotated slot's rotation.
- `glb_tools.check` also checks the Bücherstand's category nodes.
- `pipeline.ROUND` defaults to 3.
- The README documents these, plus the narrow sign-lamp rule for previews and `stalls/buecher_sections.py`.

## Rebuild

- Bücherstand: `NM_THREADS=3 /home/claude/tools/bpy-venv/bin/python blender/stalls/buecher.py [--no-render] [--no-lite]`. It writes both glbs and the preview; run `python3 blender/stalls/buecher_sections.py` after changing the plan.
- `--cam x,y,z,tx,ty,tz,lens --preview-name stall_buecher_signs` gives the sign close-up.
- On the loaded machine one LOD takes about 1 min to build and AO-bake, and the 1280x720 preview takes about 6 min.
- bpy segfaults at exit (code 139) after writing everything; this is harmless.

## Open issues and what I would improve next

- **The racks and carts make the Bücherstand busier from the home view.** The carts hide the lower half of the glazed cabinets. The cabinets still show their upper three shelves.
- **`cam_view` can't show every section.** At 4.2 m it frames the counter and both carts, and the outer bays (physics, craft) sit at the frame edge. The engineer may want per-section close-ups. I can add optional `cam_cat_<key>` empties if that helps; I did not invent a node prefix without the market owner.
- **Capacity is generous** (2–4x the shelf length the titles need), as BUILD.md asks for "some room". The vendor's sets fill the gaps with face-out covers and fillers.
- **The rack canopies cast a shadow on the upper boards** under the site's `light_1`. Their bulb strings glow but light nothing in the browser. A lighting pass, or a stand-in on the book boards, would help the upper boards read.
- **Organizer:** re-run the crowd plan for the Bücherstand browsers (see above).
- Carried over from round 2: emissive stand-ins as a workaround, bevels as real geometry, soft scorch decal on the Bratwurst.
