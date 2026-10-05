// Reads the named nodes of a placed model (see docs/BUILD.md "Scene conventions") and wires them up:
//   bulbs_ glow · light_ real-time light spots · snow_ caps · slot_ prop anchors · cam_view/cam_target
//   act_ action nodes · rot_ spinners · gondola_ and horse_ riders.
import * as THREE from 'three';

const WARM = new THREE.Color(1.0, 0.6, 0.26);
const COLD = new THREE.Color(0.62, 0.76, 1.0);

const byIndex = (a, b) => (parseInt(a.name.replace(/\D+/g, ''), 10) || 0) - (parseInt(b.name.replace(/\D+/g, ''), 10) || 0);

/** Material names come through as authored ("bulb_warm", "bulb_warm.001"). */
function bulbKind(mat, nodeName) {
  const n = (mat?.name || '').toLowerCase();
  if (n.startsWith('bulb_cold')) return 'cold';
  if (n.startsWith('bulb_warm')) return 'warm';
  if (/^bulbs_/i.test(nodeName)) return /cold|blue/i.test(nodeName) ? 'cold' : 'warm';
  return null;
}

function hasPrefixUp(o, stop, re) {
  for (let p = o; p && p !== stop.parent; p = p.parent) if (re.test(p.name)) return p;
  return null;
}

/** Scan a model root. Pure bookkeeping: returns the nodes found, changes nothing. */
export function scanNodes(root) {
  const n = { bulbs: [], lights: [], snow: [], slots: {}, acts: {}, camView: null, camTarget: null, camCats: {}, camCatTargets: {}, rots: [], gondolas: [], horses: [], meshes: [] };
  root.traverse((o) => {
    const name = o.name || '';
    if (/^light_/i.test(name)) n.lights.push(o);
    else if (/^snow_/i.test(name)) n.snow.push(o);
    else if (/^slot_/i.test(name)) { const k = name.toLowerCase(); if (!n.slots[k]) n.slots[k] = o; }
    else if (/^cam_cat_.+_target$/i.test(name)) { const k = name.toLowerCase().slice(8, -7); n.camCatTargets[k] ??= o; }
    else if (/^cam_cat_./i.test(name)) { const k = name.toLowerCase().slice(8).replace(/\.\d+$/, ''); n.camCats[k] ??= o; }
    else if (/^cam_view/i.test(name)) n.camView ??= o;
    else if (/^cam_target/i.test(name)) n.camTarget ??= o;
    // act_x is the pivot; an act_x_mesh inside it is only its geometry (the vendor's and ride builder's export)
    else if (/^act_/i.test(name) && !/_mesh(\.\d+)?$/i.test(name)) { const k = name.toLowerCase(); if (!n.acts[k]) n.acts[k] = o; }
    else if (/^rot_/i.test(name)) n.rots.push(o);
    else if (/^gondola_/i.test(name) && !hasPrefixUp(o.parent, root, /^gondola_/i)) n.gondolas.push(o);
    else if (/^horse_/i.test(name) && !hasPrefixUp(o.parent, root, /^horse_/i)) n.horses.push(o);
    if (o.isMesh) {
      n.meshes.push(o);
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const holder = hasPrefixUp(o, root, /^bulbs_/i);
      const kind = mats.map((m) => bulbKind(m, holder ? holder.name : name)).find(Boolean);
      if (holder || kind) n.bulbs.push({ mesh: o, kind: kind || 'warm' });
    }
  });
  n.gondolas.sort(byIndex);
  n.horses.sort(byIndex);
  return n;
}

/** All act_ nodes whose name starts with the prefix, in numeric order ("act_book_" -> books). */
export function actList(nodes, prefix) {
  return Object.entries(nodes.acts).filter(([k]) => k.startsWith(prefix)).map(([, o]) => o).sort(byIndex);
}

const bulbMatCache = new Map();
/** Make bulb materials emissive for bloom. Returns the glowing materials (shared per source material). */
export function lightBulbs(nodes, { lite }) {
  const out = new Set();
  for (const { mesh, kind } of nodes.bulbs) {
    const swap = (m) => {
      const key = m.uuid + kind;
      if (!bulbMatCache.has(key)) {
        const c = m.clone();
        const tint = kind === 'cold' ? COLD : WARM;
        if (!c.emissive || c.emissive.getHex() === 0) c.emissive = tint.clone();
        c.userData.baseEmissive = Math.max(c.emissiveIntensity || 1, lite ? 4 : 5.5);
        c.emissiveIntensity = c.userData.baseEmissive;
        c.userData.bulb = kind;
        bulbMatCache.set(key, c);
      }
      const c = bulbMatCache.get(key);
      out.add(c);
      return c;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.userData.bulbs = true;
  }
  return [...out];
}

/** The local axis a rot_ node spins about: userData.axis, a name hint, or its thinnest extent. */
export function spinAxis(node) {
  const hint = String(node.userData?.axis || node.userData?.spin_axis || '').toLowerCase();
  if (['x', 'y', 'z'].includes(hint)) return hint;
  if (/wheel|rad/i.test(node.name)) return 'z';
  if (/platform|carousel|karussell|turntable|canopy/i.test(node.name)) return 'y';
  node.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(node.matrixWorld).invert();
  const box = new THREE.Box3();
  const tmp = new THREE.Box3();
  node.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    tmp.copy(o.geometry.boundingBox).applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    box.union(tmp);
  });
  if (box.isEmpty()) return 'y';
  const s = box.getSize(new THREE.Vector3());
  return s.x <= s.y && s.x <= s.z ? 'x' : s.z <= s.y ? 'z' : 'y';
}

const AXES = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

/**
 * Spinners (rot_), gondolas and horses for one model. `update(dt, t, speedScale)` moves them.
 * Gondolas stay upright whether they are children of the wheel or its siblings.
 */
export function makeRides(nodes) {
  const spinners = nodes.rots.map((obj) => {
    const axis = spinAxis(obj);
    const wheelish = axis !== 'y';
    const speed = Number(obj.userData?.speed) || (wheelish ? 0.05 : -0.32);
    return { obj, axis, speed, angle: 0, q0: obj.quaternion.clone(), wheelish };
  });
  const wheel = spinners.find((s) => s.wheelish) || null;
  const platform = spinners.find((s) => !s.wheelish) || null;
  const gondolas = nodes.gondolas.map((obj, i) => {
    obj.updateMatrixWorld(true);
    const world = obj.getWorldPosition(new THREE.Vector3());
    const pivot = wheel ? wheel.obj.worldToLocal(world.clone()) : null;
    return { obj, pivot, q0: obj.getWorldQuaternion(new THREE.Quaternion()), ph: i * 1.3 };
  });
  const horses = nodes.horses.map((obj, i) => ({ obj, y0: obj.position.y, ph: i * 1.1 }));
  const _q = new THREE.Quaternion(), _pq = new THREE.Quaternion(), _v = new THREE.Vector3(), _sway = new THREE.Quaternion();
  return {
    spinners, wheel, platform, gondolas, horses,
    /**
     * Park the wheel with its gondolas where the model put them (a whole turn, angle 2πk), or let it turn again.
     * It always parks going forward, the way it turns, never backwards: on to the next whole turn ahead, on an
     * eased curve that starts at the wheel's own pace, speeds up gently and slows to a stop (round 5 pass 4).
     * `snap` parks at once (reduced motion). `parked` is true once it is there. Returns the seconds it will take.
     */
    park(on, { snap = false } = {}) {
      if (!wheel) return 0;
      if (!on) {
        // turn again: from standing, the wheel takes up its pace over a second and a half
        if (wheel.parkTo != null) wheel.ramp = 0;
        wheel.parkTo = null; wheel.parkRun = null;
        return 0;
      }
      if (wheel.parkTo != null && !snap) return wheel.parkRun ? wheel.parkRun.T - wheel.parkRun.t : 0;
      const TURN = 2 * Math.PI, dir = Math.sign(wheel.speed) || 1;
      const a = wheel.angle * dir; // forward distance measured the way the wheel turns
      let to = Math.ceil(a / TURN - 1e-4) * TURN;
      const D = Math.max(0, to - a);
      wheel.parkTo = to * dir;
      if (snap || D < 1e-3) { wheel.angle = wheel.parkTo; wheel.parkRun = null; this.update(0, 0, 1, false); return 0; }
      // a cubic Hermite from the wheel's present pace to standing: monotonic (never backwards) while m0 <= 3
      const T = Math.min(8.5, 2 + D * 1.0);
      const v0 = Math.abs(wheel.speed * (wheel.boost || 1));
      wheel.parkRun = { from: wheel.angle, D, dir, T, t: 0, m0: Math.min(3, (v0 * T) / D) };
      return T;
    },
    get parked() { return !!wheel && wheel.parkTo != null && !wheel.parkRun && Math.abs(wheel.parkTo - wheel.angle) < 1e-3; },
    update(dt, t, speedScale = 1, moving = true) {
      for (const s of spinners) {
        if (s.parkTo != null) {
          // parked (round 5): forward along the eased curve, so a placard's gondola comes down and waits there
          const r = s.parkRun;
          if (r) {
            r.t = Math.min(r.T, r.t + dt);
            const u = r.t / r.T;
            const p = (-2 * u ** 3 + 3 * u ** 2) + (u ** 3 - 2 * u ** 2 + u) * r.m0;
            s.angle = r.from + r.dir * r.D * Math.min(1, p);
            if (r.t >= r.T) { s.angle = s.parkTo; s.parkRun = null; }
          } else s.angle = s.parkTo;
        } else {
          if (s.ramp != null) { s.ramp = Math.min(1, s.ramp + dt / 1.5); if (s.ramp >= 1) s.ramp = null; }
          const k = s.ramp == null ? 1 : s.ramp * s.ramp * (3 - 2 * s.ramp);
          s.angle += dt * s.speed * speedScale * (s.boost || 1) * k;
        }
        s.obj.quaternion.copy(s.q0).multiply(_q.setFromAxisAngle(AXES[s.axis], s.angle));
      }
      if (wheel && gondolas.length) {
        wheel.obj.updateMatrixWorld(true);
        for (const g of gondolas) {
          _v.copy(g.pivot);
          wheel.obj.localToWorld(_v);
          const parent = g.obj.parent;
          parent.updateMatrixWorld(true);
          parent.worldToLocal(_v);
          g.obj.position.copy(_v);
          parent.getWorldQuaternion(_pq).invert();
          _sway.setFromAxisAngle(AXES.z, moving ? Math.sin(t * 0.8 + g.ph) * 0.03 : 0);
          g.obj.quaternion.copy(_pq).multiply(g.q0).multiply(_sway);
        }
      }
      if (moving) for (const h of horses) h.obj.position.y = h.y0 + Math.sin(t * 2.2 + h.ph) * 0.2;
    },
  };
}
