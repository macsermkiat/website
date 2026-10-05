// The Bratwürste on the swinging grate. Round 10 (ADR 0004 revision) merged them into one mesh, `sausages_grill`
// under `act_grill_swing`, so they ride the swing and cost one draw. To turn them one by one again, this module
// cuts that mesh into its sausages at load: each sausage is a connected piece of the mesh (welded by position), and
// pieces whose boxes touch are one sausage. Every piece becomes its own Mesh that shares the merged geometry's
// vertex buffers and has only its own triangles in a new index, so the GPU holds the vertices once. A stand-in grill
// (a group of separate sausage meshes) needs no cutting.
//
// Each sausage turns about its own long axis through its middle, with a small hop, as tongs would turn it. The
// sausages are not clickable one by one (ADR 0004 revision): the stall's "Turn the sausages" button turns the whole
// grate in a ripple (actions/items/wurst.js).
import * as THREE from 'three';
import { worldDirToParent, UP } from './common.js';

const WELD = 1e-3; // mesh-local units: vertices closer than this are one (seams in the glTF split them)

/** Cut a merged mesh into its pieces: [{ index: Uint32Array, box: Box3 }] in the mesh's own frame. */
export function splitIslands(geo) {
  const pos = geo.attributes.position;
  const n = pos.count;
  const idx = geo.index ? geo.index.array : Uint32Array.from({ length: n }, (_, i) => i);
  // weld by position
  const key = new Map(), weld = new Int32Array(n);
  for (let i = 0; i < n; i++) {
    const k = `${Math.round(pos.getX(i) / WELD)},${Math.round(pos.getY(i) / WELD)},${Math.round(pos.getZ(i) / WELD)}`;
    let w = key.get(k);
    if (w === undefined) { w = key.size; key.set(k, w); }
    weld[i] = w;
  }
  const parent = Int32Array.from({ length: key.size }, (_, i) => i);
  const find = (a) => { while (parent[a] !== a) { parent[a] = parent[parent[a]]; a = parent[a]; } return a; };
  const join = (a, b) => { a = find(a); b = find(b); if (a !== b) parent[b] = a; };
  for (let t = 0; t < idx.length; t += 3) { join(weld[idx[t]], weld[idx[t + 1]]); join(weld[idx[t]], weld[idx[t + 2]]); }
  const groups = new Map();
  const v = new THREE.Vector3();
  for (let t = 0; t < idx.length; t += 3) {
    const r = find(weld[idx[t]]);
    let g = groups.get(r);
    if (!g) groups.set(r, (g = { tris: [], box: new THREE.Box3() }));
    g.tris.push(idx[t], idx[t + 1], idx[t + 2]);
    for (let k = 0; k < 3; k++) g.box.expandByPoint(v.fromBufferAttribute(pos, idx[t + k]));
  }
  // pieces of one sausage (a cap, a grill mark) touch its body: merge pieces whose boxes overlap
  let list = [...groups.values()];
  for (let changed = true; changed;) {
    changed = false;
    for (let i = 0; i < list.length && !changed; i++) for (let j = i + 1; j < list.length; j++) {
      const a = list[i].box, b = list[j].box;
      const small = a.getSize(new THREE.Vector3()).length() < b.getSize(new THREE.Vector3()).length() ? a : b;
      const big = small === a ? b : a;
      // one inside the other, or a small piece touching a big one
      if (big.containsBox(small) || (big.intersectsBox(small) && small.getSize(v).length() < big.getSize(new THREE.Vector3()).length() * 0.6)) {
        list[i].tris.push(...list[j].tris);
        list[i].box.union(list[j].box);
        list.splice(j, 1);
        changed = true;
        break;
      }
    }
  }
  return list.map((g) => ({ index: Uint32Array.from(g.tris), box: g.box }));
}

/** A geometry that draws only `index` of `geo`'s vertices (shared buffers), with its own bounds. */
function pieceGeometry(geo, index, box) {
  const g = new THREE.BufferGeometry();
  for (const [k, a] of Object.entries(geo.attributes)) g.setAttribute(k, a);
  g.setIndex(new THREE.BufferAttribute(index, 1));
  const b = box.clone(), s = b.getBoundingSphere(new THREE.Sphere());
  g.boundingBox = b;
  g.boundingSphere = s;
  // the bounds come from this piece's triangles, not from every vertex of the shared buffers
  g.computeBoundingBox = function () { this.boundingBox = b.clone(); };
  g.computeBoundingSphere = function () { this.boundingSphere = s.clone(); };
  g.userData.piece = true;
  return g;
}

/**
 * The grill's sausages as separately turnable pieces. `root` is the `sausages_grill` node (or the stand-in's
 * separate `sausages_grill` meshes, as an array).
 * Returns { list: [{ mesh, pivot, axis, angle, turns }], turn(i, opts), rebuild() } or null.
 */
export function createGrillSausages(root, { anim }) {
  const roots = (Array.isArray(root) ? root : [root]).filter(Boolean);
  if (!roots.length) return null;
  const list = [];
  // a stand-in grill: separate sausage meshes already
  const loose = [];
  for (const r of roots) r.traverse((o) => { if (o.isMesh && !o.userData.itemFx && !o.userData.grillPiece && !loose.includes(o)) loose.push(o); });
  const merged = loose.length === 1 ? loose[0] : null;
  if (merged) build(merged);
  else for (const m of loose) list.push(wrapLoose(m));
  if (!list.length) return null;

  function build(src) {
    const pieces = splitIslands(src.geometry);
    // one piece is no cut at all; dozens means the mesh is not sausages
    if (pieces.length < 2 || pieces.length > 40) { list.push(wrapLoose(src)); return; }
    pieces.sort((a, b) => a.box.min.x - b.box.min.x || a.box.min.z - b.box.min.z);
    src.visible = false;
    src.userData.grillSource = true;
    pieces.forEach((p, i) => {
      const wrap = new THREE.Group();
      wrap.name = `grill_sausage_wrap_${i}`;
      wrap.position.copy(src.position); wrap.quaternion.copy(src.quaternion); wrap.scale.copy(src.scale);
      const c = p.box.getCenter(new THREE.Vector3());
      const pivot = new THREE.Group();
      pivot.position.copy(c);
      const mesh = new THREE.Mesh(pieceGeometry(src.geometry, p.index, p.box), src.material);
      mesh.name = `grill_sausage_${i}`;
      mesh.position.copy(c).negate();
      mesh.castShadow = src.castShadow; mesh.receiveShadow = src.receiveShadow;
      mesh.userData.grillPiece = true;
      mesh.userData.label = 'Bratwurst on the grill';
      pivot.add(mesh); wrap.add(pivot);
      src.parent.add(wrap);
      const s = p.box.getSize(new THREE.Vector3());
      list.push({ mesh, pivot, wrap, c0: c.clone(), axis: s.x >= s.z ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1), angle: 0, turns: 0, q0: new THREE.Quaternion() });
    });
    // the full model grafted on later (engine/stream.js) brings a finer mesh: cut it the same way
    src.userData.afterGraft = () => refit(src);
  }
  function wrapLoose(m) {
    // a mesh of its own: turn it in place about its middle
    m.geometry.computeBoundingBox();
    const box = m.geometry.boundingBox, c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
    const pivot = new THREE.Group();
    pivot.name = `${m.name || 'sausage'}_pivot`;
    m.parent.add(pivot);
    pivot.position.copy(m.position).add(c.clone().multiply(m.scale).applyQuaternion(m.quaternion));
    pivot.quaternion.copy(m.quaternion);
    pivot.scale.copy(m.scale);
    pivot.add(m);
    m.position.copy(c).negate(); m.quaternion.identity(); m.scale.set(1, 1, 1);
    if (!/^grill_sausage/.test(m.name)) m.name = `grill_sausage_${list.length}`;
    m.userData.grillPiece = true;
    m.userData.label = 'Bratwurst on the grill';
    const ax = s.x >= s.y && s.x >= s.z ? new THREE.Vector3(1, 0, 0) : s.y >= s.z ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
    return { mesh: m, pivot, axis: ax, angle: 0, turns: 0, q0: pivot.quaternion.clone(), c0: pivot.position.clone(), loose: true };
  }
  function refit(src) {
    const pieces = splitIslands(src.geometry);
    if (pieces.length !== list.length) return; // a different cut: keep the lite pieces, which still turn
    pieces.sort((a, b) => a.box.min.x - b.box.min.x || a.box.min.z - b.box.min.z);
    pieces.forEach((p, i) => {
      const s = list[i];
      s.mesh.geometry = pieceGeometry(src.geometry, p.index, p.box);
      s.mesh.material = src.material;
      const c = p.box.getCenter(new THREE.Vector3());
      s.wrap.position.copy(src.position); s.wrap.quaternion.copy(src.quaternion); s.wrap.scale.copy(src.scale);
      s.pivot.position.copy(c); s.c0.copy(c);
      s.mesh.position.copy(c).negate();
    });
  }

  const q = new THREE.Quaternion();
  return {
    list,
    /**
     * Turn sausage i half over about its long axis, hopping a little; `done(s)` when it lies again.
     * Returns false when it is already turning.
     */
    turn(i, { delay = 0, done } = {}) {
      const s = list[i];
      if (!s || s.busy) return false;
      s.busy = true;
      const a0 = s.angle;
      s.angle += Math.PI;
      s.turns++;
      const base = s.loose ? s.q0 : null;
      // the hop is in metres, up in the world, whatever the frame of the pivot
      const up = worldDirToParent(s.pivot, UP);
      const pose = (a, hop) => {
        q.setFromAxisAngle(s.axis, a);
        if (base) s.pivot.quaternion.copy(base).multiply(q); else s.pivot.quaternion.copy(q);
        s.pivot.position.copy(s.c0).addScaledVector(up, hop);
      };
      anim.add(0.5, (k) => pose(a0 + k * Math.PI, Math.sin(k * Math.PI) * 0.045), () => { pose(s.angle, 0); s.busy = false; done?.(s); }, delay);
      return true;
    },
    angleOf: (i) => list[i]?.angle ?? null,
  };
}
