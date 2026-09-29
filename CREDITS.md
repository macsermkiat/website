# Credits

Third-party assets used in the site, with source and licence.

## Carpenter (stalls, blender/lib)

All wood, paint and iron textures are procedural (Blender shader nodes baked by `blender/lib/nmlib/mats.py`); no third-party images or models are used. The only third-party assets are fonts, bundled in `blender/lib/fonts/` and turned into 3D sign lettering inside the stall models:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturMaguntia | Fraktur sign (Christbaumschmuck) | https://github.com/google/fonts/tree/main/ofl/unifrakturmaguntia | SIL Open Font License 1.1 |
| UnifrakturCook | Glühwein, Bier vom Fass, Lebkuchen, Käse, Kartoffelpuffer signs | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| IM Fell English (IM Fell types, digitised by Igino Marini) | Bücher, Kerzen, Crêpes signs | https://github.com/google/fonts/tree/main/ofl/imfellenglish and .../imfellenglishsc | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | Bratwurst, Gebrannte Mandeln, Holzspielzeug, Heiße Maroni signs; contact-sheet labels | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |

## Engineer (site/)

The engine's stand-in models, textures and sounds are made in code; no third-party images, models or sound files are added. Libraries and fonts shipped with the site:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| three.js (incl. GLTFLoader, OrbitControls, post-processing passes, meshopt decoder) | 3D engine | https://github.com/mrdoob/three.js | MIT |
| Alegreya SC and Alegreya Sans (Huerta Tipográfica), via Fontsource | Page and panel type, stand-in signs | https://github.com/huertatipografica/Alegreya, https://fontsource.org | SIL Open Font License 1.1 |
| FluidR3 GM soundfont samples by Frank Wen (piano, bass, sax) | Fallback generative band only, emitted from `prototype/samples.json` | https://github.com/gleitz/midi-js-soundfonts | CC BY 3.0 per that repo's README (the prototype footer said MIT; to confirm) |
| Tone.js drum samples | Fallback generative band only | https://github.com/Tonejs/audio | MIT |
| Vite, marked, yaml (build time only, not shipped) | Build, content from `content/*.md` | https://vitejs.dev, https://marked.js.org, https://eemeli.org/yaml | MIT, MIT, ISC |

## Architect (square, town, tree, layout)

All architect textures (cobbles, setts, granite, plaster, timber, roof tiles, slate, sandstone, painted wood, bark, fir needles and the window atlas) are generated procedurally in numpy by `blender/lib/architect_tex.py`; no third-party images or models are used. The only third-party assets are two fonts from the carpenter's bundle in `blender/lib/fonts/`, turned into 3D shop-sign lettering in `town.glb`:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturCook | Fraktur shop signs (Bäckerei, Weinstube, Gasthaus, Metzgerei, Konditorei, Kaffeehaus) | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | the other shop signs | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |

## Music writer (music/, site/public/audio/)

"Lanterns After Closing", the bandstand ballad, is an original composition written for this site (melody, changes, solos and arrangement in `music/score/ballad.py`). The recording is rendered offline from these freely licensed sample libraries; the sample files themselves are not shipped, only the rendered stems in `site/public/audio/`. The room reverb, the brush sweeps and the breath layer of the tenor are synthesised in code.

| Asset | Used for | Source | Licence |
|---|---|---|---|
| Salamander Grand Piano V3 by Alexander Holm (SFZ/FLAC edition by sfzinstruments) | Piano | https://github.com/sfzinstruments/SalamanderGrandPiano (original: https://archive.org/details/SalamanderGrandPianoV3) | CC BY 3.0 |
| Meatbass by Karoryfer Lecolds (1958 Otto Rubner double bass, played by Drogomir Smolken, recorded by Ludwik Zamenhof), pizzicato | Double bass | https://github.com/sfzinstruments/karoryfer.meatbass | CC0 1.0 |
| Virtuosity Drums by Versilian Studios (house kit at Virtuosity Musical Instruments, Boston, played by Austin McMahon), overhead, room, kick and snare mics | Snare response and soft snare hits under the brushes, feathered bass drum, hi-hat foot, ride | https://github.com/sfzinstruments/virtuosity_drums | CC0 1.0 |
| Musyng Kite soundfont, tenor sax program, as rendered to per-note files by gleitz/midi-js-soundfonts | Tenor sax in the shipped stems (sample layer; vibrato taken out, heavily reshaped) | https://github.com/gleitz/midi-js-soundfonts (MusyngKite/tenor_sax-ogg.js) | CC BY-SA 3.0 per that repo's README (the upstream synthfont.com page could not be reached from the build machine to confirm) |
| FluidR3 GM soundfont by Frank Wen, tenor sax program, as rendered to per-note files by gleitz/midi-js-soundfonts | Tenor sax in the A/B files `music/out/ab/head_fluidr3*.mp3` (not shipped); the alternative bank (`render.py --sax-bank fluidr3`) | https://github.com/gleitz/midi-js-soundfonts (FluidR3_GM/tenor_sax-ogg.js) | CC BY 3.0 per that repo's README (the original FluidR3_GM.sf2 is distributed under the MIT licence) |

**Share-alike.** Because the shipped tenor is built from the CC BY-SA 3.0 Musyng Kite samples, the stems that contain it (`ballad-sax.mp3`, `ballad-room.mp3` and `ballad-mix.mp3`) are adaptations and must be offered under CC BY-SA 3.0, with this credit. The composition itself (the notes in `music/score/`) is not affected. The piano stem needs the Salamander credit; the bass and drum stems come from CC0 sources. `manifest.json` carries the same information under `license`. If Mac prefers no share-alike, re-render with `--sax-bank fluidr3` and everything becomes attribution-only (CC BY).

Attribution line for the site's credits page: *"Lanterns After Closing" (recording CC BY-SA 3.0). Piano: Salamander Grand Piano by Alexander Holm (CC BY 3.0). Tenor sax: Musyng Kite soundfont via gleitz/midi-js-soundfonts (CC BY-SA 3.0), reshaped. Bass: Karoryfer Meatbass (CC0). Drums: Virtuosity Drums by Versilian Studios (CC0).*

## Lighting designer (site/src/lighting/)

The sky, stars, moon, clouds, snow, environment map and grain are all generated in shaders and code; no third-party images, HDRIs, textures or models are used. Code the module builds on:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| three.js AgX tone-mapping constants and post-processing passes (`EffectComposer`, `RenderPass`, `UnrealBloomPass`, `Pass`) | `grade.js` re-implements three's AgX (itself ported from Filament / Blender) to add the Punchy look; bloom and composer are used as shipped | https://github.com/mrdoob/three.js | MIT |
| Filament's AgX implementation (via three.js) | AgX matrices and curve | https://github.com/google/filament/pull/7236 | Apache 2.0 |
| Black-body colour approximation by Tanner Helland (algorithm only, re-implemented) | `kelvinRGB()` for the warm light colour | https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html | Published algorithm, no code copied |

## Ride builder (Riesenrad, Karussell, bandstand, instruments: blender/rides/)

All ride textures are procedural: the painted-steel kit `rsteel` is baked from Blender shader nodes in `blender/rides/rcommon.py`, and the wood and paint kits come from the carpenter's `nmlib`. No third-party images, models or scans are used. The only third-party assets are two fonts from the carpenter's bundle in `blender/lib/fonts/`, turned into 3D lettering inside the models:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturCook | "Riesenrad" entrance sign (ferris.glb), "Karussell" on the rounding board (carousel.glb) | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | "Kasse" sign on the Riesenrad ticket booth (ferris.glb) | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |

## Vendor (goods and props: blender/props/, site/public/models/prop_*)

Every prop is modelled in code (`blender/props/*.py`) and every texture in the vendor atlas (`prop_tex_atlas_*.webp`: book spines and cloth, mug glazes and prints, bottle and jar labels, the chalkboard, copper, brass, steel, iron, wood, bread, sausage skin, coals, Lebkuchen icing, cheese, crêpes, chestnuts and so on) is drawn procedurally with numpy and Pillow by `blender/props/vendor_atlas.py`. No third-party images or models are used. The book titles on the spines are the real titles of the books in the reading list and of other well-known books, set in the fonts below; no cover artwork is reproduced. The text on the open book is the opening of Goethe's *Faust* (1808, public domain).

The only third-party assets are fonts, used to draw lettering into the atlas (bundled in `blender/props/fonts/` and the carpenter's `blender/lib/fonts/`):

| Asset | Used for | Source | Licence |
|---|---|---|---|
| Oswald (The Oswald Project Authors) | Spines: The Order of Time, paperbacks | https://github.com/google/fonts/tree/main/ofl/oswald | SIL Open Font License 1.1 |
| EB Garamond (The EB Garamond Project Authors) | Spines, labels, the open book's text | https://github.com/google/fonts/tree/main/ofl/ebgaramond | SIL Open Font License 1.1 |
| Playfair Display (The Playfair Display Project Authors) | Spine: Gödel, Escher, Bach; paperbacks; label | https://github.com/google/fonts/tree/main/ofl/playfairdisplay | SIL Open Font License 1.1 |
| Cinzel (The Cinzel Project Authors) | Spines: The Feynman Lectures on Physics, cloth books; rum label | https://github.com/google/fonts/tree/main/ofl/cinzel | SIL Open Font License 1.1 |
| Bebas Neue (Dharma Type) | Spine: Being You; paperbacks | https://github.com/google/fonts/tree/main/ofl/bebasneue | SIL Open Font License 1.1 |
| Josefin Sans (The Josefin Sans Project Authors) | Spine: The Book of Why; paperbacks | https://github.com/google/fonts/tree/main/ofl/josefinsans | SIL Open Font License 1.1 |
| Libre Baskerville (The Libre Baskerville Project Authors) | Cloth spines, a bottle label | https://github.com/google/fonts/tree/main/ofl/librebaskerville | SIL Open Font License 1.1 |
| Caveat (The Caveat Project Authors) | Chalk handwriting on the beer price board | https://github.com/google/fonts/tree/main/ofl/caveat | SIL Open Font License 1.1 |
| Pacifico (The Pacifico Project Authors) | Glühwein mug lettering, Lebkuchen icing, Amaretto label | https://github.com/google/fonts/tree/main/ofl/pacifico | SIL Open Font License 1.1 |
| UnifrakturCook, IM Fell English, Alegreya SC (carpenter's bundle, credited above) | Mug and coaster Fraktur, spice-jar labels, paper-bag print | see Carpenter | SIL Open Font License 1.1 |

## Organizer (people, crowd: blender/people/, site/public/models/people_*, site/src/crowd.json)

Every figure, including bodies, faces, hair, coats, scarves, hats, gloves, boots, aprons, bags and the Glühwein mug, is modelled in code (`blender/people/figures.py`). The skeleton, skin weights and every clip (walk, idle, chat, drink, laugh, sit, the band's play and rest, the vendors' serve and wipe) are built and keyed procedurally (`rig.py`, `anims.py`). No motion capture, scans, third-party models or third-party images are used. The two knit and wool normal maps (`people_knit_normal`, `people_wool_normal`) are drawn in numpy by `blender/people/pmats.py`. The crowd layout in `site/src/crowd.json` is generated from the architect's `layout.json` by `crowd_plan.py`.

Tools only (nothing of theirs is shipped by this role): Blender 4.2 `bpy` (GPL, used as a build tool, so its output is not covered), glTF-Transform and meshoptimizer via the carpenter's `blender/lib/optimize.mjs` (MIT), and three.js (MIT, credited above) for checking the models in a browser.
