# Judges on vendor, round 2 pass 2

## Improve

Failed:
- Close-ups show believable materials: glazed ceramic, copper, glass with foam, charred sausages, worn book cloth: Copper, mugs, books and the grilled sausages are good. In prop_bier_counter_hero.jpg each foam spill is a rigid cream peg standing off the glass, and the wet edge reads as a gold metal band. In the wurst hero the coals are glossy flat orange facets, the ash ring reads as a white plate, and the raw sausages look white, like Weißwurst.

Fixes:
- Beer foam spill (goods.beer_fill): the spill is a round tube with a bead and stands off the glass like a peg. Replace it with a thin, flat run that hugs the glass (about 1 mm off the wall), tapers to nothing and is soft and translucent, or drop it. Also cut the metallic and specular look of the wet-edge band so it reads as wet cream, not a gold rim. Re-render prop_bier_counter_hero.jpg.
- Coal bed close-up (set_wurst.coal_lump, atlas_goods.coal_emit): the coal sides render as flat, glossy orange facets that look like copper boxes. Make the coal base dark char (roughness about 1, not metallic) with emission only in thin cracks and patches, not across whole faces, and give the lumps irregular shapes. Darken the ash ring from a flat white disc (it reads as a plate) to mottled grey ash. Re-render prop_wurst_counter_hero.jpg.
- Raw Bratwurst: change the near-white #dcc4b0 to a raw pork pink-beige so the raw tray no longer looks like Weißwurst. Also make the raw-tray sausages act_ nodes with base pivots and items.json entries, or note in NOTES why they are not clickable.
- Optional: give the Kartoffelpuffer ragged, lacy, golden-brown edges and uneven browning, so they stop reading as tarts.
- Optional: keep working the lite ratio warnings (Bier back 42%, Mandeln 43%, Spielzeug 42%, Schmuck 43%) toward a third, and add wide shots of the Glühwein shelves, the Bier back and shelf, and the two Bücher shelves.
- Market owner: delete /books_deco.log, and answer the two contract questions (whether the reading lamp gets a light_ empty, and whether the 2048 px atlases are acceptable).

## Improve

Failed:
- Close-ups show believable materials: glazed ceramic, copper, glass with foam, charred sausages, worn book cloth: Ceramic mugs, hammered copper kettle, transmission glass, browned striped sausages and worn cloth/leather spines all read well; but in a 2x crop of prop_bier_counter_hero.jpg the foam 'spills' are thin beige rods with a bead that read as toothpicks hanging over the rim, and the wet-edge band sits at the glass's outer wall (foam bbox x-extent equals the glass's) so it reads as a tan collar rather than foam inside the rim.

Fixes:
- Beer foam spill and rim: replace the thin rod-and-bead spill tube with a short, wide dribble sheet that hugs the outside of the glass (or drop the spills), and keep the wet-edge band inside or flush with the rim so the head no longer reads as a tan collar at the glass's outer diameter (foam bbox currently equals the glass's x-extent). Re-render prop_bier_counter_hero.jpg from the rebuilt glb.
- Raw sausage tray: make goods.sausage(raw=True) pinker (the #dcc4b0 satin reads as white Weißwurst in the warm key light), since the hero shot is the browser's visual target.
- Coal bed polish: the ember faces are a flat saturated orange in the hero crop; vary the emission across each lump (darker red cores, brighter cracks) so they read less like orange plastic facets.
- Re-render prop_gluehwein_counter.jpg and _hero.jpg from the Oct 4 glb so every preview on disk comes from the file that ships (the full geometry is unchanged, but the atlas was repainted).
- Optional: bring the lite ratios of Bier back (42 %), Mandeln (43 %), Spielzeug (42 %) and Schmuck (43 %) toward a third; they are warnings, not failures.
- Market owner actions, not vendor: delete /books_deco.log (still present, 1.46 MB) and answer the two contract questions (reading-lamp light_ empty; 2048 px goods atlas and 2048x3584 books atlas).

