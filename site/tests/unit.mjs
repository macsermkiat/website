// Unit checks that need no browser: the GPU classes behind the lite-market choice, the ballad's road map, the
// strict content gate, the asset credits and the download budgets.
// Usage: node tests/unit.mjs
import { readFileSync, existsSync } from 'node:fs';
import { gpuTier, detectLite } from '../src/quality.js';
import { songPlan } from '../src/audio/songplan.js';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { contentGate, contentMarkers, assetCredits, buildLibrary, libraryHtml, bookFragment, libraryPagesHtml, buildContent, setNotesMode, normTitle } from '../plugins/market.js';
import { mkdirSync, readdirSync } from 'node:fs';
import { readGlb, budget } from '../scripts/budget.mjs';

let failed = 0;
const check = (name, ok, detail = '') => { if (!ok) failed++; console.log(ok ? '  ok  ' : '  FAIL', name, detail ? `(${detail})` : ''); };

// ---------- GPU classes ----------
const GPUS = [
  ['ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)', 'software'],
  ['llvmpipe (LLVM 15.0.7, 256 bits)', 'software'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00005917) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) UHD Graphics (0x00009A78) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x00009A49) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel Inc., Intel(R) Iris(TM) Plus Graphics 655, OpenGL 4.1)', 'integrated'],
  ['Mesa Intel(R) UHD Graphics 620 (KBL GT2)', 'integrated'],
  ['Mesa Intel(R) Xe Graphics (TGL GT2)', 'integrated'],
  ['ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001638) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)', 'integrated'],
  ['Apple GPU', 'integrated'],
  ['ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)', 'discrete'],
  ['ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'discrete'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)', 'discrete'],
  ['ANGLE (Intel, Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['ANGLE (Intel, Intel(R) HD Graphics 520 (0x00001916) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['Intel HD Graphics 5000', 'weak'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 600 (0x00003185) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['Mesa Intel(R) UHD Graphics 605 (GLK 3)', 'weak'],
  ['Mali-T860', 'weak'],
  ['Mali-G52', 'weak'],
  ['Mali-G78', 'integrated'],
  ['Adreno (TM) 506', 'weak'],
  ['Adreno (TM) 660', 'integrated'],
  ['PowerVR Rogue GE8320', 'weak'],
];
for (const [r, want] of GPUS) check(`GPU class: ${r.slice(0, 70)}`, gpuTier(r) === want, `${gpuTier(r)} (want ${want})`);
const env = (ua, extra = {}) => ({ navigator: { userAgent: ua, deviceMemory: 8, hardwareConcurrency: 8, ...extra }, matchMedia: () => ({ matches: /iPhone|Android/.test(ua) }), screen: { width: /iPhone|Android/.test(ua) ? 390 : 1920, height: 844 } });
const desk = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36';
check('a UHD 620 laptop starts on the lite market (built-in GPU)', detectLite({ renderer: GPUS[2][0], maxTex: 16384 }, env(desk)).lite === true);
check('an Iris Xe laptop starts on the lite market (built-in GPU)', detectLite({ renderer: GPUS[5][0], maxTex: 16384 }, env(desk)).lite === true);
check('an Apple M3 MacBook Air starts on the lite market (measured: full ran at 1-5 fps)', detectLite({ renderer: 'ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)', maxTex: 16384 }, env(desk)).lite === true);
check('a desktop with a discrete GPU gets the full market', detectLite({ renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)', maxTex: 16384 }, env(desk)).lite === false);
check('an HD 4000 laptop gets the lite market', detectLite({ renderer: GPUS[15][0], maxTex: 16384 }, env(desk)).lite === true);
check('a phone gets the lite market', detectLite({ renderer: 'Apple GPU', maxTex: 16384 }, env('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148 Safari/604.1')).lite === true);
check('a 4 GB laptop gets the lite market', detectLite({ renderer: GPUS[2][0], maxTex: 16384 }, env(desk, { deviceMemory: 4 })).lite === true);

// ---------- the ballad's road map ----------
const manifest = JSON.parse(readFileSync(new URL('../public/audio/manifest.json', import.meta.url)));
const plan = songPlan(manifest, { fileEnd: manifest.decodedDuration });
const road = [];
for (let s = plan.segment(0, 1); s; s = plan.next(s)) road.push(s);
check('the head runs into the loop', road[0].from === 0 && Math.abs(road[0].to - manifest.loopEnd) < 1e-6);
check(`the loop plays ${plan.passes} passes`, Math.max(...road.map((s) => s.pass)) === plan.passes);
check('the last stretch is the written ending, past loopEnd to the fermata', Math.abs(road.at(-1).from - manifest.loopEnd) < 1e-6 && road.at(-1).to > manifest.ending.fermata, JSON.stringify(road.at(-1)));
if (manifest.alternates?.length) {
  const alt = road.filter((s) => s.alt);
  check('pass 2 plays the second tenor chorus from the alternates', alt.length === 1 && alt[0].pass === 2 && alt[0].from > manifest.alternates[0].start && alt[0].to < manifest.alternates[0].end, JSON.stringify(alt));
  check('pass 1 and pass 3 play the main chorus', !road.some((s) => s.alt && s.pass !== 2));
}
check('segments join up with no gap', road.every((s, i) => i === 0 || Math.abs(road[i - 1].to - s.from) < 1e-6 || (Math.abs(road[i - 1].to - plan.loopEnd) < 1e-6 && (Math.abs(s.from - plan.loopStart) < 1e-6 || Math.abs(s.from - plan.loopEnd) < 1e-6))));
check('the song is about ten minutes before it rests and starts again', plan.length > 480 && plan.length < 720, `${plan.length.toFixed(0)} s`);

// ---------- content gate, credits, budgets ----------
{
  const dir = mkdtempSync(path.join(tmpdir(), 'nm-content-'));
  writeFileSync(path.join(dir, 'a.md'), 'A line. <!-- check -->\n\nAnother [check: the year].\n');
  writeFileSync(path.join(dir, 'b.md'), 'All confirmed.\n');
  const g = contentGate(dir);
  check('the strict content gate counts <!-- check --> comments and [check] tags', g.left.length === 1 && g.left[0].checks === 2 && /check marker/.test(g.message), g.message);
  mkdirSync(path.join(dir, 'books'));
  writeFileSync(path.join(dir, 'books', 'chaos.md'), '---\ntitle: "Chaos"\nauthor: "James Gleick"\none_line: "Order in disorder."\nreview: "check"\n---\n\n## In short\n\nText.\n');
  writeFileSync(path.join(dir, 'books', 'categories.json'), JSON.stringify({ categories: [{ key: 'physics', label_en: 'Physics', label_de: 'Physik & Kosmos', books: [{ title: 'Chaos', author: 'James Gleick', slug: 'chaos' }, { title: 'Grit', author: 'Angela Duckworth', slug: 'grit' }] }] }));
  const g2 = contentGate(dir);
  check('the strict content gate counts a book page still marked review: check', g2.left.some((l) => l.file === 'books/chaos.md' && l.checks === 1), g2.message);
  const mk = contentMarkers(dir);
  check('npm run content:check lists each marker the gate counts, with its line', mk.length === 3 && mk.filter((m) => m.file === 'a.md').map((m) => m.line).join(',') === '1,3' && mk.some((m) => m.kind === 'review' && m.file === 'books/chaos.md' && m.line === 5), JSON.stringify(mk));
  const lib = buildLibrary(dir);
  check('Mac\'s bookshelf comes from categories.json, with the one-line summary where the writer has one', lib.books.length === 2 && lib.books[0].oneLine === 'Order in disorder.' && lib.books[0].category === 'physics' && lib.books[1].oneLine === '' && !lib.books[1].page, JSON.stringify(lib.books));
  check('Mac\'s bookshelf renders as a list whose titles link to their reading pages', /<details class="library"[\s\S]*<a href="plain\.html#book-chaos" data-book="chaos"><em>Chaos<\/em><\/a> · James Gleick\. <span class="one-line">Order in disorder\.<\/span>/.test(libraryHtml(lib)) && /<em>Grit<\/em> · Angela/.test(libraryHtml(lib)));
  check('the bookshelf\'s groupings are named in English only (label_en; label_de stays in the data)', /<h4>Physics<\/h4>/.test(libraryHtml(lib)) && /<h3 class="bookcat">Physics<\/h3>/.test(libraryPagesHtml(lib)) && !/Physik/.test(libraryHtml(lib) + libraryPagesHtml(lib)) && lib.books[0].categoryLabel === 'Physics' && lib.categories[0].labelDe === 'Physik & Kosmos', JSON.stringify(lib.categories[0].label));
  check('a book\'s reading page is its markdown body under the title (In short as an h3)', /<h3>In short<\/h3>\s*<p>Text\.<\/p>/.test(bookFragment(lib, 'chaos')) && bookFragment(lib, 'grit') === '');
  check('the text page carries every book\'s reading page with an anchor', /<article class="bookpage" id="book-chaos"[\s\S]*<h5>In short<\/h5>/.test(libraryPagesHtml(lib)));
  check('no categories file: an empty library, no error', buildLibrary(path.join(dir, 'nowhere')).books.length === 0);
  const credits = assetCredits();
  check('asset credits from CREDITS.md carry source URLs and licences', /<details class="credits-all"/.test(credits) && /href="https:\/\/github\.com\/mrdoob\/three\.js"/.test(credits) && /MIT/.test(credits));
  // the Bücherstand's unconfirmed front-matter list is never written into the panel or the text page, and a
  // notes-hidden build keeps only the 3D shelf's books that are on Mac's own shelf
  setNotesMode('hide');
  const built = buildContent();
  const mine = new Set(built.library.books.map((x) => normTitle(x.title)));
  const shelf = built.sections.books?.meta?.books || [];
  check('production content: the unconfirmed book list is not reinstated in the bookshop panel', !/On the shelf in the market/.test(built.sections.books?.html || ''));
  check('production content: the 3D shelf keeps only books on Mac\'s own shelf', shelf.every((x) => mine.has(normTitle(typeof x === 'string' ? x : x.title))), shelf.map((x) => x.title || x).join(', '));
  check('production content: all 55 books from categories.json, each with its reading page', built.library.books.length === 55 && built.library.books.every((x) => x.page && built.library.pages[x.slug]), `${built.library.books.length} books, ${built.library.books.filter((x) => !x.page).map((x) => x.slug).join(' ')} without a page`);
  setNotesMode('show');
  const b = budget();
  const glb = readGlb(new URL('../public/models/deco_lebkuchen.glb', import.meta.url).pathname);
  const leb = b.rows.find((r) => r.id === 'deco-lebkuchen');
  check('budget: a glb\'s external textures are counted with it', glb.images.length > 0 && leb.full.textures + leb.full.sharedTextures > 0, glb.images.join(' '));
  // the deco kit's textures are shared by nine stalls: charged once (the shared row), not to each stall
  const kit = b.shared.find((s) => /deco_kit_wood_color/.test(s.file));
  check('budget: a texture several assets share is charged once', !!kit && kit.users.length > 1 && leb.full.sharedTextures > 0, kit ? `${kit.file}: ${kit.users.length} users` : 'no shared kit texture');
  check('budget: deferred assets and the crowd\'s distance level are counted', b.totals.full.deferred > 0 && b.totals.full.everything === b.totals.full.firstLoad + b.totals.full.deferred + b.totals.full.onDemand, JSON.stringify(b.totals.full));
  // round 5: the full market streams detail (lite first, full on demand); both first loads beat round 4's
  check('budget: the full market\'s full-detail stalls are counted on demand, not in the first load', b.totals.full.onDemand > 0 && b.totals.lite.onDemand === 0, JSON.stringify(b.totals));
  check('budget: both first loads are smaller than round 4 (19.70 MB full, 7.44 MB lite)', b.totals.full.firstLoad < 19.7e6 && b.totals.lite.firstLoad < 7.44e6, `${(b.totals.full.firstLoad / 1e6).toFixed(2)} / ${(b.totals.lite.firstLoad / 1e6).toFixed(2)} MB`);
  check('budget: the shared clips (people_anims.glb) are counted', b.rows.some((r) => r.id === 'people_anims'));
  const band = b.rows.find((r) => r.id === 'bandstand'), players = b.rows.filter((r) => /^people_band_/.test(r.id));
  check('budget: the bandstand is charged with its instruments, its four players as person variants', band && players.length === 4 && players.every((r) => r.kind === 'person' && r.budget?.tris === 5000), players.map((r) => r.id).join(' '));
  check('budget: a shared texture is charged to each user in equal parts', leb.full.share > 0 && leb.full.share < leb.full.sharedTextures, `${leb.full.share} of ${leb.full.sharedTextures}`);
  const over = b.rows.filter((r) => r.over && (r.over.tris || r.over.bytes)).map((r) => r.id);
  // a note, not a failure: one role's asset over its budget should not stop Mac's deploy (npm run budget shows OVER)
  console.log(over.length ? `  note  over budget: ${over.join(' ')}` : '  note  every asset is inside its triangle and byte budget');
  const noDist = budget({ dist: '/nonexistent-dist' });
  // (CI runs these checks before the build, so the real dist may not exist yet: b.hasDist must only match the disk)
  check('budget: it reports a missing dist (the CLI then exits 1)', noDist.hasDist === false && b.hasDist === existsSync(new URL('../dist/index.html', import.meta.url)));
  check('budget: both first loads are under their aims', !b.totals.full.over && !b.totals.lite.over, `${(b.totals.full.firstLoad / 1e6).toFixed(2)} / ${(b.totals.lite.firstLoad / 1e6).toFixed(2)} MB`);
  // round 10: the GPU-compressed path (KTX2 twins) is held to the same aims, and grows a first load by about a tenth at most
  if (b.ktx2) {
    const k = b.ktx2;
    const grow = (m) => k[m].firstLoad / b.totals[m].firstLoad - 1;
    check('budget: with KTX2 textures both first loads are under their aims and below round 4', !k.full.over && !k.lite.over && !k.full.grew && !k.lite.grew, `${(k.full.firstLoad / 1e6).toFixed(2)} / ${(k.lite.firstLoad / 1e6).toFixed(2)} MB`);
    // the growth is a share of the whole first load, site code included, so it needs the built site (dist)
    if (b.hasDist) check('budget: KTX2 textures grow neither first load by more than about a tenth (11%)', grow('full') <= 0.11 && grow('lite') <= 0.11, `full ${(grow('full') * 100).toFixed(1)}%, lite ${(grow('lite') * 100).toFixed(1)}%`);
    else console.log('  note  KTX2 growth check skipped: no dist yet (npm run build first; CI runs it after the build)');
  }
}

// ---------- GPU-compressed twins (round 10, scripts/ktx2.mjs) ----------
{
  const MODELS = new URL('../public/models/', import.meta.url);
  const man = existsSync(new URL('ktx2.json', MODELS)) ? JSON.parse(readFileSync(new URL('ktx2.json', MODELS), 'utf8')) : null;
  if (man) {
    const glb = (f) => { const b = readFileSync(new URL(f, MODELS)); const len = b.readUInt32LE(12); return { b, j: JSON.parse(b.subarray(20, 20 + len).toString('utf8')), bin: 20 + len + 8 }; };
    const isKtx2 = (buf) => buf.subarray(0, 12).equals(Buffer.from([0xab, 0x4b, 0x54, 0x58, 0x20, 0x32, 0x30, 0xbb, 0x0d, 0x0a, 0x1a, 0x0a]));
    const bad = [];
    for (const [orig, twin] of Object.entries(man.files || {})) {
      if (!existsSync(new URL(twin, MODELS)) || !existsSync(new URL(orig, MODELS))) { bad.push(`${twin}: missing`); continue; }
      const a = glb(orig), t = glb(twin);
      // the same file apart from the textures: nodes, meshes, accessors, materials, animations, skins
      for (const key of ['nodes', 'meshes', 'accessors', 'materials', 'animations', 'skins', 'samplers']) if (JSON.stringify(a.j[key]) !== JSON.stringify(t.j[key])) bad.push(`${twin}: ${key} differ`);
      (t.j.textures || []).forEach((tex, i) => {
        const k = tex.extensions?.KHR_texture_basisu;
        if (!k) { if (JSON.stringify(tex) !== JSON.stringify(a.j.textures[i])) bad.push(`${twin}: texture ${i} changed`); return; }
        const im = t.j.images[k.source];
        const bv = t.j.bufferViews[im.bufferView];
        if (im.mimeType !== 'image/ktx2' || !bv || !isKtx2(t.b.subarray(t.bin + (bv.byteOffset || 0), t.bin + (bv.byteOffset || 0) + 12))) bad.push(`${twin}: texture ${i} is not KTX2`);
      });
    }
    for (const [uri, side] of Object.entries(man.sidecars || {})) {
      if (!existsSync(new URL(side, MODELS)) || !isKtx2(readFileSync(new URL(side, MODELS)))) bad.push(`${side} (for ${uri}): missing or not KTX2`);
    }
    check('ktx2: every twin is its glb with KTX2 textures in place of webp, and every external .ktx2 is there', !bad.length, bad.slice(0, 5).join('; ') || `${Object.keys(man.files || {}).length} twins, ${Object.keys(man.sidecars || {}).length} external`);
    check('ktx2: the Basis transcoder is in public/basis (the loader reads it from <base>/basis/)', ['basis_transcoder.js', 'basis_transcoder.wasm'].every((f) => existsSync(new URL(`../public/basis/${f}`, import.meta.url))));
  }
}

// ---------- streaming and the stroll ----------
{
  const MODELS = new URL('../public/models/', import.meta.url);
  const nodeNames = (f) => { const b = readFileSync(new URL(f, MODELS)); const len = b.readUInt32LE(12); const j = JSON.parse(b.subarray(20, 20 + len).toString('utf8')); return (j.nodes || []).map((n) => `${n.name || ''}:${n.mesh !== undefined ? 'm' : ''}`); };
  // the stream's graft swaps a lite stall's meshes for the full one's node by node: the two trees must match
  const layoutJson = JSON.parse(readFileSync(new URL('../src/layout.json', import.meta.url), 'utf8'));
  // (the stalls and the bandstand, whose nodes the actions hold; the town's and the tree's full files may add detail
  // nodes, which the graft moves over whole)
  const streamed = layoutJson.places.filter((e) => e.kind === 'section' || /bandstand/.test(e.id));
  const bad = [];
  for (const e of streamed) {
    const f = e.asset, l = f.replace(/\.glb$/, '.lite.glb');
    try { const a = nodeNames(f), c = nodeNames(l); if (a.join('|') !== c.join('|')) bad.push(`${f}: ${a.length} vs ${c.length} nodes`); } catch { /* a missing lite file streams nothing */ }
  }
  check('streaming: each streamed stall\'s lite and full glbs have the same node tree (the graft\'s precondition)', bad.length === 0, bad.join('; '));
  const st = layoutJson.stroll;
  if (st?.legs) {
    const ids = st.order || [];
    const has = (a, b) => st.legs.some((g) => (g.from === a && g.to === b) || (g.from === b && g.to === a));
    const missing = [];
    for (const a of ids) for (const b of ids) if (a < b && !has(a, b)) missing.push(`${a}-${b}`);
    check('stroll: a leg joins every pair of stops (a signpost choice walks straight there)', missing.length === 0, missing.join(' '));
    check('stroll: every stop has an eye and a target, and the Riesenrad its overview', st.stops.every((s) => s.eye?.length === 3 && s.target?.length === 3) && !!st.stops.find((s) => s.id === 'riesenrad')?.overview);
  }
  // in-world text: which writing surfaces the delivered models carry (write_<name>), as world/surfaces.js finds them
  const src = readFileSync(new URL('../src/world/surfaces.js', import.meta.url), 'utf8');
  const names = (f) => nodeNames(f).map((n) => n.replace(/:m?$/, ''));
  const roles = [...src.matchAll(/role: '([a-z_]+)'(?:, aliases: \[([^\]]*)\])?/g)].map((m) => [m[1], ...(m[2] ? [...m[2].matchAll(/'([a-z_]+)'/g)].map((x) => x[1]) : [])]);
  const writes = new Set();
  for (const f of readdirSync(new URL('.', MODELS)).filter((x) => /\.glb$/.test(x) && !/\.lite\.glb$/.test(x))) {
    try { for (const n of names(f)) { const m = /^write_(.+)$/.exec(n); if (m && !/_mesh$/.test(n)) writes.add(m[1]); } } catch { /* unreadable: skipped */ }
  }
  const found = roles.map((r) => [r[0], r.find((x) => writes.has(x))]);
  check('in-world text: the engine knows a write_ name for every writing surface', roles.length >= 8, roles.map((r) => r.join('/')).join(' '));
  console.log('  note  surfaces on the models\' own write_ nodes:', found.filter((f) => f[1]).map((f) => `${f[0]}=write_${f[1]}`).join(', ') || 'none', '| stand-ins:', found.filter((f) => !f[1]).map((f) => f[0]).join(', ') || 'none');
  const book = (() => { try { return names('book_open.glb'); } catch { return null; } })();
  if (book) check('book_open.glb has the pages, the leaf and the reading camera the engine uses', ['write_page_left', 'write_page_right', 'act_page_turn', 'write_page_turn_front', 'write_page_turn_back', 'cam_read_book', 'book_open_cover'].every((n) => book.includes(n)));
}


// ---------- the Riesenrad parks forward ----------
{
  const THREE = await import('three');
  const { makeRides } = await import('../src/engine/conventions.js');
  let worst = 0, back = 0, late = 0, notStill = 0, maxV = 0;
  for (const start of [0, 0.01, 0.5, 1.7, Math.PI, 4.4, 6.2, 6.28, 9.9, -0.3]) {
    for (const speed of [0.05, -0.05]) {
      const rot = new THREE.Object3D(); rot.name = 'rot_wheel'; rot.userData.speed = speed;
      rot.add(new THREE.Mesh(new THREE.BoxGeometry(10, 10, 0.3)));
      const r = makeRides({ rots: [rot], gondolas: [], horses: [] });
      r.wheel.angle = start;
      const T = r.park(true);
      let prev = r.wheel.angle, t = 0, v = 0;
      while (!r.parked && t < 20) { r.update(1 / 60, t); const d = (r.wheel.angle - prev) * Math.sign(speed); if (d < -1e-9) back++; v = d * 60; maxV = Math.max(maxV, v); prev = r.wheel.angle; t += 1 / 60; }
      if (t > T + 0.05) late++;
      if (v > 0.02) notStill++;
      worst = Math.max(worst, t);
      const rest = Math.abs(r.wheel.angle / (2 * Math.PI) - Math.round(r.wheel.angle / (2 * Math.PI)));
      if (rest > 1e-6) late++;
      r.park(false);
    }
  }
  check('Riesenrad: parking always turns forward, the way the wheel turns, and never backwards', back === 0, `${back} backward steps`);
  check('Riesenrad: parking eases to a stop on a whole turn, in the time it said', late === 0 && notStill === 0, `longest ${worst.toFixed(1)} s, top speed ${maxV.toFixed(2)} rad/s`);
}

console.log(failed ? `\n${failed} unit checks failed` : '\nall unit checks passed');
process.exit(failed ? 1 : 0);
