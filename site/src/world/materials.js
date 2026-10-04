// Small procedural materials for the writing surfaces the engine builds until the carpenter's and vendor's own
// write_ props arrive: slate, wood, cork, paper, card. Canvas textures, made once and shared; no downloads.
import * as THREE from 'three';

const cache = new Map();
function once(key, make) {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key);
}

/** A seeded random (the same board looks the same on every visit). */
export function rand(seed = 1) {
  let s = seed >>> 0 || 1;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function canvasTexture(w, h, draw, { srgb = true, repeat = false } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  return t;
}

function speckle(g, w, h, r, n, color, alpha, size = 1.2) {
  g.fillStyle = color;
  for (let i = 0; i < n; i++) { g.globalAlpha = alpha * (0.4 + r() * 0.6); g.fillRect(r() * w, r() * h, size * (0.5 + r()), size * (0.5 + r())); }
  g.globalAlpha = 1;
}

/** Slate with old chalk: wiped arcs, dust at the bottom edge. */
export function slateMaterial(seed = 3) {
  return once(`slate${seed}`, () => {
    const r = rand(seed);
    const map = canvasTexture(1024, 768, (g, w, h) => {
      g.fillStyle = '#1d2621'; g.fillRect(0, 0, w, h);
      const v = g.createRadialGradient(w * 0.5, h * 0.45, w * 0.1, w * 0.5, h * 0.5, w * 0.75);
      v.addColorStop(0, 'rgba(60,72,64,0.35)'); v.addColorStop(1, 'rgba(0,0,0,0.25)');
      g.fillStyle = v; g.fillRect(0, 0, w, h);
      // wiped-out chalk: broad soft arcs
      for (let i = 0; i < 26; i++) {
        g.strokeStyle = `rgba(220,226,214,${0.025 + r() * 0.035})`;
        g.lineWidth = 30 + r() * 70;
        g.lineCap = 'round';
        g.beginPath();
        const x = r() * w, y = r() * h;
        g.arc(x, y, 80 + r() * 260, r() * 6, r() * 6 + 0.8 + r());
        g.stroke();
      }
      // ghosts of old words
      g.fillStyle = 'rgba(230,230,220,0.035)';
      g.font = '64px Georgia, serif';
      for (let i = 0; i < 9; i++) g.fillText(['Glühwein', '3,50', 'mit Schuss', 'Kinderpunsch', 'heiß', 'Pfand 2 €'][i % 6], r() * w * 0.8, r() * h);
      speckle(g, w, h, r, 9000, '#c9d0c4', 0.06, 1.3);
      // dust along the lower edge
      const d = g.createLinearGradient(0, h * 0.88, 0, h);
      d.addColorStop(0, 'rgba(230,230,220,0)'); d.addColorStop(1, 'rgba(230,230,220,0.12)');
      g.fillStyle = d; g.fillRect(0, h * 0.88, w, h * 0.12);
    });
    return new THREE.MeshStandardMaterial({ name: 'engine_slate', map, roughness: 0.93, metalness: 0, emissive: 0x3a4a40, emissiveIntensity: 0.06 });
  });
}

/** Stained, worn wood (frames, posts, the signpost): grain along U. */
export function woodMaterial(tone = 'oak', seed = 5) {
  return once(`wood${tone}${seed}`, () => {
    const r = rand(seed);
    const base = { oak: [118, 84, 52], dark: [72, 48, 30], pale: [168, 132, 92], green: [44, 66, 50] }[tone] || [118, 84, 52];
    const map = canvasTexture(512, 512, (g, w, h) => {
      g.fillStyle = `rgb(${base})`; g.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 1) {
        const k = Math.sin(y * 0.09 + Math.sin(y * 0.013) * 4) * 0.5 + 0.5;
        const d = (k * 26 - 13) + (r() - 0.5) * 6;
        g.fillStyle = `rgba(${d > 0 ? '255,230,200' : '30,15,5'},${Math.abs(d) / 160})`;
        g.fillRect(0, y, w, 1);
      }
      for (let i = 0; i < 60; i++) {
        g.strokeStyle = `rgba(30,16,6,${0.05 + r() * 0.1})`;
        g.lineWidth = 0.6 + r() * 1.4;
        g.beginPath();
        const y = r() * h;
        g.moveTo(0, y);
        for (let x = 0; x <= w; x += 32) g.lineTo(x, y + Math.sin(x * 0.01 + i) * 4 + (r() - 0.5) * 2);
        g.stroke();
      }
      speckle(g, w, h, r, 1500, '#1a0d05', 0.12, 1.5);
      // worn, paler edges
      const e = g.createLinearGradient(0, 0, 0, h);
      e.addColorStop(0, 'rgba(255,240,210,0.08)'); e.addColorStop(0.5, 'rgba(0,0,0,0)'); e.addColorStop(1, 'rgba(255,240,210,0.08)');
      g.fillStyle = e; g.fillRect(0, 0, w, h);
    }, { repeat: true });
    return new THREE.MeshStandardMaterial({ name: `engine_wood_${tone}`, map, roughness: 0.78, metalness: 0 });
  });
}

/** Paper: cream, fibres, a little foxing. kind: 'plain' | 'staves' (sheet music) | 'kraft' (market paper). */
export function paperMaterial(kind = 'plain', seed = 7) {
  return once(`paper${kind}${seed}`, () => {
    const r = rand(seed);
    const tone = kind === 'kraft' ? '#cdb48a' : kind === 'staves' ? '#efe6cf' : '#f1e8d3';
    const map = canvasTexture(512, 720, (g, w, h) => {
      g.fillStyle = tone; g.fillRect(0, 0, w, h);
      speckle(g, w, h, r, 2600, kind === 'kraft' ? '#7a5a34' : '#a08a64', 0.08, 1.1);
      for (let i = 0; i < 160; i++) {
        g.strokeStyle = `rgba(${kind === 'kraft' ? '110,80,40' : '150,130,100'},0.08)`;
        g.lineWidth = 0.7;
        g.beginPath();
        const x = r() * w, y = r() * h, a = r() * 6.3, l = 4 + r() * 14;
        g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l);
        g.stroke();
      }
      if (kind === 'kraft') {
        // the butcher's stamp, faded
        g.strokeStyle = 'rgba(150,40,30,0.32)'; g.lineWidth = 4;
        g.beginPath(); g.arc(w * 0.8, h * 0.86, 46, 0, Math.PI * 2); g.stroke();
        g.fillStyle = 'rgba(150,40,30,0.32)'; g.font = 'bold 20px Georgia, serif'; g.textAlign = 'center';
        g.fillText('Metzgerei', w * 0.8, h * 0.86 - 4); g.fillText('seit 1898', w * 0.8, h * 0.86 + 18);
        // grease spots
        for (let i = 0; i < 5; i++) { const gr = g.createRadialGradient(r() * w, r() * h, 2, r() * w, r() * h, 40); gr.addColorStop(0, 'rgba(120,80,30,0.16)'); gr.addColorStop(1, 'rgba(120,80,30,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); }
      }
      if (kind === 'staves') {
        // five-line staves down the sheet, a treble clef's ghost at the start of each
        g.strokeStyle = 'rgba(40,28,20,0.32)'; g.lineWidth = 1.2;
        for (let s = 0; s < 3; s++) {
          const y0 = h * 0.08 + s * 26;
          for (let l = 0; l < 5; l++) { g.beginPath(); g.moveTo(w * 0.07, y0 + l * 4.4); g.lineTo(w * 0.93, y0 + l * 4.4); g.stroke(); }
          g.fillStyle = 'rgba(40,28,20,0.5)';
          for (let n = 0; n < 11; n++) { const x = w * 0.16 + n * w * 0.068, y = y0 + 2 + ((n * 7 + s * 3) % 9) * 2.2; g.beginPath(); g.ellipse(x, y, 3.2, 2.4, -0.4, 0, Math.PI * 2); g.fill(); g.fillRect(x + 2.6, y - 14, 1.1, 14); }
        }
        const b = h - 30;
        for (let l = 0; l < 5; l++) { g.beginPath(); g.moveTo(w * 0.07, b - l * 4.4); g.lineTo(w * 0.93, b - l * 4.4); g.stroke(); }
      }
      const f = g.createRadialGradient(w / 2, h / 2, w * 0.2, w / 2, h / 2, w * 0.85);
      f.addColorStop(0, 'rgba(0,0,0,0)'); f.addColorStop(1, 'rgba(120,90,40,0.18)');
      g.fillStyle = f; g.fillRect(0, 0, w, h);
    });
    return new THREE.MeshStandardMaterial({ name: `engine_paper_${kind}`, map, roughness: 0.95, metalness: 0, side: THREE.DoubleSide, emissive: 0xfff2dc, emissiveIntensity: 0.05 });
  });
}

/** Cork for the noticeboard. */
export function corkMaterial(seed = 11) {
  return once(`cork${seed}`, () => {
    const r = rand(seed);
    const map = canvasTexture(512, 512, (g, w, h) => {
      g.fillStyle = '#9c7449'; g.fillRect(0, 0, w, h);
      speckle(g, w, h, r, 14000, '#5e3f20', 0.35, 2.2);
      speckle(g, w, h, r, 9000, '#c89a64', 0.3, 1.8);
    }, { repeat: true });
    return new THREE.MeshStandardMaterial({ name: 'engine_cork', map, roughness: 0.98 });
  });
}

/**
 * A Bierdeckel: printed front (a red ring and the house's name round the rim) and a plain card back.
 * Returns [rim, front, back] materials for a CylinderGeometry (side, top, bottom).
 */
export function coasterMaterials(seed = 13, tint = '#b0302a') {
  return once(`coaster${seed}${tint}`, () => {
    const r = rand(seed);
    const card = (front) => canvasTexture(512, 512, (g, w, h) => {
      g.fillStyle = '#efe4cc'; g.fillRect(0, 0, w, h);
      speckle(g, w, h, r, 3000, '#9a8460', 0.1, 1.2);
      const c = w / 2;
      if (front) {
        g.strokeStyle = tint; g.lineWidth = 26;
        g.beginPath(); g.arc(c, c, w * 0.44, 0, Math.PI * 2); g.stroke();
        g.lineWidth = 3; g.beginPath(); g.arc(c, c, w * 0.385, 0, Math.PI * 2); g.stroke();
        // the house's name round the top of the ring
        g.fillStyle = '#f6ecd6'; g.font = 'bold 26px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        const word = 'NACHTMARKT BRÄU · SEIT 2024 · ';
        for (let i = 0; i < word.length; i++) {
          const a = -Math.PI / 2 + (i - word.length / 2) * 0.105;
          g.save(); g.translate(c + Math.cos(a) * w * 0.44, c + Math.sin(a) * w * 0.44); g.rotate(a + Math.PI / 2); g.fillText(word[i], 0, 1); g.restore();
        }
        // a hop leaf at the bottom
        g.fillStyle = tint;
        g.beginPath(); g.ellipse(c, c + w * 0.3, 16, 22, 0, 0, Math.PI * 2); g.fill();
      } else {
        g.strokeStyle = 'rgba(80,60,40,0.4)'; g.lineWidth = 2;
        g.beginPath(); g.arc(c, c, w * 0.46, 0, Math.PI * 2); g.stroke();
        // a wet ring from a glass
        g.strokeStyle = 'rgba(150,110,60,0.18)'; g.lineWidth = 9;
        g.beginPath(); g.arc(c + 30, c - 20, w * 0.3, 0.4, 5.6); g.stroke();
      }
      const e = g.createRadialGradient(c, c, w * 0.3, c, c, w * 0.5);
      e.addColorStop(0, 'rgba(0,0,0,0)'); e.addColorStop(1, 'rgba(110,80,40,0.2)');
      g.fillStyle = e; g.fillRect(0, 0, w, h);
    });
    const mk = (map) => new THREE.MeshStandardMaterial({ name: 'engine_coaster', map, roughness: 0.9, emissive: 0xfff2dc, emissiveIntensity: 0.05 });
    return [new THREE.MeshStandardMaterial({ name: 'engine_coaster_rim', color: 0xd8ccb0, roughness: 0.9 }), mk(card(true)), mk(card(false))];
  });
}

/** Painted sheet metal / plain colours for kiosks and stands. */
export function paintMaterial(color, rough = 0.7) {
  return once(`paint${color}${rough}`, () => new THREE.MeshStandardMaterial({ name: 'engine_paint', color: new THREE.Color(color), roughness: rough, metalness: 0.05 }));
}
export function ironMaterial() {
  return once('iron', () => new THREE.MeshStandardMaterial({ name: 'engine_iron', color: 0x2a2724, roughness: 0.55, metalness: 0.7 }));
}
export function brassMaterial() {
  return once('brass', () => new THREE.MeshStandardMaterial({ name: 'engine_brass', color: 0xb08a48, roughness: 0.35, metalness: 0.85 }));
}
/** The glow of a small lamp over a board (emissive, so the lighting module's bloom picks it up). */
export function lampGlassMaterial() {
  return once('lampglass', () => new THREE.MeshStandardMaterial({ name: 'bulb_warm_engine', color: 0xffe0b0, emissive: 0xffb860, emissiveIntensity: 3.2, roughness: 0.3 }));
}

/** UV-scaled box (wood grain along the long side). */
export function woodBox(w, h, d, mat) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  const long = Math.max(w, h, d);
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * long * 1.4, uv.getY(i) * 0.25);
  return new THREE.Mesh(g, mat);
}
