// Web packing for the organizer's skinned figures: Blender export in, market glb out.
//
//   node blender/people/pack.mjs in.glb out.glb [--lite] [--rest-opt] [--texture-size 256] [--keep-still]
//
// It runs the same web passes as the carpenter's blender/lib/optimize.mjs (dedup, weld, prune, sparse, WebP,
// meshopt; names kept) but handles the animations itself, because in a 5k-triangle figure the clips' glTF JSON
// was most of the file (every channel costs a channel, a sampler and one or two accessors, ~300 bytes of JSON):
//
// 1. Keys: the Blender exporter samples every frame. rig.bake_clip keys every `step` frames with linear
//    interpolation, so keeping only those frames loses nothing. All channels of a clip then share one time
//    accessor (optimize.mjs's resample() gives every channel its own).
// 2. --rest-opt: move each bone's default rotation (the node's glTF rotation; the skin's bind pose lives in
//    inverseBindMatrices and does not change) to the pose it holds still in the most clips, e.g. the left arm
//    hanging at the side. Clips that did not animate that bone get a one-key channel holding the old default,
//    so every clip plays exactly as before. Unanimated, the figure now stands arms down instead of in T-pose.
// 3. Channels that never leave the node's default are dropped; channels that hold still elsewhere become one key.
//    --lite uses coarser thresholds (about 1.6 degrees, 8 mm): lite figures are drawn far away or on phones.
//
// --keep-still skips 2 and the dropping in 3 (the shared clip library, whose channels must all be explicit for
// retargeting onto figures whose bone defaults differ).
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dedup, weld, prune, sparse, textureCompress, reorder, quantize } = require('@gltf-transform/functions');
const { EXTMeshoptCompression } = require('@gltf-transform/extensions');
const { MeshoptEncoder, MeshoptDecoder } = require('meshoptimizer');
const sharp = require('sharp');

const args = process.argv.slice(2);
const pos = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1] === '--texture-size'));
const [input, output] = pos;
const lite = args.includes('--lite');
const restOpt = args.includes('--rest-opt');
const keepStill = args.includes('--keep-still');
const ti = args.indexOf('--texture-size');
const texSize = ti >= 0 ? parseInt(args[ti + 1], 10) : lite ? 128 : 256;
const FPS = 24;
// keys every `step` frames, as rig.bake_clip wrote them (build.py: walks 2, everything else 3); lite keeps every
// other key of the slow clips (4 per second)
const stepFor = (name) => (/^walk/.test(name) ? 2 : lite ? 6 : 3);

await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(input);
const root = doc.getRoot();

const EPS = lite ? { translation: 8e-3, rotation: 1e-4, scale: 2e-3 } : { translation: 5e-5, rotation: 1.5e-5, scale: 2e-4 };
const qdist = (a, i, b, j) => {
  let dot = 0;
  for (let k = 0; k < 4; k++) dot += a[i + k] * b[j + k];
  return 1 - Math.abs(dot);
};
const restOf = (node, path) => (path === 'translation' ? node.getTranslation() : path === 'rotation' ? node.getRotation() : node.getScale());
function maxDist(out, n, path, ref) {
  let d = 0;
  for (let i = 0; i < out.length; i += n) {
    if (path === 'rotation') d = Math.max(d, qdist(out, i, ref, 0));
    else for (let k = 0; k < n; k++) d = Math.max(d, Math.abs(out[i + k] - ref[k]));
  }
  return d;
}

// ---- 1. keep the baked keys only, one shared time accessor per clip
let keysBefore = 0, keysAfter = 0;
for (const anim of root.listAnimations()) {
  const step = stepFor(anim.getName());
  const cache = new Map();
  for (const s of anim.listSamplers()) {
    const inp = s.getInput(), out = s.getOutput();
    const t = inp.getArray();
    const n = out.getElementSize();
    keysBefore += t.length;
    const last = t.length - 1;
    const keep = [];
    for (let i = 0; i <= last; i++) {
      const f = Math.round(t[i] * FPS);
      if (f % step === 0 || i === last) keep.push(i);
    }
    const key = keep.map((i) => t[i].toFixed(5)).join(',');
    if (!cache.has(key)) cache.set(key, doc.createAccessor().setType('SCALAR').setArray(new Float32Array(keep.map((i) => t[i]))));
    const src = out.getArray();
    const dst = new Float32Array(keep.length * n);
    keep.forEach((i, k) => { for (let c = 0; c < n; c++) dst[k * n + c] = src[i * n + c]; });
    s.setInput(cache.get(key));
    s.setOutput(doc.createAccessor().setType(out.getType()).setArray(dst));
    keysAfter += keep.length;
  }
}

// ---- 2. bone defaults at the most common still pose
let moved = 0, added = 0;
const SEATED = /^(sit|play|rest)/;
// held poses keep two keys, 0 and the clip's end, so a clip whose every channel holds still keeps its length
// (three.js takes a clip's duration from its last key; a zero-length looping clip plays NaN)
const ends = new Map();
const span = (a) => {
  if (!ends.has(a)) {
    const d = Math.max(...a.listSamplers().map((s) => s.getInput().getMax([])[0]));
    ends.set(a, doc.createAccessor().setType('SCALAR').setArray(new Float32Array([0, d])));
  }
  return ends.get(a);
};
const held = (v) => new Float32Array([...v, ...v]);
const isStill = (s, path) => {
  const out = s.getOutput().getArray();
  const n = s.getOutput().getElementSize();
  return maxDist(out, n, path, Array.from(out.slice(0, n))) <= EPS[path] * 0.5;
};
if (restOpt && !keepStill) {
  const anims = root.listAnimations();
  for (const node of root.listNodes()) {
    const byAnim = new Map();
    for (const a of anims) byAnim.set(a, a.listChannels().find((c) => c.getTargetNode() === node && c.getTargetPath() === 'rotation') || null);
    const still = [];
    // only standing clips may set the default, so an unanimated figure (a glTF viewer) stands rather than sits
    for (const [a, ch] of byAnim) if (ch && !SEATED.test(a.getName()) && isStill(ch.getSampler(), 'rotation')) still.push(Array.from(ch.getSampler().getOutput().getArray().slice(0, 4)));
    if (!still.length) continue;
    const missing = [...byAnim.values()].filter((c) => !c).length;
    let best = null, bestN = 0;
    for (const q of still) {
      const n = still.filter((p) => qdist(p, 0, q, 0) <= EPS.rotation * 0.5).length;
      if (n > bestN) { best = q; bestN = n; }
    }
    if (bestN <= missing) continue;
    const old = node.getRotation();
    for (const [a, ch] of byAnim) {
      if (ch) continue;
      const s = doc.createAnimationSampler().setInput(span(a)).setOutput(doc.createAccessor().setType('VEC4').setArray(held(old))).setInterpolation('LINEAR');
      a.addSampler(s).addChannel(doc.createAnimationChannel().setTargetNode(node).setTargetPath('rotation').setSampler(s));
      added++;
    }
    const len = Math.hypot(...best);
    node.setRotation(best.map((v) => v / len));
    moved++;
  }
}

// ---- 3. drop channels at the default (not in the library); still channels become two keys
let dropped = 0, kept = 0, single = 0;
for (const anim of root.listAnimations()) {
  for (const ch of anim.listChannels()) {
    const node = ch.getTargetNode(), path = ch.getTargetPath(), s = ch.getSampler();
    if (!['translation', 'rotation', 'scale'].includes(path)) { kept++; continue; }
    const rest = restOf(node, path);
    // the library keeps every rotation (retargeting needs them explicit) but no translation or scale at rest
    if ((!keepStill || path !== 'rotation') && maxDist(s.getOutput().getArray(), rest.length, path, rest) <= EPS[path]) { ch.dispose(); s.dispose(); dropped++; continue; }
    kept++;
    if (s.getInput().getCount() > 2 && isStill(s, path)) {
      const o = s.getOutput();
      s.setInput(span(anim)).setOutput(doc.createAccessor().setType(o.getType()).setArray(held(o.getArray().slice(0, o.getElementSize()))));
      single++;
    }
  }
}

// ---- 4. one vertex buffer per mesh: the primitives (one per material: coat, body, hat, scarf) share their
// attribute accessors and differ only in indices, which saves ~25 accessors and their buffer views. One skin for
// the body and the mug (the exporter writes one per object, with the same joints).
function mergePrimitives() {
for (const mesh of root.listMeshes()) {
  const prims = mesh.listPrimitives();
  if (prims.length < 2) continue;
  const sems = prims[0].listSemantics();
  if (!prims.every((p) => p.getIndices() && p.listSemantics().join() === sems.join())) continue;
  const total = prims.reduce((n, p) => n + p.getAttribute('POSITION').getCount(), 0);
  const merged = {};
  for (const sem of sems) {
    const a0 = prims[0].getAttribute(sem);
    const arr = new (a0.getArray().constructor)(total * a0.getElementSize());
    let o = 0;
    for (const p of prims) { const a = p.getAttribute(sem).getArray(); arr.set(a, o); o += a.length; }
    merged[sem] = doc.createAccessor().setType(a0.getType()).setArray(arr).setNormalized(a0.getNormalized());
  }
  let base = 0;
  for (const p of prims) {
    const cnt = p.getAttribute('POSITION').getCount();
    const idx = p.getIndices().getArray();
    const ni = new Uint32Array(idx.length);
    for (let i = 0; i < idx.length; i++) ni[i] = idx[i] + base;
    p.setIndices(doc.createAccessor().setType('SCALAR').setArray(total < 65536 ? Uint16Array.from(ni) : ni));
    for (const sem of sems) p.setAttribute(sem, merged[sem]);
    base += cnt;
  }
}
}
{
  const skinned = root.listNodes().filter((n) => n.getSkin());
  const skin0 = skinned[0]?.getSkin();
  const same = (a, b) => a.listJoints().length === b.listJoints().length && a.listJoints().every((j, i) => j === b.listJoints()[i]);
  for (const n of skinned) if (n.getSkin() !== skin0 && same(n.getSkin(), skin0)) n.setSkin(skin0);
}

// meshopt({level: 'high'}) is reorder + quantize + the EXT_meshopt_compression filter method; it is spelled
// out here so the primitives can be merged after quantize
await doc.transform(
  dedup(),
  weld(),
  prune({ keepLeaves: true, keepAttributes: false, keepSolidTextures: false }),
  reorder({ encoder: MeshoptEncoder, target: 'size' }),
  quantize({
    pattern: /^(POSITION|TEXCOORD|JOINTS|WEIGHTS|COLOR)(_\d+)?$/,
    patternTargets: /^(POSITION|TEXCOORD|JOINTS|WEIGHTS|COLOR|NORMAL|TANGENT)(_\d+)?$/,
    quantizeNormal: 8,
  }),
);
// after quantize, which gives small primitives their own compacted vertices
mergePrimitives();
if (process.env.PACK_DEBUG) for (const m of root.listMeshes()) console.log(m.getName(), m.listPrimitives().map((p) => root.listAccessors().indexOf(p.getAttribute('POSITION')) + ':' + p.getAttribute('POSITION').getCount()).join(' '));
await doc.transform(
  prune({ keepLeaves: true, keepAttributes: false, keepSolidTextures: false }),
  sparse(),
  textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [texSize, texSize], quality: 82, effort: 90 }),
);
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.FILTER });
await io.write(output, doc);
console.log(`pack${lite ? ' (lite)' : ''}: keys ${keysBefore} -> ${keysAfter}; channels kept ${kept} (${single} held), dropped ${dropped}` +
  (restOpt ? `; ${moved} bone defaults moved, ${added} held channels added` : ''));
