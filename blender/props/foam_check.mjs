// Decode prop_bier_counter(.lite).glb as the browser does (meshopt + quantisation, node transforms applied)
// and check every glass's foam head the way the engine's beer action does (site/src/actions/items/beer.js
// foamFits): the head must be under half the glass's height and its top no more than 0.35 x the glass height
// above the glass. Round 2's lite file once shipped heads 0.68 m tall; this catches that.
//
//   node blender/props/foam_check.mjs [file.glb ...]      (default: both Bierstand counter files)
//   exit 1 if any head fails
import { createRequire } from 'module';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO, getBounds } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { MeshoptDecoder } = require('meshoptimizer');

const here = path.dirname(fileURLToPath(import.meta.url));
const models = path.join(here, '..', '..', 'site', 'public', 'models');
const files = process.argv.slice(2).length ? process.argv.slice(2)
  : ['prop_bier_counter.glb', 'prop_bier_counter.lite.glb'].map((f) => path.join(models, f));
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
let bad = 0;
for (const f of files) {
  const doc = await io.read(f);
  const glasses = doc.getRoot().listNodes().filter((n) => /^act_glass_\d+$/.test(n.getName()));
  let worst = 0;
  for (const g of glasses) {
    const foam = g.listChildren().find((c) => /^foam_/.test(c.getName()));
    if (!foam) continue;
    // the glass without its head: every child subtree except the foam
    const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (const c of g.listChildren()) {
      if (c === foam) continue;
      const b = getBounds(c);
      for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], b.min[i]); hi[i] = Math.max(hi[i], b.max[i]); }
    }
    const fb = getBounds(foam);
    const gh = hi[1] - lo[1], fh = fb.max[1] - fb.min[1];
    const ok = fh < gh * 0.5 && fb.max[1] < hi[1] + gh * 0.35;
    worst = Math.max(worst, fh);
    if (!ok) { bad++; console.log(`FAIL ${path.basename(f)} ${g.getName()}: head ${(fh * 100).toFixed(1)} cm on a ${(gh * 100).toFixed(1)} cm glass`); }
  }
  console.log(`${path.basename(f)}: ${glasses.length} glasses, tallest head ${(worst * 100).toFixed(1)} cm`);
}
process.exit(bad ? 1 : 0);
