// Drop animation channels that never leave the node's rest value (the Blender exporter writes
// translation, rotation and scale for every bone in every clip), then prune what is left over.
//
//   node blender/people/slim_anims.mjs in.glb out.glb
//
// Uses the libraries bundled with the globally installed gltf-transform CLI, like blender/lib/optimize.mjs.
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { prune, resample } = require('@gltf-transform/functions');

const [input, output] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(input);
await doc.transform(resample({ tolerance: 2e-4 }));

const EPS = { translation: 5e-5, rotation: 1.5e-5, scale: 2e-4 };
let dropped = 0, kept = 0;
for (const anim of doc.getRoot().listAnimations()) {
  for (const ch of anim.listChannels()) {
    const node = ch.getTargetNode();
    const path = ch.getTargetPath();
    const s = ch.getSampler();
    const out = s.getOutput().getArray();
    const rest = path === 'translation' ? node.getTranslation() : path === 'rotation' ? node.getRotation() : path === 'scale' ? node.getScale() : null;
    if (!rest) { kept++; continue; }
    const n = rest.length;
    let still = true;
    for (let i = 0; i < out.length && still; i += n) {
      let d = 0;
      if (path === 'rotation') {
        // q and -q are the same rotation
        let dot = 0;
        for (let k = 0; k < 4; k++) dot += out[i + k] * rest[k];
        d = 1 - Math.abs(dot);
      } else {
        for (let k = 0; k < n; k++) d = Math.max(d, Math.abs(out[i + k] - rest[k]));
      }
      if (d > EPS[path]) still = false;
    }
    if (still) { ch.dispose(); s.dispose(); dropped++; } else kept++;
  }
}
await doc.transform(prune({ keepLeaves: true, keepAttributes: true }));
await io.write(output, doc);
console.log(`slim_anims: kept ${kept} channels, dropped ${dropped}`);
