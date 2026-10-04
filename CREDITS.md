# Credits

Third-party assets used in the site, with source and licence.

## Carpenter (stalls, blender/lib)

All wood, paint and iron textures are procedural (Blender shader nodes baked by `blender/lib/nmlib/mats.py`); no third-party images or models are used. The only third-party assets are fonts, bundled in `blender/lib/fonts/` and turned into 3D sign lettering inside the stall models:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturCook | Glühwein, Bier vom Fass, Lebkuchen, Käse signs | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| IM Fell English Italic (IM Fell types, digitised by Igino Marini) | Bücher, Kerzen, Crêpes signs | https://github.com/google/fonts/tree/main/ofl/imfellenglish | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | Bratwurst, Gebrannte Mandeln, Holzspielzeug, Christbaumschmuck, Heiße Maroni, Kartoffelpuffer signs; the six Bücherstand category signs (round 3); contact-sheet labels | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |
| UnifrakturMaguntia, IM Fell English SC | Bundled in `blender/lib/fonts/` as `state.font("fraktur")` and `state.font("fell_sc")` for other builders; no carpenter sign or shipped model uses them | https://github.com/google/fonts/tree/main/ofl/unifrakturmaguntia and .../imfellenglishsc | SIL Open Font License 1.1 |

## Engineer (site/)

The engine's stand-in models, textures and sounds are made in code; no third-party images, models or sound files are added. Libraries and fonts shipped with the site:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| three.js (incl. GLTFLoader, OrbitControls, post-processing passes, meshopt decoder) | 3D engine | https://github.com/mrdoob/three.js | MIT |
| Alegreya SC and Alegreya Sans (Huerta Tipográfica), via Fontsource | Page and panel type, stand-in signs | https://github.com/huertatipografica/Alegreya, https://fontsource.org | SIL Open Font License 1.1 |
| FluidR3 GM soundfont samples by Frank Wen (piano, bass, sax), as rendered by gleitz/midi-js-soundfonts | Fallback generative band only (plays only if the recorded stems cannot), emitted from `prototype/samples.json` | https://github.com/gleitz/midi-js-soundfonts | CC BY 3.0 per that repo's README (the original FluidR3_GM.sf2 is MIT); credited in the footer of both pages either way |
| Tone.js drum samples | Fallback generative band only | https://github.com/Tonejs/audio | MIT |
| Vite, marked, yaml (build time only, not shipped) | Build, content from `content/*.md` | https://vitejs.dev, https://marked.js.org, https://eemeli.org/yaml | MIT, MIT, ISC |

**Music credit on the site.** The recorded band the site plays is the music writer's (see *Music writer* below); the engineer ships no audio of its own. The build reads `site/public/audio/manifest.json` → `license.recording.credit` word for word (currently: Salamander Grand Piano, CC BY 3.0; MTG Solo Saxophones, CC BY 4.0; CC0 bass and drums) and prints it in the footer of `index.html` and `plain.html`, with every Creative Commons licence it names linked to its deed and a link to this file. The FluidR3 line above is added to the same footer for the fallback band. A change of samples by the music writer changes the footer at the next build, with no engine change.

## Architect (square, town, tree, layout)

All architect textures (cobbles, setts, granite, plaster, timber, roof tiles, slate, sandstone, painted wood, bark, fir needles and the window atlas) are generated procedurally in numpy by `blender/lib/architect_tex.py`; no third-party images or models are used. The only third-party assets are two fonts from the carpenter's bundle in `blender/lib/fonts/`, painted into the shop-sign lettering texture (`shop_signs`) in `town.glb`:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturCook | Fraktur shop signs (Bäckerei, Weinstube, Gasthaus, Metzgerei, Konditorei, Kaffeehaus) | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | the other shop signs | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |

## Music writer (music/, site/public/audio/)

"Lanterns After Closing", the bandstand ballad, is an original composition written for this site (melody, changes, solos and arrangement in `music/score/ballad.py`). The recording is rendered offline from these freely licensed sample libraries. The sample files themselves are not shipped, only the rendered stems in `site/public/audio/`. The room reverb and the tenor's breath and air layers are synthesised in code.

| Asset | Used for | Source | Licence |
|---|---|---|---|
| MTG Solo Saxophones, tenor: single notes (soft), breath noises. Recorded by the Music Technology Group, Universitat Pompeu Fabra, published on freesound.org; trimmed and mapped to SFZ by kinwie | Tenor sax in the shipped stems (sample layer, vibrato taken out, reshaped) and the recorded breath intakes before phrases | https://github.com/sfzinstruments/MTG.SoloSax (from https://freesound.org/people/MTG/packs/20251/, 20239, 20247, 20253) | CC BY 4.0 per that repo's LICENSE and README. The upstream freesound.org packs are still unconfirmed: in round 1 pass 5 the build machine's proxy refused freesound.org again (HTTP 403 on the tunnel) and a fetch through the web tool was not approved, so the check needs a machine that can open those four pack pages |
| Salamander Grand Piano V3 by Alexander Holm (SFZ/FLAC edition by sfzinstruments) | Piano | https://github.com/sfzinstruments/SalamanderGrandPiano (original: https://archive.org/details/SalamanderGrandPianoV3) | CC BY 3.0 |
| Meatbass by Karoryfer Lecolds (1958 Otto Rubner double bass, played by Drogomir Smolken, recorded by Ludwik Zamenhof), pizzicato | Double bass | https://github.com/sfzinstruments/karoryfer.meatbass | CC0 1.0 |
| Swirly Drums by Karoryfer Samples (a jazz kit played with brushes): snare stirs, brush hits and digs, hi-hat foot, brushed ride | Brushes: sweeps, taps, hi-hat foot chick, ride, the cymbal swell at the end | https://github.com/sfzinstruments/karoryfer.swirly-drums | CC0 1.0 (the repo's `license` file; changelog 1.104: "License changed to free") |
| Virtuosity Drums by Versilian Studios and Karoryfer Samples (house kit at Virtuosity Musical Instruments, Boston, played by Austin McMahon), kick | Feathered bass drum (and, with `--brushes modelled`, the round-1 modelled brushes in `music/listen/brushes_modelled*.mp3`) | https://github.com/sfzinstruments/virtuosity_drums | CC0 1.0 |
| Musyng Kite soundfont, tenor sax program, as rendered to per-note files by gleitz/midi-js-soundfonts | Only the A/B files `music/listen/head_musyngkite*.mp3` (not shipped on the site). It was the shipped tenor in round 1 pass 3 | https://github.com/gleitz/midi-js-soundfonts (MusyngKite/tenor_sax-ogg.js) | CC BY-SA 3.0 per that repo's README |
| FluidR3 GM soundfont by Frank Wen, tenor sax program, as rendered to per-note files by gleitz/midi-js-soundfonts | Only the A/B files `music/listen/head_fluidr3*.mp3` (not shipped) | https://github.com/gleitz/midi-js-soundfonts (FluidR3_GM/tenor_sax-ogg.js) | CC BY 3.0 per that repo's README (the original FluidR3_GM.sf2 is distributed under the MIT licence) |

**No share-alike on the site.** Since round 1 pass 4 the shipped tenor is the MTG recording (CC BY 4.0), so every file in `site/public/audio/` is attribution-only: the tenor, room and mix files need the MTG and Salamander credits, the piano stem the Salamander credit, and the bass and drum stems come from CC0 sources. `manifest.json` carries the same information under `license`. Share-alike (CC BY-SA 3.0) now applies only to the two listening files `music/listen/head_musyngkite.mp3` and `head_musyngkite_tenor.mp3`, which are review material in the repo and are not served by the site.

Attribution line for the site's credits page: *"Lanterns After Closing". Tenor sax: MTG Solo Saxophones by the Music Technology Group, Universitat Pompeu Fabra (freesound.org), SFZ by kinwie (CC BY 4.0). Piano: Salamander Grand Piano by Alexander Holm (CC BY 3.0). Bass: Karoryfer Meatbass (CC0). Drums: Swirly Drums by Karoryfer Samples and Virtuosity Drums by Versilian Studios and Karoryfer Samples (CC0).*

## Lighting designer (site/src/lighting/)

The sky, stars, moon, clouds, snow, environment map and grain are all generated in shaders and code; no third-party images, HDRIs, textures or models are used. Code the module builds on:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| three.js AgX tone-mapping constants, post-processing passes (`EffectComposer`, `RenderPass`, `UnrealBloomPass`, `Pass`) and shader chunks (patched in `fog.js` and `shading.js`) | `grade.js` re-implements three's AgX (itself ported from Filament / Blender) to add the Punchy look; bloom and composer are used as shipped | https://github.com/mrdoob/three.js | MIT |
| Filament's AgX implementation (via three.js) | AgX matrices and curve | https://github.com/google/filament/pull/7236 | Apache 2.0 |
| Black-body colour approximation by Tanner Helland (algorithm only, re-implemented) | `kelvinRGB()` fallback warm light colour (the default is now the Cycles previews' linear colour) | https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html | Published algorithm, no code copied |
| Roughness widening for lights with a size (Karis, "Real Shading in Unreal Engine 4", SIGGRAPH 2013; idea only, re-implemented as a roughness floor) | `shading.js` light size on direct specular | https://blog.selfshadow.com/publications/s2013-shading-course/ | Published technique, no code copied |

## Ride builder (Riesenrad, Karussell, bandstand, instruments: blender/rides/)

All ride textures are procedural: the painted-steel kit `rsteel` is baked from Blender shader nodes in `blender/rides/rcommon.py`, and the wood and paint kits come from the carpenter's `nmlib`. The posters, the price board (ferris.glb) and the drum rug (bandstand.glb) are drawn in code with Pillow by `blender/rides/art.py`. No third-party images, models or scans are used. The only third-party assets are three fonts from the carpenter's bundle in `blender/lib/fonts/`, turned into 3D lettering inside the models or set in the drawn posters:

| Asset | Used for | Source | Licence |
|---|---|---|---|
| UnifrakturCook | "Riesenrad" entrance sign (ferris.glb), "Karussell" on the rounding board (carousel.glb); titles of the booth posters and price board (ferris.glb) | https://github.com/google/fonts/tree/main/ofl/unifrakturcook | SIL Open Font License 1.1 |
| Alegreya SC (Huerta Tipográfica) | "Kasse" sign on the Riesenrad ticket booth; poster and price-board lettering (ferris.glb) | https://github.com/google/fonts/tree/main/ofl/alegreyasc | SIL Open Font License 1.1 |
| IM Fell English Italic (IM Fell types, digitised by Igino Marini) | Italic lines on the booth posters (ferris.glb) | https://github.com/google/fonts/tree/main/ofl/imfellenglish | SIL Open Font License 1.1 |

## Vendor (goods and props: blender/props/, site/public/models/prop_*)

Every prop is modelled in code (`blender/props/*.py`) and every texture in the vendor atlas (`prop_tex_atlas_*.webp`: book spines and cloth, mug glazes and prints, bottle and jar labels, the chalkboard, copper, brass, steel, iron, wood, bread, sausage skin, coals, Lebkuchen icing, cheese, crêpes, chestnuts and so on) is drawn procedurally with numpy and Pillow by `blender/props/vendor_atlas.py`. No third-party images or models are used. The book spines and covers on the Bücherstand (`prop_tex_books_*.webp`, drawn by `blender/props/atlas_books.py`) carry only the titles and authors of Mac's 55 books from `content/books/categories.json`, set in the fonts below on original typographic designs; no publisher cover artwork is reproduced. Filler books carry no lettering. The open book on the counter is the bookseller's guest book, with greetings written for this site.

The only third-party assets are fonts, used to draw lettering into the atlas (bundled in `blender/props/fonts/` and the carpenter's `blender/lib/fonts/`):

| Asset | Used for | Source | Licence |
|---|---|---|---|
| Oswald (The Oswald Project Authors) | Book spines and covers (e.g. The Order of Time), jacket lettering | https://github.com/google/fonts/tree/main/ofl/oswald | SIL Open Font License 1.1 |
| EB Garamond (The EB Garamond Project Authors) | Book spines and covers, labels | https://github.com/google/fonts/tree/main/ofl/ebgaramond | SIL Open Font License 1.1 |
| Playfair Display (The Playfair Display Project Authors) | Book spines and covers (e.g. Infinite Powers); a label | https://github.com/google/fonts/tree/main/ofl/playfairdisplay | SIL Open Font License 1.1 |
| Cinzel (The Cinzel Project Authors) | Cloth-bound spines (e.g. Einstein, Poor Charlie’s Almanack); rum label | https://github.com/google/fonts/tree/main/ofl/cinzel | SIL Open Font License 1.1 |
| Bebas Neue (Dharma Type) | Book spines and covers (e.g. Elon Musk, Atomic Habits) | https://github.com/google/fonts/tree/main/ofl/bebasneue | SIL Open Font License 1.1 |
| Josefin Sans (The Josefin Sans Project Authors) | Book spines and covers (e.g. The Book of Why) | https://github.com/google/fonts/tree/main/ofl/josefinsans | SIL Open Font License 1.1 |
| Libre Baskerville (The Libre Baskerville Project Authors) | Cloth spines, a bottle label | https://github.com/google/fonts/tree/main/ofl/librebaskerville | SIL Open Font License 1.1 |
| Caveat (The Caveat Project Authors) | Chalk handwriting on the beer price board; the guest-book greetings | https://github.com/google/fonts/tree/main/ofl/caveat | SIL Open Font License 1.1 |
| Pacifico (The Pacifico Project Authors) | Glühwein mug lettering, Lebkuchen icing, Amaretto label | https://github.com/google/fonts/tree/main/ofl/pacifico | SIL Open Font License 1.1 |
| UnifrakturCook, IM Fell English, Alegreya SC (carpenter's bundle, credited above) | Mug and coaster Fraktur, spice-jar labels, paper-bag print | see Carpenter | SIL Open Font License 1.1 |

## Organizer (people, crowd: blender/people/, site/public/models/people_*, site/src/crowd.json)

Every figure, including bodies, faces, hair, coats, scarves, hats, gloves, boots, aprons, bags and the Glühwein mug, is modelled in code (`blender/people/figures.py`). The skeleton, skin weights and every clip (walk, idle, chat, drink, laugh, sit, the band's play and rest, the vendors' serve and wipe) are built and keyed procedurally (`rig.py`, `anims.py`). No motion capture, scans, third-party models or third-party images are used. The two knit and wool normal maps (`people_knit_normal`, `people_wool_normal`) are drawn in numpy by `blender/people/pmats.py`. The crowd layout in `site/src/crowd.json` is generated from the architect's `layout.json` by `crowd_plan.py`.

Tools only (nothing of theirs is shipped by this role): Blender 4.2 `bpy` (GPL, used as a build tool, so its output is not covered), glTF-Transform, meshoptimizer and sharp (MIT / Apache-2.0) via `blender/people/pack.mjs`, which runs the same web passes as the carpenter's `blender/lib/optimize.mjs`, three.js (MIT, credited above) and Playwright with Chromium (Apache-2.0 / BSD) for checking the models in a browser (`blender/people/web/`).
