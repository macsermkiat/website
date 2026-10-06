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
  // round 2: a light_ very high on a landmark (the Ferris wheel's hub, 14.7 m) is a wash, not a stage spot
  if (kind === 'landmark' && local && K_WASH.height && local.y > K_WASH.height) return 'point';
  // stage lights high on a landmark (the bandstand roof) point straight down
  if (kind === 'landmark' && local && local.y > 2.8) return 'spot';
  return 'point';
}

// round 2: a landmark's light_ above `washHeight` (the Ferris wheel's hub light) is a wide point wash
// (warm.landmark.wash / washDistance) that lights the steel round it, as in the Cycles preview
const K_WASH = { height: 8 };
function isWash(s, K) {
  if (s.lk !== 'landmark' || !s.local || !K.wash) return false;
  K_WASH.height = K.washHeight ?? 8;
  return s.local.y > K_WASH.height;
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
    e.wash = isWash(e, K);
    return e;
  });
  // A model's first light is its interior (what makes a stall read warm), its front fill second.
  // Order: priority, then first lights before second ones, then distance to the focus. So on the full
  // market every section stall gets its interior and its front fill before any landmark is lit.
  const byModel = new Map();
  for (const s of all) (byModel.get(s.id) || byModel.set(s.id, []).get(s.id)).push(s);
  for (const list of byModel.values()) {
    // a landmark's high wash (the Ferris wheel's hub light) comes first: it is what makes it read
    list.sort((a, b) => (b.wash - a.wash) || (a.front - b.front) || a.pos.distanceTo(focus) - b.pos.distanceTo(focus));
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
  const clips = []; // interior clip boxes of unshadowed interior lights (shading.js addClip)
  const lit = new Map(); // model id -> 'lit' (shadowed interior light) | 'unshadowed'

  let L0offset = null;
  // at most `perModel` real lights per model (BUILD.md: 2 per section stall). A third light_ in a stall,
  // such as the reading lamp on the Bücherstand's counter prop, becomes a small local glow instead
  // (no three.js light, no ground pool): Codex round 1 counted three markers there.
  const perModel = new Map();
  const extras = [];
  let used = 0;
  order.forEach((s) => {
    const ud = s.obj.userData || {};
    const K = N.warm[s.lk] || N.warm.other;
    const n = perModel.get(s.id) || 0;
    if (n >= (N.warm.perModel ?? 2) && STALLS.has(s.kind)) { extras.push(s); return; }
    // a prop's lamp in a stall that the budget cannot light: a small glow, not a pool on the ground
    if (used >= cap && s.lk === 'lamp' && STALLS.has(s.kind)) { extras.push(s); return; }
    if (used < cap) {
      used++;
      perModel.set(s.id, n + 1);
      const { holder, local } = s;
      const type = lampType(s, s.lk, local);
      const color = ud.color ? new THREE.Color(ud.color) : warm.clone();
      let distance = Number(ud.distance) || (s.wash ? K.washDistance : type === 'spot' ? K.spotDistance : K.pointDistance);
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
          // placed `frontLift` m above and `frontOut` m in front of the empty: from further out the pool
          // reaches the cobbles beside the stall while the sign and counter under the eave get less
          // (Cycles: the preview's front light hangs 1.9 m out, near eave height)
          const lift = K.frontLift ?? 0, out = K.frontOut ?? 0;
          if (lift || out) L0offset = new THREE.Vector3(0, lift, out).applyQuaternion(holder.getWorldQuaternion(new THREE.Quaternion()));
          // a wide spot aimed down and `frontAim` m out: counter front, sign and cobbles, not the fascia
          L = new THREE.SpotLight(color, Number(ud.intensity) || K.front, Number(ud.distance) || K.frontDistance, K.frontAngle, K.frontPenumbra ?? 0.45, 2);
          L.target.position.copy(new THREE.Vector3(local.x, 0, local.z + (K.frontAim ?? 0.6)).applyMatrix4(holder.matrixWorld));
          scene.add(L.target);
        } else {
          L = new THREE.PointLight(color, Number(ud.intensity) || (s.wash ? K.wash : front ? K.front : K.point), front && !ud.distance ? K.frontDistance : distance, 2);
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
        // No shadow (the lite market): the light is clipped to the stall's interior box (shading.js),
        // so it cannot reach the barge boards, the eave, the plank edges in the wall gaps or the
        // ground. It keeps a short reach and a lower intensity: without the shelves' shadows the back
        // wall would wash out, and the one-sided interior glow carries the rest of the warmth.
        L.distance = Math.min(L.distance, U.distance);
        L.intensity *= U.scale;
        L.userData.baseIntensity = L.intensity;
        L.userData.unshadowed = true;
        let box = null;
        if (U.clip) {
          try { box = interiorBox(s.holder, s.pos, U.clip); } catch (e) { console.warn('[lighting] interior clip failed', e); }
        }
        if (box) {
          clips.push({ light: L, ...box });
          L.userData.clipped = true;
        } else {
          // no closed stall to clip to: keep the light below the eaves, so the leak stays at its foot
          const ws = s.obj.getWorldScale(new THREE.Vector3()).y || 1;
          L.position.y -= U.drop / ws;
        }
        if (!lit.has(s.id)) lit.set(s.id, 'unshadowed');
      }
      if (L.isSpotLight) L.position.set(0, 0, 0);
      // round 2, pass 3: the wash hangs a further `washOut` m out along the model's +Z, so the steel
      // round the hub is not many times brighter than the rim (it bloomed into a white star)
      if (s.wash && K.washOut && !L0offset) L0offset = new THREE.Vector3(0, 0, K.washOut).applyQuaternion(holder.getWorldQuaternion(new THREE.Quaternion()));
      if (L0offset) {
        // the offset is in world axes; the light is a child of the empty
        const w = s.obj.getWorldPosition(new THREE.Vector3()).add(L0offset);
        L.position.copy(s.obj.worldToLocal(w));
        L0offset = null;
      }
      L.userData.spot = s;
      s.light = L;
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
      s.pool = m;
    }
  });

  // an interior glow for every section and deco stall (see settings.js glow.interior)
  const G = N.glow?.interior;
  const interiors = [];
  const X = N.glow?.lamp;
  if (X) {
    for (const s of extras) {
      interiors.push({ a: s.pos.clone(), color: warm.clone(), intensity: X.intensity, reach: X.reach, tag: 'lamp', priority: 0, id: s.id, how: 'lamp' });
    }
  }
  if (G) {
    for (const [id, list] of byModel) {
      // the stall's own interior light_ (not a prop's lamp, whose kind is 'lamp')
      const s = list.find((x) => !x.front && x.lk === x.kind) || list.find((x) => !x.front) || list[0];
      if (!STALLS.has(s.kind)) continue;
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

  // a one-sided glow at each stall's front fill, clipped below the eave: it lights what faces it
  // above the eave line (the front of the roof, or the soffit where the lamp hangs under the eave),
  // which the downward front-fill spot cannot reach (Cycles: the light_ marker's point light)
  // and a ground-only glow at the front fill (the cobbles in front of and beside the stall; clipped
  // above `ceiling` m, so the walls, the sign and the counter do not get it): the warm pool that
  // Cycles' omnidirectional light_ marker spreads around the stall, which the front-fill spot, aimed
  // down at the front, cannot reach without lighting the sign and the lower front wall as well
  // each stall's sign board (found once; used by the sign lamps below and to keep the roof glow off it)
  const SG = N.glow?.sign;
  const signRects = new Map();
  if (SG) {
    for (const [id, list] of byModel) {
      const s = list[0];
      if (!STALLS.has(s.kind)) continue;
      const slot = findNode(s.holder, /^slot_sign/i);
      if (!slot) continue;
      try { const r = signRect(s.holder, slot, SG); if (r) signRects.set(id, r); } catch (e) { console.warn('[lighting] sign rect failed', e); }
    }
  }
  const E = N.glow?.eave, SP = N.glow?.spill;
  if (E || SP) {
    for (const [id, list] of byModel) {
      const s = list.find((x) => x.front && x.lk === x.kind);
      if (!s || !STALLS.has(s.kind)) continue;
      const out = new THREE.Vector3(0, 0, 1).transformDirection(s.holder.matrixWorld).setY(0).normalize();
      if (E) {
        const a = s.pos.clone().addScaledVector(out, E.out);
        a.y += E.up;
        // a sign board on the fascia, right in front of this glow, would take most of it and wash out
        // (round 1: the Glühwein board at 240/255 with pale pink letters): start the glow over its top
        let floor = s.pos.y - E.below;
        const sr = signRects.get(id);
        if (sr) {
          const top = sr.center.y + sr.height / 2;
          if (top > floor && sr.center.distanceTo(a) < E.reach) floor = top + 0.03;
        }
        interiors.push({
          a, color: frontWarm.clone(), intensity: E.intensity, reach: E.reach, oneSided: true,
          floor, tag: 'eave', priority: 0, id, how: 'eave',
        });
      }
      if (SP) {
        const a = s.pos.clone().addScaledVector(out, SP.out);
        a.y += SP.up;
        const base = s.holder.getWorldPosition(new THREE.Vector3()).y;
        interiors.push({
          a, color: frontWarm.clone(), intensity: SP.intensity, reach: SP.reach, oneSided: true,
          ceiling: base + SP.ceiling, tag: 'spill', priority: 0, id, how: 'spill',
        });
      }
    }
  }

  // a sign lamp for every stall with a slot_sign: a short bar lamp on two arms just above the board,
  // with a one-sided line glow along it (shading.js) clipped to the board's height band, so the
  // painted letters read from the square and close up (settings.js glow.sign). The glow is not a
  // three.js light, so the lite market's four real lights are untouched. The fixtures are added here
  // (world space; `fixtures`), one merged mesh per stall.
  const fixtures = [], signs = [];
  if (SG) {
    for (const [id, list] of byModel) {
      const s = list[0];
      const rect = signRects.get(id);
      if (!rect) continue;
      const section = s.kind === 'section';
      const color = new THREE.Color().setRGB(...(SG.color || N.warm.frontColor));
      // the lamp: `out` m in front of the board's face, `up` m over its top edge; the glow runs along
      // the lamp's bar (a line light the width of the lamp)
      const half = Math.min(rect.width * 0.5 * SG.span, SG.maxHalf ?? 0.9);
      const lamp = rect.center.clone().addScaledVector(rect.normal, SG.out).addScaledVector(rect.up, rect.height / 2 + SG.up);
      const a = lamp.clone().addScaledVector(rect.right, -half), b = lamp.clone().addScaledVector(rect.right, half);
      const g = {
        a, b, color, intensity: SG.intensity * (section ? 1 : SG.decoScale ?? 0.6), reach: SG.reach, oneSided: true,
        floor: rect.center.y - rect.height / 2 - SG.below, ceiling: lamp.y - 0.02,
        tag: 'sign', priority: section ? 1 : 0, id, how: 'sign',
      };
      interiors.push(g);
      signs.push({ id, rect, lamp, half });
      if (SG.fixture) fixtures.push(signFixture(rect, lamp, half, SG, color));
    }
    // one mesh for all the lamps of this placement (two draw calls, not two per stall)
    if (fixtures.length > 1) {
      const parts = fixtures.map((m) => { m.updateMatrix(); return m.geometry.applyMatrix4(m.matrix); });
      const mats = fixtures[0].material;
      const one = new THREE.Mesh(mergeGeos(mats.map((_, i) => mergeGeos(parts.map((g) => sub(g, i)))), true), mats);
      Object.assign(one, { name: 'lighting_sign_lamps', castShadow: false, receiveShadow: false, raycast: () => {} });
      one.userData.lightingFixture = true;
      parts.forEach((g) => g.dispose());
      fixtures.length = 0;
      fixtures.push(one);
    }
  }

  // cam_view / cam_target of each model, for finding the place the visitor has entered (index.js)
  const views = [];
  for (const [id, list] of byModel) {
    const h = list[0].holder;
    const v = findNode(h, /^cam_view/i), t = findNode(h, /^cam_target/i);
    if (v) views.push({ id, holder: h, kind: list[0].lk, view: v, target: t });
  }

  return {
    lights, pools, cap, blockers, fixtures, signs, views,
    /** Every light_ spot, with its model (`holder`), kind (`lk`), `front`, and `light` when it has one. */
    spots: all,
    /** Clip boxes for the unshadowed interior lights ({ light, center, half, cos, sin, fade, front, cut }). */
    clips,
    /** Interior glows ({ a, color, intensity, reach, oneSided, floor }), one per stall; createLighting adds them. */
    interiors,
    /** Redraw the static warm-light shadows (after moving a model). */
    refreshShadows() { lights.forEach((l) => { if (l.castShadow) l.shadow.needsUpdate = true; }); },
    dispose() {
      lights.forEach((l) => { l.target?.removeFromParent(); l.removeFromParent(); l.dispose?.(); });
      pools.forEach((p) => p.removeFromParent());
      fixtures.forEach((f) => { f.removeFromParent(); f.geometry.dispose(); });
      blockers.forEach((b) => { b.removeFromParent(); b.geometry.dispose(); });
      poolGeo.dispose();
      poolMat.dispose();
    },
  };
}

/**
 * Move an unshadowed warm light to another light_ spot (the place the visitor has entered, or back
 * home): reparent it to the spot's empty and give it that spot's colour, intensity, reach and aim.
 * The number of point and spot lights in the scene stays the same, so no material recompiles. A point
 * light serving a front spot hangs where the front fill would, at `pointFront` of the front strength.
 * Returns { target, clip }: the intensity to fade up to, and a clip box when it becomes an unshadowed
 * stall interior (null otherwise).
 */
export function retargetLight(L, s, N, { lite = false } = {}) {
  const K = N.warm[s.lk] || N.warm.other;
  const U = N.warm.unshadowed;
  const ud = s.obj.userData || {};
  const color = ud.color ? new THREE.Color(ud.color) : warmColor(N, s.front);
  L.color.copy(color);
  s.obj.add(L);
  L.position.set(0, 0, 0);
  s.holder.updateMatrixWorld(true);
  let target = 0, clip = null;
  if (s.front) {
    const lift = K.frontLift ?? 0, outM = K.frontOut ?? 0;
    const off = new THREE.Vector3(0, lift, outM).applyQuaternion(s.holder.getWorldQuaternion(new THREE.Quaternion()));
    L.position.copy(s.obj.worldToLocal(s.obj.getWorldPosition(new THREE.Vector3()).add(off)));
    L.distance = Number(ud.distance) || K.frontDistance || K.pointDistance;
    if (L.isSpotLight) {
      L.angle = K.frontAngle ?? 0.95; L.penumbra = K.frontPenumbra ?? 0.45;
      L.target.position.copy(new THREE.Vector3(s.local.x, 0, s.local.z + (K.frontAim ?? 0.6)).applyMatrix4(s.holder.matrixWorld));
      target = Number(ud.intensity) || K.front;
    } else target = (Number(ud.intensity) || K.front || K.point) * (N.warm.pointFront ?? 0.7);
  } else {
    const type = lampType(s, s.lk, s.local);
    if (L.isSpotLight) {
      L.angle = 0.95; L.penumbra = 0.6;
      const a = Array.isArray(ud.aim) ? ud.aim : [s.local.x, 0, s.local.z];
      L.target.position.copy(new THREE.Vector3(...a).applyMatrix4(s.holder.matrixWorld));
      L.distance = Number(ud.distance) || K.spotDistance;
      target = Number(ud.intensity) || (type === 'spot' ? K.spot : K.point);
    } else if (isWash(s, K)) {
      if (K.washOut) {
        const off = new THREE.Vector3(0, 0, K.washOut).applyQuaternion(s.holder.getWorldQuaternion(new THREE.Quaternion()));
        L.position.copy(s.obj.worldToLocal(s.obj.getWorldPosition(new THREE.Vector3()).add(off)));
      }
      L.distance = Number(ud.distance) || K.washDistance;
      target = Number(ud.intensity) || K.wash;
    } else {
      L.distance = Number(ud.distance) || K.pointDistance;
      target = Number(ud.intensity) || K.point;
      if (STALLS.has(s.lk) && U && !ud.distance) {
        L.distance = Math.min(L.distance, U.distance);
        target *= U.scale;
        if (U.clip) {
          try { const box = interiorBox(s.holder, s.pos, U.clip); if (box) clip = { light: L, ...box }; } catch (e) { console.warn('[lighting] interior clip failed', e); }
        }
        if (!clip) L.position.y -= U.drop / (s.obj.getWorldScale(new THREE.Vector3()).y || 1);
      }
    }
  }
  L.target?.updateMatrixWorld?.();
  L.userData.spot = s;
  L.userData.baseIntensity = target;
  L.userData.front = !!s.front;
  L.name = `lighting_${s.obj.name}`;
  return { target, clip };
}

/** The first node under `root` whose name matches `re`. */
function findNode(root, re) {
  let hit = null;
  root.traverse((o) => { if (!hit && re.test(o.name || '')) hit = o; });
  return hit;
}

/**
 * The painted board at a slot_sign empty, found by casting rays at it from in front (the stall's +Z):
 * the surface the empty sits on, and how far it runs to either side and up and down at about the same
 * depth. Returns { center, normal (out of the board), right, up, width, height } in world space, or a
 * default 1.2 x 0.35 m board at the empty when nothing is hit.
 */
export function signRect(holder, slot, SG = {}) {
  holder.updateMatrixWorld(true);
  const P = slot.getWorldPosition(new THREE.Vector3());
  const q = holder.getWorldQuaternion(new THREE.Quaternion());
  const out = new THREE.Vector3(0, 0, 1).applyQuaternion(q).setY(0).normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const right = new THREE.Vector3().crossVectors(up, out).normalize();
  const meshes = [];
  holder.traverse((o) => { if (o.isMesh && o.visible && !o.userData.shadowOnly && !/^bulbs_/i.test(o.name)) meshes.push(o); });
  const rc = new THREE.Raycaster();
  const back = out.clone().negate();
  const depth = (du, dv) => {
    rc.set(P.clone().addScaledVector(right, du).addScaledVector(up, dv).addScaledVector(out, 1.2), back);
    rc.far = 2.0;
    const h = rc.intersectObjects(meshes, false)[0];
    return h ? h.distance : null;
  };
  // the board's own depth near the empty: of a few samples, the deepest within 3 cm of the nearest
  // (raised letters stand 1-2 cm proud of the board; the wall behind it is further back than that)
  const near = [[0, 0], [0.06, 0], [-0.06, 0], [0.12, 0], [-0.12, 0], [0, 0.04], [0, -0.04]].map(([u, v]) => depth(u, v)).filter((d) => d != null);
  const dmin = near.length ? Math.min(...near) : null;
  const d0 = dmin == null ? null : Math.max(...near.filter((d) => d < dmin + 0.03));
  const fallback = { center: P.clone(), normal: out, right, up, width: SG.defaultWidth ?? 1.2, height: SG.defaultHeight ?? 0.35 };
  if (d0 == null || d0 > 1.6) return fallback;
  // walk out in small steps until the surface steps back: the board's edge is a step back in depth
  // (its thickness, or the gap to the wall behind it). A surface at the same depth (within `depthTol`
  // of the last, so a slightly tilted board is followed) moves the reference; anything proud of the
  // board (raised letters, a frame) is walked over.
  const tol = SG.depthTol ?? 0.008;
  const extent = (fn, step, max) => {
    let t = 0, last = d0;
    while (t + step <= max) {
      const d = fn(t + step);
      if (d == null || d > last + tol) break;
      if (d >= last - tol) last = d;
      t += step;
    }
    return t;
  };
  const r = extent((t) => depth(t, 0), 0.02, 1.6), l = extent((t) => depth(-t, 0), 0.02, 1.6);
  const cu = (r - l) / 2; // the board's middle across
  const u = extent((t) => depth(cu, t), 0.015, 0.8), dn = extent((t) => depth(cu, -t), 0.015, 0.8);
  const width = Math.max(0.3, r + l + 0.04), height = Math.max(0.15, u + dn + 0.02);
  const center = P.clone().addScaledVector(out, 1.2 - d0).addScaledVector(right, cu).addScaledVector(up, (u - dn) / 2);
  return { center, normal: out, right, up, width, height };
}

let fixtureMats = null;
/**
 * The sign lamp's fixture: a dark iron bar on two arms, with a warm lit strip under it (it blooms a
 * little, so the light on the board has a source). One mesh, two materials.
 */
function signFixture(rect, lamp, half, SG, color) {
  if (!fixtureMats) {
    // dark bronze outside (darker than the board, with a soft sheen), a warm reflector inside
    // and the lit tube, which blooms a little
    const iron = new THREE.MeshStandardMaterial({ color: 0x3a3226, metalness: 0.6, roughness: 0.42, side: THREE.DoubleSide });
    iron.name = 'lighting_sign_lamp_iron';
    const warm = new THREE.Color().setRGB(1, 0.72, 0.42);
    const lit = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: warm, emissiveIntensity: SG.fixtureEmissive ?? 2.2 });
    lit.name = 'lighting_sign_lamp_glow';
    const refl = new THREE.MeshStandardMaterial({ color: 0x2a2018, metalness: 0.2, roughness: 0.5, emissive: warm, emissiveIntensity: SG.reflectorEmissive ?? 0.35 });
    refl.name = 'lighting_sign_lamp_reflector';
    fixtureMats = [iron, lit, refl];
  }
  // round 2: a picture-light hood (round 1 had a flat 2.4 cm bar that read as a black line). Lamp-local
  // frame: x along the board, y up, z out of the board toward the visitor; the tube sits at the origin.
  // The hood's profile is an arc of radius r over the tube, from just behind the top round to a lip in
  // front and below it, so it opens back and down onto the board.
  const W = half + 0.015, r = SG.hoodRadius ?? 0.045, N = 8;
  const a0 = (105 * Math.PI) / 180, a1 = (-35 * Math.PI) / 180;
  const arc = (rad) => Array.from({ length: N + 1 }, (_, i) => { const t = a0 + ((a1 - a0) * i) / N; return [Math.cos(t), Math.sin(t), rad]; });
  const sheet = (rad, inward) => {
    const pos = [], nor = [];
    const pts = arc(rad);
    for (let i = 0; i < N; i++) {
      const [c0, s0] = pts[i], [c1, s1] = pts[i + 1];
      const q = [[-W, c0, s0], [W, c0, s0], [W, c1, s1], [-W, c1, s1]];
      const order = inward ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
      for (const k of order) {
        const [x, c, sn] = q[k];
        pos.push(x, sn * rad, c * rad);
        nor.push(0, inward ? -sn : sn, inward ? -c : c);
      }
    }
    return geo(pos, nor);
  };
  const caps = () => {
    // end plates closing the hood's two ends (a fan from the tube's axis)
    const pos = [], nor = [];
    const pts = arc(r);
    for (const sx of [-1, 1]) {
      for (let i = 0; i < N; i++) {
        const [c0, s0] = pts[i], [c1, s1] = pts[i + 1];
        const tri = sx > 0 ? [[0, 0], [c0, s0], [c1, s1]] : [[0, 0], [c1, s1], [c0, s0]];
        for (const [c, sn] of tri) { pos.push(sx * W, sn * r, c * r); nor.push(sx, 0, 0); }
      }
    }
    return geo(pos, nor);
  };
  const outer = sheet(r, false), inner = sheet(r - 0.004, true);
  const tube = new THREE.CylinderGeometry(0.007, 0.007, half * 2, 8, 1, true).rotateZ(Math.PI / 2).translate(0, 0.004, 0.004);
  // two arms from the back of the hood down to the board's top edge, each with a small mounting plate
  const arm = (x) => {
    const from = new THREE.Vector3(x, r * 0.6, -r * 0.2), to = new THREE.Vector3(x, -SG.up + 0.02, -SG.out + 0.012);
    const d = to.clone().sub(from), len = d.length();
    const g = new THREE.BoxGeometry(0.012, 0.012, len);
    g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), d.normalize()));
    return g.translate((from.x + to.x) / 2, (from.y + to.y) / 2, (from.z + to.z) / 2);
  };
  const plate = (x) => new THREE.BoxGeometry(0.05, 0.04, 0.008).translate(x, -SG.up + 0.02, -SG.out + 0.006);
  const ax = half * 0.7;
  const iron = mergeGeos([outer, caps(), arm(-ax), arm(ax), plate(-ax), plate(ax)]);
  const g = mergeGeos([iron, tube, inner], true);
  const m = new THREE.Mesh(g, fixtureMats);
  m.name = 'lighting_sign_lamp';
  const basis = new THREE.Matrix4().makeBasis(rect.right, rect.up, rect.normal);
  m.quaternion.setFromRotationMatrix(basis);
  m.position.copy(lamp);
  m.castShadow = false;
  m.receiveShadow = false;
  m.raycast = () => {};
  m.userData.lightingFixture = true;
  return m;
}

function geo(pos, nor) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  return g;
}

/** The part of a grouped, non-indexed geometry that uses material `index`. */
function sub(g, index) {
  const grp = g.groups.find((x) => x.materialIndex === index);
  const out = new THREE.BufferGeometry();
  for (const k of ['position', 'normal', 'uv']) {
    const a = g.attributes[k];
    out.setAttribute(k, new THREE.Float32BufferAttribute(a.array.slice(grp.start * a.itemSize, (grp.start + grp.count) * a.itemSize), a.itemSize));
  }
  return out;
}

/** Merge non-indexed copies of box geometries; with `groups`, one material group per input. */
function mergeGeos(list, groups = false) {
  const pos = [], nor = [], uv = [];
  const out = new THREE.BufferGeometry();
  let start = 0;
  list.forEach((g0, i) => {
    const g = g0.index ? g0.toNonIndexed() : g0;
    pos.push(...g.attributes.position.array);
    nor.push(...g.attributes.normal.array);
    if (g.attributes.uv) uv.push(...g.attributes.uv.array); else uv.push(...new Array(g.attributes.position.count * 2).fill(0));
    const n = g.attributes.position.count;
    if (groups) out.addGroup(start, n, i);
    start += n;
  });
  out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  out.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  return out;
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

/**
 * The interior of a stall as a box in its own frame, for clipping an unshadowed interior light
 * (shading.js addClip): found by casting rays from the light at the inner faces of the side walls,
 * the back wall, the lower front wall and the roof. The box ends `pad` past each inner face (inside
 * the boards, so the planks' edges in the gaps stay dark) and starts `floor` m over the base. In front
 * it has `front` m of extra room below the fascia (the counter top and the mugs stand out past the
 * front wall). Returns null when the stall is not closed on three sides.
 */
export function interiorBox(holder, lightPos, C = {}) {
  const pad = C.pad ?? 0.01;
  holder.updateMatrixWorld(true);
  const toWorld = holder.matrixWorld, toLocal = new THREE.Matrix4().copy(toWorld).invert();
  const L = lightPos.clone().applyMatrix4(toLocal);
  const q = holder.getWorldQuaternion(new THREE.Quaternion());
  const ws = holder.getWorldScale(new THREE.Vector3()).x || 1;
  const rc = new THREE.Raycaster();
  const meshes = [];
  holder.traverse((o) => { if (o.isMesh && !o.isInstancedMesh && o.visible && !o.userData.shadowOnly && !/^bulbs_/i.test(o.name)) meshes.push(o); });
  const first = (p, dir, far = 4) => {
    rc.set(p.clone().applyMatrix4(toWorld), dir.clone().applyQuaternion(q).normalize());
    rc.far = far * ws;
    const h = rc.intersectObjects(meshes, false)[0];
    return h ? h.distance / ws : null;
  };
  const median = (a) => { const b = a.filter((v) => v != null).sort((x, y) => x - y); return b.length ? b[b.length >> 1] : null; };
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const hs = [0.2, 0.5, 0.8].map((d) => L.y - d);
  const side = (dir, lat) => median(hs.flatMap((y) => [-0.3, 0, 0.3].map((t) => first(V(L.x, y, L.z).addScaledVector(lat, t), dir))));
  const X = V(1, 0, 0), Z = V(0, 0, 1);
  const right = side(X, Z), left = side(X.clone().negate(), Z), back = side(Z.clone().negate(), X);
  if (right == null || left == null || back == null) return null;
  // the lower front wall, below the counter
  const fr = median([0.35, 0.55, 0.75].flatMap((y) => [-0.4, 0, 0.4].map((t) => first(V(L.x + t, y, L.z), Z))));
  const zf = fr != null ? L.z + fr : L.z + 1.0;
  // the roof's underside over the interior, as a tent: its highest point (the ridge) and the steepest
  // drop either side of it, so the box stays under the boards everywhere (a flat top at the ridge
  // height would take in the shingles toward the eaves)
  const x0 = L.x - left - pad, x1 = L.x + right + pad, z0 = L.z - back - pad, z1 = zf + pad;
  const roofAt = (z) => median([-0.4, 0, 0.4].map((t) => first(V(L.x + t, L.y, z), V(0, 1, 0), 3)));
  const zs = Array.from({ length: 9 }, (_, i) => z0 + 0.05 + (z1 - z0 - 0.1) * (i / 8));
  const roofs = zs.map((z) => { const d = roofAt(z); return d == null ? null : { z, y: L.y + d }; }).filter(Boolean);
  let ridge = { z: L.z, y: L.y + 0.8 }, slope = 0;
  if (roofs.length) {
    ridge = roofs.reduce((a, b) => (b.y > a.y ? b : a));
    for (const r of roofs) if (Math.abs(r.z - ridge.z) > 0.05) slope = Math.max(slope, (ridge.y - r.y) / Math.abs(r.z - ridge.z));
  }
  const yTop = ridge.y + pad, yBot = C.floor ?? 0.3;
  // the fascia's lower edge: the lowest height over the counter where a ray forward stops at the front
  // (scanning up from the lower wall: past the serving opening, the first ray that stops at the front)
  const cutAt = (x) => {
    let open = false;
    for (let y = 0.5; y < L.y; y += 0.04) {
      const d = first(V(x, y, L.z), Z);
      const atFront = d != null && Math.abs(L.z + d - zf) < 0.25;
      if (!atFront) open = true; else if (open) return y;
    }
    return L.y;
  };
  const cut = median([-0.6, 0, 0.6].map((t) => cutAt(L.x + t)));
  const c = V((x0 + x1) / 2, (yBot + yTop) / 2, (z0 + z1) / 2);
  const center = c.clone().applyMatrix4(toWorld);
  const ax = V(1, 0, 0).applyQuaternion(q);
  const ang = Math.atan2(-ax.z, ax.x);
  return {
    center,
    half: V((x1 - x0) / 2, (yTop - yBot) / 2, (z1 - z0) / 2).multiplyScalar(ws),
    cos: Math.cos(ang), sin: Math.sin(ang),
    fade: (C.fade ?? 0.01) * ws,
    front: (C.front ?? 0.3) * ws,
    cut: (cut - 0.02 - c.y) * ws,
    slope, ridge: (ridge.z - c.z) * ws,
    local: { x0, x1, z0, z1, yBot, yTop, cut, slope, ridgeZ: ridge.z },
  };
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
/**
 * Bulb bounce (round 2): a model that has a rot_wheel (the Ferris wheel) is covered in bulbs, which
 * light its steel round them. Its opaque, non-emissive materials above B.minY m (or under rot_wheel)
 * get a warm emissive equal to albedo x colour x strength, so the cream steel reads as lit by its own
 * bulbs on full and lite alike, with no lights. Materials are cloned once per model, so a material
 * the model shares with a booth at ground level keeps its own look there.
 */
export function bulbBounce(root, N) {
  const B = N.emissive?.bounce;
  const wheel = root.getObjectByName('rot_wheel');
  if (!B || !wheel) return 0;
  root.updateMatrixWorld(true);
  const groundY = root.getWorldPosition(new THREE.Vector3()).y;
  const under = new Set();
  wheel.traverse((o) => under.add(o));
  const clones = new Map(), box = new THREE.Box3(), c = new THREE.Vector3();
  const warm = new THREE.Color().setRGB(...(B.color || [1, 0.7, 0.42]));
  let n = 0;
  root.traverse((o) => {
    if (!o.isMesh || /^bulbs_/i.test(o.name) || /^bulbs_/i.test(o.parent?.name || '')) return;
    if (!under.has(o)) {
      box.setFromObject(o).getCenter(c);
      if (c.y - groundY < (B.minY ?? 3)) return;
    }
    const one = (m) => {
      if (!m || !m.emissive || m.transparent || m.opacity < 1 || isBulbMat(m) || isWindowMat(m)) return m;
      if (m.emissiveMap || m.emissive.getHex() !== 0) return m;
      if (clones.has(m)) return clones.get(m);
      const k = /steel|metal|iron/i.test(m.name) && !/black/i.test(m.name) ? B.steel : B.other;
      const q = m.clone();
      q.name = m.name;
      q.emissive.copy(m.color).multiply(warm);
      q.emissiveMap = m.map || null;
      q.emissiveIntensity = k;
      q.userData.bulbBounce = k;
      clones.set(m, q);
      n++;
      return q;
    };
    o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material);
  });
  return n;
}

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

/**
 * Round 2, fix pass: fade the bulbs of a turning wheel (a model with rot_wheel) toward its hub, so the
 * converging spoke strings do not bloom into a starburst (settings emissive.hubFade). Each bulbs_ mesh
 * under rot_wheel gets a per-vertex `nmEmit` (1 on the rim, `min` at the hub) and a clone of its bulb
 * material that multiplies its emissive by it. `bulbs` (the model's bulb material set from
 * tuneEmissives) gets the clones, so the emissive tuning still reaches them. Returns the meshes faded.
 */
export function hubFade(root, N, bulbs) {
  const H = N.emissive?.hubFade;
  const wheel = root.getObjectByName('rot_wheel');
  if (!H || !wheel) return 0;
  root.updateMatrixWorld(true);
  const toWheel = new THREE.Matrix4().copy(wheel.matrixWorld).invert();
  const m4 = new THREE.Matrix4(), v = new THREE.Vector3();
  const lo = H.inner ?? 1.2, hi = H.outer ?? 5, min = H.min ?? 0.15;
  const clones = new Map();
  let n = 0;
  wheel.traverse((o) => {
    if (!o.isMesh || o.userData.hubFade || !(/^bulbs_/i.test(o.name) || /^bulbs_/i.test(o.parent?.name || ''))) return;
    const pos = o.geometry?.attributes?.position;
    if (!pos) return;
    m4.multiplyMatrices(toWheel, o.matrixWorld);
    const fade = new Float32Array(pos.count);
    let any = false;
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i).applyMatrix4(m4);
      const t = THREE.MathUtils.smoothstep(Math.hypot(v.x, v.y), lo, hi); // the wheel turns about its local z
      fade[i] = min + (1 - min) * t;
      if (fade[i] < 0.999) any = true;
    }
    if (!any) return; // a gondola's bulbs, out on the rim
    o.geometry = o.geometry.clone();
    o.geometry.setAttribute('nmEmit', new THREE.BufferAttribute(fade, 1));
    const one = (m) => {
      if (!m || !m.emissive) return m;
      if (clones.has(m)) return clones.get(m);
      const q = m.clone();
      q.name = m.name;
      q.userData = { ...m.userData, hubFade: true };
      const prev = m.onBeforeCompile;
      q.onBeforeCompile = (sh, r) => {
        prev?.call(q, sh, r);
        sh.vertexShader = sh.vertexShader
          .replace('#include <common>', '#include <common>\nattribute float nmEmit;\nvarying float vNmEmit;')
          .replace('#include <begin_vertex>', '#include <begin_vertex>\n\tvNmEmit = nmEmit;');
        sh.fragmentShader = sh.fragmentShader
          .replace('#include <common>', '#include <common>\nvarying float vNmEmit;')
          .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n\ttotalEmissiveRadiance *= vNmEmit;');
      };
      q.customProgramCacheKey = () => `nmHubFade|${m.customProgramCacheKey?.() ?? ''}`;
      clones.set(m, q);
      if (bulbs?.has(m)) bulbs.add(q);
      return q;
    };
    o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material);
    o.userData.hubFade = true;
    n++;
  });
  return n;
}

/**
 * Keep every bulb at least about two pixels across (2026-10-06). Without MSAA (FXAA replaced it,
 * index.js) a distant bulb smaller than a pixel lands between pixel centres and the strings drop out.
 * The vertex shader pushes each bulb vertex out along its normal by `uniforms.uBulbPx` times its view
 * depth, which the caller sets each frame to about a pixel (?lighting=bulbPx:n); near bulbs barely change.
 */
const bulbPatched = new WeakSet();
export function bulbMinSize(materials, uniforms) {
  let n = 0;
  for (const m of materials) {
    if (!m || bulbPatched.has(m) || !(m.isMeshStandardMaterial || m.isMeshLambertMaterial || m.isMeshPhongMaterial)) continue;
    // a WeakSet, not a userData flag: clone() copies userData but not onBeforeCompile (the engine's lightBulbs clones)
    bulbPatched.add(m);
    const prev = m.onBeforeCompile, key = m.customProgramCacheKey?.bind(m);
    m.onBeforeCompile = (sh, r) => {
      prev?.call(m, sh, r);
      sh.uniforms.uBulbPx = uniforms.uBulbPx;
      if (sh.vertexShader.includes('uBulbPx')) return; // hubFade's clone of a patched material chains this patch already
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uBulbPx;')
        .replace('#include <project_vertex>', '#include <project_vertex>\n\t{ float bnl = length( transformedNormal ); if ( bnl > 1e-6 ) { mvPosition.xyz += transformedNormal / bnl * ( - mvPosition.z ) * uBulbPx; gl_Position = projectionMatrix * mvPosition; } }');
    };
    m.customProgramCacheKey = () => `${key ? key() : ''}|bulbPx`;
    m.needsUpdate = true;
    n++;
  }
  return n;
}
