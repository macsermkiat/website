// The writing surfaces of the market: the objects each section's words are read on (docs/adr/0003).
// A model's own write_<name> mesh (and cam_read_<name> empty) is used when the carpenter or vendor ships one;
// until then the engine builds a stand-in object here, in the stall's own frame, from the table below.
//
// A surface: { id, placeId, kind, label, root, faces: { <face>: { area, w, h } }, theme, base, rough, glow[],
//              readView(camera) -> { pos, target, near } }
// An area is an Object3D whose local XY plane is the writing plane: x right, y up, z toward the reader, with
// (0, 0) at the top-left corner of the writing area.
import * as THREE from 'three';
import { slateMaterial, woodMaterial, paperMaterial, corkMaterial, coasterMaterials, paintMaterial, ironMaterial, brassMaterial, lampGlassMaterial, woodBox } from './materials.js';
import { label } from './text.js';
import { viewFor } from '../engine/market.js';

const UP = new THREE.Vector3(0, 1, 0);

/** An area frame: a child of `parent`, at the top-left of a w x h rectangle centred at (cx, cy) in the parent's XY. */
function areaAt(parent, w, h, cx = 0, cy = 0, z = 0.001) {
  const a = new THREE.Object3D();
  a.name = 'engine_write_area';
  a.position.set(cx - w / 2, cy + h / 2, z);
  parent.add(a);
  return a;
}

function mark(root, surfaceId) {
  root.traverse((o) => { o.userData.readable = surfaceId; if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
}

/** Where to stand to read an area: square to it, far enough back that it fills `fill` of the frame. */
export function readViewFor(area, w, h, camera, { fill = 0.8, lift = 0.06, near = 0.05, up = 0 } = {}) {
  area.updateWorldMatrix(true, false);
  // `up`: aim a little above the writing (a fraction of its height), so a board's painted header is in the picture
  const c = new THREE.Vector3(w / 2, -h / 2 + h * up, 0).applyMatrix4(area.matrixWorld);
  if (up) h *= 1 + up * 2;
  const n = new THREE.Vector3(0, 0, 1).transformDirection(area.matrixWorld).normalize();
  const s = new THREE.Vector3().setFromMatrixScale(area.matrixWorld).x || 1;
  const t = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const aspect = camera.aspect || 16 / 9;
  const d = Math.max((h * s) / (2 * t * fill), (w * s) / (2 * t * aspect * fill));
  const dir = n.clone();
  dir.y += lift;
  // a sheet lying flat is read from the side its lines start at (the bottom of its page), a little tilted, as one
  // leans over a counter: straight down would leave the picture's 'up' undefined
  if (Math.abs(n.y) > 0.8) dir.addScaledVector(new THREE.Vector3(0, -1, 0).transformDirection(area.matrixWorld), 0.5);
  dir.normalize();
  return { pos: c.clone().addScaledVector(dir, d), target: c, near, normal: n, distance: d };
}

// ---------------------------------------------------------------------------------------------------------
// stand-in objects

/** A framed chalkboard hung on two cords (or standing on legs). Outer size w x h. */
function chalkboard(w, h, { seed = 3, cords = 0.32, header = null, legs = false } = {}) {
  const g = new THREE.Group();
  const frameT = 0.045, depth = 0.03;
  const slate = new THREE.Mesh(new THREE.PlaneGeometry(w - frameT * 1.2, h - frameT * 1.2), slateMaterial(seed));
  slate.position.z = 0.002;
  const back = new THREE.Mesh(new THREE.BoxGeometry(w - 0.02, h - 0.02, 0.012), woodMaterial('dark', seed));
  back.position.z = -0.006;
  g.add(slate, back);
  const wood = woodMaterial('oak', seed + 1);
  const top = woodBox(w, frameT, depth, wood); top.position.set(0, h / 2 - frameT / 2, 0.006);
  const bot = woodBox(w, frameT * 1.25, depth * 1.6, wood); bot.position.set(0, -h / 2 + frameT * 0.6, 0.012); // the chalk ledge
  const l = woodBox(frameT, h, depth, wood); l.position.set(-w / 2 + frameT / 2, 0, 0.006);
  const r = woodBox(frameT, h, depth, wood); r.position.set(w / 2 - frameT / 2, 0, 0.006);
  g.add(top, bot, l, r);
  // a stub of chalk on the ledge
  const chalk = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.05, 8), paintMaterial('#ece8dc', 0.95));
  chalk.rotation.z = Math.PI / 2 + 0.2;
  chalk.position.set(w * 0.28, -h / 2 + frameT * 1.25, 0.03);
  g.add(chalk);
  if (cords) {
    const cordMat = paintMaterial('#2a2016', 0.9);
    for (const sx of [-1, 1]) {
      const c = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, cords, 5), cordMat);
      c.position.set(sx * (w / 2 - 0.08), h / 2 + cords / 2, 0);
      g.add(c);
      const hook = new THREE.Mesh(new THREE.TorusGeometry(0.012, 0.003, 5, 10), brassMaterial());
      hook.position.set(sx * (w / 2 - 0.08), h / 2 + 0.004, 0.006);
      g.add(hook);
    }
  }
  if (legs) {
    for (const sx of [-1, 1]) {
      const leg = woodBox(0.04, legs, 0.035, wood);
      leg.position.set(sx * (w / 2 - 0.05), -h / 2 - legs / 2 + 0.05, -0.02);
      g.add(leg);
    }
  }
  const innerW = w - frameT * 2 - 0.05, innerH = h - frameT * 2.4 - 0.05;
  let cy = 0.01;
  if (header) {
    // the stall's painted header across the top of the board
    const hh = Math.min(0.11, innerH * 0.18);
    const t = label(header, { font: 'chalkBold', size: hh * 0.78, color: '#f4d58a', glow: 0.35 });
    t.position.set(0, h / 2 - frameT - hh * 0.62, 0.004);
    g.add(t);
    cy -= hh * 0.55;
    return { group: g, area: areaAt(g, innerW, innerH - hh * 1.1, 0, cy, 0.003), w: innerW, h: innerH - hh * 1.1, glow: [slate.material] };
  }
  return { group: g, area: areaAt(g, innerW, innerH, 0, cy, 0.003), w: innerW, h: innerH, glow: [slate.material] };
}

/**
 * A small chalkboard standing on the counter, leaning back on a strut (a counter easel). The group's origin is
 * the middle of its foot; the board's face is toward +Z. Outer size w x h.
 */
function counterBoard(w, h, { seed = 3, header = null, lean = 0.2 } = {}) {
  const g = new THREE.Group();
  const b = chalkboard(w, h, { seed, header, cords: 0 });
  const pivot = new THREE.Group();
  pivot.rotation.x = -lean; // the top leans back, away from the reader
  b.group.position.set(0, h / 2, 0);
  pivot.add(b.group);
  g.add(pivot);
  // the strut behind and two rubber feet
  const wood = woodMaterial('oak', seed + 2);
  // from behind the board's upper part down and back to the counter, clear of the board itself
  const strut = woodBox(0.03, h * 0.82, 0.02, wood);
  strut.position.set(0, h * 0.4, -h * 0.4);
  strut.rotation.x = 0.4;
  g.add(strut);
  return { group: g, area: b.area, w: b.w, h: b.h, glow: b.glow };
}

/** A sheet of paper, gently curled. kind: 'plain' | 'staves' | 'kraft'. Lies in its XY plane. */
function sheet(w, h, kind = 'plain', { curl = 0.012, seed = 7, margin = 0.08, top = 0 } = {}) {
  const geo = new THREE.PlaneGeometry(w, h, 12, 12);
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i) / w, y = p.getY(i) / h;
    p.setZ(i, curl * (Math.pow(Math.abs(x) * 2, 2.2) * 0.6 + Math.pow(Math.max(0, -y * 2), 3) * 0.5));
  }
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, paperMaterial(kind, seed));
  const g = new THREE.Group();
  g.add(m);
  const mw = w * margin, mh = h * margin;
  const aw = w - mw * 2, ah = h - mh * 2 - top;
  return { group: g, area: areaAt(g, aw, ah, 0, -top / 2, curl * 0.35 + 0.0015), w: aw, h: ah, glow: [m.material] };
}

/** A music stand (iron), its desk tilted back, with a sheet on it. */
function musicStand(sw = 0.32, sh = 0.44) {
  const g = new THREE.Group();
  const iron = ironMaterial();
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.011, 1.02, 8), iron);
  pole.position.y = 0.51;
  g.add(pole);
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI * 2 + 0.5;
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.34, 6), iron);
    leg.position.set(Math.sin(a) * 0.13, 0.09, Math.cos(a) * 0.13);
    leg.rotation.set(Math.cos(a) * 1.0, 0, -Math.sin(a) * 1.0);
    g.add(leg);
  }
  const desk = new THREE.Group();
  desk.position.set(0, 1.1, 0);
  desk.rotation.x = -0.32;
  const plate = new THREE.Mesh(new THREE.BoxGeometry(sw + 0.08, sh * 0.8, 0.006), iron);
  plate.position.set(0, 0, -0.006);
  const lip = new THREE.Mesh(new THREE.BoxGeometry(sw + 0.08, 0.012, 0.035), iron);
  lip.position.set(0, -sh * 0.4, 0.012);
  desk.add(plate, lip);
  const s = sheet(sw, sh, 'staves', { curl: 0.008, seed: 21, margin: 0.09, top: sh * 0.17 });
  s.group.position.set(0, -sh * 0.4 + sh / 2 + 0.006, 0.004);
  desk.add(s.group);
  g.add(desk);
  return { group: g, area: s.area, w: s.w, h: s.h, glow: s.glow };
}

/** A small wooden easel with a card on it (the bookshop's reading card). */
function easelCard(w, h) {
  const g = new THREE.Group();
  const wood = woodMaterial('dark', 9);
  const tilt = new THREE.Group();
  tilt.rotation.x = -0.26;
  tilt.position.set(0, 0, -0.02);
  for (const sx of [-1, 1]) { const leg = woodBox(0.016, h + 0.08, 0.014, wood); leg.position.set(sx * w * 0.38, (h + 0.08) / 2, -0.006); tilt.add(leg); }
  const ledge = woodBox(w + 0.04, 0.014, 0.03, wood); ledge.position.set(0, 0.03, 0.008); tilt.add(ledge);
  const back = woodBox(0.016, h * 0.9, 0.014, wood); back.position.set(0, h * 0.42, -0.14); back.rotation.x = 0.42; g.add(back);
  const card = sheet(w, h, 'plain', { curl: 0.002, seed: 17, margin: 0.09 });
  card.group.position.set(0, 0.037 + h / 2, 0.012);
  tilt.add(card.group);
  g.add(tilt);
  return { group: g, area: card.area, w: card.w, h: card.h, glow: card.glow };
}

/** A cork noticeboard on two posts with a little roof, a paper pinned to it. */
function noticeboard(w = 1.3, h = 0.95, foot = 1.0) {
  const g = new THREE.Group();
  const wood = woodMaterial('dark', 31);
  for (const sx of [-1, 1]) { const post = woodBox(0.08, foot + h + 0.25, 0.08, wood); post.position.set(sx * (w / 2 + 0.04), (foot + h + 0.25) / 2, -0.03); g.add(post); }
  const cork = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.025), corkMaterial());
  cork.position.set(0, foot + h / 2, -0.015);
  g.add(cork);
  const roof = new THREE.Group();
  for (const sx of [-1, 1]) { const p = woodBox(w / 2 + 0.2, 0.025, 0.36, woodMaterial('green', 32)); p.position.set(sx * (w / 4 + 0.05), 0, 0.03); p.rotation.z = -sx * 0.32; roof.add(p); }
  roof.position.set(0, foot + h + 0.33, 0);
  g.add(roof);
  // a lantern under the roof, so the board can be read at night
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), lampGlassMaterial());
  lamp.position.set(0, foot + h + 0.16, 0.16);
  g.add(lamp);
  const paper = sheet(w * 0.86, h * 0.84, 'plain', { curl: 0.006, seed: 33, margin: 0.06 });
  paper.group.position.set(0, foot + h / 2, 0.004);
  g.add(paper.group);
  // brass pins at the corners
  for (const [x, y] of [[-1, 1], [1, 1], [-1, -1], [1, -1]]) {
    const pin = new THREE.Mesh(new THREE.SphereGeometry(0.009, 8, 6), brassMaterial());
    pin.position.set(x * w * 0.4, foot + h / 2 + y * h * 0.39, 0.02);
    g.add(pin);
  }
  return { group: g, area: paper.area, w: paper.w, h: paper.h, glow: paper.glow };
}

/** The carousel's ticket booth: a little painted kiosk with a window; a ticket stands in the window. */
function ticketBooth() {
  const g = new THREE.Group();
  const red = paintMaterial('#7d1f1c', 0.6), cream = paintMaterial('#e9dcc0', 0.7), gold = brassMaterial();
  const W = 1.3, D = 1.0, H = 2.25;
  // walls with a window opening in the front
  const back = new THREE.Mesh(new THREE.BoxGeometry(W, H, 0.06), red); back.position.set(0, H / 2, -D / 2); g.add(back);
  for (const sx of [-1, 1]) { const side = new THREE.Mesh(new THREE.BoxGeometry(0.06, H, D), red); side.position.set(sx * W / 2, H / 2, 0); g.add(side); }
  const sill = 1.05, winH = 0.62, winW = 0.86;
  const lower = new THREE.Mesh(new THREE.BoxGeometry(W, sill, 0.06), red); lower.position.set(0, sill / 2, D / 2); g.add(lower);
  const upperH = H - sill - winH;
  const upper = new THREE.Mesh(new THREE.BoxGeometry(W, upperH, 0.06), red); upper.position.set(0, H - upperH / 2, D / 2); g.add(upper);
  for (const sx of [-1, 1]) { const jamb = new THREE.Mesh(new THREE.BoxGeometry((W - winW) / 2, winH, 0.06), red); jamb.position.set(sx * (winW / 2 + (W - winW) / 4), sill + winH / 2, D / 2); g.add(jamb); }
  const ledge = new THREE.Mesh(new THREE.BoxGeometry(winW + 0.1, 0.03, 0.2), cream); ledge.position.set(0, sill + 0.015, D / 2 + 0.04); g.add(ledge);
  const trim = new THREE.Mesh(new THREE.BoxGeometry(W + 0.04, 0.05, 0.08), gold); trim.position.set(0, sill + winH + 0.03, D / 2 + 0.01); g.add(trim);
  // a striped roof
  const roof = new THREE.Mesh(new THREE.ConeGeometry(1.05, 0.55, 4, 1), red); roof.position.set(0, H + 0.27, 0); roof.rotation.y = Math.PI / 4; g.add(roof);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 8), gold); ball.position.set(0, H + 0.58, 0); g.add(ball);
  // inside: dark, with a warm lamp
  const inner = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.1, H - 0.1), paintMaterial('#2a1712', 0.9)); inner.position.set(0, H / 2, -D / 2 + 0.035); g.add(inner);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 8), lampGlassMaterial()); lamp.position.set(0, sill + winH - 0.07, D / 2 - 0.18); g.add(lamp);
  // the sign over the window
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.2), cream); sign.position.set(0, H - upperH / 2, D / 2 + 0.032); g.add(sign);
  const t = label('Kasse · Fahrkarten', { font: 'sc', size: 0.085, color: '#5a1612', glow: 0.1 }); t.position.set(0, H - upperH / 2, D / 2 + 0.035); g.add(t);
  // the ticket, standing in the window on the ledge, leaning back a little
  const tw = 0.34, th = 0.17;
  const ticket = new THREE.Group();
  ticket.position.set(-0.12, sill + 0.03 + th / 2, D / 2 + 0.05);
  ticket.rotation.set(-0.12, 0.08, 0);
  const card = new THREE.Mesh(new THREE.BoxGeometry(tw, th, 0.0015), paintMaterial('#e8c46a', 0.85));
  ticket.add(card);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(tw * 0.97, th * 0.95), ticketMaterial());
  face.position.z = 0.0009;
  ticket.add(face);
  g.add(ticket);
  const aw = tw * 0.7, ah = th * 0.78;
  return { group: g, area: areaAt(ticket, aw, ah, tw * 0.1, -th * 0.03, 0.0013), w: aw, h: ah, glow: [face.material] };
}

let ticketMat = null;
function ticketMaterial() {
  if (ticketMat) return ticketMat;
  const c = document.createElement('canvas');
  c.width = 1024; c.height = 512;
  const g = c.getContext('2d');
  g.fillStyle = '#efd38a'; g.fillRect(0, 0, 1024, 512);
  g.strokeStyle = '#8a2a20'; g.lineWidth = 10; g.strokeRect(18, 18, 988, 476);
  g.lineWidth = 3; g.strokeRect(34, 34, 956, 444);
  // the stub, torn along a perforation
  g.setLineDash([6, 10]); g.beginPath(); g.moveTo(170, 34); g.lineTo(170, 478); g.stroke(); g.setLineDash([]);
  g.save(); g.translate(100, 256); g.rotate(-Math.PI / 2);
  g.fillStyle = '#8a2a20'; g.font = 'bold 44px Georgia, serif'; g.textAlign = 'center'; g.fillText('KARUSSELL', 0, 0);
  g.font = '28px Georgia, serif'; g.fillText('Nº 0042', 0, 44);
  g.restore();
  for (let i = 0; i < 2600; i++) { g.fillStyle = `rgba(120,80,30,${Math.random() * 0.08})`; g.fillRect(Math.random() * 1024, Math.random() * 512, 2, 2); }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  ticketMat = new THREE.MeshStandardMaterial({ name: 'engine_ticket', map: t, roughness: 0.85, emissive: 0xfff0d0, emissiveIntensity: 0.06 });
  return ticketMat;
}

/** A Bierdeckel (10.7 cm), lying flat; front face up. Areas: front (top) and back (bottom). */
export function coaster(seed = 13) {
  const d = 0.107, t = 0.0019;
  const g = new THREE.Group();
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(d / 2, d / 2, t, 40), coasterMaterials(seed));
  g.add(disc);
  // areas: the inscribed square of the ring on each face. Front: looking down at it; back: from underneath.
  const s = d * 0.6;
  const front = new THREE.Object3D();
  front.rotation.x = -Math.PI / 2;
  front.position.y = t / 2 + 0.0004;
  g.add(front);
  const back = new THREE.Object3D();
  // seen from underneath, and upright once the coaster is turned over about its vertical axis
  back.rotation.set(Math.PI / 2, 0, Math.PI);
  back.position.y = -t / 2 - 0.0004;
  g.add(back);
  const fa = areaAt(front, s, s * 0.8, 0, 0.002, 0);
  const ba = areaAt(back, d * 0.66, d * 0.62, 0, 0, 0);
  return { group: g, faces: { front: { area: fa, w: s, h: s * 0.8 }, back: { area: ba, w: d * 0.66, h: d * 0.62 } }, glow: disc.material.slice(1) };
}

/** A placard on a gondola: a little painted board on two chains. */
function placard(w = 0.62, h = 0.3) {
  const g = new THREE.Group();
  const board = woodBox(w, h, 0.02, woodMaterial('pale', 41));
  g.add(board);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.04, h - 0.04), paintMaterial('#f0e4c6', 0.85));
  face.position.z = 0.011;
  g.add(face);
  return { group: g, area: areaAt(g, w - 0.08, h - 0.07, 0, 0, 0.012), w: w - 0.08, h: h - 0.07, glow: [face.material] };
}

// ---------------------------------------------------------------------------------------------------------
// where each stand-in goes (the stall's own frame: +Z is its front; metres; the counter top is 1.05 m)
// `face: true` turns the object toward the stop's view (about Y, at most `maxTurn` radians).

export const STANDINS = {
  // the chalkboards stand on the counter's free end, below the garland and the bulbs, in the stop's picture
  glueh: [{ role: 'board', kind: 'chalk', label: 'the chalkboard', build: () => counterBoard(0.58, 0.5, { seed: 3, header: 'Heute am Stand' }), pos: [-1.37, 1.05, 1.12], face: true, maxTurn: 0.45, base: 0.0205 }],
  bier: [
    { role: 'vomfass', kind: 'chalk', label: 'the “vom Fass” board', build: () => counterBoard(0.6, 0.5, { seed: 4, header: 'Frisch vom Fass' }), pos: [1.3, 1.05, 1.12], face: true, maxTurn: 0.45, base: 0.02 },
  ],
  wurst: [
    { role: 'menu', kind: 'chalk', label: 'the menu board', build: () => counterBoard(0.54, 0.5, { seed: 5, header: 'Speisekarte' }), pos: [1.46, 1.05, 1.08], face: true, maxTurn: 0.45, base: 0.02 },
    { role: 'paper', kind: 'paper', label: 'the wrapping paper', build: () => sheet(0.38, 0.29, 'kraft', { curl: 0.01, seed: 8, margin: 0.09 }), pos: [-0.22, 1.0545, 1.3], rx: -Math.PI / 2, ry: 0.0, rz: 0.12, base: 0.0125, theme: 'print' },
  ],
  books: [{ role: 'card', kind: 'paper', label: 'the reading card', build: () => easelCard(0.32, 0.24), pos: [0.66, 1.05, 1.24], ry: -0.18, base: 0.0128, theme: 'print' }],
  band: [{ role: 'sheet', kind: 'paper', label: 'the sheet music', build: () => musicStand(0.34, 0.46), pos: [-1.55, 0.95, 2.75], face: true, maxTurn: 0.8, base: 0.0135, theme: 'print' }],
  // the rides' stand-ins stand by the stop itself (atStop: metres ahead of the stop's eye, metres to its right),
  // on the ground and turned to it, so they sit in the picture where the walk ends
  ferris: [{ role: 'notice', kind: 'paper', label: 'the noticeboard', build: () => noticeboard(1.3, 0.95, 1.0), pos: [5.6, 0, 8.4], atStop: [4.2, 2.1], face: true, maxTurn: 0.9, base: 0.034, theme: 'print' }],
  carousel: [{ role: 'ticket', kind: 'paper', label: 'the ticket', build: () => ticketBooth(), pos: [-5.4, 0, 6.9], atStop: [3.4, -2.3], face: true, maxTurn: 1.2, base: 0.0105, theme: 'print' }],
};

/** write_<name> meshes in a model: role -> mesh. */
export function writeNodes(root) {
  const out = {};
  root?.traverse((o) => { const m = /^write_(.+)$/i.exec(o.name || ''); if (m && (o.isMesh || o.children.some((c) => c.isMesh))) out[m[1].toLowerCase().replace(/\.\d+$/, '')] = o; });
  return out;
}

/**
 * The writing area of a model's write_ mesh: the plane its UVs span (least squares over its vertices:
 * position = O + u U + v V), with +V up the text. Returns { area, w, h } or null.
 */
export function areaFromWriteMesh(node) {
  const mesh = node.isMesh ? node : node.children.find((c) => c.isMesh);
  const g = mesh?.geometry;
  const pos = g?.attributes.position, uv = g?.attributes.uv;
  if (!pos || !uv || pos.count < 3) return null;
  // normal equations for [O U V] from rows [1 u v]
  const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], B = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < pos.count; i++) {
    const r = [1, uv.getX(i), uv.getY(i)], p = [pos.getX(i), pos.getY(i), pos.getZ(i)];
    for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) { A[a][b] += r[a] * r[b]; B[a][b] += r[a] * p[b]; }
  }
  const M = new THREE.Matrix3().set(...A.flat()).invert();
  // X = A^-1 B: row 0 is O, row 1 is U, row 2 is V (Matrix3.elements is column-major)
  const row = (a) => new THREE.Vector3(...[0, 1, 2].map((k) => [0, 1, 2].reduce((acc, b) => acc + M.elements[b * 3 + a] * B[b][k], 0)));
  const O = row(0), U = row(1), V = row(2);
  // glTF UVs run v down the image, so (u, v) = (0, 0) is the text's top-left and +V points down the text
  V.negate();
  const w = U.length(), h = V.length();
  if (w < 1e-4 || h < 1e-4) return null;
  const x = U.clone().normalize(), y = V.clone().normalize(), z = new THREE.Vector3().crossVectors(x, y).normalize();
  const area = new THREE.Object3D();
  area.name = 'engine_write_area';
  area.matrix.makeBasis(x, y, z).setPosition(O.clone().add(z.clone().multiplyScalar(0.0012)));
  area.matrix.decompose(area.position, area.quaternion, area.scale);
  mesh.add(area);
  return { area, w, h };
}

/**
 * Build (or find) the surfaces of every place. `camera` for read views; returns { list, byId, byPlace }.
 */
export function createSurfaces({ market, camera, warn = () => {}, stopView = null }) {
  const list = [];
  const byId = {}, byPlace = {};
  const add = (s) => { list.push(s); byId[s.id] = s; (byPlace[s.placeId] ||= []).push(s); };
  for (const [placeId, specs] of Object.entries(STANDINS)) {
    const place = market.places[placeId];
    if (place) for (const spec of specs) add(buildSurface(place, spec, camera, warn, stopView));
    else market.whenPlace?.(placeId).then((p) => { if (!p) return; for (const spec of specs) { const s = buildSurface(p, spec, camera, warn, stopView); add(s); onAdd.forEach((f) => f(s)); } });
  }
  const onAdd = [];
  return { list, byId, byPlace, onAdd: (f) => onAdd.push(f) };
}

function buildSurface(place, spec, camera, warn, stopView) {
  const id = `${place.id}.${spec.role}`;
  const own = writeNodes(place.root)[spec.role];
  let built, root, faces;
  if (own) {
    // the model's own surface: its area from its UVs, no stand-in
    const a = areaFromWriteMesh(own);
    if (a) { root = own; faces = { main: a }; built = { glow: [] }; own.traverse((o) => { if (o.isMesh) o.userData.readable = id; }); }
    else warn(`${place.entry.id}: write_${spec.role} has no usable UVs; using a stand-in`);
  }
  if (!root) {
    built = spec.build();
    root = built.group;
    root.name = `engine_surface_${spec.role}`;
    faces = built.faces || { main: { area: built.area, w: built.w, h: built.h } };
    root.position.fromArray(spec.pos);
    root.rotation.set(spec.rx || 0, spec.ry || 0, spec.rz || 0, 'YXZ');
    place.holder.add(root);
    const stop = stopView?.(place.id);
    let maxTurn = spec.maxTurn ?? 1;
    if (spec.atStop && stop) {
      const fwd = stop.target.clone().sub(stop.pos).setY(0).normalize();
      const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
      const w = stop.pos.clone().addScaledVector(fwd, spec.atStop[0]).addScaledVector(right, spec.atStop[1]).setY(0);
      place.holder.updateMatrixWorld(true);
      root.position.copy(place.holder.worldToLocal(w));
      root.position.y = 0;
      maxTurn = Math.PI;
    }
    if (spec.face) {
      // turn toward where visitors stand at this stop
      const view = (stop || viewFor(place)).pos;
      place.holder.updateMatrixWorld(true);
      const local = place.holder.worldToLocal(view.clone());
      const want = Math.atan2(local.x - root.position.x, local.z - root.position.z);
      root.rotation.y = THREE.MathUtils.clamp(want, -maxTurn, maxTurn);
    }
    mark(root, id);
  }
  const camRead = place.root.getObjectByName(`cam_read_${spec.role}`);
  const camReadT = place.root.getObjectByName(`cam_read_${spec.role}_target`);
  const s = {
    id, placeId: place.id, role: spec.role, kind: spec.kind, label: spec.label, root, faces,
    theme: spec.theme || (spec.kind === 'chalk' ? 'chalk' : 'print'), base: spec.base, rough: spec.kind === 'chalk',
    glow: built.glow || [], fromModel: !!own,
    readView(face = 'main', opts) {
      if (camRead && face === 'main') return { pos: camRead.getWorldPosition(new THREE.Vector3()), target: (camReadT || root).getWorldPosition(new THREE.Vector3()), near: 0.05 };
      const f = faces[face] || faces.main;
      return readViewFor(f.area, f.w, f.h, camera, opts || (spec.kind === 'chalk' ? { fill: 0.86, up: 0.1 } : undefined));
    },
  };
  return s;
}

/** Coasters for the Bierstand: n Bierdeckel on the counter's left end, a little fanned. */
export function placeCoasters(place, n, camera) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const c = coaster(13 + i);
    c.group.name = `engine_coaster_${i}`;
    c.group.position.set(-1.86 + i * 0.13, 1.051 + 0.001 * i, 1.46 - (i % 2) * 0.03);
    c.group.rotation.y = 0.3 - i * 0.37;
    place.holder.add(c.group);
    const id = `bier.coaster_${i}`;
    mark(c.group, id);
    c.group.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    out.push({
      id, placeId: 'bier', role: `coaster_${i}`, kind: 'coaster', label: 'a Bierdeckel', root: c.group, faces: c.faces, theme: 'print', base: 0.0062, glow: c.glow, rough: false,
      home: { p: c.group.position.clone(), q: c.group.quaternion.clone() },
      readView(face = 'front') { const f = c.faces[face] || c.faces.front; return readViewFor(f.area, f.w, f.h, camera, { fill: 0.62 }); },
    });
  }
  return out;
}

/** Placards with the big questions, hung on the first gondolas of the Riesenrad. */
export function hangPlacards(place, n) {
  const out = [];
  const gondolas = place.nodes?.gondolas || [];
  for (let i = 0; i < Math.min(n, gondolas.length); i++) {
    const gnode = gondolas[Math.floor((i * gondolas.length) / Math.max(1, n))];
    const p = placard();
    p.group.name = `engine_placard_${i}`;
    // on the gondola's front, under its roof: the gondola's own frame (its front is +Z, like every asset)
    const box = new THREE.Box3().setFromObject(gnode);
    const size = box.getSize(new THREE.Vector3());
    const s = gnode.getWorldScale(new THREE.Vector3()).x || 1;
    p.group.position.set(0, Math.max(0.6, size.y * 0.35) / s, Math.max(0.5, size.z * 0.5) / s + 0.02);
    p.group.scale.setScalar(1 / s);
    gnode.add(p.group);
    const id = `ferris.placard_${i}`;
    mark(p.group, id);
    out.push({ id, placeId: 'ferris', role: `placard_${i}`, kind: 'placard', label: 'a placard', root: p.group, faces: { main: { area: p.area, w: p.w, h: p.h } }, theme: 'print', base: 0.034, glow: p.glow, rough: false, readView: null });
  }
  return out;
}

export { UP };
