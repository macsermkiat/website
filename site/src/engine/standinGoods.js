// Stand-in goods for real section-stall glbs that have no act_ nodes yet (the vendor's props supply them).
// Each piece hangs off the stall's slot_ empties and uses the act_ names the actions look for,
// so pour, pull, turn and pull-a-book work on the carpenter's stalls before the props arrive.
import * as THREE from 'three';
import { mats, colorMat, mergeStatic } from '../standins/kit.js';

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

  if (id === 'wurst' && !has(nodes, 'act_sausage')) {
    // on the carpenter's coal bed when there is one, else along the counter
    let grill = null;
    place.root.traverse((o) => { if (!grill && /grill|coals/i.test(o.name) && o.isMesh) grill = o; });
    const sg = new THREE.CapsuleGeometry(0.035, 0.2, 4, 8);
    const g = new THREE.Group();
    g.name = 'standin_goods_bratwurst';
    if (grill) {
      const box = new THREE.Box3().setFromObject(grill);
      const c = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      place.holder.add(g);
      g.position.copy(place.holder.worldToLocal(new THREE.Vector3(c.x, box.max.y + 0.06, c.z)));
      const span = Math.max(0.6, Math.min(1.6, Math.max(size.x, size.z) - 0.2));
      for (let i = 0; i < 7; i++) {
        const s = mesh(sg, M.sausage, -span / 2 + (i * span) / 6, 0, i % 2 ? 0.06 : -0.06, `act_sausage_${i}`);
        s.rotation.z = Math.PI / 2;
        g.add(s);
      }
    } else {
      counter.add(g);
      for (let i = 0; i < 7; i++) {
        const s = mesh(sg, M.sausage, -0.9 + i * 0.3, 0.05, 0, `act_sausage_${i}`);
        s.rotation.z = Math.PI / 2;
        g.add(s);
      }
    }
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
  // the ornament shop without the vendor's goods (ADR 0004): a rail of baubles, the pickle among the green ones, a
  // Herrnhut star, a nutcracker, a smoker, a candle arch and a little tree with hooks, under the usual act_orn_ names
  if (id === 'schmuck' && !has(nodes, 'act_orn_')) { addStandinOrnaments(counter, M); added = true; }
  if (added) warn?.(`${place.entry.id}: no act_ props yet; added stand-in goods for the panel actions.`);
  return added;
}

const NOTE_ROW = ['C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5', 'C6'];
function addStandinOrnaments(counter, M) {
  const g = under(counter, 'standin_goods_schmuck');
  const glass = (hex) => new THREE.MeshStandardMaterial({ color: hex, roughness: 0.18, metalness: 0.35 });
  const item = (o, info) => { o.userData.item = info; return o; };
  // a brass rail over the counter, the baubles hanging from it (each pivot at its ribbon's top)
  const rail = mesh(new THREE.CylinderGeometry(0.008, 0.008, 1.9, 8), M.metal, 0, 0.62, -0.05);
  rail.rotation.z = Math.PI / 2;
  g.add(rail);
  const cols = [0xa3162c, 0xc9a13a, 0x1f4f8a, 0xa3162c, 0x2e6b3a, 0xc9a13a, 0x6a2a7a, 0xe8e2d4];
  NOTE_ROW.forEach((note, i) => {
    const b = item(new THREE.Group(), { action: 'ring', note, hangable: true, label: `Glaskugel · ${note}` });
    b.name = `act_orn_bauble_${i}`;
    b.position.set(-0.85 + i * 0.2, 0.62, -0.05);
    const ball = mesh(new THREE.SphereGeometry(0.035, 16, 12), glass(cols[i]), 0, -0.1, 0);
    const string = mesh(new THREE.CylinderGeometry(0.0015, 0.0015, 0.065, 4), M.metal, 0, -0.032, 0);
    b.add(ball, string);
    g.add(b);
  });
  const pickle = item(new THREE.Group(), { action: 'find', hangable: true, reward: true, label: 'Weihnachtsgurke', detail: 'The Christmas pickle: whoever finds it gets an extra present. You found it!' });
  pickle.name = 'act_orn_pickle';
  pickle.position.set(0.95, 0.62, -0.05);
  const pk = mesh(new THREE.CapsuleGeometry(0.016, 0.06, 4, 8), glass(0x3f6b2a), 0, -0.09, 0);
  pickle.add(pk);
  g.add(pickle);
  // the Herrnhut star: a paper shell round a warm core
  const star = item(new THREE.Group(), { action: 'light', label: 'Herrnhuter Stern' });
  star.name = 'act_orn_herrnhut';
  star.position.set(-1.05, 0.62, -0.05);
  const shell = mesh(new THREE.IcosahedronGeometry(0.07, 0), new THREE.MeshStandardMaterial({ color: 0xf2e6c8, roughness: 0.8, flatShading: true }), 0, -0.12, 0);
  const core = mesh(new THREE.SphereGeometry(0.03, 10, 8), new THREE.MeshStandardMaterial({ name: 'orn_core', color: 0xffd9a0, emissive: 0xffc27a, emissiveIntensity: 0.2 }), 0, -0.12, 0);
  core.name = 'herrnhut_core';
  star.add(shell, core);
  g.add(star);
  // the nutcracker: a body, and a jaw hinged at its back
  const nut = item(new THREE.Group(), { action: 'jaw', label: 'Nussknacker', jaw: 'act_orn_nutcracker_jaw' });
  nut.name = 'act_orn_nutcracker';
  nut.position.set(-0.7, 0, 0.05);
  nut.add(mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.24, 10), colorMat(0xa3162c, 0.6), 0, 0.12, 0));
  nut.add(mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.08, 10), colorMat(0xe8c9a0, 0.7), 0, 0.28, 0));
  const jaw = mesh(new THREE.BoxGeometry(0.05, 0.02, 0.04), colorMat(0xf2f2ee, 0.8), 0, 0.245, 0.02, 'act_orn_nutcracker_jaw');
  nut.add(jaw);
  g.add(nut);
  // the Räuchermännchen, smoke at its mouth
  const smoker = item(new THREE.Group(), { action: 'smoke', label: 'Räuchermännchen', fx: 'fx_smoke_1' });
  smoker.name = 'act_orn_smoker';
  smoker.position.set(-0.35, 0, 0.05);
  smoker.add(mesh(new THREE.CylinderGeometry(0.035, 0.045, 0.2, 10), colorMat(0x2e4f7a, 0.7), 0, 0.1, 0));
  const fx = new THREE.Object3D(); fx.name = 'fx_smoke_1'; fx.position.set(0, 0.2, 0.04); smoker.add(fx);
  g.add(smoker);
  // the Schwibbogen: an arch with five candles, flames out
  const arch = item(new THREE.Group(), { action: 'candles', label: 'Schwibbogen' });
  arch.name = 'act_orn_schwibbogen';
  arch.position.set(0.2, 0, 0.05);
  const bow = mesh(new THREE.TorusGeometry(0.2, 0.012, 6, 24, Math.PI), colorMat(0x7a5230, 0.8), 0, 0.02, 0);
  arch.add(bow);
  const flameMat = new THREE.MeshStandardMaterial({ name: 'flame', color: 0xffc070, emissive: 0xffa040, emissiveIntensity: 2.5 });
  for (let i = 0; i < 5; i++) {
    const a = Math.PI * (0.15 + 0.175 * i);
    const c = new THREE.Group(); c.name = `act_orn_candle_${i}`;
    c.position.set(Math.cos(a) * 0.2, 0.02 + Math.sin(a) * 0.2 + 0.03, 0);
    c.add(mesh(new THREE.ConeGeometry(0.006, 0.02, 6), flameMat, 0, 0.01, 0));
    c.userData.item = { action: 'light', label: `Kerze ${i + 1}` };
    arch.add(c);
  }
  g.add(arch);
  // a little display tree with hooks
  const tree = new THREE.Group(); tree.name = 'standin_display_tree'; tree.position.set(0.7, 0, 0.05);
  tree.add(mesh(new THREE.ConeGeometry(0.16, 0.5, 10), colorMat(0x234a2c, 0.9), 0, 0.3, 0));
  for (let i = 0; i < 8; i++) {
    const h = new THREE.Object3D(); h.name = `hook_tree_${i}`;
    const a = i * 2.4, y = 0.12 + (i % 4) * 0.09, r = 0.15 - (i % 4) * 0.03;
    h.position.set(Math.cos(a) * r, y, Math.sin(a) * r + 0.02);
    tree.add(h);
  }
  g.add(tree);
}
