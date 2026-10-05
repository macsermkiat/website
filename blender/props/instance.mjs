// Round 9 (vendor): fold repeated goods into EXT_mesh_gpu_instancing batches, after blender/lib/optimize.mjs
// and before the shared textures are moved out of the glb (vlib.export_set).
//
//   node blender/props/instance.mjs in.glb out.glb [--min 3]
//
// The ornament shop's repeated goods (mercury-glass baubles by size and colour, gold-foil angels) are built
// in Blender as objects named inst_* that share one mesh datablock, so the exporter writes one glTF mesh
// referenced by many nodes. Each group of at least --min such nodes under the same parent becomes ONE child
// node of that parent (named inst_<mesh>) with per-instance TRANSLATION / ROTATION / SCALE relative to the
// parent; three.js's GLTFLoader turns it into a single InstancedMesh (one draw call per group).
// Unlike gltf-transform's instance(), the batch stays under the set's root node (the engine parents the
// root to its slot_ empty), and no other node is pruned: named empties survive.
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO, MathUtils } = require('@gltf-transform/core');
const { ALL_EXTENSIONS, EXTMeshGPUInstancing } = require('@gltf-transform/extensions');
const { MeshoptEncoder, MeshoptDecoder } = require('meshoptimizer');
// column-major 4x4 helpers (glTF matrices)
const mul = (a, b) => {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return o;
};
const invert = (m) => {   // general inverse by cofactors
  const a = m, inv = new Array(16);
  inv[0] = a[5]*a[10]*a[15]-a[5]*a[11]*a[14]-a[9]*a[6]*a[15]+a[9]*a[7]*a[14]+a[13]*a[6]*a[11]-a[13]*a[7]*a[10];
  inv[4] = -a[4]*a[10]*a[15]+a[4]*a[11]*a[14]+a[8]*a[6]*a[15]-a[8]*a[7]*a[14]-a[12]*a[6]*a[11]+a[12]*a[7]*a[10];
  inv[8] = a[4]*a[9]*a[15]-a[4]*a[11]*a[13]-a[8]*a[5]*a[15]+a[8]*a[7]*a[13]+a[12]*a[5]*a[11]-a[12]*a[7]*a[9];
  inv[12] = -a[4]*a[9]*a[14]+a[4]*a[10]*a[13]+a[8]*a[5]*a[14]-a[8]*a[6]*a[13]-a[12]*a[5]*a[10]+a[12]*a[6]*a[9];
  inv[1] = -a[1]*a[10]*a[15]+a[1]*a[11]*a[14]+a[9]*a[2]*a[15]-a[9]*a[3]*a[14]-a[13]*a[2]*a[11]+a[13]*a[3]*a[10];
  inv[5] = a[0]*a[10]*a[15]-a[0]*a[11]*a[14]-a[8]*a[2]*a[15]+a[8]*a[3]*a[14]+a[12]*a[2]*a[11]-a[12]*a[3]*a[10];
  inv[9] = -a[0]*a[9]*a[15]+a[0]*a[11]*a[13]+a[8]*a[1]*a[15]-a[8]*a[3]*a[13]-a[12]*a[1]*a[11]+a[12]*a[3]*a[9];
  inv[13] = a[0]*a[9]*a[14]-a[0]*a[10]*a[13]-a[8]*a[1]*a[14]+a[8]*a[2]*a[13]+a[12]*a[1]*a[10]-a[12]*a[2]*a[9];
  inv[2] = a[1]*a[6]*a[15]-a[1]*a[7]*a[14]-a[5]*a[2]*a[15]+a[5]*a[3]*a[14]+a[13]*a[2]*a[7]-a[13]*a[3]*a[6];
  inv[6] = -a[0]*a[6]*a[15]+a[0]*a[7]*a[14]+a[4]*a[2]*a[15]-a[4]*a[3]*a[14]-a[12]*a[2]*a[7]+a[12]*a[3]*a[6];
  inv[10] = a[0]*a[5]*a[15]-a[0]*a[7]*a[13]-a[4]*a[1]*a[15]+a[4]*a[3]*a[13]+a[12]*a[1]*a[7]-a[12]*a[3]*a[5];
  inv[14] = -a[0]*a[5]*a[14]+a[0]*a[6]*a[13]+a[4]*a[1]*a[14]-a[4]*a[2]*a[13]-a[12]*a[1]*a[6]+a[12]*a[2]*a[5];
  inv[3] = -a[1]*a[6]*a[11]+a[1]*a[7]*a[10]+a[5]*a[2]*a[11]-a[5]*a[3]*a[10]-a[9]*a[2]*a[7]+a[9]*a[3]*a[6];
  inv[7] = a[0]*a[6]*a[11]-a[0]*a[7]*a[10]-a[4]*a[2]*a[11]+a[4]*a[3]*a[10]+a[8]*a[2]*a[7]-a[8]*a[3]*a[6];
  inv[11] = -a[0]*a[5]*a[11]+a[0]*a[7]*a[9]+a[4]*a[1]*a[11]-a[4]*a[3]*a[9]-a[8]*a[1]*a[7]+a[8]*a[3]*a[5];
  inv[15] = a[0]*a[5]*a[10]-a[0]*a[6]*a[9]-a[4]*a[1]*a[10]+a[4]*a[2]*a[9]+a[8]*a[1]*a[6]-a[8]*a[2]*a[5];
  const det = a[0]*inv[0]+a[1]*inv[4]+a[2]*inv[8]+a[3]*inv[12];
  return inv.map((v) => v / det);
};

const args = process.argv.slice(2);
const [input, output] = args;
const k = args.indexOf('--min');
const min = k >= 0 ? parseInt(args[k + 1], 10) : 3;
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(input);
const root = doc.getRoot();
const ext = doc.createExtension(EXTMeshGPUInstancing);
const groups = new Map();   // key parent|mesh -> nodes
for (const scene of root.listScenes()) {
  scene.traverse((node) => {
    const mesh = node.getMesh();
    if (!mesh || !node.getName().startsWith('inst_') || node.listChildren().length) return;
    const parent = node.getParentNode();
    if (!parent) return;
    const key = mesh;
    if (!groups.has(key)) groups.set(key, new Map());
    const byParent = groups.get(key);
    if (!byParent.has(parent)) byParent.set(parent, []);
    byParent.get(parent).push(node);
  });
}
let batches = 0, count = 0;
for (const [mesh, byParent] of groups) {
  for (const [parent, nodes] of byParent) {
    if (nodes.length < min) continue;
    const buffer = mesh.listPrimitives()[0].getAttribute('POSITION').getBuffer();
    const n = nodes.length;
    const T = new Float32Array(3 * n), R = new Float32Array(4 * n), S = new Float32Array(3 * n);
    const inv = invert(parent.getWorldMatrix());
    nodes.forEach((node, i) => {
      const local = mul(inv, node.getWorldMatrix());
      const t = [0, 0, 0], r = [0, 0, 0, 1], s = [1, 1, 1];
      MathUtils.decompose(local, t, r, s);
      T.set(t, 3 * i); R.set(r, 4 * i); S.set(s, 3 * i);
    });
    const acc = (type, arr) => doc.createAccessor().setType(type).setArray(arr).setBuffer(buffer);
    const batch = ext.createInstancedMesh()
      .setAttribute('TRANSLATION', acc('VEC3', T))
      .setAttribute('ROTATION', acc('VEC4', R))
      .setAttribute('SCALE', acc('VEC3', S));
    // the Blender mesh is already named inst_<key> (vlib.PropSet.proto): strip any inst_ prefixes so the batch
    // is inst_<key>, never inst_inst_<key>
    const base = (mesh.getName() || `mesh_${batches}`).replace(/^(inst_)+/, '');
    const name = 'inst_' + base;
    const bn = doc.createNode(name).setMesh(mesh).setExtension('EXT_mesh_gpu_instancing', batch);
    parent.addChild(bn);
    for (const node of nodes) node.dispose();
    batches++; count += n;
  }
}
if (!batches) ext.dispose();
await io.write(output, doc);
console.log(`instanced ${input}: ${batches} batches, ${count} instances`);
