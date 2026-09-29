// Places prop sets at slot_ empties, as listed in site/public/models/props.json (owned by the vendor).
// Accepted shapes (the first that matches wins):
//   { "<stall>": { "slot_counter": "props/mugs.glb" | ["a.glb", ...] | { "model": "a.glb", "position": [..], "rotation": .. } } }
//   { "sets": [ { "stall": "gluehwein", "slot": "slot_counter", "model": "props/mugs.glb" } ] }   (or a top-level array)
import * as THREE from 'three';
import inventory from 'virtual:market-inventory';
import { loadGlb } from './loader.js';
import { liteVariant, modelExists } from '../layout.js';
import { placeFor } from '../places.js';

function rel(url) {
  return String(url).replace(/^(\.\/|\/)+/, '').replace(/^(site\/)?(public\/)?/, '').replace(/^models\//, '');
}

function normalise(json) {
  const out = [];
  const push = (owner, slot, spec) => {
    const specs = Array.isArray(spec) ? spec : [spec];
    for (const s of specs) {
      const model = typeof s === 'string' ? s : s?.model || s?.glb || s?.file || s?.src;
      if (!model) continue;
      out.push({ owner: String(owner), slot: String(slot).toLowerCase().startsWith('slot_') ? String(slot).toLowerCase() : `slot_${String(slot).toLowerCase()}`, model: rel(model), offset: s?.position || s?.offset || null, rotation: Number(s?.rotation ?? s?.ry) || 0, scale: Number(s?.scale) || 1 });
    }
  };
  const list = Array.isArray(json) ? json : Array.isArray(json?.sets) ? json.sets : Array.isArray(json?.props) ? json.props : null;
  if (list) {
    for (const e of list) push(e.stall ?? e.owner ?? e.place ?? e.target ?? '', e.slot ?? 'slot_counter', e.model ? e : e.models ?? e);
  } else if (json && typeof json === 'object') {
    for (const [owner, slots] of Object.entries(json)) {
      if (!slots || typeof slots !== 'object' || Array.isArray(slots)) continue;
      for (const [slot, spec] of Object.entries(slots)) push(owner, slot, spec);
    }
  }
  return out;
}

/** placed: [{ entry, root, nodes }]. Loads and parents props; never throws. */
export async function placeProps(placed, { lite, manager, warn, elsewhere = [] }) {
  const json = inventory.props;
  if (!json) return 0;
  const items = normalise(json);
  const cache = new Map();
  let n = 0;
  await Promise.all(items.map(async (it) => {
    const owns = (e, file) => e.id.toLowerCase() === it.owner.toLowerCase() || (e.place && e.place === placeFor(it.owner)) || (file && file.toLowerCase().includes(it.owner.toLowerCase()));
    const target = placed.find((p) => owns(p.entry, p.file));
    // a set for a stall loaded in the other batch (the lite market loads the deco stalls after its first frame)
    if (!target && elsewhere.some((e) => owns(e, e.lite) || owns(e, e.model))) return;
    if (!target) return warn(`props.json: no stall called "${it.owner}".`);
    const slot = target.nodes.slots[it.slot];
    if (!slot) return warn(`props.json: ${it.owner} has no ${it.slot}.`);
    const file = (lite && liteVariant(it.model)) || it.model;
    if (!modelExists(file)) return warn(`props.json: ${file} is not in public/models.`);
    try {
      if (!cache.has(file)) cache.set(file, loadGlb(file, manager));
      const src = await cache.get(file);
      const obj = src.parent ? src.clone(true) : src;
      if (it.offset) obj.position.fromArray(it.offset.length === 3 ? it.offset : [it.offset[0], 0, it.offset[1]]);
      obj.rotation.y += it.rotation;
      obj.scale.multiplyScalar(it.scale);
      obj.name = obj.name || `prop_${file}`;
      obj.userData.propFile = file; // which file a set came from (for debugging and tests)
      slot.add(obj);
      n++;
    } catch (e) {
      warn(`props.json: could not load ${file} (${e?.message || e}).`);
    }
  }));
  return n;
}
