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
  if (added) warn?.(`${place.entry.id}: no act_ props yet; added stand-in goods for the panel actions.`);
  return added;
}
