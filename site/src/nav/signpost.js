// The market's finger signpost: one arm per place (act_sign_<placeid>), each pointing the way. Clicking an arm
// walks there. The architect's own signpost (act_sign_ nodes in square.glb) is used when it exists; until then
// the engine builds a wooden one in the foreground of the home view. A small copy of it sits on the screen
// (ui/signboard.js) for the keyboard, phones and anyone who would rather not aim.
import * as THREE from 'three';
import { woodMaterial, paintMaterial, lampGlassMaterial, brassMaterial, woodBox } from '../world/materials.js';
import { label, fitSize } from '../world/text.js';

/** German place names on the arms (the section in English underneath). */
export const ARM_NAMES = { glueh: 'Glühwein', bier: 'Bier vom Fass', wurst: 'Bratwurst', books: 'Bücher', band: 'Musik', ferris: 'Riesenrad', carousel: 'Karussell', schmuck: 'Christbaumschmuck' };
export const SIGN_AT = [-3.4, 0, 19.2];

/**
 * Build or find the signpost. order: place ids (top arm first); sub(id): the English line; home: the home camera.
 * Returns { group, arms: { id: Object3D }, source, pick(obj) -> place id | null }.
 */
export function createSignpost({ scene, market, order, sub, home }) {
  const found = {};
  // the carpenter's signpost (signpost.glb, or act_sign_ boards in square.glb) names its boards by layout id
  const placeOf = (lid) => market.layout.entries.find((e) => e.id === lid)?.place || lid;
  scene.traverse((o) => {
    const m = /^act_sign_(.+)$/i.exec(o.name || '');
    if (!m) return;
    const id = placeOf(m[1].replace(/\.\d+$/, ''));
    if (order.includes(id)) found[id] = o;
  });
  if (Object.keys(found).length) {
    for (const [id, o] of Object.entries(found)) o.traverse((x) => { x.userData.sign = id; });
    return { group: null, arms: found, source: 'act_sign_ nodes (signpost.glb)', pick: pickOf };
  }
  const g = new THREE.Group();
  g.name = 'engine_signpost';
  g.position.fromArray(SIGN_AT);
  const post = woodMaterial('dark', 51);
  const H = 3.05;
  const pole = woodBox(0.13, H, 0.13, post);
  pole.position.y = H / 2;
  g.add(pole);
  const cap = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.16, 4), woodMaterial('green', 52));
  cap.position.y = H + 0.08;
  cap.rotation.y = Math.PI / 4;
  g.add(cap);
  // a lantern on a bracket at the top, so it reads at night
  const bracket = woodBox(0.34, 0.03, 0.03, post);
  bracket.position.set(0.16, H - 0.12, 0);
  g.add(bracket);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 8), lampGlassMaterial());
  lamp.position.set(0.3, H - 0.24, 0);
  const cage = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.15, 6, 1, true), paintMaterial('#1b1a18', 0.5));
  cage.position.copy(lamp.position);
  cage.material.side = THREE.DoubleSide;
  cage.material.wireframe = true;
  g.add(lamp, cage);
  // a stone base
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.32, 0.22, 10), paintMaterial('#55524c', 0.95));
  base.position.y = 0.11;
  g.add(base);

  const cam = new THREE.Vector3().fromArray(home.position);
  const toCam = cam.clone().sub(g.position).setY(0).normalize();
  const arms = {};
  order.forEach((id, i) => {
    const e = market.layout.entries.find((x) => x.place === id);
    if (!e) return;
    const to = new THREE.Vector3(e.position[0], 0, e.position[2]).sub(g.position).setY(0).normalize();
    // the arm points the way, turned partly toward the square's front so its words can be read from home
    let side = to.clone().addScaledVector(toCam, -to.dot(toCam));
    if (side.lengthSq() < 0.02) side = new THREE.Vector3(-toCam.z, 0, toCam.x).multiplyScalar(i % 2 ? 1 : -1);
    side.normalize();
    const dir = side.multiplyScalar(0.85).addScaledVector(to, 0.3).normalize();
    const arm = buildArm(id, ARM_NAMES[id] || id, sub(id), i + 1);
    arm.position.y = H - 0.42 - i * 0.215;
    arm.rotation.y = Math.atan2(-dir.z, dir.x);
    arm.name = `act_sign_${id}`;
    arm.traverse((x) => { x.userData.sign = id; });
    g.add(arm);
    arms[id] = arm;
  });
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  scene.add(g);
  return { group: g, arms, source: 'engine stand-in', pick: pickOf };
}

function pickOf(obj) {
  for (let o = obj; o; o = o.parent) if (o.userData?.sign) return o.userData.sign;
  return null;
}

/** One finger board: tail at the post, the pointed end toward the place, lettered on both faces. */
function buildArm(id, name, subline, n) {
  const L = 1.08, Hh = 0.175, T = 0.032, tip = 0.13;
  const shape = new THREE.Shape();
  shape.moveTo(0, -Hh / 2); shape.lineTo(L - tip, -Hh / 2); shape.lineTo(L, 0); shape.lineTo(L - tip, Hh / 2); shape.lineTo(0, Hh / 2); shape.closePath();
  const geo = new THREE.ExtrudeGeometry(shape, { depth: T, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.005, bevelSegments: 1 });
  geo.translate(0.04, 0, -T / 2);
  // grain along the arm
  const uv = geo.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 1.4, uv.getY(i) * 1.4);
  const board = new THREE.Mesh(geo, woodMaterial('green', 60 + n));
  const g = new THREE.Group();
  g.add(board);
  // a painted cream border inset on both faces
  const border = paintMaterial('#e8dcbc', 0.8);
  for (const s of [1, -1]) {
    const edge = new THREE.Mesh(new THREE.PlaneGeometry(L - tip - 0.06, 0.006), border);
    edge.position.set(0.04 + (L - tip) / 2, Hh / 2 - 0.018, s * (T / 2 + 0.0052));
    edge.rotation.y = s < 0 ? Math.PI : 0;
    const edge2 = edge.clone();
    edge2.position.y = -Hh / 2 + 0.018;
    g.add(edge, edge2);
  }
  const textW = L - tip - 0.16;
  const size = fitSize(name, 'sc', 0.072, textW);
  for (const s of [1, -1]) {
    const face = new THREE.Group();
    face.position.set(0.04 + 0.08 + textW / 2 + (s < 0 ? 0.02 : 0), 0.017, s * (T / 2 + 0.0055));
    face.rotation.y = s < 0 ? Math.PI : 0;
    const t = label(name, { font: 'sc', size, color: '#f1e6c8', glow: 0.18 });
    face.add(t);
    if (subline) { const st = label(subline, { font: 'sansItalic', size: 0.036, color: '#d8c9a2', glow: 0.14 }); st.position.y = -0.054; face.add(st); }
    const num = label(String(n), { font: 'sansBold', size: 0.05, color: '#e6b65e', glow: 0.25 });
    num.position.set(-textW / 2 - 0.045 * (s < 0 ? -1 : 1) * (s < 0 ? -1 : 1), 0.0, 0);
    if (s < 0) num.position.x = textW / 2 + 0.03;
    face.add(num);
    g.add(face);
  }
  // two brass bolts at the post
  for (const s of [1, -1]) { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, T + 0.014, 8), brassMaterial()); b.rotation.x = Math.PI / 2; b.position.set(0.075, s * 0.045, 0); g.add(b); }
  g.userData.armLength = L;
  return g;
}
