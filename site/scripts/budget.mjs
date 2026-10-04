// Download and triangle budgets (docs/BUILD.md "Budgets"), counted the way a browser pays for them.
//
// What it counts, per market (full and lite):
//   - every glb the engine loads: each layout entry's model, its props sets, the bandstand's instruments, its players (as people),
//     every crowd figure and the shared clips (people_anims.glb);
//   - on the full market, the distance level of the crowd (each figure's .lite.glb, loaded after the first frame);
//   - every external texture those glbs reference (the deco kit and the vendor's atlases are separate .webp files),
//     each texture once per market, and files with the same bytes under two names once (deduped by content hash);
//   - the site's own scripts, styles and fonts from dist/assets (run it after `npm run build`; no dist is an error).
// It splits each market's download into the first load (before the market opens) and the deferred part (the deco
// stalls, both rides and the crowd's distance level, loaded just after the first frame), as main.js does.
//
//   node scripts/budget.mjs            report
//   node scripts/budget.mjs --strict   also fail (exit 1) when a market's first load is over its aim
//   node scripts/budget.mjs --json     machine-readable
//
// Per-asset rows charge each asset its own files; a texture that two or more assets share is charged once, to the
// "shared textures" row, not to every asset that uses it. Per-asset budgets are reported for the owning roles; the
// first-load totals are the engine's to keep (it decides what loads before the first frame), so only those fail
// the strict run.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SITE = path.resolve(import.meta.dirname, '..');
const MODELS = path.join(SITE, 'public', 'models');
const DIST = path.join(SITE, 'dist');
const args = process.argv.slice(2);
const MB = 1e6;

// docs/BUILD.md: triangles and bytes per asset (after optimize.mjs)
const BUDGET = {
  section: { tris: 60000, bytes: 3 * MB, what: 'Section stall with its props' },
  deco: { tris: 20000, bytes: 1 * MB, what: 'Deco stall' },
  ride: { tris: 80000, bytes: 3 * MB, what: 'Ferris wheel / carousel' },
  bandstand: { tris: 50000, bytes: 2 * MB, what: 'Bandstand with instruments' },
  square: { tris: 40000, bytes: 3 * MB, what: 'Square ground, lamps, string-light poles' },
  town: { tris: 150000, bytes: 5 * MB, what: 'Town ring and church' },
  person: { tris: 5000, bytes: 0.4 * MB, what: 'One person variant' },
  // BUILD.md "Bücherstand categories": the bookshop with its six category sections and all its props
  buecherstand: { tris: 80000, bytes: 4 * MB, what: 'Bücherstand with all its props' },
};
const FIRST_LOAD = { full: 25 * MB, lite: 8 * MB };

/** A glb's JSON chunk: triangles (every node that draws a mesh counts), its external images. */
export function readGlb(file) {
  const b = fs.readFileSync(file);
  const len = b.readUInt32LE(12);
  const j = JSON.parse(b.subarray(20, 20 + len).toString('utf8'));
  const meshTris = (j.meshes || []).map((m) => m.primitives.reduce((a, p) => {
    if (p.mode !== undefined && p.mode !== 4) return a;
    const acc = p.indices !== undefined ? j.accessors[p.indices] : j.accessors[p.attributes.POSITION];
    return a + Math.floor((acc?.count || 0) / 3);
  }, 0));
  let tris = 0;
  for (const n of j.nodes || []) if (n.mesh !== undefined) tris += meshTris[n.mesh] || 0;
  const images = (j.images || []).map((im) => im.uri).filter((u) => u && !/^data:/.test(u)).map((u) => decodeURIComponent(u));
  return { bytes: b.length, tris, images };
}

const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };

/** One downloadable file: its path, size and content hash (two names with the same bytes are one download). */
const fileCache = new Map();
function fileInfo(p) {
  if (!fileCache.has(p)) {
    if (!fs.existsSync(p)) fileCache.set(p, null);
    else { const b = fs.readFileSync(p); fileCache.set(p, { path: p, size: b.length, hash: crypto.createHash('sha1').update(b).digest('hex') }); }
  }
  return fileCache.get(p);
}

/** What loading `glb` downloads: the glb and each external texture, as file infos; missing files listed apart. */
function filesOf(models, glb) {
  const p = path.join(models, glb);
  const g = fileInfo(p);
  if (!g) return { tris: 0, glb: null, textures: [], missing: [glb] };
  const j = readGlb(p);
  const textures = [], missing = [];
  for (const img of j.images) {
    const t = fileInfo(path.join(path.dirname(p), img));
    if (t) textures.push(t); else missing.push(img);
  }
  return { tris: j.tris, glb: g, textures, missing };
}

export function budget({ models = MODELS, site = SITE, dist = DIST } = {}) {
  const exists = (f) => fs.existsSync(path.join(models, f));
  const layout = readJson(path.join(site, 'src', 'layout.json'));
  const props = readJson(path.join(models, 'props.json'));
  const crowd = readJson(path.join(site, 'src', 'crowd.json'));
  const places = layout?.places || [];
  const kindOf = (e) => (e.kind === 'section' ? 'section' : e.kind === 'deco' ? 'deco' : /bandstand/.test(e.id) ? 'bandstand' : e.kind === 'landmark' ? 'ride' : /square/.test(e.id) ? 'square' : /town|church/.test(e.id) ? 'town' : null);
  // the engine opens both markets without the rides and the deco stalls (main.js: defer)
  // drawn instead of another file, never with it: { file: the file it replaces }
  const ALT = { 'instr_sax_stand.glb': 'instr_sax.glb' };
  const deferred = (e) => e.kind === 'deco' || /riesenrad|karussell/.test(e.id);
  const liteOf = (f) => { const l = f.replace(/\.glb$/, '.lite.glb'); return exists(l) ? l : f; };

  // groups: { id, kind, files: { full: [...], lite: [...] }, deferred: { full, lite } }
  const groups = [];
  for (const e of places) {
    const files = [e.asset || e.model];
    for (const s of props?.sets || []) if (s.stall === e.id) files.push(s.model);
    // BUILD.md budgets the "Bandstand with instruments"; its four players are person variants (5k each), charged below
    if (/bandstand/.test(e.id)) for (const k of ['sax', 'piano', 'bass', 'drums']) files.push(`instr_${k}.glb`);
    // the sax on its stand (band on a break) is shown instead of the held sax, never with it: its bytes count,
    // and its triangles only where they exceed the held sax's (ALT)
    if (/bandstand/.test(e.id) && exists('instr_sax_stand.glb')) files.push('instr_sax_stand.glb');
    const f = files.filter(Boolean);
    // a props set may name its own lite file (props.json "lite"); otherwise <model>.lite.glb when it exists
    const lite = f.map((x) => props?.sets?.find((s) => s.model === x && s.lite)?.lite || liteOf(x));
    groups.push({ id: e.id, kind: kindOf(e), files: { full: f, lite }, deferred: { full: deferred(e), lite: deferred(e) } });
  }
  // people: every figure the crowd names and the bandstand's four players (each a person variant), and the shared clips
  const people = new Set();
  JSON.stringify(crowd || {}).replace(/people_[a-z_]+\.glb/g, (m) => { people.add(m); return m; });
  if (places.some((e) => /bandstand/.test(e.id))) for (const k of ['sax', 'piano', 'bass', 'drums']) if (exists(`people_band_${k}.glb`)) people.add(`people_band_${k}.glb`);
  const anims = crowd?.shared_anims?.file || 'people_anims.glb';
  for (const f of people) {
    if (f === anims) continue;
    groups.push({ id: f.replace(/\.glb$/, ''), kind: 'person', files: { full: [f], lite: [liteOf(f)] }, deferred: { full: false, lite: false } });
    // the full market's distance level: the figure's .lite.glb, loaded after the first frame (crowd.js enableLod)
    if (liteOf(f) !== f && !/^people_band_/.test(f)) groups.push({ id: `${f.replace(/\.glb$/, '')} (distance level)`, kind: null, lod: true, files: { full: [liteOf(f)], lite: [] }, deferred: { full: true, lite: true } });
  }
  if (exists(anims)) groups.push({ id: anims.replace(/\.glb$/, ''), kind: null, files: { full: [anims], lite: [anims] }, deferred: { full: false, lite: false } });

  // which assets use each texture (by content), to charge shared textures once
  const users = new Map();
  for (const g of groups) for (const f of new Set([...g.files.full, ...g.files.lite])) for (const t of filesOf(models, f).textures) {
    if (!users.has(t.hash)) users.set(t.hash, { info: t, groups: new Set() });
    users.get(t.hash).groups.add(g.id.replace(/ \(distance level\)$/, ''));
  }
  const sharedHashes = new Set([...users].filter(([, u]) => u.groups.size > 1).map(([h]) => h));

  const measure = (files, { skipShared = false } = {}) => {
    let bytes = 0, tris = 0, textures = 0, sharedTex = 0, share = 0;
    const missing = [], seen = new Set();
    for (const f of files) {
      const m = filesOf(models, f);
      missing.push(...m.missing);
      if (!m.glb) continue;
      const alt = ALT[f.replace(/\.lite\.glb$/, '.glb')];
      if (alt) { const lf = /\.lite\.glb$/.test(f) ? liteOf(alt) : alt; tris += Math.max(0, m.tris - (files.includes(lf) ? filesOf(models, lf).tris : 0)); }
      else tris += m.tris;
      if (!seen.has(m.glb.hash)) { seen.add(m.glb.hash); bytes += m.glb.size; }
      for (const t of m.textures) {
        if (seen.has(t.hash)) continue;
        seen.add(t.hash);
        // a shared texture: listed once in the shared row; each asset that uses it carries an equal part of it
        if (skipShared && sharedHashes.has(t.hash)) { sharedTex += t.size; share += t.size / users.get(t.hash).groups.size; continue; }
        textures += t.size; bytes += t.size;
      }
    }
    return { bytes, tris, textures, sharedTextures: sharedTex, share, missing };
  };
  const rows = groups.filter((g) => !g.lod).map((g) => {
    const full = measure(g.files.full, { skipShared: true });
    const lite = measure(g.files.lite, { skipShared: true });
    const b = (g.id === 'buecherstand' && BUDGET.buecherstand) || (g.kind && BUDGET[g.kind]);
    return { id: g.id, kind: g.kind, deferred: g.deferred.full, full, lite, budget: b || null, over: b ? { tris: full.tris > b.tris, bytes: full.bytes + full.share > b.bytes } : null };
  });
  const shared = [...users].filter(([h]) => sharedHashes.has(h)).map(([, u]) => ({ file: path.relative(models, u.info.path), bytes: u.info.size, users: [...u.groups] }));

  // the site's own files: every script, stylesheet and font in dist/assets (an upper bound on what loads)
  const assets = path.join(dist, 'assets');
  const hasDist = fs.existsSync(assets);
  let code = 0;
  if (hasDist) for (const f of fs.readdirSync(assets)) if (/\.(js|css|woff2?)$/.test(f) && !/^plain-/.test(f)) code += fs.statSync(path.join(assets, f)).size;

  const totals = {};
  for (const market of ['full', 'lite']) {
    const seen = new Set();
    const add = (files) => {
      let bytes = 0;
      for (const f of files) {
        const m = filesOf(models, f);
        for (const x of [m.glb, ...m.textures]) if (x && !seen.has(x.hash)) { seen.add(x.hash); bytes += x.size; }
      }
      return bytes;
    };
    // first load before the deferred part, so a texture both use is charged to the first load
    let first = code, later = 0;
    for (const g of groups) if (!g.deferred[market]) first += add(g.files[market]);
    for (const g of groups) if (g.deferred[market]) later += add(g.files[market]);
    totals[market] = { firstLoad: first, deferred: later, everything: first + later, aim: FIRST_LOAD[market], over: first > FIRST_LOAD[market] };
  }
  return { rows, shared, totals, code, hasDist };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const r = budget();
  if (!r.hasDist) {
    console.error('budget: dist/assets is missing. Run `npm run build` first: the site\'s own code counts towards each first load.');
    process.exit(1);
  }
  if (args.includes('--json')) { console.log(JSON.stringify(r, null, 1)); process.exit(0); }
  const mb = (b) => `${(b / MB).toFixed(2)} MB`;
  const k = (t) => `${(t / 1000).toFixed(1)}k`;
  console.log('Per asset (full glb + props + own textures; lite in brackets; textures shared with other assets are in the last row,\n  and each asset is judged on its own bytes plus an equal part of every shared texture it uses)');
  for (const g of r.rows) {
    const b = g.budget;
    const flag = g.over && (g.over.tris || g.over.bytes) ? '  OVER' : '';
    const sh = g.full.sharedTextures ? ` +${mb(g.full.sharedTextures)} shared (its part ${mb(g.full.share)})` : '';
    console.log(`  ${g.id.padEnd(24)} ${k(g.full.tris).padStart(7)} tris ${mb(g.full.bytes).padStart(9)}${sh} (lite ${k(g.lite.tris)}, ${mb(g.lite.bytes)})${g.deferred ? ' [deferred]' : ''}${b ? `  budget ${k(b.tris)} / ${mb(b.bytes)}` : ''}${flag}${g.full.missing.length ? `  missing: ${g.full.missing.join(', ')}` : ''}`);
  }
  const sharedBytes = r.shared.reduce((a, s) => a + s.bytes, 0);
  console.log(`  ${'shared textures'.padEnd(24)} ${String(r.shared.length).padStart(7)} files ${mb(sharedBytes).padStart(9)} (each charged once)`);
  console.log(`Site code, styles and fonts: ${mb(r.code)}`);
  for (const [m, t] of Object.entries(r.totals)) console.log(`${m.padEnd(4)} market: first load ${mb(t.firstLoad)} (aim ${mb(t.aim)})${t.over ? '  OVER' : ''}; deferred ${mb(t.deferred)}; everything ${mb(t.everything)}`);
  if (args.includes('--strict') && Object.values(r.totals).some((t) => t.over)) { console.error('budget: a first load is over its aim'); process.exit(1); }
}
