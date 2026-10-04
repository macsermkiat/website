# Vendor, round 6 notes

This round puts each section's words on an object in its stall (docs/adr/0003, "Text lives in the market").
I added four sets of writing surfaces: the Bierdeckel, the Marktblatt, the wine back labels and the open book.
I also carried the round-4 fixes. Everything is still modelled in code under `blender/props/`. The new printed
surfaces come from a third procedural atlas, `prop_tex_print_*.webp`, drawn by `blender/props/atlas_print.py`.
It is separate from the main and books atlases, so their packing and every set built on them stay as they
were. I added no third-party assets. CREDITS.md now mentions the print atlas and the fonts it uses, all of
them already bundled.

Rebuild and check:

```
python3 blender/props/atlas_print.py                 # print atlas + print_regions.json (also built on demand)
blender/props/run_build.sh <log-tag> --only prop_bier_counter,prop_wurst_counter,prop_gluehwein_wine,book_open \
    [--no-render] [--shots hero]
python3 blender/props/check_props.py [--notes]       # contract checks, now with the round-6 writing checks
/home/claude/tools/bpy-venv/bin/python blender/props/topview.py <set> <out.png> [top|front|persp|back|side]
                                                     # quick 8-sample layout view (scratch only)
node blender/props/threejs_view.mjs <glb in site/public/models> <out.png>
                                                     # pass 2: one glb in plain three.js (AgX), outside the engine
```

## Pass 2: the judges' fixes

All five are done, in the panel's order. Rebuilt this pass: `prop_bier_counter`, `prop_wurst_counter`,
`prop_gluehwein_wine` (full and lite) and the main atlas (`prop_tex_atlas_*.webp`).

### 1. Beer heads: a soft head inside the rim (`goods.beer_fill`, `atlas_goods.g_foam`)

- The head is now **one continuous skin**. It runs from the beer up the inner wall and meets the glass along a
  wavy line 1 to 3.4 mm *under* the rim. Each glass has its own line, higher where the pour left it and lower
  where it has settled. From there it rolls over a soft shoulder into a low, lumpy dome: 7 to 12 mm over the
  rim (Weizen 13 mm), with its top pushed off centre.
- Round 6 pass 1 built the head from two meshes: a band up the wall, then a separate crown with a wet-edge
  ring at the rim. That ring was the "band", and the crown sat on the glass like a cap. Pass 2 has no second
  mesh and no texture or colour seam at the rim. One bubble texture covers the whole head. Its colour runs
  per vertex from a beer-tinted cream where the head meets the beer to pale cream on top.
- The head's rings use the glass's own sides, vertex for vertex (12 sides, 6 in lite). In pass 1 a 14-sided
  head sat in a 12-sided glass, which left dark slits between them, read as a dashed line round the rim.
- The texture (`foam` region, same place in the atlas) is now a fine, soft microfoam. A few small clusters of
  bigger, brighter bubbles break it up, with a hint of amber where the head is thinnest. The old texture's
  dark Voronoi rims and tan "burst" spots looked like cracked plaster under the lamps.
- Only the glass just pulled, on the drip tray, still has a run of foam down its side. A head that sits
  inside the rim does not spill.
- `foam_check.mjs` (in check_props) passes: tallest head 4.8 cm in both builds.

### 2. Pretzels: matte lye crust and coarse salt (`set_bier.pretzel`, `atlas_goods.g_pretzel`)

- They use the plain atlas material now. Pass 1 used `vendor_glaze`, a clear coat at 0.04 roughness, which
  made them look like brown plastic. The crust's roughness is 0.62 to 0.75, with the crumb at 0.9.
- **A new atlas region, `pretzel`** (128 × 384 px), wraps once round the rope (u) and along it (v). The rope
  gets its own UVs, measured from world up, so the dark top and pale underside stay in place.
  - The crust is deep mahogany on top, browner on the flanks and pale and floury underneath where it sat on
    the tray. It has blotches, fine blisters and hairline crazing.
  - Along the top of the belly the crust is torn open into a jagged, pale **Ausbund** with a ragged lighter
    edge. The belly is remapped to v 0.3..0.7, so the split always lands on it.
- **Salt:** 24 coarse crystals per pretzel, 3 to 6 mm across. They are squashed, skewed octahedra with flat
  shading, mostly on the belly and sunk a little into the crust. Pass 1 had nine tiny boxes, which read as
  "white dots". The lite build drops the crystals and keeps a few salt flecks in the texture.
- The arms now run down onto the belly and end pressed into its top. In pass 1 they stopped 3 cm short,
  with open tube ends in the air.
- **The atlas packing is unchanged.** `vendor_atlas.LATE` packs regions added after a round's sets were
  built on their own row under everything else. Their specs go at the end of the list, so older regions keep
  their generator seeds. I checked the result:
  - regions.json is identical for all 89 old regions and the books atlas;
  - the only pixels that changed are the `foam` region and the new row.
  So every other set built on the atlas is still valid without a rebuild.

### 3. Headroom: 2k or more under every section stall; check_props back to 2000

check_props fails a section stall again if it has under 2000 triangles of headroom (`HEADROOM = 2000`). All
three section stalls clear it:

| stall | pass 1 headroom | pass 2 headroom | what went |
|---|---|---|---|
| Bratwurst | 646 | 3298 | The Currywurst slices were whole 12-segment sausages squeezed to 2.4 cm (256 triangles each). They are now short cut drums, 36 each (`goods.sausage(cut=True)`), which saved 1.5k. The rolls have 4 rings from foot to crown instead of 6 (156 to 108 triangles, still 12-sided seen from above) on every roll, the basket's two layers included. The coal bed has 30 larger lumps instead of 40, with the same coverage. |
| Bierstand | 819 | 2369 | The heads: one skin of 12 sides, 132 triangles, against about 270 before. The beer column lost its top cap, which the head hides. One Willibecher of Dunkles is gone: the one behind the row at (0.11, 0.10), so there are 8 full glasses, `act_glass_0..7`, the last on the drip tray. The pretzels gained about 250 triangles (UV-mapped rope and real salt). |
| Glühwein | 1828 | 2088 | The five wine glasses on the wine shelf lost two profile rows (the foot meets the stem in one step and the bowl's floor is one cone), and the wine in them lost one. |

The Glühwein margin is the thinnest. If the carpenter's Glühwein stall grows again, the next trims are the
dried orange slices and star anise on `prop_gluehwein_shelf`.

### 4. The engine switch (surfaces.js, books.js): handed to the engineer, not edited

This round's machine note says not to edit `site/src`. The engineer is rewriting exactly these files right
now, and both show uncommitted edits. So I did not touch them. Where the engine stands today:

- **Coasters: done by the engineer.** `main.js` calls `modelCoasters()` (surfaces.js) and uses my
  `act_coaster_<n>` with `write_coaster_<n>_front/_back` when the props carry them. It falls back to
  `placeCoasters()` only when they don't.
- **Marktblatt: done.** The Bratwurst role `paper` has `aliases: ['writing_paper']`, so `write_writing_paper`
  is picked up.
- **Skip the `_mesh` roles: still to do.** It is one line in `writeNodes()` (surfaces.js):
  ```js
  root?.traverse((o) => { const m = /^write_(.+)$/i.exec(o.name || ''); if (m && !/_mesh(\.\d+)?$/i.test(o.name) && (o.isMesh || o.children.some((c) => c.isMesh))) out[m[1].toLowerCase().replace(/\.\d+$/, '')] = o; });
  ```
  `engine/conventions.js` and `merge.js` already skip `act_*_mesh` the same way.
- **Wine back labels: still to do.** `actions/items/gluehwein.js` `bottle()` still shows the note in a
  speech line. The model side:
  - every `act_bottle_<n>` on `prop_gluehwein_wine` has a `write_label_<n>` (cream paper, UVs 0..1, +V up the
    text) and a `cam_read_label_<n>` with its `_target`, both children of the bottle;
  - the camera stands behind the bottle, so turn the bottle 180° about its base (its node Y in three.js),
    then read from `cam_read_label_<n>`;
  - the note is the writer's (about.md `bottles:`) or the engine's TASTING fallback.

  A kind `paper` surface with role `label_<n>` from `writeNodes()` is all the reader needs.
- **book_open.glb: still to do.** `actions/items/books.js` `buildOpenBook()` still builds its own two-half
  book from boxes. The swap:
  1. Load `book_open.glb` once and clone it per opening.
  2. Put the clicked book's cover on `book_open_cover`: material `book_cover_open`, map
     `prop_tex_books_color.webp`, with offset and repeat from that book's `cover_uv` in items.json.
  3. Take `faces.left` and `faces.right` from `areaFromWriteMesh(write_page_left / write_page_right)`.
  4. Turn a page by rotating `act_page_turn` about its local Y (three.js) from 0 to -2.79 rad, which lands
     it on the left page. `write_page_turn_front` and `write_page_turn_back` carry the two faces of the
     leaf while it turns.
  5. Read from `cam_read_book` with `cam_read_book_target`.

  The root's origin is the foot of the spine, and the book stands open facing +Z (three.js).

### 5. The new Lebkuchen colours, seen in three.js

- `deco_lebkuchen_threejs.jpg`: `prop_deco_lebkuchen.glb` in plain three.js with the engine's AgX tone
  mapping, a warm key and fill from the visitor's side, and a dim sky. The tool is
  `blender/props/threejs_view.mjs` with `threejs_view.html`, which serves the repo on 127.0.0.1 only. The
  hearts read warm mid brown with bright icing, hanging and on the counter alike. **The material fix works
  in three.js.**
- `deco_lebkuchen_engine.jpg`: the same stall in the market (`shoot_items.mjs`, the engine as it stands
  mid-rewrite). There the hearts' faces still read near-black, a dark red at about 20/3/3 in sRGB, while
  their top edges glow orange and the wood behind them is lit.
- I checked the glb for the cause:
  - AO under the hearts: 0.73 to 0.9;
  - front-face normals: exactly +Z, toward the visitor;
  - vertex colour: 0.92;
  - UVs: inside their regions.

  None of these darkens the faces. The stall's lamps hang behind and above the hearts, so the iced faces
  that turn toward the visitor get almost no direct light. That is a stall lighting question for the
  lighting designer and the engineer: a front fill under the awning, or the stroll's reading light at the
  Lebkuchen stop. It does not need another material change. I did not add emission to the hearts to fake it.

## How the writing surfaces are built (all of them)

- A `write_<name>` node is an empty with one flat mesh child, `<name>_mesh`. The mesh's UVs run 0..1 across
  the writing area, with +V up the text in Blender UV space (glTF flips V, which is what
  `surfaces.js/areaFromWriteMesh` expects). check_props reads the UV bounds back from every glb and fails if a
  face's UVs do not span 0..1.
- The writing faces use plain materials: `write_card` (coasters), `write_paper` (Marktblatt), `write_label` (back
  labels) and `write_page` (book pages). Each is one flat colour from COLOR_0, matte, with no baked text and no
  AO. The colour is the measured mean of the printed card or paper around the face (`print_regions.json`,
  `write_colours`), so the seam does not show. They also sample a faint 128 px paper grain,
  `prop_tex_write_grain.webp`. That texture is needed: without one, the web optimiser prunes TEXCOORD_0 from a
  mesh whose material samples no texture. My first build lost every writing face's UVs that way, and so did
  the open book's cover.
- The printed surround (a coaster's rim, the Marktblatt's masthead and border, a back label's small print, a
  page's margins) is a separate mesh with a hole exactly where the writing face is. The two are coplanar and
  never overlap, so nothing z-fights.
- `cam_read_<name>` and `cam_read_<name>_target` are placed square to the face, at the distance where the area
  fills about 80 % of a 16:9 frame at the engine's 42° field of view (`vprint.reading_distance`).
- The previews show stand-in text on the writing faces (`vstage.preview_texts`). It renders only and changes
  nothing exported. It shows where the engine's words go and proves the UV orientation: every line in the
  renders reads upright. The text comes from content/ (the project names and summaries, the writing intro, The
  Order of Time). The four tasting notes are my own placeholders: the writer owns the real ones.

## Round 6 priorities

### 1. Bierstand: one Bierdeckel per project (`prop_bier_counter`)

- `content_projects.py` reads `content/projects.md` at build time: one coaster per `###` heading (now ProtoCol,
  Target Trial Emulation and Transfusion Audit), then 2 spares. If the writer adds a project, the next build
  adds its coaster.
- Each coaster is `act_coaster_<n>` (n = 0, 1, 2 for the projects in order, 3 and 4 for the spares): 10.7 cm
  across, 2 mm board. Its origin is the middle of its underside, which is where it rests. Children:
  - `write_coaster_<n>_front`: 60 × 44 mm, facing up. u runs along +X and v along +Y, so the text reads from
    the front of the stall.
  - `write_coaster_<n>_back`: 70 × 62 mm, facing down. It reads upright once the coaster is turned over about
    its own X axis (u along +X, v along -Y).
- The print: a coloured rim band lettered "NACHTMARKT-BRÄU · FRISCH VOM FASS ·" in Oswald, with a thin rule
  inside it, a brewer's star with a Fraktur N (the Nachtmarkt-Bräu mark) above the writing area, and a small
  line under it. The back has a thin double rule. The colourway follows the project's beer style line:
  Helles gold, Dunkles brown, "Cellar reserve" bottle green, spares red (blue and the cycle cover other
  styles). There is a faint old beer ring on the band and a little wear at the edge.
- Layout: the three project coasters lie side by side at the left front of the counter, where a visitor can
  pick them up. The two spares make a small stack behind them. The pretzel board moved back and the bar towel
  moved to the right of the tap tower.
- items.json: `name` ("Bierdeckel: ProtoCol"), `kind: "coaster"`, `project` (the heading, null on spares),
  `colourway`, `write: {front, back}`, `size_cm`. The node extras carry `name`, `kind`, `project` and `write`.
- Each coaster is a 28-sided disc (10 sides in lite). The two coasters under the full Maß are plain discs, and
  they are in lite too so the two builds keep the same bounds.

### 2. Bratwurst: the Marktblatt (`prop_wurst_counter`)

- A pad of greaseproof market paper sits in front of the raw-sausage tray, between the grill tongs and the
  roll basket, about 0.7 m right of the grill and beside the warming tray. Its print is brick red: a
  "Nachtmarkt-Blatt" Fraktur masthead, "Bratwurst · Currywurst · frische Brötchen · Senf vom Fass", a double
  frame, a border of stars, firs and little stalls, and a grease spot in one corner.
- The top sheet is `act_writing_paper` (origin at the middle of its underside, on the pad), 28 × 21 cm, with
  `write_writing_paper` (21.8 × 13.0 cm) over its blank middle. `cam_read_writing_paper` and its target are
  children of the sheet: the camera leans over it from the front at 62°, as a visitor leans over the counter.
- The engine's stand-in role was `paper`. The model's is `writing_paper`, the name the brief gave it.

### 3. Bücherstand: `book_open.glb` (new, `blender/props/set_bookopen.py`)

- This is a standalone model, not placed at a slot. props.json lists it under a new `standalone` key, so the
  `sets` list the engine places stays the same. The root node is `book_open`. The book stands open, upright and
  facing the reader (Blender -Y, three.js +Z). The spine is vertical at x = 0, and the origin is the foot of the
  spine. Each half leans back 10°. The pages are 15 × 22 cm, the cloth boards have 4 mm squares, and the page
  block is 11 mm per half and dips into a narrow gutter.
- `write_page_left` and `write_page_right`: 10.7 × 17 cm each, with margins of 3 cm at the gutter, 1.3 cm at
  the fore-edge and 2.6 cm at the foot.
- `act_page_turn`: the turning leaf, hinged on the spine axis. At rest it lies 0.4 mm under the right page, so
  it is hidden. Rotating `act_page_turn` about its local Z (three.js: local Y) from 0 to -2.79 rad
  (−(π − 2·10°)) lays it 0.4 mm under the left page, so it shows only while it turns. It carries
  `write_page_turn_front`, for the right page's words as it lifts, and `write_page_turn_back`, for the next left
  page as it lands (u runs along −x on the leaf, so the back reads correctly once the leaf has turned). The leaf
  is rigid. items.json and the node carry the turn angles.
- `cam_read_book` and `cam_read_book_target`: square to the spread. The two writing areas fill about 80 % of
  the frame.
- `book_open_cover`: the outside of the left board, which is the front cover. Its UVs run 0..1 across the cover
  (u from the spine to the fore-edge seen from outside, v up) on material `book_cover_open`. The engine can put
  the clicked book's own cover on it: `prop_tex_books_color.webp` with that book's `cover_uv` from items.json as
  the offset and repeat.
- The rest is static: page surfaces, fore-edge, head and tail page lines, cloth boards, a curved cloth
  backstrip, two red-and-cream headbands, and a red ribbon marker down the right gutter that hangs out over the
  tail. Full: 324 triangles, 26 kB. Lite: 284 triangles, 23 kB. The shared print and grain textures are not
  counted in those sizes.

### 4. Glühwein: a back label on every wine bottle (`prop_gluehwein_wine`)

- Each of the 12 bottles has a back label on its back (+Y), in the same height band as the front label.
  There is a printed surround (the estate's name in IM Fell small caps, region and vintage, a short rule, and
  "Gutsabfüllung · Qualitätswein", volume and % vol, "Enthält Sulfite · Deutschland") and a blank writing
  strip, `write_label_<n>`, where n is the bottle's number. All back labels are cream paper, even where the
  front label is dark (Ahr, Dornfelder), so the engine's print ink reads. They are printed in the estate's
  ink, or in its accent colour where the ink is light.
- The strip follows the glass (a curved band). The engine's least-squares area fit puts the text plane on the
  chord. The strip is narrow: 49° of arc, about 3.2 cm wide and 3.6 cm tall on a Schlegel bottle, and up to
  about 3.5 mm off the chord at its edges, so flat text reads cleanly from the reading camera. The Bocksbeutel's
  back is nearly flat anyway.
- `cam_read_label_<n>` and its target are children of the bottle and sit behind it. Once the engine turns the
  bottle round (180° about its base), the camera stands in front of the label. The preview turns the first four
  bottles that way.

### 5. Round-4 fixes (review/round-4/vendor/JUDGES.md)

- **Lebkuchen hearts.** They read near-black in the browser. The dough in the atlas is now a warm mid brown
  (`a85e2a` mottled toward `824619`, with lighter baked patches; round 4 was `7a3f1c`..`5a2c12`). The hearts
  now use the plain atlas material, not `vendor_glaze`. In three.js that clear coat mirrored the night sky over
  the dark dough. The sugar sheen stays, in the roughness map (0.5). The icing is brighter (`fffbf2`, a brighter
  yellow and pink and blue), the piped dots and lines are thicker, and the lettering gets a 1 px icing halo so
  it reads at market distance. I rebuilt the main atlas: its packing is unchanged (regions.json is identical)
  and only the six `lebkuchen_*` regions changed, which I checked pixel by pixel. So every other set keeps
  working with the new `prop_tex_atlas_*.webp`.
- **Helles.** It is a lighter, yellower gold, `f5b71e` (round 4 `e6a012`). The light end of the column's
  gradient is unchanged in code, so it lifts with the base colour. Dunkles, Weißbier and Radler are unchanged.
- **Lite pint glass alpha.** `vendor_glass_pint` in lite is now 0.2 (was 0.15), so the emptied glasses read as
  glasses.
- **`prop_bier_counter_hero.jpg`** is re-rendered with the current materials and the preview-only
  `beer_preview` set-up. This round it frames the coasters and the two full Maß of Helles.

## Previews (review/round-6/vendor/)

The Cycles renders are 1280 × 720, 48 samples, CPU, from this round's glbs, on the plain wooden counter at
night. The text on the writing faces is the preview-only stand-in described above. Pass 2 re-rendered the
first three and added the two three.js shots.

| file | shows |
|---|---|
| `prop_bier_counter_hero.jpg` | **pass 2**: the five Bierdeckel (project names and styles on the fronts, the spares stacked), the matte lye-crust pretzels with their Ausbund and coarse salt, the two full Maß of Helles with the new soft heads |
| `prop_bier_counter_foam.jpg` | **pass 2**: the heads close up from a visitor's eye (Maß, Willibecher of Dunkles, Weizen): one soft, uneven skin inside each rim, no cap and no band |
| `prop_wurst_counter_hero.jpg` | **pass 2**: the Marktblatt pad with "Off the grill" on the top sheet, the warming and raw trays, the 4-ring rolls in their basket, the grill behind |
| `deco_lebkuchen_threejs.jpg` | **pass 2**: three.js (AgX, light from the visitor's side): the Lebkuchen hearts warm brown with bright icing |
| `deco_lebkuchen_engine.jpg` | **pass 2**: the same stall in the engine as it stands: the hearts' faces dark under the stall's back lighting (see fix 5) |
| `prop_gluehwein_wine_hero.jpg` | four wine bottles turned round: the back labels, each with its estate and small print and a tasting note in its writing strip |
| `book_open_hero.jpg` | book_open.glb on the counter: The Order of Time on the two writing pages, cloth boards, page edges, headband, ribbon |
| `deco_lebkuchen.jpg` | the Lebkuchen stall's goods with the warm brown hearts and brighter icing |
| `deco_goods_contact_sheet.jpg` | all nine deco frames. Lebkuchen is new. The other eight are the round-4 frames of sets that did not change (their goods use the main atlas, whose other regions are identical) |
| `prop_books_physics_hero_r4.jpg`, `prop_books_people_hero_r4.jpg` | round-4 close-ups of two category sets, copied here for the spine-legibility check. Those sets did not change this round |

## Budgets

The carpenter's stalls grew this round by about 1.7k triangles each (Bierstand 41505, Glühwein 38780,
Bratwurst 38378). With the new coasters, the Marktblatt and the back labels, my first full build left the
Bierstand and Glühwein sections under 100 triangles from the 60k budget. To win room back without touching
anything a visitor handles, I trimmed:

- the clean glasses upside down on the Bierstand's upper shelf from 10 to 8 sides (6 in lite; 5 broke the
  1 cm full/lite bounds rule on the Maßkrüge)
- the Glühwein shelf's wine glasses from 12 to 10 sides
- the coasters to 28 sides

Pass 1 lowered check_props' rule to fail a section stall under 500 triangles of headroom. **Pass 2 puts it
back to 2000** after the trims under "Pass 2, fix 3". The headroom is now Bratwurst 3298, Bierstand 2369 and
Glühwein 2088.

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2610 (35%) | 183 / 99 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 6254 | 2051 (33%) | 164 / 82 | 2.29 × 0.24 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 5428 | 2194 (40%) | 144 / 98 | 2.33 × 0.23 × 0.42 |
| prop_bier_counter | bierstand | slot_counter | 8628 | 3266 (38%) | 185 / 114 | 2.37 × 0.45 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 4356 | 1812 (42%) | 102 / 53 | 2.33 × 0.25 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3194 | 1566 (49%) | 56 / 33 | 1.91 × 0.23 × 0.26 |
| prop_wurst_counter | bratwurst | slot_counter | 18324 | 5630 (31%) | 435 / 217 | 3.42 × 0.48 × 0.64 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1624 | 464 (29%) | 59 / 24 | 1.86 × 0.22 × 0.28 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1588 | 440 (28%) | 58 / 23 | 1.86 × 0.19 × 0.27 |
| prop_books_counter | buecherstand | slot_counter | 2144 | 900 (42%) | 66 / 38 | 2.09 × 0.45 × 0.40 |
| prop_books_physics | buecherstand | slot_cat_physics | 982 | 296 (30%) | 64 / 38 | 0.46 × 0.20 × 0.66 |
| prop_books_lives | buecherstand | slot_cat_lives | 814 | 264 (32%) | 52 / 30 | 0.40 × 0.44 × 0.55 |
| prop_books_mind | buecherstand | slot_cat_mind | 928 | 280 (30%) | 60 / 35 | 0.42 × 0.21 × 0.66 |
| prop_books_people | buecherstand | slot_cat_people | 1084 | 344 (32%) | 73 / 46 | 0.52 × 0.20 × 0.63 |
| prop_books_decisions | buecherstand | slot_cat_decisions | 994 | 304 (31%) | 65 / 39 | 0.49 × 0.45 × 0.58 |
| prop_books_craft | buecherstand | slot_cat_craft | 748 | 240 (32%) | 47 / 27 | 0.35 × 0.21 × 0.66 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 5102 | 1870 (37%) | 166 / 90 | 2.20 × 0.45 × 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 2774 | 1302 (47%) | 122 / 83 | 1.98 × 0.48 × 0.44 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3790 | 1368 (36%) | 127 / 71 | 2.11 × 0.48 × 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 2836 | 1668 (59%) | 127 / 82 | 2.01 × 0.46 × 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 2788 | 1344 (48%) | 121 / 79 | 2.16 × 0.39 × 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 4556 | 1968 (43%) | 126 / 80 | 2.02 × 0.48 × 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 3648 | 1434 (39%) | 106 / 65 | 2.06 × 0.47 × 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4104 | 1656 (40%) | 122 / 62 | 2.18 × 0.47 × 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 4408 | 1617 (37%) | 129 / 83 | 2.06 × 0.48 × 0.27 |

All prop glbs together: 2.96 MB full and 1.69 MB lite. Shared textures (`prop_tex_*`): 1.43 MB full and 0.23 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2000 headroom):

| stall | stall tris | + props | total / budget | headroom | MB / budget |
|---|---|---|---|---|---|
| gluehwein | 38780 | 19132 | 57912 / 60k OK | 2088 | 2.32 / 3 |
| bierstand | 41453 | 16178 | 57631 / 60k OK | 2369 | 2.27 / 3 |
| bratwurst | 38378 | 18324 | 56702 / 60k OK | 3298 | 2.27 / 3 |
| buecherstand | 48098 | 10906 | 59004 / 80k OK | 20996 | 2.87 / 4 |

Deco stalls, stall plus goods against 20k (check_props fails over):

| deco stall | stall tris | goods | total / 20k | room |
|---|---|---|---|---|
| lebkuchen | 13433 | 5102 | 18535 OK | 1465 |
| mandeln | 15985 | 2774 | 18759 OK | 1241 |
| kerzen | 14143 | 3790 | 17933 OK | 2067 |
| spielzeug | 15938 | 2836 | 18774 OK | 1226 |
| schmuck | 15799 | 2788 | 18587 OK | 1413 |
| kaese | 13380 | 4556 | 17936 OK | 2064 |
| crepes | 13283 | 3648 | 16931 OK | 3069 |
| maroni | 14346 | 4104 | 18450 OK | 1550 |
| puffer | 14978 | 4408 | 19386 OK | 614 |

<!-- check_props:end -->

## Open issues

- **Engine, still for the engineer (pass 2, fix 4).** The coasters and the Marktblatt are switched over.
  Three things are left: the one-line `_mesh` skip in `writeNodes()`, `write_label_<n>` on the bottles, and
  `book_open.glb` in place of `buildOpenBook()`. They are in `site/src`, which I may not edit this round.
  The exact changes are under "Pass 2, fix 4".
- **The Lebkuchen hearts are dark in the market's lighting** even though their material reads right in
  three.js (pass 2, fix 5). The iced faces need light from the visitor's side. That belongs to the lighting
  designer or the engineer.
- **The Glühwein section's headroom is the thinnest** at 2088. The next trims would be the orange slices and
  star anise on `prop_gluehwein_shelf`.
- **One fewer beer glass.** The Bierstand counter has 8 full glasses (`act_glass_0..7`), not 9. items.json
  is regenerated, and the engine reads glasses by name and kind, not by count.
- **The glass rims.** The dashed dark line round the rim in pass 1 came from the head's 14 sides inside a
  12-sided glass, and it is gone. What is left is a thin, even dark line at the lip, which is the inner wall of
  the glass above the head's edge.
- **The back labels are curved**, not flat rectangles as BUILD.md describes write_ meshes. A flat card on a
  round bottle would stand off the glass by about 4 mm at its edges, which shows on the shelf. I kept the
  curve small (see above). If the engine wants a strictly flat face, I can add a flat, invisible write_ plane on
  the chord instead.
- **The open book's leaf is rigid.** It does not curl as it turns. A curl would need bones or morph targets
  that the separate flat writing faces could not follow, so I left it rigid.
- **The tasting notes are placeholders** in the preview only. The real notes belong to the writer, in
  content/. Nothing about them is baked into the glbs.
- **Lite book_open** keeps about 88 % of the full triangles, because it is only 324 triangles and every node
  must match.
- **The Bier vendor's hat** (round-3 market judges) belongs to the organizer, as before.
