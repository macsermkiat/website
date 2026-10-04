// Strip meshopt compression from a shipped glb so Blender's importer can read it (previews of the
// delivered file, not of a rebuild).   node blender/square/decode_glb.mjs in.glb out.glb
import { createRequire } from 'module';
import { execSync } from 'child_process';
const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { MeshoptDecoder } = require('meshoptimizer');
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const [inp, out] = process.argv.slice(2);
const doc = await io.read(inp);
for (const e of doc.getRoot().listExtensionsUsed()) {
  if (e.extensionName === 'EXT_meshopt_compression') e.dispose();
}
await io.write(out, doc);
console.log('decoded', inp, '->', out);
