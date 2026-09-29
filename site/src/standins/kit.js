// Shared pieces for the stand-in models the engine builds while the real glbs are not there yet.
// Stand-ins follow the same node conventions as the Blender exports (bulbs_, light_, slot_, cam_view,
// act_, rot_, gondola_, horse_, snow_), so every engine feature works the same on both.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export function rng(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function canvas(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  return c;
}

export function tex(c, { repeat = [1, 1], srgb = true } = {}) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

const R = rng(20260928);

// ---------- textures (built once, on first use) ----------
let _tx = null;
function textures() {
  if (_tx) return _tx;
  const wood = canvas(512, 512, (g, w, h) => {
    const pw = 64;
    for (let x = 0; x < w; x += pw) {
      const l = 36 + R() * 14;
      g.fillStyle = `hsl(${22 + R() * 6},${38 + R() * 10}%,${l * 0.55}%)`;
      g.fillRect(x, 0, pw, h);
      for (let k = 0; k < 26; k++) {
        g.strokeStyle = `rgba(${R() < 0.5 ? 20 : 70},${R() < 0.5 ? 10 : 40},0,${0.08 + R() * 0.14})`;
        g.lineWidth = 1 + R() * 1.5;
        g.beginPath();
        const x0 = x + R() * pw;
        g.moveTo(x0, 0);
        for (let y = 0; y <= h; y += 32) g.lineTo(x0 + Math.sin(y * 0.02 + k) * 3 + R() * 1.5, y);
        g.stroke();
      }
      if (R() < 0.5) { g.fillStyle = 'rgba(30,15,5,.5)'; g.beginPath(); g.ellipse(x + pw * R(), h * R(), 4, 9, 0, 0, 6.28); g.fill(); }
      g.fillStyle = 'rgba(8,4,2,.85)'; g.fillRect(x, 0, 3, h);
    }
  });
  const roof = canvas(512, 512, (g, w, h) => {
    g.fillStyle = '#2a1b14'; g.fillRect(0, 0, w, h);
    for (let row = 0; row < 16; row++) {
      const y = row * 32, off = (row % 2) * 24;
      for (let x = -off; x < w; x += 48) {
        g.fillStyle = `hsl(${15 + R() * 10},${25 + R() * 10}%,${10 + R() * 8}%)`;
        g.fillRect(x + 2, y + 2, 44, 30);
        g.fillStyle = 'rgba(0,0,0,.45)'; g.fillRect(x + 2, y + 28, 44, 4);
      }
    }
  });
  const cobble = canvas(1024, 1024, (g, w, h) => {
    g.fillStyle = '#141012'; g.fillRect(0, 0, w, h);
    const rh = 42;
    for (let y = 0; y < h; y += rh) {
      let x = -(R() * 40);
      while (x < w) {
        const sw = 38 + R() * 30, l = 22 + R() * 14;
        const gr = g.createRadialGradient(x + sw / 2 - 6, y + rh / 2 - 8, 2, x + sw / 2, y + rh / 2, sw * 0.7);
        gr.addColorStop(0, `hsl(${20 + R() * 25},${6 + R() * 6}%,${l + 10}%)`);
        gr.addColorStop(1, `hsl(${20 + R() * 20},8%,${l - 6}%)`);
        g.fillStyle = gr; g.beginPath();
        g.roundRect ? g.roundRect(x + 3, y + 3, sw - 6, rh - 6, 10) : g.rect(x + 3, y + 3, sw - 6, rh - 6);
        g.fill(); x += sw;
      }
    }
  });
  const cobbleRough = canvas(1024, 1024, (g) => { g.filter = 'grayscale(1) contrast(1.4)'; g.drawImage(cobble, 0, 0); });
  const needles = canvas(256, 256, (g, w, h) => {
    g.fillStyle = '#12301d'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 2600; i++) {
      g.strokeStyle = `hsla(${130 + R() * 25},${35 + R() * 20}%,${10 + R() * 18}%,.9)`; g.lineWidth = 1.3;
      const x = R() * w, y = R() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (R() - 0.5) * 8, y + 6 + R() * 6); g.stroke();
    }
  });
  const stripe = canvas(1024, 64, (g, w, h) => { for (let i = 0; i < 24; i++) { g.fillStyle = i % 2 ? '#efe2c8' : '#9e2437'; g.fillRect((i * w) / 24, 0, w / 24 + 1, h); } });
  const pool = canvas(128, 128, (g) => {
    const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  });
  _tx = { wood, roof, cobble, cobbleRough, needles, stripe, pool };
  return _tx;
}

// ---------- materials ----------
let _m = null;
export function mats() {
  if (_m) return _m;
  const T = textures();
  const std = (o) => new THREE.MeshStandardMaterial(o);
  _m = {
    wood: std({ name: 'standin_wood', map: tex(T.wood, { repeat: [1.5, 1] }), roughness: 0.82 }),
    woodDark: std({ name: 'standin_wood_dark', map: tex(T.wood, { repeat: [2, 1] }), color: 0x8a6a55, roughness: 0.9 }),
    counter: std({ name: 'standin_counter', map: tex(T.wood, { repeat: [3, 0.3] }), color: 0xc79a74, roughness: 0.55 }),
    roof: std({ name: 'standin_roof', map: tex(T.roof, { repeat: [2, 2] }), roughness: 0.85 }),
    snow: std({ name: 'standin_snow', color: 0xf4f7ff, roughness: 0.75 }),
    metal: std({ name: 'standin_metal', color: 0x8c919c, metalness: 0.9, roughness: 0.35 }),
    darkMetal: std({ name: 'standin_dark_metal', color: 0x2a2c31, metalness: 0.8, roughness: 0.45 }),
    brass: std({ name: 'standin_brass', color: 0xd8ab52, metalness: 1, roughness: 0.28 }),
    frame: std({ name: 'standin_frame', color: 0xcfd4e0, metalness: 0.7, roughness: 0.35 }),
    green: std({ name: 'standin_green', color: 0x1f4a2a, roughness: 0.8 }),
    red: std({ name: 'standin_red', color: 0x9e1f33, roughness: 0.4 }),
    cream: std({ name: 'standin_cream', color: 0xefe4cf, roughness: 0.5 }),
    stone: std({ name: 'standin_stone', color: 0x6d6a70, roughness: 0.95 }),
    needles: std({ name: 'standin_needles', map: tex(T.needles, { repeat: [4, 2] }), roughness: 0.9 }),
    canopy: std({ name: 'standin_canopy', map: tex(T.stripe), roughness: 0.6, side: THREE.DoubleSide }),
    cobble: std({ name: 'standin_cobble', map: tex(T.cobble, { repeat: [60, 60] }), roughnessMap: tex(T.cobbleRough, { srgb: false, repeat: [60, 60] }), roughness: 0.9, color: 0xb8a8a0 }),
    mug: std({ name: 'standin_mug', color: 0xa3162c, roughness: 0.35 }),
    wine: std({ name: 'standin_wine', color: 0x4a0612, roughness: 0.1, emissive: 0x1a0205 }),
    sausage: std({ name: 'standin_sausage', color: 0x8a4524, roughness: 0.35 }),
    coal: new THREE.MeshStandardMaterial({ name: 'standin_coal', color: 0x1a0a04, emissive: 0xff5a14, emissiveIntensity: 2.2, roughness: 1 }),
    glass: new THREE.MeshStandardMaterial({ name: 'standin_glass', color: 0xdfe8ee, roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.28, depthWrite: false }),
    beer: std({ name: 'standin_beer', color: 0xe39a1e, roughness: 0.15, emissive: 0x3a1c00, transparent: true, opacity: 0.92 }),
    foam: std({ name: 'standin_foam', color: 0xfff5de, roughness: 0.9 }),
    lampGlass: new THREE.MeshStandardMaterial({ name: 'standin_lamp_glass', color: 0xffe0b0, emissive: 0xffb45a, emissiveIntensity: 4 }),
    bulbWarm: new THREE.MeshStandardMaterial({ name: 'bulb_warm', color: 0xffd9a0, emissive: 0xffb050, emissiveIntensity: 5 }),
    bulbCold: new THREE.MeshStandardMaterial({ name: 'bulb_cold', color: 0xd8e6ff, emissive: 0x9fc0ff, emissiveIntensity: 5 }),
    pool: new THREE.MeshBasicMaterial({ name: 'standin_light_pool', map: new THREE.CanvasTexture(T.pool), color: new THREE.Color(1.1, 0.62, 0.28), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
  };
  return _m;
}

const _gm = new Map();
/** A cached plain material by colour. */
export function colorMat(color, rough = 0.6, metal = 0) {
  const k = `${color}_${rough}_${metal}`;
  if (!_gm.has(k)) _gm.set(k, new THREE.MeshStandardMaterial({ name: `standin_${color.toString(16)}`, color, roughness: rough, metalness: metal }));
  return _gm.get(k);
}

export function mesh(geo, mat, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, name } = {}) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x, y, z);
  m.rotation.set(rx, ry, rz);
  if (name) m.name = name;
  return m;
}

export function empty(name, x = 0, y = 0, z = 0) {
  const o = new THREE.Object3D();
  o.name = name;
  o.position.set(x, y, z);
  return o;
}

// ---------- signs ----------
const signRedraws = [];
/** A painted wooden sign as a canvas texture; redrawn once the display font has loaded. */
export function signTexture(text, { w = 1024, h = 160, bg = ['#2a1a10', '#1a0f08'], ink = '#f6dca8', rim = '#c99a4a' } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  const draw = () => {
    const g = c.getContext('2d');
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, bg[0]); gr.addColorStop(1, bg[1]);
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.strokeStyle = rim; g.lineWidth = 6; g.strokeRect(10, 10, w - 20, h - 20);
    g.fillStyle = ink;
    let size = h * 0.52;
    g.font = `700 ${size}px 'Alegreya SC', Georgia, serif`;
    while (g.measureText(text).width > w - 60 && size > 10) { size -= 2; g.font = `700 ${size}px 'Alegreya SC', Georgia, serif`; }
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(text, w / 2, h * 0.54);
    t.needsUpdate = true;
  };
  draw();
  signRedraws.push(draw);
  return t;
}
export function redrawSigns() {
  signRedraws.forEach((f) => f());
}

export function signMesh(text, width, height, opts) {
  const map = signTexture(text, opts);
  const m = new THREE.MeshStandardMaterial({ map, emissiveMap: map, emissive: 0xffffff, emissiveIntensity: 0.22, roughness: 0.6 });
  return new THREE.Mesh(new THREE.PlaneGeometry(width, height), m);
}

// ---------- fairy bulbs ----------
const bulbGeo = new THREE.SphereGeometry(0.05, 8, 6);
/** One mesh of small bulbs at the given points, named bulbs_<n>, material bulb_warm or bulb_cold. */
export function bulbString(name, points, { cold = false, size = 1 } = {}) {
  const geos = points.map((p) => {
    const g = bulbGeo.clone();
    if (size !== 1) g.scale(size, size, size);
    g.translate(p.x, p.y, p.z);
    return g;
  });
  const merged = mergeGeometries(geos);
  const m = new THREE.Mesh(merged, cold ? mats().bulbCold : mats().bulbWarm);
  m.name = name;
  return m;
}

/** Points along a sagging wire between a and b. */
export function catenary(a, b, sag, n) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    pts.push(new THREE.Vector3().lerpVectors(a, b, t).add(new THREE.Vector3(0, -sag * 4 * t * (1 - t), 0)));
  }
  return pts;
}

/** Merge all plain meshes under root that share a material, to keep draw calls low. Named nodes are kept. */
export function mergeStatic(root, keep = /^(bulbs_|light_|slot_|cam_|act_|rot_|gondola_|horse_|snow_|sign)/) {
  root.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
  const buckets = new Map();
  const remove = [];
  (function walk(o) {
    for (const c of o.children) {
      if (keep.test(c.name) || c.userData.keep) continue;
      if (c.isMesh && !c.isInstancedMesh && c.children.length === 0) {
        const key = c.material.uuid;
        if (!buckets.has(key)) buckets.set(key, { mat: c.material, items: [] });
        const g = (c.geometry.index ? c.geometry.toNonIndexed() : c.geometry.clone());
        for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
        if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
        g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, c.matrixWorld));
        buckets.get(key).items.push(g);
        remove.push(c);
      } else if (!c.isMesh) walk(c);
    }
  })(root);
  for (const b of buckets.values()) {
    const merged = mergeGeometries(b.items);
    if (!merged) continue;
    const mm = new THREE.Mesh(merged, b.mat);
    mm.name = `merged_${b.mat.name || 'mat'}`;
    root.add(mm);
  }
  remove.forEach((c) => c.parent && c.parent.remove(c));
  return root;
}
