// Environment maps for reflections (wet cobbles, glass, copper, glazed mugs).
// 1. A synthetic night built at start-up: the sky dome without stars, a dark wet ground, and a ring
//    of warm glows low on the horizon standing in for the neighbouring stalls and string lights.
// 2. On the full market, a one-off capture of the real scene (`captureScene`) once it has loaded,
//    so the copper pot really reflects the bulbs and lamps around it.
import * as THREE from 'three';

export function syntheticEnvironment(renderer, sky, { size = 256 } = {}) {
  const envScene = new THREE.Scene();
  const skyMat = sky.material.clone();
  skyMat.uniforms = THREE.UniformsUtils.clone(sky.material.uniforms);
  skyMat.uniforms.uStars.value = 0;
  skyMat.uniforms.uClouds.value = 0;
  skyMat.uniforms.uMilky.value = 0;
  const dome = new THREE.Mesh(new THREE.SphereGeometry(40, 32, 16), skyMat);
  dome.material.depthTest = false;
  dome.renderOrder = -1;
  envScene.add(dome);

  // wet dark ground with a warm sheen
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(38, 32).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(0.012, 0.011, 0.012) }),
  );
  ground.position.y = -1.6;
  envScene.add(ground);

  // ring of warm stall glows and a few cooler lamp glows, low on the horizon
  let s = 3;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const blob = new THREE.SphereGeometry(1, 12, 8);
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2 + R() * 0.3;
    const d = 18 + R() * 10;
    const warm = R() > 0.15;
    const k = 0.5 + R() * 0.9;
    const m = new THREE.Mesh(blob, new THREE.MeshBasicMaterial({
      color: warm ? new THREE.Color(1.0 * k, 0.55 * k, 0.22 * k) : new THREE.Color(0.5 * k, 0.6 * k, 0.9 * k),
    }));
    m.position.set(Math.cos(a) * d, 0.2 + R() * 2.2, Math.sin(a) * d);
    m.scale.set(1.6 + R() * 1.4, 0.7 + R() * 0.6, 1.6 + R() * 1.4);
    envScene.add(m);
  }
  // string lights: small bright dots overhead
  const dot = new THREE.SphereGeometry(0.12, 6, 4);
  const dotMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 3.4, 1.4) });
  for (let i = 0; i < 60; i++) {
    const a = R() * Math.PI * 2, d = 6 + R() * 16;
    const m = new THREE.Mesh(dot, dotMat);
    m.position.set(Math.cos(a) * d, 3.5 + R() * 2, Math.sin(a) * d);
    envScene.add(m);
  }

  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(envScene, 0.02, 0.1, 100, { size });
  pmrem.dispose();
  envScene.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); o.material.dispose(); } });
  return rt;
}

/**
 * Capture the real scene into a PMREM environment from `position`. `hide` objects are hidden
 * during the capture (snow, helpers). Returns the render target (caller disposes the old one).
 */
export function captureScene(renderer, scene, position, { size = 256, hide = [] } = {}) {
  const was = hide.map((o) => o.visible);
  hide.forEach((o) => (o.visible = false));
  const env = scene.environment;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(scene, 0.0, 0.1, 400, { size, position });
  pmrem.dispose();
  scene.environment = env;
  hide.forEach((o, i) => (o.visible = was[i]));
  return rt;
}

/**
 * Re-captures the scene into an environment a face at a time, so a periodic refresh (the wheel and
 * the carousel keep turning) costs one extra 256² scene render per frame for six frames instead of
 * one long hitch. The first conversion allocates the PMREM target; later ones reuse it in place, so
 * every material keeps pointing at the same texture.
 */
export function createEnvUpdater(renderer, scene, { size = 256, near = 0.1, far = 400, hide = [] } = {}) {
  const cubeRT = new THREE.WebGLCubeRenderTarget(size, { type: THREE.HalfFloatType, generateMipmaps: false });
  const cam = new THREE.CubeCamera(near, far, cubeRT);
  const pmrem = new THREE.PMREMGenerator(renderer);
  let face = -1, out = null;

  function renderFace(i) {
    if (cam.coordinateSystem !== renderer.coordinateSystem) {
      cam.coordinateSystem = renderer.coordinateSystem;
      cam.updateCoordinateSystem();
    }
    const was = hide.map((o) => o.visible);
    hide.forEach((o) => (o.visible = false));
    const prevTarget = renderer.getRenderTarget();
    const prevFace = renderer.getActiveCubeFace(), prevMip = renderer.getActiveMipmapLevel();
    const autoShadow = renderer.shadowMap.autoUpdate;
    renderer.shadowMap.autoUpdate = false; // the frame's own shadow maps are current
    renderer.setRenderTarget(cubeRT, i);
    renderer.render(scene, cam.children[i]);
    renderer.setRenderTarget(prevTarget, prevFace, prevMip);
    renderer.shadowMap.autoUpdate = autoShadow;
    hide.forEach((o, k) => (o.visible = was[k]));
  }
  function convert() {
    out = out ? pmrem.fromCubemap(cubeRT.texture, out) : pmrem.fromCubemap(cubeRT.texture);
    return out;
  }
  return {
    get busy() { return face >= 0; },
    get target() { return out; },
    /** Capture all six faces now and return the PMREM target. */
    captureNow(position) {
      cam.position.copy(position);
      cam.updateMatrixWorld(true);
      for (let i = 0; i < 6; i++) renderFace(i);
      face = -1;
      return convert();
    },
    /** Begin a spread-out capture; call step() once a frame until it returns the target. */
    start(position) {
      cam.position.copy(position);
      cam.updateMatrixWorld(true);
      face = 0;
    },
    step() {
      if (face < 0) return null;
      renderFace(face++);
      if (face < 6) return null;
      face = -1;
      return convert();
    },
    dispose() {
      cubeRT.dispose();
      pmrem.dispose();
      out?.dispose();
    },
  };
}

const isBulbish = (o, m) => /^bulbs_/i.test(o.name) || /^bulb_/i.test(m?.name || '') || m?.userData?.bulb;

/**
 * Meshes in `holder` that need a local probe: small metals (copper pots, lanterns, wires), glass and
 * clear-coated glaze. A palettised material (gltf-transform's PaletteMaterial, whose metalness comes
 * from a tiny palette texture) counts when it might hold a metal. Large meshes (walls, roofs) keep
 * the global environment: a probe captured inside a stall would paint its outside warm.
 */
export function probeTargets(holder, { maxRadius = 1.8 } = {}) {
  const out = [];
  const sphere = new THREE.Sphere();
  const ws = new THREE.Vector3();
  holder.traverse((o) => {
    if (!o.isMesh || o.isInstancedMesh || !o.geometry) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const hit = mats.some((m) => {
      if (!m || !m.isMeshStandardMaterial || isBulbish(o, m)) return false;
      const smallMap = (t) => !t || ((t.image?.width || 999) <= 128);
      const metal = m.metalness >= 0.5 && smallMap(m.metalnessMap);
      return metal || m.clearcoat > 0 || m.transmission > 0 || (m.transparent && m.opacity < 0.9 && m.roughness < 0.3);
    });
    if (!hit) return;
    if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
    sphere.copy(o.geometry.boundingSphere);
    o.getWorldScale(ws);
    if (sphere.radius * Math.max(ws.x, ws.y, ws.z) > maxRadius) return;
    out.push(o);
  });
  return out;
}

/**
 * A local reflection probe for `meshes`: the scene captured from the middle of them (with them
 * hidden), assigned as their material's envMap. Materials are cloned per probe so models sharing
 * a material keep their own reflections. Returns { target, position, meshes, dispose() }.
 */
export function captureProbe(renderer, scene, meshes, { size = 128, intensity = 1, hide = [], position = null } = {}) {
  const box = new THREE.Box3();
  meshes.forEach((m) => box.expandByObject(m));
  const p = position ? position.clone() : box.getCenter(new THREE.Vector3());
  const hidden = [...meshes, ...hide];
  const target = captureScene(renderer, scene, p, { size, hide: hidden });
  const clones = new Map();
  meshes.forEach((o) => {
    const swap = (m) => {
      if (!m || !m.isMeshStandardMaterial) return m;
      if (!clones.has(m)) {
        const c = m.clone();
        c.envMap = target.texture;
        c.envMapIntensity = intensity;
        c.userData.probe = true;
        clones.set(m, c);
      }
      return clones.get(m);
    };
    o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material);
  });
  return {
    target, position: p, meshes,
    dispose() { target.dispose(); clones.forEach((c) => c.dispose()); },
  };
}
