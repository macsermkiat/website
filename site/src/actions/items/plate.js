// The Bratwurst plate (round 10, ADR 0004 revision). Mac: "no need to able to flip that lots sausages, just few
// different kind is enough. But if it's able to mix on plate and put on sauce must be nice."
//
// - A sausage or the roll on the serving board: the vendor takes it and a fresh one flies in a short arc to the
//   paper plate, landing at the next free plate_spot_<n> (a long one takes a whole row of two spots). The one on the
//   board is set out again. A sausage that lands while a roll waits on the plate goes into the roll.
// - A sauce bottle: it is picked up, carried over the plate and turned nozzle down, and its nozzle pipes a glossy
//   zigzag over every item on the plate in turn, following each item's surface (rays cast down onto it); an empty
//   plate gets a dollop. Each squeeze crosses the last one.
// - The curry shaker: carried over the plate and shaken; the powder falls from the pierced lid and settles on the
//   items' tops.
// - The plate itself: handed over the counter ("Guten Appetit") and a fresh plate is set down.
// Actions queue, so a quick Thüringer, Ketchup, Senf plays in that order. Reduced motion: every step lands at once.
import * as THREE from 'three';
import { boxOf, rest, restore, worldDirToParent, createStream, UP, esc } from './common.js';

const SAUCE_DEFAULTS = { senf: '#d6a21c', ketchup: '#a8140e', curry: '#b4400e' };
const SAUCE_NAMES = { senf: 'Senf', ketchup: 'Ketchup', curry: 'Currysauce' };
const SINGLE_MAX = 0.095; // m: longer items take a whole row of the plate
const MAX_SAUCES = 3; // squiggles an item takes before the vendor says enough
const MAX_DUST = 3;
const RIBBON_R = 0.0027; // m: the sauce's line

const _m = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3();

/** A node's pose in `frame`'s local space. */
function poseIn(node, frame) {
  node.updateWorldMatrix(true, false);
  frame.updateWorldMatrix(true, false);
  _m.copy(frame.matrixWorld).invert().multiply(node.matrixWorld).decompose(_p, _q, _s);
  return { p: _p.clone(), q: _q.clone(), s: _s.clone() };
}

/** A copy of what draws `node` (its meshes, sharing geometry and material), as a group in `node`'s frame. */
function copyOf(node, restScale = null) {
  const g = new THREE.Group();
  const sc = node.scale.clone();
  if (restScale) node.scale.copy(restScale);
  node.updateWorldMatrix(true, true);
  const inv = new THREE.Matrix4().copy(node.matrixWorld).invert();
  node.traverse((o) => {
    if (!o.isMesh || o.userData.itemFx || !o.visible && o !== node) return;
    const m = new THREE.Mesh(o.geometry, o.material);
    m.matrixAutoUpdate = false;
    m.matrix.copy(inv).multiply(o.matrixWorld);
    m.castShadow = true;
    m.receiveShadow = true;
    m.userData.plated = true;
    g.add(m);
  });
  node.scale.copy(sc);
  node.updateWorldMatrix(false, true);
  return g;
}

/**
 * A ribbon of sauce along points (plate-local), flattened on its underside and thinning to a point at both ends.
 * Its triangles are in path order, so a draw range draws it in as it is piped.
 */
function sauceRibbon(pts, R, seed = 1) {
  const N = pts.length, M = 8;
  const pos = new Float32Array(N * M * 3);
  const T = new THREE.Vector3(), side = new THREE.Vector3(), up = new THREE.Vector3(), v = new THREE.Vector3();
  const Y = new THREE.Vector3(0, 1, 0);
  let s = seed * 9301 + 49297;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const wob = Array.from({ length: N }, () => 0.85 + rnd() * 0.3);
  for (let i = 0; i < N; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(N - 1, i + 1)];
    T.subVectors(b, a).normalize();
    side.crossVectors(T, Y);
    if (side.lengthSq() < 1e-8) side.set(1, 0, 0);
    side.normalize();
    up.crossVectors(side, T).normalize();
    if (up.y < 0) up.negate();
    const t = i / (N - 1);
    const taper = Math.sin(Math.min(1, t / 0.07) * Math.PI / 2) * Math.pow(Math.sin(Math.min(1, (1 - t) / 0.12) * Math.PI / 2), 0.7);
    const r = R * taper * (i > 0 && i < N - 1 ? (wob[i] + wob[i - 1] + wob[i + 1]) / 3 : 1);
    for (let j = 0; j < M; j++) {
      const ang = (j / M) * Math.PI * 2;
      v.copy(pts[i]).addScaledVector(side, Math.cos(ang) * r * 1.2).addScaledVector(up, Math.sin(ang) * r * 0.68 + r * 0.25);
      pos.set([v.x, v.y, v.z], (i * M + j) * 3);
    }
  }
  const idx = [];
  for (let i = 0; i < N - 1; i++) for (let j = 0; j < M; j++) {
    const a = i * M + j, b = i * M + ((j + 1) % M), c = a + M, d = b + M;
    idx.push(a, c, b, b, c, d);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  geo.userData.perSegment = M * 6;
  return geo;
}

export function createPlate(ctx, place, { items, wurstItems, sauceItems, shakerItem, plateItem }) {
  const { anim, scene, sfx, say, crowdSay, lite, motion } = ctx;
  const plate = plateItem.node;
  const info = plateItem.info || {};
  const front = new THREE.Vector3(Math.sin(place.ry), 0, Math.cos(place.ry));
  const ray = new THREE.Raycaster();

  // ---------- the spots: the vendor's plate_spot_<n>, or a 2 x 2 grid on a plate without them ----------
  const spotNames = Array.isArray(info.spots) && info.spots.length ? info.spots : ['plate_spot_0', 'plate_spot_1', 'plate_spot_2', 'plate_spot_3'];
  const spots = spotNames.map((n, i) => {
    let o = null;
    plate.traverse((x) => { if (!o && x.name === n) o = x; });
    const p = o ? poseIn(o, plate).p : new THREE.Vector3((i % 2 ? 1 : -1) * 0.042, 0.002, (i < 2 ? -1 : 1) * 0.036);
    return { name: n, p, used: null };
  });
  const maxItems = Math.min(spots.length, +info.max_items || 4);
  // rows: spots that share a z (the plate's items lie along x)
  const rows = [];
  for (const s of spots) {
    const r = rows.find((x) => Math.abs(x.z - s.p.z) < 0.01);
    if (r) r.spots.push(s); else rows.push({ z: s.p.z, spots: [s] });
  }
  const plateMeshes = [];
  plate.traverse((o) => { if (o.isMesh && !o.userData.plated) plateMeshes.push(o); });
  const plateR = (() => { const b = boxOf(plate, plate); const s = b.getSize(new THREE.Vector3()); return Math.max(0.06, Math.min(s.x, s.z) / 2); })();

  const records = []; // what is on the plate
  const extras = []; // dollops and powder on the plate itself
  const sauceMats = {};
  let dusts = 0;
  const queue = [];
  let running = false;

  const streams = {};
  const streamFor = (key, mat) => (streams[key] ||= createStream(scene, mat, 0.0021));
  function sauceMat(key, colour) {
    if (sauceMats[key]) return sauceMats[key];
    const c = new THREE.Color(colour || SAUCE_DEFAULTS[key] || '#a8140e');
    const m = lite
      ? new THREE.MeshStandardMaterial({ name: `item_sauce_${key}`, color: c, roughness: 0.3, emissive: c.clone().multiplyScalar(0.06) })
      : new THREE.MeshPhysicalMaterial({ name: `item_sauce_${key}`, color: c, roughness: 0.24, clearcoat: 1, clearcoatRoughness: 0.08, emissive: c.clone().multiplyScalar(0.05) });
    return (sauceMats[key] = m);
  }

  // ---------- the queue ----------
  function enqueue(step) {
    if (queue.length >= 5) return false;
    queue.push(step);
    if (!running) pump();
    return true;
  }
  function pump() {
    const step = queue.shift();
    if (!step) { running = false; return; }
    running = true;
    let called = false;
    try { step(() => { if (called) return; called = true; pump(); }); } catch (e) { console.warn('[plate]', e); called = true; pump(); }
  }

  // ---------- measuring an item ----------
  function measure(node) {
    const b = boxOf(node, node);
    const s = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
    const alongZ = s.z > s.x;
    return { box: b, c, L: Math.max(s.x, s.z), W: Math.min(s.x, s.z), H: s.y, yaw0: alongZ ? Math.PI / 2 : 0 };
  }
  const meshesOf = (rec) => { const out = []; rec.group.traverse((o) => { if (o.isMesh && o.userData.plated) out.push(o); }); if (rec.filling) out.push(...meshesOf(rec.filling)); return out; };

  /** Where an item would go: { spots, at (plate-local, the item's footprint centre on the floor), host } or null. */
  function placeFor(kind, m) {
    if (['thueringer', 'krakauer', 'nuernberger'].includes(kind)) {
      const host = records.find((r) => r.kind === 'roll' && !r.filling && !r.leaving);
      if (host) return { host };
    }
    const used = records.reduce((n, r) => n + r.spots.length, 0);
    if (used >= maxItems) return null;
    if (m.L <= SINGLE_MAX) {
      const s = spots.find((x) => !x.used);
      return s ? { spots: [s], at: s.p.clone() } : null;
    }
    const row = rows.find((r) => r.spots.length >= 2 && r.spots.every((x) => !x.used));
    if (row) return { spots: row.spots, at: row.spots.reduce((a, x) => a.add(x.p), new THREE.Vector3()).multiplyScalar(1 / row.spots.length).setX(0) };
    return null;
  }

  // ---------- 1. a sausage or the roll to the plate ----------
  function toPlate(item, { quiet = false, done } = {}) {
    const node = item.node;
    const kind = item.info.wurst || (item.kind === 'roll' ? 'roll' : 'wurst');
    const m = measure(node);
    const where = placeFor(kind, m);
    if (!where) {
      if (!quiet) say(`The plate is full. <em>Tap the plate to have it handed over, and start again.</em>`);
      wobble();
      done?.(false);
      return false;
    }
    items.release(item);
    // (a second one of the same kind while the first is still being set out again: copy it at its full size)
    item.restScale ||= node.scale.clone();
    const sc0 = item.restScale.clone();
    item.busy = true;
    const g = copyOf(node, sc0);
    g.name = `plated_${kind}`;
    g.userData.itemProxy = plateItem; // a click on what is on the plate means the plate
    plate.add(g);
    const scNow = node.scale.clone();
    node.scale.copy(sc0);
    const start = poseIn(node, plate);
    node.scale.copy(scNow);
    g.position.copy(start.p); g.quaternion.copy(start.q); g.scale.copy(start.s);
    const rec = { item, kind, group: g, m, spots: where.spots || [], sauces: [], filling: null, host: where.host || null, yaw: 0 };
    rec.spots.forEach((s) => (s.used = rec));
    // the end pose, in the plate's frame (the plate is level; items lie along its x)
    let endP, yaw;
    if (rec.host) {
      const h = rec.host;
      yaw = h.yaw;
      const hTop = h.group.position.y + h.m.box.max.y;
      endP = h.group.position.clone();
      endP.y = hTop - m.H * 0.62 - m.box.min.y + 0.004;
      // centre the sausage's box over the roll's
      const off = new THREE.Vector3(m.c.x, 0, m.c.z).applyAxisAngle(UP, yaw - m.yaw0 + h.m.yaw0);
      const hOff = new THREE.Vector3(h.m.c.x, 0, h.m.c.z).applyAxisAngle(UP, yaw);
      endP.add(hOff).sub(off);
      yaw = yaw - m.yaw0 + h.m.yaw0;
      h.filling = rec;
    } else {
      const jitter = (Math.random() - 0.5) * (m.L > SINGLE_MAX ? 0.12 : 0.5);
      yaw = -m.yaw0 + jitter;
      const off = new THREE.Vector3(m.c.x, 0, m.c.z).applyAxisAngle(UP, yaw);
      endP = where.at.clone().sub(off);
      endP.y = where.at.y - m.box.min.y;
      // keep it on the plate: a long one must not hang over the rim more than a little
      endP.x = THREE.MathUtils.clamp(endP.x, -plateR + m.L * 0.42, plateR - m.L * 0.42) || 0;
      records.push(rec);
    }
    rec.yaw = yaw;
    const endQ = new THREE.Quaternion().setFromAxisAngle(UP, yaw);
    const p0 = start.p.clone(), q0 = start.q.clone(), s0 = start.s.clone();
    const arc = 0.1 + p0.distanceTo(endP) * 0.35;
    const spin = new THREE.Quaternion();
    // the one on the board: taken, and set out again a moment later
    const r0 = rest(node);
    node.scale.setScalar(0.001);
    sfx('sizzle');
    anim.add(0.75, (k) => {
      g.position.lerpVectors(p0, endP, k).addScaledVector(UP, Math.sin(k * Math.PI) * arc);
      g.quaternion.slerpQuaternions(q0, endQ, k).multiply(spin.setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.sin(k * Math.PI) * 0.5));
      g.scale.copy(s0);
    }, () => {
      g.position.copy(endP); g.quaternion.copy(endQ);
      sfx('plate');
      // a soft landing: a small squash
      anim.add(0.22, (k) => g.scale.set(s0.x * (1 + 0.05 * Math.sin(k * Math.PI)), s0.y * (1 - 0.08 * Math.sin(k * Math.PI)), s0.z * (1 + 0.05 * Math.sin(k * Math.PI))), () => g.scale.copy(s0));
      if (!quiet) say(placedNote(rec));
      done?.(true);
    });
    anim.add(0.4, (k) => node.scale.copy(sc0).multiplyScalar(Math.max(0.001, k)), () => { node.scale.copy(sc0); restore(node, r0); item.busy = false; items.settle?.(item); }, 0.9);
    return true;
  }

  function placedNote(rec) {
    const label = esc(rec.item.info.label || rec.item.label || 'Bratwurst');
    const detail = rec.item.info.detail ? ` ${esc(rec.item.info.detail)}` : '';
    const n = records.reduce((a, r) => a + r.spots.length, 0);
    if (rec.host) return `<b>${label}</b> into the Brötchen.${detail} <em>Now a sauce?</em>`;
    return `<b>${label}</b> on the plate.${detail} <em>(${n} of ${maxItems}; a bottle for sauce, the plate to finish)</em>`;
  }

  // ---------- 2. sauce ----------
  /** The squiggle over one record, in plate-local points (rays cast down onto its meshes). */
  function squigglePath(rec, n) {
    const tgt = rec.filling || rec;
    const meshes = meshesOf(tgt).filter((x) => x.userData.plated);
    const L = tgt.m.L, W = tgt.m.W;
    const half = L * 0.4;
    const waves = Math.max(2, Math.round(L / 0.03));
    const amp = Math.min(W * 0.34, 0.012) * (0.85 + 0.15 * (n % 2));
    const phase = n * 1.9;
    const N = Math.max(36, waves * 10);
    const c = tgt.group.position.clone().add(new THREE.Vector3(tgt.m.c.x, 0, tgt.m.c.z).applyAxisAngle(UP, tgt.yaw));
    const ax = new THREE.Vector3(1, 0, 0).applyAxisAngle(UP, tgt.yaw + tgt.m.yaw0);
    const lat = new THREE.Vector3(-ax.z, 0, ax.x);
    const pts = [];
    plate.updateWorldMatrix(true, true);
    const down = new THREE.Vector3(0, -1, 0).transformDirection(plate.matrixWorld);
    const dir = n % 2 ? -1 : 1; // every other squeeze runs the other way
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      const u = dir * (-half + 2 * half * t);
      const v = amp * Math.sin(t * waves * Math.PI * 2 + phase);
      const local = c.clone().addScaledVector(ax, u).addScaledVector(lat, v);
      local.y = tgt.group.position.y + tgt.m.H + 0.15;
      const from = plate.localToWorld(local.clone());
      ray.set(from, down);
      ray.far = 0.4;
      const hit = ray.intersectObjects(meshes, false)[0];
      if (!hit) continue;
      const p = plate.worldToLocal(hit.point.clone());
      p.y += RIBBON_R * 0.15;
      pts.push(p);
    }
    return pts.length >= 6 ? pts : null;
  }
  function dollopPath(n) {
    // an empty plate: a small swirl of sauce, off centre
    const a0 = n * 2.1;
    const c = new THREE.Vector3(Math.cos(a0) * plateR * 0.35, 0, Math.sin(a0) * plateR * 0.35);
    const pts = [];
    const down = new THREE.Vector3(0, -1, 0).transformDirection(plate.matrixWorld);
    for (let i = 0; i < 40; i++) {
      const t = i / 39, r = 0.016 * (1 - t * 0.75), a = t * Math.PI * 4;
      const local = c.clone().add(new THREE.Vector3(Math.cos(a) * r, 0.1, Math.sin(a) * r));
      ray.set(plate.localToWorld(local.clone()), down);
      ray.far = 0.3;
      const hit = ray.intersectObjects(plateMeshes, false)[0];
      const p = hit ? plate.worldToLocal(hit.point.clone()) : local.setY(0.004);
      p.y += RIBBON_R * 0.2 + t * 0.003; // it heaps up a little in the middle
      pts.push(p);
    }
    return pts;
  }

  /** Move a held node so that its fx point sits at `tipWorld`, tilted by `tilt` (in its parent's frame). */
  function holdAt(node, fxLocal, tipWorld, tilt) {
    node.parent.updateWorldMatrix(true, false);
    const parentInv = new THREE.Matrix4().copy(node.parent.matrixWorld).invert();
    const tip = tipWorld.clone().applyMatrix4(parentInv);
    node.quaternion.copy(tilt);
    node.position.copy(tip).sub(fxLocal.clone().multiply(node.scale).applyQuaternion(tilt));
  }

  function sauce(item, done) {
    const key = item.info.sauce || /act_sauce_(\w+)/.exec(item.node.name)?.[1] || 'ketchup';
    const name = SAUCE_NAMES[key] || item.info.label || 'Sauce';
    const mat = sauceMat(key, item.info.colour);
    const targets = records.filter((r) => r.sauces.length < MAX_SAUCES);
    if (records.length && !targets.length) { say(`That is plenty of sauce for one plate. <em>Tap the plate to finish it.</em>`); done(); return; }
    // the paths, one per item (or a dollop on an empty plate)
    const jobs = [];
    if (!records.length) { if (extras.filter((e) => e.sauce).length < 3) jobs.push({ rec: null, pts: dollopPath(extras.length) }); }
    else for (const r of targets) { const pts = squigglePath(r, r.sauces.length); if (pts) jobs.push({ rec: r, pts }); }
    if (!jobs.length) { say(`No room for more ${esc(name)} just now. <em>Tap the plate to finish it.</em>`); done(); return; }
    const node = item.node;
    items.release(item);
    item.busy = true;
    const r0 = rest(node), sc0 = node.scale.clone();
    const fx = (() => { let f = null; node.traverse((o) => { if (!f && /^fx_/.test(o.name)) f = o; }); return f ? poseIn(f, node).p : new THREE.Vector3(0, measure(node).box.max.y, 0); })();
    // the ribbons, drawn in as the nozzle passes
    const ribbons = jobs.map((j, i) => {
      const geo = sauceRibbon(j.pts, RIBBON_R * (key === 'senf' ? 0.85 : 1), records.length * 7 + i + extras.length);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.name = `item_sauce_${key}`;
      mesh.userData.itemFx = true;
      mesh.castShadow = false; mesh.receiveShadow = true;
      mesh.raycast = () => {};
      geo.setDrawRange(0, 0);
      plate.add(mesh);
      if (j.rec) j.rec.sauces.push(key); else extras.push({ mesh, sauce: key });
      if (j.rec) (j.rec.extra ||= []).push(mesh);
      return { mesh, geo, pts: j.pts, segs: j.pts.length - 1 };
    });
    // the bottle: lifted, carried over, turned nozzle down (tipped toward the visitor so its label shows and its body
    // stays behind the plate), then it pipes, then it goes home
    const frontP = worldDirToParent(node, front).normalize();
    const axis = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), frontP).normalize(); // along the counter
    const tilt = new THREE.Quaternion().setFromAxisAngle(axis, Math.PI * 0.8).multiply(r0.q);
    const lift = r0.p.clone().addScaledVector(worldDirToParent(node, UP), 0.09);
    const H = 0.035; // m: the nozzle's height over the sauce
    const worldOfLocal = (p) => plate.localToWorld(p.clone());
    const head = new THREE.Vector3();
    const tip = (rb, k) => { const i = Math.min(rb.segs, k * rb.segs); const a = Math.floor(i), f = i - a; head.lerpVectors(rb.pts[a], rb.pts[Math.min(rb.segs, a + 1)], f); return head; };
    const stream = streamFor(key, mat);
    const up = new THREE.Vector3(0, 1, 0);
    const steps = [];
    steps.push((next) => anim.add(0.28, (k) => node.position.lerpVectors(r0.p, lift, k), next));
    // carry to above the first ribbon's start
    steps.push((next) => {
      const p1 = lift.clone(), q1 = r0.q.clone();
      const startW = worldOfLocal(ribbons[0].pts[0]).addScaledVector(up, H + 0.03);
      anim.add(0.6, (k) => {
        const qq = new THREE.Quaternion().slerpQuaternions(q1, tilt, k);
        const nowTip = new THREE.Vector3().lerpVectors(node.parent.localToWorld(p1.clone().add(fx.clone().multiply(node.scale).applyQuaternion(q1))), startW, k).addScaledVector(up, Math.sin(k * Math.PI) * 0.06);
        holdAt(node, fx, nowTip, qq);
      }, next);
    });
    ribbons.forEach((rb, i) => {
      if (i > 0) steps.push((next) => {
        const a = worldOfLocal(ribbons[i - 1].pts.at(-1)).addScaledVector(up, H), b = worldOfLocal(rb.pts[0]).addScaledVector(up, H);
        anim.add(0.22, (k) => holdAt(node, fx, new THREE.Vector3().lerpVectors(a, b, k).addScaledVector(up, Math.sin(k * Math.PI) * 0.025), tilt), next);
      });
      steps.push((next) => {
        if (i === 0 || i % 2 === 0) sfx('squeeze');
        const dur = Math.min(1.1, 0.35 + rb.segs * 0.012);
        anim.add(dur, (k) => {
          const h = tip(rb, k);
          const hw = worldOfLocal(h);
          holdAt(node, fx, hw.clone().addScaledVector(up, H), tilt);
          // squeezed: the soft bottle narrows while it pipes
          const sq = 1 - 0.1 * Math.sin(Math.min(1, k * 1.2) * Math.PI);
          node.scale.set(sc0.x * sq, sc0.y, sc0.z * sq);
          rb.geo.setDrawRange(0, Math.floor(rb.segs * k) * rb.geo.userData.perSegment);
          const nz = node.localToWorld(fx.clone());
          stream?.set(nz, hw);
        }, () => { rb.geo.setDrawRange(0, Infinity); stream?.set(null); node.scale.copy(sc0); next(); });
      });
    });
    steps.push((next) => {
      const p1 = node.position.clone(), q1 = node.quaternion.clone();
      anim.add(0.7, (k) => { node.position.lerpVectors(p1, r0.p, k).addScaledVector(worldDirToParent(node, UP), Math.sin(k * Math.PI) * 0.08); node.quaternion.slerpQuaternions(q1, r0.q, k); }, () => {
        restore(node, r0); node.scale.copy(sc0); item.busy = false; items.settle?.(item); next();
      });
    });
    const on = records.length ? records.map((r) => esc((r.filling ? `${r.filling.item.info.label || 'Bratwurst'} im Brötchen` : r.item.info.label || r.item.label))).join(', ') : 'the empty plate';
    say(`<b>${esc(name)}</b> over ${on}. <em>${records.length ? 'Another sauce, some curry powder, or tap the plate to finish.' : 'A sausage would go nicely with it.'}</em>`);
    let i = 0;
    const go = () => { const s = steps[i++]; if (s) s(go); else done(); };
    go();
  }

  // ---------- 3. curry powder ----------
  const dustGeo = new THREE.IcosahedronGeometry(0.0011, 0);
  const dustMat = new THREE.MeshStandardMaterial({ name: 'item_curry_powder', color: 0xffffff, roughness: 0.95 });
  const falling = [];
  const _d = new THREE.Object3D();
  function dust(item, done) {
    if (dusts >= MAX_DUST) { say('That is plenty of curry powder. <em>Tap the plate to finish it.</em>'); done(); return; }
    const node = item.node;
    items.release(item);
    item.busy = true;
    dusts++;
    const r0 = rest(node), sc0 = node.scale.clone();
    const fx = (() => { let f = null; node.traverse((o) => { if (!f && /^fx_/.test(o.name)) f = o; }); return f ? poseIn(f, node).p : new THREE.Vector3(0, measure(node).box.max.y, 0); })();
    const colour = new THREE.Color(item.info.colour || '#c8781a');
    const N = lite ? 90 : 150;
    const inst = new THREE.InstancedMesh(dustGeo, dustMat, N);
    inst.name = 'item_curry_powder';
    inst.userData.itemFx = true;
    inst.raycast = () => {};
    inst.frustumCulled = false;
    inst.castShadow = false;
    const col = new THREE.Color();
    _d.position.set(0, 0, 0); _d.rotation.set(0, 0, 0); _d.scale.setScalar(0.0001); _d.updateMatrix();
    for (let i = 0; i < N; i++) inst.setMatrixAt(i, _d.matrix);
    for (let i = 0; i < N; i++) inst.setColorAt(i, col.copy(colour).offsetHSL((Math.random() - 0.5) * 0.03, 0, (Math.random() - 0.5) * 0.12));
    // where each grain settles: on top of what is on the plate, else on the plate
    const targets = [];
    const meshes = records.flatMap((r) => meshesOf(r));
    const down = new THREE.Vector3(0, -1, 0).transformDirection(plate.matrixWorld);
    const centre = records.length ? records.reduce((a, r) => a.add(r.group.position), new THREE.Vector3()).multiplyScalar(1 / records.length) : new THREE.Vector3();
    for (let i = 0; i < N; i++) {
      let p = null;
      for (let tries = 0; tries < 4 && !p; tries++) {
        const a = Math.random() * Math.PI * 2, r = Math.sqrt(Math.random()) * (records.length ? plateR * 0.75 : 0.035);
        const local = centre.clone().add(new THREE.Vector3(Math.cos(a) * r, 0.2, Math.sin(a) * r));
        ray.set(plate.localToWorld(local.clone()), down);
        ray.far = 0.4;
        const hit = ray.intersectObjects(meshes.length && Math.random() < 0.85 ? meshes : plateMeshes, false)[0] || ray.intersectObjects(plateMeshes, false)[0];
        if (hit) p = plate.worldToLocal(hit.point.clone());
      }
      targets.push(p || centre.clone().setY(0.003));
    }
    plate.add(inst);
    extras.push({ mesh: inst });
    const ev = { inst, targets, start: [], delay: [], dur: [], rot: [], scale: [], t: 0, live: true };
    for (let i = 0; i < N; i++) { ev.delay.push(0.15 + Math.random() * 0.8); ev.dur.push(0.3 + Math.random() * 0.25); ev.rot.push(new THREE.Euler(Math.random() * 6, Math.random() * 6, Math.random() * 6)); ev.scale.push(0.6 + Math.random() * 0.8); ev.start.push(null); }
    // the tin: over the plate, lid down, four shakes
    const frontP = worldDirToParent(node, front).normalize();
    const axis = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), frontP).normalize();
    const tilt = new THREE.Quaternion().setFromAxisAngle(axis, Math.PI * 0.78).multiply(r0.q);
    const up = new THREE.Vector3(0, 1, 0);
    const over = plate.localToWorld(centre.clone().setY(0.13));
    const nowLid = () => node.localToWorld(fx.clone());
    const pin = (w, q) => holdAt(node, fx, w, q);
    const lift = r0.p.clone().addScaledVector(worldDirToParent(node, UP), 0.08);
    say(`<b>${esc(item.info.label || 'Currypulver')}</b>, shaken over ${records.length ? 'the plate' : 'the empty plate'}. <em>${records.length ? 'Tap the plate when it looks right.' : 'Now something to put it on?'}</em>`);
    anim.add(0.25, (k) => node.position.lerpVectors(r0.p, lift, k), () => {
      const a = nowLid(), q1 = node.quaternion.clone();
      anim.add(0.55, (k) => pin(new THREE.Vector3().lerpVectors(a, over, k).addScaledVector(up, Math.sin(k * Math.PI) * 0.05), new THREE.Quaternion().slerpQuaternions(q1, tilt, k)), () => {
        sfx('shake');
        ev.emitFrom = () => nowLid();
        falling.push(ev);
        const side = new THREE.Vector3(1, 0, 0).applyQuaternion(plate.getWorldQuaternion(new THREE.Quaternion()));
        anim.add(0.95, (k) => {
          const s = Math.sin(k * Math.PI * 8);
          pin(over.clone().addScaledVector(side, s * 0.014).addScaledVector(up, Math.abs(s) * 0.006), tilt.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), s * 0.12)));
        }, () => {
          const p1 = node.position.clone(), q2 = node.quaternion.clone();
          anim.add(0.6, (k) => { node.position.lerpVectors(p1, r0.p, k).addScaledVector(worldDirToParent(node, UP), Math.sin(k * Math.PI) * 0.06); node.quaternion.slerpQuaternions(q2, r0.q, k); }, () => {
            restore(node, r0); node.scale.copy(sc0); item.busy = false; items.settle?.(item);
            if (motion?.reduced) settleDust(ev);
            done();
          });
        });
      });
    });
    if (motion?.reduced) settleDust(ev);
  }
  function settleDust(ev) {
    for (let i = 0; i < ev.targets.length; i++) {
      _d.position.copy(ev.targets[i]); _d.rotation.copy(ev.rot[i]); _d.scale.setScalar(ev.scale[i]); _d.updateMatrix();
      ev.inst.setMatrixAt(i, _d.matrix);
    }
    ev.inst.instanceMatrix.needsUpdate = true;
    ev.live = false;
    const k = falling.indexOf(ev);
    if (k >= 0) falling.splice(k, 1);
  }
  function stepDust(dt) {
    for (const ev of [...falling]) {
      ev.t += dt;
      let all = true;
      for (let i = 0; i < ev.targets.length; i++) {
        const t = (ev.t - ev.delay[i]) / ev.dur[i];
        if (t < 0) { all = false; _d.scale.setScalar(0.0001); _d.position.set(0, 0, 0); _d.updateMatrix(); ev.inst.setMatrixAt(i, _d.matrix); continue; }
        if (!ev.start[i]) ev.start[i] = plate.worldToLocal(ev.emitFrom()).add(new THREE.Vector3((Math.random() - 0.5) * 0.012, 0, (Math.random() - 0.5) * 0.012));
        const k = Math.min(1, t);
        if (k < 1) all = false;
        const s = ev.start[i], e = ev.targets[i];
        _d.position.set(s.x + (e.x - s.x) * k, s.y + (e.y - s.y) * k * k, s.z + (e.z - s.z) * k);
        _d.rotation.set(ev.rot[i].x + ev.t * 4, ev.rot[i].y, ev.rot[i].z + ev.t * 3);
        _d.scale.setScalar(ev.scale[i]);
        _d.updateMatrix();
        ev.inst.setMatrixAt(i, _d.matrix);
      }
      ev.inst.instanceMatrix.needsUpdate = true;
      if (all) settleDust(ev);
    }
  }

  // ---------- 4. the plate handed over ----------
  function wobble() {
    if (plateItem.busy) return;
    const r0 = rest(plate);
    const ax = worldDirToParent(plate, front).normalize();
    const side = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), ax).normalize();
    anim.add(0.45, (k) => { plate.quaternion.copy(r0.q).multiply(new THREE.Quaternion().setFromAxisAngle(side, Math.sin(k * Math.PI * 3) * 0.05 * (1 - k))); }, () => restore(plate, r0));
  }
  function describe() {
    return records.map((r) => {
      const base = r.filling ? `${r.filling.item.info.label || 'Bratwurst'} im Brötchen` : (r.item.info.label || r.item.label);
      const s = [...new Set([...(r.sauces || []), ...(r.filling?.sauces || [])])].map((k) => SAUCE_NAMES[k] || k);
      return esc(base) + (s.length ? ` with ${esc(s.join(' and '))}` : '');
    }).join(', ');
  }
  function clear(done, { quiet = false } = {}) {
    if (!records.length && !extras.length) {
      if (!quiet) say('The plate is empty. <em>Tap a sausage or the Brötchen on the board, then a bottle for sauce.</em>');
      wobble();
      done?.();
      return;
    }
    items.release(plateItem);
    plateItem.busy = true;
    const what = describe();
    const r0 = rest(plate), sc0 = plate.scale.clone();
    const out = worldDirToParent(plate, front.clone().multiplyScalar(0.42).add(new THREE.Vector3(0, 0.1, 0)));
    if (!quiet) {
      say(`${esc(info.clear_note || 'Guten Appetit')}! ${what ? `${what}, handed over the counter.` : 'Handed over the counter.'} <em>A fresh plate is set down.</em>`);
      crowdSay?.(`${info.clear_note || 'Guten Appetit'}!`, place.center.clone().setY(0), 9);
    }
    sfx('plate');
    anim.add(0.75, (k) => { plate.position.copy(r0.p).addScaledVector(out, k); plate.scale.copy(sc0).multiplyScalar(1 - k * 0.85); }, () => {
      for (const r of records) { r.group.removeFromParent(); for (const e of r.extra || []) { e.removeFromParent(); e.geometry.dispose(); } if (r.filling) for (const e of r.filling.extra || []) { e.removeFromParent(); e.geometry.dispose(); } }
      for (const e of extras) { e.mesh.removeFromParent(); if (e.mesh.isInstancedMesh) e.mesh.dispose(); else e.mesh.geometry.dispose(); }
      for (const ev of falling.splice(0)) ev.live = false;
      records.length = 0; extras.length = 0; dusts = 0;
      spots.forEach((s) => (s.used = null));
      restore(plate, r0);
      plate.scale.copy(sc0).multiplyScalar(0.001);
      anim.add(0.35, (k) => plate.scale.copy(sc0).multiplyScalar(Math.max(0.001, k)), () => { plate.scale.copy(sc0); plateItem.busy = false; items.settle?.(plateItem); done?.(); }, 0.35);
    });
  }

  // ---------- the visitor's clicks, queued ----------
  const api = {
    records,
    /** A board item (sausage or roll) to the plate. */
    plate: (item) => enqueue((next) => toPlate(item, { done: next })),
    sauce: (item) => enqueue((next) => sauce(item, next)),
    dust: (item) => enqueue((next) => dust(item, next)),
    clear: () => enqueue((next) => clear(next)),
    /** "One in a bun, please": a Brötchen to the plate, a Thüringer into it, a line of Senf over it. */
    bun(onDone) {
      const roll = wurstItems.find((i) => i.kind === 'roll' || i.info.wurst === 'roll');
      const wurst = wurstItems.find((i) => i.info.wurst === 'thueringer') || wurstItems.find((i) => ['krakauer', 'nuernberger'].includes(i.info.wurst));
      const senf = sauceItems.find((i) => (i.info.sauce || '') === 'senf') || sauceItems[0];
      if (!roll || !wurst) return false;
      const waiting = records.find((r) => r.kind === 'roll' && !r.filling);
      if (!waiting) {
        // room for a roll: else hand the plate over first
        if (!placeFor('roll', measure(roll.node))) enqueue((next) => clear(next, { quiet: true }));
        enqueue((next) => toPlate(roll, { quiet: true, done: next }));
      }
      enqueue((next) => toPlate(wurst, { quiet: true, done: next }));
      if (senf) enqueue((next) => sauce(senf, next));
      enqueue((next) => { onDone?.(); next(); });
      return true;
    },
    /** Rolls with a sausage in them on the plate. */
    buns: () => records.filter((r) => r.kind === 'roll' && r.filling).length,
    busy: () => running,
    update(dt) { stepDust(dt); },
    /** For tests and the panel: what is on the plate. */
    stats: () => ({
      items: records.map((r) => ({ kind: r.kind, spots: r.spots.map((s) => s.name), filling: r.filling?.kind || null, sauces: [...r.sauces, ...(r.filling?.sauces || [])] })),
      extras: extras.map((e) => (e.sauce ? `sauce:${e.sauce}` : 'powder')),
      sauceLines: plate.children.filter((o) => /^item_sauce_/.test(o.name)).length,
      powder: plate.children.filter((o) => o.name === 'item_curry_powder').length,
      busy: running, queued: queue.length,
      max: maxItems,
    }),
  };
  return api;
}
