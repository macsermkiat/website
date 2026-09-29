# Engineer, round 1 (pass 3): the market in the browser

`site/` is a Vite 8 + three.js 0.186 app. It builds to `site/dist` with base `/website/`. `.github/workflows/pages.yml` deploys it to GitHub Pages: npm ci, the unit checks, build, upload, deploy.

This pass works through the panel's list from pass 2. Everything below was measured on this build, on software GL (SwiftShader). **No one has run it on a real GPU yet** (see "Frame time" and question 1).

## Summary of this pass

| | Pass 2 | Pass 3 |
|---|---|---|
| Full market: download before it opens | 26.0 MB | **17.5 MB** (aim: 25 MB) |
| Lite market: download before it opens | 6.8 MB | **5.5 MB** (aim: 8 MB) |
| Full market, home view: meshes drawn | 1,127 | **451** |
| Full market, home view: triangles | 897k | **878k** |
| Lite market at first paint: meshes | 557 | **262** |
| Smoke suite | 61 checks | **SMOKE_TOTAL checks** (38 are browser-free unit checks), no console errors |

## What changed

### 1. First load under 25 MB: the full market defers too

- Both markets now open without the Riesenrad, the Karussell and the nine deco stalls. They load right after the first frame. `?defer=0` loads everything up front.
- **Lights in two passes.** On the full market the first pass holds back one real light for each ride (`DEFERRED_LIGHTS = 2` in `main.js`). When the rides arrive, a second `placeLights` pass gives them those two lights. It adds no more static shadows.
- The end state is the same as before: 12 real lights. That is two each on the four section stalls, plus the bandstand, the tree, the Karussell and the Riesenrad. The smoke test checks this.
- The crowd's walkers used the placed deco stalls to keep off them. They now use the layout, so the stalls count before their models arrive.
- A ride asked for before it arrives starts when it arrives. This is unchanged from pass 2 and now covers the full market too.

### 2. Fewer draw calls (`engine/merge.js`)

- **Static merge.** In each model, meshes that draw the same are merged into one mesh per rigid body. "Draw the same" means the same material, or materials that look the same, including the same shared texture. A rigid body is the model root, or a `rot_`, `gondola_`, `horse_` or `instrument_` node.
  - It merges the vendor's rows of mugs, bottles and glasses. They are `act_` nodes that no action moves.
  - It leaves alone every `act_` node an action uses. `actions/util.js` marks them as `live` when an action asks for them.
  - It also leaves alone snow caps, skinned meshes, animated nodes, and anything the engine or the lighting module added.
  - Emissive materials merge only with the same material object, because the lighting module and the actions animate them.
- **Bulb strings.** They are merged per rigid body after the lighting module has read them. The square alone had 50 separate bulb meshes.
- **The deco row.** Their `vendor_atlas` goods and kit wood are merged across all nine stalls into one row. Each stall's own AO-baked parts stay separate.
- **Riders.** Gondolas and horses that are built alike are drawn as instances: one `InstancedMesh` per part, with the pose copied from the rider every frame.
  - The meshopt export orders each copy's vertices differently, so parts are matched by material, triangle count and bounds.
  - The Riesenrad drops from 89 meshes to about 15.
- **Ground pools.** The lighting module's 41 pools, one quad per unlit `light_`, are now one instanced draw per placement pass.
- **The crowd.** Each lite figure's four parts (coat, body, hat, scarf) are merged into one skinned mesh with one shared material.
  - Each person's colours go into the vertex colours of their own copy of the colour attribute. Everything else is shared.
  - That is one draw per person instead of four, in the main pass and again in the moon-shadow pass.
  - The full figures (near the camera) keep their cloth normal maps and their four parts.
- **Result:** in the home view, meshes drop from 1,127 to 451. Draw calls per frame follow the meshes, plus the shadow and post passes. Full detail is in the budgets below.

### 3. The GPU rule, the LOD distance and a governor (`quality.js`, `governor.js`)

**The GPU rule**
- The pass-2 regex sent every "Intel(R) UHD Graphics" to lite. `gpuTier()` now sorts the renderer string into five classes: `software`, `weak`, `integrated`, `discrete` and `unknown`.
- Only `software` and `weak` go to lite by name:
  - software renderers;
  - Intel HD Graphics (2011–2016);
  - UHD 600/605/610 (Celeron and Pentium Silver);
  - Mali-4xx and Mali-T;
  - Adreno 3xx–5xx;
  - PowerVR.
- UHD 620/630/7xx, Iris, Iris Xe, Radeon integrated graphics and Apple M-series get the full market.
- `tests/unit.mjs` checks 26 real renderer strings, in ANGLE, Mesa and Safari forms, plus five detection cases.

**The LOD distance**
- The crowd's distance LOD now starts by class:
  - 18 m on a discrete GPU;
  - 14 m when the GPU is unknown;
  - 12 m on integrated graphics;
  - 8 m on a weak or software GPU.
- `?lod=<metres>` pins it for measuring.
- These are starting points, not measurements. See question 1.

**The frame-time governor (full market)**
- It measures the visitor's own frame time. When the median is over 33 ms, it steps down once per 120 frames:
  1. LOD to 12 m;
  2. LOD to 6 m;
  3. everyone uses their lite figure, and the crowd stops casting shadows;
  4. the "Running slowly? Switch to the lite market" button.
- It waits for the lighting module's own adaptive steps (MSAA, pixel ratio, bloom) to go first.
- It replaces the old one-off "slow frames" counter. `?governor=0` turns it off.

**The `?perf` meter**
- It now has a **Tour** button. The tour visits home, Glühwein, the bandstand, the Bücherstand, the Riesenrad view and home again, for about 6.5 s each.
- It then copies one line per view: median, 95th percentile, draw calls, triangles, the lighting step and the governor step.
- Mac only needs to press one button, then paste the result.

### 4. The Riesenrad delivers its view from the top

- The rider boards the lowest gondola. The wheel then turns about seven times faster, easing in and out, until that gondola reaches the top.
- It holds there for 14 s, barely moving, then carries on at its own pace. The panel says "At the top…"; the writer can override that line with a `Ride the wheel (done)` note.
- The exposure opens up while riding, from ×1.2 at the bottom to ×1.65 at the top, and comes back down on the ground.
- From the top, the view looks out over the square instead of down at the bandstand roof. See `ride_riesenrad.jpg`.
- The smoke test checks all of this: the top reached, the camera above 14 m, the exposure raised and restored, and the panel line.

### 5. A pulled book goes back

- Closing the panel, resetting the view or opening another place calls `retract()`. That puts the book back on the shelf and hides its title tag.
- This also works while the book is still sliding out.
- There are two smoke checks: one for reset view (full market) and one for the panel's close button (lite).

### 6. The ballad's written ending and its second chorus (`audio/songplan.js`, `audio/stems.js`)

**The stems**
- They now follow a road map built from the manifest:
  1. the head;
  2. the loop three times (`ending.passes` in the manifest, default 3), where pass 2 plays the tenor's second written chorus from `alternates`;
  3. the out head to the fermata (bars 81–96);
  4. 7 s of quiet;
  5. from the top.
- One pass through the whole road map is about 10 minutes.

**How it plays**
- Segments are scheduled on the AudioContext clock, with 6 s of lookahead and a timer, so it keeps playing in a background tab. All five stems start on the same tick.
- The alternate sax and room files swap in 0.25 s inside their edges, where the manifest says they are identical to the main stems.
- The alternates load after the main stems. If they are not ready yet, that pass plays the main chorus.

**The mix**
- The streamed mix (lite market, and the full market's first seconds) follows the same passes and ending, without the alternate chorus.
- The hand-over to the stems lands on the same bar of the same pass.

**Checks**
- `tests/unit.mjs` checks the road map.
- The smoke test plays the real stems and checks three things:
  - Seeking just before `loopEnd` on the last pass runs on into the out head.
  - On pass 1 it loops round.
  - Pass 2 plays the alternate chorus and pass 3 does not.

### 7. Crowd, snow and the lite Bratwurst (with the lighting designer and organizer)

- **The crowd no longer shows as black silhouettes.** Every crowd material gets a small fill proportional to its own colour (`crowdLift` in `crowd.js`, 0.4), so coats read as cloth in the home view. See `home_full.jpg`.
  - The full and lite figures get the same fill, so a person does not change brightness at the LOD switch.
  - The lighting module's moon rim still does the edges.
- **Snowflakes.** The engine caps the flake size at 3 cm and the softness at 0.45 (`capFlakes` in `main.js`).
  - The nearest layer was up to 5 cm and 90 % soft, which read as grey discs.
  - This is a request to the lighting designer, like the fog cap was. Once `settings.js` agrees, it changes nothing.
  - The lighting designer has already taken the fog cap (0.017) into `settings.js`.
- **Bratwurst (and every section stall) on lite.** The lite market has a close-up key light: one warm spot under the front eave of the open section stall, aimed at the counter front and the vendor. It fades in on open and out at home.
  - It is always in the scene, so moving it does not recompile shaders. That makes 5 lights on lite instead of 4.
  - See `panel_bratwurst_lite.jpg`. The smoke test checks that it follows the Bratwurst and fades out at home.

### 8. Phone home framing

- On a narrow portrait screen the home view comes in closer and lower: camera `[0.8, 5, 19.5]`, looking at `[0, 2.7, -4]`.
- The bandstand, the tree and the Glühwein and Bierstand stalls now fill the upper two-thirds, instead of a thin band over dark ground. See `phone_home.jpg`.

### 9. Smaller fixes

- **Music credit.** The music writer switched the sax to the MTG Solo Saxophones (CC BY 4.0).
  - The footer already takes the manifest's credit word for word. The licence links now cover any CC licence the credit names (BY/BY-SA/…, any version, and CC0), where pass 2 knew only BY 3.0, BY-SA 3.0 and CC0.
  - The test now checks the manifest's own credit line and a link for every licence it names.
  - `CREDITS.md` is updated.
- **Unit checks** (`npm run test:unit`, no browser) run in CI before the build.

## Verification

- **`npm ci && npm run build` passes** in `site/`. The only message is the writer's placeholder count, 16 in 7 files, which production builds leave out.
- **Smoke suite, final run: SMOKE_RESULT.**
  - It ran with `node tests/smoke.mjs --dist <copy of dist>` on the final build, started at 20:59 UTC.
  - At that time the newest lighting module file and glb on disk were from 20:16, so it ran against the vendor's latest `stall_bier`/`stall_bratwurst`/prop exports and the lighting designer's current module.
  - Its phases:
    - unit checks;
    - full market (screenshots, first-load size, deferral, the second light pass, merges, LOD, the governor);
    - every interaction on lite;
    - lite detection and download;
    - a phone with reduced motion;
    - plain.html and the credits;
    - missing models, plus the perf meter;
    - the recorded band, with the road map.
- **The screenshots come from the production build.** The writer's notes to Mac are hidden (`CONTENT_NOTES` unset). Pass 2's set had been taken from a notes-shown build.
- SwiftShader takes 10–30 s per full-quality frame. The full-market screenshots use reduced motion and a frozen frame.

| File | What it shows |
|---|---|
| `home_full.jpg` | Home view, full market: rides deferred and arrived, merged meshes, crowd LOD and fill |
| `panel_gluehwein.jpg` | Glühwein after "Pour" and "Prost!" |
| `panel_buecherstand.jpg` | Bücherstand after "Pick a book for me" |
| `panel_bandstand.jpg` | Bandstand, sax featured |
| `home_full_snow.jpg` | Snow on, with smaller, crisper flakes |
| `ride_riesenrad.jpg` | At the top of the Riesenrad (lite, deferred ride), exposure opened up |
| `ride_karussell.jpg` | From a horse |
| `home_lite_stage.jpg` | Lite market, detected on the software GPU |
| `phone_home.jpg` | 390×844 phone: the new home framing |
| `phone_reduced_motion.jpg` | Phone, reduced motion, the Karussell above the bottom sheet |
| `panel_bratwurst_lite.jpg` | Lite Bratwurst with the close-up key light on the counter front and the vendor |
| `plain_html.jpg` | The text page with the music credit |
| `missing_models_standins.jpg` | Every glb missing and `layout.json` ignored: the BUILD.md layout in stand-ins |

## Budgets (measured in the final smoke run)

**Scene, as drawn** (visible meshes; instanced meshes count every copy's triangles)

| | Full market, home view | Lite market |
|---|---|---|
| Triangles | 878k after LOD (867k at first paint, before the rides) | 184k at first paint, about 250k after deferral |
| Meshes | 451 after LOD and deferral (624 at first paint, full figures) | 262 at first paint, about 360 after deferral |
| Real-time lights | 12 + 2 band spots (10 at first paint, 2 more with the rides) | 4 + the close-up key |
| Ground pools | 41, drawn as 2 instanced meshes | 25 → 51, drawn as 2 instanced meshes |
| Crowd | 90 people + 4 musicians; LOD from 8–18 m by GPU class (8 m on SwiftShader) | 40 people, one draw each |
| Pixel ratio cap | 1.5 | 1.25 |

**Download**

| What | Size |
|---|---|
| JS: three.js chunk | 751 KB (187 KB gzip), cached separately |
| JS: market code | 256 KB (79 KB gzip) |
| JS: lighting module | 48 KB (19 KB gzip) |
| Full market before it opens (code, fonts, models) | **17.5 MB**; about 25 MB once the rides, deco stalls and LOD figures have arrived |
| Lite market before it opens | **5.5 MB**; about 9 MB after deferral |
| All `*.lite.glb` + lite textures on disk | 8.0 MB (aim 8 MB for the lite market) |
| Audio | 4.3 MB mix on lite; on full, the mix, then 21.5 MB of stems plus the two alternate stems, only after play |

## Frame time: still not measured on a real GPU

There is no GPU on the cloud machine, so the panel's first and eighth items cannot be completed from here. What exists instead:

1. The GPU classes and starting LOD distances above, which follow the usual GPU tiers. They are not based on measurements.
2. The governor, which measures every visitor's own frame time and cuts cost until the market holds 30 fps, or offers lite.
3. The `?perf` **Tour**, which produces the numbers in one press.

**Before announcing the site, please** open these and press Tour, then paste the copied lines back:
- `https://macsermkiat.github.io/website/?perf&quality=full&governor=0` on a mid-range laptop;
- `?perf&quality=lite` on a phone.

What to do with the laptop numbers:
- **Median above ~33 ms:** lower `LOD_BY_TIER.integrated` (and `unknown`) in `quality.js`, or move that class to lite.
- **Median well under 16 ms:** `integrated` can go to 18 m.

## Questions for Mac

1. **Real-GPU numbers** (above). This is the one thing that should happen before launch.
2. **When should the placeholder gate go on?** Set the repository variable `STRICT_CONTENT=1` and the Pages build fails while any of the 16 `[[Mac: …]]` notes remain.
3. **Pages settings.** Pages must use "GitHub Actions" as its source. The base path comes from the Pages settings.
4. **Header tagline.** It says "Physician in Bangkok. I write software for clinical research." Nothing clinical appears in the scene. Keep it?

## For the other roles

- **Lighting designer**
  - Please take the snowflake caps into `snow.js`/`settings.js` (size ≤ 3 cm, softness ≤ 0.45 for the near layer). Then `capFlakes` in `main.js` does nothing.
  - The engine now instances your pools. A `placeLights({ instancedPools: true })` in your module would be cleaner.
  - The lite close-up key light (`createKeyLight` in `main.js`) is yours to restyle or replace.
- **Carpenter and architect: smaller lite glbs.** All lite models together are 8.0 MB, against the 8 MB aim. The lite market opens at 5.5 MB only because it defers the rides and deco stalls. The largest lite files are:
  - `town.lite.glb` 1.4 MB;
  - `square.lite.glb` 1.0 MB;
  - `ferris.lite.glb` 0.73 MB;
  - `carousel.lite.glb` 0.61 MB.

  Sharing the square's ground textures with the town, and 256 px textures on the far town, would help most.
- **Ride builder.** Gondolas and horses built as linked duplicates would instance exactly. The engine now matches them by bounds, which works for the gondolas. The horses are four designs, and each is instanced within its own design.
- **Organizer.** Crowd materials now get a colour-proportional fill. If a figure looks too flat, `crowdLift` in `crowd.js` is the one knob. Lite figures are drawn as one mesh, so please keep the part materials named `coat`, `body`, `hat` and `scarf`.
- **Vendor.** Rows of `act_` goods that no action moves are merged now. If an action is added for one, it must ask for the node through `act()`/`acts()` in `actions/util.js`, which keeps it out of the merge.

## Still open

- The musicians' hands do not follow the small sway of their instruments.
- Snow caps (`snow_`) are not merged, so turning snow on adds their draws back.
- Horses of a design seen only once are not instanced.

## Contract notes

- **Light count on lite.** The lite market has 4 lights plus a close-up key that is dark at home: 5 real-time lights in the shader. BUILD.md says "fewer lights", with no number.
- **Light budget and deferral.** The full market's light budget stays 14 (12 + 2 band spots). Two of the 12 are placed only when the rides arrive.

---

## What the site does (from passes 1–2, still true)

- **Loading.** `layout.json` (or the BUILD.md layout) → GLTFLoader + MeshoptDecoder, four at a time, `*.lite.glb` on lite. Each model falls back from lite to full to a labelled stand-in. A build-time inventory stops the page asking for files that do not exist. `?missing=all` / `?missing=a,b` and `?layout=builtin` test the fallbacks.
- **Node conventions.**
  - `bulbs_*` glow and pulse with the bass.
  - `light_*` become lights within the budget, and pools beyond it.
  - `snow_*` follow the snow toggle.
  - `slot_*` take the vendor's sets from `props.json`, and the instruments and musicians.
  - `cam_view`/`cam_target` drive the flights.
  - `rot_*` spin.
  - `gondola_*` stay upright and `horse_*` bob.
  - `*_seat*` empties are the ride cameras.
  - `act_*` drive the actions.
- **Interactions.**
  - Hover outline and tooltip, and click to open.
  - The panel with its action buttons.
  - Pour a mug, Prost, pull a pint, turn the sausages, a sausage in a bun, pull a book (or click a spine), feature a player, play and pause.
  - Both rides, snow and reset.
  - Keyboard: 1–7, Esc, arrows, +/-, Home, Tab through the place buttons.
  - Reduced motion, watched live.
- **Content.** `content/*.md` is parsed at build time (front matter + marked), with the prototype text in `site/content-fallback/` as the fallback. `plain.html` is filled from the same content and linked from the 3D page.
- **Lighting.** `src/lighting/index.js` is loaded through `import.meta.glob`, with `src/lighting-fallback.js` if it is missing or throws.
- **Sound.**
  - Full market: the mix first, then five HRTF-panned stems at the players' places, with featuring.
  - Lite market: the mix only.
  - Fallback: the prototype's generative band.
  - Stall sounds are synthesised.
- **Quality.** `?quality=lite|full`, then the remembered choice, then detection, with a header toggle.
