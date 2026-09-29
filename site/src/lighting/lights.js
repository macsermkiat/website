// Warm real-time lights at light_ empties, within a budget, plus the emissive tuning of bulbs_ and
// window_warm materials. The engine calls placeLights() with the spots it found; lights that miss the
// budget become a soft warm pool on the ground, and every section and deco stall also gets an
// interior glow (shading.js), so a stall never goes dark.
import * as THREE from 'three';
import { kelvinRGB } from './settings.js';

// Section stalls first: the 4-light lite market lights exactly the four section interiors, and the
// full market lights their interiors and front fills before any landmark (the bandstand has its
// bulbs and the engine's two reserved spots; the rides have their bulbs).
const PRIORITY = { section: 0, landmark: 1, tree: 1, deco: 2, lamp: 3, strings: 3, ground: 3, other: 3 };
const STALLS = new Set(['section', 'deco']);

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

/** A spot's position in its model's frame; a point more than 0.9 m in front of the model is a front fill. */
function localOf(s, inv) {
  const holder = holderOf(s.obj);
  holder.updateMatrixWorld(true);
  return { holder, local: s.pos.clone().applyMatrix4(inv.copy(holder.matrixWorld).invert()) };
}

/**
 * spots: [{ obj, kind, id }] (the engine's shape). Adds lights as children of the empties.
 * Returns { lights, pools, cap, interiors, dispose() }; `interiors` are the stall-interior glows
 * (shading.js specs) that createLighting adds.
 */
export function placeWarmLights(scene, spots, N, { lite = false, budget, focus = new THREE.Vector3(), reserved = 0, shadowed = 0 } = {}) {
  const cap = Math.max(0, (budget ?? (lite ? 4 : 14)) - reserved);
  const warm = warmColor(N);
  const frontWarm = warmColor(N, true);
  const U = N.warm.unshadowed;
  const inv = new THREE.Matrix4();
  const all = spots.map((s) => {
    const e = { ...s, pos: s.obj.getWorldPosition(new THREE.Vector3()), lk: lampKind(s) };
    Object.assign(e, localOf(e, inv));
    const K = N.warm[e.lk] || N.warm.other;
    e.front = e.local.z > 0.9 && !!K.front;
    return e;
  });
  // A model's first light is its interior (what makes a stall read warm), its front fill second.
  // Order: priority, then first lights before second ones, then distance to the focus. So on the full
  // market every section stall gets its interior and its front fill before any landmark is lit.
  const byModel = new Map();
  for (const s of all) (byModel.get(s.id) || byModel.set(s.id, []).get(s.id)).push(s);
  for (const list of byModel.values()) {
    list.sort((a, b) => (a.front - b.front) || a.pos.distanceTo(focus) - b.pos.distanceTo(focus));
    list.forEach((s, i) => (s.rank = Math.min(i, 1)));
  }
  const order = all.sort((a, b) => (PRIORITY[a.lk] ?? 3) - (PRIORITY[b.lk] ?? 3) || a.rank - b.rank
    || a.pos.distanceTo(focus) - b.pos.distanceTo(focus));

  const lights = [], pools = [];
  const poolMat = new THREE.MeshBasicMaterial({
    map: poolTexture(), color: warm.clone().multiplyScalar(0.9), transparent: true, opacity: 0.5,
    blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, fog: true,
  });
  const poolGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  let shadows = lite ? 0 : shadowed;
  const blockers = [];
  const lit = new Map(); // model id -> 'lit' (shadowed interior light) | 'unshadowed'

  order.forEach((s, i) => {
    const ud = s.obj.userData || {};
    const K = N.warm[s.lk] || N.warm.other;
    if (i < cap) {
      const { holder, local } = s;
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
        const front = s.front;
        if (front && !ud.color) color.copy(frontWarm);
        if (front && K.frontAngle) {
          // a wide spot aimed down and 0.6 m out: counter front, sign and cobbles, not the fascia
          L = new THREE.SpotLight(color, Number(ud.intensity) || K.front, Number(ud.distance) || K.frontDistance, K.frontAngle, 0.45, 2);
          L.target.position.copy(new THREE.Vector3(local.x, 0, local.z + 0.6).applyMatrix4(holder.matrixWorld));
          scene.add(L.target);
        } else {
          L = new THREE.PointLight(color, Number(ud.intensity) || (front ? K.front : K.point), front && !ud.distance ? K.frontDistance : distance, 2);
        }
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
      // static shadows go to stall interiors (the budget's shadowed slots), or to a light_ asking for one
      if (shadows > 0 && ((interior && STALLS.has(s.lk)) || ud.shadow)) {
        shadows--;
        staticShadow(L, N, type === 'point');
        if (interior) {
          lit.set(s.id, 'lit');
          if (N.warm.blocker) {
            try {
              const b = shadowBlocker(holder, s.pos, N.warm.blocker);
              if (b) blockers.push(b);
            } catch (e) { console.warn('[lighting] shadow blocker failed', e); }
          }
        }
      } else if (interior && U && !ud.distance && STALLS.has(s.lk)) {
        // No shadow: keep the light below the eaves (so it cannot reach the top of the roof) and
        // short, so the leak through the walls stays a small pool at the foot of the stall.
        L.distance = Math.min(L.distance, U.distance);
        L.intensity *= U.scale;
        L.userData.baseIntensity = L.intensity;
        const ws = s.obj.getWorldScale(new THREE.Vector3()).y || 1;
        L.position.y -= U.drop / ws;
        L.userData.unshadowed = true;
        if (!lit.has(s.id)) lit.set(s.id, 'unshadowed');
      }
      if (L.isSpotLight) L.position.set(0, 0, 0);
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

  // an interior glow for every section and deco stall (see settings.js glow.interior)
  const G = N.glow?.interior;
  const interiors = [];
  if (G) {
    for (const [id, list] of byModel) {
      const s = list.find((x) => !x.front) || list[0];
      if (!STALLS.has(s.lk)) continue;
      const how = lit.get(id) || 'only';
      const base = s.holder.getWorldPosition(new THREE.Vector3()).y;
      const a = s.pos.clone();
      a.y -= G.drop;
      interiors.push({
        a, color: warm.clone(), intensity: G[how], reach: G.reach, oneSided: true,
        // clipped below the floor band (no halo on the ground around the walls) and just above the
        // empty (the shingles' lower edges face down toward it; the roof must not glow)
        floor: base + G.floor, ceiling: s.pos.y + G.ceiling, tag: 'interior', priority: 1, id, how,
      });
    }
  }

  return {
    lights, pools, cap, blockers,
    /** Interior glows ({ a, color, intensity, reach, oneSided, floor }), one per stall; createLighting adds them. */
    interiors,
    /** Redraw the static warm-light shadows (after moving a model). */
    refreshShadows() { lights.forEach((l) => { if (l.castShadow) l.shadow.needsUpdate = true; }); },
    dispose() {
      lights.forEach((l) => { l.target?.removeFromParent(); l.removeFromParent(); l.dispose?.(); });
      pools.forEach((p) => p.removeFromParent());
      blockers.forEach((b) => { b.removeFromParent(); b.geometry.dispose(); });
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

// A blocker renders nothing on screen (no colour, no depth) and nothing into the moon's shadow map
// (its depth material puts every vertex outside the clip volume); it only fills point-light shadows.
let blockerMats = null;
function blockerMaterials() {
  if (blockerMats) return blockerMats;
  const main = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, depthTest: false, side: THREE.DoubleSide, fog: false });
  main.name = 'lighting_shadow_blocker';
  const none = new THREE.ShaderMaterial({
    vertexShader: 'void main() { gl_Position = vec4( 2.0, 2.0, 2.0, 1.0 ); }',
    fragmentShader: 'void main() { gl_FragColor = vec4( 0.0 ); discard; }',
  });
  blockerMats = { main, none };
  return blockerMats;
}

/**
 * A shadow-only shell around a stall's interior light: a floor just above the stall's base, and
 * planes just outside the side walls, the back wall and the lower front wall (up to the counter).
 * The walls are found by casting rays at the stall from outside, so the shell sits outside every
 * board and never shadows the interior. It closes the hairline gaps between wall planks and the
 * slot under the walls, which a 512² cube shadow otherwise lets through as sharp streaks and a pale
 * strip on the ground around the stall. Only the point light's shadow sees it.
 */
export function shadowBlocker(holder, lightPos, B = {}) {
  const pad = B.pad ?? 0.012;
  holder.updateMatrixWorld(true);
  const toWorld = holder.matrixWorld, toLocal = new THREE.Matrix4().copy(toWorld).invert();
  const Lw = lightPos.clone(), L = Lw.clone().applyMatrix4(toLocal);
  const q = holder.getWorldQuaternion(new THREE.Quaternion());
  const ws = holder.getWorldScale(new THREE.Vector3()).x || 1;
  const box = new THREE.Box3().setFromObject(holder);
  const far = box.getSize(new THREE.Vector3()).length() / ws + 1;
  const base = 0; // the model's origin is its footprint at ground level
  const rc = new THREE.Raycaster();
  const meshes = [];
  holder.traverse((o) => { if (o.isMesh && !o.isInstancedMesh && o.visible && !/^bulbs_/i.test(o.name)) meshes.push(o); });
  const hit = (oLocal, dLocal) => {
    rc.set(oLocal.clone().applyMatrix4(toWorld), dLocal.clone().applyQuaternion(q).normalize());
    rc.far = far * ws * 2;
    const h = rc.intersectObjects(meshes, false)[0];
    return h ? h.distance / ws : null;
  };
  const top = Math.max(L.y - base, 0.6);
  const heights = (lo, hi) => [0.3, 0.55, 0.8].map((f) => base + lo + (hi - lo) * f);
  // outermost surface along each direction, sampled on a grid of the wall
  const outer = (dir, lateral, hs) => {
    let best = null;
    for (const y of hs) for (const t of [-0.35, 0, 0.35]) {
      const p = new THREE.Vector3(L.x, y, L.z).addScaledVector(lateral, t);
      const d = hit(p.clone().addScaledVector(dir, far), dir.clone().negate());
      if (d == null) continue;
      const along = far - d; // distance of that surface from p, along dir
      if (along > 0.05 && (best == null || along > best)) best = along;
    }
    return best;
  };
  const X = new THREE.Vector3(1, 0, 0), Z = new THREE.Vector3(0, 0, 1);
  const wallH = heights(0.1, Math.min(top, 1.6));
  const right = outer(X, Z, wallH), left = outer(X.clone().negate(), Z, wallH);
  const back = outer(Z.clone().negate(), X, wallH);
  const front = outer(Z, X, heights(0.1, 0.8));
  if (left == null || right == null || back == null) return null; // not a closed stall: no shell
  const x0 = L.x - left - pad, x1 = L.x + right + pad, z0 = L.z - back - pad;
  const z1 = front != null ? L.z + front + pad : L.z + 0.5;
  // the counter: the lowest first surface below the light just inside the front, over a few spots
  // across it (a pot or a mug on the counter must not raise the front plane into the opening)
  let counter = null;
  if (front != null) {
    for (const t of [-0.8, -0.5, -0.2, 0.2, 0.5, 0.8]) {
      const x = L.x + t * (x1 - x0) * 0.5;
      const d = hit(new THREE.Vector3(x, L.y - 0.05, z1 - 0.2), new THREE.Vector3(0, -1, 0));
      if (d == null) continue;
      const y = L.y - 0.05 - d;
      if (y > base + 0.4 && (counter == null || y < counter)) counter = y;
    }
  }
  const yTop = base + top + 0.2, yFloor = base + (B.floor ?? 0.05);
  const quads = [];
  const quad = (a, b, c, d) => quads.push(a, b, c, a, c, d);
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  quad(V(x0, yFloor, z0), V(x1, yFloor, z0), V(x1, yFloor, z1), V(x0, yFloor, z1)); // floor
  quad(V(x0, yFloor, z0), V(x0, yTop, z0), V(x0, yTop, z1), V(x0, yFloor, z1)); // left
  quad(V(x1, yFloor, z0), V(x1, yTop, z0), V(x1, yTop, z1), V(x1, yFloor, z1)); // right
  quad(V(x0, yFloor, z0), V(x1, yFloor, z0), V(x1, yTop, z0), V(x0, yTop, z0)); // back
  if (counter != null && counter > base + 0.4) {
    const yc = counter - 0.03;
    quad(V(x0, yFloor, z1), V(x1, yFloor, z1), V(x1, yc, z1), V(x0, yc, z1)); // lower front
  }
  const g = new THREE.BufferGeometry().setFromPoints(quads.flatMap((v) => [v]));
  g.computeVertexNormals();
  const M = blockerMaterials();
  const m = new THREE.Mesh(g, M.main);
  m.name = 'lighting_shadow_blocker';
  m.castShadow = true;
  m.receiveShadow = false;
  m.customDepthMaterial = M.none; // not in the moon's (or any spot light's) shadow
  m.raycast = () => {};
  m.renderOrder = -10;
  m.frustumCulled = false;
  m.userData.shadowOnly = true;
  m.userData.shell = { x0, x1, z0, z1, counter, yTop };
  holder.add(m); // in the holder's frame, so it moves with the stall (open at the top and above the counter)
  return m;
}

/** Give a warm light a static shadow (drawn once; call refreshShadows after moving things). */
function staticShadow(L, N, point) {
  const S = N.warm.shadowMap || { size: 512, radius: 2.5, bias: -0.002, normalBias: 0.02 };
  L.castShadow = true;
  L.shadow.mapSize.set(point ? S.size : S.size * 2, point ? S.size : S.size * 2);
  L.shadow.bias = S.bias;
  L.shadow.normalBias = S.normalBias;
  L.shadow.radius = point ? S.radius : 2.5;
  L.shadow.intensity = point ? N.warm.interiorShadow : 1;
  L.shadow.camera.near = S.near ?? 0.15;
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
