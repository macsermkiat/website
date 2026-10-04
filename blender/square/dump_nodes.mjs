// Dump named nodes (world matrix within the asset) and the mesh bounding box of each glb.
//   node blender/square/dump_nodes.mjs out.json a.glb b.glb ...
// Used by stroll.py to find each place's cam_view / cam_target and footprint.
import { createRequire } from 'module';
import { execSync } from 'child_process';
import fs from 'fs';
const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { getBounds } = require('@gltf-transform/core');
const { MeshoptDecoder } = require('meshoptimizer');
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const [out, ...files] = process.argv.slice(2);
const res = {};
for (const f of files) {
  const doc = await io.read(f);
  const scene = doc.getRoot().getDefaultScene() || doc.getRoot().listScenes()[0];
  const nodes = {};
  // triangles that reach into the walking band (0.05-2.2 m above the ground), as local xz triangles,
  // written to <out>.<asset>.tri.bin (float32 x0 z0 x1 z1 x2 z2 per triangle)
  const tri = [];
  scene.traverse((n) => {
    const name = n.getName();
    if (/^(cam_|slot_|light_|path_|act_|write_|rot_)/.test(name)) {
      const w = n.getWorldMatrix();
      nodes[name] = [w[12], w[13], w[14]];
    }
    const mesh = n.getMesh();
    if (!mesh || /^(snow_|bulbs_)/.test(name)) return;
    const m = n.getWorldMatrix();
    for (const prim of mesh.listPrimitives()) {
      const pos = prim.getAttribute('POSITION');
      if (!pos) continue;
      const idx = prim.getIndices();
      const c = pos.getCount();
      const W = new Float32Array(c * 3);
      const v = [0, 0, 0];
      for (let i = 0; i < c; i++) {
        pos.getElement(i, v);
        W[i * 3] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
        W[i * 3 + 1] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
        W[i * 3 + 2] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14];
      }
      const nt = idx ? idx.getCount() / 3 : c / 3;
      for (let t = 0; t < nt; t++) {
        const a = idx ? idx.getScalar(t * 3) : t * 3, b = idx ? idx.getScalar(t * 3 + 1) : t * 3 + 1, d = idx ? idx.getScalar(t * 3 + 2) : t * 3 + 2;
        const ya = W[a * 3 + 1], yb = W[b * 3 + 1], yd = W[d * 3 + 1];
        if (Math.min(ya, yb, yd) > 2.2 || Math.max(ya, yb, yd) < 0.05) continue;
        tri.push(W[a * 3], W[a * 3 + 2], W[b * 3], W[b * 3 + 2], W[d * 3], W[d * 3 + 2]);
      }
    }
  });
  fs.writeFileSync(`${out}.${f.split('/').pop()}.tri.bin`, Buffer.from(new Float32Array(tri).buffer));
  const b = getBounds(scene);
  res[f.split('/').pop()] = { nodes, bounds: b };
}
fs.writeFileSync(out, JSON.stringify(res));
console.log('wrote', out, Object.keys(res).length);
