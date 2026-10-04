// The Bratwurst stand: click a sausage and it is turned on the grill, with a sizzle, a flare of the coals and
// sparks; click a roll and a sausage from the grill goes into it, with a line of mustard. The grill swings on its
// tripod, the coals glow and flicker, and smoke drifts over the crowd.
import * as THREE from 'three';
import { boxOf, rest, restore, worldDirToParent, createSparks, MUSTARD, UP, esc } from './common.js';
import { createEmitter } from '../effects.js';
import { act, acts, findNode, counterLocal, toLocal, worldOf, longAxis } from '../util.js';
import { actionNote, crowdLine } from '../../content.js';

export function createWurst(ctx) {
  const { market, anim, scene, sfx, say, crowdSay, items, lite } = ctx;
  const place = market.places.wurst;
  if (!place) return {};
  const front = new THREE.Vector3(Math.sin(place.ry), 0, Math.cos(place.ry));
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
  // the coals: the vendor's glowing coal material, or the grill itself on a stand-in
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

  // ---------- sausages ----------
  const sausages = new Map();
  for (const s of acts(place, 'act_sausage')) {
    const item = items.of('wurst', 'sausage').find((i) => i.node === s) || items.add(s, 'wurst', place, 'sausage');
    if (item) sausages.set(item, { item, r: rest(s), axis: longAxis(s), centre: turnCentre(s, item.info), angle: 0, turns: 0 });
  }
  const onGrill = () => [...sausages.values()].filter((s) => !s.item.info.raw && (/grill/i.test(s.item.info.name || '') || !s.item.info.name));
  // only a sausage over the coals flares and sparks; the raw ones and the warm tray are just turned in place
  const overCoals = (item) => !item.info.raw && (/grill/i.test(item.info.name || '') || !item.info.name);
  let turned = 0;

  function turnOne(item, delay = 0, quiet = false) {
    const s = sausages.get(item);
    if (!s || item.busy) return;
    items.release(item);
    item.busy = true;
    item.keepOwn = true;
    const node = item.node;
    const a0 = s.angle;
    s.angle += Math.PI;
    s.turns++;
    const up = worldDirToParent(node, UP);
    const q = new THREE.Quaternion();
    // turn about the sausage's own long axis through its middle, not about its base pivot (items.json turn_axis)
    const sc = s.centre.clone().multiply(node.scale);
    const shift = new THREE.Vector3();
    const pose = (a, hop) => {
      q.setFromAxisAngle(s.axis, a);
      node.quaternion.copy(s.r.q).multiply(q);
      shift.copy(sc).applyQuaternion(q).negate().add(sc).applyQuaternion(s.r.q);
      node.position.copy(s.r.p).add(shift).addScaledVector(up, hop);
    };
    anim.add(0.55, (k) => pose(a0 + k * Math.PI, Math.sin(k * Math.PI) * 0.05), () => {
      pose(s.angle, 0);
      item.busy = false;
      // fat drips on the coals: a flare and a spray of sparks
      if (!overCoals(item)) return;
      flare = Math.min(2.2, flare + (quiet ? 0.35 : 1.2));
      sparks.burst(node.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, -0.04, 0)), quiet ? 4 : 12);
      smoke.boost = Math.max(smoke.boost, quiet ? 0.5 : 1.4);
    }, delay);
    if (!quiet && item.info.raw) {
      say(`<b>${esc(item.info.name)}</b>, turned over in the tray. It goes on the grill when there is room.`);
    } else if (!quiet) {
      sfx('sizzle');
      turned++;
      say(`<b>${esc(item.info.name || 'A Bratwurst')}</b>, turned (${s.turns}×). ${actionNote('wurst', 'turn', ['Turned. Nicely browned on this side.', 'The coals flare up and the smoke drifts over the crowd.', 'Almost ready. Mustard or ketchup?'][(s.turns - 1) % 3], { n: s.turns - 1, name: item.info.name })}`);
    }
  }
  function turnAll() {
    const grillList = onGrill().map((s) => s.item);
    const list = grillList.length ? grillList : [...sausages.keys()];
    list.forEach((it, i) => turnOne(it, i * 0.07, true));
    sfx('sizzle');
    turned++;
    say(actionNote('wurst', 'turn', ['Turned. Nicely browned on this side.', 'The coals flare up and the smoke drifts over the crowd.', 'Almost ready. Mustard or ketchup?'][(turned - 1) % 3], { n: turned - 1 }));
  }

  // ---------- a sausage in a bun ----------
  const buns = new Map(); // roll item -> { clone, mustard, left }
  const making = new Set(); // rolls being filled right now
  let next = 0;
  function bun(rollItem) {
    if (rollItem.busy) return;
    if (buns.has(rollItem)) { handOver(rollItem); return; }
    const grilled = onGrill().filter((s) => !s.item.busy && s.item.node.visible);
    const from = grilled[next++ % Math.max(1, grilled.length)];
    items.release(rollItem);
    rollItem.busy = true;
    rollItem.keepOwn = true;
    making.add(rollItem);
    sfx('sizzle');
    const roll = rollItem.node;
    const rb = boxOf(roll);
    const rs = rb.getSize(new THREE.Vector3());
    const along = rs.x >= rs.z ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1);
    // the sausage: a copy of one from the grill (the grill gets a fresh one a few seconds later)
    const g = new THREE.Group();
    g.name = 'item_bun_sausage';
    let len = 0.16, rad = 0.014;
    if (from) {
      const src = from.item.node;
      const lb = boxOf(src, src), ls = lb.getSize(new THREE.Vector3());
      len = Math.max(ls.x, ls.y, ls.z); rad = Math.min(ls.x, ls.y, ls.z) / 2;
      src.traverse((o) => {
        if (!o.isMesh || o.userData.itemFx) return;
        const m = new THREE.Mesh(o.geometry, o.material);
        m.matrixAutoUpdate = false;
        m.matrix.copy(new THREE.Matrix4().copy(src.matrixWorld).invert().multiply(o.matrixWorld));
        m.castShadow = true;
        g.add(m);
      });
      g.position.copy(src.getWorldPosition(new THREE.Vector3()));
      g.quaternion.copy(src.getWorldQuaternion(new THREE.Quaternion()));
      g.scale.copy(src.getWorldScale(new THREE.Vector3()));
      src.visible = false;
      setTimeout(() => { src.visible = true; src.scale.setScalar(1); }, 6000);
    } else {
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(rad, len - rad * 2, 4, 10).rotateZ(Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x8a4a26, roughness: 0.5 }));
      g.add(m);
      g.position.copy(roll.getWorldPosition(new THREE.Vector3())).add(new THREE.Vector3(0, 0.4, 0));
    }
    scene.add(g);
    // where it ends: lying in the roll, along its length (the sausage's own long axis is its X)
    const axisW = along.clone().applyQuaternion(roll.getWorldQuaternion(new THREE.Quaternion())).setY(0).normalize();
    const side = new THREE.Vector3().crossVectors(axisW, UP).normalize();
    const qEnd = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(axisW, UP, side.clone().negate()));
    const pEnd = rb.getCenter(new THREE.Vector3()).setY(rb.max.y - rad * 0.2);
    const p0 = g.position.clone(), q0 = g.quaternion.clone();
    // mustard: a zigzag piped along the top, drawn in as it goes
    const pts = [];
    const n = 9;
    for (let i = 0; i <= n; i++) pts.push(new THREE.Vector3(-len * 0.38 + (len * 0.76 * i) / n, rad * 1.05, (i % 2 ? 1 : -1) * rad * 0.55));
    const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, rad * 0.22, 6, false);
    const mustard = new THREE.Mesh(tube, MUSTARD);
    mustard.name = 'item_mustard';
    mustard.userData.itemFx = true;
    tube.setDrawRange(0, 0);
    say(actionNote('wurst', 'bun', 'One Bratwurst im Brötchen with mustard. <em>That will be 4 euros.</em>'));
    anim.add(0.9, (k) => {
      g.position.lerpVectors(p0, pEnd, k).addScaledVector(UP, Math.sin(k * Math.PI) * 0.25);
      g.quaternion.slerpQuaternions(q0, qEnd, k);
      const sc = from ? from.item.node.getWorldScale(new THREE.Vector3()) : new THREE.Vector3(1, 1, 1);
      g.scale.copy(sc);
    }, () => {
      g.add(mustard);
      mustard.scale.set(1 / g.scale.x, 1 / g.scale.y, 1 / g.scale.z);
      const total = tube.index.count;
      anim.add(0.8, (k) => tube.setDrawRange(0, Math.floor((total * k) / 3) * 3), () => {
        rollItem.busy = false;
        making.delete(rollItem);
        buns.set(rollItem, { g, mustard, left: 12 });
        crowdSay(crowdLine('wurst', 'bun', 'Smells good!'), place.center.clone().setY(0), 9);
      });
    });
  }
  function handOver(rollItem) {
    const b = buns.get(rollItem);
    if (!b || rollItem.busy) return;
    buns.delete(rollItem);
    rollItem.busy = true;
    const roll = rollItem.node, r0 = rest(roll);
    const g0 = b.g.position.clone();
    const out = front.clone().multiplyScalar(0.45).add(new THREE.Vector3(0, 0.12, 0));
    const outL = worldDirToParent(roll, out);
    say('Handed over the counter, warm, in a paper napkin. <em>Guten Appetit!</em>');
    anim.add(0.7, (k) => {
      roll.position.copy(r0.p).addScaledVector(outL, k);
      b.g.position.copy(g0).addScaledVector(out, k);
      const s = 1 - k * 0.9;
      roll.scale.setScalar(s); b.g.scale.setScalar(s * (b.g.userData.s0 ||= b.g.scale.x));
    }, () => {
      b.g.removeFromParent();
      b.mustard.geometry.dispose();
      restore(roll, r0);
      roll.scale.setScalar(0.01);
      // the vendor sets out a fresh roll
      anim.add(0.4, (k) => roll.scale.setScalar(Math.max(0.01, k)), () => { roll.scale.setScalar(1); rollItem.busy = false; rollItem.keepOwn = false; items.settle(rollItem); }, 0.6);
    });
  }
  function served(item) {
    if (item.busy) return;
    items.release(item);
    item.busy = true;
    const node = item.node, r0 = rest(node);
    const out = worldDirToParent(node, front.clone().multiplyScalar(0.2).add(new THREE.Vector3(0, 0.1, 0)));
    anim.add(1.4, (k) => node.position.copy(r0.p).addScaledVector(out, Math.sin(k * Math.PI)), () => { restore(node, r0); item.busy = false; });
    say(actionNote('wurst', 'bun', 'One Bratwurst im Brötchen with mustard. <em>That will be 4 euros.</em>'));
  }
  function nextRoll() {
    const rolls = items.of('wurst', 'roll');
    const r = rolls.find((x) => !buns.has(x) && !x.busy);
    if (r) { bun(r); return true; }
    const b = [...buns.keys()][0];
    if (b) handOver(b);
    return false;
  }

  return {
    kinds: { sausage: (i) => turnOne(i), roll: bun, served },
    api: {
      sausagesReady: sausages.size > 0,
      turnAll, bunNext: nextRoll,
      rollsReady: items.of('wurst', 'roll').length > 0,
      sausageAngle: (name) => { const it = [...sausages.keys()].find((i) => i.node.name === name); return it ? +sausages.get(it).angle.toFixed(3) : null; },
      bunCount: () => buns.size + making.size, // filled rolls, and any being filled
    },
    retract() {},
    update(dt, t, still) {
      flare *= Math.exp(-dt * 1.2);
      smoke.base = 0.28 + flare * 0.1;
      smoke.update(dt, still);
      sparks.update(dt);
      for (const m of grillMats) m.emissiveIntensity = m.userData.baseEmissive * (1 + (still ? 0 : Math.sin(t * 13) * 0.08 + Math.sin(t * 7.1) * 0.06) + flare * 1.2);
      if (grillLight) grillLight.intensity = 4 + (still ? 0 : Math.sin(t * 13) * 0.6 + Math.sin(t * 7.1) * 0.5) + flare * 6;
      if (swing && !still) {
        const a = Math.sin(t * 1.15) * (0.035 + flare * 0.05);
        swing.e.set(a, 0, Math.sin(t * 0.8 + 1) * 0.02);
        swing.node.quaternion.copy(swing.q0).multiply(swing.q.setFromEuler(swing.e));
      }
      for (const [roll, b] of buns) if (!roll.busy && (b.left -= dt) <= 0) handOver(roll);
    },
  };
}

/**
 * The point (node-local) the sausage turns about: items.json turn_axis gives the axis height over a base pivot;
 * otherwise the middle of its mesh, across its long axis.
 */
function turnCentre(node, info = {}) {
  const off = +info.turn_axis?.offset_threejs_y;
  if (Number.isFinite(off) && off !== 0) return new THREE.Vector3(0, off / (node.scale.y || 1), 0);
  const box = boxOf(node, node);
  if (box.isEmpty()) return new THREE.Vector3();
  const c = box.getCenter(new THREE.Vector3());
  const ax = longAxis(node);
  return c.sub(ax.clone().multiplyScalar(c.dot(ax)));
}
