// Assembles the market: loads every layout entry (glb or stand-in), places it, places props,
// and reads the node conventions into one registry the rest of the app works from.
import * as THREE from 'three';
import { resolveLayout } from '../layout.js';
import { loadEntry } from './loader.js';
import { placeProps } from './props.js';
import { scanNodes, lightBulbs, makeRides } from './conventions.js';
import { addStandinGoods } from './standinGoods.js';
import { placeInstruments } from './instruments.js';
import { mergeActMeshes } from './merge.js';

const LIGHT_CAP = { section: 2, deco: 1 };
const isInProp = (o, root) => { for (let x = o.parent; x && x !== root; x = x.parent) if (x.userData?.propFile) return true; return false; };
const ITEM_RE = /^act_(book|glass|mug|bottle|wineglass|roll|sausage)_/i;

async function pool(items, n, fn) {
  const out = new Array(items.length);
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, async () => {
    while (i < items.length) { const k = i++; out[k] = await fn(items[k], k); }
  }));
  return out;
}

/**
 * Load and place the market. `defer(entry)` picks entries to load only when `market.loadDeferred()` is called
 * (the lite market opens without the rides and the deco stalls, then adds them after its first frame).
 */
export async function buildMarket({ scene, lite, warn, onProgress, defer = () => false, stream = () => false }) {
  const layout = resolveLayout();
  layout.notes.forEach((n) => console.info('[layout]', n));
  const manager = new THREE.LoadingManager();
  const groundHasModel = layout.entries.some((e) => e.kind === 'ground' && e.model);
  const all = layout.entries.filter((e) => !(e.kind === 'strings' && !e.model && groundHasModel));
  const now = all.filter((e) => !defer(e));
  const later = all.filter((e) => defer(e));

  const market = {
    layout, placed: [], places: {}, bulbMaterials: [], snow: [], rides: [], lightSpots: [], mixers: [], propCount: 0, instrumentCount: 0,
    hotRoots: [], decoRoots: [], decos: {}, merges: {}, deferred: later.map((e) => e.id), report: [],
    // bindings that did not resolve exactly (layout.json assets, props.json sets): reported, never guessed
    bindings: [...layout.bindings],
    // other breaks of the BUILD.md contract found while loading (too many light_ markers)
    contract: [],
  };

  /** Load entries (four at a time) and add them to the scene. */
  async function load(entries, progress) {
    let done = 0;
    const placed = await pool(entries, 4, async (entry) => {
      const res = await loadEntry(entry, { lite: lite || !!stream(entry), manager, warn });
      progress?.(++done / entries.length, entry);
      return { entry, ...res, streamed: !lite && !!stream(entry) && res.source === 'lite' };
    });
    for (const p of placed) {
      const { entry, root } = p;
      const holder = new THREE.Group();
      holder.name = `place_${entry.id}`;
      holder.position.fromArray(entry.position);
      holder.rotation.y = entry.rotation || 0;
      holder.scale.setScalar(entry.scale || 1);
      holder.add(root);
      holder.userData.entry = entry;
      if (entry.place) holder.userData.place = entry.place;
      scene.add(holder);
      p.holder = holder;
      const isGround = entry.kind === 'ground';
      root.traverse((o) => {
        if (!o.isMesh) return;
        o.castShadow = !lite && !isGround && entry.kind !== 'town' && entry.kind !== 'church';
        o.receiveShadow = !lite;
      });
    }
    scene.updateMatrixWorld(true);
    const elsewhere = all.filter((e) => !entries.includes(e));
    const liteOf = (e) => !lite && !!stream(e);
    market.propCount += await placeProps(placed.map((p) => ({ ...p, nodes: scanNodes(p.root) })), { lite, liteOf, manager, warn, elsewhere, bindings: market.bindings });
    market.instrumentCount += await placeInstruments(placed, scanNodes, { lite, liteOf, manager, warn });
    scene.updateMatrixWorld(true);
    return placed;
  }

  /** Read the node conventions of newly placed entries into the market's registry. */
  function integrate(placed) {
    const spots = [], bulbs = [], snow = [];
    for (const p of placed) {
      let nodes = scanNodes(p.root);
      if (p.entry.place && p.source !== 'standin' && addStandinGoods({ id: p.entry.place, nodes, root: p.root, holder: p.holder, entry: p.entry }, { lite, warn: (m) => console.info('[market]', m) })) {
        p.root.updateMatrixWorld(true);
        nodes = scanNodes(p.root);
      }
      p.nodes = nodes;
      bulbs.push(...lightBulbs(nodes, { lite }));
      snow.push(...nodes.snow);
      // BUILD.md: at most 2 light_ markers per section stall and 1 per deco stall, props included. The stall's
      // own markers come first; any over the cap (a prop set's lamp, say) is reported and left to its glowing bulb.
      const cap = LIGHT_CAP[p.entry.kind];
      const own = nodes.lights.filter((o) => !isInProp(o, p.root)), fromProps = nodes.lights.filter((o) => isInProp(o, p.root));
      const lightList = cap ? [...own, ...fromProps].slice(0, cap) : nodes.lights;
      for (const o of nodes.lights) if (!lightList.includes(o)) market.contract.push({ id: p.entry.id, light: o.name, problem: `more than ${cap} light_ markers in a ${p.entry.kind} stall (BUILD.md); ${o.name} is not lit.` });
      lightList.forEach((obj) => spots.push({ obj, kind: p.entry.kind, id: p.entry.id }));
      const rides = nodes.rots.length || nodes.gondolas.length || nodes.horses.length ? makeRides(nodes) : null;
      if (rides) market.rides.push(rides);
      if (p.root.userData.animations?.length) {
        const mixer = new THREE.AnimationMixer(p.root);
        p.root.userData.animations.forEach((clip) => mixer.clipAction(clip).play());
        market.mixers.push(mixer);
      }
      if (p.entry.place) {
        const box = new THREE.Box3().setFromObject(p.holder);
        const size = box.getSize(new THREE.Vector3());
        const center = new THREE.Vector3(p.holder.position.x, THREE.MathUtils.clamp(size.y * 0.45, 1.6, 9), p.holder.position.z);
        const place = { id: p.entry.place, entry: p.entry, holder: p.holder, root: p.root, nodes, rides, center, ry: p.holder.rotation.y, source: p.source, radius: Math.max(size.x, size.z) / 2 };
        // streaming: opened lite on the full market, the full model is grafted on at its stop (engine/stream.js);
        // its goods are merged after that
        place.streamed = p.streamed;
        place.record = p;
        // the goods (the bookshop's spines, the mugs, glasses, bottles, sausages and rolls): one merged mesh per
        // set and look instead of one draw each; an item leaves it while it moves or its look changes
        if (!place.streamed) mergeGoods(place);
        market.places[p.entry.place] = place;
        market.hotRoots.push(p.holder);
      }
      if (p.entry.kind === 'deco') {
        // deco stalls open no panel, but a click flies to their close-up and their goods can be looked at
        market.decoRoots.push(p.holder);
        market.decos[p.entry.id] = { id: p.entry.id, entry: p.entry, holder: p.holder, root: p.root, nodes, ry: p.holder.rotation.y, center: p.holder.position.clone().setY(1.6) };
      }
      market.placed.push(p);
      market.report.push({ id: p.entry.id, place: p.entry.place || null, kind: p.entry.kind, source: p.source, file: p.file, deferred: later.includes(p.entry) || undefined });
    }
    // bulb materials are shared per source material
    const fresh = [...new Set(bulbs)].filter((m) => !market.bulbMaterials.includes(m));
    market.bulbMaterials.push(...fresh);
    market.snow.push(...snow);
    market.lightSpots.push(...spots);
    return { placed, spots, snow, bulbs: fresh };
  }

  function mergeGoods(place) {
    const merge = mergeActMeshes(place.root, ITEM_RE);
    if (merge) { place.merge = merge; market.merges[place.id] = { books: merge.count, meshes: merge.groups.length }; }
  }
  /** After a streamed place got its full model: merge its goods as at load. */
  market.mergeGoods = mergeGoods;

  integrate(await load(now, onProgress));

  let pending = null;
  /** Load what `defer` held back. Resolves to { placed, spots, snow, bulbs } for the new entries. */
  market.loadDeferred = () => {
    pending ||= later.length ? load(later).then(integrate) : Promise.resolve({ placed: [], spots: [], snow: [], bulbs: [] });
    return pending;
  };
  /** Resolves once a place exists (a deferred ride may still be on its way). */
  market.whenPlace = async (id) => {
    if (market.places[id]) return market.places[id];
    if (later.some((e) => e.place === id)) await market.loadDeferred();
    return market.places[id] || null;
  };
  return market;
}

const _v = new THREE.Vector3();
/** Where the camera goes for a place: its cam_view/cam_target, or a view worked out from its position. */
// Per-place camera nudges on top of the architect's cam_view: `dolly` keeps that fraction of the distance to
// cam_target. The Bücherstand is about its books, so its view comes in closer to the shelves.
// the Bücherstand with its six category sections (round 3): pull back a little from the carpenter's cam_view so the side racks
// stand clear of the panel (was 0.8 for the small round-1 stall)
// the Bierstand (round 4): back a little so the tap tower to the right of the vendor clears the panel too
export const VIEW_NUDGE = { books: { dolly: 1.12 }, bier: { dolly: 1.2 } };

export function viewFor(place) {
  const n = place.nodes;
  if (n.camView) {
    const pos = n.camView.getWorldPosition(new THREE.Vector3());
    const target = n.camTarget ? n.camTarget.getWorldPosition(new THREE.Vector3()) : place.center.clone();
    const nudge = VIEW_NUDGE[place.id];
    if (nudge?.dolly) pos.lerpVectors(target, pos, nudge.dolly);
    return { pos, target };
  }
  const c = place.center.clone();
  const fwd = new THREE.Vector3(Math.sin(place.ry), 0, Math.cos(place.ry));
  if (place.id === 'ferris') return { pos: c.clone().add(fwd.multiplyScalar(26)).add(_v.set(8, -3, 0)), target: c };
  if (place.id === 'carousel') return { pos: c.clone().add(_v.set(-8, 2.5, 11)), target: c };
  if (place.id === 'band') return { pos: c.clone().add(_v.set(0, 1.4, 11.5)), target: c.clone().add(_v.set(0, -0.3, 0)) };
  return { pos: c.clone().add(fwd.multiplyScalar(6.5)).add(_v.set(0, 1.2, 0)), target: c.clone().add(_v.set(0, 0.1, 0)) };
}
