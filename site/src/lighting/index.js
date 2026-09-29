// The night: sky, moonlight, fill, fog, reflections, tone mapping, bloom, warm lights and snow.
//
//   const lighting = createLighting({ scene, renderer, camera, lite });
//   lighting.composer.render(dt);          // every frame, after lighting.update(dt, t)
//   lighting.setSnow(true);                // flakes fade in, fog thickens, stars go behind cloud
//
// Also returned (optional for the engine): placeLights(spots, opts), tune(root), captureEnvironment(pos),
// refreshEnvironment(), captureProbes(), fitShadow(center, radius), stats(), settings, profile, and the
// parts (sky, moonLight, hemi, bloom, grade, shading).
// See README.md in this folder for the settings and the reasoning behind them.
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { NIGHT, PROFILES } from './settings.js';
import { createSky } from './sky.js';
import { installHeightFog, recompile } from './fog.js';
import { syntheticEnvironment, createEnvUpdater, probeTargets, captureProbe } from './env.js';
import { installShading, bulbStrings } from './shading.js';
import { createSnow } from './snow.js';
import { GradePass } from './grade.js';
import { placeWarmLights, adoptEngineLights, tuneEmissives } from './lights.js';

export { NIGHT, PROFILES } from './settings.js';
export { placeWarmLights, tuneEmissives } from './lights.js';

/** Bloom at a fraction of the composer's resolution (the lite market blooms at half size). */
class ScaledBloomPass extends UnrealBloomPass {
  constructor(res, strength, radius, threshold, scale = 1) {
    super(new THREE.Vector2(Math.max(2, res.x * scale), Math.max(2, res.y * scale)), strength, radius, threshold);
    this.scale = scale;
    this.fullSize = res.clone();
  }
  setSize(w, h) {
    this.fullSize.set(w, h);
    super.setSize(Math.max(2, Math.round(w * this.scale)), Math.max(2, Math.round(h * this.scale)));
  }
  setScale(scale) { this.scale = scale; this.setSize(this.fullSize.x, this.fullSize.y); }
}

const PROBE_KINDS = new Set(['section', 'deco', 'landmark']);
const damp = (a, b, rate, dt) => a + (b - a) * (1 - Math.exp(-rate * dt));

/**
 * @param {object} ctx
 * @param {THREE.Scene} ctx.scene
 * @param {THREE.WebGLRenderer} ctx.renderer
 * @param {THREE.Camera} ctx.camera
 * @param {boolean} [ctx.lite] the lite market: fewer lights, no shadows, cheaper post
 * @param {object} [ctx.options] { shadowCenter:[x,y,z], shadowRadius, envCapturePosition:[x,y,z], envCapture,
 *   probes, adaptive, profile:{...overrides}, adoptEngineLights (legacy, off) }
 */
export function createLighting({ scene, renderer, camera, lite = false, options = {} }) {
  const N = NIGHT;
  const P = { ...(lite ? PROFILES.lite : PROFILES.full), ...(options.profile || {}) };
  const added = [];
  const add = (o) => { scene.add(o); added.push(o); return o; };
  const disposers = [];
  const _cam = new THREE.Vector3();
  // the renderer state this module changes, put back by dispose()
  const was = {
    toneMapping: renderer.toneMapping,
    exposure: renderer.toneMappingExposure,
    outputColorSpace: renderer.outputColorSpace,
    shadows: renderer.shadowMap.enabled,
    shadowType: renderer.shadowMap.type,
    background: scene.background,
    environment: scene.environment,
    environmentIntensity: scene.environmentIntensity,
    fog: scene.fog,
  };

  // ---------- colour management and tone mapping ----------
  // The scene renders linear HDR into a half-float target; GradePass does AgX + look + sRGB.
  THREE.ColorManagement.enabled = true;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping; // for anything rendered straight to the screen
  renderer.toneMappingExposure = N.exposure;
  renderer.shadowMap.enabled = P.shadows;
  renderer.shadowMap.type = THREE.PCFShadowMap; // three r18x: PCF is Vogel-disk soft, radius-controlled

  // ---------- fog (with ground mist) ----------
  const fogPatch = installHeightFog({ mist: N.fog.mist, mistHeight: N.fog.mistHeight });
  const fogBase = { color: new THREE.Color(N.fog.color), density: N.fog.density };
  scene.fog = new THREE.FogExp2(fogBase.color.clone(), fogBase.density);
  scene.background = fogBase.color.clone();
  recompile(scene);

  // ---------- light size, local glows (bulb strings, stall interiors) and moon rim ----------
  const shading = installShading({
    maxGlows: P.glows, maxClips: P.clips ?? 4, minRoughness: N.lightSize.minRoughness, minClearcoatRoughness: N.lightSize.minClearcoatRoughness,
    pointShadowTaps: N.warm.shadowMap?.taps ?? 5,
  });
  shading.setRim(new THREE.Vector3(...N.moon.skyDirection), new THREE.Color(N.rim.color), N.rim.strength, N.rim.power, N.rim.dark);

  // ---------- sky ----------
  const sky = createSky(N, { clouds: P.clouds });
  add(sky.mesh);

  // ---------- moonlight and fill ----------
  const hemi = add(new THREE.HemisphereLight(N.hemi.sky, N.hemi.ground, N.hemi.intensity));
  hemi.name = 'lighting_hemi';
  const moonLight = new THREE.DirectionalLight(N.moon.lightColor, N.moon.lightIntensity);
  moonLight.name = 'lighting_moon';
  const moonDir = new THREE.Vector3(...N.moon.lightDirection).normalize();
  const shadowCenter = new THREE.Vector3(...(options.shadowCenter || [0, 0, -4]));
  let shadowRadius = options.shadowRadius || 42;
  add(moonLight);
  add(moonLight.target);
  function fitShadow(center = shadowCenter, radius = shadowRadius) {
    shadowCenter.copy(center);
    shadowRadius = radius;
    moonLight.target.position.copy(center);
    moonLight.position.copy(center).addScaledVector(moonDir, radius * 2);
    const c = moonLight.shadow.camera;
    Object.assign(c, { left: -radius, right: radius, top: radius, bottom: -radius, near: radius * 0.5, far: radius * 3.5 });
    c.updateProjectionMatrix();
    moonLight.shadow.needsUpdate = true;
  }
  if (P.shadows) {
    moonLight.castShadow = true;
    moonLight.shadow.mapSize.set(P.shadowMapSize, P.shadowMapSize);
    moonLight.shadow.radius = P.shadowRadius;
    moonLight.shadow.bias = -0.0004;
    moonLight.shadow.normalBias = 0.025;
    moonLight.shadow.intensity = 0.85;
    moonLight.shadow.autoUpdate = !(P.moonShadowEvery > 1);
  }
  let moonShadowEvery = P.moonShadowEvery || 1;
  fitShadow();

  // ---------- environment for reflections ----------
  // The synthetic night first; on full, the real market is captured once on frame 3. There is no
  // periodic refresh (the market is static apart from the rides and the crowd): the capture is
  // repeated, one cube face per frame, only once the snow has settled after a toggle, or when the
  // engine calls refreshEnvironment() after changing the lights. Local probes (frame 3) give copper,
  // glass and glaze near the view their own reflections of the lit stall around them.
  const synthRT = syntheticEnvironment(renderer, sky, { size: P.envSize });
  scene.environment = synthRT.texture;
  scene.environmentIntensity = N.env.intensity;
  const envCapture = options.envCapture ?? P.envCapture;
  const envPos = new THREE.Vector3(...(options.envCapturePosition || [0, 1.6, 2]));
  let updater = null;
  const hideInCapture = [];
  let refreshAt = Infinity, wall = 0; // wall-clock time of a pending re-capture
  function captureEnvironment(position = envPos) {
    updater ||= createEnvUpdater(renderer, scene, { size: P.envSize, hide: hideInCapture });
    envPos.copy(position);
    const rt = updater.captureNow(position);
    scene.environment = rt.texture;
    scene.environmentIntensity = N.env.captureIntensity;
  }
  /** Re-capture the market's reflections, spread over six frames (full only; call after changing the lights). */
  function refreshEnvironment(delay = 0) {
    if (!envCapture) return false;
    refreshAt = wall + Math.max(0, delay);
    return true;
  }
  const probes = [];
  const probeCount = options.probes ?? P.probes;
  /** Local probes for the `count` models nearest the camera that hold copper, glass or glaze. */
  function captureProbes(count = probeCount) {
    const cam = camera.getWorldPosition(new THREE.Vector3());
    const holders = new Map();
    scene.children.forEach((h) => {
      if (h === sky.mesh || h === snow.group || h.isLight) return;
      // stalls and landmarks only: rides turn (a static probe would lie) and the town ring is too big
      const kind = h.userData.entry?.kind || h.userData.kind;
      if (!PROBE_KINDS.has(kind)) return;
      const meshes = probeTargets(h).filter((m) => !m.material?.userData?.probe);
      if (meshes.length) holders.set(h, meshes);
    });
    const ranked = [...holders.entries()]
      .map(([h, meshes]) => ({ meshes, d: new THREE.Box3().setFromObject(h).distanceToPoint(cam) }))
      .sort((a, b) => a.d - b.d).slice(0, count);
    for (const r of ranked) {
      try { probes.push(captureProbe(renderer, scene, r.meshes, { size: P.probeSize, intensity: N.env.probeIntensity, hide: hideInCapture })); } catch (e) { console.warn('[lighting] probe capture failed', e); }
    }
    return probes.length;
  }

  // ---------- emissives, bulb-string glows and warm lights ----------
  const glowOf = new Map(); // bulbs_ mesh -> its glows
  function addBulbGlows(root) {
    const G = N.glow.bulbs;
    root.traverse((o) => {
      if (!o.isMesh || glowOf.has(o)) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const bulb = mats.find((m) => /^bulb_(warm|cold)/i.test(m?.name || '') || m?.userData?.bulb);
      if (!bulb && !/^bulbs_/i.test(o.name)) return;
      const cold = /cold/i.test(bulb?.name || '');
      const color = cold ? N.emissive.cold.color : N.emissive.warm.color;
      // strings on stalls only: short and level (the wheel, the carousel crown, the tree and the
      // long festoons across the square are skipped: they move, or hang far from anything to light)
      const strings = bulbStrings(o).filter((st) => st.a.distanceTo(st.b) <= G.maxLength && st.height <= G.maxHeight);
      glowOf.set(o, strings.map((st) => shading.add({ a: st.a, b: st.b, color, intensity: G.intensity, reach: G.reach, tag: 'bulbs' })));
    });
  }
  const emissives = tuneEmissives(scene, N, { lite });
  addBulbGlows(scene);
  // LEGACY: re-tune lights the engine placed before this module ran (main.js now calls placeLights)
  const adopted = options.adoptEngineLights === true
    ? adoptEngineLights(scene, N, { shadowed: P.shadows ? P.shadowedLights : 0, focus: camera.getWorldPosition(new THREE.Vector3()) })
    : [];
  const placed = [];
  function placeLights(spots, opts = {}) {
    const r = placeWarmLights(scene, spots, N, { lite, budget: P.lightBudget, shadowed: P.shadows ? P.shadowedLights : 0, ...opts });
    r.glows = (r.interiors || []).map((g) => shading.add(g));
    // unshadowed interior lights (lite) are clipped to their stall's interior box
    r.clipEntries = (r.clips || []).map((c) => shading.addClip(c)).filter(Boolean);
    const dispose = r.dispose;
    r.dispose = () => { r.glows.forEach((g) => shading.remove(g)); r.clipEntries.forEach((c) => shading.removeClip(c)); dispose(); };
    shading.update(camera.getWorldPosition(_cam));
    placed.push(r);
    const tags = {};
    r.glows.forEach((g) => (tags[g.tag] = (tags[g.tag] || 0) + 1));
    console.info(`[lighting] placed ${r.lights.length} lights (${r.lights.filter((l) => l.castShadow).length} shadowed, ${r.clipEntries.length} clipped to their stall), ${r.pools.length} pools, glows ${JSON.stringify(tags)}`);
    return r;
  }
  function tune(root) {
    const r = tuneEmissives(root, N, { lite });
    r.bulbs.forEach((m) => emissives.bulbs.add(m));
    r.windows.forEach((m) => emissives.windows.add(m));
    addBulbGlows(root);
    return r;
  }

  // ---------- moon shadow casters ----------
  // Once the static interior shadows are drawn, meshes of the placed models (stalls, props, the town)
  // smaller than P.minMoonCaster stop casting the moon's shadow: at 5.5 cm a texel their shadow is a
  // blur of a few texels, and each is a draw call in every moon-shadow pass. The crowd and anything
  // not from the layout keep theirs (a figure's head must not lose its shadow).
  const trimmed = [];
  function trimMoonCasters(root = scene) {
    const min = P.minMoonCaster || 0;
    if (!P.shadows || !min) return 0;
    const ws = new THREE.Vector3();
    let n = 0;
    for (const h of root === scene ? scene.children : [root]) {
      if (!h.userData?.entry) continue;
      h.traverse((o) => {
        if (!o.isMesh || !o.castShadow || o.isInstancedMesh || o.isSkinnedMesh || !o.geometry) return;
        if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
        o.getWorldScale(ws);
        if (o.geometry.boundingSphere.radius * Math.max(ws.x, ws.y, ws.z) >= min) return;
        o.castShadow = false;
        trimmed.push(o);
        n++;
      });
    }
    return n;
  }

  // ---------- snow ----------
  const snow = createSnow({ layers: P.snowLayers, camera, renderer });
  add(snow.group);
  hideInCapture.push(snow.group);
  let snowTarget = 0, snowMix = 0;
  const wind = new THREE.Vector2(), windOffset = new THREE.Vector2();
  let lastT = null;

  // ---------- post: render -> bloom -> grade (AgX, sRGB, vignette, grain) ----------
  const size = renderer.getSize(new THREE.Vector2());
  const pr = renderer.getPixelRatio();
  const W = Math.max(2, size.x * pr), H = Math.max(2, size.y * pr);
  const target = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: P.msaa });
  const composer = new EffectComposer(renderer, target);
  // the composer's pixel ratio can be capped below the canvas's (adaptive quality); the grade pass
  // upsamples to the canvas
  let prCap = Infinity, prWanted = pr;
  const setPR = composer.setPixelRatio.bind(composer);
  composer.setPixelRatio = (v) => { prWanted = v; setPR(Math.min(v, prCap)); };
  composer.setPixelRatio(pr);
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);
  const bloom = new ScaledBloomPass(new THREE.Vector2(W, H), N.bloom.strength, N.bloom.radius, N.bloom.threshold, P.bloomScale);
  bloom.highPassUniforms.smoothWidth.value = N.bloom.knee;
  function bloomLook(half) {
    const B = half ? { ...N.bloom, ...N.bloomHalf } : N.bloom;
    bloom.compositeMaterial.uniforms.bloomFactors.value = B.factors.slice();
    base.bloom = B.strength;
  }
  // clamp what feeds the bloom (by the brightest channel, keeping hue) so a specular glint on copper
  // or glaze enters no brighter than a bulb, and a few glint pixels cannot outshine a string of bulbs
  const hp = bloom.materialHighPassFilter;
  hp.fragmentShader = hp.fragmentShader.replace(
    'vec4 texel = texture2D( tDiffuse, vUv );',
    `vec4 texel = texture2D( tDiffuse, vUv ); texel.rgb *= min( 1.0, ${N.bloom.clamp.toFixed(2)} / max( max( texel.r, max( texel.g, texel.b ) ), 1e-4 ) );`,
  );
  hp.needsUpdate = true;
  composer.addPass(bloom);
  const grade = new GradePass({ exposure: N.exposure, punch: N.punch, vignette: N.vignette, grain: P.grain ? N.grain : 0 });
  grade.exposureFrom = renderer;
  composer.addPass(grade);
  composer.setSize(size.x || 256, size.y || 256);

  // ---------- per frame ----------
  let frame = 0;
  const base = {
    hemi: N.hemi.intensity,
    moon: N.moon.lightIntensity,
    stars: N.sky.starIntensity,
    clouds: P.clouds ? N.sky.clouds : 0,
    moonDisc: sky.uniforms.uMoonColor.value.clone(),
    bloom: N.bloom.strength,
    bloomRadius: N.bloom.radius,
  };
  bloomLook(P.bloomScale < 1);

  // ---------- adaptive quality (full only) ----------
  // Measured in wall-clock time after the first captures. If the median frame is slower than
  // ~55 fps, step down once per window: 1) MSAA 4x -> 2x, 2) composer pixel ratio <= 1.5,
  // 3) bloom at half resolution (with the half-resolution bloom weights). Never steps back up.
  // ?lighting-adaptive=0 in the page URL turns it off (for profiling the fixed full profile)
  let urlAdaptive = null;
  try { urlAdaptive = new URLSearchParams(globalThis.location?.search || '').get('lighting-adaptive'); } catch { /* no location */ }
  const adaptive = (options.adaptive ?? (urlAdaptive != null ? urlAdaptive !== '0' : P.adaptive)) && !lite;
  const quality = { level: 0, msaa: P.msaa, pixelRatioCap: null, bloomScale: P.bloomScale, moonShadowEvery };
  const ft = new Float32Array(240);
  let ftN = 0, ftAll = 0, sinceStep = 0;
  function stepDown() {
    quality.level++;
    if (quality.level === 1 && P.msaa > 2) {
      quality.msaa = 2;
      for (const rt of [composer.renderTarget1, composer.renderTarget2]) { rt.samples = 2; rt.dispose(); }
    } else if (quality.level <= 2 && prWanted > 1.5) {
      quality.level = 2;
      prCap = 1.5;
      quality.pixelRatioCap = 1.5;
      composer.setPixelRatio(prWanted);
    } else if (quality.level <= 3 && bloom.scale > 0.5) {
      quality.level = 3;
      bloom.setScale(0.5);
      quality.bloomScale = 0.5;
      bloomLook(true);
    } else if (quality.level <= 4 && P.shadows && moonShadowEvery < 4) {
      quality.level = 4;
      moonShadowEvery = 4;
      moonLight.shadow.autoUpdate = false;
      quality.moonShadowEvery = 4;
    } else {
      quality.level = 5; // nothing left to give here; main.js offers the lite market
    }
    console.info('[lighting] adaptive quality', JSON.stringify(quality));
  }
  function stats() {
    const n = Math.min(ftN, ft.length);
    const a = Array.from(ft.slice(0, n)).sort((x, y) => x - y);
    const q = (p) => (n ? +a[Math.min(n - 1, Math.floor(p * n))].toFixed(2) : null);
    return { frames: ftAll, window: n, p50: q(0.5), p95: q(0.95), p99: q(0.99), fps: n ? +(1000 / q(0.5)).toFixed(1) : null, ...quality };
  }
  const snowFog = new THREE.Color(N.snow.fogColor);

  let lastWall = null;
  function update(dt = 0.016, t = 0) {
    frame++;
    const rawDt = Math.max(dt || 0, 0);
    dt = Math.min(rawDt, 0.1);
    const st = lastT == null ? 0 : Math.max(0, t - lastT); // scene time step (0 under reduced motion)
    lastT = t;
    // wall-clock step: the snow blend and the refresh timer run in real time, so a slow machine
    // (dt clamped to 0.1 s) still fades the weather in over ~2 s
    const now = performance.now();
    const wdt = lastWall == null ? 0 : (now - lastWall) / 1000;
    lastWall = now;
    wall += wdt;
    if (frame > 10 && wdt > 0) {
      ft[ftN++ % ft.length] = wdt * 1000;
      ftAll++;
      if (adaptive && quality.level < 5 && ++sinceStep >= 150 && ftN >= 150 && frame > 200) {
        const s = stats();
        if (s.p50 > 18.2) { stepDown(); ftN = 0; }
        sinceStep = 0;
      }
    }

    // snow blend: 0 clear night .. 1 snowing
    snowMix = damp(snowMix, snowTarget, 1.4, Math.max(rawDt, wdt));
    if (Math.abs(snowMix - snowTarget) < 0.001) snowMix = snowTarget;
    const k = snowMix;
    scene.fog.density = THREE.MathUtils.lerp(fogBase.density, N.snow.fogDensity, k);
    scene.fog.color.lerpColors(fogBase.color, snowFog, k);
    scene.background.copy(scene.fog.color);
    sky.uniforms.uFogColor.value.copy(scene.fog.color);
    sky.uniforms.uOvercast.value = k * 0.85;
    sky.uniforms.uStars.value = base.stars * (1 - k * (1 - N.snow.starsLeft));
    sky.uniforms.uClouds.value = P.clouds ? THREE.MathUtils.lerp(base.clouds, N.snow.clouds, k) : 0;
    sky.uniforms.uTime.value = t;
    hemi.intensity = base.hemi * THREE.MathUtils.lerp(1, N.snow.hemiBoost, k);
    moonLight.intensity = base.moon * THREE.MathUtils.lerp(1, N.snow.moonDim, k);
    bloom.strength = base.bloom * (1 + 0.15 * k);
    bloom.radius = base.bloomRadius + 0.12 * k; // snowy air scatters more

    // wind: a steady drift with slow gusts, integrated in scene time
    const g = 1 + N.snow.gust * (0.6 * Math.sin(t * 0.21) + 0.4 * Math.sin(t * 0.53 + 1.7));
    wind.set(N.snow.wind[0] * g, N.snow.wind[1] * (0.7 + 0.3 * Math.sin(t * 0.17)));
    windOffset.addScaledVector(wind, st);
    snow.uniforms.uFall.value = N.snow.fall;
    if (k > 0 && frame % 30 === 1) feedSnowLights();
    // the weather has settled after a toggle: re-capture the reflections once (full only)
    if (snowSettling && snowMix === snowTarget) { snowSettling = false; refreshEnvironment(N.env.settle); }
    snow.update({ t, windOffset, fog: scene.fog, opacity: k });

    if (P.shadows && moonShadowEvery > 1 && frame % moonShadowEvery === 0) moonLight.shadow.needsUpdate = true;

    // local glows nearest the camera into the shared uniform (the camera moves slowly)
    if (frame % 15 === 1) shading.update(camera.getWorldPosition(_cam));

    if (frame === 3) {
      if (envCapture) {
        try { captureEnvironment(); } catch (e) { console.warn('[lighting] environment capture failed', e); }
      }
      if (probeCount > 0) captureProbes();
    }
    // after the first frames have drawn the static interior shadows
    if (frame === 5) trimMoonCasters();
    if (wall >= refreshAt && frame > 3) {
      refreshAt = Infinity;
      if (updater) { if (!updater.busy) updater.start(envPos); } else captureEnvironment();
    }
    if (updater?.busy) updater.step();
  }

  const _wp = new THREE.Vector3(), _cp = new THREE.Vector3();
  function feedSnowLights() {
    camera.getWorldPosition(_cp);
    const all = [];
    scene.traverse((o) => { if ((o.isPointLight || o.isSpotLight) && o.visible && o.intensity > 0) all.push(o); });
    const near = all.map((o) => ({ o, d: o.getWorldPosition(_wp).distanceToSquared(_cp), position: o.getWorldPosition(new THREE.Vector3()) }))
      .sort((a, b) => a.d - b.d).slice(0, 4)
      .map((e) => ({ position: e.position, intensity: e.o.intensity * 0.012 }));
    snow.setWarmLights(near);
  }

  let snowSettling = false;
  function setSnow(on) {
    const next = on ? 1 : 0;
    if (next === snowTarget) return;
    snowTarget = next;
    // re-capture the reflections once the weather has settled (full market only; see update)
    snowSettling = envCapture;
  }

  function dispose() {
    trimmed.forEach((o) => (o.castShadow = true));
    added.forEach((o) => o.removeFromParent());
    placed.forEach((r) => r.dispose());
    snow.dispose();
    sky.mesh.geometry.dispose();
    sky.material.dispose();
    synthRT.dispose();
    updater?.dispose();
    probes.forEach((p) => p.dispose());
    shading.restore();
    bloom.dispose();
    grade.dispose();
    composer.dispose?.();
    target.dispose();
    if (globalThis.__lighting === api) delete globalThis.__lighting;
    fogPatch.restore();
    disposers.forEach((f) => f());
    // put the renderer and scene back as they were
    renderer.toneMapping = was.toneMapping;
    renderer.toneMappingExposure = was.exposure;
    renderer.outputColorSpace = was.outputColorSpace;
    renderer.shadowMap.enabled = was.shadows;
    renderer.shadowMap.type = was.shadowType;
    renderer.shadowMap.needsUpdate = true;
    scene.fog = was.fog;
    scene.background = was.background;
    scene.environment = was.environment;
    scene.environmentIntensity = was.environmentIntensity;
  }

  const api = {
    composer,
    update,
    setSnow,
    dispose,
    // helpers for the engine
    placeLights,
    tune,
    captureEnvironment,
    refreshEnvironment,
    captureProbes,
    trimMoonCasters,
    fitShadow,
    stats,
    quality,
    // parts, for tuning from the console or a test page
    settings: N,
    profile: P,
    lite,
    sky,
    hemi,
    moonLight,
    bloom,
    grade,
    shading,
    probes,
    renderPass,
    emissives,
    adoptedLights: adopted,
    get snow() { return snowTarget === 1; },
    get snowAmount() { return snowMix; },
  };
  globalThis.__lighting = api; // a debug handle for profiling and the console (perf.mjs reads stats())
  return api;
}

export default createLighting;
