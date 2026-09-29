// The crowd: people standing in groups and walking the lanes, with speech bubbles.
// Reads site/src/crowd.json (owned by the organizer) when it exists; otherwise uses the prototype's groups.
// Person models come from crowd.json "variants" (glbs in public/models); stand-in figures otherwise.
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { buildPerson } from './standins/people.js';
import { rng } from './standins/kit.js';
import { readVec, readRot, modelExists, liteVariant } from './layout.js';
import { loadGlb } from './engine/loader.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const crowdFiles = import.meta.glob('./crowd.json', { eager: true, import: 'default' });
const RAW = crowdFiles['./crowd.json'] ?? null;

const GROUPS = [[-3.5, 5], [4, 4.2], [-9.5, 8], [9.5, 8.5], [0, 10], [-15, 9], [15, 10], [-5.5, 1.5], [6, 1.8], [-1.5, 14], [11, 13], [-17, 0], [17, 7], [-16.5, -6], [-7, -14], [1, -15.5], [11, -16], [-11, 15], [5, 17], [-4, -10.5], [13, -4.5]];

// The lite market draws its 40 people from a smaller set of figures (recoloured, so the crowd still varies):
// three fewer downloads, about 300 KB.
const LITE_ALIAS = {
  'people_man_parka.glb': 'people_man_coat.glb',
  'people_woman_young.glb': 'people_woman_coat.glb',
  'people_child_girl.glb': 'people_child_boy.glb',
};
// Full market: people farther than lod.far metres from the camera switch to their .lite.glb figure
// (about 1.5k triangles and one draw call instead of 4.6k and four), and back nearer than lod.near.
// The defaults depend on the GPU class (quality.js), ?lod=far overrides them, and the frame-time governor in
// main.js pulls them in on a machine that cannot keep up.
export const LOD_FAR = 18, LOD_NEAR = 16;

// ---------- one draw call per figure ----------
// The organizer's figures have four body parts (coat, body, hat, scarf), each its own material, so four draw
// calls (and four more in the moon's shadow pass) per person. The lite figures carry no textures besides one
// shared occlusion map, so their parts can be one mesh: each part's colour goes into the vertex colours
// (times the figure's own COLOR_0), and one material draws the whole crowd. Recolouring a person rewrites the
// colour attribute of their own copy of the geometry; everything else is shared.
const PARTS = new Set(['coat', 'body', 'hat', 'scarf']);
const compacted = new WeakMap();
let sharedFigureMat = null;

/**
 * A lift for the crowd: a little light proportional to each figure's own colour, so the dark coats read as
 * cloth at night (a figure between the stalls catches their glow) instead of black cut-outs. The lighting
 * module's moon rim does the edges; this does the faces of the cloth. `crowdLift.value` is shared.
 */
export const crowdLift = { value: 0.4 };
function liftMaterial(m) {
  if (!m || m.userData.crowdLift) return m;
  m.userData.crowdLift = true;
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (shader, r) => {
    prev?.call(m, shader, r);
    shader.uniforms.crowdLift = crowdLift;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float crowdLift;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n  totalEmissiveRadiance += ( diffuseColor.rgb * 0.8 + vec3( 0.006, 0.0065, 0.009 ) ) * crowdLift * vec3( 0.55, 0.5, 0.62 );');
  };
  const key = m.customProgramCacheKey?.bind(m);
  m.customProgramCacheKey = () => `${key ? key() : ''}|crowdLift`;
  m.needsUpdate = true;
  return m;
}

function figureMaterial(ao) {
  if (sharedFigureMat) return sharedFigureMat;
  sharedFigureMat = liftMaterial(new THREE.MeshStandardMaterial({ name: 'crowd_figure', vertexColors: true, roughness: 0.86, metalness: 0, side: THREE.DoubleSide, aoMap: ao || null }));
  return sharedFigureMat;
}

/** Merge a figure's part meshes into one skinned mesh, once per loaded figure. Returns the figure. */
function compactFigure(src) {
  if (compacted.has(src)) return src;
  compacted.set(src, true);
  const byParent = new Map();
  src.traverse((o) => {
    if (!o.isSkinnedMesh || Array.isArray(o.material)) return;
    const m = o.material;
    if (!PARTS.has(m.name) || m.map || m.normalMap) return; // full figures keep their cloth normal maps
    if (!byParent.has(o.parent)) byParent.set(o.parent, []);
    byParent.get(o.parent).push(o);
  });
  for (const [parent, list] of byParent) {
    if (list.length < 2 || list.some((o) => o.skeleton !== list[0].skeleton)) continue;
    const names = ['position', 'normal', 'uv', 'skinIndex', 'skinWeight'];
    if (!list.every((o) => names.every((n) => o.geometry.getAttribute(n)))) continue;
    const parts = [];
    let start = 0;
    const geos = list.map((o) => {
      const g = floatCopy(o.geometry, names);
      const n = g.getAttribute('position').count;
      const own = o.geometry.getAttribute('color');
      const base = new Float32Array(n * 3).fill(1);
      if (own) for (let i = 0; i < n; i++) { base[i * 3] = own.getX(i); base[i * 3 + 1] = own.getY(i); base[i * 3 + 2] = own.getZ(i); }
      parts.push({ name: o.material.name, start, count: n, base, color: o.material.color.clone() });
      start += n;
      g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      return g;
    });
    const merged = mergeGeometries(geos, false);
    if (!merged) continue;
    merged.userData.parts = parts;
    paint(merged.getAttribute('color'), parts, null);
    const first = list[0];
    const ao = list.map((o) => o.material.aoMap).find(Boolean);
    const mesh = new THREE.SkinnedMesh(merged, figureMaterial(ao));
    mesh.name = 'figure';
    mesh.position.copy(first.position); mesh.quaternion.copy(first.quaternion); mesh.scale.copy(first.scale);
    mesh.bind(first.skeleton, first.bindMatrix);
    mesh.bindMode = first.bindMode;
    mesh.frustumCulled = first.frustumCulled;
    parent.add(mesh);
    list.forEach((o) => o.removeFromParent());
  }
  return src;
}

function floatCopy(src, names) {
  const g = new THREE.BufferGeometry();
  for (const name of names) {
    const a = src.getAttribute(name);
    const Arr = name === 'skinIndex' ? Uint16Array : Float32Array;
    const out = new Arr(a.count * a.itemSize);
    const get = [(i) => a.getX(i), (i) => a.getY(i), (i) => a.getZ(i), (i) => a.getW(i)];
    for (let i = 0; i < a.count; i++) for (let k = 0; k < a.itemSize; k++) out[i * a.itemSize + k] = get[k](i);
    g.setAttribute(name, new THREE.BufferAttribute(out, a.itemSize));
  }
  g.setIndex(src.index ? Array.from(src.index.array) : [...Array(src.getAttribute('position').count).keys()]);
  return g;
}

/** Fill a merged figure's colour attribute: each part's COLOR_0 times its colour (or the person's own). */
function paint(attr, parts, colors) {
  const c = new THREE.Color();
  for (const p of parts) {
    const want = colors?.[p.name];
    if (want) c.set(want); else c.copy(p.color);
    for (let i = 0; i < p.count; i++) {
      const j = (p.start + i) * 3;
      attr.array[j] = p.base[i * 3] * c.r; attr.array[j + 1] = p.base[i * 3 + 1] * c.g; attr.array[j + 2] = p.base[i * 3 + 2] * c.b;
    }
  }
  attr.needsUpdate = true;
}

/** Per person: the merged figure's geometry with their own colours (shared by people dressed alike). */
const painted = new Map();
function paintFigure(fig, colors) {
  fig.traverse((o) => {
    const parts = o.isSkinnedMesh && o.geometry.userData.parts;
    if (!parts || !colors) return;
    const key = `${o.geometry.uuid}|${JSON.stringify(colors)}`;
    if (!painted.has(key)) {
      const g = new THREE.BufferGeometry();
      for (const [n, a] of Object.entries(o.geometry.attributes)) if (n !== 'color') g.setAttribute(n, a);
      g.setIndex(o.geometry.index);
      g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(o.geometry.getAttribute('color').array.length), 3));
      g.boundingSphere = o.geometry.boundingSphere;
      g.boundingBox = o.geometry.boundingBox;
      g.userData.parts = parts;
      paint(g.getAttribute('color'), parts, colors);
      painted.set(key, g);
    }
    o.geometry = painted.get(key);
  });
}

function rel(url) {
  return String(url).replace(/^(\.\/|\/)+/, '').replace(/^(site\/)?(public\/)?/, '').replace(/^models\//, '');
}

/** Tolerant reading of crowd.json into { variants, people: [{pos, ry, walk?, path?, mug, variant}] }. */
function parseCrowd(json) {
  const variants = [];
  const people = [];
  const vlist = json.variants || json.models || json.people_models || json.meshes;
  if (Array.isArray(vlist)) for (const v of vlist) { const f = typeof v === 'string' ? v : v?.model || v?.glb || v?.file; if (f) variants.push(rel(f)); }
  const visit = (node, depth = 0) => {
    if (!node || typeof node !== 'object' || depth > 5) return;
    if (Array.isArray(node)) return node.forEach((n) => visit(n, depth + 1));
    const path = node.path || node.waypoints || node.route;
    if (Array.isArray(path) && path.length >= 2) {
      const pts = path.map((p) => (Array.isArray(p) ? new THREE.Vector3(p[0], 0, p[p.length === 3 ? 2 : 1]) : new THREE.Vector3(p.x, 0, p.z)));
      people.push({ pos: pts[0].clone(), ry: 0, path: pts, speed: Number(node.speed) || 0.9, mug: !!node.mug, variant: node.variant });
      return;
    }
    const pos = readVec(node);
    if (pos) {
      const count = Number(node.count ?? node.size ?? node.n) || 0;
      const members = node.members || node.people;
      if (Array.isArray(members)) {
        members.forEach((m) => {
          const p = readVec(m);
          people.push({ pos: new THREE.Vector3(...(p ? [pos[0] + p[0], 0, pos[2] + p[2]] : pos)), ry: readRot(m), mug: !!m.mug, variant: m.variant, facing: new THREE.Vector3(pos[0], 0, pos[2]) });
        });
      } else if (count > 1) {
        for (let i = 0; i < count; i++) {
          const a = (i / count) * Math.PI * 2, r = Number(node.radius) || 0.65;
          const p = new THREE.Vector3(pos[0] + Math.cos(a) * r, 0, pos[2] + Math.sin(a) * r);
          people.push({ pos: p, ry: Math.atan2(pos[0] - p.x, pos[2] - p.z), mug: node.mug ?? i % 3 !== 2, variant: node.variant });
        }
      } else {
        people.push({ pos: new THREE.Vector3(pos[0], 0, pos[2]), ry: readRot(node), mug: !!node.mug, variant: node.variant, walk: /walk/i.test(node.kind || node.type || '') });
      }
      return;
    }
    for (const [k, v] of Object.entries(node)) if (!['variants', 'models'].includes(k)) visit(v, depth + 1);
  };
  visit(json);
  return { variants, people };
}

/**
 * The organizer's crowd.json (version 1): vendors, queues, walkers, groups and benches, each person naming a model,
 * a clip, a phase and colours for the coat, scarf and hat materials. Members are relative to their group and face
 * its pos unless they carry their own rotY. Entries are most important first, so the lite market keeps the head.
 */
function parseOrganizer(json) {
  const people = [];
  const person = (m, extra) => ({
    model: m.model ? rel(m.model) : null, variant: m.variant, clip: m.clip || null, idleClip: m.idle_clip || null,
    phase: Number(m.phase) || 0, colors: m.colors || null, mug: !!m.mug, kind: m.kind || extra.kind, id: m.id || null, stall: m.stall || null, ...extra,
  });
  const v3 = (a) => (a.length >= 3 ? new THREE.Vector3(a[0], a[1], a[2]) : new THREE.Vector3(a[0], 0, a[1]));
  const skip = new Set(['version', 'about', 'clips', 'variants', 'lite', 'musicians', 'count']);
  for (const [key, list] of Object.entries(json)) {
    if (skip.has(key) || !Array.isArray(list)) continue;
    for (const e of list) {
      if (!e || typeof e !== 'object') continue;
      if (Array.isArray(e.path) && e.path.length >= 2) {
        const path = e.path.map((q) => new THREE.Vector3(q[0], 0, q[q.length === 3 ? 2 : 1]));
        people.push(person(e, { kind: 'walker', path, speed: Number(e.speed) || 0.9, start: Number(e.start) || 0, pos: path[0].clone(), ry: 0 }));
      } else if (Array.isArray(e.members) && Array.isArray(e.pos)) {
        const c = v3(e.pos);
        for (const m of e.members) {
          const at = Array.isArray(m.pos) ? c.clone().add(v3(m.pos)) : c.clone();
          const ry = Number.isFinite(Number(m.rotY)) && m.rotY !== undefined ? Number(m.rotY) : Math.atan2(c.x - at.x, c.z - at.z);
          people.push(person(m, { kind: e.kind || 'group', pos: at, ry }));
        }
      } else if (Array.isArray(e.pos)) {
        people.push(person(e, { kind: e.kind || 'person', pos: v3(e.pos), ry: Number(e.rotY) || 0 }));
      }
    }
  }
  const variants = (json.variants || []).map((v) => rel(typeof v === 'string' ? v : v.model || ''));
  return { variants, people, organizer: true, cap: Number(json.lite?.cap) || 40 };
}

/** Musicians from crowd.json: [{ slot, model, clip, rest_clip, seated }] (placed by engine/instruments.js). */
export function crowdMusicians() {
  const list = RAW?.musicians;
  if (!Array.isArray(list)) return [];
  return list.filter((m) => m && m.slot && m.model).map((m) => ({ slot: String(m.slot).toLowerCase(), model: rel(m.model), clip: m.clip || 'play', rest: m.rest_clip || 'rest', seated: !!m.seated }));
}

/** Recolour the organizer's coat / scarf / hat materials; one material per colour, shared. */
const recolorCache = new Map();
function recolor(root, colors) {
  if (!colors) return;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const swap = (m) => {
      const want = m && colors[m.name];
      if (!want) return m;
      const key = `${m.uuid}|${want}`;
      if (!recolorCache.has(key)) { const c = liftMaterial(m.clone()); c.color = new THREE.Color(want); recolorCache.set(key, c); }
      return recolorCache.get(key);
    };
    o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material);
  });
}

function fallbackCrowd(avoid) {
  const r = rng(77);
  const people = [];
  GROUPS.forEach(([gx, gz]) => {
    const n = 2 + (r() < 0.6 ? 1 : 0) + (r() < 0.25 ? 1 : 0);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + r();
      const x = gx + Math.cos(a) * 0.65, z = gz + Math.sin(a) * 0.65;
      people.push({ pos: new THREE.Vector3(x, 0, z), ry: Math.atan2(gx - x, gz - z), mug: r() < 0.7 });
    }
  });
  // walkers pace the lanes between the stalls
  for (let i = 0; i < 16; i++) {
    let x, z, len, tries = 0;
    const clear = () => [0, 0.25, 0.5, 0.75, 1].every((k) => avoid(x - len / 2 + k * len, z));
    do { x = (r() - 0.5) * 30; z = -3 + r() * 20; len = 5 + r() * 7; } while (!clear() && ++tries < 60);
    if (!clear()) continue;
    people.push({ pos: new THREE.Vector3(x, 0, z), path: [new THREE.Vector3(x - len / 2, 0, z), new THREE.Vector3(x + len / 2, 0, z)], speed: 0.7 + r() * 0.5, mug: r() < 0.3 });
  }
  for (let i = 0; i < 8; i++) {
    const x = (i % 2 ? 1 : -1) * (17 + r() * 1.5);
    people.push({ pos: new THREE.Vector3(x, 0, 0), path: [new THREE.Vector3(x, 0, -9), new THREE.Vector3(x, 0, 14)], speed: 0.6 + r() * 0.5, mug: r() < 0.3 });
  }
  return { variants: [], people };
}

// Where a vendor stands is the organizer's, but the site needs the panel view clear in a few stalls. The
// bookseller stood right in front of Mac's five books (the middle of the lower shelf), so in the Bücherstand
// view his head hid them. He steps this far (metres) sideways along the counter, to his right: the
// customer's left, beside the open book. Positive is his right hand.
export const VENDOR_STEP = { buecherstand: 0.62 };

function stepVendors(people) {
  for (const p of people) {
    const d = p.kind === 'vendor' && VENDOR_STEP[p.stall];
    if (!d) continue;
    const ry = p.ry || 0; // the vendor faces +Z turned by ry; his right hand is -X turned by ry
    p.pos = p.pos.clone().add(new THREE.Vector3(-Math.cos(ry), 0, Math.sin(ry)).multiplyScalar(d));
  }
}

export async function createCrowd({ scene, overlay, lite, manager, warn, avoid, phrases, lodFar = LOD_FAR }) {
  const lod = { far: lodFar, near: Math.max(0, lodFar - 2) };
  const isOrganizer = RAW && RAW.version && ['vendors', 'queues', 'walkers', 'groups'].some((k) => Array.isArray(RAW[k]));
  const data = RAW ? (isOrganizer ? parseOrganizer(RAW) : parseCrowd(RAW)) : null;
  const plan = data && data.people.length ? data : fallbackCrowd(avoid);
  if (RAW && !(data && data.people.length)) warn('crowd.json has no people the engine can read; using the prototype crowd.');
  const cap = lite ? plan.cap || 40 : 90;
  const people = plan.people.slice(0, cap);
  stepVendors(people);

  // person models, if the organizer has shipped them: each person names a file, or an index into variants
  const byFile = new Map();
  const alias = (v) => (lite && LITE_ALIAS[v] && modelExists(liteVariant(LITE_ALIAS[v]) || LITE_ALIAS[v]) ? LITE_ALIAS[v] : v);
  const want = new Set(people.map((p) => p.model).filter(Boolean));
  if (!lite) plan.variants.forEach((v) => want.add(v));
  await Promise.all([...new Set([...want].map(alias))].map(async (v) => {
    const file = (lite && liteVariant(v)) || v;
    if (!modelExists(file)) return;
    try { byFile.set(v, await loadGlb(file, manager)); } catch (e) { warn(`crowd: could not load ${file}.`); }
  }));
  for (const v of want) if (alias(v) !== v && byFile.has(alias(v))) byFile.set(v, byFile.get(alias(v)));
  const variantRoots = plan.variants.map((v) => byFile.get(v)).filter(Boolean);
  const sourceFor = (p, i) => (p.model && byFile.get(p.model)) || (Number.isInteger(p.variant) && byFile.get(plan.variants[p.variant])) || (variantRoots.length ? variantRoots[i % variantRoots.length] : null);

  /** One figure of a person (the full or the lite model): a recoloured skinned clone with its own mixer. */
  const noMug = (p) => (p.clip && /_free$/.test(p.clip)) || (plan.organizer && p.mug === false);
  function makeLevel(src, p, phase) {
    const fig = cloneSkinned(compactFigure(src));
    paintFigure(fig, p.colors);
    recolor(fig, p.colors);
    // the full figure's own materials get the same lift as the merged ones, so a person does not change
    // brightness when they switch level
    fig.traverse((o) => { if (o.isMesh && !Array.isArray(o.material) && PARTS.has(o.material.name)) liftMaterial(o.material); });
    // a figure without a mug still carries the (scaled-away) mug mesh: skip drawing it
    if (noMug(p)) fig.traverse((o) => { if (o.isMesh && /^mug/i.test(o.name)) o.visible = false; });
    fig.traverse((o) => { if (o.isMesh) { o.castShadow = !lite; o.receiveShadow = false; } });
    const level = { root: fig, mixer: null, clips: null };
    const clips = src.userData.animations || [];
    if (clips.length) {
      const mixer = new THREE.AnimationMixer(fig);
      const named = (n) => n && clips.find((c) => c.name === n);
      const clip = named(p.clip) || clips.find((c) => (p.path ? /walk/i : /idle|stand|talk/i).test(c.name)) || clips[0];
      const action = mixer.clipAction(clip).play();
      // the walk cycle is authored at 1.0 m/s (children 0.8): match the feet to the ground speed
      if (p.path && /walk/i.test(clip.name)) action.timeScale = (p.speed || 0.9) / (/child/i.test(p.model || '') ? 0.8 : 1.0);
      mixer.setTime(phase);
      level.mixer = mixer;
      level.clips = { all: clips, action, base: clip, mixer };
    }
    return level;
  }

  const r = rng(91);
  const root = new THREE.Group();
  root.name = 'crowd';
  scene.add(root);
  const crowd = people.map((p, i) => {
    const g = new THREE.Group();
    g.name = p.id || `person_${i}`;
    const src = sourceFor(p, i);
    const phase = p.phase || r() * 5;
    let levels;
    if (src) {
      const hi = makeLevel(src, p, phase);
      g.add(hi.root);
      const box = new THREE.Box3().setFromObject(hi.root);
      g.userData.head = box.max.y - 0.12;
      levels = [hi];
    } else {
      const fig = buildPerson(r, { mug: p.mug });
      fig.traverse((o) => { if (o.isMesh) { o.castShadow = !lite; o.receiveShadow = false; } });
      g.add(fig);
      g.userData.head = (fig.userData.head || 1.6) * fig.scale.y;
      levels = [{ root: fig, mixer: null, clips: null }];
    }
    g.position.copy(p.pos);
    if (p.facing) g.rotation.y = Math.atan2(p.facing.x - p.pos.x, p.facing.z - p.pos.z);
    else g.rotation.y = p.ry || 0;
    root.add(g);
    const person = { g, plan: p, levels, lvl: levels[0], phase, kind: p.kind, vendor: p.kind === 'vendor', walk: !!p.path, path: p.path, seg: 0, dir: 1, speed: p.speed || 0.8, ph: r() * 6, sayUntil: 0, head: g.userData.head || 1.6 };
    if (person.walk) {
      // start part-way along the path (crowd.json "start" is the fraction of its length)
      const lens = p.path.slice(1).map((b, k) => b.distanceTo(p.path[k]));
      let d = (p.start ?? r()) * lens.reduce((a, b) => a + b, 0);
      person.seg = 0;
      while (person.seg < lens.length - 1 && d > lens[person.seg]) d -= lens[person.seg++];
      person.u = lens[person.seg] ? d / lens[person.seg] : 0;
      person.g.position.lerpVectors(p.path[person.seg], p.path[person.seg + 1], person.u);
    }
    return person;
  });
  const vendors = crowd.filter((p) => p.vendor);
  let lodOn = false;

  /**
   * Full market only: load each figure's .lite.glb and give every person a second, lighter level that is
   * drawn beyond LOD_FAR metres. Called after the first frame, so it never delays the market opening.
   */
  async function enableLod() {
    if (lite || lodOn) return 0;
    const files = new Map();
    for (const p of crowd) {
      const m = p.plan.model || (Number.isInteger(p.plan.variant) ? plan.variants[p.plan.variant] : null);
      const lv = m && liteVariant(m);
      if (lv && p.levels[0].clips) files.set(p, lv);
    }
    const loaded = new Map();
    await Promise.all([...new Set(files.values())].map(async (f) => {
      try { loaded.set(f, await loadGlb(f, manager)); } catch { warn(`crowd: could not load ${f} for the distance level.`); }
    }));
    let n = 0;
    for (const [p, f] of files) {
      const src = loaded.get(f);
      if (!src) continue;
      const lo = makeLevel(src, p.plan, p.phase);
      lo.root.visible = false;
      p.g.add(lo.root);
      p.levels.push(lo);
      n++;
    }
    lodOn = true;
    return n;
  }
  const _cp = new THREE.Vector3();
  function applyLod(p, camPos) {
    if (p.levels.length < 2) return;
    const d2 = p.g.position.distanceToSquared(camPos);
    const want = p.lvl === p.levels[0] ? (d2 > lod.far * lod.far ? 1 : 0) : (d2 < lod.near * lod.near ? 0 : 1);
    const next = p.levels[want];
    if (next === p.lvl) return;
    // carry the clip time over, so the switch does not restart a step or a sip
    if (next.mixer && p.lvl.mixer) next.mixer.setTime(p.lvl.mixer.time);
    p.lvl.root.visible = false;
    next.root.visible = true;
    p.lvl = next;
  }

  const bubbles = [];
  let T = 0, nextTalk = 2;
  const tmp = new THREE.Vector3();
  const standing = crowd.filter((p) => !p.walk);

  function speak(p, text) {
    p.sayUntil = T + 3.2;
    const d = document.createElement('div');
    d.className = 'bubble';
    d.textContent = text;
    d.style.opacity = '0';
    overlay.appendChild(d);
    bubbles.push({ p, d });
  }

  /** Play another of a person's clips for a while (e.g. drink for Prost), then go back. Only for people holding a mug. */
  function gesture(p, name, secs) {
    const c = p.lvl.clips;
    if (!c || /_free$/.test(c.base.name) || p.walk) return;
    const clip = c.all.find((x) => x.name === name);
    if (!clip || clip === c.base) return;
    const a = c.mixer.clipAction(clip);
    a.reset().setEffectiveWeight(1).play();
    c.action.crossFadeTo(a, 0.35, false);
    clearTimeout(p.gestureTimer);
    p.gestureTimer = setTimeout(() => { c.action.reset().play(); a.crossFadeTo(c.action, 0.5, false); }, secs * 1000);
  }

  const segDir = new THREE.Vector3(), probe = new THREE.Vector3(), rel = new THREE.Vector3();
  /**
   * Does a person at `pos` stand between a close camera and what it looks at? Anyone in front of the camera,
   * nearer than the target, inside a cone of about 35 degrees round the sight line (body or head).
   */
  function blocks(pos, from, dir, len) {
    for (const y of [1.0, 1.6]) {
      probe.set(pos.x, pos.y + y, pos.z);
      rel.subVectors(probe, from);
      const s = rel.dot(dir);
      if (s < 0.2 || s > len - 1.2) continue;
      if (rel.addScaledVector(dir, -s).length() < 0.8 + s * 0.7) return true;
    }
    return false;
  }

  /** Is a person on the line from the camera to a vendor's chest, nearer than the vendor? (a narrow cone) */
  const vLine = [];
  function blocksVendor(pos, from) {
    for (const v of vLine) {
      for (const y of [1.0, 1.55]) {
        probe.set(pos.x, pos.y + y, pos.z);
        rel.subVectors(probe, from);
        const s = rel.dot(v.dir);
        if (s < 0.3 || s > v.len - 0.45) continue;
        if (rel.addScaledVector(v.dir, -s).length() < 0.32 + s * 0.09) return true;
      }
    }
    return false;
  }
  const _vp = new THREE.Vector3();
  /** Vendors a close camera can see: in front of it, within 14 m and near the middle of the view. */
  function vendorLines(camera, look) {
    vLine.length = 0;
    for (const v of vendors) {
      _vp.copy(v.g.position); _vp.y += 1.25;
      const dir = _vp.clone().sub(camera.position);
      const len = dir.length();
      if (len > 14) continue;
      dir.divideScalar(len);
      if (dir.dot(look) < 0.8) continue; // more than ~37 degrees off the sight line
      vLine.push({ dir, len });
    }
  }

  return {
    group: root,
    count: crowd.length,
    enableLod,
    /** Distance LOD: beyond `far` metres a person draws their lite figure (0: everyone does). */
    setLod(far) { lod.far = Math.max(0, far); lod.near = Math.max(0, far - 2); },
    get lod() { return { ...lod }; },
    get lodLevels() { return crowd.filter((p) => p.levels.length > 1).length; },
    /** Numbers for tests and the debug report. */
    stats() {
      let hidden = 0, far = 0;
      for (const p of crowd) { if (!p.g.visible) hidden++; if (p.levels.length > 1 && p.lvl === p.levels[1]) far++; }
      return { people: crowd.length, hidden, lite: far, lodFar: lod.far, vendorsVisible: vendors.filter((v) => v.g.visible).length };
    },
    /** For tests: the people stepped out of the current shot. */
    hiddenIds: () => crowd.filter((p) => !p.g.visible).map((p) => p.g.name),
    /** For tests: everyone's name, feet position, visibility and whether they are a vendor. */
    people: () => crowd.map((p) => ({ name: p.g.name, pos: p.g.position.toArray(), visible: p.g.visible, vendor: p.vendor, stall: p.plan.stall || null })),
    speak,
    /** Up to five standing people near `center` say `text`, one after another, and raise their mugs if they have one. */
    say(text, center, radius) {
      standing.filter((p) => p.g.visible && p.g.position.distanceTo(center) < radius).slice(0, 5).forEach((p, i) => setTimeout(() => { speak(p, text); gesture(p, 'drink', 2.6); }, i * 280));
    },
    update(dt, t, camera, w, h, { still, chatter = true, look = null }) {
      T = t;
      // people standing between a close camera and what it looks at step out of the shot
      let seg = 0;
      if (look) {
        segDir.subVectors(look, camera.position);
        seg = segDir.length();
        segDir.divideScalar(seg || 1);
        if (seg < 20) vendorLines(camera, segDir); else vLine.length = 0;
      }
      camera.getWorldPosition(_cp);
      for (const p of crowd) {
        // Vendors stay: they are what a close-up looks at. Anyone else on the sight line, or on the line to a
        // vendor in view (the queue at the counter), steps out of the shot.
        if (look) p.g.visible = p.vendor || !(seg < 20 && (blocks(p.g.position, camera.position, segDir, seg) || blocksVendor(p.g.position, camera.position)));
        if (lodOn) applyLod(p, _cp);
        if (p.lvl.mixer && !still && p.g.visible) p.lvl.mixer.update(dt);
        if (p.walk && !still) {
          const a = p.path[p.seg], b = p.path[p.seg + 1];
          const len = a.distanceTo(b) || 1;
          p.u += (dt * p.speed * p.dir) / len;
          if (p.u > 1 || p.u < 0) {
            p.u = THREE.MathUtils.clamp(p.u, 0, 1);
            if (p.dir > 0 && p.seg < p.path.length - 2) { p.seg++; p.u = 0; } else if (p.dir < 0 && p.seg > 0) { p.seg--; p.u = 1; } else p.dir *= -1;
          }
          const A = p.path[p.seg], B = p.path[p.seg + 1];
          p.g.position.lerpVectors(A, B, p.u);
          p.g.rotation.y = Math.atan2((B.x - A.x) * p.dir, (B.z - A.z) * p.dir);
          if (!p.lvl.mixer) {
            p.ph += dt * p.speed * 5.2;
            p.g.position.y = Math.abs(Math.cos(p.ph)) * 0.035;
            p.g.rotation.z = Math.sin(p.ph) * 0.03;
          }
        } else if (!p.walk && !still && !p.lvl.mixer) {
          p.g.rotation.z = Math.sin(t * 0.9 + p.ph) * 0.012;
        }
      }
      if (chatter && !still && t > nextTalk && standing.length) {
        const cand = standing.filter((p) => p.g.visible && t > p.sayUntil + 2);
        if (cand.length) speak(cand[(Math.random() * cand.length) | 0], phrases[(Math.random() * phrases.length) | 0]);
        nextTalk = t + 1.4 + Math.random() * 1.6;
      }
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];
        if (T > b.p.sayUntil) { b.d.remove(); bubbles.splice(i, 1); continue; }
        tmp.copy(b.p.g.position); tmp.y += b.p.head + 0.45;
        const dist = tmp.distanceTo(camera.position);
        tmp.project(camera);
        const vis = b.p.g.visible && tmp.z < 1 && dist < 30 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1;
        b.d.style.opacity = vis ? String(Math.min(1, (30 - dist) / 8)) : '0';
        b.d.style.left = ((tmp.x + 1) / 2) * w + 'px';
        b.d.style.top = ((1 - tmp.y) / 2) * h + 'px';
      }
    },
  };
}
