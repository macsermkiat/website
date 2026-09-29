// Stand-in market stall (section or deco), 4 m wide, front facing +Z, counter top at 1.05 m.
import * as THREE from 'three';
import { mats, mesh, empty, signMesh, bulbString, catenary, colorMat, mergeStatic, rng } from './kit.js';
import { buildPerson } from './people.js';

export const STALL = { W: 4, D: 2.8, H: 2.6, TOP: 1.075 };

export function buildStallStandin({ label, place = null, deco = false, seed = 1, kind = '' }) {
  const M = mats();
  const { W, D, H, TOP } = STALL;
  const fz = D / 2 + 0.12;
  const g = new THREE.Group();
  g.name = `standin_${place || kind || 'stall'}`;

  // shell
  g.add(mesh(new THREE.BoxGeometry(W + 0.3, 0.16, D + 0.3), M.woodDark, { y: 0.08 }));
  g.add(mesh(new THREE.BoxGeometry(W, H, 0.1), M.wood, { y: H / 2, z: -D / 2 }));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.1, H, D), M.wood, { x: (sx * W) / 2, y: H / 2 }));
  g.add(mesh(new THREE.BoxGeometry(W, 1.0, 0.1), M.wood, { y: 0.5, z: D / 2 }));
  g.add(mesh(new THREE.BoxGeometry(W + 0.3, 0.07, 0.6), M.counter, { y: 1.04, z: D / 2 + 0.1 }));
  g.add(mesh(new THREE.BoxGeometry(W, 0.6, 0.1), M.wood, { y: H - 0.3, z: D / 2 }));
  const sign = signMesh(label, 3.3, 0.52);
  sign.name = 'sign';
  sign.position.set(0, H - 0.3, D / 2 + 0.056);
  g.add(sign);
  g.add(mesh(new THREE.BoxGeometry(W - 0.2, 0.04, 0.04), M.lampGlass, { y: H - 0.63, z: D / 2 - 0.06 }));
  // gables and roof
  const tri = new THREE.Shape();
  tri.moveTo(-W / 2 - 0.1, 0); tri.lineTo(0, 1.2); tri.lineTo(W / 2 + 0.1, 0); tri.closePath();
  const tg = new THREE.ExtrudeGeometry(tri, { depth: 0.08, bevelEnabled: false });
  g.add(mesh(tg, M.wood, { y: H, z: D / 2 - 0.04 }));
  g.add(mesh(tg, M.wood, { y: H, z: -D / 2 - 0.04 }));
  const half = W / 2 + 0.4, rise = 1.25, len = Math.hypot(half, rise), ang = Math.atan2(rise, half);
  [-1, 1].forEach((s, i) => {
    g.add(mesh(new THREE.BoxGeometry(len, 0.1, D + 0.8), M.roof, { x: (s * half) / 2, y: H + rise / 2 + 0.06, rz: -s * ang }));
    const cap = mesh(new THREE.BoxGeometry(len + 0.02, 0.09, D + 0.82), M.snow, { x: (s * half) / 2 - s * Math.sin(ang) * 0.08, y: H + rise / 2 + 0.06 + Math.cos(ang) * 0.09, rz: -s * ang, name: `snow_${i}` });
    g.add(cap);
  });
  g.add(mesh(new THREE.BoxGeometry(0.18, 0.18, D + 0.9), M.woodDark, { y: H + rise + 0.08 }));
  // eave bulbs
  const eb = [];
  for (const s of [-1, 1]) for (let i = 0; i <= 11; i++) { const t = i / 11; eb.push(new THREE.Vector3(s * half * (1 - t), H + rise * t - 0.02, D / 2 + 0.42)); }
  g.add(bulbString('bulbs_0', eb));
  // garland under the counter
  const gc = new THREE.CatmullRomCurve3(catenary(new THREE.Vector3(-W / 2, 0.95, D / 2 + 0.09), new THREE.Vector3(W / 2, 0.95, D / 2 + 0.09), 0.25, 12));
  g.add(mesh(new THREE.TubeGeometry(gc, 40, 0.055, 6), M.green));
  for (let i = 1; i < 8; i++) { const p = gc.getPoint(i / 8); g.add(mesh(new THREE.SphereGeometry(0.05, 10, 8), i % 2 ? M.brass : M.red, { x: p.x, y: p.y - 0.07, z: p.z + 0.03 })); }
  // back shelves
  for (const y of [1.62, 2.1]) g.add(mesh(new THREE.BoxGeometry(W - 0.2, 0.05, 0.3), M.woodDark, { y, z: -D / 2 + 0.22 }));
  if (deco) g.add(mesh(new THREE.PlaneGeometry(W - 0.3, 1.4), colorMat(0x8c5424, 1), { y: 1.75, z: -D / 2 + 0.07 }));

  // engine nodes
  g.add(empty('slot_counter', 0, TOP, D / 2 + 0.1));
  g.add(empty('slot_shelf_1', 0, 1.645, -D / 2 + 0.22));
  g.add(empty('slot_shelf_2', 0, 2.125, -D / 2 + 0.22));
  g.add(empty('slot_vendor', 0.8, 0, -0.3));
  g.add(empty('slot_sign', 0, H - 0.3, D / 2 + 0.06));
  g.add(empty('slot_front', 0, 0, D / 2 + 1.2));
  g.add(empty('light_0', 0, 2.05, 0.9));
  if (!deco) {
    g.add(empty('light_1', 0, 1.5, D / 2 + 1.6));
    g.add(empty('cam_view', 0, 2.8, 6.8));
    g.add(empty('cam_target', 0, 1.6, 0));
  }

  const r = rng(seed * 17 + 3);
  const vendor = buildPerson(r, { arms: 'down' });
  vendor.name = 'vendor';
  vendor.position.set(0.8, 0, -0.3);
  g.add(vendor);

  const goods = GOODS[place || kind];
  if (goods) goods(g, { M, TOP, fz, D, W, r });
  mergeStatic(g);
  return g;
}

const GOODS = {
  glueh(g, { M, TOP, fz, D }) {
    const mugG = new THREE.LatheGeometry([[0.001, 0], [0.07, 0], [0.075, 0.02], [0.075, 0.14], [0.068, 0.145], [0.064, 0.02]].map((p) => new THREE.Vector2(p[0], p[1])), 16);
    const hG = new THREE.TorusGeometry(0.04, 0.012, 6, 12, Math.PI);
    for (let i = 0; i < 9; i++) {
      const x = -1.7 + i * 0.26;
      g.add(mesh(mugG, M.mug, { x, y: TOP, z: fz + (i % 2) * 0.1 }));
      g.add(mesh(hG, M.mug, { x: x + 0.075, y: TOP + 0.075, z: fz + (i % 2) * 0.1, rz: -Math.PI / 2 }));
    }
    const pot = new THREE.Group();
    pot.name = 'act_pot';
    pot.position.set(1.3, TOP, fz - 0.05);
    pot.add(mesh(new THREE.CylinderGeometry(0.32, 0.3, 0.5, 24), M.metal, { y: 0.25 }));
    pot.add(mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.02, 24), M.wine, { y: 0.49 }));
    const lid = mesh(new THREE.CylinderGeometry(0.33, 0.33, 0.03, 24), M.metal, { y: 0.52, name: 'act_pot_lid' });
    lid.add(mesh(new THREE.SphereGeometry(0.04, 8, 6), M.darkMetal, { y: 0.04 }));
    lid.position.set(-0.36, 0.26, 0.05); lid.rotation.z = 1.2; // resting open against the pot
    pot.add(lid);
    g.add(pot);
    for (let i = 0; i < 14; i++) g.add(mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.32, 10), i % 3 ? colorMat(0x5a0f1e, 0.1, 0.1) : colorMat(0x1d4a24, 0.1, 0.1), { x: -1.7 + i * 0.26, y: 1.645 + 0.16, z: -D / 2 + 0.2 }));
  },
  bier(g, { M, TOP, fz, D }) {
    for (let i = 0; i < 6; i++) {
      const x = -1.7 + i * 0.22;
      g.add(mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.24, 14), M.beer, { x, y: TOP + 0.12, z: fz }));
      g.add(mesh(new THREE.CylinderGeometry(0.062, 0.062, 0.04, 14), M.foam, { x, y: TOP + 0.26, z: fz }));
    }
    g.add(mesh(new THREE.BoxGeometry(0.9, 0.1, 0.12), M.metal, { x: 0.6, y: TOP + 0.5, z: fz - 0.1 }));
    g.add(mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 12), M.metal, { x: 0.6, y: TOP + 0.25, z: fz - 0.1 }));
    [0xc9a341, 0x8e2a3f, 0x2f5c7a].forEach((c, i) => {
      const pv = new THREE.Group();
      pv.name = `act_tap_${i}`;
      pv.position.set(0.3 + i * 0.3, TOP + 0.55, fz - 0.1);
      pv.add(mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.3, 10), colorMat(c, 0.3), { y: 0.17 }));
      pv.add(mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.12, 8), M.metal, { y: -0.08 }));
      g.add(pv);
    });
    const barrelG = new THREE.LatheGeometry(Array.from({ length: 12 }, (_, i) => { const t = i / 11; return new THREE.Vector2(0.36 + Math.sin(t * Math.PI) * 0.07, t * 0.95); }), 24);
    for (const [bx, bz] of [[-2.55, 1.9], [2.6, 1.8]]) {
      g.add(mesh(barrelG, M.woodDark, { x: bx, z: bz }));
      for (const hy of [0.15, 0.8]) g.add(mesh(new THREE.TorusGeometry(0.4, 0.018, 6, 24), M.darkMetal, { x: bx, y: hy, z: bz, rx: Math.PI / 2 }));
    }
    for (let i = 0; i < 14; i++) g.add(mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.3, 10), colorMat(0x1d4a24, 0.1, 0.1), { x: -1.7 + i * 0.26, y: 1.645 + 0.15, z: -D / 2 + 0.2 }));
  },
  wurst(g, { M, TOP, fz, W }) {
    g.add(mesh(new THREE.BoxGeometry(3, 0.12, 0.5), M.darkMetal, { y: TOP + 0.06, z: fz - 0.05 }));
    const grill = mesh(new THREE.BoxGeometry(2.8, 0.02, 0.42), M.coal.clone(), { y: TOP + 0.13, z: fz - 0.05, name: 'act_grill' });
    g.add(grill);
    for (let i = 0; i < 12; i++) g.add(mesh(new THREE.BoxGeometry(0.01, 0.01, 0.46), M.darkMetal, { x: -1.35 + i * 0.245, y: TOP + 0.16, z: fz - 0.05 }));
    const sg = new THREE.CapsuleGeometry(0.035, 0.2, 4, 8);
    for (let i = 0; i < 9; i++) g.add(mesh(sg, M.sausage, { x: -1.25 + i * 0.3, y: TOP + 0.2, z: fz - 0.05 + (i % 2 ? 0.08 : -0.08), rz: Math.PI / 2, name: `act_sausage_${i}` }));
    for (let i = 0; i < 16; i++) g.add(mesh(sg, M.sausage, { x: -1.8 + i * 0.24, y: 2.0, z: -0.4 }));
    g.add(mesh(new THREE.CylinderGeometry(0.006, 0.006, W, 6), M.darkMetal, { y: 2.16, z: -0.4, rz: Math.PI / 2 }));
    g.add(empty('act_smoke', 0, TOP + 0.25, fz - 0.05));
  },
  books(g, { M, TOP, fz, D, W, r }) {
    const pal = [0x7a1e2c, 0x1f3a5a, 0x2e5a3a, 0xb88a2e, 0x5a3a6a, 0xd9cbb0, 0x3a2a22, 0x8a4a2a, 0x1a1a1f, 0x2a6a7a];
    const bg = new THREE.BoxGeometry(1, 1, 1);
    let n = 0;
    for (const [si, sy] of [0.45, 1.05, 1.65, 2.2].entries()) {
      g.add(mesh(new THREE.BoxGeometry(W - 0.2, 0.04, 0.34), M.counter, { y: sy - 0.02, z: -D / 2 + 0.22 }));
      let x = -W / 2 + 0.15;
      while (x < W / 2 - 0.2) {
        const bw = 0.035 + r() * 0.05, bh = 0.2 + r() * 0.14;
        const b = mesh(bg, colorMat(pal[(r() * pal.length) | 0], 0.7), { x: x + bw / 2, y: sy + bh / 2, z: -D / 2 + 0.22 + (r() - 0.5) * 0.04, rz: r() < 0.06 ? 0.25 : 0 });
        b.scale.set(bw, bh, 0.2 + r() * 0.06);
        // books at eye level can be pulled; the rest are merged into the shelf
        if (si >= 1 && si <= 2 && r() < 0.4) b.name = `act_book_${n++}`;
        g.add(b);
        x += bw + 0.004;
      }
    }
    for (let s = 0; s < 7; s++) {
      const cx = -1.7 + s * 0.5;
      let y = TOP;
      for (let k = 0; k < 3 + ((r() * 4) | 0); k++) {
        const bh = 0.03 + r() * 0.03;
        const b = mesh(bg, colorMat(pal[(r() * pal.length) | 0], 0.7), { x: cx + (r() - 0.5) * 0.05, y: y + bh / 2, z: fz - 0.02, ry: (r() - 0.5) * 0.4 });
        b.scale.set(0.3, bh, 0.22);
        g.add(b);
        y += bh;
      }
    }
    g.add(mesh(new THREE.BoxGeometry(0.5, 0.02, 0.32), M.cream, { x: 1.2, y: TOP + 0.02, z: fz + 0.02, ry: -0.2 }));
    g.add(mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.5, 8), M.brass, { x: 1.75, y: TOP + 0.25, z: fz - 0.15 }));
    g.add(mesh(new THREE.ConeGeometry(0.12, 0.14, 16, 1, true), M.green, { x: 1.75, y: TOP + 0.5, z: fz - 0.15 }));
    g.add(mesh(new THREE.SphereGeometry(0.04, 10, 8), M.lampGlass, { x: 1.75, y: TOP + 0.46, z: fz - 0.15 }));
  },
  // deco stalls: a few simple goods so the lanes read as stocked
  lebkuchen(g, o) { decoRow(g, o, 0x7a4322, 'heart'); },
  mandeln(g, o) { decoRow(g, o, 0x8a5a2a, 'bowl'); },
  maroni(g, o) { decoRow(g, o, 0x4a2414, 'bowl'); },
  kerzen(g, o) { decoRow(g, o, 0xefe4cf, 'candle'); },
  holzspielzeug(g, o) { decoRow(g, o, 0xb3263a, 'toy'); },
  spielzeug(g, o) { decoRow(g, o, 0xb3263a, 'toy'); },
  christbaumschmuck(g, o) { decoRow(g, o, 0xd9a441, 'bauble'); },
  schmuck(g, o) { decoRow(g, o, 0xd9a441, 'bauble'); },
  puffer(g, o) { decoRow(g, o, 0xb8762e, 'plate'); },
  kaese(g, o) { decoRow(g, o, 0xe8b64a, 'wheel'); },
  crepes(g, o) { decoRow(g, o, 0xd9a45a, 'plate'); },
  kartoffelpuffer(g, o) { decoRow(g, o, 0xb8762e, 'plate'); },
};

function decoRow(g, { TOP, fz, D, r }, color, shape) {
  const cols = [color, 0xb3263a, 0x2f5c7a, 0xd9a441, 0x3f6a3a, 0xefe4cf];
  const geo = {
    heart: new THREE.CylinderGeometry(0.1, 0.1, 0.03, 12),
    bowl: new THREE.CylinderGeometry(0.2, 0.14, 0.12, 16),
    candle: new THREE.CylinderGeometry(0.05, 0.05, 0.25, 10),
    toy: new THREE.BoxGeometry(0.14, 0.3, 0.14),
    bauble: new THREE.SphereGeometry(0.07, 12, 8),
    wheel: new THREE.CylinderGeometry(0.26, 0.26, 0.14, 20),
    plate: new THREE.CylinderGeometry(0.3, 0.3, 0.06, 20),
  }[shape];
  const n = shape === 'wheel' || shape === 'plate' ? 4 : shape === 'bowl' ? 5 : 12;
  for (let i = 0; i < n; i++) {
    const x = -1.6 + (i * 3.2) / Math.max(1, n - 1);
    const h = geo.parameters.height ?? 0.14;
    g.add(mesh(geo, colorMat(i % 3 ? color : cols[i % cols.length], 0.5, shape === 'bauble' ? 0.8 : 0), { x, y: TOP + h / 2, z: fz - 0.02, rx: shape === 'heart' ? 0 : 0 }));
  }
  for (const y of [1.645, 2.125]) {
    for (let i = 0; i < 12; i++) {
      const h = geo.parameters.height ?? 0.14;
      const m = mesh(geo, colorMat(cols[(i + (y > 2 ? 1 : 0)) % cols.length], 0.55, shape === 'bauble' ? 0.8 : 0), { x: -1.7 + i * 0.31, y: y + (h * 0.6) / 2, z: -D / 2 + 0.22 });
      m.scale.setScalar(0.6);
      g.add(m);
    }
  }
}
