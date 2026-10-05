// Places prop sets at slot_ empties, as listed in site/public/models/props.json (owned by the vendor).
// Accepted shapes (the first that matches wins):
//   { "<stall>": { "slot_counter": "props/mugs.glb" | ["a.glb", ...] | { "model": "a.glb", "position": [..], "rotation": .. } } }
//   { "sets": [ { "stall": "gluehwein", "slot": "slot_counter", "model": "props/mugs.glb" } ] }   (or a top-level array)
import * as THREE from 'three';
import inventory from 'virtual:market-inventory';
import { loadGlb } from './loader.js';
import { liteVariant, modelExists } from '../layout.js';

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
      out.push({ set: s?.set || null, lite: s?.lite ? rel(s.lite) : null, asset: s?.asset ? rel(s.asset) : null, owner: String(owner), slot: String(slot).toLowerCase().startsWith('slot_') ? String(slot).toLowerCase() : `slot_${String(slot).toLowerCase()}`, model: rel(model), offset: s?.position || s?.offset || null, rotation: Number(s?.rotation ?? s?.ry) || 0, scale: Number(s?.scale) || 1 });
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

/**
 * placed: [{ entry, root, nodes }]. Loads and parents props; never throws.
 * Bindings are exact: a set's `stall` is a layout.json id, its `slot` a slot_ empty in that stall's model, its
 * `model` and `lite` files in public/models, and its `asset` (when given) the file that stall is built from.
 * Anything else is reported (warn + `bindings`), never guessed.
 */
export async function placeProps(placed, { lite, liteOf = null, manager, warn, elsewhere = [], bindings = [] }) {
  const json = inventory.props;
  if (!json) return 0;
  const items = normalise(json);
  const cache = new Map();
  let n = 0;
  const bad = (it, problem) => { bindings.push({ set: it.set || it.model, stall: it.owner, problem }); warn(`props.json: ${it.set || it.model}: ${problem}`); };
  await Promise.all(items.map(async (it) => {
    const owns = (e) => e.id === it.owner;
    const target = placed.find((p) => owns(p.entry));
    // a set for a stall loaded in the other batch (both markets load the deco stalls after the first frame)
    if (!target && elsewhere.some(owns)) return;
    if (!target) return bad(it, `no layout entry with id "${it.owner}".`);
    if (it.asset && target.entry.model && it.asset !== target.entry.model) bad(it, `says stall "${it.owner}" is ${it.asset}, but layout.json builds it from ${target.entry.model}.`);
    const slot = target.nodes.slots[it.slot];
    if (!slot && target.source === 'standin') return; // a stand-in stall without that shelf
    if (!slot) return bad(it, `${target.file} has no ${it.slot}.`);
    let file = it.model;
    // streaming: a stall that opens lite on the full market takes its props lite too, and grafts the full ones later
    const useLite = lite || !!liteOf?.(target.entry);
    if (useLite) {
      if (it.lite && modelExists(it.lite)) file = it.lite;
      else if (it.lite && modelExists(it.model)) bad(it, `lite file ${it.lite} is not in site/public/models; the lite market loads ${it.model}.`);
      else if (it.lite) return bad(it, `neither ${it.lite} nor ${it.model} is in site/public/models.`);
      else file = liteVariant(it.model) || it.model;
    }
    if (!modelExists(file)) return bad(it, `${file} is not in site/public/models.`);
    try {
      if (!cache.has(file)) cache.set(file, loadGlb(file, manager));
      const src = await cache.get(file);
      const obj = src.parent ? src.clone(true) : src;
      if (it.offset) obj.position.fromArray(it.offset.length === 3 ? it.offset : [it.offset[0], 0, it.offset[1]]);
      obj.rotation.y += it.rotation;
      obj.scale.multiplyScalar(it.scale);
      obj.name = obj.name || `prop_${file}`;
      obj.userData.propFile = file; // which file a set came from (for debugging and tests)
      obj.userData.propSet = it.set || file.replace(/(\.lite)?\.glb$/, '');
      if (useLite && !lite && file !== it.model && !target.entry.liteOnly) obj.userData.fullFile = it.model;
      slot.add(obj);
      n++;
    } catch (e) {
      bad(it, `could not load ${file} (${e?.message || e}).`);
    }
  }));
  return n;
}
