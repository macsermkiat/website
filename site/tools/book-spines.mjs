// Which act_book_ spine carries which named title, read from the vendor's glbs and atlas regions.
// The vendor prints the reading list's titles on individual spines (blender/props/set_books.py), but the glb
// does not say which node is which. This reads each book's UVs and finds the ones inside the atlas regions
// "spine_<key>" of blender/out/vendor/regions.json, then writes site/src/book-spines.json:
//   { "sets": { "prop_books_shelf_1": { "act_book_22": "order_of_time", ... }, "prop_books_shelf_1.lite": { ... } } }
// Run it again after the vendor re-exports the book sets:  node tools/book-spines.mjs
// (dev only: needs @gltf-transform/core + extensions and meshoptimizer, e.g. from a global @gltf-transform/cli).
// If the vendor adds extras { "title": "<key>" } to the act_book_ nodes, the site reads those instead.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const SITE = path.resolve(import.meta.dirname, '..');
const REPO = path.resolve(SITE, '..');
const require = createRequire(import.meta.url);
const tryReq = (names) => { for (const n of names) { try { return require(n); } catch { /* next */ } } throw new Error(`cannot find ${names[0]}`); };
const G = '/opt/node22/lib/node_modules/@gltf-transform/cli/node_modules/';
const core = tryReq(['@gltf-transform/core', G + '@gltf-transform/core']);
const ext = tryReq(['@gltf-transform/extensions', G + '@gltf-transform/extensions']);
const { MeshoptDecoder } = tryReq(['meshoptimizer', G + 'meshoptimizer']);

const regionsFile = path.join(REPO, 'blender/out/vendor/regions.json');
if (!fs.existsSync(regionsFile)) { console.error(`no ${regionsFile}: run blender/props/vendor_atlas.py first`); process.exit(1); }
const regions = JSON.parse(fs.readFileSync(regionsFile, 'utf8')).regions;
// the named spines: every spine_<key> that is not a generic spine_g<n>
const named = Object.entries(regions).filter(([k]) => /^spine_/.test(k) && !/^spine_g\d+$/.test(k)).map(([k, r]) => ({ key: k.slice(6), r }));

await MeshoptDecoder.ready;
const io = new core.NodeIO().registerExtensions(ext.ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const out = {};
// every book set, full and lite (the lite export numbers its books a little differently)
const files = fs.readdirSync(path.join(SITE, 'public/models')).filter((f) => /^prop_books_.*\.glb$/.test(f)).sort();
for (const file of files) {
  const p = path.join(SITE, 'public/models', file);
  if (!fs.existsSync(p)) continue;
  const doc = await io.read(p);
  const map = {};
  for (const node of doc.getRoot().listNodes()) {
    const name = node.getName();
    if (!/^act_book_\d+$/.test(name)) continue;
    const counts = new Map();
    const visit = (n) => {
      const mesh = n.getMesh();
      if (mesh) for (const prim of mesh.listPrimitives()) {
        const uv = prim.getAttribute('TEXCOORD_0');
        if (!uv) continue;
        const e = [];
        for (let i = 0; i < uv.getCount(); i++) {
          uv.getElement(i, e);
          const u = e[0], v = 1 - e[1]; // glTF v runs down; regions.json v runs up
          for (const { key, r } of named) if (u >= r[0] && u <= r[2] && v >= r[1] && v <= r[3]) counts.set(key, (counts.get(key) || 0) + 1);
        }
      }
      n.listChildren().forEach(visit);
    };
    visit(node);
    const best = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
    if (best && best[1] >= 3) map[name] = best[0];
  }
  if (Object.keys(map).length) out[file.replace(/\.glb$/, '')] = map;
}
// the printed titles, from the vendor's atlas specs: "geb": dict(..., title="GÖDEL, ESCHER, BACH", ...)
const titles = {};
const atlasPy = path.join(REPO, 'blender/props/vendor_atlas.py');
if (fs.existsSync(atlasPy)) {
  const src = fs.readFileSync(atlasPy, 'utf8');
  for (const { key } of named) {
    const m = new RegExp(`"${key}":\\s*dict\\([^)]*?title="([^"]+)"`, 's').exec(src);
    if (m) titles[key] = m[1].replace(/\\n/g, ' ').replace(/\s+/g, ' ').trim();
  }
}
const dest = path.join(SITE, 'src/book-spines.json');
fs.writeFileSync(dest, JSON.stringify({ about: 'Which act_book_ spine shows which named title (written by tools/book-spines.mjs from the vendor glbs and atlas regions).', titles, sets: out }, null, 1) + '\n');
console.log(JSON.stringify(out));
