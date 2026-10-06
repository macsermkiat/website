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
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';
import { NIGHT, PROFILES } from './settings.js';
import { createSky } from './sky.js';
import { installHeightFog, recompile } from './fog.js';
import { syntheticEnvironment, createEnvUpdater, probeTargets, captureProbe } from './env.js';
import { installShading, bulbStrings } from './shading.js';
import { createSnow } from './snow.js';
import { GradePass } from './grade.js';
import { placeWarmLights, adoptEngineLights, tuneEmissives, retargetLight, bulbBounce, hubFade, bulbMinSize } from './lights.js';

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
  // ?lighting=key:value,... overrides profile numbers for measuring (e.g. lighting=lightBudget:4,glows:16,shadows:0)
  const urlProfile = {};
  try {
    const q = new URLSearchParams(globalThis.location?.search || '').get('lighting');
    for (const kv of (q || '').split(',').filter(Boolean)) {
      const [k, v] = kv.split(':');
      if (k && v != null && /^-?\d+(\.\d+)?$/.test(v)) urlProfile[k] = (k === 'shadows' || k === 'envCapture' || k === 'clouds' || k === 'grain') ? v !== '0' : +v;
    }
  } catch { /* no location */ }
  const P = { ...(lite ? PROFILES.lite : PROFILES.full), ...(options.profile || {}), ...urlProfile };
  const added = [];
  const add = (o) => { scene.add(o); added.push(o); return o; };
  const disposers = [];
  const _cam = new THREE.Vector3();
  const _buf = new THREE.Vector2();
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
    maxGlows: P.glows, maxClips: P.clips ?? 4, minRoughness: N.lightSize.minRoughness, minClearcoatRoughness: N.lightSize.minClearcoatRoughness, ao: N.ao,
    pointShadowTaps: N.warm.shadowMap?.taps ?? 5,
  });
  shading.setRim(new THREE.Vector3(...N.moon.skyDirection), new THREE.Color(N.rim.color), N.rim.strength, N.rim.power, N.rim.dark);
  if (N.town) {
    const T = N.town;
    shading.setTownWash(new THREE.Color().setRGB(...T.color), T.intensity, T.r0, T.r1, T.height, T.facing);
  }
  // round 4: figures get a highlight shoulder and a close-up fill (shading.js, LIGHTING_FIGURE)
  if (N.figure) {
    const F = N.figure;
    shading.setFigure(new THREE.Color().setRGB(...F.fill.color), F.fill.intensity, F.fill.near, F.fill.far, F.knee, F.range, F.spec);
  }
  // A figure is a skinned mesh under the crowd's group (crowd.js names it `crowd`), or any material
  // the crowd lifted (userData.crowdLift) or flagged userData.figure. The crowd arrives after the
  // lighting, and swaps figures as it loads, so this runs again every couple of seconds; each
  // material is marked once (a define, so three compiles the figure variant once per material kind).
  const figureMats = new Set();
  let lastMark = -1;
  function markFigures() {
    if (!N.figure) return 0;
    let n = 0;
    const mark = (m) => {
      if (!m || figureMats.has(m) || !m.isMaterial || !('roughness' in m || 'shininess' in m)) return;
      m.defines = { ...(m.defines || {}), LIGHTING_FIGURE: '' };
      m.needsUpdate = true;
      figureMats.add(m);
      n++;
    };
    const visit = (o, inCrowd) => {
      if (o.isMesh) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of mats) if ((inCrowd && o.isSkinnedMesh) || m?.userData?.crowdLift || m?.userData?.figure || o.userData?.figure) mark(m);
      }
      const c = inCrowd || o.name === 'crowd';
      for (const ch of o.children) visit(ch, c);
    };
    visit(scene, false);
    return n;
  }

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
  // round 4: a wash under a bulb string that no light_ of its model reaches (the Bücherstand's rack
  // canopies), toward the model's front, so the boards the canopy shadows are lit by its bulbs
  const _cw = new THREE.Vector3(), _cq = new THREE.Quaternion();
  function canopyGlows(mesh, strings) {
    const C = N.canopy;
    if (!C || !C.intensity || !strings.length || mesh.isInstancedMesh) return [];
    const pos = mesh.geometry?.attributes?.position;
    if (!pos) return [];
    // the model: the outermost ancestor under the scene (a placed holder, or the bench's stall)
    let model = mesh;
    while (model.parent && model.parent !== scene && !model.parent.isScene) model = model.parent;
    // section stalls only (the market's layout kind, or the bench's): the tree's and the deco stalls'
    // short low strings would otherwise each take a priority glow slot (the first market run gave
    // the tree 23 of them)
    const kind = model.userData?.entry?.kind || model.userData?.kind;
    if (kind !== 'section') return [];
    const lamps = [];
    model.traverse((x) => { if (/^light_/.test(x.name)) lamps.push(x.getWorldPosition(new THREE.Vector3())); });
    if (!lamps.length) return [];
    model.getWorldQuaternion(_cq);
    const front = new THREE.Vector3(0, 0, 1).applyQuaternion(_cq).setY(0).normalize();
    // bulbStrings joins strings up to a cell apart in height, so a rack canopy's string 0.3 m under
    // the eave string becomes part of it: cluster the bulbs again, finer in height (0.1 m cells, so
    // strings more than ~0.2 m apart in height stay apart), and keep the clusters that hang lower than
    // the model's top string, are at least `minLength` m long and that no light_ reaches
    mesh.updateWorldMatrix(true, false);
    const cells = new Map(), v = new THREE.Vector3();
    const step = Math.max(1, Math.floor(pos.count / 4000));
    let topY = -Infinity;
    for (let i = 0; i < pos.count; i += step) {
      v.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
      topY = Math.max(topY, v.y);
      const k = [Math.floor(v.x / 0.2), Math.floor(v.y / 0.1), Math.floor(v.z / 0.2)];
      const key = k.join(',');
      let c = cells.get(key);
      if (!c) cells.set(key, (c = { k, p: new THREE.Vector3(), n: 0 }));
      c.p.add(v); c.n++;
    }
    const seen = new Set(), comps = [];
    for (const [key0, c0] of cells) {
      if (seen.has(key0)) continue;
      seen.add(key0);
      const comp = [], stack = [c0];
      while (stack.length) {
        const c = stack.pop();
        comp.push(c);
        for (let dx = -2; dx <= 2; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -2; dz <= 2; dz++) {
          const k = `${c.k[0] + dx},${c.k[1] + dy},${c.k[2] + dz}`;
          if (cells.has(k) && !seen.has(k)) { seen.add(k); stack.push(cells.get(k)); }
        }
      }
      comps.push(comp.map((c) => c.p.clone().divideScalar(c.n)));
    }
    const out = [];
    const base = model.getWorldPosition(new THREE.Vector3()).y;
    for (const pts of comps) {
      if (out.length >= C.perModel) break;
      // the two cells farthest apart in plan are the string's ends
      let a = pts[0], b = pts[0], best = 0;
      for (const p of pts) for (const q of pts) { const d = Math.hypot(p.x - q.x, p.z - q.z); if (d > best) { best = d; a = p; b = q; } }
      const mid = pts.reduce((m, p) => m.add(p), new THREE.Vector3()).divideScalar(pts.length);
      if (best < C.minLength || mid.y > topY - C.below) continue;
      const away = Math.min(...lamps.map((p) => Math.hypot(p.x - mid.x, p.z - mid.z)));
      if (away < C.minAway) continue;
      // just under the bulbs and a little toward the model's front, so the light comes down onto the
      // boards from above and the front, as from the bulbs; the ends drawn in by `inset` of the
      // length, so the wash stays on the rack and off its neighbours (the display cabinets)
      const off = front.clone().multiplyScalar(C.out).add(new THREE.Vector3(0, -C.down, 0));
      const y = mid.y;
      const ea = a.clone().lerp(b, C.inset), eb = b.clone().lerp(a, C.inset);
      out.push(shading.add({
        a: ea.setY(y).add(off), b: eb.setY(y).add(off), color: C.color, intensity: C.intensity, reach: C.reach,
        oneSided: true, floor: base + C.floor, ceiling: y - C.ceiling, tag: 'canopy', priority: 1,
      }));
    }
    if (out.length) console.info(`[lighting] ${out.length} canopy wash${out.length > 1 ? 'es' : ''} under the bulb strings of ${model.name || 'a model'}: ${out.map((e) => `${e.a.toArray().map((x) => x.toFixed(2))}..${e.b.toArray().map((x) => x.toFixed(2))}`).join(' | ')}`);
    return out;
  }
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
      const entries = strings.map((st) => shading.add({ a: st.a, b: st.b, color, intensity: G.intensity, reach: G.reach, tag: 'bulbs' }));
      entries.push(...canopyGlows(o, strings));
      glowOf.set(o, entries);
    });
  }
  const emissives = tuneEmissives(scene, N, { lite });
  // bulbs keep ~2 px across when MSAA is off (lights.js bulbMinSize); uBulbPx is set each frame in update()
  const bulbPx = { uBulbPx: { value: 0 } };
  const bulbMin = (set) => { if (!P.msaa) bulbMinSize(set, bulbPx); };
  bulbMin(emissives.bulbs);
  addBulbGlows(scene);
  // LEGACY: re-tune lights the engine placed before this module ran (main.js now calls placeLights)
  const adopted = options.adoptEngineLights === true
    ? adoptEngineLights(scene, N, { shadowed: P.shadows ? P.shadowedLights : 0, focus: camera.getWorldPosition(new THREE.Vector3()) })
    : [];
  const placed = [];
  const allSpots = [], allViews = [];
  const clipOf = new Map(); // light -> its interior clip entry (shading.js)
  function placeLights(spots, opts = {}) {
    const r = placeWarmLights(scene, spots, N, { lite, budget: P.lightBudget, shadowed: P.shadows ? P.shadowedLights : 0, ...opts });
    r.glows = (r.interiors || []).map((g) => shading.add(g));
    (r.fixtures || []).forEach((f) => scene.add(f));
    allSpots.push(...(r.spots || []));
    allViews.push(...(r.views || []));
    // unshadowed interior lights (lite) are clipped to their stall's interior box
    r.clipEntries = (r.clips || []).map((c) => { const e = shading.addClip(c); if (e) clipOf.set(c.light, e); return e; }).filter(Boolean);
    const dispose = r.dispose;
    r.dispose = () => { r.glows.forEach((g) => shading.remove(g)); r.clipEntries.forEach((c) => shading.removeClip(c)); dispose(); };
    shading.update(camera.getWorldPosition(_cam));
    placed.push(r);
    const tags = {};
    r.glows.forEach((g) => (tags[g.tag] = (tags[g.tag] || 0) + 1));
    console.info(`[lighting] placed ${r.lights.length} lights (${r.lights.filter((l) => l.castShadow).length} shadowed, ${r.clipEntries.length} clipped to their stall), ${r.pools.length} pools, glows ${JSON.stringify(tags)}`);
    return r;
  }
  // ---------- the entered place gets the lights (Codex round 1, fix 3) ----------
  // When the visitor enters a place (the camera settles at its cam_view, or the engine calls
  // focusPlace(id)), its light_ spots that have no real light borrow one: unshadowed lights are moved
  // from the least important, farthest models (deco before landmark before section; far before near),
  // up to P.focusLights. On the lite market that is how the bandstand, the wheel and the carousel get a
  // real light when entered, and a section stall gets its front fill. Leaving puts every light back.
  // The count of point and spot lights never changes, so no material recompiles; lights fade in.
  const moved = new Map(); // light -> its home spot
  const fades = new Map(); // light -> intensity it fades up to
  let focusId = null, focusExplicit = false;
  const DONATE = { deco: 3, lamp: 3, strings: 3, other: 3, ground: 3, landmark: 2, tree: 2, section: 1 };
  const ofPlace = (s, id) => s.id === id || s.holder?.userData?.place === id || s.holder?.userData?.entry?.place === id;
  function glowHow(id) {
    const interior = allSpots.find((s) => s.id === id && !s.front && s.light);
    const how = interior ? (interior.light.castShadow ? 'lit' : 'unshadowed') : 'only';
    for (const g of shading.glows) if (g.tag === 'interior' && g.id === id) { g.how = how; g.intensity = N.glow.interior[how]; }
  }
  function moveLight(L, s) {
    const prev = L.userData.spot;
    const old = clipOf.get(L);
    if (old) { shading.removeClip(old); clipOf.delete(L); }
    const { target, clip } = retargetLight(L, s, N, { lite });
    if (clip) { const e = shading.addClip(clip); if (e) clipOf.set(L, e); }
    if (prev && prev !== s) prev.light = null;
    s.light = L;
    L.intensity = 0;
    fades.set(L, target);
    if (prev) glowHow(prev.id);
    glowHow(s.id);
  }
  /** Give the place `id` (a place id such as 'glueh', or a layout id) the real lights; null gives them back. */
  function focusPlace(id, { auto = false } = {}) {
    // round 2, fix pass: once the engine calls focusPlace itself (openPlace / close), the camera-settle
    // detection stops for good, so focusPlace(null) on close does not hand control back to it
    if (!auto) focusExplicit = true;
    id = id || null;
    if (id === focusId) return focusId;
    for (const [L, home] of moved) moveLight(L, home);
    moved.clear();
    focusId = id;
    if (id) {
      const mine = allSpots.filter((s) => ofPlace(s, id));
      if (mine.length) {
        const center = mine[0].holder.getWorldPosition(new THREE.Vector3());
        const room = Math.max(0, (N.warm.perModel ?? 2) - mine.filter((s) => s.light).length);
        const need = mine.filter((s) => !s.light).sort((a, b) => (a.lk !== a.kind) - (b.lk !== b.kind) || a.front - b.front).slice(0, Math.min(P.focusLights ?? 2, room));
        const donors = allSpots
          .filter((s) => s.light && !s.light.castShadow && !ofPlace(s, id) && s.light.parent)
          .sort((a, b) => (DONATE[b.lk] ?? 3) - (DONATE[a.lk] ?? 3) || b.pos.distanceTo(center) - a.pos.distanceTo(center));
        for (const s of need) {
          const wantSpot = s.front && !lite;
          let i = donors.findIndex((d) => !!d.light.isSpotLight === wantSpot);
          if (i < 0) i = donors.findIndex((d) => !d.light.isSpotLight);
          if (i < 0) break;
          const d = donors.splice(i, 1)[0];
          moved.set(d.light, d);
          moveLight(d.light, s);
        }
      }
    }
    shading.update(camera.getWorldPosition(_cam));
    console.info(`[lighting] focus ${focusId || 'none'} (${moved.size} lights moved)`);
    return focusId;
  }
  // the entered place, from the camera: at (or near) a place's cam_view, looking toward its cam_target
  // Only once the camera has settled (moved < 5 cm since the last check), so a flight that passes near
  // another place's view on its way does not move lights; "near" is within 1.5 m, or 12 % of the
  // distance from cam_view to cam_target for the far views of the rides (the engine may dolly in a bit).
  const _va = new THREE.Vector3(), _vb = new THREE.Vector3(), _vd = new THREE.Vector3(), _vc = new THREE.Vector3();
  const _vLast = new THREE.Vector3(1e9, 0, 0);
  function enteredPlace() {
    camera.getWorldPosition(_vc);
    const settled = _vc.distanceTo(_vLast) < 0.05;
    _vLast.copy(_vc);
    if (!settled) return focusId;
    camera.getWorldDirection(_vd);
    let best = null, bs = Infinity;
    for (const v of allViews) {
      if (!v.view.parent) continue;
      v.view.getWorldPosition(_va);
      (v.target || v.holder).getWorldPosition(_vb);
      const span = Math.max(1, _va.distanceTo(_vb));
      const d = _vc.distanceTo(_va);
      const look = _vd.dot(_vb.sub(_vc).normalize());
      if (d < Math.max(1.5, 0.12 * span) && look > 0.9 && d < bs) { bs = d; best = v.holder.userData?.place || v.id; }
    }
    return best;
  }

  function tune(root) {
    const r = tuneEmissives(root, N, { lite });
    try { const n = bulbBounce(root, N); if (n) console.info(`[lighting] bulb bounce on ${n} materials of ${root.name || 'a model'}`); } catch (e) { console.warn('[lighting] bulb bounce failed', e); }
    try { const h = hubFade(root, N, r.bulbs); if (h) console.info(`[lighting] hub fade on ${h} bulb meshes of ${root.name || 'a model'}`); } catch (e) { console.warn('[lighting] hub fade failed', e); }
    bulbMin(r.bulbs); // after hubFade, which adds its clones to r.bulbs
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
  // Edge smoothing by FXAA on the graded image instead of MSAA (2026-10-06): on Mac's M3 MacBook Air the
  // multisampled half-float targets (every post pass ping-pongs through them) cost 10-15x the frame time;
  // msaa:0 took the full market from ~650 ms to ~45 ms a frame. ?lighting=msaa:4 brings MSAA back for comparison.
  // FXAA alone smooths a lone bright pixel away as if it were a jagged edge, and the bulb strings across the square
  // vanished with it; a pixel much brighter than FXAA's result keeps its own colour. ?lighting=fxaa:0 turns it off.
  const fxaa = P.msaa || P.fxaa === 0 ? null : new ShaderPass({
    ...FXAAShader,
    fragmentShader: FXAAShader.fragmentShader.replace(
      'gl_FragColor = ApplyFXAA( tDiffuse, resolution.xy, vUv );',
      `vec4 aa = ApplyFXAA( tDiffuse, resolution.xy, vUv );
			vec4 own = texture2D( tDiffuse, vUv );
			float lo = dot( own.rgb, vec3( 0.299, 0.587, 0.114 ) ), la = dot( aa.rgb, vec3( 0.299, 0.587, 0.114 ) );
			gl_FragColor = ( lo > 0.35 && lo > la * 1.25 ) ? own : aa;`),
  });
  if (fxaa) composer.addPass(fxaa);
  const setSize = composer.setSize.bind(composer);
  composer.setSize = (w, h) => {
    setSize(w, h);
    if (fxaa) { const r = Math.min(prWanted, prCap); fxaa.material.uniforms.resolution.value.set(1 / Math.max(1, w * r), 1 / Math.max(1, h * r)); }
  };
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
  // a camera override for screenshots and tuning (shoot-market.mjs "@cam="): applied every frame after
  // the engine's camera rig has run, so any view of the market can be framed; null hands the camera back
  let camOverride = null;
  function debugCamera(pos, target) {
    camOverride = pos ? { pos: new THREE.Vector3(...pos), target: new THREE.Vector3(...target) } : null;
  }
  function update(dt = 0.016, t = 0) {
    frame++;
    if (camOverride) { camera.position.copy(camOverride.pos); camera.lookAt(camOverride.target); camera.updateMatrixWorld(); }
    const rawDt = Math.max(dt || 0, 0);
    dt = Math.min(rawDt, 0.1);
    if (!P.msaa && camera.isPerspectiveCamera) {
      renderer.getDrawingBufferSize(_buf);
      bulbPx.uBulbPx.value = (P.bulbPx ?? 1) * 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) / (camera.zoom || 1) / Math.max(1, _buf.y);
    }
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
        const ms = P.adaptiveMs || [16.7, 18.2];
        if (s.p50 > (quality.level === 0 ? ms[0] : ms[1])) { stepDown(); ftN = 0; }
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

    if (frame === 2 || wall - lastMark > 2) { lastMark = wall; markFigures(); }
    if (P.shadows && moonShadowEvery > 1 && frame % moonShadowEvery === 0) moonLight.shadow.needsUpdate = true;

    // the entered place gets the lights (unless the engine sets it with focusPlace)
    if (!focusExplicit && frame % 10 === 5 && allViews.length && (P.focusLights ?? 0) > 0) {
      const id = enteredPlace();
      if (id !== focusId) focusPlace(id, { auto: true });
    }
    for (const [L, want] of fades) {
      L.intensity = damp(L.intensity, want, 3, Math.max(rawDt, wdt));
      if (Math.abs(L.intensity - want) < 0.01 * want) { L.intensity = want; fades.delete(L); }
    }
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
    figureMats.forEach((m) => { if (m.defines) { delete m.defines.LIGHTING_FIGURE; m.needsUpdate = true; } });
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
    focusPlace,
    debugCamera,
    get focus() { return focusId; },
    get focusMoves() { return [...moved.keys()].map((L) => ({ light: L.name, place: L.userData.spot?.id, from: moved.get(L).id })); },
    tune,
    markFigures,
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
