# Engineer, round 1: the market in the browser

## What was built

`site/` is a Vite 8 + three.js 0.186 app. It builds to `site/dist` with base `/website/`, and `.github/workflows/pages.yml` deploys it to GitHub Pages (npm ci, build, upload, deploy). `npm run build` passes, and `npm run test:e2e` (`site/tests/smoke.mjs`) drives the built site in Playwright on software GL.

Everyone's round-1 output is in the market now:
- the architect's square, town, tree and layout;
- the carpenter's four stalls and nine deco stalls;
- the vendor's 17 prop sets;
- the ride builder's bandstand, Riesenrad, Karussell and four instruments;
- the organizer's crowd (`crowd.json` and 16 animated people glbs);
- the lighting designer's module;
- the music writer's stems;
- the writer's content.

**Loading**
- The engine reads `site/src/layout.json`, or falls back to the BUILD.md layout without it.
- It loads each glb with GLTFLoader + MeshoptDecoder, four at a time, and uses `*.lite.glb` on the lite market. The loader tries the lite file, then the full file, then a labelled stand-in built in code, so a missing or broken glb never stops the market.
- A build-time inventory (`virtual:market-inventory`) lists which models, props and audio files exist, so the page never asks for a missing file.
- Deco stalls share their kit textures. Each image is fetched and decoded once, and uploaded to the GPU once.

**Node conventions** (`src/engine/conventions.js`, `market.js`, `props.js`, `instruments.js`)
- `bulbs_*`: glow, with a slow shimmer and a pulse on the bass.
- `light_*`: become lights up to the budget. When the lighting module offers `placeLights`, as it now does, it places them (point or spot, with static shadows on full). Otherwise the engine does. Lights over the budget become warm pools on the ground.
- `snow_*`: follow the snow toggle.
- `slot_*`:
  - take the vendor's sets from `public/models/props.json` (its `sets` list, or a map);
  - on the bandstand, `slot_sax|piano|bass|drums` take `instr_<player>.glb` plus the organizer's musician (`people_band_<player>.glb` from `crowd.json` "musicians"). The musician plays the "play" clip while the band plays and "rest" otherwise. Without those files, a stand-in figure stands or sits there.
- `cam_view` / `cam_target`: the flight to each place.
- `rot_*`: spin. The axis comes from `userData.axis`, a hint in the name, or the thinnest side.
- `gondola_*`: stay upright. `horse_*`: bob.
- Seats: `gondola_seat_0` and `horse_seat_2` are the ride cameras. Gondolas are built alike, so gondola 0's seat is used in whichever gondola is at the bottom when you board.
- `act_*`: drive the actions.
  - `act_x_mesh` inside `act_x` counts as geometry, not a second pivot.
  - The vendor's `act_grill_swing` swings.
  - The ride builder's `act_brush_l|r` sweep with the drums stem.
  - When a stall has no `act_` goods, the engine adds stand-in goods so its buttons still work. Since the vendor's props arrived, no stall needs them.

**Every interaction from the prototype**
- Hover outline (an OutlinePass inside the lighting composer), a tooltip, and click to open.
- The panel carries the writer's content and the action buttons. It is a bottom sheet on phones. The view shifts off-centre so the place stays clear of the panel. Opening a place from the buttons under the market scrolls the market back into view.
- Actions:
  - Glühwein: pour a mug, Prost (the crowd answers).
  - Bierstand: pull a pint.
  - Bratwurst: turn the sausages, one in a bun.
  - Bücherstand: pull a book (click a spine or let the bookseller choose).
  - Bandstand: feature a player, play and pause.
- Rides: the Riesenrad and the carousel.
- Controls:
  - snow toggle (`?snow=0|1`, otherwise on in season);
  - reset;
  - keyboard: 1–7, Esc, arrows and +/- on the focused canvas, Home.
- Reduced motion, watched live: flights are instant, and the scene stands still unless you ride.
- People standing between a close camera and the stall step out of the shot.

**Crowd** (`src/crowd.js`) reads the organizer's `crowd.json` v1:
- The groups are vendors, queues, walkers, groups and benches. Members are relative to their group and face it, unless they carry a `rotY`.
- Each person gets their model, `clip`, `phase` and coat/scarf/hat `colors`. There is one material per colour, shared.
- Walkers follow their `path` from `start`, with the walk cycle scaled to their `speed`.
- The lite market keeps the first `lite.cap` (40) entries.
- On "Prost!", nearby people holding a mug play `drink` for a moment and say a toast.
- Other crowd.json shapes are read loosely, and with no crowd.json the prototype's crowd is built from stand-in figures.

**Content** (`plugins/market.js`, `src/content.js`)
- `content/*.md` is parsed at build time (YAML front matter plus marked). The prototype text in `site/content-fallback/` fills gaps.
- The writer's front matter all drives the page:
  - `hint`, `actions`, `notes` (with `(done)`, lists, `{n}`, `{title}`, `{author}`, `{note}` and `{play}`), `books`, `crowd`, `order`;
  - `site.md`'s `tagline`, `description` and `ui`.
- `[[Mac: ...]]` shows as a small dashed note, and `<!-- check -->` stays invisible. The build prints how many placeholders are left, and `STRICT_CONTENT=1 npm run build` fails while any remain.

**Lighting**
- `src/engine/lighting.js` imports `src/lighting/index.js` through `import.meta.glob`, checks what it returns and falls back to `src/lighting-fallback.js`.
- With the module present, the engine lets it place the lights and turns off its own snowfall. Those were the lighting designer's two requests.

**Sound** (`src/audio/`)
- **Full market.**
  1. Pressing play streams `ballad-mix.mp3` at once through one panner at the bandstand.
  2. Meanwhile the five stems download and decode one at a time. Each is folded to mono (the room return stays stereo), resampled to 24 kHz (drums 32 kHz) and cut at `loopEnd`.
  3. The stems take over at the same bar with a 0.35 s crossfade. All of them start on one AudioContext tick and loop `loopStart`–`loopEnd`.
  4. Each player has an HRTF panner at their place on stage, and the listener follows the camera.
  5. Featuring raises one player (×1.6) and lowers the rest (×0.5). The analysers drive the players, the brushes and the bulbs.
- **Lite market.** Only the mix streams, through an `<audio>` element. Levels come from `ballad-events.json`, and the spotlight still moves.
- Nothing is fetched before play.
- If the recording fails, the prototype's generative band plays from `fallback/samples.json`. The stall sounds stay synthesised.

**Lite market**
- The choice comes from `?quality=lite|full`, then the remembered choice, then detection. Detection looks for a phone-sized touch screen, a software or weak GPU, low memory or cores, or Save-Data.
- It uses the lite glbs, no shadows, 4 lights, the lighting module's lite profile and equal-power panning, with the pixel ratio capped at 1.25.
- The crowd is the first 40 people of crowd.json instead of 90.
- The bandstand spot is a pool of light instead of a light, which frees the light for a stall. A soft beam joins the pool while a player is featured.
- The header toggle switches quality, and a "Running slowly?" button appears on a slow full market.

**plain.html**: the same content as a static page with all seven sections. It needs no JavaScript and links back to the market. The 3D page links to it from the skip link and the footer.

## Verification

- **`npm run build` passes.** The only message is the writer's placeholder count (17 in 7 files).
- **The smoke suite passes on the final build: 42 of 42 checks, and no console errors, failed requests or HTTP errors.** The run was `node tests/smoke.mjs --dist <copy of dist> --out <dir>`. It covers six phases:
  - the full market (screenshots);
  - every interaction on the lite market: pour, Prost, pint, sausages, bun, book, featuring, play and stop, both rides, snow, reset, the keyboard, and hover and click in 3D;
  - the recorded band on the full market, where the mix starts at once, the stems take over and the levels move;
  - lite detection (no shadows, 4 lights or fewer);
  - a phone with reduced motion;
  - plain.html.
- After that run I changed only the carousel rider's view direction. The interaction phase was re-run afterwards; see the last line.
- `npm run dev` serves the same page, with the content and inventory as virtual modules.

Screenshots in this folder:

| File | What it shows |
|---|---|
| `home_full.jpg` | Home view, full market |
| `panel_gluehwein.jpg` | Glühwein panel after "Pour a mug" and "Prost!" |
| `panel_buecherstand.jpg` | Bücherstand after "Pull a book" |
| `panel_bandstand.jpg` | Bandstand with the ride builder's instruments, sax featured |
| `home_full_snow.jpg` | Snow on (the lighting module's snow) |
| `ride_riesenrad.jpg` | From a Riesenrad gondola, lite |
| `ride_karussell.jpg` | From the carousel horse, lite |
| `home_lite_stage.jpg` | Lite market, detected on the software GPU |
| `phone_reduced_motion.jpg` | 390×844 phone, reduced motion, carousel panel as a bottom sheet |
| `plain_html.jpg` | The text page |

The full-market screenshots use reduced motion and a frozen frame. SwiftShader takes 9–23 s per full-quality frame, so waiting for flights would take hours.

## Budgets

**Scene, as built** (visible meshes; instanced copies counted):

| | Full market | Lite market |
|---|---|---|
| Triangles | 1,197,259 | 347,889 |
| Meshes (about the draw calls per pass) | 1,155 | 875 |
| Real-time lights | 12 + 2 band spots | 4 (band spot faked) |
| Light pools on the ground | 64 | 50 |
| Crowd | 90 animated people (crowd.json) + 4 musicians | 40 + 4 musicians |
| Shadows | moonlight + static shadows on 4 stall lights | none |

**Download**

| What | Size |
|---|---|
| JS: three.js chunk | 751 KB (187 KB gzip), cached separately |
| JS: market code | 152 KB (54 KB gzip) |
| JS: lighting module | 30 KB (12 KB gzip) |
| CSS | 8 KB + 4 KB (plain page) |
| Fonts (Alegreya SC / Sans, latin woff2, used weights only) | about 120 KB |
| Models, full market (all 56 glbs, incl. 2.0 MB of people) | 24.9 MB |
| Models, lite market (lite variants where they exist) | 10.4 MB at most |
| Audio, lite (mix, streamed on play) | 4.3 MB |
| Audio, full (mix while loading, then 5 stems) | up to 4.3 + 21.5 MB, only after play |
| Fallback samples (only if the stems fail) | 1.1 MB |

Decoded stems stay at about 120 MB of memory on the full market: mono at 24/32 kHz, cut at loopEnd. Full-length stereo at the device rate would be about 520 MB.

**Per model (full / lite triangles)**
- square 32.4k / 12.7k; town 146k / 39.9k; tree 36.5k / 7.7k.
- Stalls: gluehwein 38.6k / 11.0k, bier 45.0k / 12.7k, bratwurst 26.7k / 10.0k, buecher 31.9k / 9.7k.
- Deco stalls: 11.8–19.0k / 5.0–8.0k each.
- Rides: bandstand 30.7k / 10.4k, ferris 63.5k / 22.9k, carousel 78.7k / 27.3k.
- Instruments: 2.8–6.7k each. Vendor sets: 1.6–15.8k each.
- People (organizer): about 4.6k / 1.5k each.

## What to improve next

1. **Measure on real hardware.** This machine only has SwiftShader, so there is no real frame time. Someone should open the page on a mid-range laptop and a phone and read the frame time. That decides whether the full market's 1.2M triangles and 1,155 meshes (the organizer's 90 people add about 320k triangles), shadowed lights and MSAA fit, or whether more places should default to lite. The "Running slowly?" button is the safety net.
2. **Draw calls.** The glbs are already merged per material. The rest of the count is the crowd (two skinned meshes per person: body and mug) and the vendor's `act_*` goods (one mesh each, e.g. 60+ books). Books could merge into one mesh per shelf, with a picking proxy. The crowd is the biggest single item on the full market (90 × 4.6k triangles). People far from the camera could use their `.lite.glb` (1.5k) through a distance LOD, which would cut about 250k triangles from the home view.
3. **Lite lighting** (for the lighting designer). The module ranks landmarks equal with section stalls. On the 4-light lite market, the Bratwurst stand can end up with no light, and its panel view is dark. I suggest ranking section stalls first on lite. The engine's own fallback placement already does.
4. **The ballad's ending never plays** (the music writer's point). A "last tune" button could let the stems run past `loopEnd`, but then they could not be trimmed at `loopEnd`.
5. **Books.** Map the five books in `reading.md` to five named spines, so clicking a spine gives that book rather than the next in the list.
6. **Crowd and camera.** A few groups stand close to the bandstand steps and the stall fronts. The engine hides people on the line of sight when the camera is close, but a pass with the organizer on who stands where for each `cam_view` would be cleaner.
7. **Musicians and instrument sway.** The engine sways `act_sax` and `act_bass` with the stems, and the organizer's musicians have their own "play" clip. The sway is small (a few cm), but the ride builder and the organizer should check that the hands stay on the instruments.

## Contract

- **No breaks.** Everything reads the agreed files and conventions and keeps working when any of them is missing.
- **Additions other roles can use** (all optional):
  - the manifest's `mix` and `events`;
  - `userData.axis` on `rot_`, and `userData.color|intensity|distance` on `light_`;
  - `instr_<player>.glb` on `slot_<player>`;
  - `*_seat*` ride cameras;
  - crowd.json `musicians` played on the bandstand slots;
  - `act_x_mesh` as geometry;
  - the writer's `order`.
- **Nothing lab, pathology or clinical appears in the scene.** The text mentions clinical research only as Mac's work, in the writer's words.
- **Process note.** I only write inside `site/` (except layout.json, crowd.json, lighting/, public/models, public/audio), `.github/workflows/` and this folder, plus my section of `CREDITS.md`.

## Questions (for Mac or the lead)

1. **FluidR3 licence.** `CREDITS.md` lists FluidR3 GM as CC BY 3.0, per the gleitz repo README, but the prototype footer said MIT. The fallback band and the music writer's sax both use it. If it is CC BY, the site needs a visible credit line, and I can add one to the footer.
2. **Placeholders on the live site.** Should the Pages workflow build with `STRICT_CONTENT=1`, so nothing goes public until the writer's `[[Mac: ...]]` notes are filled?
3. **Pages.** The repository's Pages source must be set to "GitHub Actions". The base path `/website/` assumes the repository is called `website`. Is that right?
4. **Header tagline.** It says "Physician in Bangkok. I build tools for clinical research…", from `site.md`. Is that fine, given the rule that nothing clinical appears in the scene?
