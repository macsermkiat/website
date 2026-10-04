# Vendor, round 3 notes

All goods are still modelled in code under `blender/props/` and textured from two procedural atlases (goods and
books). No third-party models or images; the only third-party assets are the OFL fonts already credited. In
CREDITS.md (Vendor section) I changed only the wording: the book textures now carry only Mac's titles, and the
open book is a guest book, no longer *Faust*.

Rebuild and check:

```
python3 blender/props/vendor_atlas.py                 # atlases -> blender/out/vendor/ (main, books, coal pair)
blender/props/run_build.sh <log-tag> [--only a,b] [--no-render] [--no-lite] [--no-ao] [--samples 48] \
    [--res 1280x720] [--shots wide,hero,stall]        # build_props.py with NM_DEVICE / NM_THREADS (default CPU / 2)
python3 blender/props/check_props.py [--notes] [--no-seat]   # contract checks; exit 1 on FAIL
node blender/props/foam_check.mjs                     # beer heads as the browser decodes them (also run by check_props)
python3 blender/props/books_catalog.py                # the 55 books, their numbers, spine titles and designs
```

bpy may segfault on exit after `build_props.py` has written everything; the outputs are complete.

## Round 3 priorities

### 1. Mac's 55 books, one section per category

- **Source.** `content/books/categories.json` is the only source. `blender/props/books_catalog.py` reads it and
  numbers the books 00..54 in file order, so `act_book_<nn>` stays the same book from build to build. It holds
  each copy's look: binding (dust jacket, paperback, or a cloth case for a secondhand copy with no jacket),
  real-world size, colours, typeface and cover motif. It also holds a short spine title (the full title, split
  over two lines when it is long) and the author's surname(s). The designs are original typographic spines and
  covers; no publisher artwork is copied.
- **Atlas.** `atlas_books.py` draws a spine (`spine_b<nn>`) and a front cover (`cover_b<nn>`) for every book.
  Each one is sized to the book's real proportions at one texel density (27 × 20 px per cm on spines, 10 px
  per cm on covers), so no spine is stretched and every title is equally sharp. It also draws 18 untitled
  filler spines (cloth with blind rules, leather with raised bands and blank labels, plain paper with a colour
  band). The books atlas is now 2048 × 2816; round 2 was 2048 × 3584. The open book on the counter is the
  bookseller's guest book: handwritten greetings in Caveat and no printed title. Round 2 showed *Faust* there.
- **Sets.** There is one set per category, `prop_books_<key>` → `slot_cat_<key>` of `stall_buecher`. It is
  built from the carpenter's `blender/stalls/buecher_sections.json` (version 1, read on 4 October at 02:14). Each board's
  offset, width, depth and clear height come from that file. I invented no layout: `set_books.sections()`
  raises if the file is missing. Books are split over the section's two boards (the upper board gets the larger
  half). Each board's titled books stand together, spine out and 12 mm behind the board's front edge, among
  untitled filler books. About a fifth of the spare width is left free at the right end, with a brass bookend
  (room to restock). Heights stay under each board's clear height minus 12 mm; depths stay inside the board.
  On the carts, the lower tier's books stay under the upper tier's board.
- **Nodes and pivots.** Every titled book is its own `act_book_<nn>` empty with its origin at the middle of
  the spine's foot (base pivot), the spine toward -Y, one material `book_cover_<nn>`, and a mesh child
  `act_book_<nn>_mesh`. The front cover is the +X board, with the spine on its left. Filler books are merged
  into the set's static mesh and are not `act_` nodes.
- **items.json** has, for every book: `name` (= title), `title`, `author`, `slug`, `category`, `category_de`,
  `cover_material`, `cover_uv` (glTF space, top-left origin), `cover_texture`, `size_m`, `set` and `stall`.
  check_props confirms the following: each of the 55 slugs is exactly one `act_book_` node in its category's
  set; name, author and category match categories.json; every slug has `content/books/<slug>.md`; and no
  `act_book_` carries any other title.
- **Old Bücherstand sets.** `prop_books_shelf_1`, `prop_books_shelf_2` and `prop_books_counter` keep their
  slots and now hold only untitled secondhand stock: standing runs, lying stacks and bookends. They have no
  `act_book_` nodes and no invented titles. The counter keeps the guest book on its reading stand, a second open
  book, bookmarks, price cards, the cash box and the banker's lamp. It also has two face-out display copies of
  Mac's books on small easels, *The Order of Time* and *Atomic Habits*. These copies are static, so each title
  is clickable only once, on its category shelf.

| set | slot | books (act_book_<nn>) |
|---|---|---|
| prop_books_physics | slot_cat_physics | 00 The Many Hidden Worlds of Quantum Mechanics; 01 The Biggest Ideas in the Universe; 02 Quanta and Fields; 03 Chaos; 04 Reality Is Not What It Seems; 05 On the Origin of Time; 06 Mysteries of Modern Physics: Time; 07 Something Deeply Hidden; 08 The Order of Time; 09 Infinite Powers |
| prop_books_lives | slot_cat_lives | 10 Elon Musk; 11 The Making of the Atomic Bomb; 12 The Meaning of It All; 13 Einstein; 14 Surely You're Joking, Mr. Feynman!; 15 What Do You Care What Other People Think? |
| prop_books_mind | slot_cat_mind | 16 The Laws of Human Nature; 17 Man's Search for Meaning; 18 Grit; 19 How to Be Bold; 20 The Courage to Be Happy; 21 The Courage to Be Disliked; 22 Ultra-Processed People; 23 Breath; 24 The Almanack of Naval Ravikant |
| prop_books_people | slot_cat_people | 25 Unreasonable Hospitality; 26 Six-Minute X-Ray; 27 Set Boundaries, Find Peace; 28 Cues; 29 Captivate; 30 How to Know a Person; 31 Crucial Conversations; 32 The Next Conversation; 33 Supercommunicators; 34 Influence; 35 Never Split the Difference; 36 Unf*ck Your Boundaries; 37 How to Win Friends & Influence People; 38 Stop Walking on Eggshells |
| prop_books_decisions | slot_cat_decisions | 39 Quit; 40 Poor Charlie’s Almanack; 41 The Misbehavior of Markets; 42 Antifragile; 43 The Black Swan; 44 Algorithms to Live By; 45 Framers; 46 Think Again; 47 Calling Bullshit; 48 Thinking, Fast and Slow; 49 The Book of Why |
| prop_books_craft | slot_cat_craft | 50 The Pragmatic Programmer; 51 Clean Code; 52 Deep Work; 53 Atomic Habits; 54 Ultralearning |

**The five named titles.** The round-1 brief asked for *The Order of Time*, *Gödel, Escher, Bach*, *The Feynman
Lectures on Physics*, *Being You* and *The Book of Why*. The round-3 rule (BUILD.md, "Bücherstand categories")
makes categories.json the only source of titles and says the invented titles go. Three of those five are not
in Mac's list, so they are gone. *The Order of Time* (08) and *The Book of Why* (49) are on their shelves and
legible in `prop_books_physics_hero.jpg` and `prop_books_decisions_hero.jpg`.

### 2. Judges' fixes from round 2

| fix | what I did | where to look |
|---|---|---|
| Foam spill reads as a rigid peg | `goods.beer_fill`: the tube and bead are gone. A spill is now a thin, flat sheet that hugs the outside of the glass 1 mm off the wall. It is widest (12 mm) at the lip, tapers to nothing about 3 cm down, has a soft wavy edge and a slightly proud middle, and is a cream colour. | `prop_bier_counter_hero.jpg` |
| Wet-edge band reads as a gold metal rim or tan collar | The crown now stays inside the glass's inner wall all the way up and domes from there. Round 2 swelled it out to the outer diameter, which caused the collar. The wet-edge texture (`atlas_goods.g_foam`) is paler and matte-satin (roughness 0.48–0.68, was 0.22). The foam's subsurface weight is 0.15 (was 0.35), which had greyed the thin shell. Pass 2: the band of foam seen through the glass now takes a strip of the dry crown texture (fine pale bubbles), not the wet strip, whose lacing still read as a tan collar. The other cause was the preview itself: Cycles stops shadow rays at transmission glass, so beer and foam were lit only by noisy caustics and rendered dark. `vstage.glass_no_shadow()` now turns off shadow casting for meshes with transmission glass, in the previews only. Thin glass passes nearly all light, and the browser's glass casts no shadow either. The beer now reads golden and the band reads as cream. | same |
| Coal bed: glossy orange facets, white ash plate | `atlas_goods.g_coal` / `coal_emit` (now 512 px): matte black char with a faint wood grain. Emission sits only in thin cracks, with an orange-yellow core fading to deep red, brightness varying in patches, plus a few small dull ember spots. The faces between cracks do not glow. `coal_glow`: roughness 1.0, metallic 0, specular 0.2. Lumps (`set_wurst.irregular`) get their own stretch, broad lumps and one or two flat broken faces. The ash ring, the flat ash flakes and the ash pan use the mottled grey ash half of the coal map, not flat pale grey. | `prop_wurst_counter_hero.jpg` |
| Raw sausages look like Weißwurst; not clickable | Raw-pork pink-beige `#c89d90` (satin). The first round-3 try, `#c99c8e`, went salmon like a hot dog in the warm light. All eight are now `act_sausage_16..23`: base pivot, `turn_axis`, `raw: true` and items.json entries "Raw Bratwurst, ready for the grill". Lite has all eight too (it had three static ones). Pass 2 fixed a parity bug: their jitter came from a shared random stream that runs differently in lite, so lite placed them up to 1.2 cm away. They now use their own seeded generator, and check_props' act_ parity passes. | same; items.json |
| Lite Bierstand foam columns about 65 cm tall | Rebuilt. New `blender/props/foam_check.mjs` decodes both glbs as the browser does (meshopt, quantised node transforms) and applies the engine's own `foamFits` rule. Result: 9 glasses in each file, tallest head 6.1 cm in full and in lite. check_props runs it and fails if any head is too tall. | `node blender/props/foam_check.mjs` |
| Optional: Kartoffelpuffer read as tarts | `set_deco.pancake`: a domed disc thinning from 8.5 mm to a 1.5–3 mm ragged edge with stray potato strands. The texture is mapped flat across it. `g_puffer` adds uneven browning, near-black strand tips and oily gloss. | `deco_puffer.jpg` |
| Re-render Glühwein previews from the shipped glb | All round-3 previews are rendered from the glbs built in this round. | `prop_gluehwein_*` |

### 3. Market owner's answers

- The reading lamp's bulb now uses the emissive material **`bulb_warm`** (it was `lamp_glow`). The counter set
  has no `light_` empty.
- 2048 px atlases kept. Lite files use 512 px wide versions.

### 4. For the engineer: turning sausages

**turnSausages should rotate each sausage about its `turn_axis`, not about the node origin.** Every
`act_sausage_<n>` has its origin at its base, the middle of its underside where it rests on the grate. Its
long axis is the node's local X, **12.5 mm above the origin** (Blender Z / three.js Y). items.json gives this
on every sausage as `turn_axis: {offset_blender_z: 0.0125, offset_threejs_y: 0.0125, axis: "node X"}`.
Rotating the node itself about X would roll the sausage around its bottom edge and lift it off the grate. Use
translate(0, +0.0125, 0) · rotateX(angle) · translate(0, -0.0125, 0) in the node's local frame, or rotate the
child mesh about that line. The grilled ones (`act_sausage_0..9`) are children of `act_grill_swing`.
`act_sausage_10..15` keep warm in the steel tray, and the raw ones (`act_sausage_16..23`, `raw: true`) wait in
the tray next to it.

## Previews (review/round-3/vendor/)

Every preview here was rendered in round 3 from the glb that ships (1280 × 720, 48 samples, CPU). All counter,
shelf and deco shots stand on the generic plain stage (`vstage.env_counter`). The six category sets stand on a
stand-in bay built from the same `buecher_sections.json` boards (`vstage.env_section`), so the books stand
where the carpenter's boards will be. The carpenter's round-3 `stall_buecher.glb` (exported
at 03:02) carries the matching `slot_cat_` empties (his `buecher_sections.py --check` agrees with the json),
and his `stall_buecher_preview.jpg` shows these six sets standing in the real stall. check_props' seat check
runs every set against the real stall glbs (see the table below).

All at 1280 × 720, 48 samples, Cycles on CPU, rendered on 4 October. Pass 2 is the run after the machine
restarted (05:30 onward UTC).

| file | from | shows |
|---|---|---|
| `prop_books_physics_hero.jpg` | pass 2 | Physik & Kosmos, top board: *The Order of Time* (Rovelli) among Carroll, Hertog and Strogatz |
| `prop_books_decisions_hero.jpg` | pass 2 | Risiko & Entscheidungen, the cart's upper tier: *The Book of Why*, *Thinking, Fast and Slow*, *Calling Bullshit* and the rest |
| `prop_books_lives_hero.jpg` | pass 2 | Lebensgeschichten, the cart's upper tier |
| `prop_books_mind_hero.jpg` | pass 2 | Geist & Körper, top board |
| `prop_books_people_hero.jpg` | pass 2 | Menschen & Gespräche, top board |
| `prop_books_craft_hero.jpg` | pass 2 | Handwerk & Gewohnheit, top board |
| `prop_books_physics.jpg` | pass 1, 03:01 | both boards of the physics bay (wide; the set's geometry did not change in pass 2) |
| `prop_books_counter_hero.jpg` | pass 2 | guest book, banker's lamp with its `bulb_warm` bulb, easel copy, price cards, bookmark tray |
| `prop_books_counter.jpg` | pass 1, 02:49 | the whole counter (wide). Pass 2 only raised the easel legs by about 3 mm |
| `prop_books_shelf_1.jpg`, `prop_books_shelf_2.jpg` | pass 1, 02:36 / 02:43 | the untitled secondhand stock on the back shelves (wide) |
| `prop_bier_counter_hero.jpg` | pass 2 | tap handles, cream foam heads with flat spills, golden beer (glass casts no shadow in the preview) |
| `prop_bier_back_hero.jpg`, `prop_bier_shelf_hero.jpg` | pass 2 | barrels and chalkboard; clean glasses |
| `prop_wurst_counter_hero.jpg` | pass 2 | ember cracks in a dark char bed, grey ash, charred sausages on the grate, warming tray, raw tray |
| `prop_gluehwein_counter_hero.jpg`, `prop_gluehwein_shelf_hero.jpg`, `prop_gluehwein_wine_hero.jpg` | pass 2 | copper kettle and mugs; bottles, spices, oranges; wine labels |
| `deco_puffer.jpg` | pass 2 | Kartoffelpuffer with ragged, lacy edges |
| `deco_goods_contact_sheet.jpg` | pass 2 | all nine deco frames. Eight frames are from round 2 (sets unchanged); the Puffer frame is new |

## Budgets

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->
<!-- check_props:end -->

## What I would improve next

- Stage the six category sets in the carpenter's new `stall_buecher.glb` as soon as it is exported (`--shots
  stall`), and run the seat check against its boards.
- Give the cloth-bound secondhand copies a little more individual wear: a faded spine top or a sticker.
  Consider a leaning book where a bookend leaves a gap.
- Lite ratio warnings that are still open (see the table).

## Contract notes and open issues

- **The five named titles.** Three of the round-1 five (*Gödel, Escher, Bach*, *The Feynman Lectures on
  Physics*, *Being You*) are not in Mac's 55, so under the round-3 rule they are gone. A judge checking "the five
  named titles legible on spines" will find only *The Order of Time* and *The Book of Why*. If Mac wants the
  other three, the writer adds them to categories.json and one rebuild puts them on a shelf.
- **Feynman spine title.** "Surely You're Joking, Mr. Feynman!" and "What Do You Care What Other People
  Think?" are long; their spines use two lines in a smaller face. They read in a close-up, but less boldly
  than the short titles.
- **Wide shots of five category sets** (mind, people, decisions, lives, craft) are not rendered; the heroes
  frame each top board, and the carpenter's `stall_buecher_preview.jpg` shows all six sets in the stall.
  The heroes do not show the lower boards.
- **Beer colour.** Now that light reaches the beer in the preview, it reads orange-gold and a little opaque.
  The glb's beer material is unchanged (transmission 0.65 on `beer`). A slightly clearer, more yellow Helles
  would be a one-line change in `goods.beer_fill`.
- **Lite ratios (WARN, not FAIL):** Bier back 42 %, Books counter 42 %, Mandeln 43 %, Spielzeug 42 %,
  Schmuck 43 %, Käse 39 %, Maroni 40 %. They are mostly boxes and low-segment lathes that lite cannot cut further.
- **Headroom.** Bierstand and Bratwurst are the tightest section stalls (see the budget table). The
  Bücherstand, with the six category sets, is well inside its 80k / 4 MB.
- **Glass in lite** uses alpha blending and the same material names. The site's lite path must not expect
  KHR_materials_transmission. Foam subsurface shows only in Cycles; the glb carries sheen.
- **Seat check limits.** `seat_check.mjs` flags props cutting into the stall and objects buried under a
  stall top. It does not flag a prop floating above a surface.
- **Contract:** nothing in my sets breaks BUILD.md. The counter set has no `light_` empty, and the lamp bulb is
  `bulb_warm`. The 2048 px atlases are within the stalls' file budgets (see the table), and lite uses 512 px.
- The stray `/books_deco.log` from round 2 is outside the repo. Only the market owner can remove it.

