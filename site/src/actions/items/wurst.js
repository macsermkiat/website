// The Bratwurst stand (round 10, ADR 0004 revision "Bratwurst plate instead of many sausages"). Mac: "no need to
// be able to flip lots of sausages, just a few different kinds is enough. But if it's able to mix on a plate and
// put on sauce, that must be nice."
//
// Four kinds stand on the vendor's serving board (act_wurst_thueringer, _nuernberger (a trio), _krakauer, _curry)
// with a Brötchen (act_roll). Tapping one tosses a fresh copy onto the paper plate (act_plate), to the next free
// plate_spot_<n>, four at most, piling up where it lands. The three squeeze bottles (act_sauce_senf, _ketchup,
// _curry) lift off the counter, turn over above the plate and pipe a glossy squiggle from their fx_sauce_ nozzle
// over whatever is on it (a dollop on the side of an empty plate). The curry tin (act_shaker_curry) shakes powder
// over the food. Tapping the plate hands it over the counter: "Guten Appetit". The actions follow items.json
// (`action`: plate, sauce, dust, clear). A Thüringer or a Krakauer tapped while an empty Brötchen waits on the
// plate goes into it. The grill swings on its tripod, the coals glow, and smoke drifts.
//
// The sausages on the grill are scenery, not clickable one by one, but the prototype's "Turn the sausages" stays: the
// panel button turns the whole grate in a ripple, tongs-style, each sausage hopping over about its own length
// (grillSausages.js cuts the vendor's merged `sausages_grill` mesh into its sausages for that).
import * as THREE from 'three';
import { boxOf, rest, restore, worldDirToParent, createSparks, createStream, UP, esc } from './common.js';
import { createGrillSausages } from './grillSausages.js';
import { createEmitter } from '../effects.js';
import { act, acts, findNode, counterLocal, toLocal, worldOf } from '../util.js';
import { actionNote, crowdLine } from '../../content.js';

/** What a node of the plate set is, by name (items.json's `kind` wins when it has one). */
const KIND_OF = (name) => (/^act_wurst_/.test(name) ? 'wurst' : name === 'act_roll' ? 'roll' : /^act_sauce_/.test(name) ? 'sauce' : /^act_shaker_/.test(name) ? 'spice' : name === 'act_plate' ? 'plate' : null);
const SAUCE = { senf: '#d6a21c', ketchup: '#a8140e', curry: '#b4400e' };
const SAUCE_NAME = { senf: 'Senf', ketchup: 'Ketchup', curry: 'Currysauce' };
const WURST_NAME = { thueringer: 'Thüringer', nuernberger: 'Nürnberger', krakauer: 'Krakauer', curry: 'Currywurst', roll: 'Brötchen' };
const RIM = 0.1; // metres from the plate's centre that food may reach (a long Thüringer hangs over it, as they do)
const MAX_SAUCES = 8;

export function createWurst(ctx) {
  const { market, anim, scene, sfx, say, crowdSay, items, lite, motion, camera } = ctx;
  const place = market.places.wurst;
  if (!place) return {};
  const sparks = createSparks(scene, 30);

  // ---------- the grill: coals, smoke, the swinging grate, a warm flicker ----------
  let flare = 0, grillLight = null, swing = null;
  const grillMats = [];
  const grill = act(place, 'act_grill') || findNode(place, /grill|coals|ember/i, { mesh: true });
  const sw = act(place, 'act_grill_swing');
  if (sw) swing = { node: sw, q0: sw.quaternion.clone(), e: new THREE.Euler(), q: new THREE.Quaternion() };
  const c = counterLocal(place);
  const smokeSrc = act(place, 'act_smoke') || findNode(place, /^smoke/i) || grill;
  const sp = smokeSrc ? worldOf(place, smokeSrc).add(new THREE.Vector3(0, smokeSrc === grill ? 0.12 : 0, 0)) : worldOf(place, [c.x, c.y + 0.25, c.z - 0.05]);
  const smoke = createEmitter(scene, sp, { color: 0xbab4bc, n: 16, rise: 3.2, spread: 0.9, scale: 1.5, opacity: 0.28 });
  const coalRoot = findNode(place, /^coals/i) || grill;
  coalRoot?.traverse((o) => {
    if (!o.isMesh) return;
    o.material = o.material.clone();
    o.material.userData.baseEmissive = o.material.emissiveIntensity || 1;
    if (o.material.emissive && o.material.emissive.getHex() === 0) o.material.emissive.set(0xff5a14);
    grillMats.push(o.material);
  });
  if (!lite) {
    grillLight = new THREE.PointLight(0xff5a1a, 4, 5, 2);
    grillLight.name = 'engine_grill_light';
    grillLight.position.copy(toLocal(place, sp)).add(new THREE.Vector3(0, 0.2, 0.3));
    place.holder.add(grillLight);
  }
  function fatFlare(n = 1) {
    flare = Math.min(2.2, flare + 0.8 * n);
    if (grill) sparks.burst(sp.clone().add(new THREE.Vector3(0, -0.06, 0)), Math.round(6 * n));
    smoke.boost = Math.max(smoke.boost || 0, 0.9 * n);
  }

  // ---------- turning the sausages on the grill (the panel button) ----------
  const grillRoots = [];
  place.root.traverse((o) => { if (/^sausages_grill/.test(o.name) && !grillRoots.some((r) => r === o.parent || r.getObjectById(o.id))) grillRoots.push(o); });
  const grillS = grillRoots.length ? createGrillSausages(grillRoots, { anim }) : null;
  let turns = 0;
  const TURN_NOTES = ['Turned. Nicely browned on this side.', 'The coals flare up and the smoke drifts over the crowd.', 'Almost ready. Mustard or ketchup?'];
  function turnAll() {
    const n = turns++;
    const note = actionNote('wurst', 'turn', TURN_NOTES[n % 3], { n });
    sfx('sizzle');
    fatFlare(1.2);
    if (!grillS) { say(note); return false; }
    // a ripple along the grate, left to right; reduced motion turns them all at once
    let turned = 0;
    grillS.list.forEach((_, i) => grillS.turn(i, { delay: motion.reduced ? 0 : i * 0.09, done: () => { if (++turned === grillS.list.length) fatFlare(0.5); } }));
    say(`${note} <em>(${grillS.list.length} on the grate${n ? `, turned ${n + 1}×` : ''})</em>`);
    return true;
  }

  // ---------- the plate set ----------
  const reg = (node) => {
    if (!node) return null;
    return items.of('wurst').find((i) => i.node === node) || items.add(node, 'wurst', place, KIND_OF(node.name));
  };
  const kinds = [...acts(place, 'act_wurst_'), act(place, 'act_roll')].map(reg).filter(Boolean);
  const sauces = acts(place, 'act_sauce_').map(reg).filter(Boolean);
  const shaker = reg(acts(place, 'act_shaker_')[0] || null);
  const plateItem = reg(act(place, 'act_plate'));
  const P = plateItem ? {
    node: plateItem.node,
    max: +plateItem.info.max_items || 4,
    spots: (plateItem.info.spots || [0, 1, 2, 3].map((i) => `plate_spot_${i}`)).map((n) => plateItem.node.getObjectByName(n)).filter(Boolean),
    food: [], // { g, key, box (plate-local), landed }
    sauces: [], // { mesh, key }
    dust: [], // { points, n }
    served: 0,
    gen: 0, // the plate's generation: a clear takes everything tapped onto it before the clear
  } : null;
  if (P && !P.spots.length) [[-0.042, -0.036], [0.042, -0.036], [-0.042, 0.036], [0.042, 0.036]].forEach(([x, z], i) => { const s = new THREE.Object3D(); s.name = `plate_spot_${i}`; s.position.set(x, 0.002, z); P.node.add(s); P.spots.push(s); });
  const keyOf = (item) => item.info.wurst || item.info.sauce || item.node.name.replace(/^act_(wurst_|sauce_)?/, '');
  const cur = () => P.food.filter((f) => f.gen === P.gen);
  const nameOf = (item) => WURST_NAME[keyOf(item)] || item.info.label || item.label;

  // one thing at a time on the plate: a toss lands before the sauce goes over it
  const queue = [];
  let running = false;
  function enqueue(fn) {
    if (queue.length > 6) return;
    queue.push(fn);
    if (!running) next();
  }
  function next() {
    const fn = queue.shift();
    if (!fn) { running = false; return; }
    running = true;
    let finished = false;
    try { fn(() => { if (finished) return; finished = true; next(); }); } catch (e) { console.warn('[market] plate action failed', e); finished = true; next(); }
  }

  // ---------- helpers in the plate's frame ----------
  const _m = new THREE.Matrix4();
  const plateInv = () => { P.node.updateWorldMatrix(true, false); return _m.copy(P.node.matrixWorld).invert(); };
  const plateToWorld = (v) => P.node.localToWorld(v.clone());
  const ray = new THREE.Raycaster();
  /** The top surface of the plate and what is on it at (x, z), plate-local; null when the ray misses. */
  function topAt(x, z, targets) {
    const from = plateToWorld(new THREE.Vector3(x, 0.5, z));
    const to = plateToWorld(new THREE.Vector3(x, -0.05, z));
    ray.set(from, to.sub(from).normalize());
    ray.far = 0.6;
    const hit = ray.intersectObjects(targets, false)[0];
    return hit ? P.node.worldToLocal(hit.point.clone()).y : null;
  }
  const surfaceMeshes = () => { const out = []; P.node.traverse((o) => { if (o.isMesh && !o.userData.noHit && o.visible) out.push(o); }); return out; };
  const foodBox = () => { const b = new THREE.Box3(); for (const f of P.food) if (f.landed) b.union(f.box); return b; };

  /** A copy of an item's meshes, as a group whose frame is the item's own (its base). */
  function copyOf(src) {
    src.updateWorldMatrix(true, true);
    const inv = new THREE.Matrix4().copy(src.matrixWorld).invert();
    const g = new THREE.Group();
    g.name = `item_on_plate_${src.name.replace(/^act_/, '')}`;
    const local = new THREE.Box3();
    src.traverse((o) => {
      if (!o.isMesh || o.userData.itemFx || o.userData.mergedItems) return;
      const m = new THREE.Mesh(o.geometry, o.material);
      m.matrixAutoUpdate = false;
      m.matrix.multiplyMatrices(inv, o.matrixWorld);
      m.castShadow = !lite;
      m.receiveShadow = !lite;
      g.add(m);
      if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
      local.union(o.geometry.boundingBox.clone().applyMatrix4(m.matrix));
    });
    return { g, local };
  }

  // ---------- 1. a kind onto the plate ----------
  let tossN = 0;
  function toPlate(item, { onto = null, quiet = false } = {}) {
    if (!P) return;
    if (cur().length >= P.max) {
      wiggle();
      say(`The plate is full (${P.max} at most). Tap the plate: <em>${esc(plateItem.info.clear_note || 'Guten Appetit')}!</em>`);
      return;
    }
    const key = keyOf(item);
    // a long sausage goes into a Brötchen that waits empty on the plate
    if (!onto && (key === 'thueringer' || key === 'krakauer')) onto = cur().find((f) => f.key === 'roll' && !f.filled) || null;
    if (onto) onto.filled = true;
    const entry = { key, g: null, box: null, landed: false, gen: P.gen, onto: onto ? onto.key : null };
    P.food.push(entry); // the spot is taken at the tap
    const n = cur().length;
    const spot = P.spots[Math.min(n - 1, P.spots.length - 1)];
    if (!quiet) say(onto ? `<b>${esc(item.info.name || nameOf(item))}</b> into the Brötchen. A sauce on it? Senf, Ketchup or Currysauce.` : `<b>${esc(item.info.name || nameOf(item))}</b> on the plate${n > 1 ? ` (${n} of ${P.max})` : ''}. ${n === 1 ? 'A sauce next? Senf, Ketchup or Currysauce.' : esc(item.info.detail || '')}`);
    enqueue((done) => {
      items.release(item);
      const src = item.node, r0 = rest(src);
      // the tapped one bobs as the vendor takes a fresh one from behind it
      const up = worldDirToParent(src, UP);
      anim.add(0.32, (k) => src.position.copy(r0.p).addScaledVector(up, Math.sin(k * Math.PI) * 0.025), () => restore(src, r0));
      const { g, local } = copyOf(src);
      entry.g = g;
      const inv = plateInv();
      const m0 = new THREE.Matrix4().multiplyMatrices(inv, src.matrixWorld);
      const p0 = new THREE.Vector3(), q0 = new THREE.Quaternion(), s0 = new THREE.Vector3();
      m0.decompose(p0, q0, s0);
      P.node.add(g);
      g.position.copy(p0); g.quaternion.copy(q0); g.scale.copy(s0);
      // where it lands: at the spot, kept on the plate, on top of whatever is already there
      const size = local.getSize(new THREE.Vector3()).multiply(s0), ctr = local.getCenter(new THREE.Vector3()).multiply(s0);
      const hx = size.x / 2, hz = size.z / 2;
      const yaw = onto ? 0 : (((tossN++ * 0.618) % 1) - 0.5) * 0.3;
      let x, z, floor;
      if (onto?.box) {
        const ob = onto.box.getCenter(new THREE.Vector3());
        x = ob.x; z = ob.z;
        floor = onto.box.max.y - (onto.box.max.y - onto.box.min.y) * 0.45;
      } else {
        const mx = Math.max(0, RIM - hx), mz = Math.max(0, RIM - hz);
        x = THREE.MathUtils.clamp(spot.position.x, -mx, mx);
        z = THREE.MathUtils.clamp(spot.position.z, -mz, mz);
        floor = spot.position.y;
        for (const f of P.food) {
          if (!f.box || f === entry) continue;
          const ox = Math.min(x + hx, f.box.max.x) - Math.max(x - hx, f.box.min.x), oz = Math.min(z + hz, f.box.max.z) - Math.max(z - hz, f.box.min.z);
          if (ox > 0.01 && oz > 0.006) floor = Math.max(floor, f.box.max.y - (f.box.max.y - f.box.min.y) * 0.3);
        }
      }
      const p1 = new THREE.Vector3(x - ctr.x, floor - local.min.y * s0.y, z - ctr.z);
      const q1 = new THREE.Quaternion().setFromAxisAngle(UP, yaw);
      entry.box = new THREE.Box3(new THREE.Vector3(x - hx, floor, z - hz), new THREE.Vector3(x + hx, floor + size.y, z + hz));
      // a toss: up and over, a sausage turning once about its length on the way
      const spin = key !== 'curry' && key !== 'roll';
      const qs = new THREE.Quaternion(), ax = new THREE.Vector3(1, 0, 0);
      const arc = 0.1 + p0.distanceTo(p1) * 0.22;
      if (key !== 'roll') { sfx('sizzle'); fatFlare(0.6); }
      anim.add(0.85, (k) => {
        g.position.lerpVectors(p0, p1, k).y += Math.sin(k * Math.PI) * arc;
        g.quaternion.slerpQuaternions(q0, q1, k);
        if (spin) g.quaternion.multiply(qs.setFromAxisAngle(ax, k * Math.PI * 2));
      }, () => {
        g.position.copy(p1); g.quaternion.copy(q1);
        entry.landed = true;
        sfx('plate');
        // it settles with a small bounce
        anim.add(0.22, (k) => { g.position.y = p1.y + Math.sin(k * Math.PI) * 0.006; }, () => { g.position.y = p1.y; done(); });
      });
    });
  }

  // ---------- 2. sauce from a squeeze bottle ----------
  const sauceMats = {};
  function sauceMat(key, colour) {
    if (sauceMats[key]) return sauceMats[key];
    const col = new THREE.Color(colour);
    const m = lite
      ? new THREE.MeshStandardMaterial({ name: `item_sauce_${key}`, color: col, roughness: 0.28, emissive: col.clone().multiplyScalar(0.06) })
      : new THREE.MeshPhysicalMaterial({ name: `item_sauce_${key}`, color: col, roughness: 0.32, clearcoat: 1, clearcoatRoughness: 0.06, emissive: col.clone().multiplyScalar(0.05) });
    return (sauceMats[key] = m);
  }
  const streams = {};
  /** The squiggle's path (plate-local), draped over the food: a zigzag along it, or a swirl on an empty plate. */
  function saucePath(R) {
    const targets = surfaceMeshes();
    const fb = foodBox();
    const pts = [];
    if (fb.isEmpty()) {
      const cx = 0.05, cz = 0.025;
      for (let i = 0; i <= 30; i++) { const a = (i / 30) * Math.PI * 3.4, r = 0.004 + (i / 30) * 0.013; pts.push(new THREE.Vector3(cx + Math.cos(a) * r, 0, cz + Math.sin(a) * r)); }
    } else {
      let x0 = fb.min.x + 0.014, x1 = fb.max.x - 0.014;
      if (x1 - x0 < 0.05) { const m = (x0 + x1) / 2; x0 = m - 0.03; x1 = m + 0.03; }
      const zc = (fb.min.z + fb.max.z) / 2, amp = THREE.MathUtils.clamp((fb.max.z - fb.min.z) / 2 - 0.008, 0.007, 0.028);
      const periods = Math.max(2, Math.round((x1 - x0) / 0.034)), N = 22 + periods * 10;
      const ph = P.sauces.length * 0.9; // each new line crosses the last
      for (let i = 0; i < N; i++) { const t = i / (N - 1); pts.push(new THREE.Vector3(x0 + t * (x1 - x0), 0, zc + amp * Math.sin(t * periods * Math.PI * 2 + ph))); }
    }
    const raw = pts.map((p) => topAt(p.x, p.z, targets) ?? 0.004);
    pts.forEach((p, i) => { const s = (raw[Math.max(0, i - 1)] + raw[i] + raw[Math.min(raw.length - 1, i + 1)]) / 3; p.y = Math.max(raw[i], s) + R * 0.7; });
    return pts;
  }
  function squeeze(item, { quiet = false } = {}) {
    if (!P) return;
    const key = item.info.sauce || keyOf(item);
    const label = SAUCE_NAME[key] || item.info.label || key;
    if (P.sauces.length >= MAX_SAUCES) { say(`That is plenty of sauce. Tap the plate: <em>${esc(plateItem.info.clear_note || 'Guten Appetit')}!</em>`); return; }
    enqueue((done) => {
      const fb = foodBox();
      const on = P.food.filter((f) => f.landed).map((f) => WURST_NAME[f.key] || f.key);
      if (!quiet) say(on.length ? `<b>${esc(label)}</b> over the ${esc(listOf([...new Set(on)]))}.` : `A dollop of <b>${esc(label)}</b> on the side of the empty plate. Something to dip in it?`);
      items.release(item);
      const bottle = item.node, r0 = rest(bottle), s0 = bottle.scale.clone();
      const fx = bottle.getObjectByName(item.info.fx || `fx_sauce_${key}`);
      const nozzle = (fx ? fx.position.clone() : new THREE.Vector3(0, 0.2165, 0)).multiply(s0);
      const R = fb.isEmpty() ? 0.0034 : 0.0028;
      const pts = saucePath(R);
      const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
      const tube = new THREE.TubeGeometry(curve, pts.length * 3, R, lite ? 5 : 7, false);
      const mesh = new THREE.Mesh(tube, sauceMat(key, item.info.colour || SAUCE[key] || '#a8140e'));
      mesh.name = `item_sauce_${key}`;
      mesh.castShadow = false;
      tube.setDrawRange(0, 0);
      P.node.add(mesh);
      P.sauces.push({ mesh, key });
      const stream = (streams[key] ||= createStream(scene, mesh.material, R * 0.55));
      // the bottle, turned nozzle-down (about its own X, leaning towards the visitor)
      const qInv = r0.q.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI * 0.86));
      const toParent = (v) => bottle.parent.worldToLocal(plateToWorld(v));
      const baseFor = (nozzlePlate, q) => toParent(nozzlePlate).sub(nozzle.clone().applyQuaternion(q));
      const hover = 0.045;
      const start = baseFor(pts[0].clone().add(new THREE.Vector3(0, hover, 0)), qInv);
      const head = new THREE.Vector3(), tmp = new THREE.Vector3(), nzW = new THREE.Vector3();
      const total = tube.index.count;
      anim.add(0.75, (k) => {
        bottle.position.lerpVectors(r0.p, start, k).addScaledVector(worldDirToParent(bottle, UP), Math.sin(k * Math.PI) * 0.1);
        bottle.quaternion.slerpQuaternions(r0.q, qInv, k);
      }, () => {
        sfx('squeeze');
        anim.add(1.25, (k) => {
          curve.getPointAt(Math.min(1, k), head);
          bottle.position.copy(baseFor(tmp.copy(head).setY(head.y + hover), qInv));
          bottle.quaternion.copy(qInv);
          // pressed: the sides give a little
          const sq = Math.sin(Math.min(1, k * 1.15) * Math.PI);
          bottle.scale.set(s0.x * (1 - 0.1 * sq), s0.y * (1 + 0.02 * sq), s0.z * (1 - 0.1 * sq));
          tube.setDrawRange(0, Math.floor((total * k) / 3) * 3);
          bottle.updateWorldMatrix(true, true);
          if (fx) fx.getWorldPosition(nzW); else nzW.copy(bottle.localToWorld(nozzle.clone()));
          stream.set(k < 0.995 ? nzW : null, plateToWorld(head));
        }, () => {
          tube.setDrawRange(0, Infinity);
          stream.set(null);
          bottle.scale.copy(s0);
          anim.add(0.7, (k) => {
            bottle.position.lerpVectors(start, r0.p, k).addScaledVector(worldDirToParent(bottle, UP), Math.sin(k * Math.PI) * 0.08);
            bottle.quaternion.slerpQuaternions(qInv, r0.q, k);
          }, () => { restore(bottle, r0); done(); });
        });
      });
    });
  }

  // ---------- 3. curry powder from the tin ----------
  let dotTex = null;
  function speckTexture() {
    if (dotTex) return dotTex;
    const cv = document.createElement('canvas');
    cv.width = cv.height = 16;
    const g = cv.getContext('2d');
    g.fillStyle = '#fff';
    g.beginPath(); g.arc(8, 8, 6.5, 0, Math.PI * 2); g.fill();
    return (dotTex = new THREE.CanvasTexture(cv));
  }
  let dusting = null; // { pts, from[], to[], t0[], t, points }
  function dust(item) {
    if (!P) return;
    enqueue((done) => {
      const fb = foodBox();
      say(fb.isEmpty() ? 'A shake of <b>curry powder</b> over the empty plate. Better with a Currywurst under it.' : 'A dusting of <b>curry powder</b>, the Berlin way.');
      items.release(item);
      const tin = item.node, r0 = rest(tin);
      const fx = tin.getObjectByName(item.info.fx || 'fx_shaker_curry');
      const lid = (fx ? fx.position.clone() : new THREE.Vector3(0, 0.1, 0)).multiply(tin.scale);
      const centre = fb.isEmpty() ? new THREE.Vector3(0, 0.004, 0) : fb.getCenter(new THREE.Vector3()).setY(fb.max.y);
      const qTilt = r0.q.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI * 0.72));
      const lidAt = centre.clone().add(new THREE.Vector3(0, 0.09, 0.012));
      const base = tin.parent.worldToLocal(plateToWorld(lidAt)).sub(lid.clone().applyQuaternion(qTilt));
      const shakeDir = worldDirToParent(tin, UP).multiplyScalar(0.016);
      // where the powder lands: scattered over the food, thickest in the middle
      const n = lite ? 120 : 220;
      const targets = surfaceMeshes();
      const rx = fb.isEmpty() ? 0.05 : Math.max(0.03, (fb.max.x - fb.min.x) / 2), rz = fb.isEmpty() ? 0.04 : Math.max(0.025, (fb.max.z - fb.min.z) / 2);
      const to = [], t0 = [];
      let s = 7 + P.dust.length * 31;
      const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
      for (let i = 0; i < n; i++) {
        const a = rnd() * Math.PI * 2, r = Math.sqrt(rnd()) * (0.55 + 0.45 * rnd());
        const x = centre.x + Math.cos(a) * r * rx, z = centre.z + Math.sin(a) * r * rz;
        to.push(new THREE.Vector3(x, (topAt(x, z, targets) ?? 0.003) + 0.0012, z));
        t0.push((i / n) * 0.95);
      }
      const geo = new THREE.BufferGeometry();
      const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
      const cBase = new THREE.Color(item.info.colour || '#c8781a');
      for (let i = 0; i < n; i++) { const k = 0.75 + rnd() * 0.45; col[i * 3] = Math.min(1, cBase.r * k); col[i * 3 + 1] = cBase.g * k * (0.85 + rnd() * 0.2); col[i * 3 + 2] = cBase.b * k; }
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      geo.setDrawRange(0, 0);
      const points = new THREE.Points(geo, new THREE.PointsMaterial({ name: 'item_curry_powder', size: 0.0065, vertexColors: true, map: speckTexture(), alphaTest: 0.5, sizeAttenuation: true }));
      points.name = 'item_curry_powder';
      points.userData.noHit = true;
      points.frustumCulled = false;
      P.node.add(points);
      P.dust.push({ points, n });
      const from = [];
      const settleAll = () => { for (let i = 0; i < n; i++) to[i].toArray(pos, i * 3); geo.setDrawRange(0, n); geo.attributes.position.needsUpdate = true; dusting = null; };
      anim.add(0.7, (k) => {
        tin.position.lerpVectors(r0.p, base, k).addScaledVector(worldDirToParent(tin, UP), Math.sin(k * Math.PI) * 0.08);
        tin.quaternion.slerpQuaternions(r0.q, qTilt, k);
      }, () => {
        sfx('shake');
        if (motion.reduced) settleAll();
        else dusting = { n, to, t0, from, t: 0, pos, geo, lidOf: () => { tin.updateWorldMatrix(true, true); return P.node.worldToLocal(fx ? fx.getWorldPosition(new THREE.Vector3()) : tin.localToWorld(lid.clone())); } };
        anim.add(1.05, (k) => {
          tin.position.copy(base).addScaledVector(shakeDir, Math.sin(k * Math.PI * 8) * Math.sin(k * Math.PI));
          tin.quaternion.copy(qTilt);
        }, () => {
          anim.add(0.65, (k) => {
            tin.position.lerpVectors(base, r0.p, k).addScaledVector(worldDirToParent(tin, UP), Math.sin(k * Math.PI) * 0.06);
            tin.quaternion.slerpQuaternions(qTilt, r0.q, k);
          }, () => { restore(tin, r0); if (dusting) settleAll(); done(); });
        });
      });
    });
  }
  function stepDust(dt) {
    const d = dusting;
    if (!d) return;
    d.t += dt;
    const FALL = 0.32;
    let shown = 0;
    const lidP = d.lidOf();
    for (let i = 0; i < d.n; i++) {
      if (d.t < d.t0[i]) break;
      if (!d.from[i]) d.from[i] = lidP.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.01, 0, (Math.random() - 0.5) * 0.01));
      const u = Math.min(1, (d.t - d.t0[i]) / FALL);
      const f = d.from[i], t = d.to[i];
      d.pos[i * 3] = f.x + (t.x - f.x) * u;
      d.pos[i * 3 + 1] = f.y + (t.y - f.y) * u * u;
      d.pos[i * 3 + 2] = f.z + (t.z - f.z) * u;
      shown = i + 1;
    }
    d.geo.setDrawRange(0, shown);
    d.geo.attributes.position.needsUpdate = true;
  }

  // ---------- 4. the plate handed over: Guten Appetit ----------
  function wiggle() {
    if (!P || P.node.userData.wiggling) return;
    const r0 = rest(P.node);
    P.node.userData.wiggling = true;
    anim.add(0.4, (k) => P.node.quaternion.copy(r0.q).multiply(new THREE.Quaternion().setFromAxisAngle(UP, Math.sin(k * Math.PI * 4) * 0.06 * (1 - k))), () => { restore(P.node, r0); P.node.userData.wiggling = false; });
  }
  function clearPlate({ quiet = false } = {}) {
    if (!P) return;
    if (!cur().length && !P.sauces.length && !P.dust.length) {
      if (!quiet) { wiggle(); say('The plate is empty. Tap a sausage on the board to put one on it.'); }
      return;
    }
    const upTo = P.gen++;
    enqueue((done) => {
      items.release(plateItem);
      const plate = P.node, r0 = rest(plate);
      const out = camera ? camera.position.clone().sub(plate.getWorldPosition(new THREE.Vector3())) : new THREE.Vector3(0, 0.3, 0.6);
      const outL = worldDirToParent(plate, out.multiplyScalar(0.3));
      const lift = worldDirToParent(plate, UP);
      P.served++;
      const note = plateItem.info.clear_note || 'Guten Appetit';
      if (!quiet) say(`<em>${esc(note)}!</em> Handed over the counter on its paper plate. Plates served tonight: <b>${P.served}</b>.`);
      if (!quiet) crowdSay(crowdLine('wurst', 'bun', 'Smells good!'), place.center.clone().setY(0), 9);
      sfx('plate');
      anim.add(0.75, (k) => {
        plate.position.copy(r0.p).addScaledVector(outL, k).addScaledVector(lift, Math.sin(k * Math.PI) * 0.08);
        plate.scale.setScalar(Math.max(0.01, 1 - k * 0.92));
      }, () => {
        for (const f of P.food) if (f.gen <= upTo) f.g?.removeFromParent();
        for (const s of P.sauces) { s.mesh.removeFromParent(); s.mesh.geometry.dispose(); }
        for (const d of P.dust) { d.points.removeFromParent(); d.points.geometry.dispose(); d.points.material.dispose(); }
        P.food = P.food.filter((f) => f.gen > upTo); P.sauces.length = 0; P.dust.length = 0;
        dusting = null;
        restore(plate, r0);
        plate.scale.setScalar(0.01);
        // the vendor sets out a fresh plate
        anim.add(0.35, (k) => plate.scale.setScalar(Math.max(0.01, k)), () => { plate.scale.setScalar(1); done(); }, 0.25);
      });
    });
  }

  // ---------- the panel buttons ----------
  const byKey = (k) => kinds.find((i) => keyOf(i) === k);
  const sauceBy = (k) => sauces.find((i) => (i.info.sauce || keyOf(i)) === k);
  function bunPlate() {
    if (!P) return false;
    const roll = byKey('roll'), wurst = byKey('thueringer') || kinds.find((i) => i !== roll);
    if (!roll || !wurst) return false;
    if (cur().length) clearPlate({ quiet: true });
    say(actionNote('wurst', 'bun', 'One Bratwurst im Brötchen with mustard. <em>That will be 4 euros.</em>'));
    toPlate(roll, { quiet: true });
    toPlate(wurst, { quiet: true }); // into the roll that just went down
    const senf = sauceBy('senf') || sauces[0];
    if (senf) squeeze(senf, { quiet: true });
    enqueue((done) => { crowdSay(crowdLine('wurst', 'bun', 'Smells good!'), place.center.clone().setY(0), 9); done(); });
    return true;
  }
  const MIX = [['nuernberger', 'senf'], ['krakauer', 'ketchup'], ['curry', 'dust'], ['thueringer', 'curry']];
  let mixN = 0;
  function mixPlate() {
    if (!P || !kinds.length) return false;
    if (cur().length >= P.max) clearPlate({ quiet: true });
    const [k, top] = MIX[mixN++ % MIX.length];
    const item = byKey(k) || kinds[mixN % kinds.length];
    toPlate(item);
    if (top === 'dust' && shaker) dust(shaker);
    else if (sauceBy(top)) squeeze(sauceBy(top));
    return true;
  }

  // focus: the camera comes close enough to see the board, the bottles and the plate together
  let region = null;
  function focusPoint() {
    if (region) return region.clone();
    const b = new THREE.Box3();
    for (const it of [...kinds, ...sauces, shaker, plateItem]) if (it) b.union(boxOf(it.node));
    region = b.isEmpty() ? null : b.getCenter(new THREE.Vector3());
    return region?.clone() || null;
  }
  const PLATE_KINDS = new Set(['wurst', 'roll', 'sauce', 'spice', 'plate']);

  return {
    kinds: { wurst: (i) => toPlate(i), roll: (i) => toPlate(i), sauce: squeeze, spice: dust, plate: () => clearPlate() },
    focusOf(item) { return item.placeId === 'wurst' && PLATE_KINDS.has(item.kind) ? focusPoint() : null; },
    api: {
      plateReady: !!P && kinds.length > 0,
      bunPlate, mixPlate,
      grillReady: !!grillS,
      turnAll,
      /** For tests: how many sausages lie on the grate and how often each has been turned. */
      grill: () => (grillS ? { n: grillS.list.length, turns: grillS.list.map((s) => s.turns), busy: grillS.list.some((s) => s.busy), angles: grillS.list.map((s) => +s.angle.toFixed(3)) } : null),
      clearPlate: () => clearPlate(),
      /** For tests: what is on the plate. */
      plate: () => (P ? { food: P.food.filter((f) => f.landed).map((f) => f.key), filled: P.food.filter((f) => f.landed && f.onto === 'roll').map((f) => f.key), sauces: P.sauces.map((s) => s.key), dust: P.dust.reduce((a, d) => a + d.n, 0), served: P.served, max: P.max, busy: running || queue.length > 0, kinds: kinds.map(keyOf), bottles: sauces.map((s) => s.info.sauce || keyOf(s)), shaker: !!shaker } : null),
    },
    retract() {},
    update(dt, t, still) {
      flare *= Math.exp(-dt * 1.2);
      smoke.base = 0.28 + flare * 0.1;
      smoke.update(dt, still);
      sparks.update(dt);
      stepDust(dt);
      for (const m of grillMats) m.emissiveIntensity = m.userData.baseEmissive * (1 + (still ? 0 : Math.sin(t * 13) * 0.08 + Math.sin(t * 7.1) * 0.06) + flare * 1.2);
      if (grillLight) grillLight.intensity = 4 + (still ? 0 : Math.sin(t * 13) * 0.6 + Math.sin(t * 7.1) * 0.5) + flare * 6;
      if (swing && !still) {
        const a = Math.sin(t * 1.15) * (0.035 + flare * 0.05);
        swing.e.set(a, 0, Math.sin(t * 0.8 + 1) * 0.02);
        swing.node.quaternion.copy(swing.q0).multiply(swing.q.setFromEuler(swing.e));
      }
    },
  };
}

/** "a, b and c" */
function listOf(a) {
  return a.length < 2 ? a.join('') : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`;
}
