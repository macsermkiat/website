// Grill probe: where is the Bratwurst stall's grill opening, measured in the frame of its slot_counter?
//
//   node blender/props/grill_probe.mjs [site/public/models/stall_bratwurst.glb] [slot_counter]
//
// The vendor's Schwenkgrill (prop_wurst_counter, act_grill) must stand in the stall's grill opening under
// the chimney hood. The carpenter owns the stall, so instead of hard-coding its numbers, set_wurst.py runs
// this probe at build time. Blender axes, metres, origin on the slot (the counter top):
//   hood:    x/y centre and x-range of the stall faces between 0.55 and 1.6 m above the counter, near the
//            left of the counter (the hood skirt and lip), or null when there is none
//   counter: the x-range of the counter top at the slot height along y = 0 (level faces within 1.2 cm)
//   opening: the gap in that top on the hood side: x0..x1 (x1 = where the counter top begins)
//   floor:   the highest up-facing stall surface round the hood's middle (between 1.1 m below and
//            6 cm above the counter): what the grill stands on, and its x/y extent at that height
//   slot_grill: the carpenter's slot_grill empty (where the grill stands), when the stall has one
// Prints one JSON object.
import { createRequire } from 'module';
import { execSync } from 'child_process';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dequantize } = require('@gltf-transform/functions');
const { MeshoptDecoder } = require('meshoptimizer');

const [stallPath = 'site/public/models/stall_bratwurst.glb', slotName = 'slot_counter'] = process.argv.slice(2);
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(stallPath);
await doc.transform(dequantize());

function mul(a, b) {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let s = 0;
    for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
    o[c * 4 + r] = s;
  }
  return o;
}
function inv(m) {
  const a = [m[0], m[1], m[2], m[4], m[5], m[6], m[8], m[9], m[10]];
  const det = a[0] * (a[4] * a[8] - a[5] * a[7]) - a[3] * (a[1] * a[8] - a[2] * a[7]) + a[6] * (a[1] * a[5] - a[2] * a[4]);
  const i = [
    (a[4] * a[8] - a[5] * a[7]) / det, (a[2] * a[7] - a[1] * a[8]) / det, (a[1] * a[5] - a[2] * a[4]) / det,
    (a[5] * a[6] - a[3] * a[8]) / det, (a[0] * a[8] - a[2] * a[6]) / det, (a[2] * a[3] - a[0] * a[5]) / det,
    (a[3] * a[7] - a[4] * a[6]) / det, (a[1] * a[6] - a[0] * a[7]) / det, (a[0] * a[4] - a[1] * a[3]) / det];
  const t = [m[12], m[13], m[14]];
  const o = [i[0], i[1], i[2], 0, i[3], i[4], i[5], 0, i[6], i[7], i[8], 0, 0, 0, 0, 1];
  o[12] = -(i[0] * t[0] + i[3] * t[1] + i[6] * t[2]);
  o[13] = -(i[1] * t[0] + i[4] * t[1] + i[7] * t[2]);
  o[14] = -(i[2] * t[0] + i[5] * t[1] + i[8] * t[2]);
  return o;
}
const xf = (m, x, y, z) => [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13],
  m[2] * x + m[6] * y + m[10] * z + m[14]];
const toB = (p) => [p[0], -p[2], p[1]];

const slot = doc.getRoot().listNodes().find((n) => n.getName() === slotName);
if (!slot) { console.log(JSON.stringify({ error: `${slotName} not in ${stallPath}` })); process.exit(0); }
const F = inv(slot.getWorldMatrix());
const tris = [];
for (const node of doc.getRoot().listNodes()) {
  const mesh = node.getMesh();
  if (!mesh) continue;
  const W = mul(F, node.getWorldMatrix());
  for (const prim of mesh.listPrimitives()) {
    if (prim.getMode() !== 4) continue;
    const pos = prim.getAttribute('POSITION').getArray();
    const idx = prim.getIndices() ? prim.getIndices().getArray() : null;
    const vs = [];
    for (let i = 0; i < pos.length; i += 3) vs.push(toB(xf(W, pos[i], pos[i + 1], pos[i + 2])));
    const n = idx ? idx.length : vs.length;
    const mat = prim.getMaterial() ? prim.getMaterial().getName() : '';
    for (let i = 0; i < n; i += 3) {
      const t = idx ? [vs[idx[i]], vs[idx[i + 1]], vs[idx[i + 2]]] : [vs[i], vs[i + 1], vs[i + 2]];
      t.mat = mat;
      tris.push(t);
    }
  }
}

// vertical ray down through (x, y): every hit z with the face's normal z (for "up-facing")
function hits(x, y) {
  const out = [];
  for (const [a, b, c] of tris) {
    const minx = Math.min(a[0], b[0], c[0]), maxx = Math.max(a[0], b[0], c[0]);
    const miny = Math.min(a[1], b[1], c[1]), maxy = Math.max(a[1], b[1], c[1]);
    if (x < minx || x > maxx || y < miny || y > maxy) continue;
    const d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]);
    if (Math.abs(d) < 1e-12) continue;
    const l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d;
    const l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d;
    const l3 = 1 - l1 - l2;
    if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
    const z = l1 * a[2] + l2 * b[2] + l3 * c[2];
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const nz = u[0] * v[1] - u[1] * v[0];
    const nl = Math.hypot(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], nz) || 1;
    out.push({ z, up: nz / nl });
  }
  return out;
}
const r3 = (v) => Math.round(v * 1000) / 1000;

// counter top at a few depths (between the plank joints): up-facing level faces at the slot height
const STEP = 0.01;
// plain counter at x: at every sampled depth the highest up-facing surface up to 40 cm above the slot is
// the counter top itself (nothing standing on it: no firebox rim, hearth plate or grill)
const topAt = (x) => [-0.17, -0.04, 0.05, 0.18].every((y) => {
  const up = hits(x, y).filter((h) => h.up > 0.3 && h.z > -0.05 && h.z < 0.4);
  if (!up.length) return false;
  const top = up.reduce((a, b) => (b.z > a.z ? b : a));
  return Math.abs(top.z) < 0.012 && top.up > 0.95;
});
// the counter's right end, then walk left along the top until it stops for 3 cm: that is where the
// counter begins (the grill opening lies left of it)
let cx0 = null, cx1 = null;
for (let x = 2.2; x > -2.2; x -= STEP) if (topAt(x)) { cx1 = x; break; }
if (cx1 !== null) {
  let miss = 0;
  cx0 = cx1;
  for (let x = cx1; x > -2.3; x -= STEP) {
    if (topAt(x)) { cx0 = x; miss = 0; } else if (++miss >= 3) break;
  }
}

// hood: iron faces 0.55..1.6 m up on the left half, over the front of the counter
let hx0 = 1e9, hx1 = -1e9, hy0 = 1e9, hy1 = -1e9, nh = 0;
for (const t of tris) {
  const zs = t.map((p) => p[2]);
  if (Math.min(...zs) < 0.55 || Math.max(...zs) > 1.6 || !/iron|hood/i.test(t.mat)) continue;
  const xs = t.map((p) => p[0]), ys = t.map((p) => p[1]);
  if (Math.max(...xs) > 0.3 || Math.min(...ys) < -0.6 || Math.max(...ys) > 0.9) continue;
  hx0 = Math.min(hx0, ...xs); hx1 = Math.max(hx1, ...xs); hy0 = Math.min(hy0, ...ys); hy1 = Math.max(hy1, ...ys); nh++;
}
const hood = nh ? { x0: r3(hx0), x1: r3(hx1), y0: r3(hy0), y1: r3(hy1), cx: r3((hx0 + hx1) / 2), cy: r3((hy0 + hy1) / 2), faces: nh } : null;

// the opening: from where the counter begins, left to the hood's left edge (or 1.6 m)
let opening = null;
if (cx0 !== null) {
  const x0 = hood ? Math.max(hood.x0, cx0 - 2.0) : cx0 - 1.6;
  opening = { x0: r3(x0), x1: r3(cx0), width: r3(cx0 - x0) };
}

// floor of the opening: the highest up-facing stall surface from 1.1 m below to 6 cm above the slot,
// sampled on a grid round the middle of the hood (or of the opening)
let floor = null;
const mx = hood ? hood.cx : opening ? (opening.x0 + opening.x1) / 2 : null;
if (mx !== null) {
  const zs = [];
  for (let dx = -0.2; dx <= 0.20001; dx += 0.05) for (const y of [-0.17, -0.12, -0.04, 0.05, 0.13, 0.18]) {
    const up = hits(mx + dx, y).filter((h) => h.up > 0.7 && h.z > -1.1 && h.z < 0.06);
    if (up.length) zs.push(Math.max(...up.map((h) => h.z)));
  }
  if (zs.length) {
    const z = Math.max(...zs);
    const onIt = (x, y) => hits(x, y).some((h) => h.up > 0.7 && Math.abs(h.z - z) < 0.012);
    // walk out from the middle until the surface stops (a plank joint of up to 2 cm does not stop it)
    const walk = (f, from, step, lim) => {
      let last = from, miss = 0;
      for (let v = from + step; step > 0 ? v < lim : v > lim; v += step) {
        if (f(v)) { last = v; miss = 0; } else if (++miss > 2) break;
      }
      return last;
    };
    const y0 = walk((y) => onIt(mx, y), -0.04, -0.01, -0.6), y1 = walk((y) => onIt(mx, y), -0.04, 0.01, 0.8);
    const fx0 = walk((x) => onIt(x, -0.04), mx, -0.01, mx - 1.2), fx1 = walk((x) => onIt(x, -0.04), mx, 0.01, mx + 1.2);
    floor = { z: r3(z), x0: r3(fx0), x1: r3(fx1), y0: r3(y0), y1: r3(y1), lowest: r3(Math.min(...zs)), samples: zs.length };
  }
}
// the carpenter's slot_grill empty (round 2): where the grill stands, in the slot frame
let slotGrill = null;
const sg = doc.getRoot().listNodes().find((n) => n.getName() === 'slot_grill');
if (sg) {
  const w = sg.getWorldMatrix();
  const p = toB(xf(F, w[12], w[13], w[14]));
  slotGrill = { x: r3(p[0]), y: r3(p[1]), z: r3(p[2]) };
}
console.log(JSON.stringify({ stall: stallPath, slot: slotName, counter: cx0 === null ? null : { x0: r3(cx0), x1: r3(cx1) }, opening, hood, floor, slot_grill: slotGrill }));
