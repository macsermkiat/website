// Warm real-time lights at light_ empties, within a budget, plus the emissive tuning of bulbs_ and
// window_warm materials. The engine calls placeLights() with the spots it found; lights that miss the
// budget become a soft warm pool on the ground so a stall never goes dark.
import * as THREE from 'three';
import { kelvinRGB } from './settings.js';

const PRIORITY = { section: 0, landmark: 0, tree: 1, deco: 2, lamp: 3, strings: 3, ground: 3, other: 3 };

let poolTex = null;
function poolTexture() {
  if (poolTex) return poolTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,0.55)');
  gr.addColorStop(0.35, 'rgba(255,255,255,0.22)');
  gr.addColorStop(0.7, 'rgba(255,255,255,0.05)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  poolTex = new THREE.CanvasTexture(c);
  poolTex.colorSpace = THREE.SRGBColorSpace;
  return poolTex;
}

/** The top-level holder of a placed model: the ancestor right under the scene. */
function holderOf(obj) {
  let o = obj;
  while (o.parent && !o.parent.isScene) o = o.parent;
  return o;
}

/** A light_ empty's kind of lamp, from its name or the kind the engine gave its model. */
function lampKind(spot) {
  const n = spot.obj.name.toLowerCase();
  if (/^light_lamp/.test(n)) return 'lamp';
  if (/^light_tree/.test(n)) return 'tree';
  if (/^light_string/.test(n)) return 'strings';
  return spot.kind in PRIORITY ? spot.kind : 'other';
}

/**
 * Spot or point? userData.type wins ('spot' | 'point'), then a name containing "spot". Otherwise
 * points: inside a stall a point lights walls, shelves and counter; under the front eave it is the
 * front fill that lights the garland, the counter front, the sign and the cobbles (as the Cycles
 * previews do). High light_ empties on a landmark become downward stage spots.
 */
function lampType(spot, kind, local) {
  const t = String(spot.obj.userData?.type || spot.obj.userData?.light || '').toLowerCase();
  if (t === 'spot' || t === 'point') return t;
  if (/spot/i.test(spot.obj.name)) return 'spot';
  // stage lights high on a landmark (the bandstand roof) point straight down
  if (kind === 'landmark' && local && local.y > 2.8) return 'spot';
  return 'point';
}

/**
 * spots: [{ obj, kind, id }] (the engine's shape). Adds lights as children of the empties.
 * Returns { lights, pools, cap, dispose() }.
 */
export function placeWarmLights(scene, spots, N, { lite = false, budget, focus = new THREE.Vector3(), reserved = 0, shadowed = 0 } = {}) {
  const cap = Math.max(0, (budget ?? (lite ? 4 : 14)) - reserved);
  const warm = warmColor(N);
  const frontWarm = warmColor(N, true);
  const U = N.warm.unshadowed;
  const bounces = [];
  const ranked = spots
    .map((s) => ({ ...s, pos: s.obj.getWorldPosition(new THREE.Vector3()), lk: lampKind(s) }))
    .sort((a, b) => (PRIORITY[a.lk] ?? 3) - (PRIORITY[b.lk] ?? 3) || a.pos.distanceTo(focus) - b.pos.distanceTo(focus));
  // one light per model until every model has one, then second lights
  const firsts = [], seconds = [], seen = new Set();
  for (const s of ranked) (seen.has(s.id) ? seconds : firsts).push(s), seen.add(s.id);
  const order = [...firsts, ...seconds];

  const lights = [], pools = [];
  const poolMat = new THREE.MeshBasicMaterial({
    map: poolTexture(), color: warm.clone().multiplyScalar(0.9), transparent: true, opacity: 0.5,
    blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, fog: true,
  });
  const poolGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const inv = new THREE.Matrix4();
  let shadows = lite ? 0 : shadowed;

  order.forEach((s, i) => {
    const ud = s.obj.userData || {};
    const K = N.warm[s.lk] || N.warm.other;
    if (i < cap) {
      const holder = holderOf(s.obj);
      holder.updateMatrixWorld(true);
      const local = s.pos.clone().applyMatrix4(inv.copy(holder.matrixWorld).invert());
      const type = lampType(s, s.lk, local);
      const color = ud.color ? new THREE.Color(ud.color) : warm.clone();
      let distance = Number(ud.distance) || (type === 'spot' ? K.spotDistance : K.pointDistance);
      let L;
      if (type === 'spot') {
        L = new THREE.SpotLight(color, Number(ud.intensity) || K.spot, distance, 0.95, 0.6, 2);
        // aim straight down, or at userData.aim ([x, y, z] in the model's frame)
        const a = Array.isArray(ud.aim) ? ud.aim : [local.x, 0, local.z];
        const aim = new THREE.Vector3(...a).applyMatrix4(holder.matrixWorld);
        L.target.position.copy(aim);
        scene.add(L.target);
      } else {
        // a point outside the model's front (under the eave) is the front fill: softer, longer reach
        const front = local.z > 0.9 && K.front;
        if (front && !ud.color) color.copy(frontWarm);
        L = new THREE.PointLight(color, Number(ud.intensity) || (front ? K.front : K.point), front && !ud.distance ? K.frontDistance : distance, 2);
        if (front) L.userData.front = true;
      }
      L.name = `lighting_${s.obj.name}`;
      L.userData.lightingKind = s.lk;
      L.userData.baseIntensity = L.intensity;
      // Interior point lights of the highest-priority models get a shadow so they stop at the
      // walls. Stalls do not move, so the map is drawn once (autoUpdate off): nearly free per frame.
      // The shadow is nearly opaque; the light the walls bounce back comes from a dim, unshadowed,
      // short-reach glow at the same spot (see shading.js), not from a see-through shadow.
      const interior = type === 'point' && !L.userData.front;
      s.obj.add(L);
      if (shadows > 0 && (interior || ud.shadow)) {
        shadows--;
        staticShadow(L, N, type === 'point');
        if (interior && N.warm.bounce) {
          bounces.push({ a: s.pos.clone(), color: color.clone(), intensity: N.warm.bounce.intensity * (L.intensity / (K.point || 40)), reach: N.warm.bounce.reach, tag: 'bounce', priority: 1 });
        }
      } else if (interior && U && !ud.distance && (s.lk === 'section' || s.lk === 'deco')) {
        // No shadow: keep the light below the eaves (so it cannot reach the top of the roof) and
        // short, so the leak through the walls stays a small pool at the foot of the stall.
        L.distance = Math.min(L.distance, U.distance);
        L.intensity *= U.scale;
        L.userData.baseIntensity = L.intensity;
        const ws = s.obj.getWorldScale(new THREE.Vector3()).y || 1;
        L.position.y -= U.drop / ws;
        L.userData.unshadowed = true;
      }
      if (type === 'spot') L.position.set(0, 0, 0);
      lights.push(L);
    } else {
      const m = new THREE.Mesh(poolGeo, poolMat);
      m.name = `pool_${s.obj.name}`;
      const size = Math.min(8, 2.5 + s.pos.y * 1.3);
      m.scale.set(size, 1, size);
      m.position.set(s.pos.x, 0.03, s.pos.z);
      m.renderOrder = 2;
      m.raycast = () => {};
      scene.add(m);
      pools.push(m);
    }
  });

  return {
    lights, pools, cap,
    /** Dim bounce-light glows for the shadowed interiors ({ a, color, intensity, reach }); createLighting adds them. */
    bounces,
    /** Redraw the static warm-light shadows (after moving a model). */
    refreshShadows() { lights.forEach((l) => { if (l.castShadow) l.shadow.needsUpdate = true; }); },
    dispose() {
      lights.forEach((l) => { l.target?.removeFromParent(); l.removeFromParent(); l.dispose?.(); });
      pools.forEach((p) => p.removeFromParent());
      poolGeo.dispose();
      poolMat.dispose();
    },
  };
}

/** The warm-light colour (linear), or the paler front-fill colour. */
export function warmColor(N, front = false) {
  const c = front ? N.warm.frontColor : N.warm.color;
  if (Array.isArray(c)) return new THREE.Color().setRGB(...c); // linear, like Blender's light colour
  return new THREE.Color().setRGB(...kelvinRGB(N.warm.kelvin), THREE.SRGBColorSpace);
}

/** Give a warm light a static shadow (drawn once; call refreshShadows after moving things). */
function staticShadow(L, N, point) {
  L.castShadow = true;
  L.shadow.mapSize.set(point ? 512 : 1024, point ? 512 : 1024);
  L.shadow.bias = -0.002;
  L.shadow.normalBias = 0.02;
  L.shadow.radius = 2.5;
  L.shadow.intensity = point ? N.warm.interiorShadow : 1;
  L.shadow.camera.near = 0.05;
  L.shadow.autoUpdate = false;
  L.shadow.needsUpdate = true;
}

/**
 * LEGACY (off by default since main.js calls placeLights; pass options.adoptEngineLights = true).
 * The engine's own light_ lights (engine/lights.js places them before the lighting exists) re-tuned
 * to this module's values: colour temperature, interior vs front-fill intensity and reach, and static
 * shadows on the interior lights of the `shadowed` section stalls nearest `focus`.
 */
export function adoptEngineLights(scene, N, { shadowed = 0, focus = null } = {}) {
  const warm = warmColor(N);
  const out = [];
  const inv = new THREE.Matrix4(), p = new THREE.Vector3();
  scene.traverse((o) => {
    if (!o.isPointLight || !/^engine_light_/i.test(o.name)) return;
    const n = o.name.replace(/^engine_/i, '').toLowerCase();
    const empty = o.parent;
    const holder = empty ? holderOf(empty) : null;
    const entryKind = holder?.userData?.entry?.kind || holder?.userData?.kind;
    const kind = /^light_lamp/.test(n) ? 'lamp' : /^light_tree/.test(n) ? 'tree' : /^light_string/.test(n) ? 'strings'
      : entryKind in N.warm ? entryKind : (o.intensity < 10 ? 'deco' : 'section');
    const K = N.warm[kind] || N.warm.other;
    const ud = empty?.userData || {};
    let front = false;
    if (holder) {
      holder.updateMatrixWorld(true);
      o.getWorldPosition(p).applyMatrix4(inv.copy(holder.matrixWorld).invert());
      front = p.z > 0.9 && !!K.front;
    }
    if (!ud.color) o.color.copy(warm);
    o.intensity = Number(ud.intensity) || (front ? K.front : K.point);
    o.distance = Number(ud.distance) || (front ? K.frontDistance : K.pointDistance);
    o.decay = 2;
    o.userData.baseIntensity = o.intensity;
    o.userData.lightingKind = kind;
    o.userData.front = front;
    out.push(o);
  });
  if (shadowed > 0) {
    const f = focus || new THREE.Vector3();
    out.filter((o) => (o.userData.lightingKind === 'section' || o.userData.lightingKind === 'landmark') && !o.userData.front)
      .sort((a, b) => a.getWorldPosition(p).distanceToSquared(f) - b.getWorldPosition(new THREE.Vector3()).distanceToSquared(f))
      .slice(0, shadowed)
      .forEach((o) => staticShadow(o, N, true));
  }
  return out;
}

const isBulbMat = (m) => /^bulb_(warm|cold)/i.test(m?.name || '') || m?.userData?.bulb;
const isWindowMat = (m) => /^window_warm/i.test(m?.name || '');

/**
 * Bulbs and lit windows get this module's emissive levels (the engine animates around
 * userData.baseEmissive, so that is set too). Works on anything under `root`, so late-loaded
 * models can be tuned with lighting.tune(root). Returns { bulbs, windows } material sets.
 */
export function tuneEmissives(root, N, { lite = false } = {}) {
  const bulbs = new Set(), windows = new Set();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const inBulbs = /^bulbs_/i.test(o.name) || /^bulbs_/i.test(o.parent?.name || '');
    for (const m of mats) {
      if (!m) continue;
      if (isBulbMat(m) || (inBulbs && m.emissive)) {
        const cold = /cold/i.test(m.name) || m.userData?.bulb === 'cold';
        const E = cold ? N.emissive.cold : N.emissive.warm;
        if (m.emissive) {
          if (!m.emissiveMap) m.emissive.setRGB(...E.color);
          const v = E.intensity * (lite ? 0.85 : 1);
          m.emissiveIntensity = v;
          m.userData.baseEmissive = v;
        }
        bulbs.add(m);
        o.castShadow = false;
      } else if (isWindowMat(m)) {
        if (m.emissive) {
          if (!m.emissiveMap && m.emissive.getHex() === 0) m.emissive.setRGB(1.0, 0.62, 0.3);
          m.emissiveIntensity = N.emissive.window;
          m.userData.baseEmissive = N.emissive.window;
        }
        windows.add(m);
      }
    }
  });
  return { bulbs, windows };
}
