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
  };
}
