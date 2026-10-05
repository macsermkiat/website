// Seat check: do the vendor's prop sets sit on their stall without cutting into it?
//
//   node blender/props/seat_check.mjs jobs.json        (jobs: [{set, prop, stall, slot}], glb paths)
//
// Each stall glb is decoded and moved into the frame of the set's slot_ empty (Blender axes: x right,
// y back, z up, origin on the slot). Then, for every prop set:
//   - collisions: every prop triangle is tested against the stall triangles near it (Moeller's
//     triangle-triangle test). A pair counts when the triangles really cross and the part of the prop's
//     triangle over the stall face reaches more than EPS behind it (its outward side from the CCW
//     winding), so goods resting on a board pass and anything that cuts into the counter, the firebox,
//     a post or a brace fails. Reported per act_ node (or "static") with that depth.
//     Goods sunk whole under a top (the counter, the hearth plate), where no faces cross, are caught
//     by a height field of the up-facing level faces near the slot height.
//   - support: the level stall surfaces within 1.2 cm of the slot height under the set (the counter top
//     or shelf board) give the board's y-range; the set's bounding box must stay inside it, so nothing
//     hangs past the counter's back edge.
// Prints one JSON object: {set: {collisions: [{node, depth, at}], support: {...}, bbox: {...}}}.
import { createRequire } from 'module';
import { execSync } from 'child_process';
import fs from 'fs';

const globalRoot = execSync('npm root -g').toString().trim();
const require = createRequire(`${globalRoot}/@gltf-transform/cli/package.json`);
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dequantize } = require('@gltf-transform/functions');
const { MeshoptDecoder } = require('meshoptimizer');

const CELL = 0.005, EPS = 0.003, SUPPORT_TOL = 0.012;

await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const cache = new Map();

async function load(path) {
  if (!cache.has(path)) {
    const doc = await io.read(path);
    await doc.transform(dequantize());
    cache.set(path, doc);
  }
  return cache.get(path);
}

// column-major 4x4 helpers
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
  // affine inverse: [R t] -> [R^-1  -R^-1 t]
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
function xf(m, x, y, z) {
  return [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13],
    m[2] * x + m[6] * y + m[10] * z + m[14]];
}
// glTF (x, y up, z front) -> Blender (x, y back, z up)
const toB = (p) => [p[0], -p[2], p[1]];

// every mesh node's triangles (Blender axes) in the frame `frame` (a glTF world matrix to invert),
// with the name of the nearest act_ / rot_ ancestor (or "static")
function triangles(doc, frame) {
  const F = frame ? inv(frame) : null;
  const out = [];
  const parentOf = new Map();
  for (const n of doc.getRoot().listNodes()) for (const c of n.listChildren()) parentOf.set(c, n);
  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    let owner = 'static', p = node;
    while (p) {
      const nm = p.getName() || '';
      if ((nm.startsWith('act_') || nm.startsWith('rot_')) && !nm.endsWith('_mesh')) { owner = nm; break; }
      p = parentOf.get(p);
    }
    const W0 = F ? mul(F, node.getWorldMatrix()) : node.getWorldMatrix();
    // round 9: an EXT_mesh_gpu_instancing node draws its mesh once per instance (TRS relative to the node)
    const batch = node.getExtension('EXT_mesh_gpu_instancing');
    const Ws = batch ? instanceMatrices(batch).map((M) => mul(W0, M)) : [W0];
    for (const W of Ws) for (const prim of mesh.listPrimitives()) {
      if (prim.getMode() !== 4) continue;
      const pos = prim.getAttribute('POSITION').getArray();
      const idx = prim.getIndices() ? prim.getIndices().getArray() : null;
      const vs = [];
      for (let i = 0; i < pos.length; i += 3) vs.push(toB(xf(W, pos[i], pos[i + 1], pos[i + 2])));
      const n = idx ? idx.length : vs.length;
      const tris = [];
      for (let i = 0; i < n; i += 3) {
        tris.push(idx ? [vs[idx[i]], vs[idx[i + 1]], vs[idx[i + 2]]] : [vs[i], vs[i + 1], vs[i + 2]]);
      }
      out.push({ owner, verts: vs, tris });
    }
  }
  return out;
}

function instanceMatrices(batch) {
  const T = batch.getAttribute('TRANSLATION'), R = batch.getAttribute('ROTATION'), S = batch.getAttribute('SCALE');
  const n = (T || R || S).getCount();
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = T ? T.getElement(i, []) : [0, 0, 0];
    const [x, y, z, w] = R ? R.getElement(i, []) : [0, 0, 0, 1];
    const s = S ? S.getElement(i, []) : [1, 1, 1];
    out.push([
      (1 - 2 * (y * y + z * z)) * s[0], (2 * (x * y + z * w)) * s[0], (2 * (x * z - y * w)) * s[0], 0,
      (2 * (x * y - z * w)) * s[1], (1 - 2 * (x * x + z * z)) * s[1], (2 * (y * z + x * w)) * s[1], 0,
      (2 * (x * z + y * w)) * s[2], (2 * (y * z - x * w)) * s[2], (1 - 2 * (x * x + y * y)) * s[2], 0,
      t[0], t[1], t[2], 1]);
  }
  return out;
}

function findNode(doc, name) {
  return doc.getRoot().listNodes().find((n) => n.getName() === name);
}


const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

function plane(t) {
  const n = cross(sub(t[1], t[0]), sub(t[2], t[0]));
  const L = Math.hypot(...n);
  if (L < 1e-12) return null;
  const u = [n[0] / L, n[1] / L, n[2] / L];
  return { n: u, d: -dot(u, t[0]), area: L / 2 };
}

// interval of triangle t along direction D where it meets the other plane (distances ds)
function interval(t, ds, D) {
  const ps = t.map((v) => dot(v, D));
  const pts = [];
  for (let i = 0; i < 3; i++) {
    const j = (i + 1) % 3;
    if (ds[i] === 0) pts.push(ps[i]);
    if ((ds[i] > 0 && ds[j] < 0) || (ds[i] < 0 && ds[j] > 0)) pts.push(ps[i] + (ps[j] - ps[i]) * ds[i] / (ds[i] - ds[j]));
  }
  return pts.length ? [Math.min(...pts), Math.max(...pts)] : null;
}

// the part of polygon P over triangle B (inside the prism its edges sweep along its normal)
function clipToPrism(P, B, n) {
  let poly = P;
  for (let e = 0; e < 3 && poly.length; e++) {
    const p = B[e], q = B[(e + 1) % 3], r = B[(e + 2) % 3];
    let m = cross(n, sub(q, p));
    if (dot(m, sub(r, p)) < 0) m = [-m[0], -m[1], -m[2]];
    const side = (x) => dot(m, sub(x, p));
    const out = [];
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length];
      const sa = side(a), sb = side(b);
      if (sa >= 0) out.push(a);
      if ((sa >= 0) !== (sb >= 0)) {
        const t = sa / (sa - sb);
        out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]);
      }
    }
    poly = out;
  }
  return poly;
}

// how deep the prop's triangle A cuts into the stall's triangle B (0 = apart, or only resting on it).
// The triangles must really cross (Moeller's interval test); the depth is how far the part of A that
// lies over B reaches behind B's outward face (glTF winding is CCW, so the stall's normals point out).
function cutDepth(A, pA, B, pB) {
  const da = A.map((v) => dot(pB.n, v) + pB.d);
  if (Math.min(...da) >= -EPS || Math.max(...da) <= 0) return 0;
  const db = B.map((v) => dot(pA.n, v) + pA.d);
  if (Math.min(...db) >= 0 || Math.max(...db) <= 0) return 0;
  const D = cross(pA.n, pB.n);
  const L = Math.hypot(...D);
  if (L < 1e-6) return 0;
  const ia = interval(A, da, D), ib = interval(B, db, D);
  if (!ia || !ib || (Math.min(ia[1], ib[1]) - Math.max(ia[0], ib[0])) / L <= 1e-4) return 0;
  const over = clipToPrism(A, B, pB.n);
  if (!over.length) return 0;
  const depth = -Math.min(...over.map((v) => dot(pB.n, v) + pB.d));
  return depth > EPS ? depth : 0;
}

async function job({ set, prop, stall, slot }) {
  const sdoc = await load(stall);
  const slotNode = findNode(sdoc, slot);
  if (!slotNode) return { error: `${slot} not in ${stall}` };
  const pdoc = await load(prop);
  const propParts = triangles(pdoc, null);
  const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
  for (const part of propParts) for (const v of part.verts) for (let k = 0; k < 3; k++) {
    lo[k] = Math.min(lo[k], v[k]); hi[k] = Math.max(hi[k], v[k]);
  }
  // stall triangles near the set, in a uniform grid
  const G = 0.05, M = 0.02;
  const gx0 = lo[0] - M, gy0 = lo[1] - 0.3, gz0 = lo[2] - M;
  const gnx = Math.ceil((hi[0] - gx0 + M) / G), gny = Math.ceil((hi[1] + 0.3 - gy0) / G), gnz = Math.ceil((hi[2] - gz0 + M) / G);
  const grid = new Map();
  const range = (t) => {
    const r = [];
    for (let k = 0; k < 3; k++) {
      const mn = Math.min(t[0][k], t[1][k], t[2][k]), mx = Math.max(t[0][k], t[1][k], t[2][k]);
      r.push([mn, mx]);
    }
    return r;
  };
  const cells = (r) => {
    const o = [[gx0, gnx], [gy0, gny], [gz0, gnz]].map(([g0, gn], k) =>
      [Math.max(0, Math.floor((r[k][0] - g0) / G)), Math.min(gn - 1, Math.floor((r[k][1] - g0) / G))]);
    return o;
  };
  const stallTris = [];
  let x0 = lo[0] - M, y0 = lo[1] - 0.3;
  const nx = Math.ceil((hi[0] - lo[0] + 2 * M) / CELL), ny = Math.ceil((hi[1] - lo[1] + 0.6) / CELL);
  const field = new Float32Array(nx * ny).fill(-1e9);
  const tops = new Float32Array(nx * ny).fill(-1e9);       // up-facing level faces near the slot height
  const raster = (t, fn) => {
    const [a, b, cc] = t;
    const d = (b[1] - cc[1]) * (a[0] - cc[0]) + (cc[0] - b[0]) * (a[1] - cc[1]);
    if (Math.abs(d) < 1e-12) return;
    const i0 = Math.max(0, Math.floor((Math.min(a[0], b[0], cc[0]) - x0) / CELL));
    const i1 = Math.min(nx - 1, Math.floor((Math.max(a[0], b[0], cc[0]) - x0) / CELL));
    const j0 = Math.max(0, Math.floor((Math.min(a[1], b[1], cc[1]) - y0) / CELL));
    const j1 = Math.min(ny - 1, Math.floor((Math.max(a[1], b[1], cc[1]) - y0) / CELL));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const px = x0 + (i + 0.5) * CELL, py = y0 + (j + 0.5) * CELL;
      const l1 = ((b[1] - cc[1]) * (px - cc[0]) + (cc[0] - b[0]) * (py - cc[1])) / d;
      const l2 = ((cc[1] - a[1]) * (px - cc[0]) + (a[0] - cc[0]) * (py - cc[1])) / d;
      const l3 = 1 - l1 - l2;
      if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
      fn(j * nx + i, l1 * a[2] + l2 * b[2] + l3 * cc[2]);
    }
  };
  for (const part of triangles(sdoc, slotNode.getWorldMatrix())) {
    for (const t of part.tris) {
      const r = range(t);
      if (r[0][1] < gx0 || r[0][0] > gx0 + gnx * G || r[1][1] < gy0 || r[1][0] > gy0 + gny * G ||
          r[2][1] < gz0 || r[2][0] > gz0 + gnz * G) continue;
      const pl = plane(t);
      if (!pl || pl.area < 1e-8) continue;
      const id = stallTris.length;
      stallTris.push({ t, pl, r });
      const c = cells(r);
      for (let i = c[0][0]; i <= c[0][1]; i++) for (let j = c[1][0]; j <= c[1][1]; j++) for (let k = c[2][0]; k <= c[2][1]; k++) {
        const key = (k * gny + j) * gnx + i;
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(id);
      }
      // the support board: level faces within SUPPORT_TOL of the slot height
      if (Math.abs(pl.n[2]) > 0.98 && Math.abs(r[2][0]) < SUPPORT_TOL && Math.abs(r[2][1]) < SUPPORT_TOL) {
        raster(t, (k) => { field[k] = 0; });
      }
      // tops: up-facing level faces from 2 cm below to 10 cm above the slot (counter, hearth plate, rims)
      if (pl.n[2] > 0.9 && r[2][0] > -0.02 && r[2][1] < 0.1) {
        raster(t, (k, z) => { if (z > tops[k]) tops[k] = z; });
      }
    }
  }
  const worst = new Map();
  let tested = 0;
  for (const part of propParts) {
    for (const t of part.tris) {
      const pl = plane(t);
      if (!pl) continue;
      const r = range(t);
      const c = cells(r);
      const seen = new Set();
      for (let i = c[0][0]; i <= c[0][1]; i++) for (let j = c[1][0]; j <= c[1][1]; j++) for (let k = c[2][0]; k <= c[2][1]; k++) {
        const ids = grid.get((k * gny + j) * gnx + i);
        if (!ids) continue;
        for (const id of ids) {
          if (seen.has(id)) continue;
          seen.add(id);
          const S = stallTris[id];
          if (S.r[0][1] < r[0][0] || S.r[0][0] > r[0][1] || S.r[1][1] < r[1][0] || S.r[1][0] > r[1][1] ||
              S.r[2][1] < r[2][0] || S.r[2][0] > r[2][1]) continue;
          tested++;
          const depth = cutDepth(t, pl, S.t, S.pl);
          if (depth > 0 && (!worst.has(part.owner) || depth > worst.get(part.owner).depth)) {
            const cen = [0, 1, 2].map((k) => +((t[0][k] + t[1][k] + t[2][k]) / 3).toFixed(3));
            worst.set(part.owner, { node: part.owner, depth: +depth.toFixed(4), at: cen });
            if (process.env.SEAT_DEBUG) worst.get(part.owner).pair = [t, S.t].map((q) => q.map((v) => v.map((c) => +c.toFixed(4))));
          }
        }
      }
    }
  }
  // goods sunk right under a top (fully inside the counter or the firebox, so no face crosses): a
  // vertex up to 12 cm below the lowest top in the 3x3 cells round it
  for (const part of propParts) {
    for (const v of part.verts) {
      const i = Math.floor((v[0] - x0) / CELL), j = Math.floor((v[1] - y0) / CELL);
      let t = 1e9;
      for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
        const ii = i + di, jj = j + dj;
        t = Math.min(t, ii < 0 || jj < 0 || ii >= nx || jj >= ny ? -1e9 : tops[jj * nx + ii]);
      }
      const depth = t - v[2];
      if (t > -1e8 && depth > EPS && depth < 0.12 && (!worst.has(part.owner) || depth > worst.get(part.owner).depth)) {
        worst.set(part.owner, { node: part.owner, depth: +depth.toFixed(4), at: v.map((c) => +c.toFixed(3)), sunk: true });
      }
    }
  }
  let sy0 = 1e9, sy1 = -1e9, sx0 = 1e9, sx1 = -1e9;
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    if (field[j * nx + i] < -1e8) continue;
    const px = x0 + (i + 0.5) * CELL, py = y0 + (j + 0.5) * CELL;
    if (px < lo[0] || px > hi[0]) continue;
    sy0 = Math.min(sy0, py); sy1 = Math.max(sy1, py); sx0 = Math.min(sx0, px); sx1 = Math.max(sx1, px);
  }
  const support = sy0 < 1e8 ? { y_min: +(sy0 - CELL / 2).toFixed(3), y_max: +(sy1 + CELL / 2).toFixed(3),
    x_min: +(sx0 - CELL / 2).toFixed(3), x_max: +(sx1 + CELL / 2).toFixed(3) } : null;
  return {
    collisions: [...worst.values()].sort((a, b) => b.depth - a.depth),
    support,
    bbox: { min: lo.map((c) => +c.toFixed(3)), max: hi.map((c) => +c.toFixed(3)) },
    pairs_tested: tested,
  };
}

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
const out = {};
for (const j of jobs) {
  try {
    out[j.set] = await job(j);
  } catch (e) {
    out[j.set] = { error: String(e) };
  }
}
console.log(JSON.stringify(out));
