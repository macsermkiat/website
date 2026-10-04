# Vendor, round 4 notes

A short polish round. All goods are still modelled in code under `blender/props/` and textured from the two
procedural atlases. I added no third-party assets, so CREDITS.md is unchanged. The atlases were not
repacked, so the sets I did not touch keep working with the shared `prop_tex_*` textures.

Rebuild and check (same as round 3, plus one new script):

```
blender/props/run_build.sh <log-tag> [--only a,b] [--no-render] [--no-lite] [--shots wide,hero] [--render-only a,b]
python3 blender/props/check_props.py [--notes]        # contract checks; exit 1 on FAIL
node blender/props/shoot_items.mjs --dist <scratch>/dist --build --out <dir> \
     --shots bier:act_glass_0:three_bier_pints.jpg,deco-lebkuchen:act_heart_4:three_lebkuchen_tag.jpg:click
```

`build_props.py` now defaults to the contract's review size (1280 × 720, 48 samples). In round 3 it defaulted
to 1920 × 1080 at 128 samples. `shoot_items.mjs` (new) takes check shots in the real engine. It builds the
site into a scratch folder, serves it with `vite preview`, opens a place, flies to an item and saves a JPEG.
It writes nothing into `site/`. With `vite dev` the page reloaded whenever a glb was rebuilt mid-run.

## Round 4 priorities

### 1. Clear golden beer with a foam head (`goods.beer_fill`, `vlib.material("beer")`)

**Why the pints looked empty in the browser.** The beer was transmissive (`KHR_materials_transmission`
0.65) and so was the glass around it. three.js draws only *opaque* objects into the buffer that a
transmissive surface samples. So the glass wall showed the counter behind the beer, never the beer.
That is why the market judges saw empty glasses in `item_bier_prost.jpg`. The fix:

- `vendor_beer` is now **opaque in the glb** (no transmission). The glass stays transmissive and now shows
  the beer behind it.
- **No clear coat on the beer in the glb.** My first build gave the beer a coat for the wet shine. In three.js
  a `KHR_materials_clearcoat` layer adds a second, untinted mirror of the sky over the beer and pulls it
  toward white, so I took it out. The coat is now only in the Cycles previews.
- **A darker, fainter lite glass for the pints.** In the engine the beer at first read pale grey-beige. Two
  tests on the full glb (emissive beer, duller glass) changed nothing, because the market now opens each
  stall on its **lite** models (`engine/stream.js`, new this round) and grafts the full ones in later. In
  lite the eye looks at the beer through two alpha walls of the glass (outer and inner surface). At 28 % each,
  a white-lit diffuse shell veiled about half the beer. The counter's full glasses now wear their own
  material, `vendor_glass_pint`. In lite it is a dark grey shell (base 0.2) at 15 %: its highlights stay and
  the beer keeps its colour. In full it is the same transmissive glass as `vendor_glass`. Bottles, jars and
  the shelf's clean glasses keep `vendor_glass`. **The name must not contain "beer", "lager" or "ale"**:
  `beer.js` finds a glass's beer by `/beer|lager|ale/` in the material name. My first try, named
  `vendor_glass_beer`, made the engine treat the glass as the beer and hide it.
- The beer column carries a **per-vertex colour gradient**: deeper amber at the foot (more beer to look
  through), the named colour in the middle, and a brighter, yellower gold just under the head. No white is
  mixed into the light end. In the first try I mixed some in, and under the warm light and tone mapping the
  beer turned peach, like orange juice.
- **Helles** is now `#e6a012`, a saturated gold. Round 3 used orange `#e0901c`. Dunkles, Weißbier and Radler
  keep their colours and get the same gradient.
- The foam heads are unchanged from round 3: a separate `foam_<n>` mesh on each glass, under the engine's
  `foamFits` limit (`foam_check.mjs`: tallest head 6.1 cm, full and lite).
- **Cycles preview only** (`vstage.beer_preview`): the beer gets Transmission 0.6 and a clear coat, so the
  hero shows the lit golden body with some depth, a wet shine, and the refracted counter behind it. I tried
  full transmission first (`Transmission 1.0`): it went dark olive, because the stall is lit from the front and the column refracts
  the unlit wall. Nothing exported changes, because the previews render after the glbs are written.

I tested the alternatives on the full models in the real engine (before streaming arrived) before picking
this one. With a transmissive beer and alpha-blended glass, the beer almost vanished (pink tint). With opaque
beer and alpha-blended glass at 18 %, the beer went pale peach under the white glass veil. Opaque beer behind
the transmissive glass read the most golden.

Note for the engineer: the engine empties every glass but the first two Maß at start (`beer.js`, "two full
Maß and the rest clean and empty"). So in the browser only `act_glass_0` and `act_glass_1` show their beer
until a visitor pours. The close-up is framed on `act_glass_0`. There are two engine shots: the default
market, which streams the lite Bierstand in first, and `?stream=0` with the full models.

### 2. Deco goods are now act_ nodes with `detail` fields

Every deco set now has clickable items, 101 in all, so `site/src/actions/items/deco.js` no longer needs its
code-made stand-in hearts: it builds them only when a Lebkuchen set has no act_ nodes. In items.json every
item has `kind: "deco"`, a display `name`, a `pivot`, and a `detail` line for the engine's paper tag. Some
also have extras, such as `icing` and `size_cm` on the hearts and `colour` and `lit` on the candles.

| set | act_ nodes | pivot | what the tag says (examples) |
|---|---|---|---|
| prop_deco_lebkuchen | `act_heart_0..11` hanging from the rod, `act_heart_12..16` leaning on the display board | hang: the ribbon's knot on the rod (0..11); base: the heart's lowest point on the board's rail (12..16) | "“Frohe Weihnachten” (Merry Christmas), white lettering in a yellow piped border. About 17 cm across. It hangs on a ribbon…" (the icing text matches the texture on that heart face) |
| prop_deco_mandeln | `act_cone_0..9` (the rack of paper cones) | base (cone tip on the counter) | gebrannte Mandeln, Zimtmandeln, Cashews, Schokomandeln, Erdnüsse; 100 g 3,50 € / 200 g 6 € |
| prop_deco_kerzen | `act_candle_0..11` (every third column of the risers) | base | "Plum pillar candle, 14 cm tall, 5 cm across. Hand-dipped…"; beeswax, block, lit |
| prop_deco_spielzeug | `act_nutcracker_0..2`, `act_train_0`, `act_top_0..2`, `act_rockinghorse_0` | base | the three nutcrackers' uniforms and sizes, the train, the tops' colours |
| prop_deco_schmuck | `act_bauble_0..11` hanging (baubles, glass icicles, straw stars), `act_bauble_12..14` lying on the counter | hang (0..11); base (12..14) | "A mouth-blown glass bauble, deep red, mirror-silvered inside… made in Lauscha…" |
| prop_deco_kaese | `act_cheese_0..12` | base (each stacked wheel on its own underside) | Allgäuer Bergkäse (the cut wheel), Butterkäse, Tilsiter, Edamer, Weißlacker, Romadur, Limburger, mini Goudas, Räucherkäse |
| prop_deco_crepes | `act_crepe_0..3`, `act_jar_0..1`, `act_shaker_0..1` | base | the four folded crêpes' fillings and prices, nut-nougat cream, apple purée, sugar and cinnamon |
| prop_deco_maroni | `act_bag_0..3`, `act_scale_0` | base | "A kraft bag printed “Heiße Maroni”… about 200 g for 4 €", the shop scale |
| prop_deco_puffer | `act_puffer_0..8` (the tray), `act_plate_0`, `act_jar_2..4` | base | Kartoffelpuffer, the served plate with applesauce, jars of applesauce |

- **Pivots.** A hanging item's origin is the ribbon's knot on the rod, so the engine's click swing turns it
  about the knot. Its ribbon belongs to the item and swings with it. A standing item's origin is the point
  it rests on. check_props has two new deco checks. A "base" item's geometry must start within 4 mm of its
  origin. A "hang" item must have nothing above its origin but the knot (at most 12 mm), with the item below
  it. Every deco item must also have a detail line. All of them pass.
- **Lite parity.** Every item is in the lite glb too, at the same place and within 1 cm of the same bounds.
  Positions and jitter come from each item's own seeded generator (`set_deco.irng`), not from the shared
  stream, which runs differently in lite. Round lite items keep at least 6 sides (cones, candles, baubles,
  jars) or 12 (cheese wheels, the Puffer plate), so their lite bounds match. Lite now always has the three
  nutcrackers, the three train cars and all three tops, the ten cones and the nine Puffer.
- **Small fixes on the way.** The rocking horse floated 14 mm above the counter. Its rockers now touch it.
  The crêpe and Puffer jars wore the spice shelf's "Orangenschale" label, which the new tags would
  contradict. They now have plain kraft labels.
- **Full triangles did not grow.** Every deco set has the same count as in round 3, and Kartoffelpuffer is
  lower (4408, was 4600). Its pancakes now have 14 sides in both builds. This gives the tightest deco stall
  more room under 20k.

### 3. `prop_books_counter.jpg` re-rendered wide

It is rendered from this round's glb, with the easel legs fixed in round 3. I also rendered the wide shots
the round-3 judges asked for, of the mind, people and craft category sets.

## Previews (review/round-4/vendor/)

All are Cycles renders at 1280 × 720, 48 samples, CPU, from this round's glbs, except where marked.

| file | shows |
|---|---|
| `prop_bier_counter_hero.jpg` | the pints: golden Helles with cream heads, Dunkles, Weißbier, Radler; tap handles. Rendered before the coat moved from the glb material into `beer_preview`, so the Cycles material is the same as today's preview |
| `three_bier_pints.jpg` | **three.js (the real engine)**, default market (the Bierstand on its lite models, as streaming opens it): the two full Maß of Helles (`act_glass_0`, `act_glass_1`), golden with a deeper amber foot and cream heads; the emptied glasses as faint shells |
| `three_bier_pints_full.jpg` | **three.js**, `?stream=0` (full models, transmissive glass): golden beer with a deeper amber foot and cream heads |
| `three_lebkuchen_tag.jpg` | **three.js**: the Lebkuchen stall with the vendor's own hearts. One was clicked and its paper tag shows the item's `detail` |
| `deco_lebkuchen.jpg`, `deco_mandeln.jpg`, `deco_kerzen.jpg` | the three deco frames whose look changed (the hearts as items, the new nut kinds, the re-laid candle risers) |
| `deco_goods_contact_sheet.jpg` | all nine deco frames. Lebkuchen, Mandeln and Kerzen are new. The other six frames are from rounds 2 and 3: those sets look the same, because their goods were only split into nodes |
| `prop_books_counter.jpg` | the whole books counter (wide) |
| `prop_books_mind.jpg`, `prop_books_people.jpg`, `prop_books_craft.jpg` | wide shots of the three category sets that had only close-ups in round 3 |

## Budgets

<!-- check_props:begin (generated by blender/props/check_props.py --notes; do not edit by hand) -->

Triangles are after optimisation. kB is the glb alone (full / lite), which embeds its own AO map; the shared atlases are counted once below. Size is the set's bounding box in metres.

| set | stall | slot | tris | lite tris (ratio) | kB full / lite | size x × y × z m |
|---|---|---|---|---|---|---|
| prop_gluehwein_counter | gluehwein | slot_counter | 7450 | 2610 (35%) | 183 / 99 | 1.99 × 0.47 × 0.57 |
| prop_gluehwein_shelf | gluehwein | slot_shelf_1 | 6254 | 2051 (33%) | 164 / 82 | 2.29 × 0.24 × 0.34 |
| prop_gluehwein_wine | gluehwein | slot_shelf_2 | 5268 | 1856 (35%) | 111 / 66 | 2.33 × 0.23 × 0.42 |
| prop_bier_counter | bierstand | slot_counter | 9238 | 3262 (35%) | 176 / 104 | 2.01 × 0.39 × 0.63 |
| prop_bier_back | bierstand | slot_shelf_1 | 4356 | 1812 (42%) | 102 / 53 | 2.33 × 0.25 × 0.34 |
| prop_bier_shelf | bierstand | slot_shelf_2 | 3746 | 1380 (37%) | 58 / 33 | 1.91 × 0.23 × 0.26 |
| prop_wurst_counter | bratwurst | slot_counter | 20946 | 6108 (29%) | 453 / 216 | 3.42 × 0.48 × 0.64 |
| prop_books_shelf_1 | buecherstand | slot_shelf_1 | 1624 | 464 (29%) | 59 / 24 | 1.86 × 0.22 × 0.28 |
| prop_books_shelf_2 | buecherstand | slot_shelf_2 | 1588 | 440 (28%) | 58 / 23 | 1.86 × 0.19 × 0.27 |
| prop_books_counter | buecherstand | slot_counter | 2144 | 900 (42%) | 66 / 38 | 2.09 × 0.45 × 0.40 |
| prop_books_physics | buecherstand | slot_cat_physics | 982 | 296 (30%) | 64 / 38 | 0.46 × 0.20 × 0.66 |
| prop_books_lives | buecherstand | slot_cat_lives | 814 | 264 (32%) | 52 / 30 | 0.40 × 0.44 × 0.55 |
| prop_books_mind | buecherstand | slot_cat_mind | 928 | 280 (30%) | 60 / 35 | 0.42 × 0.21 × 0.66 |
| prop_books_people | buecherstand | slot_cat_people | 1084 | 344 (32%) | 73 / 46 | 0.52 × 0.20 × 0.63 |
| prop_books_decisions | buecherstand | slot_cat_decisions | 994 | 304 (31%) | 65 / 39 | 0.49 × 0.45 × 0.58 |
| prop_books_craft | buecherstand | slot_cat_craft | 748 | 240 (32%) | 47 / 27 | 0.35 × 0.21 × 0.66 |
| prop_deco_lebkuchen | deco-lebkuchen | slot_counter | 5102 | 1870 (37%) | 177 / 100 | 2.20 × 0.45 × 1.15 |
| prop_deco_mandeln | deco-mandeln | slot_counter | 2774 | 1302 (47%) | 122 / 83 | 1.98 × 0.48 × 0.44 |
| prop_deco_kerzen | deco-kerzen | slot_counter | 3790 | 1368 (36%) | 127 / 71 | 2.11 × 0.48 × 1.15 |
| prop_deco_spielzeug | deco-spielzeug | slot_counter | 2836 | 1668 (59%) | 127 / 82 | 2.01 × 0.46 × 0.42 |
| prop_deco_schmuck | deco-schmuck | slot_counter | 2788 | 1344 (48%) | 121 / 79 | 2.16 × 0.39 × 1.15 |
| prop_deco_kaese | deco-kaese | slot_counter | 4556 | 1968 (43%) | 126 / 80 | 2.02 × 0.48 × 0.24 |
| prop_deco_crepes | deco-crepes | slot_counter | 3648 | 1434 (39%) | 106 / 65 | 2.06 × 0.47 × 0.20 |
| prop_deco_maroni | deco-maroni | slot_counter | 4104 | 1656 (40%) | 122 / 62 | 2.18 × 0.47 × 0.26 |
| prop_deco_puffer | deco-kartoffelpuffer | slot_counter | 4408 | 1617 (37%) | 129 / 83 | 2.06 × 0.48 × 0.27 |

All prop glbs together: 2.95 MB full and 1.66 MB lite. Shared textures (`prop_tex_*`): 1.07 MB full and 0.20 MB lite, loaded once for all sets.

Section stalls, the carpenter's current stall glb plus my props (60k triangles and 3 MB with the shared textures the sets use, the Bücherstand 80k and 4 MB; check_props fails under 2k headroom):

| stall | stall tris | + props | total / budget | headroom | MB / budget |
|---|---|---|---|---|---|
| gluehwein | 37858 | 18972 | 56830 / 60k OK | 3170 | 1.90 / 3 |
| bierstand | 39745 | 17340 | 57085 / 60k OK | 2915 | 1.84 / 3 |
| bratwurst | 36402 | 20946 | 57348 / 60k OK | 2652 | 1.86 / 3 |
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

- **Lite ratios.** Lite must keep every clickable item at the same size, so the deco sets with many items
  went up: Spielzeug 59 %, Schmuck 48 %, Mandeln 47 %. I trimmed what is not an item (the cones' inner
  paper, the almond heaps' profile, all but one shaving tree). The three nutcrackers are now in lite as
  well, so Spielzeug stays the highest. These are warnings (target about a third), not failures. Every lite
  deco set stays under 2k triangles.
- **Bier vendor's hat** (round-3 market judges: "fix the Bier vendor's hat so it reads as a hat, not a
  grey blob"). The figures are the organizer's (`blender/people/`), so I did not touch it.
- **Frosted glass in the browser.** In the software-GL shots, the full model's transmissive glass blurs what is
  behind it (the transmission buffer is low-resolution), so the beer reads slightly hazy, not crystal clear.
  It still reads as golden beer with a head. A sharper look would need the engine's transmission settings
  (engineer/lighting). Lite pint glasses are a dark 15 % shell (other lite glass 28 %).
- **Faint clean glasses in lite.** The engine empties every pint but the first two Maß, so on the lite
  models the other seven glasses are only the dark 15 % shell and read faintly (see `three_bier_pints.jpg`).
  If they should read more, raise the lite `glass_pint` alpha to about 0.2. Above that the veil starts to
  grey the beer again.
- **File sizes.** Each deco goods glb grew by about 40–50 kB (Lebkuchen 127 → 177 kB). The items are separate
  nodes, which compress less well together, and each set embeds its own AO map. The largest deco stall with
  its goods is 542 kB (Lebkuchen), under the 1 MB budget. The shared textures are counted once for the whole
  market.
- **Draw calls.** The 101 deco items are separate nodes, and many have two materials. The engine does not
  merge deco items (`pseudo.merge = null` in `deco.js`), so a deco stall now adds about 10–17 nodes. Only one
  or two deco stalls are on screen up close at a time.
- **The six unchanged deco frames** in the contact sheet are renders from rounds 2 and 3. Their sets' goods were split
  into nodes without changing their look. The Puffer pancakes now have 14 sides, not 18, which does not show
  at frame distance.
