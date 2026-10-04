// Reads site/src/layout.json (owned by the architect) and turns it into a list of placements.
// Anything the file leaves out, or the whole file when it is missing, comes from the BUILD.md layout.
import inventory from 'virtual:market-inventory';
import { PLACE_ORDER, SECTION_STALLS, placeFor } from './places.js';

// Vite resolves this at build time; an empty object when layout.json does not exist yet.
const layoutFiles = import.meta.glob('./layout.json', { eager: true, import: 'default' });
// ?layout=builtin ignores layout.json (to test the BUILD.md fallback without deleting the file)
const builtinLayout = (() => { try { return new URLSearchParams(globalThis.location?.search || '').get('layout') === 'builtin'; } catch { return false; } })();
const RAW = builtinLayout ? null : layoutFiles['./layout.json'] ?? null;

export const HOME = { position: [3, 9, 33], target: [0, 2.2, -3] };

/**
 * The BUILD.md starting layout, used when layout.json is missing. `asset` is the exact file each role ships
 * (the names layout.json uses); nothing is guessed from file names.
 */
export const FALLBACK_LAYOUT = [
  { id: 'square', kind: 'ground', label: 'Market square', position: [0, 0, 0], rotation: 0, asset: 'square.glb' },
  { id: 'town', kind: 'town', label: 'Town', position: [0, 0, 0], rotation: 0, asset: 'town.glb' },
  { id: 'church', kind: 'church', label: 'Church', position: [8, 0, -56], rotation: -0.1, asset: null },
  { id: 'gluehwein', kind: 'section', place: 'glueh', label: 'Glühwein', position: [-7.4, 0, -1.4], rotation: 0.42, asset: 'stall_gluehwein.glb' },
  { id: 'bratwurst', kind: 'section', place: 'wurst', label: 'Bratwurst', position: [-12.8, 0, 2.6], rotation: 0.8, asset: 'stall_bratwurst.glb' },
  { id: 'bierstand', kind: 'section', place: 'bier', label: 'Bier vom Fass', position: [7.4, 0, -1.4], rotation: -0.42, asset: 'stall_bier.glb' },
  { id: 'buecherstand', kind: 'section', place: 'books', label: 'Bücher', position: [12.8, 0, 2.6], rotation: -0.8, asset: 'stall_buecher.glb' },
  { id: 'bandstand', kind: 'landmark', place: 'band', label: 'Bandstand', position: [0, 0, -5], rotation: 0, asset: 'bandstand.glb' },
  { id: 'riesenrad', kind: 'landmark', place: 'ferris', label: 'Riesenrad', position: [-22, 0, -17], rotation: 0.65, asset: 'ferris.glb' },
  { id: 'karussell', kind: 'landmark', place: 'carousel', label: 'Karussell', position: [19, 0, -12], rotation: 0, asset: 'carousel.glb' },
  { id: 'tree', kind: 'tree', label: 'Christmas tree', position: [6.5, 0, -15], rotation: 0, asset: 'tree.glb' },
  { id: 'deco-lebkuchen', kind: 'deco', label: 'Lebkuchen', position: [-21, 0, -3], rotation: Math.PI / 2, asset: 'deco_lebkuchen.glb' },
  { id: 'deco-mandeln', kind: 'deco', label: 'Gebrannte Mandeln', position: [-21, 0, 3.5], rotation: Math.PI / 2, asset: 'deco_mandeln.glb' },
  { id: 'deco-kerzen', kind: 'deco', label: 'Kerzen', position: [-21, 0, 10], rotation: Math.PI / 2, asset: 'deco_kerzen.glb' },
  { id: 'deco-spielzeug', kind: 'deco', label: 'Holzspielzeug', position: [21, 0, -3], rotation: -Math.PI / 2, asset: 'deco_spielzeug.glb' },
  { id: 'deco-schmuck', kind: 'deco', label: 'Christbaumschmuck', position: [21, 0, 3.5], rotation: -Math.PI / 2, asset: 'deco_schmuck.glb' },
  { id: 'deco-kaese', kind: 'deco', label: 'Käse', position: [21, 0, 10], rotation: -Math.PI / 2, asset: 'deco_kaese.glb' },
  { id: 'deco-crepes', kind: 'deco', label: 'Crêpes', position: [-9.5, 0, -21], rotation: 0, asset: 'deco_crepes.glb' },
  { id: 'deco-maroni', kind: 'deco', label: 'Heiße Maroni', position: [-3.5, 0, -21.5], rotation: 0, asset: 'deco_maroni.glb' },
  { id: 'deco-kartoffelpuffer', kind: 'deco', label: 'Kartoffelpuffer', position: [14, 0, -21], rotation: 0, asset: 'deco_puffer.glb' },
  { id: 'strings', kind: 'strings', label: 'String lights', position: [0, 0, 0], rotation: 0, asset: null },
];

// ?missing=all or ?missing=stall_bier,ferris pretends those models were never shipped (to test the stand-ins)
const MISSING = (() => {
  try { return (new URLSearchParams(globalThis.location?.search || '').get('missing') || '').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean); } catch { return []; }
})();
const isMissing = (f) => MISSING.includes('all') || MISSING.some((m) => f.toLowerCase().replace(/(\.lite)?\.(glb|gltf)$/, '') === m.replace(/(\.lite)?\.(glb|gltf)$/, ''));
const MODEL_FILES = (inventory.models || []).filter((f) => /\.(glb|gltf)$/i.test(f) && !isMissing(f));
export function modelExists(rel) {
  return !!rel && MODEL_FILES.includes(rel);
}

/** "x.glb" -> "x.lite.glb" when that file exists. */
export function liteVariant(rel) {
  if (!rel) return null;
  const lite = rel.replace(/\.(glb|gltf)$/i, '.lite.$1');
  return MODEL_FILES.includes(lite) ? lite : null;
}

// ---------- tolerant reading of layout.json ----------

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : typeof v === 'string' && v.trim() !== '' && Number.isFinite(+v) ? +v : null);

export function readVec(o) {
  for (const k of ['position', 'pos', 'at', 'xz', 'location', 'translation', 'p']) {
    const v = o[k];
    if (Array.isArray(v) && (v.length === 2 || v.length === 3) && v.every((x) => num(x) !== null)) {
      return v.length === 2 ? [+v[0], 0, +v[1]] : [+v[0], +v[1], +v[2]];
    }
    if (v && typeof v === 'object' && num(v.x) !== null && num(v.z) !== null) return [+v.x, num(v.y) ?? 0, +v.z];
  }
  if (num(o.x) !== null && num(o.z) !== null) return [+o.x, num(o.y) ?? 0, +o.z];
  return null;
}

export function readRot(o) {
  const unitsDeg = /deg/i.test(String(o.units || o.rotationUnits || ''));
  for (const k of ['rotation', 'rot', 'ry', 'rotY', 'rotationY', 'yaw', 'heading', 'angle']) {
    let v = o[k];
    if (Array.isArray(v) && v.length === 3) v = v[1];
    if (v && typeof v === 'object' && num(v.y) !== null) v = v.y;
    const n = num(v);
    if (n !== null) return unitsDeg || /deg/i.test(k) || Math.abs(n) > Math.PI * 2 + 0.01 ? (n * Math.PI) / 180 : n;
  }
  for (const k of ['rotationDeg', 'rotDeg', 'yawDeg', 'degrees']) {
    const n = num(o[k]);
    if (n !== null) return (n * Math.PI) / 180;
  }
  return 0;
}

function readModel(o) {
  for (const k of ['asset', 'model', 'glb', 'file', 'src', 'url', 'path', 'mesh']) {
    const v = o[k];
    if (typeof v === 'string' && /\.(glb|gltf)$/i.test(v)) return v;
    if (v && typeof v === 'object' && typeof (v.full || v.desktop || v.src) === 'string') return v.full || v.desktop || v.src;
  }
  return null;
}

function readLite(o) {
  for (const k of ['lite', 'liteModel', 'lite_model', 'modelLite']) if (typeof o[k] === 'string') return o[k];
  const m = o.model;
  if (m && typeof m === 'object' && typeof m.lite === 'string') return m.lite;
  return null;
}

function relModel(url) {
  if (!url) return null;
  return url.replace(/^(\.\/|\/)+/, '').replace(/^(site\/)?(public\/)?/, '').replace(/^models\//, '');
}

const KIND_WORDS = [
  ['deco', /deco/i],
  ['strings', /string|lamp|pole/i],
  ['tree', /tree|baum/i],
  ['church', /church|kirche/i],
  ['ground', /ground|square|platz|floor/i],
  ['town', /town|houses|buildings|ring$/i],
  ['landmark', /landmark|ride/i],
  ['section', /section|stall/i],
];

const KINDS = ['section', 'landmark', 'deco', 'tree', 'ground', 'town', 'church', 'strings'];
function inferKind(entry, parentKey) {
  const k = String(entry.kind || entry.type || entry.category || entry.role || '').toLowerCase();
  const probe = (s) => KIND_WORDS.find(([, re]) => re.test(s))?.[0];
  if (entry.place) return ['glueh', 'bier', 'wurst', 'books'].includes(entry.place) ? 'section' : 'landmark';
  if (KINDS.includes(k)) return k;
  // "scenery" and other broad kinds: tell square, town and tree apart by id and file name
  return probe(entry.id || '') || probe(entry.model || '') || probe(k) || probe(parentKey || '') || 'other';
}

function collectEntries(node, parentKey, out, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 6) return;
  if (Array.isArray(node)) {
    node.forEach((n, i) => collectEntries(n, parentKey, out, depth + 1));
    return;
  }
  const pos = readVec(node);
  if (pos) {
    const model = readModel(node);
    const id = String(node.id ?? node.name ?? node.key ?? node.slug ?? parentKey ?? `item${out.length}`);
    const placeWord = node.place ?? node.section ?? node.opens ?? node.link ?? node.panel ?? null;
    const place = placeFor(placeWord) || placeFor(id);
    const e = {
      id,
      label: node.label || node.title || node.sign || node.name || id,
      place,
      model: relModel(model),
      lite: relModel(readLite(node)),
      position: pos,
      rotation: readRot(node),
      scale: num(node.scale) ?? 1,
      goods: typeof node.goods === 'string' ? node.goods : null,
      raw: node,
    };
    e.kind = inferKind({ ...node, id, model: model || '', place }, parentKey);
    out.push(e);
    return; // children of a placed item are its own business
  }
  for (const [k, v] of Object.entries(node)) {
    if (['home', 'camera', 'homeCamera', 'home_camera'].includes(k)) continue;
    collectEntries(v, k, out, depth + 1);
  }
}

function readHome(raw) {
  const h = raw && (raw.home || raw.camera?.home || raw.homeCamera || raw.home_camera || raw.camera);
  if (!h) return HOME;
  const p = Array.isArray(h.position) ? h.position : Array.isArray(h.pos) ? h.pos : null;
  const t = Array.isArray(h.target) ? h.target : Array.isArray(h.lookAt) ? h.lookAt : Array.isArray(h.look_at) ? h.look_at : null;
  const fov = Number(h.fov);
  if (!(p && t && p.length === 3 && t.length === 3)) return HOME;
  return { position: p.map(Number), target: t.map(Number), ...(fov > 10 && fov < 100 ? { fov } : {}) };
}

/**
 * The market's placements. Each entry has a model path (relative to public/models) when the file exists,
 * or `model: null`, in which case the engine builds a labelled stand-in.
 */
export function resolveLayout() {
  const notes = [];
  let entries = [];
  if (RAW) {
    collectEntries(RAW, null, entries);
    if (!entries.length) notes.push('layout.json has no placements the engine can read; using the BUILD.md layout.');
    else notes.push(`layout.json: ${entries.length} placements.`);
  } else notes.push('layout.json is missing; using the BUILD.md layout.');

  if (entries.length) {
    // Keep every interactive place and the ground even when the file leaves them out.
    const have = new Set(entries.map((e) => e.place).filter(Boolean));
    for (const f of FALLBACK_LAYOUT) {
      if (f.place && !have.has(f.place)) {
        entries.push({ ...f });
        notes.push(`layout.json has no ${f.place}; using BUILD.md position.`);
      }
    }
    if (!entries.some((e) => e.kind === 'ground')) entries.push({ ...FALLBACK_LAYOUT[0] });
  } else {
    entries = FALLBACK_LAYOUT.map((f) => ({ ...f }));
  }

  // Exact bindings: each entry's asset is the file the owning role named (layout.json `asset`, or the BUILD.md
  // layout's own names). The lite market takes `<name>.lite.glb` (the contract), or the entry's `lite` field.
  // Nothing is guessed from file names: a binding to a file that is not there is reported, and that place
  // gets a labelled stand-in.
  const bindings = [];
  const bad = (e, problem) => { bindings.push({ id: e.id, asset: e.model || null, problem, simulated: MISSING.length > 0 || undefined }); notes.push(`${e.id}: ${problem}`); };
  for (const e of entries) {
    if (e.asset !== undefined && e.model === undefined) e.model = e.asset; // a BUILD.md fallback entry
    const fb = FALLBACK_LAYOUT.find((f) => (e.place && f.place === e.place) || f.id === e.id);
    if (e.model && !modelExists(e.model)) {
      bad(e, `${e.model} is not in site/public/models; using a stand-in.`);
      e.model = null;
    } else if (!e.model && e.kind !== 'strings' && e.kind !== 'church') {
      bad(e, 'no asset named; using a stand-in.');
    }
    if (e.lite && !modelExists(e.lite)) { if (e.model) bad(e, `lite asset ${e.lite} is not in site/public/models; the lite market loads ${e.model}.`); e.lite = null; }
    if (!e.lite) e.lite = liteVariant(e.model);
    if (!e.label && fb) e.label = fb.label;
    if (e.place && !SECTION_STALLS.includes(e.place) && e.kind === 'section') e.kind = 'landmark';
    if (!e.place && (e.kind === 'section' || e.kind === 'landmark')) e.kind = 'deco';
  }
  // interactive places first so they load first
  const rank = (e) => (e.place ? PLACE_ORDER.indexOf(e.place) : e.kind === 'ground' ? -1 : 50);
  entries.sort((a, b) => rank(a) - rank(b));
  return { entries, home: readHome(RAW), notes, bindings, fromFile: !!RAW, raw: RAW };
}
