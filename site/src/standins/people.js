// Stand-in people: one merged, vertex-coloured mesh per person so a crowd costs one draw call each.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const SKIN = [0xe8c4a6, 0xd7a98a, 0xc28a68, 0x9c6a4c, 0xf0d2bb, 0xb57d5c];
const COATS = [0x2b2e3f, 0x4a2430, 0x2d3b48, 0x3b302b, 0x223040, 0x51403a, 0x1e2226, 0x5a4a3a, 0x33424a];
const SCARVES = [0xb8324b, 0xd9a441, 0x3f7fa3, 0xe6e1d3, 0x6a9a5a, 0x8a4bb0, 0xc85a2a];
const HAIR = [0x1a1412, 0x2e2018, 0x4a3020, 0x121010];
const PANTS = [0x1b1c22, 0x2a2620, 0x1d2230];

const G = {
  leg: new THREE.CapsuleGeometry(0.075, 0.62, 3, 8),
  arm: new THREE.CapsuleGeometry(0.062, 0.42, 3, 8),
  head: new THREE.SphereGeometry(0.115, 14, 10),
  beanie: new THREE.SphereGeometry(0.125, 14, 7, 0, Math.PI * 2, 0, Math.PI / 2),
  pom: new THREE.SphereGeometry(0.045, 8, 6),
  hair: new THREE.SphereGeometry(0.12, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.55),
  scarf: new THREE.TorusGeometry(0.105, 0.048, 6, 14),
  coat: new THREE.LatheGeometry([[0.29, 0.58], [0.27, 0.8], [0.24, 1.05], [0.23, 1.28], [0.2, 1.4], [0.12, 1.46], [0.001, 1.48]].map((p) => new THREE.Vector2(p[0], p[1])), 14),
  shoe: new THREE.BoxGeometry(0.1, 0.07, 0.22),
  mug: new THREE.CylinderGeometry(0.045, 0.04, 0.1, 10),
};

const MAT = new THREE.MeshStandardMaterial({ name: 'standin_person', vertexColors: true, roughness: 0.8 });

function part(geo, color, m) {
  const g = (geo.index ? geo.toNonIndexed() : geo.clone());
  g.applyMatrix4(m);
  const c = new THREE.Color(color);
  const n = g.attributes.position.count;
  const col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'color'].includes(k)) g.deleteAttribute(k);
  return g;
}

const M4 = (x, y, z, rx = 0, ry = 0, rz = 0, s = 1) =>
  new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)), new THREE.Vector3(s, s, s));

/**
 * A person as one mesh. Options: seated (legs forward), mug (holds a mug), arms: 'down' | 'play' | 'mug'.
 * The group's userData.head is the local head height, for speech bubbles.
 */
export function buildPerson(r, { mug = false, seated = false, arms = 'down', scale } = {}) {
  const pick = (a) => a[(r() * a.length) | 0];
  const coat = pick(COATS), pants = pick(PANTS), skin = pick(SKIN), scarf = pick(SCARVES);
  const parts = [];
  const dy = seated ? -0.32 : 0;
  for (const sx of [-0.1, 0.1]) {
    if (seated) {
      parts.push(part(G.leg, pants, M4(sx, 0.48, 0.28, Math.PI / 2 - 0.1)));
      parts.push(part(G.shoe, 0x141212, M4(sx, 0.05, 0.62)));
    } else {
      parts.push(part(G.leg, pants, M4(sx, 0.42, 0)));
      parts.push(part(G.shoe, 0x141212, M4(sx, 0.035, 0.04)));
    }
  }
  parts.push(part(G.coat, coat, M4(0, dy, 0)));
  const holdsMug = arms === 'mug' || mug;
  for (const sx of [-1, 1]) {
    const shoulder = M4(sx * 0.25, 1.36 + dy, 0);
    if (holdsMug && sx === 1) {
      // bent arm: upper arm hangs a little forward, forearm raised to hold the mug at chest height
      const upper = shoulder.clone().multiply(M4(0, 0, 0, -0.25, 0, 0.08));
      parts.push(part(G.arm, coat, upper.clone().multiply(M4(0, -0.15, 0)).multiply(new THREE.Matrix4().makeScale(1, 0.55, 1))));
      const elbow = upper.clone().multiply(M4(0, -0.3, 0, -1.35, 0, 0));
      parts.push(part(G.arm, coat, elbow.clone().multiply(M4(0, -0.13, 0)).multiply(new THREE.Matrix4().makeScale(0.95, 0.5, 0.95))));
      parts.push(part(G.mug, 0xa3162c, elbow.clone().multiply(M4(0, -0.3, 0.03, 1.35 + 0.25, 0, 0))));
      continue;
    }
    let rx = 0, rz = sx * 0.12;
    if (arms === 'play') { rx = -1.1; rz = sx * 0.2; }
    parts.push(part(G.arm, coat, shoulder.clone().multiply(M4(0, 0, 0, rx, 0, rz)).multiply(M4(0, -0.26, 0))));
  }
  parts.push(part(G.head, skin, M4(0, 1.6 + dy, 0)));
  if (r() < 0.5) {
    const hc = pick(SCARVES);
    parts.push(part(G.beanie, hc, M4(0, 1.63 + dy, 0)));
    parts.push(part(G.pom, hc, M4(0, 1.76 + dy, 0)));
  } else parts.push(part(G.hair, pick(HAIR), M4(0, 1.615 + dy, 0, -0.25)));
  parts.push(part(G.scarf, scarf, M4(0, 1.46 + dy, 0, Math.PI / 2)));
  const geo = mergeGeometries(parts);
  const m = new THREE.Mesh(geo, MAT);
  m.name = 'person';
  m.castShadow = true;
  m.userData.keep = true;
  const g = new THREE.Group();
  g.add(m);
  const s = scale ?? 0.93 + r() * 0.14;
  g.scale.setScalar(s);
  g.userData.head = 1.6 + dy;
  g.userData.person = true;
  return g;
}
