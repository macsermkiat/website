// Draw-call savings for rows of small act_ goods (the vendor's books: about a hundred spines, one mesh each).
// The meshes under each prop set are merged into one mesh per material; the act_ nodes stay where they were,
// with their own meshes hidden, as pick proxies (a raycast still hits a hidden mesh) and as the pivots the
// actions move. While a book is out of the shelf, its own mesh shows and its copy in the merged mesh is
// collapsed; when it is back, the merged copy returns.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

/** A float, non-interleaved copy of the attributes the merge needs (quantized glb attributes decoded). */
function floatGeometry(src, names) {
  const g = new THREE.BufferGeometry();
  for (const name of names) {
    const a = src.getAttribute(name);
    const n = a.count, size = a.itemSize;
    const out = new Float32Array(n * size);
    // getX..getW decode normalized (quantized) values, interleaved or not
    const get = [(i) => a.getX(i), (i) => a.getY(i), (i) => a.getZ(i), (i) => a.getW(i)];
    for (let i = 0; i < n; i++) for (let k = 0; k < size; k++) out[i * size + k] = get[k](i);
    g.setAttribute(name, new THREE.BufferAttribute(out, size));
  }
  if (src.index) g.setIndex(Array.from(src.index.array));
  else g.setIndex([...Array(src.getAttribute('position').count).keys()]);
  return g;
}

const texKey = (t) => (t ? `${t.source?.uuid || t.uuid}:${t.offset.x},${t.offset.y},${t.repeat.x},${t.repeat.y},${t.rotation},${t.channel ?? 0}` : '-');
/** Materials that draw the same get the same key (their names may differ). */
function materialLook(m) {
  const c = (x) => (x?.isColor ? x.getHexString() : '-');
  return [m.type, c(m.color), c(m.emissive), m.emissiveIntensity, m.roughness, m.metalness, m.opacity, m.transparent, m.alphaTest, m.side, m.vertexColors, m.flatShading,
    texKey(m.map), texKey(m.normalMap), texKey(m.roughnessMap), texKey(m.metalnessMap), texKey(m.aoMap), texKey(m.emissiveMap), texKey(m.alphaMap),
    m.normalScale ? `${m.normalScale.x},${m.normalScale.y}` : '-', m.aoMapIntensity ?? '-', m.envMapIntensity ?? '-'].join('|');
}

/**
 * Merge the act_ meshes whose pivot name matches `re` under `root`, one merged mesh per (parent, material).
 * Returns { groups, lift(node), settle(node), count } or null when there is nothing worth merging.
 */
export function mergeActMeshes(root, re, { minCount = 6 } = {}) {
  root.updateMatrixWorld(true);
  // pivot -> its meshes (the pivot itself may be the mesh, or hold an act_x_mesh child)
  const pivots = [];
  root.traverse((o) => { if (re.test(o.name || '') && !/_mesh(\.\d+)?$/i.test(o.name)) pivots.push(o); });
  if (pivots.length < minCount) return null;

  // group by the set the pivot belongs to (its parent) and by what the material looks like: the vendor gives
  // every book its own cover material (book_cover_<n>) so it can be found by name, but they all sample one
  // texture, so they draw the same and can share one merged mesh
  const buckets = new Map();
  const owner = new Map(); // mesh -> { bucket, start, count }
  for (const pivot of pivots) {
    pivot.traverse((m) => {
      if (!m.isMesh || m.isSkinnedMesh || Array.isArray(m.material) || m.morphTargetInfluences) return;
      const key = `${pivot.parent.uuid}|${materialLook(m.material)}`;
      if (!buckets.has(key)) buckets.set(key, { parent: pivot.parent, material: m.material, items: [] });
      buckets.get(key).items.push({ pivot, mesh: m });
    });
  }
  const groups = [];
  const inv = new THREE.Matrix4();
  for (const b of buckets.values()) {
    if (b.items.length < 2) continue;
    const names = ['position', 'normal', 'uv', 'uv1', 'tangent', 'color'].filter((n) => b.items.every(({ mesh }) => mesh.geometry.getAttribute(n)));
    if (!names.includes('position')) continue;
    inv.copy(b.parent.matrixWorld).invert();
    const geos = [];
    let offset = 0;
    for (const it of b.items) {
      const g = floatGeometry(it.mesh.geometry, names);
      g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, it.mesh.matrixWorld));
      const count = g.index.count;
      it.range = { start: offset, count };
      offset += count;
      geos.push(g);
    }
    const merged = mergeGeometries(geos, false);
    geos.forEach((g) => g.dispose());
    if (!merged) continue;
    merged.computeBoundingSphere();
    merged.computeBoundingBox();
    const mesh = new THREE.Mesh(merged, b.material);
    mesh.name = `merged_${b.items[0].pivot.name.replace(/_\d+$/, '')}s`;
    mesh.castShadow = b.items[0].mesh.castShadow;
    mesh.receiveShadow = b.items[0].mesh.receiveShadow;
    mesh.userData.merged = true;
    b.parent.add(mesh);
    const saved = merged.index.array.slice();
    for (const it of b.items) {
      it.mesh.visible = false; // stays in the tree: the pick proxy and the thing the action moves
      owner.set(it.mesh, { mesh, range: it.range, saved });
    }
    groups.push({ mesh, count: b.items.length });
  }
  if (!groups.length) return null;

  const meshesOf = (pivot) => { const out = []; pivot.traverse((m) => { if (owner.has(m)) out.push(m); }); return out; };
  function setRange(m, show) {
    const o = owner.get(m);
    const idx = o.mesh.geometry.index;
    const { start, count } = o.range;
    if (show) idx.array.set(o.saved.subarray(start, start + count), start);
    else idx.array.fill(idx.array[start], start, start + count); // degenerate triangles: nothing drawn
    idx.addUpdateRange(start, count);
    idx.needsUpdate = true;
  }
  return {
    groups,
    count: owner.size,
    /** Take a pivot out of the merged mesh (its own mesh draws, so it can move). */
    lift(pivot) { for (const m of meshesOf(pivot)) { setRange(m, false); m.visible = true; } },
    /** Put it back once it is home again. */
    settle(pivot) { for (const m of meshesOf(pivot)) { m.visible = false; setRange(m, true); } },
    /** Leave a mesh out of the merged mesh for good (its own mesh is then drawn, or hidden, by its owner). */
    drop(m) { if (!owner.has(m)) return; setRange(m, false); owner.delete(m); },
  };
}

// ---------------------------------------------------------------------------------------------------------
// Static merge: fewer draw calls for everything that never moves on its own.
//
// Inside one placed model, meshes that draw the same (same material, or materials that look the same) are
// merged into one mesh per "rigid body". A rigid body is the model root, or a node that moves as a whole:
// rot_ (the wheel, the platform), gondola_, horse_ and instrument_. Its merged meshes stay its children, so a
// gondola still swings and the wheel still turns with everything on it.
// Never merged: act_ nodes an action uses (marked userData.live by actions/util.js; the rest of the act_
// nodes, such as the vendor's rows of mugs and bottles, are static), snow_ (toggled), bulbs_ and bulb materials (the
// lighting module finds them by name), skinned or instanced meshes, morph targets, meshes the model's own
// animation clips move, hidden meshes, and anything the engine or the lighting module added (engine_,
// action_, effect_, lighting_, pool_ and the musicians).
// Emissive materials (windows, embers) are only merged with the very same material object, because the
// lighting module and the actions change those materials while the market runs.

const SKIP = /^(snow_|bulbs_|musician_|lighting_|engine_|action_|effect_|item_|open_|band_pick_|pool_|merged_)/i;
const skipNode = (o) => SKIP.test(o.name || '') || o.userData.live || o.userData.pickProxy;
const ANCHOR = /^(rot_|gondola_|horse_|instrument_)/i;
const ATTRS = ['position', 'normal', 'uv', 'uv1', 'uv2', 'tangent', 'color'];
const defaultBeforeRender = THREE.Object3D.prototype.onBeforeRender;

function liveMaterial(m) {
  if (m.userData?.bulb || /^bulb_/i.test(m.name || '') || m.userData?.baseEmissive != null) return true;
  const glows = m.emissive && m.emissive.getHex() !== 0 && (m.emissiveIntensity ?? 1) > 0;
  return !!(glows || m.emissiveMap);
}

function eligible(o) {
  if (!o.isMesh || o.isSkinnedMesh || o.isInstancedMesh || o.isPoints || o.isLine) return false;
  if (o.morphTargetInfluences || o.userData.merged || o.userData.bulbs || o.userData.keep) return false;
  if (o.onBeforeRender !== defaultBeforeRender) return false;
  const m = o.material;
  if (!m || Array.isArray(m) || !o.geometry?.getAttribute('position')) return false;
  if (/^bulb_/i.test(m.name || '') || m.userData?.bulb || /^lighting_/i.test(m.name || '')) return false;
  return true;
}

/** Nodes an animation clip of this model moves (their subtrees are left alone). */
function animatedNames(root) {
  const out = new Set();
  for (const clip of root.userData.animations || []) {
    for (const t of clip.tracks) out.add(t.name.split('.')[0]);
  }
  return out;
}

function mergeItems(items, frame) {
  const names = ATTRS.filter((n) => items[0].mesh.geometry.getAttribute(n));
  const inv = new THREE.Matrix4().copy(frame.matrixWorld).invert();
  const geos = [];
  for (const it of items) {
    const g = floatGeometry(it.mesh.geometry, names);
    const m = new THREE.Matrix4().multiplyMatrices(inv, it.mesh.matrixWorld);
    g.applyMatrix4(m);
    // a mirrored mesh: three flips its front face while drawing; baked in, the winding has to flip instead
    if (m.determinant() < 0) {
      const a = g.index.array;
      for (let i = 0; i < a.length; i += 3) { const t = a[i + 1]; a[i + 1] = a[i + 2]; a[i + 2] = t; }
    }
    geos.push(g);
  }
  const merged = mergeGeometries(geos, false);
  geos.forEach((g) => g.dispose());
  if (!merged) return null;
  merged.computeBoundingSphere();
  merged.computeBoundingBox();
  const first = items[0].mesh;
  const mesh = new THREE.Mesh(merged, first.material);
  mesh.castShadow = first.castShadow;
  mesh.receiveShadow = first.receiveShadow;
  mesh.renderOrder = first.renderOrder;
  mesh.frustumCulled = first.frustumCulled;
  mesh.layers.mask = first.layers.mask;
  mesh.userData.merged = true;
  return mesh;
}

function bucketKey(o, anchorId) {
  const m = o.material;
  const look = liveMaterial(m) ? `id:${m.uuid}` : materialLook(m);
  const attrs = ATTRS.filter((n) => o.geometry.getAttribute(n)).join(',');
  return `${anchorId}|${look}|${o.castShadow ? 1 : 0}${o.receiveShadow ? 1 : 0}|${o.renderOrder}|${o.frustumCulled ? 1 : 0}|${o.layers.mask}|${attrs}`;
}

/**
 * Merge the static meshes of one placed model (see above). Returns { before, after } mesh counts.
 * `extraSkip(o)` may protect more nodes (with their subtrees).
 */
export function mergeStatic(root, { extraSkip = null } = {}) {
  root.updateMatrixWorld(true);
  const moving = animatedNames(root);
  const buckets = new Map();
  let before = 0;
  const bulbs = new Map();
  const walk = (o, anchor) => {
    if (o !== root) {
      // bulb strings: merged among themselves (same material object only), after the lighting module has read
      // them; the merged mesh keeps the bulbs_ name and flag, so picking and the lighting still know it
      if (o.visible && /^bulbs_/i.test(o.name || '') && !o.userData.live && !moving.has(o.name)) {
        o.traverse((m) => {
          if (!m.isMesh || !m.visible || m.isSkinnedMesh || m.isInstancedMesh || Array.isArray(m.material) || m.morphTargetInfluences) return;
          before++;
          const key = `${anchor.uuid}|${m.material.uuid}|${ATTRS.filter((n) => m.geometry.getAttribute(n)).join(',')}`;
          if (!bulbs.has(key)) bulbs.set(key, { anchor, items: [] });
          bulbs.get(key).items.push({ mesh: m, node: o });
        });
        return;
      }
      if (!o.visible || skipNode(o) || moving.has(o.name) || extraSkip?.(o)) return;
      if (ANCHOR.test(o.name || '')) anchor = o;
    }
    if (o.isMesh) before++;
    if (eligible(o)) {
      const key = bucketKey(o, anchor.uuid);
      if (!buckets.has(key)) buckets.set(key, { anchor, items: [] });
      buckets.get(key).items.push({ mesh: o });
    }
    for (const c of o.children) walk(c, anchor);
  };
  walk(root, root);
  let removed = 0;
  for (const b of buckets.values()) {
    if (b.items.length < 2) continue;
    const mesh = mergeItems(b.items, b.anchor);
    if (!mesh) continue;
    mesh.name = `merged_${b.items[0].mesh.material.name || 'mesh'}`;
    b.anchor.add(mesh);
    for (const it of b.items) it.mesh.removeFromParent();
    removed += b.items.length - 1;
  }
  for (const b of bulbs.values()) {
    if (b.items.length < 2) continue;
    const mesh = mergeItems(b.items, b.anchor);
    if (!mesh) continue;
    mesh.name = 'bulbs_merged';
    mesh.userData.bulbs = true;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    b.anchor.add(mesh);
    for (const it of b.items) it.mesh.visible = false; // the bulbs_ nodes stay (the lighting module knows them)
    removed += b.items.length - 1;
  }
  return { before, after: before - removed };
}

/**
 * Riders (the Riesenrad's gondolas, the carousel's horses) are built alike: each part of every rider is drawn
 * as one instance of an InstancedMesh, one per part, instead of one mesh per part per rider. Parts are matched
 * by material and shape (sampled vertices, in the rider's own frame); a part that differs keeps its own mesh.
 * The rider nodes still move as before (makeRides); `sync()` copies their poses into the instances, once per
 * frame after the rides have moved. The original meshes stay, hidden, for the seat and picking code.
 * Returns { sync, parts, riders } or null.
 */
export function instanceRiders(riders, frame) {
  if (riders.length < 2) return null;
  const inv = new THREE.Matrix4();
  // a rider's parts, each with its pose and bounds in the rider's own frame. The meshopt export orders (and
  // sometimes welds) the vertices of each copy differently, so parts are matched by material, triangle count
  // and bounds, not vertex by vertex.
  const partsOf = (r) => {
    r.updateWorldMatrix(true, true);
    inv.copy(r.matrixWorld).invert();
    const out = [];
    r.traverse((m) => {
      if (!m.isMesh || !m.visible || m.isSkinnedMesh || m.isInstancedMesh || Array.isArray(m.material) || m.morphTargetInfluences) return;
      for (let p = m.parent; p && p !== r; p = p.parent) if (p.userData.live || !p.visible) return;
      const local = new THREE.Matrix4().multiplyMatrices(inv, m.matrixWorld);
      const g = m.geometry;
      if (!g.boundingBox) g.computeBoundingBox();
      const box = g.boundingBox.clone().applyMatrix4(local);
      out.push({ mesh: m, local, box, key: `${m.material.uuid}|${g.index ? g.index.count : g.getAttribute('position').count}` });
    });
    return out.sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : a.box.min.x - b.box.min.x || a.box.min.y - b.box.min.y || a.box.min.z - b.box.min.z));
  };
  const near = (a, b) => a.distanceToSquared(b) < 4e-6; // 2 mm
  const same = (A, B) => A.length === B.length && A.every((a, i) => a.key === B[i].key && near(a.box.min, B[i].box.min) && near(a.box.max, B[i].box.max));
  // riders built alike form a class (the carousel has a few horse designs; the wheel's gondolas are one class)
  const classes = [];
  for (const r of riders) {
    const parts = partsOf(r);
    if (!parts.length) continue;
    const c = classes.find((k) => same(k.parts, parts));
    if (c) c.members.push({ r, parts }); else classes.push({ parts, members: [{ r, parts }] });
  }
  const insts = [];
  let saved = 0;
  for (const c of classes) {
    if (c.members.length < 2) continue;
    c.parts.forEach((first, k) => {
      const im = new THREE.InstancedMesh(first.mesh.geometry, first.mesh.material, c.members.length);
      im.name = `riders_${first.mesh.material.name || 'part'}`;
      im.castShadow = first.mesh.castShadow;
      im.receiveShadow = first.mesh.receiveShadow;
      im.frustumCulled = false; // the instances move; the geometry's bounds say nothing about them
      if (first.mesh.userData.bulbs) im.userData.bulbs = true;
      frame.add(im);
      c.members.forEach((mb) => { mb.parts[k].mesh.visible = false; });
      insts.push({ im, local: first.local, riders: c.members.map((mb) => mb.r) });
      saved += c.members.length - 1;
    });
  }
  const parts = insts;
  if (!parts.length) return null;
  const m = new THREE.Matrix4(), frameInv = new THREE.Matrix4();
  function sync() {
    frame.updateWorldMatrix(true, false);
    frameInv.copy(frame.matrixWorld).invert();
    for (const r of riders) r.updateWorldMatrix(true, false);
    for (const p of parts) {
      p.riders.forEach((r, i) => { m.multiplyMatrices(frameInv, r.matrixWorld).multiply(p.local); p.im.setMatrixAt(i, m); });
      p.im.instanceMatrix.needsUpdate = true;
    }
  }
  sync();
  return { sync, parts: parts.length, riders: riders.length, classes: classes.length, saved };
}

/**
 * Merge across several models that share a texture kit (the nine deco stalls and their goods): the meshes
 * that hang directly off each model's root (not a rigid body of its own) and draw the same become one mesh
 * for the whole row, in world space, under `into`. Returns how many draw calls that saved.
 */
export function mergeAcross(roots, into) {
  const buckets = new Map();
  for (const root of roots) {
    root.updateMatrixWorld(true);
    const moving = animatedNames(root);
    const walk = (o) => {
      if (o !== root && (!o.visible || skipNode(o) || ANCHOR.test(o.name || '') || moving.has(o.name))) return;
      if (eligible(o) && !liveMaterial(o.material)) {
        const key = bucketKey(o, 'world');
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push({ mesh: o });
      }
      for (const c of o.children) walk(c);
    };
    walk(root);
  }
  into.updateMatrixWorld(true);
  let saved = 0;
  for (const items of buckets.values()) {
    if (items.length < 2) continue;
    const mesh = mergeItems(items, into);
    if (!mesh) continue;
    mesh.name = `merged_row_${items[0].mesh.material.name || 'mesh'}`;
    into.add(mesh);
    for (const it of items) it.mesh.removeFromParent();
    saved += items.length - 1;
  }
  return saved;
}

/**
 * The warm pools on the ground (one quad per light_ the budget did not light) drawn as one instanced mesh per
 * material instead of one draw each. The originals stay in the scene, hidden, so whoever made them can still
 * remove them. Returns the instanced meshes made.
 */
export function instancePools(pools, scene) {
  const groups = new Map();
  for (const p of pools) {
    if (!p?.isMesh || !p.visible || p.isInstancedMesh) continue;
    const key = `${p.geometry.uuid}|${p.material.uuid}|${p.renderOrder}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(p);
  }
  const out = [];
  for (const list of groups.values()) {
    if (list.length < 2) continue;
    const im = new THREE.InstancedMesh(list[0].geometry, list[0].material, list.length);
    im.name = 'pools_instanced';
    im.renderOrder = list[0].renderOrder;
    im.raycast = () => {};
    im.frustumCulled = false;
    list.forEach((p, i) => { p.updateMatrixWorld(true); im.setMatrixAt(i, p.matrixWorld); p.visible = false; });
    im.instanceMatrix.needsUpdate = true;
    scene.add(im);
    out.push(im);
  }
  return out;
}
