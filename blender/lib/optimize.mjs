// Web optimisation for market glb files, keeping the named-node contract intact.
//
//   node blender/lib/optimize.mjs in.glb out.glb [--texture-size 1024] [--no-webp]
//
// Why not `gltf-transform optimize`? The CLI's optimize step prunes empty leaf nodes,
// so every slot_*, light_*, cam_view and cam_target empty disappears, and its palette /
// join steps merge and rename materials such as bulb_warm. This script runs the same
// passes (dedup, weld, prune, sparse, WebP + resize, meshopt) with prune({keepLeaves:true})
// and without flatten / join / palette / simplify, so node and material names survive.
import { createRequire } from 'module';
import { execSync } from 'child_process';

// Resolve the libraries bundled with the globally installed CLI.
const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dedup, weld, prune, sparse, resample, textureCompress, meshopt } = require('@gltf-transform/functions');
const { MeshoptEncoder, MeshoptDecoder } = require('meshoptimizer');
const sharp = require('sharp');

const args = process.argv.slice(2);
const [input, output] = args;
if (!input || !output) {
  console.error('usage: node optimize.mjs in.glb out.glb [--texture-size N] [--no-webp]');
  process.exit(2);
}
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : dflt;
};
const size = parseInt(opt('--texture-size', '1024'), 10);
const webp = !args.includes('--no-webp');

await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });

const doc = await io.read(input);
await doc.transform(
  dedup(),
  weld(),
  resample(),
  prune({ keepLeaves: true, keepAttributes: false, keepSolidTextures: false }),
  sparse(),
  textureCompress({
    encoder: sharp,
    targetFormat: webp ? 'webp' : undefined,
    resize: [size, size],
    quality: 82,
    effort: 90,
  }),
  meshopt({ encoder: MeshoptEncoder, level: 'high' }),
);
await io.write(output, doc);
console.log(`optimized ${input} -> ${output}`);
