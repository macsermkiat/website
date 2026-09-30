// Download and triangle budgets (docs/BUILD.md "Budgets"), counted the way a browser pays for them: each glb
// plus every external texture it references (the deco kit and the vendor's atlases are separate .webp files),
// each shared texture once per market, plus the site's own code and fonts from dist/.
//
//   node scripts/budget.mjs            report
//   node scripts/budget.mjs --strict   also fail (exit 1) when a market's first load is over its aim
//   node scripts/budget.mjs --json     machine-readable
//
// Per-asset budgets are reported for the owning roles; the first-load totals are the engine's to keep (it
// decides what loads before the first frame), so only those fail the strict run.
import fs from 'node:fs';
import path from 'node:path';

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

const exists = (f) => fs.existsSync(path.join(MODELS, f));
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };

export function budget() {
  const layout = readJson(path.join(SITE, 'src', 'layout.json'));
  const props = readJson(path.join(MODELS, 'props.json'));
  const crowd = readJson(path.join(SITE, 'src', 'crowd.json'));
  const places = layout?.places || [];
  const kindOf = (e) => (e.kind === 'section' ? 'section' : e.kind === 'deco' ? 'deco' : /bandstand/.test(e.id) ? 'bandstand' : e.kind === 'landmark' ? 'ride' : /square/.test(e.id) ? 'square' : /town|church/.test(e.id) ? 'town' : null);
  // the engine opens both markets without the rides and the deco stalls (main.js: defer)
  const deferred = (e) => e.kind === 'deco' || /riesenrad|karussell/.test(e.id);
  const groups = [];
  for (const e of places) {
    const files = [e.asset];
    for (const s of props?.sets || []) if (s.stall === e.id) files.push(s.model);
    if (/bandstand/.test(e.id)) for (const k of ['sax', 'piano', 'bass', 'drums']) files.push(`instr_${k}.glb`, `people_band_${k}.glb`);
    groups.push({ id: e.id, kind: kindOf(e), files: files.filter(Boolean), deferred: deferred(e) });
  }
  // people: every variant the crowd names (the bandstand's players are counted with it)
  const people = new Set();
  JSON.stringify(crowd || {}).replace(/people_[a-z_]+\.glb/g, (m) => { if (!m.includes('.lite') && !/band_/.test(m)) people.add(m); return m; });
  for (const f of people) groups.push({ id: f.replace(/\.glb$/, ''), kind: f === 'people_anims.glb' ? null : 'person', files: [f], deferred: false });

  const liteOf = (f) => { const l = f.replace(/\.glb$/, '.lite.glb'); return exists(l) ? l : f; };
  const measure = (files, seen) => {
    let bytes = 0, tris = 0, textures = 0;
    const missing = [];
    for (const f of files) {
      if (!exists(f)) { missing.push(f); continue; }
      const g = readGlb(path.join(MODELS, f));
      bytes += g.bytes; tris += g.tris;
      for (const img of g.images) {
        const p = path.join(path.dirname(path.join(MODELS, f)), img);
        if (!fs.existsSync(p)) { missing.push(img); continue; }
        const size = fs.statSync(p).size;
        if (!seen || !seen.has(p)) { textures += size; bytes += size; seen?.add(p); }
      }
    }
    return { bytes, tris, textures, missing };
  };
  const rows = groups.map((g) => {
    const full = measure(g.files, null);
    const lite = measure(g.files.map(liteOf), null);
    const b = g.kind && BUDGET[g.kind];
    return { ...g, full, lite, budget: b || null, over: b ? { tris: full.tris > b.tris, bytes: full.bytes > b.bytes } : null };
  });
  // the site's own files: every script, stylesheet and font in dist/assets (an upper bound on what loads)
  let code = 0;
  const assets = path.join(DIST, 'assets');
  if (fs.existsSync(assets)) for (const f of fs.readdirSync(assets)) if (/\.(js|css|woff2)$/.test(f) && !/^plain-/.test(f)) code += fs.statSync(path.join(assets, f)).size;
  const totals = {};
  for (const market of ['full', 'lite']) {
    const seen = new Set(), seenAll = new Set();
    let first = code, all = code;
    for (const g of groups) {
      const files = market === 'lite' ? g.files.map(liteOf) : g.files;
      const m = measure(files, seenAll);
      all += m.bytes;
      if (!g.deferred) first += measure(files, seen).bytes;
    }
    totals[market] = { firstLoad: first, everything: all, aim: FIRST_LOAD[market], over: first > FIRST_LOAD[market] };
  }
  return { rows, totals, code };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const r = budget();
  if (args.includes('--json')) { console.log(JSON.stringify(r, null, 1)); process.exit(0); }
  const mb = (b) => `${(b / MB).toFixed(2)} MB`;
  const k = (t) => `${(t / 1000).toFixed(1)}k`;
  console.log('Per asset (full glb + props + external textures; lite in brackets)');
  for (const g of r.rows) {
    const b = g.budget;
    const flag = g.over && (g.over.tris || g.over.bytes) ? '  OVER' : '';
    console.log(`  ${g.id.padEnd(24)} ${k(g.full.tris).padStart(7)} tris ${mb(g.full.bytes).padStart(9)} (lite ${k(g.lite.tris)}, ${mb(g.lite.bytes)})${b ? `  budget ${k(b.tris)} / ${mb(b.bytes)}` : ''}${flag}${g.full.missing.length ? `  missing: ${g.full.missing.join(', ')}` : ''}`);
  }
  console.log(`Site code, styles and fonts: ${mb(r.code)}`);
  for (const [m, t] of Object.entries(r.totals)) console.log(`${m.padEnd(4)} market: first load ${mb(t.firstLoad)} (aim ${mb(t.aim)})${t.over ? '  OVER' : ''}; everything ${mb(t.everything)}`);
  if (args.includes('--strict') && Object.values(r.totals).some((t) => t.over)) { console.error('budget: a first load is over its aim'); process.exit(1); }
}
