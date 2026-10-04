export const meta = {
  name: 'nachtmarkt-build-round',
  description: 'Specialists build parts of the Nachtmarkt; an Opus + Fable judge panel reviews each and the builder iterates until both ship (max 3 passes)',
  phases: [
    { title: 'Build', detail: 'each specialist builds their part' },
    { title: 'Judge', detail: 'Opus 5.5 and Fable judge each part' },
  ],
}

const REPO = args.repo || '/home/claude/website'
const MACHINE = args.machine || ''
const START = args.startPass || 1
const ROUND = args.round || 1
const MAX_PASSES = args.maxPasses || 3

const COMMON = `You are a specialist on the team building Mac's personal website: a 3D German Christmas night market ("Nachtmarkt") in the browser. The repo is ${REPO} (github.com/macsermkiat/website). Read these first:
- MACHINE NOTE: ${MACHINE}
- ${REPO}/docs/BUILD.md is the build contract: ownership, tools, naming, budgets and layout. Follow it exactly and write only inside the paths your role owns.
- ${REPO}/CONTEXT.md is the glossary.
- ${REPO}/prototype/index.html (with audio.js) is the first mockup, built in code from primitives. The real build must clearly beat it in detail and craft.
- ${REPO}/blender/stalls/gluehwein.py is a worked Blender example: planks, shingles, procedural wood baked to textures, glb export and a Cycles preview. Its preview is ${REPO}/review/reference/gluehwein_preview.png.

The target look is a "realistic miniature": real materials, warm light, believable wear and irregularity, fine detail where the eye lands. It is not photoreal and not cartoon. Nothing lab, pathology or clinical may appear in the scene.

Other specialists are working at the same time on the other parts: architect, carpenter, vendor, ride builder, organizer, engineer, lighting designer, music writer and writer. Don't wait for them. Build against the contract, and use simple stand-ins for anything you need from another role.

Rules:
- Follow the "Where things run" section of BUILD.md for this machine: which Python runs Blender, which environment variables apply (NM_DEVICE, NM_THREADS), and the render sizes.
- Do not git commit or push. The session that started you does that.
- Do not install system packages with apt. pip and npm installs are fine when needed.
- Credit every third-party asset in ${REPO}/CREDITS.md under your role's heading. Use only assets whose licence allows a public website (CC0, CC-BY, MIT and similar).

When done, write the round notes in review/round-${ROUND}/<role>/NOTES.md, put your previews in the same folder, and return the structured summary.`

const ROLES = {
  architect: {
    title: 'architect and landscape designer',
    brief: `You own the market square, the old town around it, the Christmas tree and the layout.
Build with Blender scripts in blender/square/ and blender/town/ and export to site/public/models/:
- square.glb (+ square.lite.glb). The cobblestone square (about 70 m across) is irregular, worn and slightly wet-looking, with gutters, curbs and a gentle camber. Include:
  - cast-iron street lamps, each with a light_ empty and a bulbs_ lamp;
  - the string-light poles, with swagged wires carrying warm bulbs as bulbs_ meshes that criss-cross above the lanes, as in the prototype;
  - a few benches, bins and bollards;
  - a snow_ cover layer that fits the ground.
- town.glb (+ town.lite.glb). A ring of German old-town buildings at radius 47–64: half-timbered and plaster facades, varied heights, roofs, dormers, chimneys, shutters and shopfronts. No two neighbouring houses are identical. Windows use an emissive material named window_warm (some lit, some dark). Include a church with a tall tower at [8,-56]. Include snow_ caps on the roofs.
- tree.glb (+ lite). A tall decorated Christmas tree with baubles, a star, bulbs_ lights and a snow_ layer.
- site/src/layout.json. It is the single source of placement for every stall, landmark, deco stall, the tree, square, town and home camera. Each entry has: id, kind (section|landmark|deco|scenery), asset (glb file name), section (for section/landmark), label (German sign text), pos [x,z], rotY, and for deco stalls a goods key. Start from the layout in BUILD.md. You may improve it for a bigger, more natural market with room to walk, but keep the four section stalls and the bandstand in the main view from the home camera.
Render previews: one of the square and town from the home camera (with plain boxes where stalls go), one closer view of a street of houses and one of the tree.`,
    checks: [
      'site/src/layout.json exists, parses, and lists all 4 section stalls, 3 landmarks, 9 deco stalls, tree, square and town with pos and rotY',
      'square.glb, town.glb and tree.glb and their .lite.glb versions exist in site/public/models and are within the BUILD.md budgets (check with gltf-transform inspect)',
      'The town preview shows varied half-timbered facades with no two neighbouring houses identical and a church tower',
      'Windows use a material named window_warm and roofs/ground carry snow_ nodes',
      'Lamps and string lights carry light_ empties and bulbs_ meshes with bulb_warm material',
      'The cobblestones look irregular and worn, not like a flat repeating texture, in the preview',
      'The previews are clearly more detailed and believable than the prototype (prototype/index.html)',
      'NOTES.md lists triangle counts, file sizes and open issues',
    ],
  },
  carpenter: {
    title: 'carpenter (stall builder)',
    brief: `You own the wooden market stalls and the shared Blender helper library.
- blender/lib/: shared helpers for procedural wood, painted wood, shingles, metal, baking (base colour, roughness, normal, AO) and export plus gltf-transform optimisation. Other builders may import them, so give them a small, stable API and document it in blender/lib/README.md. Start by generalising what blender/stalls/gluehwein.py does.
- The four section stalls, each with its own character, in blender/stalls/ → site/public/models/stall_gluehwein.glb, stall_bratwurst.glb, stall_bier.glb and stall_buecher.glb, plus .lite.glb versions:
  - Glühwein: a tall hut with a carved, scalloped valance, star cut-outs and a red-and-gold painted trim.
  - Bratwurst: a sooty hut with a chimney hood over a grill opening.
  - Bierstand: a Bavarian-style bar with a blue-and-white rhombus pennant roof edge and a barrel-front counter.
  - Bücherstand: an antiquarian bookshop hut with glazed side cabinets, a little bay window and a hand-painted sign.
  Every stall must have the slot_ empties, light_ empties, bulbs_ garlands along the eaves, snow_ caps on the roof, cam_view/cam_target empties, a 3D sign with German text (Glühwein, Bratwurst, Bier vom Fass, Bücher) and a 1.05 m counter.
- A deco stall kit (blender/stalls/deco.py) with 9 variants: Lebkuchen, Gebrannte Mandeln, Kerzen, Holzspielzeug, Christbaumschmuck, Käse, Crêpes, Heiße Maroni, Kartoffelpuffer. Each is a structure with its sign, slots and lights, but no goods (the vendor makes goods). Export them to site/public/models/deco_<key>.glb (+ lite), sharing textures across variants.
Previews: one Cycles render per section stall (3/4 front view at night) and one contact sheet of the deco stalls.`,
    checks: [
      'blender/lib/ exists with a README documenting a reusable API used by the stall scripts',
      'stall_gluehwein/bratwurst/bier/buecher.glb and .lite.glb exist and are within budget',
      'Each section stall has a visibly distinct character matching its brief in its preview render',
      'Each stall glb contains slot_counter, slot_shelf_1, slot_shelf_2, slot_vendor, slot_sign, slot_front, light_*, bulbs_*, snow_*, cam_view and cam_target (verify by listing node names)',
      'The counter top is 1.05 m high',
      'Signs carry correctly spelled German text',
      '9 deco_<key>.glb files exist with signs and share textures, and each is within the deco budget',
      'Wood shows plank-level variation, wear and bevels, not flat single-colour boxes',
      'The previews are clearly more detailed than the prototype stalls and at least match the gluehwein reference render',
      'NOTES.md lists triangle counts, file sizes and open issues',
    ],
  },
  vendor: {
    title: 'vendor (brewer, Glühwein maker, cook, bookseller and goods dresser)',
    brief: `You own everything on and behind the counters: props in blender/props/, exported to site/public/models/prop_*.glb (+ .lite.glb). The engine places prop sets at a stall's slot_ empties, so author each set with its origin at the slot it belongs to, and document which slot in NOTES.md and in a machine-readable site/public/models/props.json ({set: {slot, stall}}). Counter depth is about 0.5 m and counter width 2.4–3.6 m.
- prop_gluehwein_counter: a copper pot with a ladle and a lid node act_pot_lid, and at least 8 glazed ceramic Glühwein mugs (boot-shaped and classic) as act_mug_0..n, some with steam-ready rims.
- prop_gluehwein_shelf: bottles, spice jars, orange slices and cinnamon.
- prop_bier_counter: a three-tap tower with tap handles act_tap_0..2 that pivot at their base, drip tray and a row of pint and Maß glasses (act_glass_0..n) with a separate foam mesh on each.
- prop_bier_back: wooden barrels on a rack, a chalkboard price board.
- prop_wurst_counter: a round swinging charcoal grill (act_grill) with glowing coals (emissive coal_glow material), sausages act_sausage_0..n, a stack of rolls, mustard and ketchup pots, paper trays.
- prop_books_shelf_1 and prop_books_shelf_2: shelves full of individual books with varied sizes, colours, wear and spine lettering. Mac's 55 real books live in the category sets described under 'Bücherstand categories' in docs/BUILD.md; content/books/categories.json is the only source for titles, and these two shelves hold untitled filler.
- prop_gluehwein_wine: a small wine shelf for the Glühwein stand (slot_shelf_2) with 8–12 individual bottles act_bottle_0..n: German reds and whites (Riesling, Spätburgunder, Dornfelder, Silvaner), each with its own legible label, capsule and glass colour. Include a few wine glasses act_wineglass_0..n.\n- Every item a visitor might click must be its own node with its pivot at its base and a sensible bounding box, and must be clickable on its own: each book, mug, glass, bottle, sausage and roll. Books need a readable title on the spine and a front cover the engine can show when a book is opened (name the cover material book_cover_<n>). Write site/public/models/items.json that maps every act_ node to its display name (for books: title and author).\n- prop_books_counter: open books, a reading lamp with a light_ empty, a cash box.
- For each of the 9 deco stalls, prop_deco_<key>: the goods, e.g. hanging Lebkuchen hearts with icing, paper cones of almonds, candles of many colours and sizes, wooden toys, glass baubles, wheels of cheese, a crêpe griddle, a chestnut roaster, a potato-pancake pan.
Previews: one close-up Cycles render per section set on a plain wooden counter at night, and one contact sheet of the deco goods.`,
    checks: [
      'site/public/models/props.json exists and maps every prop set to a stall and slot',
      'All section prop sets and 9 prop_deco_<key> sets exist with .lite.glb versions',
      'Glühwein mugs are act_mug_*, tap handles act_tap_0..2 pivot at their base, sausages act_sausage_*, grill act_grill, books act_book_* (verify node names and pivot origins)',
      'Book spines from content/books/categories.json are legible in a close-up preview',
      'Prop sets fit a 0.5 m deep counter and 1.05 m counter height (check bounding boxes)',
      'Close-ups show believable materials: glazed ceramic, copper, glass with foam, charred sausages, worn book cloth',
      'Total prop triangles fit inside the section stall budget when combined with each stall',
      'NOTES.md lists triangle counts, file sizes and open issues',
    ],
  },
  rides: {
    title: 'ride builder (Ferris wheel, carousel, bandstand and instruments)',
    brief: `You own the landmarks, built in blender/rides/ and exported to site/public/models/ with .lite.glb versions:
- ferris.glb (Riesenrad, about 26 m tall): a steel lattice wheel with spokes, hub and A-frame legs as rot_wheel, 16 enclosed gondolas gondola_0..15 (painted, with little windows and roofs; each pivots at its hanging point), rim bulbs_ lights and a ticket booth at its base. Give it cam_view/cam_target and a gondola_seat_ empty inside gondola_0 for the ride camera.
- carousel.glb (Karussell): a classic two-tier carousel with a painted rounding board with mirrors and bulbs, a striped canopy, a centre column, 12 carved horses horse_0..11 on brass poles (each with its own node for up/down motion), benches and an outer rail. rot_platform carries the horses. Give it cam_view/cam_target and a horse_seat_ empty on horse_2.
- bandstand.glb: an octagonal wooden or cast-iron bandstand with a roof, railings, garlands, bulbs_, light_ empties for a stage wash, and marks slot_sax, slot_piano, slot_bass, slot_drums where the organizer's musicians stand or sit.
- Instruments as separate files so they can be placed and animated: instr_sax (a tenor saxophone with keys), instr_piano (an upright piano), instr_bass (a double bass with bow and stand) and instr_drums (a small jazz kit with brushes). Each is placed by the engine at the bandstand slots.
Previews: one Cycles night render each for the Ferris wheel, carousel and bandstand with instruments.`,
    checks: [
      'ferris, carousel, bandstand and the four instr_* glbs plus .lite.glb versions exist within budget',
      'The Ferris wheel has rot_wheel and 16 gondola_* nodes with pivots at the hanging point',
      'The carousel has rot_platform and 12 horse_* nodes on poles',
      'The bandstand has slot_sax, slot_piano, slot_bass and slot_drums',
      'Rides and bandstand have cam_view and cam_target, and the rides have seat empties',
      'The instruments are recognisable at close range (sax keys, piano keys, bass f-holes and strings, drums with cymbals)',
      'The previews read as a real fairground at night, with lit bulbs and believable steel, paint and wood',
      'NOTES.md lists triangle counts, file sizes and open issues',
    ],
  },
  organizer: {
    title: 'organizer (people, crowd and choreography)',
    brief: `You own the people. The crowd is what makes the market feel alive.
- Figures: people_*.glb in site/public/models/ (with .lite.glb), made in blender/people/ or adapted from a CC0 source (Quaternius and Kenney are good places to look; verify the licence and credit it).
  - Use realistic-miniature proportions: adults and a few children in winter clothes (long coats, scarves, knit hats, gloves).
  - Provide at least 6 base figures, with material variations the engine can recolour (coat, scarf, hat colours as separate materials named coat, scarf, hat).
  - Skinned animations: walk, idle, chat (gestures), drink (raise mug), laugh, and sit.
  - Keep each figure within budget.
- Musicians: a tenor saxophonist, a pianist, a bassist and a drummer with brushes (people_band_*.glb), each with a slow, loopable playing animation. The instruments come from the ride builder; make hands meet the instruments at the bandstand slots.
- Vendors: a vendor figure per section stall with a serving or idle animation, standing at slot_vendor.
- site/src/crowd.json: groups of 2–5 people chatting near the stalls and the tree; walkers on paths through the lanes; people queueing at the Glühwein and Bier stands; a couple on a bench; kids near the carousel; vendors and musicians. It references figure files and animation names and uses layout.json coordinates (read site/src/layout.json if the architect has written it, otherwise BUILD.md).
Previews: a Cycles line-up of all figures, the band posed together, and a small group chatting.`,
    checks: [
      'At least 6 people_*.glb base figures plus 4 people_band_* and vendor figures exist within budget, with .lite.glb versions',
      'Each figure has skinned animations named walk, idle, chat, drink (verify with gltf-transform inspect)',
      'Figures have separate coat, scarf and hat materials for recolouring',
      'Figures read as realistic-miniature people in winter clothes, not capsules or blobs, in the line-up preview',
      'site/src/crowd.json exists, parses, and places groups, walkers, queues, vendors and musicians',
      'Third-party figures, if any, are credited in CREDITS.md with a licence that allows a public website',
      'NOTES.md lists triangle counts, file sizes and open issues',
    ],
  },
  engineer: {
    title: 'front-end engineer',
    brief: `You own the site in site/ (except layout.json, crowd.json, lighting/, public/models and public/audio) plus .github/workflows/.
Build a Vite + three.js (current npm version) app that:
- reads site/src/layout.json, loads each glb with GLTFLoader and MeshoptDecoder, and places it. When a glb or layout.json is missing, it falls back to a labelled placeholder box and the BUILD.md layout, so the site always runs while other roles work;
- uses the node conventions in BUILD.md: bulbs_ glow, light_ becomes real-time lights (capped by budget), snow_ toggles with the snow button, slot_ places prop sets from site/public/models/props.json, cam_view/cam_target drive flyTo, rot_ spins, gondola_/horse_ animate, act_ nodes drive the actions;
- ports every interaction from prototype/index.html. That covers:
  - hover outline, clicking stalls and landmarks, the panel with its action buttons;
  - pour a mug, pull a pint, Prost, turn the sausages, a sausage in a bun, pull a book, feature a band member;
  - the Ferris wheel and carousel rides, the snow toggle and reset view;
  - keyboard navigation and reduced motion;
- builds panel content from content/*.md at build time. Read the writer's files if they exist and fall back to the prototype text;
- loads the lighting from site/src/lighting/index.js. The interface is: export function createLighting({scene, renderer, camera, lite}) returning {composer, update(dt, t), setSnow(on), dispose()}. Write a minimal stand-in at site/src/lighting-fallback.js and use it if the lighting module is missing or throws;
- plays the band from stems listed in site/public/audio/manifest.json ({bpm, duration, loopStart, loopEnd, stems:{sax,piano,bass,drums,room}: url}), in sync, spatialised at the bandstand, with featuring. Fall back to prototype/audio.js if the manifest is missing. Stall SFX stay synthesised as in the prototype;
- detects phones and weak GPUs and serves the lite market (*.lite.glb, no shadows, fewer lights) with a toggle;
- ships plain.html, a fast accessible text version of all content linked from the 3D page;
- deploys to GitHub Pages with .github/workflows/pages.yml (npm ci, build, upload, deploy). Set Vite base for a project page at /website/.
Verify with npm run build and a Playwright run (software GL is slow; allow long timeouts). Take screenshots of the home view, one stall panel, and plain.html with no console errors. Put the screenshots in review/round-${ROUND}/engineer/.`,
    checks: [
      'npm ci && npm run build succeeds in site/ (run it)',
      'The Playwright run loads the page with no console errors, and screenshots exist in the review folder',
      'Missing glbs fall back to placeholders without errors',
      'All prototype interactions are present: each action button, both rides, snow toggle, reset, keyboard access and reduced motion (check the code)',
      'Content panels are built from content/*.md with a fallback',
      'Audio plays from the stems manifest with a fallback to prototype/audio.js, and featuring works (check the code)',
      'The lite market path exists and is selected on phones or weak GPUs',
      'plain.html contains all section content and is linked from the 3D page',
      '.github/workflows/pages.yml builds and deploys to Pages, and the Vite base is /website/',
      'The code is organised into modules rather than one giant file',
    ],
  },
  lighting: {
    title: 'lighting and atmosphere designer',
    brief: `You own site/src/lighting/: the night itself. Implement export function createLighting({scene, renderer, camera, lite}) returning {composer, update(dt, t), setSnow(on), dispose()} in site/src/lighting/index.js, using three from npm (the engineer sets up site/package.json; if it is not there yet, create site/src/lighting/package.json for your own testing only).
It covers:
- a deep blue night sky with a gradient, stars and a soft-haloed moon;
- a moonlight directional light with good soft shadows, hemisphere fill and exponential fog with the right blue;
- a PMREM environment map for reflections on wet cobbles, glass and copper;
- tone mapping (choose AgX or ACES and justify it) and colour management;
- bloom tuned so bulbs_ (bulb_warm/bulb_cold) and window_warm glow without washing out the scene;
- helpers the engine calls to turn light_ empties into warm point or spot lights within a budget, with a lite profile;
- snow: falling flakes with depth and wind drift, and setSnow toggling them.
Build a test page at site/src/lighting/test.html. It loads review/reference/gluehwein_stall_web.glb (a Blender-built test stall) on a plain ground plane. Tune until a Playwright screenshot approaches the Cycles reference review/reference/gluehwein_preview.png in mood: warm interior, cool night, readable wood. Save before/after screenshots and a side-by-side against the reference in review/round-${ROUND}/lighting/. Write docs of your settings in site/src/lighting/README.md.`,
    checks: [
      'site/src/lighting/index.js exports createLighting with the agreed return shape',
      'The test page renders the reference stall, and screenshots exist in the review folder',
      'The side-by-side shows warm interior light, cool moonlit surroundings and readable wood grain, approaching the Cycles reference mood',
      'Bulbs bloom softly without washing out the image',
      'The sky has stars and a moon, and fog is present',
      'Snow toggles through setSnow and has depth and drift',
      'A lite profile exists with fewer lights and no shadows',
      'README.md documents the tone mapping choice and key settings',
    ],
  },
  music: {
    title: 'music writer and mix engineer',
    brief: `You own music/ (sources, scores, render scripts) and site/public/audio/.
Write and produce an ORIGINAL jazz ballad for the bandstand quartet: tenor sax, piano, double bass and drums played with brushes. Mac wants it "slow, sad, yet warm". The tenor sound he wants is a soft, low subtone: warm, breathy, smoky, like Ben Webster or Stan Getz at a whisper. He found earlier versions too harsh.
Musical brief:
- 56–66 bpm, in a minor key with warm major moments;
- a 32-bar AABA or ABAC song form. Play the head, then an improvised-sounding sax chorus with space, then a piano half-chorus, then the out head with a rubato ending;
- 3 to 4.5 minutes;
- real ballad harmony: ii-V-i motion, tritone substitutions, voice-led rootless piano voicings, walking or two-feel bass, brush sweeps with feathered kick;
- human timing: laid-back sax phrasing, dynamics and swing appropriate to a ballad.
Production:
- Find the best freely licensed samples you can reach. Try GitHub and PyPI (for example sfzinstruments on GitHub, the Salamander piano and MusyngKite / FluidR3 via gleitz/midi-js-soundfonts). Check each licence and credit it.
- Render offline in Python (numpy/scipy; write your own sampler if needed). Give the sax slow attacks, a breath-noise layer, gentle vibrato and a dark EQ. Put the instruments in a room with convolution or algorithmic reverb, and add gentle bus compression.
- Export sample-aligned stems sax, piano, bass, drums and a room (reverb return), each as .mp3 at 128–160 kbps (lameenc from pip is fine), plus site/public/audio/manifest.json: {bpm, duration, loopStart, loopEnd, stems:{sax,piano,bass,drums,room}: url}.
- Also export a full stereo mix preview in music/out/ (not shipped).
Measure and report: tempo, key, duration, sax spectral centroid (target below 900 Hz), peak level (below -1 dBFS), integrated loudness of the mix (about -18 LUFS) and loop seam smoothness. Put a spectrogram PNG of the sax stem and of the mix in review/round-${ROUND}/music/.`,
    checks: [
      'site/public/audio/manifest.json exists and lists five stem files that exist and are sample-aligned (equal duration)',
      'Tempo is 56–66 bpm, and the piece is 3 to 4.5 minutes in a song form described in the score or notes',
      'The harmony uses ii-V-i motion and rootless or voice-led piano voicings (check the source score or MIDI)',
      'The sax stem spectral centroid is below 900 Hz (re-measure it with a short Python script)',
      'The mix peak is below -1 dBFS and loudness is near -18 LUFS (re-measure)',
      'The sax has slow attacks, breath noise and vibrato in its rendering code',
      'The samples used have licences that allow a public website and are credited in CREDITS.md',
      'The composition is original, not a transcription of a copyrighted song',
      'NOTES.md reports the measurements and open issues',
    ],
  },
  writer: {
    title: 'writer',
    brief: `You own content/: one Markdown file per section.
The files are: about.md (Glühwein), projects.md (Bierstand), writing.md (Bratwurst), reading.md (Bücherstand), music.md (Bandstand), questions.md (Riesenrad) and contact.md (Karussell). Also write site.md with the page title, tagline, meta description and the text for the plain version's intro.
Each file has YAML front matter: section, stall (German name), title and actions (the action button labels, matching the prototype: e.g. "Pour a mug", "Pull a pint", "Prost!", "Turn the sausages", "One in a bun", "Pull a book", the band members, "Ride the wheel", "Ride the carousel").
Source material:
- the prototype's text in prototype/index.html (PLACES);
- what is known about Mac: a physician at Chulalongkorn University in Bangkok who builds software for clinical research; projects ProtoCol (a chatbot for writing study protocols and working out sample size), a Target Trial Emulation course with YouTube lessons, and a transfusion audit system; INTJ; loves jazz (ballads), physics, philosophy, the brain, Christmas markets, beer and wine; GitHub macsermkiat.
Keep each stall's flavour: the beer menu metaphor for projects, the grill for writing, the bookshop shelf for reading, the view from the top for big questions.
Voice: Mac prefers plain, direct prose without flourish. Write in the first person as Mac, in short sentences. Use the agent-skills humanize or no-ai-slop skill to check your drafts.
Mark every factual claim about Mac that is not in the source material with <!-- check -->. Don't invent credentials, dates, employers or publications. Use clearly marked placeholders where Mac must supply facts. Keep the stall-specific action notes the prototype shows (e.g. "Pouring… tilt, fill, then top it off with foam.") as a short 'notes' map in front matter.`,
    checks: [
      'All 8 content files exist with valid front matter including actions',
      'Nothing about Mac is invented without a check marker or placeholder',
      'The prose is plain and direct, with no marketing tone, filler or em-dash chains (read it)',
      "Each section keeps its stall's metaphor lightly, without forcing it",
      'There is no lab, pathology or clinical imagery used as decoration',
      'The Reading list includes the five prototype titles, and projects cover ProtoCol, Target Trial Emulation and the transfusion audit',
    ],
  },
}

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'What you built, in a few sentences' },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' }, description: 'Paths of preview images' },
    budgets: { type: 'string', description: 'Triangle counts and file sizes' },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files', 'previews', 'open_issues'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: { check: { type: 'string' }, pass: { type: 'boolean' }, evidence: { type: 'string' } },
        required: ['check', 'pass', 'evidence'],
      },
    },
    verdict: { type: 'string', enum: ['Ship', 'Improve', 'Rework'] },
    fixes: { type: 'array', items: { type: 'string' }, description: 'Concrete fixes in priority order; empty only for Ship' },
  },
  required: ['checks', 'verdict', 'fixes'],
}

const EXTRA = args.extra || {}
const EXTRA_CHECKS = args.extraChecks || {}
for (const k of Object.keys(EXTRA_CHECKS)) if (ROLES[k]) ROLES[k].checks = ROLES[k].checks.concat(EXTRA_CHECKS[k])
for (const k of Object.keys(EXTRA)) if (ROLES[k]) ROLES[k].brief = ROLES[k].brief + `\n\nROUND ${ROUND} PRIORITIES (these come first):\n` + EXTRA[k]

function buildPrompt(key, pass, prev, fixes) {
  const r = ROLES[key]
  let p = `${COMMON}\n\nYour role: ${r.title} (role folder name: ${key}).\n\n${r.brief}\n\nThe judges will check:\n- ${r.checks.join('\n- ')}`
  if (pass === 1 && args.priorRound) p += `\n\nThis is round ${ROUND}. Your work from round ${args.priorRound} is on disk. Read review/round-${args.priorRound}/${key}/NOTES.md and JUDGES.md (the Opus and Fable judges' last verdicts), and review/round-${args.priorRound}/CODEX_JUDGE.md (the Codex judge on the whole market). Fix every open point that concerns your role, as well as the round ${ROUND} priorities.`
  if (pass > 1) {
    p += `\n\nThis is pass ${pass}. Your previous pass returned:\n${JSON.stringify(prev)}\n\nThe judging panel asked for these fixes (in priority order). Make all of them, re-render the previews, and update NOTES.md:\n- ${fixes.join('\n- ')}`
  }
  return p
}

function judgePrompt(key, built) {
  const r = ROLES[key]
  return `You are on the judging panel for Mac's 3D Nachtmarkt website (repo ${REPO}). Read ${REPO}/docs/BUILD.md for the contract. You are judging the work of the ${r.title}, round ${ROUND}. The builder reports:\n${JSON.stringify(built)}\n\nThe brief they were given:\n${r.brief}\n\nJudge strictly and independently, but economically: check what the checks need and no more. Evidence must come from the files themselves:
- open the preview images with the Read tool and look at them;
- run commands (e.g. gltf-transform inspect, node or python one-liners, npm run build) to verify counts, names, sizes and behaviour;
- read the code or source.
Don't trust the builder's claims. The quality bar is a "realistic miniature" that is clearly more detailed and crafted than the prototype (prototype/index.html). Answer each check with pass true or false and one line of evidence:
- ${r.checks.join('\n- ')}

Add any further checks you find necessary. Then give one holistic verdict:
- Ship: good enough for the real site now;
- Improve: close, with specific fixes;
- Rework: the approach is wrong.

Don't average the checks: one serious failure can decide the verdict alone. List concrete fixes in priority order. Don't edit any files.`
}


// ---- Dynamic model/effort selection (args.dynamic) ----
const DYNAMIC = !!args.dynamic
const WRITING_ROLES = new Set(args.writingRoles || ['writer'])
const TIERS = {
  light: { model: 'sonnet', effort: 'low' },
  standard: { model: null, effort: 'medium' },   // null = session model (Opus 5.5)
  heavy: { model: null, effort: 'high' },
}
const TRIAGE_SCHEMA = {
  type: 'object',
  properties: { tier: { type: 'string', enum: ['light', 'standard', 'heavy'] }, reason: { type: 'string' } },
  required: ['tier', 'reason'],
}
async function builderOpts(key, pass, fixes) {
  const fixed = (args.builderModel || {})[key] ? { model: args.builderModel[key] } : {}
  if (!DYNAMIC) return { opts: { effort: (args.builderEffort || {})[key] || 'high', ...fixed } }
  const r = ROLES[key]
  const t = await agent(`Classify how demanding this next work pass is, so the right model and effort can be chosen. Don't open any files; judge from the text below.
Role: ${r.title}. Pass ${pass} of round ${ROUND}.
Fixes and priorities for this pass:
- ${(fixes && fixes.length ? fixes : [r.brief.slice(-2500)]).join('\n- ')}

Tiers:
- light: small, local edits (text tweaks, renames, a parameter or colour change, re-export, notes cleanup) with no new modelling, no new code paths and no visual judgement.
- standard: several fixes or moderate new code or modelling, where the approach is clear.
- heavy: new systems or geometry, cross-cutting refactors, hard visual quality work, or anything whose approach is unclear.
Pick the lowest tier that will do the job well.`, { label: `triage · ${key} · ${pass}`, phase: 'Build', schema: TRIAGE_SCHEMA, model: 'sonnet', effort: 'low' })
  let tier = (t && t.tier) || 'standard'
  if ((args.minTier || {})[key] === 'standard' && tier === 'light') tier = 'standard'
  if ((args.minTier || {})[key] === 'heavy') tier = 'heavy'
  const o = { ...TIERS[tier] }
  if (WRITING_ROLES.has(key)) { o.model = 'sonnet'; if (o.effort === 'high') o.effort = 'medium' }   // Mac: writing runs on Sonnet
  if (fixed.model) o.model = fixed.model
  const opts = { effort: o.effort, ...(o.model ? { model: o.model } : {}) }
  log(`${key} pass ${pass}: ${tier} → ${o.model || 'opus'} / ${o.effort}${t ? ' (' + t.reason.slice(0, 80) + ')' : ''}`)
  return { tier, opts }
}

const results = await pipeline(args.roles, async (key) => {
  let pass = START, built = null, fixes = [], history = []
  if (START > 1) { built = { summary: `Pass ${START - 1} was done earlier. Read review/round-${ROUND}/${key}/NOTES.md for what was built, and the current files.` }; fixes = [`Read review/round-${ROUND}/${key}/JUDGES.md (the Opus and Fable judges) and review/round-${ROUND}/CODEX_JUDGE.md (the Codex judge, whole market), and fix everything that concerns your role. The files on disk may hold a partly finished earlier pass; continue from them.`] }
  while (pass < START + MAX_PASSES) {
    const bopts = await builderOpts(key, pass, fixes)
    built = await agent(buildPrompt(key, pass, built, fixes), { label: `${key} · pass ${pass}${bopts.tier ? ' · ' + bopts.tier : ''}`, phase: 'Build', schema: BUILD_SCHEMA, ...bopts.opts })
    if (!built) { history.push({ pass, error: 'builder failed' }); break }
    let verdicts
    if (DYNAMIC) {
      // Staged panel: Opus judges first; Fable is only spent to confirm a Ship.
      const first = await agent(judgePrompt(key, built), { label: `judge opus · ${key} · ${pass}`, phase: 'Judge', schema: VERDICT_SCHEMA, effort: args.judgeEffort || 'low' })
      verdicts = [first].filter(Boolean)
      if (first && first.verdict === 'Ship') {
        const second = await agent(judgePrompt(key, built), { label: `judge fable · ${key} · ${pass}`, phase: 'Judge', schema: VERDICT_SCHEMA, model: 'fable', effort: args.judgeEffort || 'low' })
        if (second) verdicts.push(second)
      }
    } else {
      verdicts = (await parallel([
        () => agent(judgePrompt(key, built), { label: `judge opus · ${key} · ${pass}`, phase: 'Judge', schema: VERDICT_SCHEMA, effort: args.judgeEffort || 'high' }),
        () => agent(judgePrompt(key, built), { label: `judge fable · ${key} · ${pass}`, phase: 'Judge', schema: VERDICT_SCHEMA, model: 'fable', effort: args.judgeEffort || 'high' }),
      ])).filter(Boolean)
    }
    history.push({ pass, built, verdicts: verdicts.map(v => ({ verdict: v.verdict, failed: v.checks.filter(c => !c.pass), fixes: v.fixes })) })
    log(`${key} pass ${pass}: ${verdicts.map(v => v.verdict).join(' / ')}`)
    if (verdicts.length && verdicts.every(v => v.verdict === 'Ship')) break
    const seen = new Set()
    fixes = verdicts.flatMap(v => v.fixes).filter(f => { const k = f.toLowerCase().slice(0, 80); if (seen.has(k)) return false; seen.add(k); return true })
    pass++
  }
  const last = history[history.length - 1]
  return { role: key, passes: history.length, final: last && last.verdicts ? last.verdicts.map(v => v.verdict) : ['none'], history }
})

return results
