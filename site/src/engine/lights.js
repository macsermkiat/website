// light_ empties become warm real-time point lights, up to a budget; the rest get a cheap glow on the ground.
import * as THREE from 'three';

export const LIGHT_BUDGET = { full: 14, lite: 4 };

// the four section stalls first: their interiors are what the panels look at; the rides have plenty of bulbs
const PRIORITY = { section: 0, landmark: 1, tree: 2, deco: 3, strings: 4, ground: 4, other: 4 };
let poolTex = null;
function pool() {
  if (poolTex) return poolTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,.6)');
  gr.addColorStop(0.5, 'rgba(255,255,255,.18)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  poolTex = new THREE.CanvasTexture(c);
  poolTex.colorSpace = THREE.SRGBColorSpace;
  return poolTex;
}

/**
 * spots: [{ obj, kind, id }]. Returns { lights, pools, reserve } and adds them to the scene.
 * `reserved` lights are kept back for the bandstand spotlights.
 */
export function placeLights(scene, spots, { lite, focus, reserved = 0 }) {
  const cap = Math.max(0, (lite ? LIGHT_BUDGET.lite : LIGHT_BUDGET.full) - reserved);
  const tmp = new THREE.Vector3();
  const ranked = spots
    .map((s) => ({ ...s, pos: s.obj.getWorldPosition(new THREE.Vector3()) }))
    .sort((a, b) => (PRIORITY[a.kind] ?? 3) - (PRIORITY[b.kind] ?? 3) || a.pos.distanceTo(focus) - b.pos.distanceTo(focus));
  // keep at most one light per model until every model has one, then fill with second lights
  const firsts = [], seconds = [];
  const seen = new Set();
  for (const s of ranked) (seen.has(s.id) ? seconds : firsts).push(s), seen.add(s.id);
  const order = [...firsts, ...seconds];
  const lights = [], pools = [];
  const poolMat = new THREE.MeshBasicMaterial({ map: pool(), color: new THREE.Color(1.0, 0.55, 0.22), transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
  const poolGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  order.forEach((s, i) => {
    const ud = s.obj.userData || {};
    if (i < cap) {
      const color = ud.color ? new THREE.Color(ud.color) : new THREE.Color(0xffb46b);
      const L = new THREE.PointLight(color, Number(ud.intensity) || (s.kind === 'deco' ? 9 : 14), Number(ud.distance) || (s.kind === 'strings' ? 14 : 11), 2);
      L.name = `engine_${s.obj.name}`;
      L.castShadow = false;
      s.obj.add(L);
      lights.push(L);
    } else {
      // a warm pool of light on the ground under the dropped light (all pools are one instanced draw)
      const size = Math.min(8, 3 + s.pos.y * 1.3);
      pools.push({ name: `pool_${s.obj.name}`, x: s.pos.x, z: s.pos.z, size });
    }
  });
  if (pools.length) {
    const inst = new THREE.InstancedMesh(poolGeo, poolMat, pools.length);
    inst.name = 'engine_pools';
    const m = new THREE.Matrix4();
    pools.forEach((p, i) => inst.setMatrixAt(i, m.compose(tmp.set(p.x, 0.03, p.z), new THREE.Quaternion(), new THREE.Vector3(p.size, 1, p.size))));
    inst.instanceMatrix.needsUpdate = true;
    inst.computeBoundingSphere();
    inst.renderOrder = 2;
    inst.frustumCulled = false;
    scene.add(inst);
  }
  return { lights, pools, cap };
}
