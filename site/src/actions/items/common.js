// Shared helpers for the clickable items (actions/items/*): frames, boxes, liquids and small effects.
import * as THREE from 'three';
import inventory from 'virtual:market-inventory';

export const UP = new THREE.Vector3(0, 1, 0);

/** The vendor's items.json entry for a node (keyed by node name), or {}. */
export function infoOf(node) {
  return inventory.items?.[node.name] || node.userData?.item || {};
}

/** Kind of an act_ node: items.json's `kind`, else the word after act_ (act_glass_3 -> glass). */
export function kindOf(node) {
  // the ornament shop's goods (act_orn_<kind>_<n>, ADR 0004) are one kind for the clicks; their own action is in
  // items.json (`action`: ring, light, jaw, smoke, candles, hang, find)
  if (/^act_orn_/i.test(node.name || '')) return /_mesh(_\d+)?(\.\d+)?$/i.test(node.name) ? null : 'orn';
  const k = infoOf(node).kind;
  if (k) return String(k).toLowerCase();
  const m = /^act_([a-z]+?)(?:_\d+)?$/i.exec(node.name || '');
  return m ? m[1].toLowerCase() : null;
}

/** Bounding box of a node's meshes in `frame`'s local space (the world when frame is null). Hidden meshes count. */
export function boxOf(node, frame = null) {
  node.updateWorldMatrix(true, true);
  const inv = frame ? new THREE.Matrix4().copy(frame.matrixWorld).invert() : null;
  const box = new THREE.Box3(), tmp = new THREE.Box3(), m = new THREE.Matrix4();
  node.traverse((o) => {
    if (!o.isMesh || o.userData.itemFx) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    m.copy(o.matrixWorld);
    if (inv) m.premultiply(inv);
    box.union(tmp.copy(o.geometry.boundingBox).applyMatrix4(m));
  });
  return box;
}

/** A world-space direction in a node's parent frame (for moving a node by world offsets). */
export function worldDirToParent(node, dir) {
  const q = node.parent.getWorldQuaternion(new THREE.Quaternion()).invert();
  const s = node.parent.getWorldScale(new THREE.Vector3());
  return dir.clone().applyQuaternion(q).divide(s);
}

/** A world point in a node's parent frame. */
export function worldToParent(node, p) {
  return node.parent.worldToLocal(p.clone());
}

/**
 * The pose of a node rotated by `angle` about a world axis through a world point, starting from its rest pose
 * (p0, q0 in its parent frame). Writes into node.position / node.quaternion.
 */
const _m = new THREE.Matrix4(), _r = new THREE.Matrix4(), _t = new THREE.Matrix4(), _b = new THREE.Matrix4(), _pw = new THREE.Matrix4(), _pinv = new THREE.Matrix4();
const _s = new THREE.Vector3(), _q = new THREE.Quaternion(), _p = new THREE.Vector3();
export function rotateAbout(node, rest, pointWorld, axisWorld, angle) {
  node.parent.updateWorldMatrix(true, false);
  _pw.copy(node.parent.matrixWorld);
  _pinv.copy(_pw).invert();
  _m.compose(rest.p, rest.q, node.scale).premultiply(_pw); // rest pose in the world
  _r.makeRotationAxis(axisWorld, angle);
  _b.makeTranslation(-pointWorld.x, -pointWorld.y, -pointWorld.z);
  _t.makeTranslation(pointWorld.x, pointWorld.y, pointWorld.z).multiply(_r).multiply(_b);
  _m.premultiply(_t).premultiply(_pinv);
  _m.decompose(_p, _q, _s);
  node.position.copy(_p);
  node.quaternion.copy(_q);
}

export const rest = (node) => ({ p: node.position.clone(), q: node.quaternion.clone() });
export const restore = (node, r) => { node.position.copy(r.p); node.quaternion.copy(r.q); };

/** The first mesh under a node whose material name matches. */
export function meshByMaterial(node, re) {
  let hit = null;
  node.traverse((o) => { if (!hit && o.isMesh && !o.userData.itemFx && re.test(o.material?.name || '')) hit = o; });
  return hit;
}

// ---------- liquids ----------

export const WINE = new THREE.MeshStandardMaterial({ name: 'item_wine', color: 0x3a0610, roughness: 0.12, emissive: 0x1a0205 });
export const BEER = new THREE.MeshStandardMaterial({ name: 'item_beer', color: 0xd9901c, roughness: 0.15, emissive: 0x2a1200, transparent: true, opacity: 0.85 });
export const FOAM = new THREE.MeshStandardMaterial({ name: 'item_foam', color: 0xfff4dc, roughness: 0.95 });
export const MUSTARD = new THREE.MeshStandardMaterial({ name: 'item_mustard', color: 0xc99a14, roughness: 0.55 });

/** A falling stream of liquid (a thin tapered cylinder) drawn between two world points. */
export function createStream(scene, material, radius = 0.006) {
  const geo = new THREE.CylinderGeometry(radius * 0.8, radius, 1, 8, 1, true);
  geo.translate(0, -0.5, 0); // hangs down from its origin
  const m = new THREE.Mesh(geo, material);
  m.name = 'item_stream';
  m.userData.itemFx = true;
  m.visible = false;
  m.castShadow = false;
  scene.add(m);
  const a = new THREE.Vector3(), b = new THREE.Vector3();
  return {
    mesh: m,
    /** Show the stream from `from` down to `to` (world points), or hide it with null. */
    set(from, to) {
      if (!from) { m.visible = false; return; }
      a.copy(from); b.copy(to);
      const len = Math.max(0.001, a.distanceTo(b));
      m.position.copy(a);
      m.scale.set(1, len, 1);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), b.clone().sub(a).normalize());
      m.visible = true;
    },
  };
}

/**
 * A liquid surface inside a vessel, as a child of the vessel's pivot so it moves with it. `level(f)` puts the
 * surface at f (0 empty .. 1 full) of the way up the inside. Built from the vessel's current world box, so an
 * upside-down mug is turned upright first.
 */
export function createSurface(pivot, material, { fill = 0.84, radius = 0.4, floor = 0.12 } = {}) {
  const box = boxOf(pivot);
  const size = box.getSize(new THREE.Vector3());
  const c = box.getCenter(new THREE.Vector3());
  const r = Math.max(0.01, Math.min(size.x, size.z) * radius);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(r, 24), material);
  disc.name = 'item_surface';
  disc.userData.itemFx = true;
  disc.castShadow = false;
  pivot.add(disc);
  const bottom = box.min.y + size.y * floor, top = box.min.y + size.y * fill;
  const world = new THREE.Vector3(), q = new THREE.Quaternion();
  const face = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
  // the pivot's pose when the surface was made: later levels are set relative to it
  pivot.updateWorldMatrix(true, false);
  const inv = pivot.matrixWorld.clone().invert();
  const pq = pivot.getWorldQuaternion(new THREE.Quaternion()).invert();
  return {
    mesh: disc,
    top: () => pivot.localToWorld(disc.position.clone()),
    level(f) {
      world.set(c.x, bottom + (top - bottom) * Math.max(0, Math.min(1, f)), c.z).applyMatrix4(inv);
      disc.position.copy(world);
      disc.quaternion.copy(q.copy(pq).multiply(face));
      disc.visible = f > 0.02;
    },
  };
}

// ---------- effects ----------

let sparkTex = null;
function dotTexture() {
  if (sparkTex) return sparkTex;
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,220,160,.8)'); gr.addColorStop(1, 'rgba(255,120,20,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
  sparkTex = new THREE.CanvasTexture(c);
  return sparkTex;
}

/** Sparks off the coals: a burst of small hot dots that fly up and die out. */
export function createSparks(scene, count = 24) {
  const mat = new THREE.SpriteMaterial({ map: dotTexture(), color: 0xffa040, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const list = [];
  for (let i = 0; i < count; i++) {
    const s = new THREE.Sprite(mat);
    s.name = 'item_spark';
    s.visible = false;
    s.scale.setScalar(0.018);
    scene.add(s);
    list.push({ s, v: new THREE.Vector3(), life: 0 });
  }
  let next = 0;
  return {
    burst(at, n = 10) {
      for (let i = 0; i < n; i++) {
        const p = list[next++ % list.length];
        p.s.position.copy(at).add(new THREE.Vector3((Math.random() - 0.5) * 0.25, 0.02, (Math.random() - 0.5) * 0.12));
        p.v.set((Math.random() - 0.5) * 0.5, 0.8 + Math.random() * 1.1, (Math.random() - 0.5) * 0.3);
        p.life = 0.5 + Math.random() * 0.7;
        p.s.visible = true;
      }
    },
    update(dt) {
      for (const p of list) {
        if (p.life <= 0) continue;
        p.life -= dt;
        p.v.y -= dt * 0.6;
        p.s.position.addScaledVector(p.v, dt);
        p.s.scale.setScalar(0.012 + 0.012 * Math.max(0, p.life));
        if (p.life <= 0) p.s.visible = false;
      }
    },
  };
}

/** Wrap text into lines that fit `width` pixels on a 2D canvas context. */
export function wrap(g, text, width) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = '';
  for (const w of words) {
    const t = line ? `${line} ${w}` : w;
    if (g.measureText(t).width > width && line) { lines.push(line); line = w; } else line = t;
  }
  if (line) lines.push(line);
  return lines;
}

export const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
