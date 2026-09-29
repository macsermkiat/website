// Steam over the Glühwein pot and smoke over the grill: soft sprites that rise and fade.
import * as THREE from 'three';

let smokeTex = null;
function texture() {
  if (smokeTex) return smokeTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  let s = 3;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 14; i++) {
    const x = 40 + R() * 48, y = 40 + R() * 48, r = 18 + R() * 26;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, 'rgba(255,255,255,.18)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  }
  smokeTex = new THREE.CanvasTexture(c);
  return smokeTex;
}

export function createEmitter(scene, pos, { color, n, rise, spread, scale, opacity }) {
  const arr = [];
  for (let i = 0; i < n; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture(), color, transparent: true, depthWrite: false, opacity: 0 }));
    sp.name = 'effect_puff';
    scene.add(sp);
    arr.push({ s: sp, t: i / n });
  }
  const em = {
    pos, base: opacity, boost: 0,
    update(dt, still) {
      em.boost *= Math.exp(-dt * 0.8);
      const op = em.base * (1 + em.boost);
      for (const p of arr) {
        if (!still) p.t = (p.t + dt / (rise * 1.3)) % 1;
        const t = p.t;
        p.s.position.set(pos.x + Math.sin(t * 6 + p.t * 40) * spread * t, pos.y + t * rise, pos.z + Math.cos(t * 5) * spread * 0.5 * t);
        const sc = scale * (0.3 + t);
        p.s.scale.set(sc, sc, 1);
        p.s.material.opacity = op * Math.sin(t * Math.PI);
      }
    },
  };
  return em;
}
