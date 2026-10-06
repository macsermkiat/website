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
import { bakeFigure, createFarFigure } from './crowdFar.js';
import { shadowStandIns } from './engine/merge.js';

const crowdFiles = import.meta.glob('./crowd.json', { eager: true, import: 'default' });
const RAW = crowdFiles['./crowd.json'] ?? null;

const GROUPS = [[-3.5, 5], [4, 4.2], [-9.5, 8], [9.5, 8.5], [0, 10], [-15, 9], [15, 10], [-5.5, 1.5], [6, 1.8], [-1.5, 14], [11, 13], [-17, 0], [17, 7], [-16.5, -6], [-7, -14], [1, -15.5], [11, -16], [-11, 15], [5, 17], [-4, -10.5], [13, -4.5]];

// The lite market draws its 40 people from a smaller set of figures (recoloured, so the crowd still varies):
// three fewer downloads, about 300 KB.
const LITE_ALIAS = {
  'people_man_parka.glb': 'people_man_coat.glb',
  'people_woman_young.glb': 'people_woman_coat.glb',
  'people_child_girl.glb': 'people_child_boy.glb',
  'people_woman_parka.glb': 'people_woman_coat.glb', // round 8's new figure: the lite market draws the coat in its place
};
// People farther than lod.far metres from the camera are drawn by the far crowd (crowdFar.js): their .lite.glb
// figure, baked into a vertex animation texture and instanced, one draw call per figure for everyone far away;
// back nearer than lod.near they are their own skinned figure again. Round 8 (docs/adr/0004): about 80 people,
// the switch at about 25 m, and the skinned people beyond 12 m animate every second frame (beyond 18 m every
// third), so the CPU's share stays flat. The defaults depend on the GPU class (quality.js), ?lod=far overrides
// them, and the frame-time governor in main.js pulls them in on a machine that cannot keep up.
export const LOD_FAR = 25, LOD_NEAR = 23;
const THROTTLE = [[18, 3], [12, 2]]; // [metres, update every n-th frame]

// ---------- one draw call per figure ----------
// The organizer's figures have four body parts (coat, body, hat, scarf), each its own material, so four draw
// calls (and four more in the moon's shadow pass) per person. The lite figures carry no textures besides one
// shared occlusion map, so their parts can be one mesh: each part's colour goes into the vertex colours
// (times the figure's own COLOR_0), and one material draws the whole crowd. Recolouring a person rewrites the
// colour attribute of their own copy of the geometry; everything else is shared.
const PARTS = new Set(['coat', 'body', 'hat', 'scarf']);
const QUERY = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
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

/**
 * The same skin: one skeleton, or (a figure copied by SkeletonUtils.clone, which gives each mesh its own skeleton
 * object) the same bones with the same inverse bind matrices.
 */
function sameSkin(a, b) {
  if (a === b) return true;
  if (!a || !b || a.bones.length !== b.bones.length) return false;
  return a.bones.every((x, i) => x === b.bones[i]) && a.boneInverses.every((m, i) => m.equals(b.boneInverses[i]));
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
    if (list.length < 2 || list.some((o) => !sameSkin(o.skeleton, list[0].skeleton))) continue;
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

// ---------- one draw per near figure on the full market (round 10) ----------
// The full figures keep their cloth normal maps (wool on the coat, knit on the hat and scarf), so compactFigure
// leaves them as five meshes: five draws a person, and five more in every moon-shadow pass. Here a figure's parts
// become one skinned mesh with one material that does per part what the five did: each vertex carries its part,
// and the part picks its roughness, its normal map (none, the first or the second) and normal scale, whether it is
// one-sided (a back face of a one-sided part is discarded, as culling would) and whether the crowd's lift applies
// (the mug has none); colours go into the vertex colours (part colour times COLOR_0), as for the lite figures, so a
// person's own colours repaint their copy of the geometry. The shadows come from two hidden stand-ins on the same
// skeleton (the double-sided parts and the one-sided ones, as three's shadow pass treats them), drawn only in the
// shadow passes (engine/merge.js shadowStandIns). A figure is built twice at most: with its mug, and without.
const fullTemplates = new WeakMap();
const MAX_PARTS = 8;
function fullFigureMaterial(parts, normalA, normalB, ao, lift) {
  const m = new THREE.MeshStandardMaterial({ name: 'crowd_figure_full', vertexColors: true, roughness: 1, metalness: 0, side: THREE.DoubleSide, normalMap: normalA || normalB || null, aoMap: ao || null });
  const arr = (f) => Array.from({ length: MAX_PARTS }, (_, i) => (parts[i] ? f(parts[i]) : 0));
  const uni = {
    cfRough: { value: arr((p) => p.roughness) },
    cfNMap: { value: arr((p) => p.nmap) },
    cfNScale: { value: Array.from({ length: MAX_PARTS }, (_, i) => (parts[i]?.nscale || new THREE.Vector2(1, 1)).clone()) },
    cfFront: { value: arr((p) => (p.front ? 1 : 0)) },
    cfLift: { value: arr((p) => (p.lift ? 1 : 0)) },
    cfNormalB: { value: normalA && normalB ? normalB : null },
  };
  const twoMaps = !!(normalA && normalB);
  // lit like the parts it draws: the crowd's lift per part (below), and the lighting module's figure terms
  // (it marks materials flagged crowdLift); the band's players have neither
  m.userData.crowdLift = !!lift;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uni);
    shader.uniforms.crowdLift = crowdLift;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float aPart;\nvarying float vPart;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vPart = aPart;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
varying float vPart;
uniform float cfRough[ ${MAX_PARTS} ];
uniform float cfNMap[ ${MAX_PARTS} ];
uniform vec2 cfNScale[ ${MAX_PARTS} ];
uniform float cfFront[ ${MAX_PARTS} ];
uniform float cfLift[ ${MAX_PARTS} ];
uniform float crowdLift;
${twoMaps ? 'uniform sampler2D cfNormalB;' : ''}`)
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
  int cfPart = int( vPart + 0.5 );
  if ( cfFront[ cfPart ] > 0.5 && ! gl_FrontFacing ) discard;`)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = cfRough[ cfPart ];')
      .replace('#include <normal_fragment_maps>', `#ifdef USE_NORMALMAP_TANGENTSPACE
  {
    vec3 cfA = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
    ${twoMaps ? 'vec3 cfB = texture2D( cfNormalB, vNormalMapUv ).xyz * 2.0 - 1.0;' : 'vec3 cfB = cfA;'}
    float cfN = cfNMap[ cfPart ];
    vec3 mapN = cfN > 1.5 ? cfB : ( cfN > 0.5 ? cfA : vec3( 0.0, 0.0, 1.0 ) );
    mapN.xy *= cfNScale[ cfPart ];
    normal = normalize( tbn * mapN );
  }
#endif`)
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n  totalEmissiveRadiance += ( diffuseColor.rgb * 0.8 + vec3( 0.006, 0.0065, 0.009 ) ) * crowdLift * vec3( 0.55, 0.5, 0.62 ) * cfLift[ cfPart ];');
  };
  m.customProgramCacheKey = () => `crowdFull|${twoMaps ? 2 : 1}`;
  return m;
}

/**
 * The figure (a template to clone per person) with its parts in one mesh, or null when it cannot be done.
 * `shadows`: make the shadow stand-ins (the full market); `lift`: the crowd's lift on the cloth (not the band).
 */
function fullFigureTemplate(src, withMug, { shadows = true, lift = true } = {}) {
  let t = fullTemplates.get(src);
  if (!t) fullTemplates.set(src, (t = {}));
  const key = `${withMug ? 'mug' : 'bare'}|${shadows}|${lift}`;
  if (key in t) return t[key];
  t[key] = null;
  const tpl = cloneSkinned(src);
  const list = [];
  tpl.traverse((o) => {
    if (!o.isSkinnedMesh || Array.isArray(o.material) || !o.visible) return;
    const isMug = /^mug/i.test(o.name) || /^mug/i.test(o.material.name || '');
    if (isMug && !withMug) { o.visible = false; return; }
    if (PARTS.has(o.material.name) || isMug) list.push({ o, isMug });
  });
  if (list.length < 2 || list.length > MAX_PARTS) return null;
  // the parts may hang off different nodes (the body's primitives under one, the mug under its own); they must sit
  // in the same place and bind to the same skeleton the same way
  const first = list[0].o;
  tpl.updateMatrixWorld(true);
  const near = (a, b) => a.elements.every((v, i) => Math.abs(v - b.elements[i]) < 1e-6);
  if (list.some(({ o }) => o.bindMode !== first.bindMode || !near(o.matrixWorld, first.matrixWorld) || !near(o.bindMatrix, first.bindMatrix))) return null;
  // a part on a skin of its own (the mug: its own skin over the same bones, bound in another pose) is moved onto the
  // first part's skin: each joint maps to the same bone there, and a vertex is carried from its own bind pose to
  // that skin's (bindMatrix⁻¹ · boneInverse_first⁻¹ · boneInverse_own · bindMatrix), which is exact for a vertex
  // whose joints all need the same carry (the mug hangs off one hand)
  const skel = first.skeleton;
  const remaps = new Map();
  const bindInv = first.bindMatrix.clone().invert();
  for (const { o } of list) {
    if (o.skeleton === skel) continue;
    const map = o.skeleton.bones.map((b) => skel.bones.indexOf(b));
    if (map.some((k) => k < 0)) return null;
    const carry = map.map((k, j) => {
      if (near(o.skeleton.boneInverses[j], skel.boneInverses[k])) return null;
      return bindInv.clone().multiply(skel.boneInverses[k].clone().invert()).multiply(o.skeleton.boneInverses[j]).multiply(first.bindMatrix);
    });
    remaps.set(o, { map, carry });
  }
  // the textures: at most two distinct normal maps, one occlusion map (any channel), no other maps
  const normals = [];
  let ao = null;
  for (const { o } of list) {
    const m = o.material;
    if (!m.isMeshStandardMaterial || m.map || m.roughnessMap || m.metalnessMap || m.emissiveMap || m.alphaMap || m.transparent || m.metalness !== 0 || (m.emissive && m.emissive.getHex() !== 0)) return null;
    if (m.normalMap && !normals.some((n) => n.source === m.normalMap.source)) normals.push(m.normalMap);
    if (m.aoMap) { if (ao && ao.source !== m.aoMap.source) return null; ao ||= m.aoMap; }
    if (!m.vertexColors && o.geometry.getAttribute('color')) return null;
  }
  if (normals.length > 2) return null;
  const parts = [], geos = [], shadowSides = { double: [], front: [] };
  let start = 0;
  for (const [i, { o, isMug }] of list.entries()) {
    const m = o.material, g = o.geometry;
    const n = g.getAttribute('position').count;
    const out = new THREE.BufferGeometry();
    const copy = (name, from = name, Arr = Float32Array) => {
      const a = g.getAttribute(from);
      const size = a ? a.itemSize : (name === 'uv' || name === 'uv1' ? 2 : 3);
      const arr = new Arr(n * size);
      if (a) { const get = [(k) => a.getX(k), (k) => a.getY(k), (k) => a.getZ(k), (k) => a.getW(k)]; for (let k = 0; k < n; k++) for (let c = 0; c < size; c++) arr[k * size + c] = get[c](k); }
      out.setAttribute(name, new THREE.BufferAttribute(arr, size));
    };
    copy('position'); copy('normal'); copy('uv'); copy('skinIndex', 'skinIndex', Uint16Array); copy('skinWeight');
    const remap = remaps.get(o);
    if (remap) {
      const si = out.getAttribute('skinIndex').array, sw = out.getAttribute('skinWeight').array;
      const pos = out.getAttribute('position'), nor = out.getAttribute('normal');
      const v = new THREE.Vector3(), nm = new THREE.Matrix3();
      for (let k = 0; k < n; k++) {
        let c;
        for (let q = 0; q < 4; q++) {
          if (sw[k * 4 + q] <= 1e-5) continue;
          const cj = remap.carry[si[k * 4 + q]] || null;
          if (c === undefined) c = cj;
          else if (!(c === cj || (c && cj && near(c, cj)))) return null; // joints that need different carries
        }
        if (c) {
          pos.setXYZ(k, ...v.fromBufferAttribute(pos, k).applyMatrix4(c).toArray());
          nm.getNormalMatrix(c);
          nor.setXYZ(k, ...v.fromBufferAttribute(nor, k).applyMatrix3(nm).normalize().toArray());
        }
        for (let q = 0; q < 4; q++) si[k * 4 + q] = remap.map[si[k * 4 + q]] ?? 0;
      }
    }
    // the occlusion map's coordinates, wherever the part read them from
    copy('uv1', m.aoMap ? (m.aoMap.channel ? `uv${m.aoMap.channel}` : 'uv') : 'uv');
    const own = g.getAttribute('color');
    const base = new Float32Array(n * 3).fill(1);
    if (own) for (let k = 0; k < n; k++) { base[k * 3] = own.getX(k); base[k * 3 + 1] = own.getY(k); base[k * 3 + 2] = own.getZ(k); }
    out.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    out.setAttribute('aPart', new THREE.BufferAttribute(new Float32Array(n).fill(i), 1));
    out.setIndex(g.index ? Array.from(g.index.array) : [...Array(n).keys()]);
    geos.push(out);
    parts.push({
      name: m.name, start, count: n, base, color: m.color.clone(),
      roughness: m.roughness, nmap: m.normalMap ? 1 + normals.findIndex((x) => x.source === m.normalMap.source) : 0,
      nscale: m.normalScale ? m.normalScale.clone() : new THREE.Vector2(1, 1), front: m.side === THREE.FrontSide, lift: lift && !isMug && PARTS.has(m.name),
    });
    (m.side === THREE.DoubleSide ? shadowSides.double : shadowSides.front).push(out);
    start += n;
  }
  const merged = mergeGeometries(geos, false);
  if (!merged) return null;
  const aoTex = ao ? (ao.channel === 1 ? ao : Object.assign(ao.clone(), { channel: 1 })) : null;
  merged.userData.parts = parts;
  paint(merged.getAttribute('color'), parts, null);
  merged.computeBoundingSphere(); merged.computeBoundingBox();
  const mesh = new THREE.SkinnedMesh(merged, fullFigureMaterial(parts, normals[0], normals[1], aoTex, lift));
  mesh.name = 'figure';
  mesh.position.copy(first.position); mesh.quaternion.copy(first.quaternion); mesh.scale.copy(first.scale);
  mesh.bind(first.skeleton, first.bindMatrix);
  mesh.bindMode = first.bindMode;
  mesh.frustumCulled = first.frustumCulled;
  mesh.userData.castsByProxy = shadows; // its shadow comes from the stand-ins below
  first.parent.add(mesh);
  for (const [side, gs] of [[THREE.DoubleSide, shadowSides.double], [THREE.FrontSide, shadowSides.front]]) {
    if (!gs.length || !shadows) continue;
    const sg = mergeGeometries(gs.map((x) => { const y = new THREE.BufferGeometry(); for (const nm of ['position', 'skinIndex', 'skinWeight']) y.setAttribute(nm, x.getAttribute(nm)); y.setIndex(x.index); return y; }), false);
    if (!sg) continue;
    sg.computeBoundingSphere(); sg.computeBoundingBox();
    const sm = new THREE.SkinnedMesh(sg, new THREE.MeshBasicMaterial({ name: 'engine_shadow_proxy', side, colorWrite: false, depthWrite: false }));
    sm.name = 'engine_shadow_proxy';
    sm.position.copy(first.position); sm.quaternion.copy(first.quaternion); sm.scale.copy(first.scale);
    sm.bind(first.skeleton, first.bindMatrix);
    sm.bindMode = first.bindMode;
    sm.frustumCulled = first.frustumCulled;
    sm.visible = false;
    sm.castShadow = true;
    sm.receiveShadow = false;
    sm.raycast = () => {};
    sm.userData.shadowProxy = true;
    first.parent.add(sm);
  }
  for (const { o } of list) o.removeFromParent();
  t[key] = tpl;
  return tpl;
}

/**
 * The band's players (engine/instruments.js): a player's figure in one draw as the crowd's (no lift: the band is
 * lit as it was), with shadow stand-ins on the full market. Returns the figure to use (the loaded one when the
 * parts cannot be merged), its clips carried over.
 */
export function compactMusician(g, lite) {
  if (QUERY.get('figures') === '0') return g;
  const tpl = fullFigureTemplate(g, true, { shadows: !lite && QUERY.get('proxies') !== '0', lift: false });
  if (!tpl) return g;
  Object.defineProperty(tpl.userData, 'animations', { value: g.userData.animations || [], enumerable: false, writable: true, configurable: true });
  tpl.name = g.name;
  tpl.traverse((o) => { if (o.userData.shadowProxy) shadowStandIns.add(o); });
  return tpl;
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

/**
 * The shared clips (crowd.json "shared_anims": people_anims.glb, every crowd and vendor clip on one skeleton with no
 * mesh). Loaded once per market; null when the file or the entry is missing. Its hips rest height is kept, because
 * the clips' hips.position keys are absolute for the reference figure.
 */
async function loadSharedAnims(manager, warn) {
  const file = rel(RAW?.shared_anims?.file || 'people_anims.glb');
  if (!modelExists(file)) return null;
  try {
    const root = await loadGlb(file, manager);
    const clips = root.userData.animations || [];
    if (!clips.length) return null;
    root.updateMatrixWorld(true);
    const hips = root.getObjectByName('hips');
    return { file, clips, hipsRest: hips ? hips.position.clone() : new THREE.Vector3(), byOffset: new Map() };
  } catch {
    warn(`crowd: could not load ${file}; each figure plays only its own clips.`);
    return null;
  }
}

/**
 * A figure's clips: its own, plus every shared clip it does not carry, retargeted to its hips (each hips.position
 * key moves by the figure's hips rest minus the reference's). A figure shipped without clips plays the shared set;
 * a lite figure gains the clips its file leaves out (laugh, the _free set, serve and wipe).
 */
const WITH_SHARED = new WeakMap();
export function clipsFor(src, shared) {
  const own = src.userData.animations || [];
  if (!shared) return own;
  if (WITH_SHARED.has(src)) return WITH_SHARED.get(src);
  const have = new Set(own.map((c) => c.name));
  const hips = src.getObjectByName('hips');
  const d = hips ? hips.position.clone().sub(shared.hipsRest) : new THREE.Vector3();
  const key = d.toArray().map((v) => v.toFixed(3)).join(',');
  let set = shared.byOffset.get(key);
  if (!set) {
    set = shared.clips.map((c) => {
      if (d.lengthSq() < 1e-8) return c;
      const copy = c.clone();
      for (const t of copy.tracks) {
        if (!/(^|\.|\/)hips\.position$/.test(t.name)) continue;
        const v = t.values;
        for (let i = 0; i < v.length; i += 3) { v[i] += d.x; v[i + 1] += d.y; v[i + 2] += d.z; }
      }
      return copy;
    });
    shared.byOffset.set(key, set);
  }
  const out = own.concat(set.filter((c) => !have.has(c.name)));
  WITH_SHARED.set(src, out);
  return out;
}

export async function createCrowd({ scene, overlay, lite, manager, warn, avoid, phrases, lodFar = LOD_FAR }) {
  const lod = { far: lodFar, near: Math.max(0, lodFar - 2) };
  const isOrganizer = RAW && RAW.version && ['vendors', 'queues', 'walkers', 'groups'].some((k) => Array.isArray(RAW[k]));
  const data = RAW ? (isOrganizer ? parseOrganizer(RAW) : parseCrowd(RAW)) : null;
  const plan = data && data.people.length ? data : fallbackCrowd(avoid);
  if (RAW && !(data && data.people.length)) warn('crowd.json has no people the engine can read; using the prototype crowd.');
  // the full market's crowd: about 80 people (the organizer's crowd.json; ADR 0004), the lite market's its first 40
  const cap = lite ? plan.cap || 40 : 96;
  const people = plan.people.slice(0, cap);
  stepVendors(people);

  // person models, if the organizer has shipped them: each person names a file, or an index into variants
  const byFile = new Map();
  const alias = (v) => (lite && LITE_ALIAS[v] && modelExists(liteVariant(LITE_ALIAS[v]) || LITE_ALIAS[v]) ? LITE_ALIAS[v] : v);
  const want = new Set(people.map((p) => p.model).filter(Boolean));
  if (!lite) plan.variants.forEach((v) => want.add(v));
  const sharedAnims = loadSharedAnims(manager, warn);
  await Promise.all([...new Set([...want].map(alias))].map(async (v) => {
    const file = (lite && liteVariant(v)) || v;
    if (!modelExists(file)) return;
    try { byFile.set(v, await loadGlb(file, manager)); } catch (e) { warn(`crowd: could not load ${file}.`); }
  }));
  const shared = await sharedAnims;
  for (const v of want) if (alias(v) !== v && byFile.has(alias(v))) byFile.set(v, byFile.get(alias(v)));
  const variantRoots = plan.variants.map((v) => byFile.get(v)).filter(Boolean);
  const sourceFor = (p, i) => (p.model && byFile.get(p.model)) || (Number.isInteger(p.variant) && byFile.get(plan.variants[p.variant])) || (variantRoots.length ? variantRoots[i % variantRoots.length] : null);

  /** One figure of a person (the full or the lite model): a recoloured skinned clone with its own mixer. */
  const noMug = (p) => (p.clip && /_free$/.test(p.clip)) || (plan.organizer && p.mug === false);
  function makeLevel(src, p, phase) {
    // a near figure in one draw, its mug included (fullFigureTemplate; compactFigure if that cannot be done); on the
    // full market its shadow from the stand-ins, unless they are off (?proxies=0: the figure casts its own)
    const byProxy = QUERY.get('proxies') !== '0';
    const tpl = QUERY.get('figures') !== '0' ? fullFigureTemplate(src, !noMug(p), { shadows: !lite && byProxy }) : null;
    const fig = cloneSkinned(tpl || compactFigure(src));
    paintFigure(fig, p.colors);
    recolor(fig, p.colors);
    // the full figure's own materials get the same lift as the merged ones, so a person does not change
    // brightness when they switch level
    fig.traverse((o) => { if (o.isMesh && !Array.isArray(o.material) && PARTS.has(o.material.name)) liftMaterial(o.material); });
    // a figure without a mug still carries the (scaled-away) mug mesh: skip drawing it
    if (noMug(p)) fig.traverse((o) => { if (o.isMesh && /^mug/i.test(o.name)) o.visible = false; });
    fig.traverse((o) => { if (o.isMesh) { o.castShadow = !lite && !o.userData.castsByProxy; o.receiveShadow = false; } });
    fig.traverse((o) => { if (o.userData.shadowProxy) shadowStandIns.add(o); });
    const level = { root: fig, mixer: null, clips: null };
    const clips = clipsFor(src, shared);
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
  // stalls whose vendor has stepped back out of a camera moment (round 9: the view over the Schwibbogen stands
  // where the ornament seller does)
  const away = new Set();
  let lodOn = false;
  let frameNo = 0, updateMs = 0;
  const mixStats = { ran: 0, throttled: 0, far: 0 };

  /**
   * The far crowd: each figure's .lite.glb (the lite market's own figures), baked into a vertex animation texture
   * and instanced (crowdFar.js); every person gets a slot in their figure's instanced mesh, drawn beyond lod.far.
   * Called after the first frame and baked one figure at a time between frames, so it never holds up the market.
   */
  const farTime = { value: 0 };
  const farFigures = new Map(); // lite file -> far figure
  const farStats = { figures: 0, people: 0, bakeMs: 0, vertices: 0, rows: 0 };
  async function enableLod() {
    if (lodOn) return 0;
    lodOn = true;
    const fileOf = (p) => {
      const m = p.plan.model || (Number.isInteger(p.plan.variant) ? plan.variants[p.plan.variant] : null);
      if (!m) return null;
      return lite ? ((liteVariant(alias(m)) && modelExists(liteVariant(alias(m)))) ? liteVariant(alias(m)) : alias(m)) : liteVariant(m);
    };
    const groups = new Map(); // file -> [person]
    for (const p of crowd) {
      if (!p.levels[0].clips) continue; // a stand-in figure: stays as it is
      const f = fileOf(p);
      if (f && modelExists(f)) (groups.get(f) || groups.set(f, []).get(f)).push(p);
    }
    let n = 0;
    for (const [f, list] of groups) {
      let src;
      try { src = await loadGlb(f, manager); } catch { warn(`crowd: could not load ${f} for the far crowd.`); continue; }
      compactFigure(src);
      const clips = clipsFor(src, shared);
      // the clips these people play (by name), as the lite figure carries them
      const names = new Set(list.map((p) => p.levels[0].clips.base.name));
      const want = clips.filter((c) => names.has(c.name));
      if (!want.length) continue;
      await new Promise((r) => setTimeout(r, 0)); // a frame between figures
      let baked = null;
      try { baked = await bakeFigure(src, want); } catch (e) { warn(`crowd: could not bake ${f} (${e?.message || e}).`); }
      if (!baked) continue;
      let ao = null;
      src.traverse((o) => { if (!ao && o.isMesh && o.material?.aoMap) ao = o.material.aoMap; });
      const parts = {};
      src.traverse((o) => { for (const pt of o.geometry?.userData?.parts || []) parts[pt.name] ||= `#${pt.color.getHexString()}`; });
      // colours: a part's default is its material colour, given as linear values (the instance attribute is linear)
      const far = createFarFigure(baked, { capacity: list.length, ao, lift: liftMaterial, time: farTime, colors: null });
      const def = {};
      src.traverse((o) => { for (const pt of o.geometry?.userData?.parts || []) def[pt.name] ||= pt.color; });
      for (const p of list) {
        const cc = (k) => (p.plan.colors?.[k] ? new THREE.Color(p.plan.colors[k]) : def[k] || new THREE.Color(1, 1, 1));
        const slot = far.add(p, { mug: !noMug(p.plan) });
        // the instance colours are written as linear floats; Color(hex) already converts to the working space
        for (const [k, attr] of [['coat', 'iCoat'], ['hat', 'iHat'], ['scarf', 'iScarf']]) { const c = cc(k); far.mesh.geometry.getAttribute(attr).setXYZ(slot, c.r, c.g, c.b); }
        far.mesh.geometry.getAttribute('iCoat').needsUpdate = true;
        p.far = { fig: far, slot, clip: p.levels[0].clips.base.name, speed: p.levels[0].clips.action.timeScale || 1, on: false, root: p.levels[0].root };
        n++;
      }
      root.add(far.mesh);
      farFigures.set(f, far);
      farStats.figures++; farStats.bakeMs += baked.ms; farStats.vertices += baked.vertices; farStats.rows += baked.rows;
      void parts;
    }
    farStats.people = n;
    return n;
  }
  const _cp = new THREE.Vector3(), _m = new THREE.Matrix4();
  /** The person's world matrix for their instance (the crowd group sits at the scene's origin). */
  function farMatrix(p) {
    p.g.updateMatrix();
    return _m.multiplyMatrices(p.g.matrix, p.far.root.matrix);
  }
  function toFar(p) {
    const lv = p.levels[0];
    const t = lv.mixer ? lv.clips.action.time : 0;
    // carry the clip time over, so the switch does not restart a step or a sip
    p.far.phase = t - farTime.value * p.far.speed;
    p.far.root.updateMatrix();
    p.far.fig.show(p.far.slot, farMatrix(p), p.far.clip, p.far.phase, p.far.speed);
    lv.root.visible = false;
    p.far.on = true;
  }
  function toNear(p) {
    const lv = p.levels[0];
    p.far.fig.hide(p.far.slot);
    if (lv.mixer) {
      const d = lv.clips.base.duration || 1;
      lv.clips.action.time = (((farTime.value * p.far.speed + (p.far.phase || 0)) % d) + d) % d;
      lv.mixer.update(0);
      p.mixDt = 0;
    }
    lv.root.visible = true;
    p.far.on = false;
  }
  function applyLod(p, camPos) {
    if (!p.far) return;
    const d2 = p.g.position.distanceToSquared(camPos);
    const far = p.far.on ? d2 > lod.near * lod.near : d2 > lod.far * lod.far;
    if (far && !p.far.on) toFar(p);
    else if (!far && p.far.on) toNear(p);
    else if (far && p.walk) p.far.fig.move(p.far.slot, farMatrix(p));
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
  /**
   * In a stall's close-up (the camera within 12 m of what it looks at), anyone standing between the camera and
   * the stall inside the picture, even at its edge, steps out, so no half figure is cut by the frame.
   */
  function inCloseUp(pos, from, dir, len) {
    if (len > 12) return false;
    rel.set(pos.x - from.x, 0, pos.z - from.z);
    const d = rel.length();
    if (d > len + 0.8 || d < 0.05) return false;
    const fx = dir.x, fz = dir.z, fl = Math.hypot(fx, fz) || 1;
    const cos = (rel.x * fx + rel.z * fz) / (d * fl);
    return cos > Math.cos((46 * Math.PI) / 180);
  }
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
    get lodLevels() { return crowd.filter((p) => p.far).length; },
    /** Numbers for tests and the debug report. */
    stats() {
      let hidden = 0, far = 0;
      for (const p of crowd) { if (!p.g.visible) hidden++; if (p.far?.on) far++; }
      return {
        people: crowd.length, hidden, lite: far, lodFar: lod.far, vendorsVisible: vendors.filter((v) => v.g.visible).length,
        sharedAnims: shared ? { file: shared.file, clips: shared.clips.length, retargets: shared.byOffset.size } : null,
        // the far crowd: how many are drawn instanced now, by how many instanced meshes (draw calls), and the bake
        far: { ...farStats, drawn: far, meshes: farFigures.size },
        // the skinned people's animation this frame: how many mixers ran, and how many were throttled
        mixers: { ...mixStats },
        updateMs: +updateMs.toFixed(3),
      };
    },
    /** For tests: the people stepped out of the current shot. */
    hiddenIds: () => crowd.filter((p) => !p.g.visible).map((p) => p.g.name),
    /** A stall's vendor steps out of view (on) or back (off). */
    stepOut(stall, on) { if (on) away.add(stall); else away.delete(stall); for (const p of vendors) if (p.plan.stall === stall) p.g.visible = !on; },
    /** For tests: everyone's name, feet position, visibility and whether they are a vendor. */
    people: () => crowd.map((p) => ({ name: p.g.name, pos: p.g.position.toArray(), visible: p.g.visible, vendor: p.vendor, stall: p.plan.stall || null })),
    speak,
    /** Up to five standing people near `center` say `text`, one after another, and raise their mugs if they have one. */
    say(text, center, radius) {
      // the nearest who are in view; when nobody in view stands that close (the close-up has sent the queue out of
      // the shot), the nearest in view a little further off answer instead, so a Prost is never met with silence
      const near = (r) => standing.filter((p) => p.g.visible && p.g.position.distanceTo(center) < r).sort((a, b) => a.g.position.distanceTo(center) - b.g.position.distanceTo(center));
      let who = near(radius);
      if (!who.length) who = near(radius * 2.5).slice(0, 2);
      who.slice(0, 5).forEach((p, i) => setTimeout(() => { speak(p, text); gesture(p, 'drink', 2.6); }, i * 280));
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
      const t0 = performance.now();
      frameNo++;
      if (!still) farTime.value += dt;
      mixStats.ran = 0; mixStats.throttled = 0; mixStats.far = 0;
      for (const p of crowd) {
        // Vendors stay: they are what a close-up looks at. Anyone else on the sight line, or on the line to a
        // vendor in view (the queue at the counter), steps out of the shot.
        const wasVisible = p.g.visible;
        if (look) p.g.visible = p.vendor || !(seg < 20 && (blocks(p.g.position, camera.position, segDir, seg) || blocksVendor(p.g.position, camera.position) || inCloseUp(p.g.position, camera.position, segDir, seg)));
        if (p.vendor && away.size && away.has(p.plan.stall)) p.g.visible = false;
        if (p.far) {
          if (!p.g.visible) { if (p.far.on) { p.far.fig.hide(p.far.slot); p.far.on = false; p.levels[0].root.visible = true; } }
          else applyLod(p, _cp);
          void wasVisible;
        }
        // the skinned figure's clip: every frame near by, every 2nd or 3rd frame further off (the time saved up)
        if (p.lvl.mixer && !still && p.g.visible && !p.far?.on) {
          p.mixDt = (p.mixDt || 0) + dt;
          const d = p.g.position.distanceTo(_cp);
          const every = (THROTTLE.find(([m]) => d > m) || [0, 1])[1];
          if (every === 1 || (frameNo + (p.ph * 7 | 0)) % every === 0) { p.lvl.mixer.update(p.mixDt); p.mixDt = 0; mixStats.ran++; } else mixStats.throttled++;
        } else if (p.far?.on) mixStats.far++;
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
          if (p.far?.on) p.far.fig.move(p.far.slot, farMatrix(p));
          if (!p.lvl.mixer) {
            p.ph += dt * p.speed * 5.2;
            p.g.position.y = Math.abs(Math.cos(p.ph)) * 0.035;
            p.g.rotation.z = Math.sin(p.ph) * 0.03;
          }
        } else if (!p.walk && !still && !p.lvl.mixer) {
          p.g.rotation.z = Math.sin(t * 0.9 + p.ph) * 0.012;
        }
      }
      updateMs = updateMs * 0.9 + (performance.now() - t0) * 0.1;
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
