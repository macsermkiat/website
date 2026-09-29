// Mac's Nachtmarkt: boot. Everything else lives in its own module; this file wires them together.
import './styles/main.css';
import * as THREE from 'three';
import { OutlinePass } from 'three/examples/jsm/postprocessing/OutlinePass.js';
import inventory from 'virtual:market-inventory';
import { chooseQuality, switchQuality } from './quality.js';
import { buildMarket, viewFor } from './engine/market.js';
import { setupLighting } from './engine/lighting.js';
import { placeLights } from './engine/lights.js';
import { createSnowfall } from './engine/snowfall.js';
import { redrawSigns } from './standins/index.js';
import { createCrowd } from './crowd.js';
import { createAudio } from './audio/index.js';
import { createActions } from './actions/index.js';
import { bandPositions } from './actions/band.js';
import { createCameraRig } from './interaction/camera.js';
import { createPicking } from './interaction/picking.js';
import { bindKeyboard, watchMotion } from './interaction/keyboard.js';
import { createPanel, buildPlaceNav } from './ui/panel.js';
import { SECTIONS, ORDER, bookPicks, phrases, taglineHtml } from './content.js';

const $ = (id) => document.getElementById(id);
const warnings = [];
const warn = (msg) => { warnings.push(msg); console.warn('[market]', msg); };
const debug = new URLSearchParams(location.search).has('debug');

function inSeason() {
  const d = new Date(), m = d.getMonth(), day = d.getDate();
  return (m === 10 && day >= 20) || m === 11 || (m === 0 && day <= 6);
}

function fail(msg) {
  $('loadingText').textContent = msg;
  $('loadingBar').parentElement.hidden = true;
}

async function boot() {
  if (!$('tagline').textContent.trim()) $('tagline').innerHTML = taglineHtml();
  const quality = chooseQuality();
  const lite = quality.lite;
  const qBtn = $('quality');
  qBtn.textContent = `Lite market: ${lite ? 'on' : 'off'}`;
  qBtn.setAttribute('aria-pressed', String(lite));
  qBtn.title = lite
    ? `Using the lite market${quality.source === 'detected' ? ` (${quality.detected.reasons.join(', ')})` : ''}. Press for the full market.`
    : 'Press for the lite market: fewer lights, no shadows, lighter models.';
  qBtn.addEventListener('click', () => switchQuality(!lite));
  document.documentElement.dataset.quality = lite ? 'lite' : 'full';

  if (!quality.info.webgl) {
    fail('This browser cannot show 3D graphics (WebGL is off). The text version has everything.');
    return;
  }

  const motion = watchMotion();
  const stage = $('stage'), overlay = $('overlay');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  } catch (e) {
    fail('This browser cannot show 3D graphics (WebGL is off). The text version has everything.');
    return;
  }
  const PR = Math.min(window.devicePixelRatio || 1, lite ? 1.25 : 1.75);
  renderer.setPixelRatio(PR);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setSize(stage.clientWidth, stage.clientHeight, false);
  stage.insertBefore(renderer.domElement, overlay);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, stage.clientWidth / stage.clientHeight, 0.1, 600);

  // ---------- the market ----------
  const bar = $('loadingBar');
  const market = await buildMarket({
    scene, lite, warn,
    onProgress: (f, e) => { bar.style.width = `${Math.round(f * 85)}%`; $('loadingText').textContent = `Setting up the market… ${e.label || e.id}`; },
  });
  const home = market.layout.home;
  const focus = new THREE.Vector3().fromArray(home.target);
  const { lighting, source: lightingSource } = await setupLighting({ scene, renderer, camera, lite }, warn);
  // light_ empties become lights: the lighting designer's placement when the module offers one, else the engine's
  const reserved = lite ? 0 : 2; // the bandstand's two spotlights (the lite market fakes its spot)
  let lightInfo = null;
  if (lightingSource === 'lighting' && typeof lighting.raw?.placeLights === 'function') {
    try { lightInfo = lighting.raw.placeLights(market.lightSpots, { focus, reserved }); } catch (e) { warn(`lighting.placeLights failed (${e?.message || e}); the engine places the lights.`); }
  }
  if (!lightInfo?.lights) lightInfo = placeLights(scene, market.lightSpots, { lite, focus, reserved });
  const composer = lighting.composer;
  let outline = null;
  if (typeof composer.insertPass === 'function' && composer.passes?.[0]?.scene) {
    const size = renderer.getSize(new THREE.Vector2());
    outline = new OutlinePass(size, scene, camera);
    outline.edgeStrength = 3.2; outline.edgeGlow = 0.6; outline.edgeThickness = 1.4;
    outline.visibleEdgeColor.set(0xffc76a); outline.hiddenEdgeColor.set(0x3a2a10);
    composer.insertPass(outline, 1);
  }
  bar.style.width = '92%';

  // the lighting module brings its own falling snow; the engine's flakes are only for the stand-in lighting
  const ownSnow = lightingSource === 'lighting' && lighting.raw && 'snowAmount' in lighting.raw;
  const snowfall = ownSnow ? { set() {}, update() {} } : createSnowfall(scene, { lite });
  const avoid = (x, z) => {
    for (const p of Object.values(market.places)) if (Math.hypot(x - p.holder.position.x, z - p.holder.position.z) < (p.radius || 3) + 1) return false;
    for (const pl of market.placed) if ((pl.entry.kind === 'deco' || pl.entry.kind === 'tree') && Math.hypot(x - pl.entry.position[0], z - pl.entry.position[2]) < 3.4) return false;
    return true;
  };
  const crowd = await createCrowd({ scene, overlay, lite, manager: undefined, warn, avoid, phrases: phrases() });
  if (!lite) crowd.group.traverse((o) => { if (o.isMesh) o.castShadow = true; });

  // ---------- sound ----------
  const positions = bandPositions(market);
  const audio = createAudio({ manifest: inventory.audio, positions, getCamera: () => camera, lite, warn });

  // ---------- camera, panel, actions ----------
  const rig = createCameraRig({ camera, dom: renderer.domElement, home, motion });
  let panel;
  const actions = createActions({
    market, scene, lite, motion, audio, rig,
    books: bookPicks(),
    sfx: (n) => audio.sfx(n),
    say: (html) => panel.say(html),
    crowdSay: (text, center, radius) => crowd.say(text, center, radius),
    togglePlay: () => togglePlay(),
  });

  const playBtn = $('play'), np = $('nowplaying');
  const playLabel = () => (audio.playing ? '❚❚ Pause the ballad' : '▶ Play the ballad');
  function syncPlay(label) {
    const txt = label || playLabel();
    playBtn.textContent = txt;
    playBtn.setAttribute('aria-pressed', String(audio.playing));
    panel.syncPlay(txt);
    np.hidden = !audio.playing;
    const title = inventory.audio?.title;
    np.textContent = audio.mode === 'stems'
      ? `Now playing: ${title || 'a ballad'} · the Nachtmarkt Quartett`
      : 'Now playing: a ballad in D minor · tenor sax, piano, bass, brushes';
  }
  async function togglePlay() {
    if (audio.playing) { audio.stop(); syncPlay(); return; }
    playBtn.disabled = true;
    syncPlay('Tuning up…');
    try { await audio.start(); } catch (e) { console.warn('[market] sound could not start', e); playBtn.disabled = false; syncPlay('Sound could not start'); return; }
    playBtn.disabled = false;
    syncPlay();
  }
  playBtn.addEventListener('click', togglePlay);

  function goTo(id) {
    const place = market.places[id];
    if (!place) return;
    if (actions.rides.riding) actions.rides.endRide(true);
    rig.flyTo(viewFor(place));
  }
  panel = createPanel({
    actionsFor: (id) => actions.get(id),
    playButtonLabel: playLabel,
    onOpen: () => requestAnimationFrame(() => panelShift()),
    onClose: () => panelShift(),
  });
  // Opening a place from the buttons under the market: bring the market back into view first.
  const showStage = () => {
    const top = stage.getBoundingClientRect().top;
    if (top < 0) window.scrollBy({ top: top - 8, behavior: motion.reduced ? 'auto' : 'smooth' });
  };
  const openPlace = (id) => { showStage(); goTo(id); panel.open(id); };
  let picking = null;
  buildPlaceNav(openPlace, (id) => picking?.highlight(id));

  picking = createPicking({
    dom: renderer.domElement, camera, market, overlay, outline,
    labelFor: (id) => `${SECTIONS[id]?.name} · ${SECTIONS[id]?.sub}`,
    onPick: (id) => { if (actions.rides.riding?.place?.id === id) return; openPlace(id); },
    onBook: (node) => { if (panel.current !== 'books') openPlace('books'); actions.pullBook(node); },
  });

  // ---------- snow, reset, keyboard ----------
  const snowBtn = $('snow');
  let snowOn = false;
  function setSnow(on) {
    snowOn = on;
    snowfall.set(on);
    market.snow.forEach((o) => (o.visible = on));
    try { lighting.setSnow(on); } catch (e) { warn(`lighting.setSnow failed: ${e?.message || e}`); }
    snowBtn.textContent = `❄ Snow: ${on ? 'on' : 'off'}`;
    snowBtn.setAttribute('aria-pressed', String(on));
  }
  snowBtn.addEventListener('click', () => setSnow(!snowOn));
  const q = new URLSearchParams(location.search).get('snow');
  setSnow(q === '1' ? true : q === '0' ? false : inSeason());

  function resetView() {
    actions.rides.endRide(true);
    panel.close();
    rig.flyTo(null);
  }
  $('reset').addEventListener('click', resetView);
  bindKeyboard({
    canvas: renderer.domElement, order: ORDER, openPlace, rig, resetView,
    closePanel: () => panel.close(),
    endRide: () => actions.rides.endRide(false),
    isRiding: () => !!actions.rides.riding,
  });
  motion.listeners.push((r) => rig.setReduced(r));

  // ---------- keep the chosen place clear of the panel ----------
  // The panel covers the right of the market on wide screens and the bottom on phones, so the view is
  // shifted (an off-centre projection) to keep the stall in the part that is still visible.
  const panelEl = $('panel');
  const shift = { x: 0, y: 0, tx: 0, ty: 0 };
  function panelShift() {
    shift.tx = shift.ty = 0;
    if (panelEl.hidden) return;
    const s = stage.getBoundingClientRect(), p = panelEl.getBoundingClientRect();
    const overlapX = Math.max(0, Math.min(s.right, p.right) - Math.max(s.left, p.left));
    const overlapY = Math.max(0, Math.min(s.bottom, p.bottom) - Math.max(s.top, p.top));
    if (!overlapX || !overlapY) return;
    if (p.width < s.width * 0.8) shift.tx = (p.left > s.left + s.width / 2 ? 1 : -1) * Math.min(overlapX, s.width * 0.45) / 2;
    else shift.ty = Math.min(overlapY, s.height * 0.6) / 2;
  }
  function applyShift(dt) {
    const k = motion.reduced ? 1 : 1 - Math.exp(-dt * 4);
    shift.x += (shift.tx - shift.x) * k;
    shift.y += (shift.ty - shift.y) * k;
    const w = stage.clientWidth, h = stage.clientHeight;
    if (Math.abs(shift.x) < 0.5 && Math.abs(shift.y) < 0.5 && !shift.tx && !shift.ty) {
      if (camera.view?.enabled) { camera.clearViewOffset(); }
      return;
    }
    camera.setViewOffset(w, h, shift.x, shift.y, w, h);
  }

  // ---------- size ----------
  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    composer.setPixelRatio?.(PR);
    composer.setSize(w, h);
    camera.aspect = w / h;
    // the architect's framing on wide screens; narrow screens need a wider lens to keep the stalls in view
    const baseFov = home.fov || 42;
    camera.fov = w < 600 ? baseFov + 13 : baseFov;
    camera.updateProjectionMatrix();
    panelShift();
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  // ---------- loop ----------
  const timer = new THREE.Timer();
  timer.connect?.(document);
  let T = 0, frames = 0, slowFrames = 0;
  const w0 = { w: stage.clientWidth, h: stage.clientHeight };
  let frozen = false;
  /** Advance everything that moves by dt seconds (no rendering). */
  function step(dt) {
    const riding = !!actions.rides.riding;
    const still = motion.reduced && !riding;
    if (!still) T += dt;
    audio.update(dt);
    rig.update(dt);
    applyShift(dt);
    const L = audio.levels;
    for (const r of market.rides) r.update(still ? 0 : dt, T, 1, !still);
    for (const m of market.mixers) if (!still) m.update(dt);
    const pulse = (L.bass || 0) * 0.35 + (L.drums || 0) * 0.1;
    market.bulbMaterials.forEach((m, i) => { m.emissiveIntensity = m.userData.baseEmissive * (0.9 + (still ? 0 : 0.07 * Math.sin(T * 1.3 + i * 1.7)) + pulse); });
    actions.update(dt, T, still);
    snowfall.update(dt, T, still);
    w0.w = stage.clientWidth; w0.h = stage.clientHeight;
    crowd.update(dt, T, camera, w0.w, w0.h, { still, look: rig.controls.target });
    try { lighting.update(dt, T); } catch { /* the lighting module's own business */ }
  }
  function frame() {
    if (frozen) { requestAnimationFrame(frame); return; }
    timer.update();
    const dt = Math.min(timer.getDelta(), 0.1);
    step(dt);
    composer.render(dt);
    frames++;
    if (!lite && frames > 30 && frames < 330 && dt > 0.045) slowFrames++;
    if (frames === 330 && slowFrames > 200) suggestLite();
    requestAnimationFrame(frame);
  }
  function suggestLite() {
    const b = document.createElement('button');
    b.className = 'btn badge';
    b.type = 'button';
    b.textContent = 'Running slowly? Switch to the lite market';
    b.addEventListener('click', () => switchQuality(true));
    stage.appendChild(b);
  }

  // first frame, then reveal
  frame();
  bar.style.width = '100%';
  $('loading').classList.add('done');
  $('loading').setAttribute('aria-hidden', 'true');
  document.fonts?.load("700 64px 'Alegreya SC'").then(redrawSigns).catch(() => {});
  setTimeout(() => audio.prefetch(), 4000);

  const report = {
    quality: { lite, source: quality.source, reasons: quality.detected.reasons, gpu: quality.info.renderer },
    layout: market.layout.fromFile ? 'layout.json' : 'BUILD.md fallback',
    lighting: lightingSource,
    audio: inventory.audio ? 'stems' : 'generative fallback',
    content: Object.fromEntries(Object.entries(SECTIONS).map(([k, s]) => [k, s.fromWriter ? s.source : 'fallback'])),
    models: market.report,
    lights: { realtime: lightInfo.lights.length, pools: lightInfo.pools.length, cap: lightInfo.cap },
    props: market.propCount,
    crowd: crowd.count,
    scene: sceneStats(scene),
    warnings,
  };
  if (debug) console.info('[market] report', report);
  // a small handle for tests and for the curious
  window.__market = {
    ready: true, report, openPlace, resetView, setSnow, togglePlay,
    act(id, key) { const a = actions.get(id)?.acts.find((x) => x.key === key); if (!a) throw new Error(`no action ${key} at ${id}`); a.fn(); },
    get riding() { return actions.rides.riding?.type || null; },
    get panel() { return panel.current; },
    get snow() { return snowOn; },
    /** Hold the last rendered frame (tests take screenshots of it; software GL can take seconds per frame). */
    freeze(on = true) { frozen = !!on; if (!frozen) timer.reset?.(); },
    /** Run the market's clock forward without drawing (tests: see the wheel turn on a 1 fps software renderer). */
    advance(seconds) { for (let t = 0; t < seconds; t += 0.05) step(0.05); },
    get audio() { return { playing: audio.playing, mode: audio.mode, phase: audio.phase, levels: { ...audio.levels } }; },
    camera, scene, renderer,
  };
  document.documentElement.dataset.ready = 'true';
}

/** Triangles and meshes in the scene as built (instanced meshes count every copy). */
function sceneStats(scene) {
  let triangles = 0, meshes = 0;
  scene.traverse((o) => {
    if (!o.isMesh || !o.visible || !o.geometry) return;
    const g = o.geometry;
    const n = g.index ? g.index.count : g.attributes.position?.count || 0;
    triangles += (n / 3) * (o.isInstancedMesh ? o.count : 1);
    meshes++;
  });
  return { triangles: Math.round(triangles), meshes };
}

boot().catch((err) => {
  console.error('[market] could not start', err);
  fail('The market could not open in this browser. The text version has everything.');
});
