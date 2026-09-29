// Undo the web compression of a market glb so Blender can import it (for previews that show
// another role's shipped asset, e.g. the vendor's props on a stall).
//
//   node blender/lib/decode.mjs in.glb out.glb
//
// Removes EXT_meshopt_compression (Blender's importer cannot read it) and keeps everything else
// (WebP textures import fine in Blender 4.2).
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dequantize } = require('@gltf-transform/functions');
const { MeshoptDecoder } = require('meshoptimizer');

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node decode.mjs in.glb out.glb');
  process.exit(2);
}
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(input);
await doc.transform(dequantize());          // float positions/normals/UVs again
for (const ext of doc.getRoot().listExtensionsUsed()) {
  if (ext.extensionName === 'EXT_meshopt_compression' || ext.extensionName === 'KHR_mesh_quantization') ext.dispose();
}
await io.write(output, doc);
console.log(`decoded ${input} -> ${output}`);
