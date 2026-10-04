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
import { createReader, libraryBook } from './ui/reading.js';
import { SECTIONS, ORDER, bookPicks, phrases, taglineHtml } from './content.js';
import { createPerfMeter } from './perf.js';
import { mergeStatic, mergeAcross, mergeSnow, instancePools, instanceRiders } from './engine/merge.js';
import { createGovernor } from './governor.js';
import { counterLocal } from './actions/util.js';
import { showPlainFallback } from './ui/fallback.js';
import { setupMute } from './ui/mute.js';

const $ = (id) => document.getElementById(id);
const warnings = [];
const warn = (msg) => { warnings.push(msg); console.warn('[market]', msg); };
const params = new URLSearchParams(location.search);
const debug = params.has('debug');

function inSeason() {
  const d = new Date(), m = d.getMonth(), day = d.getDate();
  return (m === 10 && day >= 20) || m === 11 || (m === 0 && day <= 6);
}

function fail(msg, { plain = true } = {}) {
  $('loadingText').textContent = msg;
  $('loadingBar').parentElement.hidden = true;
  // no 3D here: the text of every section is shown in place of the market (the same content as plain.html)
  if (plain) showPlainFallback(msg);
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

  if (!quality.info.webgl || params.has('nowebgl')) {
    fail('This browser cannot show 3D graphics (WebGL is off), so here is the market as text.');
    return;
  }

  const motion = watchMotion();
  const stage = $('stage'), overlay = $('overlay');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  } catch (e) {
    fail('This browser cannot show 3D graphics (WebGL is off), so here is the market as text.');
    return;
  }
  // pixel ratio capped at 1.5 on the full market (a 4K laptop screen at 2x is four times the fragments)
  const PR = Math.min(window.devicePixelRatio || 1, lite ? 1.25 : 1.5);
  renderer.setPixelRatio(PR);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setSize(stage.clientWidth, stage.clientHeight, false);
  // an accessible name from the start (bindKeyboard adds the keys once the market is up)
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', "Mac's Nachtmarkt: a 3D Christmas market at night. The places are also listed as buttons below the market.");
  stage.insertBefore(renderer.domElement, overlay);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, stage.clientWidth / stage.clientHeight, 0.1, 600);

  // ---------- the market ----------
  const bar = $('loadingBar');
  // Both markets open without the rides and the nine deco stalls (about 8 MB of full models, 3.4 MB lite) and
  // add them just after the first frame. ?defer=0 loads everything up front.
  const deferOn = params.get('defer') !== '0';
  const market = await buildMarket({
    scene, lite, warn,
    defer: deferOn ? (e) => e.kind === 'deco' || e.place === 'ferris' || e.place === 'carousel' : undefined,
    onProgress: (f, e) => { bar.style.width = `${Math.round(f * 85)}%`; $('loadingText').textContent = `Setting up the market… ${e.label || e.id}`; },
  });
  const home = market.layout.home;
  const focus = new THREE.Vector3().fromArray(home.target);
  const { lighting, source: lightingSource } = await setupLighting({ scene, renderer, camera, lite }, warn);
  // light_ empties become lights: the lighting designer's placement when the module offers one, else the engine's
  const reserved = lite ? 0 : 2; // the bandstand's two spotlights (the lite market fakes its spot)
  // On the full market the two rides take a real light each once they arrive: keep those two back now.
  const heldForLater = !lite && market.deferred.some((id) => /riesenrad|karussell|ferris|carousel/.test(id)) ? DEFERRED_LIGHTS : 0;
  const fullBudget = Number(lighting.raw?.profile?.lightBudget) || 14;
  const lightInfo = placeMarketLights({ scene, lighting, lightingSource, spots: market.lightSpots, lite, focus, reserved, warn, budget: lite ? undefined : fullBudget - heldForLater });
  // the ground pools of unlit light_ empties: one instanced draw instead of one each
  instancePools(lightInfo.pools, scene);
  // the lite market's close-up key: one warm spot that follows the open section stall (see keyLight below)
  const key = lite ? createKeyLight(scene) : null;
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
  // (The snow fog and flake caps the engine used to apply now live in the lighting module's settings.js.)
  const snowfall = ownSnow ? { set() {}, update() {} } : createSnowfall(scene, { lite });
  // keep walkers off the stalls (from the layout, so the deco stalls count before their models arrive)
  const avoid = (x, z) => {
    for (const p of Object.values(market.places)) if (Math.hypot(x - p.holder.position.x, z - p.holder.position.z) < (p.radius || 3) + 1) return false;
    for (const e of market.layout.entries) if ((e.kind === 'deco' || e.kind === 'tree' || (e.place && !market.places[e.place])) && Math.hypot(x - e.position[0], z - e.position[2]) < (e.place ? 6 : 3.4)) return false;
    return true;
  };
  const crowd = await createCrowd({ scene, overlay, lite, manager: undefined, warn, avoid, phrases: phrases(), lodFar: quality.lodFar });
  if (!lite) crowd.group.traverse((o) => { if (o.isMesh) o.castShadow = true; });

  // ---------- sound ----------
  const positions = bandPositions(market);
  const audio = createAudio({ manifest: inventory.audio, positions, getCamera: () => camera, lite, warn });

  // ---------- camera, panel, actions ----------
  // Phones (a narrow, tall market): the architect's home view shows the stalls as a thin band over a lot of
  // dark ground. Come in closer and lower, so the four section stalls and the bandstand fill the upper part.
  const phoneHome = stage.clientWidth < 600 && stage.clientHeight > stage.clientWidth * 0.9;
  const rig = createCameraRig({ camera, dom: renderer.domElement, home: phoneHome ? PHONE_HOME : home, motion });
  let panel, openedFor = null;
  // the reading view: a book opened on the Bücherstand shows its page from content/books/<slug>.md
  // while a book is open the page carries .reading; at 960 px and below the reading view is a sheet along the bottom
  // and the panel steps aside (main.css), so the open book has the picture above the sheet to itself
  const reader = createReader({ onToggle: (on) => { document.documentElement.classList.toggle('reading', on); requestAnimationFrame(() => panelShift()); } });
  const actions = createActions({
    reader,
    market, scene, lite, motion, audio, rig, camera, overlay,
    books: bookPicks(),
    sfx: (n) => audio.sfx(n),
    say: (html) => panel.say(html),
    crowdSay: (text, center, radius) => crowd.say(text, center, radius),
    togglePlay: () => togglePlay(),
    frame: (o) => frameRegion(o),
    keyAt: (center, facing) => key?.aim(center, facing),
    flyBack: (v) => { if (!rig.riding && v) rig.flyTo(v); },
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
    if (!place) {
      // a ride the lite market is still loading: fly there once it arrives, if its panel is still open
      market.whenPlace?.(id).then((p) => { if (p && panel.current === id) rig.flyTo(viewFor(p)); });
      return;
    }
    if (actions.rides.riding) actions.rides.endRide(true);
    rig.flyTo(viewFor(place));
  }
  panel = createPanel({
    actionsFor: (id) => actions.get(id),
    itemsFor: (id) => goodsList(id),
    playButtonLabel: playLabel,
    onOpen: (id) => {
      // an open book, a bottle being shown or a raised glass goes back when another place opens
      if (id !== openedFor) actions.retract();
      openedFor = id;
      decoCaption(null);
      key?.follow(market.places[id]);
      requestAnimationFrame(() => panelShift());
    },
    onClose: () => { actions.retract(); openedFor = null; key?.follow(null); panelShift(); },
  });
  // a title in the bookshelf list opens that book on its shelf, with its page in the reading view
  $('pBody').addEventListener('click', (e) => {
    const a = e.target.closest?.('a[data-book]');
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    if (actions.items.handlers.openBySlug?.(a.dataset.book)) e.preventDefault();
  });
  // Opening a place from the buttons under the market: bring the market back into view first.
  // On a phone the panel is a bottom sheet: bring the market to the top of the screen, so the part above the
  // sheet shows the place.
  const narrow = window.matchMedia('(max-width: 640px)');
  const showStage = () => {
    const top = stage.getBoundingClientRect().top;
    if (top < 0 || (narrow.matches && top > 8)) window.scrollBy({ top: top - 8, behavior: motion.reduced ? 'auto' : 'smooth' });
  };
  const openPlace = (id) => { showStage(); goTo(id); panel.open(id); };
  let picking = null;
  buildPlaceNav(openPlace, (id) => picking?.highlight(id));

  picking = createPicking({
    dom: renderer.domElement, camera, market, overlay, outline, items: actions.items,
    current: () => panel.current,
    labelFor: (id) => `${SECTIONS[id]?.name} · ${SECTIONS[id]?.sub}`,
    onPick: (id) => { if (actions.rides.riding?.place?.id === id) return; openPlace(id); },
    // an item on a counter or shelf: its own action, opening its stall first if the panel is elsewhere
    onItem: (item) => {
      if (item.placeId && market.places[item.placeId] && panel.current !== item.placeId) openPlace(item.placeId);
      actions.items.click(item);
      focusItem(item);
    },
    // a deco stall: fly to its close-up (it opens no panel)
    onDeco: (id) => openDeco(id),
  });
  // the deco stall's name under its close-up, and a hint that its goods can be looked at
  const caption = document.createElement('p');
  caption.className = 'decocap';
  caption.hidden = true;
  stage.appendChild(caption);
  function decoCaption(d) {
    caption.hidden = !d;
    if (d) caption.textContent = `${d.entry.label || d.id}. Point at the goods to look closer; Reset view to go back.`;
  }
  /** Come in close to where a clicked item's little scene plays out (the glass under the tap, the ladle over
   *  the mug, the sausage on the grill), keeping the direction the visitor looks from. */
  const ITEM_NEAR = 1.7;
  function focusItem(item) {
    const at = actions.items.focusOf(item);
    if (!at || rig.riding) return;
    const dir = camera.position.clone().sub(at);
    const dist = dir.length();
    if (dist < ITEM_NEAR * 1.15) return; // already close: no flight for a neighbour
    dir.y = Math.max(dir.y, dist * 0.25);
    const pos = at.clone().addScaledVector(dir.normalize(), ITEM_NEAR);
    const target = at.clone();
    // a phone's panel is a sheet over the lower half: the item sits in the upper part of the picture
    if (camera.aspect < 1) { target.y -= ITEM_NEAR * 0.2; pos.y -= ITEM_NEAR * 0.2; }
    rig.flyTo({ pos, target, near: 1 });
  }

  /** Frame a box (its centre, the way its face looks, half its width and height in metres) in the part of the
   *  market the panel or the reading view leaves free, square to its face and a little above it. Returns the
   *  view it left, so the caller can go back to it. */
  function frameRegion({ center, facing, halfW, halfH, depth = 0, lift = 0.25, margin = 1.25, near = 0.5 }) {
    if (rig.riding || !center || !facing) return null;
    const { fx, fy } = freeFraction();
    const t = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    const d = Math.max((halfH * margin) / (t * fy), (halfW * margin) / (t * camera.aspect * fx), near + 0.15) + depth / 2;
    const dir = facing.clone().setY(0).normalize();
    dir.y = lift;
    dir.normalize();
    const back = { pos: camera.position.clone(), target: rig.controls.target.clone(), near: rig.controls.minDistance };
    rig.flyTo({ pos: center.clone().addScaledVector(dir, d), target: center.clone(), near });
    return back;
  }

  function openDeco(id) {
    const d = market.decos[id];
    if (!d) return;
    if (actions.rides.riding) actions.rides.endRide(true);
    panel.close();
    rig.flyTo(viewFor(d));
    decoCaption(d);
  }

  // ---------- fewer draw calls ----------
  // Now that the lights are placed and the actions hold their nodes, the static meshes of every model are merged
  // (engine/merge.js): one mesh per material per rigid body, and the deco stalls' shared kit as one row.
  const merges = { before: 0, after: 0, row: 0 };
  const decoRow = new THREE.Group();
  decoRow.name = 'deco_row_merged';
  scene.add(decoRow);
  const snowRow = new THREE.Group();
  snowRow.name = 'snow_row_merged';
  scene.add(snowRow);
  const riderSyncs = [];
  function compact(placed) {
    for (const p of placed) {
      try { const r = mergeStatic(p.root); merges.before += r.before; merges.after += r.after; } catch (e) { warn(`merge ${p.entry.id}: ${e?.message || e}`); }
      // the gondolas and horses: one instanced draw per part for all of them
      for (const list of [p.nodes?.gondolas, p.nodes?.horses]) {
        if (!list?.length) continue;
        try {
          const r = instanceRiders(list, p.root);
          if (r) { riderSyncs.push(r.sync); merges.after -= r.saved; merges.riders = (merges.riders || 0) + r.saved; }
        } catch (e) { warn(`instance riders ${p.entry.id}: ${e?.message || e}`); }
      }
    }
    const deco = placed.filter((p) => p.entry.kind === 'deco').map((p) => p.root);
    if (deco.length > 1) {
      try { const saved = mergeAcross(deco, decoRow); merges.row += saved; merges.after -= saved; } catch (e) { warn(`merge deco row: ${e?.message || e}`); }
    }
    // the snow caps of these models: one mesh per look for all of them (the toggle then shows a few draws)
    try {
      const s = mergeSnow(placed.map((p) => p.root), snowRow);
      if (s.added.length) {
        market.snow = market.snow.filter((o) => !s.removed.includes(o)).concat(s.added);
        merges.snow = (merges.snow || 0) + s.saved;
      }
    } catch (e) { warn(`merge snow caps: ${e?.message || e}`); }
  }
  if (params.get('merge') !== '0') compact(market.placed);

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
    actions.retract();
    decoCaption(null);
    key?.follow(null);
    rig.flyTo(null);
  }
  $('reset').addEventListener('click', resetView);
  const mute = setupMute($('mute'), audio);
  bindKeyboard({
    canvas: renderer.domElement, order: ORDER, openPlace, rig, resetView,
    closePanel: () => (reader.isOpen ? reader.close() : panel.close()),
    endRide: () => actions.rides.endRide(false),
    isRiding: () => !!actions.rides.riding,
  });
  motion.listeners.push((r) => rig.setReduced(r));

  // ---------- keep the chosen place clear of the panel ----------
  // The panel covers the right of the market on wide screens and the bottom on phones, so the view is
  // shifted (an off-centre projection) to keep the stall in the part that is still visible.
  const panelEl = $('panel');
  const shift = { x: 0, y: 0, tx: 0, ty: 0 };
  // The open overlay: the reading view while a book is open (on a narrow screen it is a sheet, not the side
  // panel), else the panel. The picture moves over so its centre is the centre of the part left free.
  const readerEl = $('reader');
  function overlayRects() {
    const el = readerEl && !readerEl.hidden ? readerEl : panelEl.hidden ? null : panelEl;
    if (!el) return null;
    const s = stage.getBoundingClientRect(), p = el.getBoundingClientRect();
    const overlapX = Math.max(0, Math.min(s.right, p.right) - Math.max(s.left, p.left));
    const overlapY = Math.max(0, Math.min(s.bottom, p.bottom) - Math.max(s.top, p.top));
    if (!overlapX || !overlapY) return null;
    const side = p.width < s.width * 0.8;
    return { s, p, side, ox: Math.min(overlapX, s.width * 0.45), oy: Math.min(overlapY, s.height * 0.6) };
  }
  function freeFraction() {
    const r = overlayRects();
    if (!r) return { fx: 1, fy: 1 };
    return r.side ? { fx: 1 - r.ox / r.s.width, fy: 1 } : { fx: 1, fy: 1 - r.oy / r.s.height };
  }
  function panelShift() {
    shift.tx = shift.ty = 0;
    const r = overlayRects();
    if (!r) return;
    if (r.side) shift.tx = (r.p.left > r.s.left + r.s.width / 2 ? 1 : -1) * r.ox / 2;
    else shift.ty = r.oy / 2;
  }
  // the sheet is fixed to the screen, so its overlap with the market changes as the page scrolls
  let shiftQueued = false;
  window.addEventListener('scroll', () => {
    if ((panelEl.hidden && readerEl?.hidden !== false) || shiftQueued) return;
    shiftQueued = true;
    requestAnimationFrame(() => { shiftQueued = false; panelShift(); });
  }, { passive: true });
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
  const baseExposure = renderer.toneMappingExposure || 1;
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
    for (const sync of riderSyncs) sync();
    for (const m of market.mixers) if (!still) m.update(dt);
    const pulse = (L.bass || 0) * 0.35 + (L.drums || 0) * 0.1;
    // bulbs burn a little brighter in falling snow, so the strings still read through it
    const snowLift = 1 + 0.3 * (lighting.raw?.snowAmount ?? (snowOn ? 1 : 0));
    market.bulbMaterials.forEach((m, i) => { m.emissiveIntensity = m.userData.baseEmissive * snowLift * (0.9 + (still ? 0 : 0.07 * Math.sin(T * 1.3 + i * 1.7)) + pulse); });
    actions.update(dt, T, still);
    key?.update(dt);
    // from a gondola the lit market is far below: open the exposure up while riding, and back on the ground
    const wantExp = baseExposure * actions.rides.exposure();
    renderer.toneMappingExposure += (wantExp - renderer.toneMappingExposure) * (motion.reduced ? 1 : 1 - Math.exp(-dt * 2));
    snowfall.update(dt, T, still);
    w0.w = stage.clientWidth; w0.h = stage.clientHeight;
    crowd.update(dt, T, camera, w0.w, w0.h, { still, look: rig.controls.target });
    try { lighting.update(dt, T); } catch { /* the lighting module's own business */ }
  }
  function frame() {
    if (frozen) { requestAnimationFrame(frame); return; }
    timer.update();
    const rawDt = timer.getDelta();
    const dt = Math.min(rawDt, 0.1);
    step(dt);
    composer.render(dt);
    perf?.frame(rawDt);
    governor?.frame(rawDt);
    frames++;
    if (!lite && !governor && frames > 30 && frames < 330 && dt > 0.045) slowFrames++;
    if (!governor && frames === 330 && slowFrames > 200) suggestLite();
    requestAnimationFrame(frame);
  }
  let suggested = false;
  function suggestLite() {
    if (suggested) return;
    suggested = true;
    const b = document.createElement('button');
    b.className = 'btn badge';
    b.type = 'button';
    b.textContent = 'Running slowly? Switch to the lite market';
    b.addEventListener('click', () => switchQuality(true));
    stage.appendChild(b);
  }

  // a frame-time meter for measuring on real hardware (?perf): median and 95th percentile, draw calls, triangles
  // The frame-time governor (full market): if this machine cannot hold ~30 fps once the lighting module has
  // made its own cuts, the crowd's distance LOD comes in (12 m, then 6 m, then everyone on the lite figure),
  // the crowd stops casting moon shadows, and last the lite market is offered. ?governor=0 turns it off.
  const governor = !lite && params.get('governor') !== '0' ? createGovernor({
    crowd, lightingStats: () => lighting.raw?.stats?.(), suggestLite,
    onStep: (s) => { report.governor = s; console.info('[market] governor', JSON.stringify(s)); },
  }) : null;
  const perf = params.has('perf') ? createPerfMeter({ stage, renderer, lite, governor: () => governor?.state || null, tour: { openPlace, resetView, advance: (s) => step(s) } }) : null;
  // ?perf=tour starts the tour by itself once the deferred models are in (tests/perf.mjs on Mac's own machine)
  if (perf && params.get('perf') === 'tour') setTimeout(() => perf.startTour(), 6000);

  // first frame, then reveal (the mark lets tests and ?perf count what was fetched before the market opened)
  performance.mark?.('market-ready');
  frame();
  bar.style.width = '100%';
  $('loading').classList.add('done');
  $('loading').setAttribute('aria-hidden', 'true');
  document.fonts?.load("700 64px 'Alegreya SC'").then(redrawSigns).catch(() => {});
  setTimeout(() => audio.prefetch(), 4000);

  // ---------- after the first frame ----------
  // Full market: people far from the camera switch to their lighter figure (distance LOD).
  const lodReady = lite ? Promise.resolve(0) : new Promise((res) => setTimeout(res, 300)).then(() => crowd.enableLod()).catch((e) => { warn(`crowd LOD: ${e?.message || e}`); return 0; });
  // Lite market: the rides and deco stalls arrive now. Their lights become warm pools (the four real lights
  // stay on the section stalls), the lighting module tunes their bulbs, and they join picking and snow.
  // Full market: the rides take the two real lights held back for them (a second placement pass).
  const deferredReady = !market.deferred.length ? Promise.resolve(null) : new Promise((res) => requestAnimationFrame(() => res())).then(() => market.loadDeferred()).then((added) => {
    const more = placeMarketLights({ scene, lighting, lightingSource, spots: added.spots, lite, focus, reserved: 0, warn, budget: heldForLater, second: true });
    lightInfo.pools.push(...more.pools);
    lightInfo.lights.push(...more.lights);
    instancePools(more.pools, scene);
    for (const p of added.placed) { try { lighting.raw?.tune?.(p.holder); } catch (e) { warn(`lighting.tune failed: ${e?.message || e}`); } }
    added.snow.forEach((o) => (o.visible = snowOn));
    actions.items.addPlaced(added.placed);
    if (params.get('merge') !== '0') compact(added.placed);
    picking.refresh();
    report.lights.realtime = lightInfo.lights.length;
    report.lights.places = lightInfo.lights.map(placeOfLight);
    report.merges = { ...merges };
    report.scene = sceneStats(scene);
    report.lights.pools = lightInfo.pools.length;
    report.props = market.propCount;
    document.documentElement.dataset.deferred = 'done';
    return added.placed.length;
  }).catch((e) => { warn(`deferred models: ${e?.message || e}`); return 0; });

  /** The panel's list of goods for a stall: each clickable item once, with a number when names repeat. */
  function goodsList(id) {
    const featured = new Set(actions.featuredBooks);
    const list = actions.items.of(id).filter((it) => it.clickable && !['tap', 'lid', 'kettle', 'pot', 'served'].includes(it.kind))
      // books: every one of Mac's books (items.json gives each its slug); stock without a title stays out
      .filter((it) => it.kind !== 'book' || featured.has(it.node) || !!it.info.slug || /counter/i.test(it.info.where || ''));
    const seen = {};
    const total = {};
    for (const it of list) total[it.label] = (total[it.label] || 0) + 1;
    return list.map((it) => {
      seen[it.label] = (seen[it.label] || 0) + 1;
      const label = total[it.label] > 1 ? `${it.label} (${seen[it.label]})` : it.label;
      return { name: it.node.name, label: label.replace(/, (full and steaming|upside down to dry)$/, (m) => m), fn: () => actions.items.click(it) };
    });
  }
  function itemCounts() {
    const out = {};
    for (const it of actions.items.all()) { const k = `${it.placeId}:${it.kind}`; out[k] = (out[k] || 0) + 1; }
    return out;
  }
  const report = {
    quality: { lite, source: quality.source, reasons: quality.detected.reasons, gpu: quality.info.renderer },
    layout: market.layout.fromFile ? 'layout.json' : 'BUILD.md fallback',
    lighting: lightingSource,
    audio: inventory.audio ? 'stems' : 'generative fallback',
    content: Object.fromEntries(Object.entries(SECTIONS).map(([k, s]) => [k, s.fromWriter ? s.source : 'fallback'])),
    models: market.report,
    lights: { realtime: lightInfo.lights.length, pools: lightInfo.pools.length, cap: lightInfo.cap, places: lightInfo.lights.map(placeOfLight) },
    books: { merged: market.merges.books || null, featured: actions.featuredBooks.map((n) => n.name) },
    items: itemCounts(),
    bindings: market.bindings,
    contract: market.contract,
    merges: { ...merges },
    lod: crowd.lod,
    deferred: market.deferred,
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
    /** The snow caps (tests): how many snow_ entries the toggle drives, merged meshes among them, how many show. */
    snowCaps: () => ({ entries: market.snow.length, merged: market.snow.filter((o) => o.userData.snow).length, visible: market.snow.filter((o) => o.visible).length, saved: merges.snow || 0 }),
    /** Hold the last rendered frame (tests take screenshots of it; software GL can take seconds per frame). */
    freeze(on = true) { frozen = !!on; if (!frozen) timer.reset?.(); },
    /** Run the market's clock forward without drawing (tests: see the wheel turn on a 1 fps software renderer). */
    advance(seconds) { for (let t = 0; t < seconds; t += 0.05) step(0.05); },
    get audio() { return { playing: audio.playing, mode: audio.mode, phase: audio.phase, levels: { ...audio.levels }, where: audio.where(), endings: audio.endings, alternatesReady: audio.alternatesReady }; },
    seekSong: (pos, pass) => audio.seek(pos, pass),
    get rideStage() { return actions.rides.stage; },
    get exposure() { return renderer.toneMappingExposure; },
    governor: () => governor?.state || null,
    keyLight: () => key?.state() || null,
    crowd: () => crowd.stats(),
    hiddenPeople: () => crowd.hiddenIds(),
    people: () => crowd.people(),
    sceneStats: () => sceneStats(scene),
    /** Resolves when the after-first-frame work is done (LOD figures, deferred models). */
    settled: () => Promise.all([lodReady, deferredReady]).then(([lod, deferred]) => ({ lod, deferred })),
    featuredBooks: () => actions.featuredBooks.map((n) => n.name),
    /** The reading view (tests): open, which book, and whether its page has loaded. */
    reading: () => { const r = document.getElementById('reader'); return { open: reader.isOpen, slug: reader.slug, state: r?.dataset.state || null, title: document.getElementById('rTitle')?.textContent || '', text: (document.getElementById('rBody')?.textContent || '').slice(0, 400) }; },
    closeReader: () => reader.close(),
    /** The books "Pick a book for me" offers first, as [title, author] (tests compare a clicked spine with them). */
    bookPicks: () => bookPicks().map((b) => [b[0], b[1]]),
    /** The items (tests): click one by node name as a visitor would, read an item's state. */
    items: () => itemCounts(),
    clickItem(name, { focus = false } = {}) { const it = actions.items.all().find((i) => i.node.name === name); if (!it) throw new Error(`no item ${name}`); picking.setEnabled(true); if (it.placeId && market.places[it.placeId] && panel.current !== it.placeId) openPlace(it.placeId); const r = actions.items.click(it); if (focus) focusItem(it); return r; },
    item: (name) => { const it = actions.items.all().find((i) => i.node.name === name); if (!it) return null; const n = it.node; return { name: n.name, kind: it.kind, label: it.label, busy: it.busy, position: n.getWorldPosition(new THREE.Vector3()).toArray().map((v) => +v.toFixed(4)), quaternion: n.getWorldQuaternion(new THREE.Quaternion()).toArray().map((v) => +v.toFixed(4)), visible: n.visible }; },
    /** Fly in close to an item as its click would (tests take the close-up before clicking). */
    focusOn(name) { const it = actions.items.all().find((i) => i.node.name === name); if (it) focusItem(it); },
    handlers: actions.items.handlers,
    /** A book's category key on Mac's shelf (content/books/categories.json). */
    bookCategory: (slug) => libraryBook({ slug })?.category || null,
    openedBook: () => actions.items.handlers.openedBook?.() || null,
    itemAt: (x, y) => picking.itemAt(x, y),
    pickAt: (x, y) => picking.at(x, y),
    hoverAt(x, y) { renderer.domElement.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, pointerType: 'mouse', bubbles: true })); },
    get hoveredItem() { return actions.items.hovered?.node.name || null; },
    /** Draw exactly one frame now (tests: a pose set with advance() while frozen). */
    renderFrame() { composer.render(0.016); },
    muted: () => audio.muted,
    openDeco,
    /** Client point over the middle of a scene object (tests aim clicks with it). */
    screenPoint(name) {
      const o = scene.getObjectByName(name);
      if (!o) return null;
      const box = new THREE.Box3();
      o.traverse((m) => { if (m.isMesh) { m.geometry.computeBoundingBox(); box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld)); } });
      const p = (box.isEmpty() ? o.getWorldPosition(new THREE.Vector3()) : box.getCenter(new THREE.Vector3())).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height };
    },
    /** People (visible ones) on the line from the camera to the middle of a scene object: tests check the view is clear. */
    blockers(name) {
      const o = scene.getObjectByName(name);
      const people = scene.getObjectByName('crowd');
      if (!o || !people) return [];
      const box = new THREE.Box3();
      o.traverse((m) => { if (m.isMesh) { m.geometry.computeBoundingBox(); box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld)); } });
      const to = box.isEmpty() ? o.getWorldPosition(new THREE.Vector3()) : box.getCenter(new THREE.Vector3());
      const from = camera.getWorldPosition(new THREE.Vector3());
      const dist = from.distanceTo(to);
      const ray = new THREE.Raycaster(from, to.clone().sub(from).normalize(), 0, dist - 0.02);
      const shown = (x) => { for (; x; x = x.parent) if (!x.visible) return false; return true; };
      const who = new Set();
      for (const h of ray.intersectObject(people, true)) {
        if (!shown(h.object)) continue;
        let g = h.object;
        while (g.parent && g.parent !== people) g = g.parent;
        who.add(g.name);
      }
      return [...who];
    },
    perf: () => perf?.stats() || null,
    perfTour: () => perf?.tourData || null,
    camera, scene, renderer,
  };
  document.documentElement.dataset.ready = 'true';
}

// the home view on a phone (see phoneHome in boot)
// Between the front row's string-light poles at [0, 7.5] and [7.5, 6.5] (blender/lib/architect_plan.py POLES_THREE),
// close enough that both stand outside a portrait frame (more than 20 degrees off the axis): no pole runs down the
// picture. The bandstand sits left of centre, the Bierstand and the tree to the right.
const PHONE_HOME = { position: [3.75, 5.6, 16], target: [3.4, 2.4, -4] };
// the full market holds back one real light for each ride until the ride's model arrives
const DEFERRED_LIGHTS = 2;

/**
 * The lite market's close-up key light. Its four real lights sit inside the section stalls, so in a close-up
 * the counter front and the vendor's face were in the dark. One warm spot, always in the scene (so no shader
 * recompiles when it moves), fades in under the front eave of the open section stall, aimed at the counter,
 * and fades out at home.
 */
function createKeyLight(scene) {
  const L = new THREE.SpotLight(0xffc98f, 0, 7.5, 0.72, 0.55, 1.6);
  L.name = 'engine_key_light';
  L.castShadow = false;
  scene.add(L, L.target);
  let want = 0, placeId = null;
  const INTENSITY = 22;
  return {
    follow(place) {
      if (!place || !['glueh', 'bier', 'wurst', 'books'].includes(place.id)) { want = 0; placeId = null; return; }
      placeId = place.id;
      const c = counterLocal(place); // the counter top, in the stall's frame
      // under the front eave, a little in front of the counter and above head height, aimed at the counter
      // front and the vendor behind it
      const from = new THREE.Vector3(c.x, 2.35, c.z + 1.25);
      const to = new THREE.Vector3(c.x, 1.05, c.z - 0.1);
      place.holder.localToWorld(from);
      place.holder.localToWorld(to);
      L.position.copy(from);
      L.target.position.copy(to);
      L.target.updateMatrixWorld();
      want = INTENSITY;
    },
    /** Light one part of the open stall (a bookshop shelf the camera looks along): from in front and above. */
    aim(center, facing) {
      if (!placeId || !center || !facing) return;
      L.position.copy(center).addScaledVector(facing.clone().setY(0).normalize(), 1.3).add(new THREE.Vector3(0, 1.1, 0));
      L.target.position.copy(center);
      L.target.updateMatrixWorld();
      want = INTENSITY;
    },
    update(dt) { L.intensity += (want - L.intensity) * Math.min(1, dt * 3); },
    state: () => ({ place: placeId, intensity: +L.intensity.toFixed(2), position: L.position.toArray().map((v) => +v.toFixed(2)) }),
  };
}

/**
 * light_ empties become lights: the lighting designer's placement when the module offers one, else the engine's.
 * On the lite market the section stalls are placed first and alone, so its four lights go one to each of
 * the four stalls whose panels look into them; every other light_ becomes a warm pool on the ground.
 */
function placeMarketLights({ scene, lighting, lightingSource, spots, lite, focus, reserved, warn, budget, second = false }) {
  const theirs = lightingSource === 'lighting' && typeof lighting.raw?.placeLights === 'function';
  const place = (list, opts) => {
    if (theirs) {
      try { const r = lighting.raw.placeLights(list, { focus, reserved, ...opts }); if (r?.lights) return r; } catch (e) { warn(`lighting.placeLights failed (${e?.message || e}); the engine places the lights.`); }
    }
    return placeLights(scene, list, { lite, focus, reserved, budget: opts.budget });
  };
  // a later pass (the deferred models): only the lights held back for it, and no more static shadows
  if (second || budget === 0) return place(spots, { budget: budget || 0, reserved: 0, shadowed: 0 });
  if (!lite) return place(spots, budget != null ? { budget } : {});
  const first = place(spots.filter((s) => s.kind === 'section'), {});
  const rest = place(spots.filter((s) => s.kind !== 'section'), { budget: Math.max(0, first.cap - first.lights.length) + reserved });
  return { lights: [...first.lights, ...rest.lights], pools: [...first.pools, ...rest.pools], cap: first.cap };
}

/** The layout id of the model a light hangs in. */
function placeOfLight(L) {
  let o = L;
  while (o.parent && !o.parent.isScene) o = o.parent;
  return o.userData.entry?.id || o.name;
}

/** Triangles and meshes in the scene as built (instanced meshes count every copy). */
function sceneStats(scene) {
  let triangles = 0, meshes = 0;
  // what is drawn: hidden subtrees (a person's far figure, a merged book's own mesh) do not count
  scene.traverseVisible((o) => {
    if (!o.isMesh || !o.geometry) return;
    const g = o.geometry;
    const n = g.index ? g.index.count : g.attributes.position?.count || 0;
    triangles += (n / 3) * (o.isInstancedMesh ? o.count : 1);
    meshes++;
  });
  return { triangles: Math.round(triangles), meshes };
}

boot().catch((err) => {
  console.error('[market] could not start', err);
  fail('The market could not open in this browser, so here is the market as text.');
});
