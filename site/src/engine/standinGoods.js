// Stand-in goods for real section-stall glbs that have no act_ nodes yet (the vendor's props supply them).
// Each piece hangs off the stall's slot_ empties and uses the act_ names the actions look for,
// so pour, pull, the Bratwurst plate and pull-a-book work on the carpenter's stalls before the props arrive.
import * as THREE from 'three';
import { mats, colorMat, mergeStatic } from '../standins/kit.js';
import { buildPlateSet } from '../standins/plate.js';

const has = (nodes, prefix) => Object.keys(nodes.acts).some((k) => k.startsWith(prefix));

function mesh(geo, mat, x = 0, y = 0, z = 0, name) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x, y, z);
  if (name) m.name = name;
  m.castShadow = true;
  return m;
}

/** A group under `slot` that ignores the slot's own rotation quirks but keeps its position and heading. */
function under(slot, name) {
  const g = new THREE.Group();
  g.name = name;
  slot.add(g);
  return g;
}

export function addStandinGoods(place, { warn }) {
  const { nodes, id } = place;
  const S = nodes.slots;
  const M = mats();
  const counter = S.slot_counter;
  if (!counter) return false;
  let added = false;

  if (id === 'glueh' && !has(nodes, 'act_pot') && !has(nodes, 'act_ladle')) {
    const g = under(counter, 'standin_goods_gluehwein');
    const pot = new THREE.Group();
    pot.name = 'act_pot';
    pot.position.set(1.1, 0, -0.08);
    pot.add(mesh(new THREE.CylinderGeometry(0.26, 0.24, 0.42, 24), M.metal, 0, 0.21));
    pot.add(mesh(new THREE.CylinderGeometry(0.245, 0.245, 0.02, 24), M.wine, 0, 0.41));
    const lid = mesh(new THREE.CylinderGeometry(0.27, 0.27, 0.025, 24), M.metal, -0.3, 0.24, 0.02, 'act_pot_lid');
    lid.rotation.z = 1.2;
    pot.add(lid);
    g.add(pot);
    const mugG = new THREE.LatheGeometry([[0.001, 0], [0.07, 0], [0.075, 0.02], [0.075, 0.14], [0.068, 0.145], [0.064, 0.02]].map((p) => new THREE.Vector2(p[0], p[1])), 16);
    for (let i = 0; i < 6; i++) g.add(mesh(mugG, M.mug, -1.3 + i * 0.22, 0, 0.06 + (i % 2) * 0.08));
    added = true;
  }

  if (id === 'bier' && !has(nodes, 'act_tap')) {
    const g = under(counter, 'standin_goods_bier');
    g.add(mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 12), M.metal, 0.6, 0.25, -0.1));
    g.add(mesh(new THREE.BoxGeometry(0.9, 0.1, 0.12), M.metal, 0.6, 0.5, -0.1));
    [0xc9a341, 0x8e2a3f, 0x2f5c7a].forEach((c, i) => {
      const pv = new THREE.Group();
      pv.name = `act_tap_${i}`;
      pv.position.set(0.3 + i * 0.3, 0.55, -0.1);
      pv.add(mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.3, 10), colorMat(c, 0.3), 0, 0.17));
      pv.add(mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.12, 8), M.metal, 0, -0.08));
      g.add(pv);
    });
    for (let i = 0; i < 4; i++) {
      g.add(mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.24, 14), M.beer, -1.3 + i * 0.22, 0.12, 0.05));
      g.add(mesh(new THREE.CylinderGeometry(0.062, 0.062, 0.04, 14), M.foam, -1.3 + i * 0.22, 0.26, 0.05));
    }
    added = true;
  }

  if (id === 'wurst' && !has(nodes, 'act_wurst_') && !has(nodes, 'act_plate')) {
    // the round-10 plate set (stand-in for prop_wurst_counter.glb) at the counter; a grill only when the
    // carpenter's stall has no coal bed of its own
    let grill = null;
    place.root.traverse((o) => { if (!grill && /grill|coals/i.test(o.name) && o.isMesh) grill = o; });
    const set = buildPlateSet({ withGrill: !grill && !has(nodes, 'act_grill') });
    set.name = 'standin_goods_bratwurst';
    counter.add(set);
    added = true;
  }

  if (id === 'books' && !has(nodes, 'act_book_')) {
    const pal = [0x7a1e2c, 0x1f3a5a, 0x2e5a3a, 0xb88a2e, 0x5a3a6a, 0xd9cbb0, 0x3a2a22, 0x8a4a2a, 0x1a1a1f, 0x2a6a7a];
    const bg = new THREE.BoxGeometry(1, 1, 1);
    let s = 17;
    const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    let n = 0;
    for (const key of ['slot_shelf_1', 'slot_shelf_2', 'slot_cabinet_l', 'slot_cabinet_r']) {
      const slot = S[key];
      if (!slot) continue;
      const g = under(slot, `standin_books_${key}`);
      const half = key.startsWith('slot_cabinet') ? 0.3 : 1.4;
      let x = -half;
      while (x < half) {
        const bw = 0.035 + r() * 0.05, bh = 0.2 + r() * 0.12;
        const b = mesh(bg, colorMat(pal[(r() * pal.length) | 0], 0.7), x + bw / 2, bh / 2, 0);
        b.scale.set(bw, bh, 0.18 + r() * 0.05);
        if (r() < 0.05) b.rotation.z = 0.2;
        if (r() < 0.45) b.name = `act_book_${n++}`;
        g.add(b);
        x += bw + 0.004;
      }
      // the books you can pull stay separate; the rest of the row is one draw per colour
      mergeStatic(g, /^act_book/);
    }
    added = n > 0;
  }
  // the ornament shop without the vendor's goods (ADR 0004, round-9 revision): its three interactive pieces under
  // the vendor's names, a glass-harmonica row of twelve baubles, the mercury-glass ball with its dive cameras, and
  // the Schwibbogen with seven candles
  if (id === 'schmuck' && !has(nodes, 'act_orn_')) { addStandinOrnaments(counter, M); added = true; }
  if (added) warn?.(`${place.entry.id}: no act_ props yet; added stand-in goods for the panel actions.`);
  return added;
}

function addStandinOrnaments(counter, M) {
  const g = under(counter, 'standin_goods_schmuck');
  const glass = (hex, name = 'vendor_mercury') => new THREE.MeshStandardMaterial({ name, color: hex, roughness: 0.12, metalness: 0.8 });
  const item = (o, info) => { o.userData.item = info; return o; };
  // the glass harmonica: a brass rail over the counter's front, twelve baubles hanging from it, left to right
  const rail = mesh(new THREE.CylinderGeometry(0.008, 0.008, 2.1, 8), M.metal, 0, 0.95, 0.2);
  rail.rotation.z = Math.PI / 2;
  g.add(rail);
  const cols = [0xd8d8dc, 0xd9b26a];
  for (let i = 0; i < 12; i++) {
    const b = item(new THREE.Group(), { action: 'harmonica', index: i, label: `Glasharmonika · Kugel ${i + 1} von 12` });
    b.name = `act_orn_harmonica_${i}`;
    b.position.set(-0.935 + i * 0.17, 0.95, 0.2);
    const r = 0.047 - i * 0.0013;
    const ball = mesh(new THREE.SphereGeometry(r, 16, 12), glass(cols[i % 2]), 0, -0.13 - r, 0);
    const string = mesh(new THREE.CylinderGeometry(0.0015, 0.0015, 0.13, 4), M.metal, 0, -0.065, 0);
    b.add(ball, string);
    g.add(b);
  }
  // the mercury-glass ball, 18 cm, on its own hook to the left, with the cameras for the dive
  const ball = item(new THREE.Group(), { action: 'dive', label: 'Spiegelkugel · 18 cm', cam: 'cam_dive', cam_target: 'cam_dive_target' });
  ball.name = 'act_orn_mirrorball';
  ball.position.set(-1.45, 1.05, 0.55);
  ball.add(mesh(new THREE.SphereGeometry(0.09, 32, 20), glass(0xcfcfd4), 0, -0.119, 0));
  const cam = (n, x, y, z) => { const o = new THREE.Object3D(); o.name = n; o.position.set(x, y, z); ball.add(o); };
  cam('cam_dive', 0.051, -0.119, 0.141); cam('cam_dive_target', 0, -0.119, 0); cam('cam_dive_approach', 0.238, -0.119, 0.658);
  g.add(ball);
  // the Schwibbogen: an arch with seven candles, flames out; they light from the outside in
  const arch = item(new THREE.Group(), { action: 'candles', label: 'Schwibbogen' });
  arch.name = 'act_orn_schwibbogen';
  arch.position.set(-0.42, 0, -0.11);
  const bow = mesh(new THREE.TorusGeometry(0.21, 0.014, 6, 28, Math.PI), colorMat(0x7a5230, 0.8), 0, 0.03, 0);
  arch.add(bow);
  const flameMat = new THREE.MeshStandardMaterial({ name: 'flame', color: 0xffc070, emissive: 0xffa040, emissiveIntensity: 2.5 });
  for (let i = 0; i < 7; i++) {
    const a = Math.PI * (0.1 + (0.8 * i) / 6);
    const c = new THREE.Group(); c.name = `act_orn_candle_${i}`;
    c.position.set(Math.cos(a) * 0.21, 0.03 + Math.sin(a) * 0.21 + 0.035, 0);
    c.add(mesh(new THREE.ConeGeometry(0.006, 0.022, 6), flameMat, 0, 0.011, 0));
    c.userData.item = { action: 'light', order: Math.min(i, 6 - i), label: `Kerze ${i + 1} am Schwibbogen` };
    arch.add(c);
  }
  g.add(arch);
}
