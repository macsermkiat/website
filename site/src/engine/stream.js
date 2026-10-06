// Streaming (docs/adr/0003): the full market opens with the lite models of the stalls and landmarks, and a place
// gets its full-detail model only when it is the current or the next stop of the stroll.
//
// The upgrade is a graft. A stall's .glb and .lite.glb have the same node tree (same names, same order; checked
// in tests/unit.mjs; the town and the tree may have extra detail nodes in full, which are moved over whole), so the full model's meshes are moved onto the lite model's nodes: geometry and material
// (and the dequantising transform of each mesh node) change, while every node the actions, items, lights and
// slots hold stays the same object. Engine-changed materials (glowing bulbs, the grill's embers) are kept.
// Then the place's static meshes are merged, as they would have been at load.
import * as THREE from 'three';
import { loadGlb } from './loader.js';
import { modelExists } from '../layout.js';

/** True for an object the glTF loader made for a node (not one the engine added later). */
const isGltf = (o) => !!o.userData?.gltfNode || o.userData?.gltfNode === 0;

/**
 * The mesh objects that draw one glTF node: the node itself when it is a Mesh, plus its primitive children
 * (a multi-material mesh is a Group of Meshes that are not nodes themselves).
 */
function primitivesOf(o) {
  const out = [];
  if (o.isMesh) out.push(o);
  for (const c of o.children) if (c.isMesh && c.userData?.gltfPrimitive && !isGltf(c)) out.push(c);
  return out;
}

const keepMaterial = (m) => !m || !m.userData?.fromGlb || m.userData.bulb || m.userData.baseEmissive != null || /^bulb_/i.test(m.name || '');

/**
 * Move the full tree's drawing onto the lite tree, node by node (matched by name among siblings).
 * Returns { meshes, nodes } counts and `added`, the full-only nodes moved over.
 */
export function graft(lite, full) {
  let meshes = 0, nodes = 0;
  const visit = (a, b) => {
    nodes++;
    const pa = primitivesOf(a), pb = primitivesOf(b);
    if (pb.length) {
      // the dequantising transform lives on the mesh node: take the full model's
      if (a.isMesh || b.isMesh) { a.position.copy(b.position); a.quaternion.copy(b.quaternion); a.scale.copy(b.scale); }
      const n = Math.min(pa.length, pb.length);
      for (let i = 0; i < n; i++) {
        const x = pa[i], y = pb[i];
        x.geometry = y.geometry;
        if (x.material?.userData?.readGlow && y.material && !Array.isArray(y.material)) {
          // a writing surface's reading-glow copy (world/surfaces.js readGlow) stays the same object, which the
          // reader brightens, and takes the full model's textures
          const g = x.material;
          for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap']) if (k in y.material) g[k] = y.material[k];
          g.emissiveMap = g.map || null;
          g.vertexColors = !!y.material.vertexColors;
          g.needsUpdate = true;
        } else if (!keepMaterial(x.material)) x.material = y.material;
        if (x !== a) { x.position.copy(y.position); x.quaternion.copy(y.quaternion); x.scale.copy(y.scale); }
        meshes++;
      }
      // a mesh the full model splits into more primitives: the extra ones join the lite node
      for (let i = n; i < pb.length; i++) {
        const y = pb[i];
        const m = new THREE.Mesh(y.geometry, y.material);
        m.position.copy(y.position); m.quaternion.copy(y.quaternion); m.scale.copy(y.scale);
        m.castShadow = pa[0]?.castShadow ?? true; m.receiveShadow = pa[0]?.receiveShadow ?? true;
        m.userData.gltfPrimitive = true;
        a.add(m);
        meshes++;
      }
      for (let i = n; i < pa.length; i++) if (pa[i] !== a) pa[i].removeFromParent();
    }
    // children that are nodes, matched by name and order among same-named siblings
    const count = {};
    const fullKids = {};
    for (const c of b.children) if (isGltf(c)) (fullKids[c.name] ||= []).push(c);
    const used = new Set();
    for (const c of [...a.children]) {
      if (!isGltf(c)) continue;
      const k = (count[c.name] = (count[c.name] || 0) + 1) - 1;
      const m = fullKids[c.name]?.[k];
      if (m) { used.add(m); visit(c, m); }
    }
    // nodes only the full model has (the town's and the tree's lite files drop some detail nodes): moved over
    // whole; nothing in the engine holds them yet. A lite-only node stays as it is.
    for (const list of Object.values(fullKids)) for (const m of list) if (!used.has(m)) {
      a.add(m);
      added.push(m);
      m.traverse((o) => { if (o.isMesh) meshes++; });
    }
    // a node the engine dressed (a coaster's write_ card given the coaster's print) dresses itself again
    try { a.userData.afterGraft?.(); } catch (e) { console.warn('[stream] afterGraft', a.name, e); }
  };
  const added = [];
  visit(lite, full);
  return { meshes, nodes, added };
}

/**
 * The streamer. after(record, { failed }) runs once a placed model is upgraded (merge, lighting tune, picking).
 * A record is a placed layout entry { entry, root, source, streamed } (market.placed; a place's is place.record).
 */
export function createStreamer({ market, lite, warn, before, after, manager }) {
  const state = {}; // layout id -> 'lite' | 'loading' | 'full' | 'failed' | 'scenery' (a deco stall: its lite file, for good)
  const report = [];
  const pending = {};

  /** The parts to upgrade: the model and every prop or instrument loaded lite (they carry their full file). */
  function partsOf(rec) {
    const parts = [];
    if (rec.source === 'lite' && rec.entry.model && modelExists(rec.entry.model)) parts.push({ node: rec.root, full: rec.entry.model });
    rec.root.traverse((o) => {
      const f = o.userData?.fullFile;
      if (f && o !== rec.root && modelExists(f)) parts.push({ node: o, full: f });
    });
    return parts;
  }

  function upgradeRecord(rec) {
    const id = rec.entry.id;
    if (lite || !rec.streamed) return Promise.resolve(false);
    if (state[id] === 'full') return Promise.resolve(true);
    if (pending[id]) return pending[id];
    state[id] = 'loading';
    const t0 = performance.now();
    pending[id] = (async () => {
      const parts = partsOf(rec);
      let meshes = 0;
      try {
        const loaded = await Promise.all(parts.map((p) => loadGlb(p.full, manager).then((root) => ({ ...p, root }))));
        before?.(rec);
        for (const p of loaded) {
          const g = graft(p.node, p.root);
          meshes += g.meshes;
          // snow caps on moved-over nodes join the market's snow, so the Snow button reaches them
          for (const r of g.added) r.traverse((o) => { if (/^snow_/i.test(o.name || '') && market.snow && !market.snow.includes(o)) market.snow.push(o); });
        }
        rec.source = 'glb';
        rec.streamed = false;
        const place = rec.entry.place && market.places[rec.entry.place];
        if (place) { place.source = 'glb'; place.streamed = false; }
        state[id] = 'full';
        report.push({ id, files: parts.map((p) => p.full), meshes, ms: Math.round(performance.now() - t0) });
        after?.(rec, {});
        return true;
      } catch (e) {
        state[id] = 'failed';
        rec.streamed = false;
        warn?.(`streaming ${id}: ${e?.message || e}; it stays lite`);
        after?.(rec, { failed: true });
        return false;
      }
    })();
    return pending[id];
  }

  for (const rec of market.placed) state[rec.entry.id] = rec.streamed ? 'lite' : rec.entry.liteOnly ? 'scenery' : 'full';
  const recOf = (placeId) => market.places[placeId]?.record || null;
  return {
    upgradeRecord,
    /** Upgrade a place (by place id) to full detail. */
    upgrade: (placeId) => { const r = recOf(placeId); return r ? upgradeRecord(r) : Promise.resolve(false); },
    /** Upgrade the current stop and the next one (the stroll calls this on every move). */
    want(ids) { for (const id of ids) if (id) { const r = recOf(id); if (r) upgradeRecord(r); } },
    stateOf: (placeId) => state[recOf(placeId)?.entry.id] || null,
    state: () => ({ ...state }),
    report: () => report.slice(),
    track(records) { for (const rec of records) if (!(rec.entry.id in state)) state[rec.entry.id] = rec.streamed ? 'lite' : rec.entry.liteOnly ? 'scenery' : 'full'; },
  };
}
