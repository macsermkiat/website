// The deco stalls open no panel, but their goods can be looked at: an item lifts a little under the pointer
// and a click shows its small detail on a paper tag (the icing text on a Lebkuchen heart, for one).
// Items are the vendor's act_ nodes in a deco prop set (items.json `detail` or `note`). A Lebkuchen stall whose
// set has none gets three iced hearts made here, hanging from the counter front, until the vendor ships its own.
import * as THREE from 'three';
import { boxOf, rest, restore, worldDirToParent, UP } from './common.js';
import { createWorldTag } from '../util.js';

const HEARTS = [
  { text: ['Frohe', 'Weihnachten'], icing: '#fff7ee', size: 0.24, detail: '“Frohe Weihnachten”, piped in white icing, with sugar holly.' },
  { text: ['Für', 'Dich'], icing: '#ffd9e4', size: 0.19, detail: '“Für Dich” (for you), in pink icing, with three sugar roses.' },
  { text: ['Süßer', 'Schatz'], icing: '#fff7ee', size: 0.2, detail: '“Süßer Schatz” (sweet treasure), in white icing.' },
];

export function createDeco(ctx) {
  const { anim, scene, items, camera, overlay, sfx } = ctx;
  const tag = createWorldTag(overlay, 'booktag itemtag');
  let shown = null, left = 0;

  function addPlaced(p) {
    if (p.entry.kind !== 'deco') return;
    const pseudo = { id: p.entry.id, holder: p.holder, root: p.root, merge: null };
    let n = 0;
    p.root.traverse((o) => {
      if (/^act_/i.test(o.name || '') && !/_mesh(\.\d+)?$/i.test(o.name)) { if (items.add(o, p.entry.id, pseudo, 'deco')) n++; }
    });
    const goods = String(p.entry.goods || p.entry.id || '').toLowerCase();
    if (!n && /lebkuchen/.test(goods)) hangHearts(p, pseudo);
  }

  function hangHearts(p, pseudo) {
    const slot = p.root.getObjectByName('slot_counter');
    if (!slot) return;
    p.root.updateWorldMatrix(true, true);
    // the counter's front edge, in the stall's own frame (front is +Z): its box, near the counter's height
    const c = p.holder.worldToLocal(slot.getWorldPosition(new THREE.Vector3()));
    const box = boxOf(p.root, p.holder);
    const frontZ = Math.min(box.max.z, c.z + 0.45);
    HEARTS.forEach((h, i) => {
      const heart = buildHeart(h);
      heart.name = `act_heart_${i}`;
      heart.position.set(c.x + (i - 1) * 0.62, c.y - 0.2 - (i === 1 ? 0.06 : 0), frontZ + 0.035);
      heart.rotation.y = (i - 1) * 0.08;
      heart.userData.label = `Lebkuchen heart: ${h.text.join(' ')}`;
      heart.userData.item = { detail: h.detail };
      p.holder.add(heart);
      items.add(heart, p.entry.id, pseudo, 'deco');
    });
  }

  function click(item) {
    const detail = item.info.detail || item.info.note || item.node.userData.item?.detail || item.info.name || item.label;
    if (shown === item) { tag.hide(); shown = null; return; }
    shown = item;
    left = 6;
    tag.show(detail, item.node);
    sfx('chime');
    if (item.busy) return;
    // a little swing on its ribbon (or a wobble on the counter)
    items.release(item);
    item.busy = true;
    const node = item.node, r0 = rest(node);
    const ax = worldDirToParent(node, new THREE.Vector3(1, 0, 0)).normalize();
    anim.add(1.6, (k) => { node.quaternion.copy(r0.q).premultiply(new THREE.Quaternion().setFromAxisAngle(ax, Math.sin(k * Math.PI * 4) * 0.18 * (1 - k))); }, () => { restore(node, r0); item.busy = false; });
  }

  return {
    kinds: { deco: click },
    addPlaced,
    api: { decoDetail: () => (shown ? { name: shown.node.name, detail: shown.info.detail || shown.node.userData.item?.detail || shown.label } : null) },
    retract() { tag.hide(); shown = null; },
    update(dt) {
      if (camera) tag.update(camera);
      if (shown && (left -= dt) <= 0) { tag.hide(); shown = null; }
    },
  };
}

// ---------- a Lebkuchen heart ----------

function heartShape(s) {
  const h = new THREE.Shape();
  h.moveTo(0, 0.3 * s);
  h.bezierCurveTo(0, 0.46 * s, -0.24 * s, 0.56 * s, -0.4 * s, 0.4 * s);
  h.bezierCurveTo(-0.58 * s, 0.2 * s, -0.42 * s, -0.08 * s, 0, -0.46 * s);
  h.bezierCurveTo(0.42 * s, -0.08 * s, 0.58 * s, 0.2 * s, 0.4 * s, 0.4 * s);
  h.bezierCurveTo(0.24 * s, 0.56 * s, 0, 0.46 * s, 0, 0.3 * s);
  return h;
}

const DOUGH = new THREE.MeshStandardMaterial({ name: 'item_lebkuchen', color: 0x7b3f1a, roughness: 0.78 });
const RIBBON = new THREE.MeshStandardMaterial({ name: 'item_ribbon', color: 0x2f5aa8, roughness: 0.6 });

function buildHeart({ text, icing, size }) {
  const g = new THREE.Group();
  const shape = heartShape(size);
  const body = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.012, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.005, bevelSegments: 2, curveSegments: 18 }), DOUGH);
  body.castShadow = true;
  g.add(body);
  // the iced face: the same heart, its texture drawn in icing
  const faceGeo = new THREE.ShapeGeometry(shape, 24);
  faceGeo.computeBoundingBox();
  const bb = faceGeo.boundingBox;
  const uv = faceGeo.attributes.uv, pos = faceGeo.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, (pos.getX(i) - bb.min.x) / (bb.max.x - bb.min.x), (pos.getY(i) - bb.min.y) / (bb.max.y - bb.min.y));
  const face = new THREE.Mesh(faceGeo, new THREE.MeshStandardMaterial({ map: icingTexture(text, icing), roughness: 0.6, transparent: true }));
  face.position.z = 0.0165;
  g.add(face);
  // the ribbon it hangs from
  const top = 0.3 * size;
  const ribbon = new THREE.Mesh(new THREE.BoxGeometry(0.008, 0.2, 0.002), RIBBON);
  ribbon.position.set(0, top + 0.1, 0.006);
  g.add(ribbon);
  g.traverse((m) => { if (m.isMesh) m.userData.itemFx = false; });
  // the node's origin is where the ribbon hangs from, so the heart swings about it
  const wrapG = new THREE.Group();
  g.position.y = -(top + 0.2);
  wrapG.add(g);
  wrapG.position.y = 0;
  return wrapG;
}

function icingTexture(text, icing) {
  const W = 512, H = 512;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  g.clearRect(0, 0, W, H);
  // piped border: a scalloped line just inside the heart's edge
  const s = W / 1.16;
  const map = (x, y) => [W / 2 + x * s, H * 0.535 - y * s];
  g.save();
  g.strokeStyle = icing; g.lineWidth = 9; g.lineCap = 'round';
  g.setLineDash([2, 16]);
  g.beginPath();
  const k = 0.86;
  const P = (x, y) => map(x * k, y * k + 0.02);
  g.moveTo(...P(0, 0.3));
  g.bezierCurveTo(...P(0, 0.46), ...P(-0.24, 0.56), ...P(-0.4, 0.4));
  g.bezierCurveTo(...P(-0.58, 0.2), ...P(-0.42, -0.08), ...P(0, -0.46));
  g.bezierCurveTo(...P(0.42, -0.08), ...P(0.58, 0.2), ...P(0.4, 0.4));
  g.bezierCurveTo(...P(0.24, 0.56), ...P(0, 0.46), ...P(0, 0.3));
  g.stroke();
  g.restore();
  // the words, piped
  g.fillStyle = icing;
  g.strokeStyle = 'rgba(80,40,20,0.35)';
  g.lineWidth = 3;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const lines = text;
  const fs = lines.some((l) => l.length > 8) ? 62 : 80;
  g.font = `italic 700 ${fs}px 'Alegreya SC', Georgia, serif`;
  lines.forEach((l, i) => { const y = H * 0.42 + (i - (lines.length - 1) / 2) * fs * 1.05; g.strokeText(l, W / 2, y); g.fillText(l, W / 2, y); });
  // sugar flowers and holly
  const dot = (x, y, r, col) => { g.fillStyle = col; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); };
  for (const [x, y] of [[W * 0.3, H * 0.2], [W * 0.7, H * 0.2]]) {
    for (let a = 0; a < 5; a++) dot(x + Math.cos((a / 5) * Math.PI * 2) * 13, y + Math.sin((a / 5) * Math.PI * 2) * 13, 10, '#c8283a');
    dot(x, y, 7, '#f2d24a');
  }
  dot(W / 2 - 16, H * 0.72, 9, '#2e7a3a'); dot(W / 2 + 16, H * 0.72, 9, '#2e7a3a'); dot(W / 2, H * 0.69, 8, '#c8283a');
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export { UP };
