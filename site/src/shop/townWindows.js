// The town wakes (round 9, the Schwibbogen): the old town's dark windows turn warm, spreading outward from the
// market. The architect's window_warm material is an atlas of lit and dark panes (blender/town/town.py: a 4x4 grid,
// lit rooms in cells 0-8, dark ones in cells 10, 12 and 14, stained glass in the other bottom cells). Each dark
// window gets two vertex attributes: its rank (0 never; else 0..1 by its distance from the market's centre, with
// a little jitter so it is not a perfect ring) and the offset to a lit cell of the same atlas. The material's
// shader blends a window to its lit room once the wake front `uWake` has passed its rank.
import * as THREE from 'three';

const DARK = new Set([10, 12, 14]);
const LIT = new Set([0, 1, 2, 3, 4, 5, 6, 7, 8]); // rooms lit by default: they go quiet while the town waits, and wake with the rest
const QUIET = 0.2; // a lit room's glow while it waits for the wake front
const SHARE = 0.78; // not every dark room lights: some neighbours are out tonight
const FEATHER = 0.05;

export function createTownWindows({ scene, market }) {
  const uniforms = { uWake: { value: 0 }, uWakeGain: { value: 1 }, uHush: { value: 0 } };
  const patched = new WeakSet();
  let meshes = [];
  let candidates = 0;

  function townRoots() {
    return market.placed.filter((p) => p.entry.kind === 'town' || /town/i.test(p.entry.id)).map((p) => p.holder);
  }

  /** Give a window mesh its wake attributes (once per geometry: a streamed full town brings new ones). */
  function dress(mesh) {
    const g = mesh.geometry;
    if (g.userData.wake) return g.userData.wake.count;
    const uv = g.attributes.uv, pos = g.attributes.position;
    if (!uv || !pos) { g.userData.wake = { count: 0 }; return 0; }
    const n = pos.count;
    const idx = g.index ? g.index.array : null;
    const faces = idx ? idx.length / 3 : n / 3;
    const vi = (f, k) => (idx ? idx[f * 3 + k] : f * 3 + k);
    // windows as groups of faces that share vertices (a pane is two triangles; neighbouring windows never share)
    const parent = new Int32Array(n).map((_, i) => i);
    const find = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
    const cellOf = new Int8Array(n).fill(-1);
    for (let f = 0; f < faces; f++) {
      const a = vi(f, 0), b = vi(f, 1), c = vi(f, 2);
      const u = (uv.getX(a) + uv.getX(b) + uv.getX(c)) / 3, v = (uv.getY(a) + uv.getY(b) + uv.getY(c)) / 3;
      const cell = Math.floor(THREE.MathUtils.clamp(v, 0, 0.9999) * 4) * 4 + Math.floor(THREE.MathUtils.clamp(u, 0, 0.9999) * 4);
      if (!DARK.has(cell) && !LIT.has(cell)) continue;
      cellOf[a] = cellOf[b] = cellOf[c] = cell;
      parent[find(b)] = find(a); parent[find(c)] = find(a);
    }
    mesh.updateWorldMatrix(true, false);
    const sums = new Map(), p = new THREE.Vector3();
    for (let i = 0; i < n; i++) {
      if (cellOf[i] < 0) continue;
      const r = find(i);
      p.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
      const s = sums.get(r) || { x: 0, z: 0, k: 0, lit: LIT.has(cellOf[i]) };
      s.x += p.x; s.z += p.z; s.k++;
      sums.set(r, s);
    }
    let dMin = Infinity, dMax = 0;
    for (const s of sums.values()) { s.d = Math.hypot(s.x / s.k, s.z / s.k); dMin = Math.min(dMin, s.d); dMax = Math.max(dMax, s.d); }
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (const s of sums.values()) {
      if (s.lit) {
        // a room lit by default: a negative rank, so the shader knows to quieten it until the front passes
        s.rank = -THREE.MathUtils.clamp(0.02 + 0.9 * (s.d - dMin) / Math.max(1, dMax - dMin) + (rnd() - 0.5) * 0.12, 0.02, 0.97);
        s.du = 0;
        continue;
      }
      const lit = rnd() < SHARE;
      s.rank = lit ? THREE.MathUtils.clamp(0.02 + 0.9 * (s.d - dMin) / Math.max(1, dMax - dMin) + (rnd() - 0.5) * 0.12, 0.02, 0.97) : 0;
      // the lit room this window shows: the same atlas column or the next one, two rows up (cells 2/3, 4/5, 6/7)
      s.du = rnd() < 0.5 ? 0 : 0.25;
    }
    const wake = new Float32Array(n), off = new Float32Array(n * 2);
    let count = 0, quiet = 0;
    for (let i = 0; i < n; i++) {
      if (cellOf[i] < 0) continue;
      const s = sums.get(find(i));
      wake[i] = s.rank;
      off[i * 2] = s.du;
      off[i * 2 + 1] = s.lit ? 0 : -0.5; // glTF UVs run top-down: dark rows 2-3 to lit rows 0-1
    }
    for (const s of sums.values()) { if (s.rank > 0) count++; else if (s.rank < 0) quiet++; }
    g.setAttribute('aWake', new THREE.BufferAttribute(wake, 1));
    g.setAttribute('aWakeOff', new THREE.BufferAttribute(off, 2));
    g.userData.wake = { count, quiet };
    return count;
  }

  function patch(material) {
    if (patched.has(material)) return;
    patched.add(material);
    const prev = material.onBeforeCompile;
    material.onBeforeCompile = (shader, r) => {
      prev?.call(material, shader, r);
      Object.assign(shader.uniforms, uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aWake;\nattribute vec2 aWakeOff;\nvarying float vWake;\nvarying vec2 vWakeOff;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWake = aWake;\nvWakeOff = aWakeOff;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uWake;\nuniform float uWakeGain;\nuniform float uHush;\nvarying float vWake;\nvarying vec2 vWakeOff;')
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
#ifdef USE_EMISSIVEMAP
  if ( vWake > 0.0 ) {
    float wk = clamp( ( uWake - vWake ) / ${FEATHER.toFixed(3)}, 0.0, 1.0 ) * uWakeGain;
    vec3 room = emissive * texture2D( emissiveMap, vEmissiveMapUv + vWakeOff ).rgb * ( 0.8 + 0.4 * fract( vWake * 97.31 ) );
    totalEmissiveRadiance = mix( totalEmissiveRadiance, room, wk );
  } else if ( vWake < 0.0 ) {
    // lit by default: quiet while the town waits (uHush), back to full once the wake front has passed
    float passed = clamp( ( uWake + vWake ) / ${FEATHER.toFixed(3)}, 0.0, 1.0 );
    totalEmissiveRadiance *= mix( 1.0, ${QUIET.toFixed(2)}, uHush * ( 1.0 - passed ) );
  }
#endif`);
    };
    const key = material.customProgramCacheKey?.bind(material);
    material.customProgramCacheKey = () => `${key ? key() : ''}|townwake`;
    material.needsUpdate = true;
  }

  /** Find (again) the town's window meshes and dress them. Cheap when nothing changed. */
  function refresh() {
    const found = [];
    for (const root of townRoots()) {
      root.traverse((o) => {
        if (!o.isMesh) return;
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        if (!ms.some((m) => /^window_warm/i.test(m?.name || ''))) return;
        found.push(o);
      });
    }
    let total = 0;
    for (const m of found) {
      total += dress(m);
      for (const mat of Array.isArray(m.material) ? m.material : [m.material]) if (/^window_warm/i.test(mat?.name || '')) patch(mat);
    }
    meshes = found;
    candidates = total;
    return total;
  }

  return {
    uniforms,
    refresh,
    /** Where the wake front is (0 all dark .. 1 every chosen window lit). */
    set wake(v) { uniforms.uWake.value = v; },
    /** How quiet the town's lit rooms are while they wait for the wake (0 as usual .. 1 nearly dark). */
    set hush(v) { uniforms.uHush.value = v; },
    get hush() { return uniforms.uHush.value; },
    get wake() { return uniforms.uWake.value; },
    /** How many windows wait to wake, and how many are lit now (tests). */
    stats() {
      let lit = 0;
      const w = uniforms.uWake.value;
      for (const m of meshes) {
        const a = m.geometry.attributes.aWake;
        if (!a) continue;
        // count windows (a pane is several vertices; count each rank once)
        const seen = new Set();
        for (let i = 0; i < a.count; i++) { const r = a.array[i]; if (r > 0 && !seen.has(r)) { seen.add(r); if (w - r >= FEATHER) lit++; } }
      }
      const quiet = meshes.reduce((a, m) => a + (m.geometry.userData.wake?.quiet || 0), 0);
      return { meshes: meshes.length, candidates, lit, quiet, hush: +uniforms.uHush.value.toFixed(3), wake: +w.toFixed(3) };
    },
    /** Make sure the town is dressed (a streamed town swaps its geometry for the full one). */
    check() { if (meshes.some((m) => !m.geometry.userData.wake) || !meshes.length) refresh(); },
    get scene() { return scene; },
  };
}
