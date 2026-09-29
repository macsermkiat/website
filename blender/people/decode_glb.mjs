// Write a copy of a web glb without meshopt compression, so Blender's importer can read it
// (preview.py imports the ride builder's bandstand and instruments this way).
//
//   node blender/people/decode_glb.mjs in.glb out.glb
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { MeshoptDecoder } = require('meshoptimizer');

await MeshoptDecoder.ready;
const [input, output] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(input);
for (const ext of doc.getRoot().listExtensionsUsed()) {
  if (ext.extensionName === 'EXT_meshopt_compression') ext.dispose();
}
await io.write(output, doc);
console.log(`decoded ${input} -> ${output}`);
