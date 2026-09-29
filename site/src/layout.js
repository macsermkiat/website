// Reads site/src/layout.json (owned by the architect) and turns it into a list of placements.
// Anything the file leaves out, or the whole file when it is missing, comes from the BUILD.md layout.
import inventory from 'virtual:market-inventory';
import { PLACE_ORDER, SECTION_STALLS, placeFor, fileTokens } from './places.js';

// Vite resolves this at build time; an empty object when layout.json does not exist yet.
const layoutFiles = import.meta.glob('./layout.json', { eager: true, import: 'default' });
const RAW = layoutFiles['./layout.json'] ?? null;

export const HOME = { position: [3, 9, 33], target: [0, 2.2, -3] };

/** The BUILD.md starting layout. `keys` are words used to find a model file for the entry. */
export const FALLBACK_LAYOUT = [
  { id: 'square', kind: 'ground', label: 'Market square', position: [0, 0, 0], rotation: 0, keys: ['square', 'ground', 'platz', 'marktplatz'] },
  { id: 'town', kind: 'town', label: 'Town', position: [0, 0, 0], rotation: 0, keys: ['town', 'townring', 'town-ring', 'houses'] },
  { id: 'church', kind: 'church', label: 'Church', position: [8, 0, -56], rotation: -0.1, keys: ['church', 'kirche'] },
  { id: 'gluehwein', kind: 'section', place: 'glueh', label: 'Glühwein', position: [-7.4, 0, -1.4], rotation: 0.42, keys: ['gluehwein', 'glueh', 'glühwein'] },
  { id: 'bratwurst', kind: 'section', place: 'wurst', label: 'Bratwurst', position: [-12.8, 0, 2.6], rotation: 0.8, keys: ['bratwurst', 'wurst'] },
  { id: 'bierstand', kind: 'section', place: 'bier', label: 'Bier vom Fass', position: [7.4, 0, -1.4], rotation: -0.42, keys: ['bierstand', 'bier', 'beer'] },
  { id: 'buecherstand', kind: 'section', place: 'books', label: 'Bücher', position: [12.8, 0, 2.6], rotation: -0.8, keys: ['buecherstand', 'buecher', 'bücherstand', 'books', 'bookshop'] },
  { id: 'bandstand', kind: 'landmark', place: 'band', label: 'Bandstand', position: [0, 0, -5], rotation: 0, keys: ['bandstand', 'band'] },
  { id: 'riesenrad', kind: 'landmark', place: 'ferris', label: 'Riesenrad', position: [-22, 0, -17], rotation: 0.65, keys: ['riesenrad', 'ferris', 'ferriswheel'] },
  { id: 'karussell', kind: 'landmark', place: 'carousel', label: 'Karussell', position: [19, 0, -12], rotation: 0, keys: ['karussell', 'carousel'] },
  { id: 'tree', kind: 'tree', label: 'Christmas tree', position: [6.5, 0, -15], rotation: 0, keys: ['tree', 'christmastree', 'christbaum', 'weihnachtsbaum'] },
  { id: 'lebkuchen', kind: 'deco', label: 'Lebkuchen', position: [-21, 0, -3], rotation: Math.PI / 2, keys: ['lebkuchen'] },
  { id: 'mandeln', kind: 'deco', label: 'Gebrannte Mandeln', position: [-21, 0, 3.5], rotation: Math.PI / 2, keys: ['mandeln', 'gebrannte-mandeln', 'almonds'] },
  { id: 'kerzen', kind: 'deco', label: 'Kerzen', position: [-21, 0, 10], rotation: Math.PI / 2, keys: ['kerzen', 'candles'] },
  { id: 'holzspielzeug', kind: 'deco', label: 'Holzspielzeug', position: [21, 0, -3], rotation: -Math.PI / 2, keys: ['holzspielzeug', 'spielzeug', 'toys'] },
  { id: 'christbaumschmuck', kind: 'deco', label: 'Christbaumschmuck', position: [21, 0, 3.5], rotation: -Math.PI / 2, keys: ['christbaumschmuck', 'schmuck', 'ornaments'] },
  { id: 'kaese', kind: 'deco', label: 'Käse', position: [21, 0, 10], rotation: -Math.PI / 2, keys: ['kaese', 'käse', 'cheese'] },
  { id: 'crepes', kind: 'deco', label: 'Crêpes', position: [-9.5, 0, -21], rotation: 0, keys: ['crepes', 'crêpes'] },
  { id: 'maroni', kind: 'deco', label: 'Heiße Maroni', position: [-3.5, 0, -21.5], rotation: 0, keys: ['maroni', 'heisse-maroni', 'chestnuts'] },
  { id: 'kartoffelpuffer', kind: 'deco', label: 'Kartoffelpuffer', position: [14, 0, -21], rotation: 0, keys: ['kartoffelpuffer', 'puffer'] },
  { id: 'strings', kind: 'strings', label: 'String lights', position: [0, 0, 0], rotation: 0, keys: ['strings', 'string-lights', 'stringlights', 'lamps', 'poles'] },
];

const MODEL_FILES = (inventory.models || []).filter((f) => /\.(glb|gltf)$/i.test(f));
const IGNORE_TOKENS = ['prop', 'props', 'person', 'people', 'crowd', 'vendor'];

/** Find a model in site/public/models by name words. Returns the full (non-lite) relative path or null. */
export function findModelByKeys(keys) {
  const want = keys.map((k) => k.toLowerCase().normalize('NFC').replace(/[\s_.]+/g, '-'));
  const full = MODEL_FILES.filter((f) => !/\.lite\.glb$/i.test(f) && !f.split('/').some((p) => IGNORE_TOKENS.includes(p.toLowerCase())));
  // exact base name first, then a matching word in the name
  for (const k of want) {
    const hit = full.find((f) => fileTokens(f).join('-') === k);
    if (hit) return hit;
  }
  for (const k of want) {
    const hit = full.find((f) => {
      const t = fileTokens(f);
      return !t.some((x) => IGNORE_TOKENS.includes(x)) && (t.includes(k) || t.join('-').endsWith('-' + k) || t.join('-').startsWith(k + '-'));
    });
    if (hit) return hit;
  }
  return null;
}

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
  for (const k of ['model', 'glb', 'file', 'src', 'url', 'asset', 'path', 'mesh']) {
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
    const place = placeFor(placeWord) || placeFor(id) || (model ? placeFor(fileTokens(model).join('-')) : null);
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

  for (const e of entries) {
    const bare = String(e.id).toLowerCase().replace(/^(deco|stall|place)[-_]/, '');
    const fb = FALLBACK_LAYOUT.find((f) => (e.place && f.place === e.place) || f.id === e.id || f.id === bare || (e.goods && f.id === String(e.goods).toLowerCase()) || f.keys.includes(bare));
    if (e.model && !modelExists(e.model)) {
      const byName = findModelByKeys([fileTokens(e.model).join('-')]);
      notes.push(`${e.id}: ${e.model} not found${byName ? `, using ${byName}` : ', using a stand-in'}.`);
      e.model = byName;
    }
    if (!e.model) e.model = findModelByKeys([...(e.keys || []), e.id, ...(e.goods ? [`deco-${e.goods}`, e.goods] : []), ...(fb?.keys || []).flatMap((k) => (e.kind === 'deco' ? [`deco-${k}`, k] : [k]))]);
    if (e.lite && !modelExists(e.lite)) e.lite = null;
    if (!e.lite) e.lite = liteVariant(e.model);
    if (!e.label && fb) e.label = fb.label;
    if (e.place && !SECTION_STALLS.includes(e.place) && e.kind === 'section') e.kind = 'landmark';
    if (!e.place && (e.kind === 'section' || e.kind === 'landmark')) e.kind = 'deco';
  }
  // interactive places first so they load first
  const rank = (e) => (e.place ? PLACE_ORDER.indexOf(e.place) : e.kind === 'ground' ? -1 : 50);
  entries.sort((a, b) => rank(a) - rank(b));
  return { entries, home: readHome(RAW), notes, fromFile: !!RAW };
}
