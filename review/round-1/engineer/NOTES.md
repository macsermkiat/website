# Engineer, round 1 (pass 2): the market in the browser

`site/` is a Vite 8 + three.js 0.186 app. It builds to `site/dist` with base `/website/`, and `.github/workflows/pages.yml` deploys it to GitHub Pages (npm ci, build, upload, deploy). Pass 1 is described at the end of this file ("What the site does"). This pass works through the judging panel's list.

## What changed in pass 2

### 1. Music credit on both pages (was the precondition for a public deploy)

- The footer of `index.html` and `plain.html` now carries the music credit. The build takes it from the music writer's `manifest.json` (`license.recording.credit`) in `plugins/market.js` (`audioCredit()`). It names the piece and credits the Salamander Grand Piano (CC BY 3.0), the MusyngKite tenor sax (CC BY-SA 3.0), the CC0 bass and drums, and the recording (CC BY-SA 3.0).
- Every licence name links to its Creative Commons deed, and the line ends with a link to `CREDITS.md`.
- A second sentence credits the fallback band: FluidR3 GM by Frank Wen (CC BY 3.0) and the Tone.js drums (MIT). It is there because that band can still play if the recording fails.
- `CREDITS.md`, engineer section: the FluidR3 row now says it serves only the fallback band. A new paragraph says which credit the site shows and where it comes from. The old open question named FluidR3 for the shipped sax, which was wrong. The shipped stems use MusyngKite and Salamander, and the question is now closed (see the questions below).

### 2. The Glühwein close-up: the vendor is visible

- `crowd.js` has a second test next to the sight-line cone. For each vendor that a close camera can see (within 14 m and within about 37° of the view direction), anyone on the line from the camera to the vendor's chest steps out of the shot, if they are nearer than the vendor. Vendors themselves are never hidden.
- During this pass the organizer also moved the Glühwein queue to the side of the counter, so on the final build nobody stands on the line any more. The engine test stays as a safety net for the other stalls and for later crowd edits. See `panel_gluehwein.jpg`.
- The smoke test checks two things, independently of the engine code: the vendor is visible, and no visible person stands between the camera and the vendor (a plain line-of-sight test in the test itself).

### 3. Fewer triangles and draw calls

**Crowd distance LOD** (full market)
- After the first frame, each person gets a second figure from its `people_*.lite.glb`. Beyond 18 m the lite figure draws; nearer than 16 m the full one does. The gap stops people flickering between the two at the boundary.
- Each figure has its own mixer. Only the visible one is updated, and on a switch the clip time carries over, so a step or a sip does not restart.
- Loading the LOD figures waits until after the market is on screen, so it does not delay opening.
- Home view: **1.18 M → 0.90 M triangles** (all 90 people use the lite figure from there).

**Merged book spines**
- `engine/merge.js` merges the bookshop's 104 `act_book_` meshes into **3 meshes, one per shelf set**. The quantized glb attributes are decoded to floats first.
- The book nodes stay in the scene as hidden pick proxies. A raycast still hits a hidden mesh, so clicking a spine still works.
- When a book is pulled, its own mesh shows and its copy in the merged mesh collapses to empty triangles. When it is back on the shelf, the merged copy returns.

**Mugs**
- People without a mug (the organizer's `_free` clips) no longer draw their scaled-away mug mesh.

**Totals**
- Meshes: full market **1,124**. That includes the vendor's new sets from this round (a wine shelf, a beer shelf and more books); the same build without the merge had 1,232.
- Lite market: **838** after its deferred models arrive.

**Rendering cost**
- The full market's pixel ratio is capped at **1.5** (it was 1.75).
- The lighting module already has adaptive quality. Under ~55 fps it steps down in order: MSAA 4× → 2×, then pixel ratio 1.5, then half-resolution bloom, then moon shadows every 4th frame.

**A meter for real hardware**
- `?perf` opens a frame-time meter in the corner of the market. It shows the median and 95th-percentile frame time over 240 frames, fps, draw calls and triangles for the whole composer frame, the canvas size and the pixel ratio.
- "Copy" puts a one-line report on the clipboard. I still have no real GPU here; see question 1.

### 4. The lite market: under 8 MB before it opens

- The lite market now opens without the Riesenrad, the Karussell and the nine deco stalls (about 3.4 MB). They load right after the first frame.
- When they arrive:
  - their `light_` empties become warm pools, so the four real lights stay on the section stalls;
  - the lighting module's `tune()` sets up their bulbs;
  - they join picking and the snow toggle.
- If someone asks for a ride before the ride has loaded, it starts when the ride arrives, and the camera flies there once it exists.
- The lite crowd draws its 40 people from 9 figures instead of 12. Parka → coat, young woman → woman in coat and girl → boy, recoloured as before, which saves about 300 KB.
- Measured in the smoke run: **6.87 MB** is fetched before the market opens, counting code, fonts and models. The count is every resource that started before the page's `market-ready` mark. The total after everything arrives is about 10.5 MB.
- `?defer=0` loads everything up front.

### 5. Re-run against the current lighting module

- The build and every screenshot in this folder come from the current `site/src/lighting/` (the lighting designer's pass-2 files), in one smoke run after the last code change.

### 6. Lights on the lite market, and snow

**Lite lights**
- `main.js` → `placeMarketLights()` calls the lighting module's `placeLights` twice on lite:
  1. with the section stalls only, so each of the four takes one of the four lights;
  2. with everything else at budget 0, so the rest become pools.
- The smoke test checks that Glühwein, Bierstand, Bücherstand and Bratwurst each have exactly one light. The Bratwurst panel is lit now.
- The engine's own fallback placement takes the same `budget` option.

**Snow**
- With snow on, the lighting module thickened the fog to 0.024, and the stall lights and bulbs drowned in it.
- The engine now caps the snow fog at 0.017 (`SNOW_FOG_MAX` in `main.js`). This is written into the module's exposed `settings.snow.fogDensity` only when the module's value is higher, so once the lighting designer adopts a value at or under 0.017 in `settings.js`, the cap does nothing.
- Bulbs also burn 30% brighter as the snow comes in.
- See `home_full_snow.jpg`. **Request to the lighting designer:** please take 0.017 (or your own lower value) into `settings.js` so that the setting lives in your module.

### 7. Phone layout

- On a phone the panel is a bottom sheet capped at **58% of the screen** (`min(58svh, 560px)`), and its height follows its content.
- Opening a place scrolls the market to the top of the screen, and the view shifts so the place sits in the visible part above the sheet. The shift is recomputed as the page scrolls.
- Smoke check on a 390×844 phone: the sheet is 53% of the screen, and 45% of the screen above it still shows the market (`phone_reduced_motion.jpg`).

### 8. The five books on five named spines

- In this round the vendor printed the reading list's titles on real spines in the middle of the lower shelf: The Order of Time, GEB, the three Feynman volumes, Being You and The Book of Why. Every book now carries a name, as glb extras (`title`, `author`) and in `public/models/items.json`, keyed by node name.
- `stalls.js` reads a book's identity from the node's extras. It falls back to `items.json`, because the lite glbs have no extras, but their books have the same node names and cover materials.
- Each `reading.md` book is matched to its spine by title. "The Feynman Lectures on Physics, Vol. II" still counts as the Feynman lectures. Clicking a spine pulls that book and shows its title, author and note.
- Clicking any other spine names that book (for example *Critique of Judgment* · Immanuel Kant) and says it is the bookseller's stock and where Mac's five stand.
- "Pull a book" goes through Mac's five in order and pulls the right spine.
- If Mac swaps in a book that has no printed spine, it gets a free spine near the middle of the view (not behind the bookseller) with a red paper band round it.
- The smoke test aims a real mouse click at the second book's spine and checks that the panel shows "Gödel, Escher, Bach".
- The vendor's new export gives every book its own cover material (`book_cover_<n>`). All of those materials sample one texture, so the merge groups materials by how they look, not by identity. It still makes 3 meshes from 108 books.

### 9. Smaller fixes

- **Lite band buttons.** On lite the player buttons read "Spotlight: Sax" and so on, with a tooltip, because the lite market streams one mix. The featuring note uses the writer's `play.lite` sentence.
- **Pages settings.**
  - `pages.yml` runs `actions/configure-pages` before the build and passes its `base_path` to Vite (`PAGES_BASE`). A renamed repository or a custom domain then still works. A local build keeps `/website/`.
  - The placeholder gate is a repository variable: set `STRICT_CONTENT` to `1` in the repository settings and the build fails while any `[[Mac: …]]` is left. There is no code change to make on the day.
- **Testing stand-ins without deleting files.** `?missing=all` or `?missing=stall_bier,ferris` pretends those glbs were never shipped, and `?layout=builtin` ignores `layout.json`. The smoke test uses both: every place becomes a labelled stand-in, the actions still work, and there are no console errors (`missing_models_standins.jpg`).
- **Bug fixed.** A click on a spine resolved to the book's mesh node (`act_book_N_mesh`) instead of its pivot. Picking now skips `_mesh` names.

## Verification

- **`npm ci && npm run build` passes.** The only message is the writer's placeholder count (16 in 7 files).
- **Smoke suite, `node tests/smoke.mjs --dist <copy of dist>`: 61/61 checks passed, no console errors.** It ran on the final build (snapshot taken 10:51 UTC, after the lighting module's last change) against the current lighting module. The vendor was still re-exporting a few props (`prop_bier_back`) while it ran, so the models on disk may be slightly newer than the ones tested. Its phases are the full market (screenshots), every interaction, lite detection, a phone with reduced motion, plain.html and the credits, missing models, and the recorded band. New checks in this pass:
  - the crowd LOD;
  - the merged spines;
  - the vendor visible in the Glühwein view, with nobody visible on the line to the vendor;
  - five named spines, and a 3D click on one giving its book;
  - "Spotlight" labels on lite;
  - deferred rides and stalls arriving;
  - the lite download before opening;
  - one light per section stall on lite;
  - the phone sheet at 60% of the screen or less, with the market visible above it;
  - the music credit and licence links on both pages;
  - every glb missing, `layout.json` ignored, and two named glbs missing.
- SwiftShader takes 10–30 s per full-quality frame. The full-market screenshots use reduced motion and a frozen frame. The LOD figures load with the picture frozen for the same reason.

Screenshots in this folder:

| File | What it shows |
|---|---|
| `home_full.jpg` | Home view, full market, with the crowd LOD active |
| `panel_gluehwein.jpg` | Glühwein panel after "Pour" and "Prost!": the vendor in view, nobody on the line to the counter |
| `panel_buecherstand.jpg` | Bücherstand after "Pull a book" |
| `panel_bandstand.jpg` | Bandstand, sax featured |
| `home_full_snow.jpg` | Snow on, with the fog capped at 0.017 and the bulbs lifted |
| `ride_riesenrad.jpg`, `ride_karussell.jpg` | From a gondola and from a horse (lite, deferred rides) |
| `home_lite_stage.jpg` | Lite market, detected on the software GPU |
| `phone_reduced_motion.jpg` | 390×844 phone, reduced motion: the Karussell above a 53% bottom sheet |
| `plain_html.jpg` | The text page, with the music credit in its footer |
| `missing_models_standins.jpg` | Every glb missing and `layout.json` ignored: the BUILD.md layout in stand-ins |
| `panel_bratwurst_lite.jpg` | Lite market, Bratwurst after "Turn the sausages": the stall has its own light now (the counter front is still dim) |

## Budgets

**Scene, as drawn** (visible meshes, instanced copies counted):

| | Full market (home view) | Lite market (after deferred models) |
|---|---|---|
| Triangles | 897k with LOD (1.17 M without) | 191k at first paint; about 297k after the deferred models |
| Meshes (about the draw calls per pass) | 1,127 (about 1,235 without the book merge) | 557 at first paint; about 838 after |
| Real-time lights | 12 + 2 band spots | 4, one per section stall (band spot faked) |
| Light pools on the ground | 64 | 25 at first paint; 51 after |
| Crowd | 90 people + 4 musicians; lite figures beyond 18 m | 40 people from 9 figures + 4 musicians |
| Pixel ratio cap | 1.5 | 1.25 |

**Download**

| What | Size |
|---|---|
| JS: three.js chunk | 751 KB (190 KB gzip), cached separately |
| JS: market code | 190 KB (66 KB gzip) |
| JS: lighting module | 42 KB (17 KB gzip) |
| Lite market, everything fetched before it opens (code, fonts, models) | 6.81 MB |
| Lite market, after the deferred rides and deco stalls | about 10.5 MB |
| Full market before it opens | about 26.7 MB (plus 1.3 MB of LOD figures after) |
| Audio | unchanged: 4.3 MB mix on lite; the mix plus 21.5 MB of stems on full, only after play |

## Questions for Mac

1. **Frame time on real hardware.** Nothing here has a GPU, so no one has seen the market run on one. Please open the site with `?perf` (and `?quality=full`) on a mid-range laptop and a phone. Press "Copy" on the meter and paste the line back. If the full market is under 30 fps on the laptop, the next steps are to make more machines default to lite, or to lower the LOD distance.
2. **When should the placeholder gate be switched on?** Setting the repository variable `STRICT_CONTENT=1` makes the Pages build fail while any of the writer's 16 `[[Mac: …]]` notes remain.
3. **Pages.** Pages must use "GitHub Actions" as its source. The base path now comes from the Pages settings, so the repository name no longer has to be `website`.
4. **Share-alike music.** The shipped sax recording is CC BY-SA 3.0, because it is built from the MusyngKite samples. The site credits it correctly now. If you would rather avoid share-alike, the music writer can re-render with `--sax-bank fluidr3` (CC BY only).
5. **Header tagline.** It still says "I build tools for clinical research…" (from `site.md`). Nothing clinical appears in the scene. Keep the wording?

(Pass 1's question about the FluidR3 licence is closed. FluidR3 is used only by the fallback band, and it is credited in the footer either way.)

## For the other roles

- **Lighting designer:** please put the snow fog at 0.017 or lower in `settings.js` (the engine caps it for now). On lite, the engine places the section stalls first; it could be a `placeLights({ ranking: 'sections-first' })` option in your module instead. On lite the Bratwurst stall now has its light, but the counter front stays dim (`panel_bratwurst_lite.jpg`); a slightly lower or more forward light position there would help.
- **Vendor:** thank you for the book extras and `items.json`; the site uses both. Please put the same extras in the lite glbs as well. For now the site finds lite books through `items.json`, by node name.
- **Organizer:** thanks for moving the Glühwein queue aside. The engine still hides anyone who ends up on a camera-to-vendor line, so later crowd edits cannot hide a vendor again.

## Still open

- The ballad's ending never plays, because the loop cuts before the out head. The manifest now describes the ending and a second tenor chorus for alternate passes (`alternates`). The stems player does not use either yet.
- The full market still fetches all its models before it opens (about 25 MB). The same deferral as on lite would work there, but the rides' lights are among its twelve real ones, so their placement would need a second pass.
- The musicians' hands do not follow the small sway of their instruments.

---

## What the site does (from pass 1, still true)

- **Loading.** `layout.json` (or the BUILD.md layout) → GLTFLoader + MeshoptDecoder, four at a time, `*.lite.glb` on lite. Each model falls back from lite to full to a labelled stand-in built in code. A build-time inventory stops the page asking for files that do not exist.
- **Node conventions.**
  - `bulbs_*` glow and pulse with the bass.
  - `light_*` become lights within the budget, and pools beyond it.
  - `snow_*` follow the snow toggle.
  - `slot_*` take the vendor's sets from `props.json`. On the bandstand they take the instruments and the organizer's musicians.
  - `cam_view`/`cam_target` drive the flights.
  - `rot_*` spin.
  - `gondola_*` stay upright; `horse_*` bob.
  - `*_seat*` empties are the ride cameras.
  - `act_*` drive the actions.
- **Interactions.**
  - Hover outline and tooltip, and click to open.
  - The panel with its action buttons.
  - Pour a mug, Prost, pull a pint, turn the sausages, a sausage in a bun, pull a book, feature a player, play and pause.
  - The Riesenrad and the Karussell.
  - Snow toggle and reset.
  - Keyboard: 1–7, Esc, arrows, +/-, Home.
  - Reduced motion, watched live.
- **Content.** `content/*.md` is parsed at build time (front matter + marked), with the prototype text in `site/content-fallback/` as the fallback. `plain.html` is filled from the same content.
- **Lighting.** `src/lighting/index.js` through `import.meta.glob`, with `src/lighting-fallback.js` if it is missing or throws.
- **Sound.**
  - Full market: the mix starts at once, then the five stems (HRTF panners at the players' places) take over at the same bar, and featuring raises one player.
  - Lite market: the mix only.
  - Fallback: the prototype's generative band.
  - Stall sounds are synthesised.
- **Quality.** `?quality=lite|full`, then the remembered choice, then detection (phone, weak or software GPU, low memory or cores, Save-Data), with a header toggle and a "Running slowly?" button.
