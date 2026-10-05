// Stand-in for the vendor's round-10 Bratwurst plate set (BUILD.md, ADR 0004 revision): the four kinds on a
// two-step serving board, a roll, three sauce bottles with fx_sauce_ empties at their nozzles, the curry shaker
// and the paper plate with plate_spot_0..3. Same node names and places as prop_wurst_counter.glb (slot_counter
// frame, metres, +Z towards the visitor), so actions/items/wurst.js works the same on a stand-in.
import * as THREE from 'three';
import { colorMat } from './kit.js';

function part(geo, mat, x = 0, y = 0, z = 0, name) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x, y, z);
  if (name) m.name = name;
  m.castShadow = true;
  return m;
}
function node(name, x, y, z, item) {
  const o = new THREE.Group();
  o.name = name;
  o.position.set(x, y, z);
  if (item) o.userData.item = item;
  return o;
}
/** A sausage lying along X with its base at the origin. */
function sausage(len, rad, color) {
  const m = part(new THREE.CapsuleGeometry(rad, Math.max(0.001, len - rad * 2), 4, 10).rotateZ(Math.PI / 2), colorMat(color, 0.42), 0, rad, 0);
  return m;
}

/** The plate set (a Group in slot_counter's frame). `withGrill` adds a small stand-in grill at x -0.9. */
export function buildPlateSet({ withGrill = false } = {}) {
  const g = new THREE.Group();
  g.name = 'standin_plate_set';
  const wood = colorMat(0x7a5232, 0.8);
  // the serving board: a front step and a back step raised 4 cm
  g.add(part(new THREE.BoxGeometry(0.62, 0.022, 0.12), wood, 0.66, 0.011, 0.205));
  g.add(part(new THREE.BoxGeometry(0.62, 0.062, 0.12), wood, 0.66, 0.031, 0.093));

  const t = node('act_wurst_thueringer', 0.52, 0.062, 0.093, { kind: 'wurst', action: 'plate', wurst: 'thueringer', name: 'Thüringer Rostbratwurst', label: 'Thüringer' });
  t.add(sausage(0.22, 0.012, 0x7a3b1c));
  const k = node('act_wurst_krakauer', 0.82, 0.062, 0.093, { kind: 'wurst', action: 'plate', wurst: 'krakauer', name: 'Krakauer, smoked', label: 'Krakauer' });
  k.add(sausage(0.17, 0.02, 0x6a2418));
  const n = node('act_wurst_nuernberger', 0.44, 0.022, 0.205, { kind: 'wurst', action: 'plate', wurst: 'nuernberger', count: 3, name: 'Drei Nürnberger Rostbratwürstchen', label: '3 Nürnberger' });
  for (let i = 0; i < 3; i++) { const s = sausage(0.085, 0.009, 0x8a4a22); s.position.z = (i - 1) * 0.02; n.add(s); }
  const c = node('act_wurst_curry', 0.66, 0.022, 0.205, { kind: 'wurst', action: 'plate', wurst: 'curry', name: 'Currywurst, sliced', label: 'Currywurst' });
  c.add(part(new THREE.BoxGeometry(0.13, 0.012, 0.07), colorMat(0xeee6d4, 0.9), 0, 0.006, 0));
  for (let i = 0; i < 6; i++) c.add(part(new THREE.CylinderGeometry(0.012, 0.012, 0.012, 10).rotateX(Math.PI / 2), colorMat(0x8a4a22, 0.5), -0.05 + i * 0.02, 0.022, 0));
  c.add(part(new THREE.BoxGeometry(0.12, 0.004, 0.04), colorMat(0xa8240e, 0.25), 0, 0.03, 0));
  const r = node('act_roll', 0.87, 0.022, 0.205, { kind: 'roll', action: 'plate', wurst: 'roll', name: 'Brötchen (crusty bread roll)', label: 'Brötchen' });
  const bun = part(new THREE.SphereGeometry(0.03, 14, 8), colorMat(0xc58a46, 0.75), 0, 0.022, 0);
  bun.scale.set(1.7, 0.75, 1);
  r.add(bun);
  g.add(t, k, n, c, r);

  const sauces = [['senf', 1.04, 0.19, 0xd6a21c], ['ketchup', 1.118, 0.172, 0xa8140e], ['curry', 1.196, 0.19, 0xb4400e]];
  for (const [key, x, z, col] of sauces) {
    const b = node(`act_sauce_${key}`, x, 0, z, { kind: 'sauce', action: 'sauce', sauce: key, colour: '#' + col.toString(16).padStart(6, '0'), fx: `fx_sauce_${key}`, label: key });
    b.add(part(new THREE.CylinderGeometry(0.026, 0.028, 0.17, 14), colorMat(col, 0.3), 0, 0.085, 0));
    b.add(part(new THREE.CylinderGeometry(0.016, 0.02, 0.02, 12), colorMat(0xf2efe6, 0.4), 0, 0.18, 0));
    b.add(part(new THREE.ConeGeometry(0.008, 0.026, 10), colorMat(0xf2efe6, 0.4), 0, 0.203, 0));
    const fx = new THREE.Object3D(); fx.name = `fx_sauce_${key}`; fx.position.set(0, 0.2165, 0); b.add(fx);
    g.add(b);
  }
  const sh = node('act_shaker_curry', 1.269, 0, 0.2, { kind: 'spice', action: 'dust', colour: '#c8781a', fx: 'fx_shaker_curry', label: 'Currypulver' });
  sh.add(part(new THREE.CylinderGeometry(0.025, 0.025, 0.09, 14), colorMat(0xb8b2a6, 0.35, 0.8), 0, 0.045, 0));
  sh.add(part(new THREE.SphereGeometry(0.025, 14, 6, 0, Math.PI * 2, 0, Math.PI / 2), colorMat(0xd8d2c6, 0.3, 0.8), 0, 0.09, 0));
  const sfx = new THREE.Object3D(); sfx.name = 'fx_shaker_curry'; sfx.position.set(0, 0.1, 0); sh.add(sfx);
  g.add(sh);

  const p = node('act_plate', 0.14, 0, 0.148, { kind: 'plate', action: 'clear', spots: ['plate_spot_0', 'plate_spot_1', 'plate_spot_2', 'plate_spot_3'], max_items: 4, clear_note: 'Guten Appetit', label: 'Pappteller' });
  p.add(part(new THREE.CylinderGeometry(0.115, 0.1, 0.012, 28), colorMat(0xf4f1ea, 0.85), 0, 0.006, 0));
  [[-0.042, -0.036], [0.042, -0.036], [-0.042, 0.036], [0.042, 0.036]].forEach(([x, z], i) => { const s = new THREE.Object3D(); s.name = `plate_spot_${i}`; s.position.set(x, 0.002 + 0.01, z); p.add(s); });
  g.add(p);

  if (withGrill) {
    const grill = node('act_grill', -0.9, 0, 0);
    grill.add(part(new THREE.BoxGeometry(0.9, 0.1, 0.4), colorMat(0x2a2624, 0.6, 0.5), 0, 0.05, 0));
    const coals = part(new THREE.BoxGeometry(0.84, 0.02, 0.34), new THREE.MeshStandardMaterial({ name: 'standin_coals', color: 0x1a0c08, emissive: 0xff5a14, emissiveIntensity: 0.8, roughness: 0.9 }), 0, 0.11, 0, 'coals');
    grill.add(coals);
    const swing = node('act_grill_swing', 0, 0.58, 0);
    const grate = part(new THREE.BoxGeometry(0.8, 0.01, 0.34), colorMat(0x3a3634, 0.5, 0.7), 0, -0.4, 0);
    swing.add(grate);
    for (let i = 0; i < 6; i++) { const s = sausage(0.2, 0.014, 0x7a3b1c); s.position.set(-0.3 + i * 0.12, -0.395, (i % 2 ? 0.06 : -0.06)); s.rotation.y = Math.PI / 2; s.name = 'sausages_grill'; swing.add(s); }
    grill.add(swing);
    const smoke = new THREE.Object3D(); smoke.name = 'act_smoke'; smoke.position.set(0, 0.28, 0); grill.add(smoke);
    g.add(grill);
  }
  return g;
}
