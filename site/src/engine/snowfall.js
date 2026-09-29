// Falling snow around the camera's part of the market.
import * as THREE from 'three';

export function createSnowfall(scene, { lite }) {
  const N = lite ? 2500 : 8000;
  const pos = new Float32Array(N * 3), vel = new Float32Array(N);
  let s = 11;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < N; i++) { pos[i * 3] = (R() - 0.5) * 90; pos[i * 3 + 1] = R() * 26; pos[i * 3 + 2] = (R() - 0.5) * 80; vel[i] = 0.6 + R() * 0.9; }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,.5)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.09, map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, color: 0xffffff, opacity: 0.9 }));
  pts.name = 'engine_snowfall';
  pts.visible = false;
  pts.frustumCulled = false;
  scene.add(pts);
  return {
    points: pts,
    set(on) { pts.visible = on; },
    update(dt, t, still) {
      if (!pts.visible || still) return;
      for (let i = 0; i < N; i++) {
        pos[i * 3 + 1] -= vel[i] * dt;
        pos[i * 3] += Math.sin(t * 0.7 + i) * 0.15 * dt;
        if (pos[i * 3 + 1] < 0) pos[i * 3 + 1] = 26;
      }
      geo.attributes.position.needsUpdate = true;
    },
  };
}
