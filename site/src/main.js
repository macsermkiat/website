// Mac's Nachtmarkt: boot. Everything else lives in its own module; this file wires them together.
// Round 5 (docs/adr/0003): a guided stroll instead of free orbit, every section's words on an object in its stall
// instead of side panels, and the stalls streamed in at full detail as the stroll reaches them.
import './styles/main.css';
import * as THREE from 'three';
import { OutlinePass } from 'three/examples/jsm/postprocessing/OutlinePass.js';
import inventory from 'virtual:market-inventory';
import { chooseQuality, switchQuality } from './quality.js';
import { buildMarket } from './engine/market.js';
import { initTextures, textureInfo } from './engine/loader.js';
import { setupLighting } from './engine/lighting.js';
import { placeLights } from './engine/lights.js';
import { createSnowfall } from './engine/snowfall.js';
import { createStreamer } from './engine/stream.js';
import { redrawSigns } from './standins/index.js';
import { createCrowd } from './crowd.js';
import { createAudio } from './audio/index.js';
import { createActions } from './actions/index.js';
import { bandPositions } from './actions/band.js';
import { createCameraRig } from './interaction/camera.js';
import { createPicking } from './interaction/picking.js';
import { createGlow, GLOW } from './interaction/glow.js';
import { itemFrame } from './interaction/itemFrame.js';
import { bindKeyboard, watchMotion } from './interaction/keyboard.js';
import { createStroll } from './nav/stroll.js';
import { createSignpost, ARM_NAMES } from './nav/signpost.js';
import { createGuide } from './nav/guide.js';
import { createSignboard } from './ui/signboard.js';
import { createStopbar } from './ui/stopbar.js';
import { createNote } from './ui/note.js';
import { libraryBook } from './ui/reading.js';
import { createWorldReader } from './world/reader.js';
import { createSurfaces, placeCoasters, modelCoasters, hangPlacards } from './world/surfaces.js';
import { sectionPieces } from './world/sections.js';
import { SECTIONS, ORDER, bookPicks, phrases, taglineHtml } from './content.js';
import { createPerfMeter } from './perf.js';
import { mergeStatic, mergeAcross, mergeSnow, instancePools, instanceRiders, shadowProxies, holdShadowProxies, shadowStandIns } from './engine/merge.js';
import { PROFILES as LIGHTING_PROFILES } from './lighting/settings.js';
import { thinGlass } from './engine/glass.js';
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
  $('still')?.classList.add('done');
  // no 3D here: the text of every section is shown in place of the market (the same content as plain.html)
  if (plain) showPlainFallback(msg);
}

/** Which layout entries open lite on the full market and get their full model at their stop (streaming). */
const STREAMED = (e) => e.kind === 'section' || e.place === 'band' || e.kind === 'town' || e.id === 'tree' || e.kind === 'tree';

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
  // ?pr=<n> caps the pixel ratio (for measuring)
  const PR = Math.min(window.devicePixelRatio || 1, lite ? 1.25 : 1.5, Number(params.get('pr')) > 0 ? Number(params.get('pr')) : Infinity);
  renderer.setPixelRatio(PR);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setSize(stage.clientWidth, stage.clientHeight, false);
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', "Mac's Nachtmarkt: a 3D Christmas market at night.");
  stage.insertBefore(renderer.domElement, overlay);
  // GPU-compressed textures where the GPU takes them (engine/loader.js; ?ktx2=0 loads the webp files)
  initTextures(renderer, { enabled: params.get('ktx2') !== '0' });

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, stage.clientWidth / stage.clientHeight, 0.1, 600);

  // ---------- the market ----------
  const bar = $('loadingBar');
  // Both markets open without the rides and the nine deco stalls and add them just after the first frame
  // (?defer=0 loads everything up front). The full market also opens the section stalls, the bandstand, the town
  // and the tree with their lite models and grafts the full ones on when the stroll reaches them (?stream=0: off).
  const deferOn = params.get('defer') !== '0';
  const streamOn = !lite && params.get('stream') !== '0';
  const market = await buildMarket({
    scene, lite, warn,
    // round 5, pass 2: the town ring comes just after the first frame too (the still covers the first frame, and
    // the town is the far backdrop), which is most of the lite market's margin under round 4
    // round 8: the ornament shop too (a stop at the far right, not in the home view's foreground): its goods are
    // most of a megabyte, and the first frame does not need them
    defer: deferOn ? (e) => e.kind === 'deco' || e.place === 'ferris' || e.place === 'carousel' || e.place === 'schmuck' || e.kind === 'town' : undefined,
    stream: streamOn ? STREAMED : undefined,
    onProgress: (f, e) => { bar.style.width = `${Math.round(f * 85)}%`; $('loadingText').textContent = `Setting up the market… ${e.label || e.id}`; },
  });
  const home = market.layout.home;
  const focus = new THREE.Vector3().fromArray(home.target);
  const { lighting, source: lightingSource } = await setupLighting({ scene, renderer, camera, lite }, warn);
  const reserved = lite ? 0 : 2; // the bandstand's two spotlights (the lite market fakes its spot)
  const heldForLater = lite ? 0 : (market.deferred.some((id) => /riesenrad|karussell|ferris|carousel/.test(id)) ? DEFERRED_LIGHTS : 0) + (market.deferred.some((id) => /schmuck/.test(id)) ? SHOP_LIGHTS : 0);
  const fullBudget = Number(lighting.raw?.profile?.lightBudget) || 14;
  const lightInfo = placeMarketLights({ scene, lighting, lightingSource, spots: market.lightSpots, lite, focus, reserved, warn, budget: lite ? undefined : fullBudget - heldForLater });
  instancePools(lightInfo.pools, scene);
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

  const ownSnow = lightingSource === 'lighting' && lighting.raw && 'snowAmount' in lighting.raw;
  const snowfall = ownSnow ? { set() {}, update() {} } : createSnowfall(scene, { lite });
  const avoid = (x, z) => {
    for (const p of Object.values(market.places)) if (Math.hypot(x - p.holder.position.x, z - p.holder.position.z) < (p.radius || 3) + 1) return false;
    for (const e of market.layout.entries) if ((e.kind === 'deco' || e.kind === 'tree' || (e.place && !market.places[e.place])) && Math.hypot(x - e.position[0], z - e.position[2]) < (e.place ? 6 : 3.4)) return false;
    // the signpost in the foreground of the home view
    const sp = market.layout.entries.find((e) => e.id === 'signpost')?.position || SIGN_POS;
    if (Math.hypot(x - sp[0], z - sp[2]) < 1.8) return false;
    return true;
  };
  // the crowd streams in just after the first frame (round 5: the still and the stalls come first); until then
  // a stand-in with the same API answers for it. ?crowd=first loads it before the market opens, as round 4 did.
  const idleCrowd = { group: new THREE.Group(), count: 0, enableLod: async () => 0, setLod() {}, lod: { far: 0, near: 0 }, lodLevels: 0, stats: () => ({ people: 0, hidden: 0, lite: 0, lodFar: 0, vendorsVisible: 0, sharedAnims: null }), hiddenIds: () => [], people: () => [], speak() {}, say() {}, update() {} };
  let crowdNow = idleCrowd;
  const crowd = new Proxy({}, { get: (_, k) => { const v = crowdNow[k]; return typeof v === 'function' ? v.bind(crowdNow) : v; } });
  const loadCrowd = () => createCrowd({ scene, overlay, lite, manager: undefined, warn, avoid, phrases: phrases(), lodFar: quality.lodFar }).then((c) => {
    crowdNow = c;
    if (!lite) c.group.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    document.documentElement.dataset.crowd = 'ready';
    return c;
  }).catch((e) => { warn(`crowd: ${e?.message || e}`); document.documentElement.dataset.crowd = 'failed'; return idleCrowd; });
  const crowdFirst = params.get('crowd') === 'first';
  if (crowdFirst) await loadCrowd();

  // ---------- sound ----------
  const positions = bandPositions(market);
  const audio = createAudio({ manifest: inventory.audio, positions, getCamera: () => camera, lite, warn });

  // ---------- camera, stroll, words, actions ----------
  const phoneHome = stage.clientWidth < 600 && stage.clientHeight > stage.clientWidth * 0.9;
  const rig = createCameraRig({ camera, dom: renderer.domElement, home: phoneHome ? PHONE_HOME : home, motion });
  const stroll = createStroll({ market, layout: market.layout, order: ORDER, scene });
  const announceEl = $('announce');
  const announce = (t) => { announceEl.textContent = t; };
  let guide = null;
  const note = createNote({ overlay, announce: announceEl, anchorFor: (id) => noteAnchor(market, id || guide?.here) });
  let world = null;
  let glow = null; // the glow on what can be clicked (interaction/glow.js)
  const sfxLog = [];
  const actions = createActions({
    market, scene, lite, motion, audio, rig, camera, overlay,
    books: bookPicks(),
    sfx: (n, o) => { sfxLog.push({ name: n, note: o?.note || null }); if (sfxLog.length > 40) sfxLog.shift(); return audio.sfx(n, o); },
    say: (html) => note.say(html),
    crowdSay: (text, center, radius) => crowd.say(text, center, radius),
    togglePlay: () => togglePlay(),
    frame: (o) => { const b = frameRegion(o); if (b) guide?.markCloseUp(); return b; },
    keyAt: (center, facing) => (center ? key?.aim(center, facing) : key?.follow(market.places[guide?.here])),
    flyBack: (v) => { if (!rig.riding && v) { rig.flyTo(v); if (v.exact) guide?.markCloseUp(); } },
    // where the visitor stands at this stop, and a turn of the head from there (null: back to the stop's own view)
    stopEye: () => (guide?.here && guide.arrived ? guide.stopView() : null),
    turnTo: (target) => { const v = guide?.here && guide.arrived ? guide.stopView() : null; if (!v || rig.riding) return; rig.flyTo(target ? { pos: v.pos, target, near: 0.5 } : v); },
    world: () => world,
    // the keyboard's focus on one item (a book in an open cabinet): outlined, and said
    highlight: (node) => { if (outline) outline.selectedObjects = node ? [node] : []; },
    announce: (t) => announce(t),
    // the ornament shop's moments (round 9) drive the camera, draw a reflection and a post pass, and step the
    // shop's vendor out of the view over the counter
    renderer, dom: renderer.domElement,
    composer: () => composer,
    lights: () => lightInfo.lights,
    bloom: () => lighting.raw?.bloom || composer.passes?.find((p) => p.highPassUniforms || /bloom/i.test(p.constructor?.name || '')) || null,
    renderNow: () => renderMarket(0),
    guide: () => guide,
    picking: () => picking,
    reading: () => world?.isOpen,
    stepOut: (on) => crowd.stepOut?.('deco-schmuck', on),
    sfxLog: (e) => { sfxLog.push(e); if (sfxLog.length > 40) sfxLog.shift(); },
  });

  /** A click on a writing surface (or its probe in the tests): read it, turn its page, or park the wheel first. */
  function readSurface(sid, p = null) {
    const piece = world.pieceFor(sid);
    if (!piece) return;
    // reading already: a click on the page turns it (the right half on, the left half back)
    if (world.isOpen && world.current.surface === sid) {
      const half = clickHalf(sid, p);
      if (half !== 0) world.goTo(world.current.view + half);
      return;
    }
    const surf = world.surface(sid);
    // the engine's own placards open the noticeboard; the ride builder's (with a reading camera in the gondola)
    // are read where they hang: the wheel turns that gondola down to the visitor and waits there (round 6 rides)
    // (a placard with no question written on it yet, only '?', opens the noticeboard too)
    if (piece.decorative && !(surf?.readView && surf.holdsWheel && piece.question)) { guide.read('ferris.notice'); return; }
    if (surf?.holdsWheel) { readOnParkedWheel(piece.id); return; }
    guide.read(piece.id);
  }
  // a placard on a gondola: park the wheel (its gondola back where the model hung it, at the bottom), then read
  const wheelRide = () => market.rides.find((r) => r.wheel && r.gondolas?.length) || null;
  let parkWait = 0;
  function readOnParkedWheel(id) {
    const r = wheelRide();
    if (!r || actions.rides.riding) { guide.read(id); return; }
    // the wheel goes on the way it turns, never back, and eases to a stop with the gondola at the bottom
    const T = r.park(true, { snap: motion.reduced });
    const ticket = ++parkWait;
    const t0 = performance.now(), from = guide.here;
    const wait = () => {
      if (ticket !== parkWait) return;
      if (guide.here !== from) { releaseWheel(); return; }
      // (a slow machine whose frames come too rarely to bring it down in time: the gondola is set down at once)
      if (!r.parked && performance.now() - t0 > T * 1000 + 4000) r.park(true, { snap: true });
      if (r.parked) { guide.read(id); return; }
      requestAnimationFrame(wait);
    };
    wait();
  }
  function releaseWheel() { parkWait++; wheelRide()?.park(false); }

  world = createWorldReader({
    camera, rig, motion, announce,
    sfx: (n) => audio.sfx(n === 'chalk' || n === 'card' ? 'page' : n),
    // after reading a book from an open cabinet, the camera goes back to that cabinet
    stopView: () => { const cv = actions.items.handlers.cabinetView?.(); if (cv) { const b = frameRegionView(cv); if (b) return b; } return guide?.stopView(); },
    els: { bar: $('readbar'), title: $('readTitle'), page: $('readPage'), prevBtn: $('readPrev'), nextBtn: $('readNext'), closeBtn: $('readClose'), flipBtn: $('readFlip'), copy: $('readCopy') },
    onOpen: () => { stopbarEl.hidden = true; picking?.refresh(); glow?.interacted(); },
    onClose: () => { releaseWheel(); if (guide?.here && guide.arrived) stopbar.show(guide.here, { prevId: stroll.prev(guide.here), nextId: stroll.next(guide.here) }); },
  });
  const stopbarEl = $('stopbar');
  // the writing surfaces (stand-ins until the carpenter's and vendor's write_ props arrive) and their words
  const pieces = sectionPieces();
  const surfaces = createSurfaces({ market, camera, warn, stopView: (id) => (stroll.hasStops ? stroll.footOf(id) : null) });
  surfaces.list.forEach((s) => world.addSurface(s));
  surfaces.onAdd((s) => { world.addSurface(s); picking?.refresh(); });
  if (market.places.bier) {
    const n = pieces['bier.vomfass']?.projects?.length || 0;
    // the vendor's Bierdeckel when the props carry them (write_coaster_<i>_front/_back), else the engine's own
    const own = modelCoasters(market.places.bier, n, camera);
    (own.length ? own : placeCoasters(market.places.bier, n, camera)).forEach((s) => world.addSurface(s));
  }
  const hang = (place) => {
    const qs = pieces['ferris.notice']?.questions || [];
    hangPlacards(place, Math.max(qs.length, 3), camera).forEach((s, i) => {
      world.addSurface(s);
      // a placard carries its question (or, before any is written, the wheel's own name)
      world.addPiece({ id: s.id, placeId: 'ferris', surface: s.id, title: qs[i] || 'Big questions', html: pieces['ferris.notice'].html, faces: { main: [{ kind: 'h', level: 1, runs: [{ text: qs[i] || (i === 1 ? 'Große Fragen' : '?') }], size: qs[i] ? 1 : 1.6 }] }, decorative: true, question: !!qs[i] });
    });
  };
  if (market.places.ferris) hang(market.places.ferris); else market.whenPlace?.('ferris').then((p) => p && hang(p));
  for (const p of Object.values(pieces)) world.addPiece(p);

  const signpost = createSignpost({ scene, market, order: ORDER, sub: (id) => SECTIONS[id]?.sub || '', home: phoneHome ? PHONE_HOME : home });

  const playBtn = $('play'), np = $('nowplaying');
  const playLabel = () => (audio.playing ? '❚❚ Pause the ballad' : '▶ Play the ballad');
  let stopbar = null;
  function syncPlay(label) {
    const txt = label || playLabel();
    playBtn.textContent = txt;
    playBtn.setAttribute('aria-pressed', String(audio.playing));
    stopbar?.syncPlay(txt);
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

  // ---------- streaming ----------
  const streamer = createStreamer({
    market, lite, warn,
    // the lite model's merged meshes go before the graft: it moves the full model onto the original nodes
    before: (rec) => {
      try { rec.unshadow?.(); rec.unmerge?.(); } catch (e) { warn(`unmerge ${rec.entry.id}: ${e?.message || e}`); }
      rec.unmerge = null; rec.unshadow = null;
      const place = rec.entry.place && market.places[rec.entry.place];
      if (place?.merge?.undo) { place.merge.undo(); place.merge = null; }
    },
    after: (rec, { failed }) => {
      if (failed) { compact([rec]); return; }
      try { lighting.raw?.tune?.(rec.holder); } catch (e) { warn(`lighting.tune failed: ${e?.message || e}`); }
      compact([rec]);
      const place = rec.entry.place && market.places[rec.entry.place];
      if (place) market.mergeGoods(place);
      // the merged goods' glass gets its specular draw too (engine/glass.js)
      if (place) { try { thinGlass(place.root); } catch (e) { warn(`thin glass: ${e?.message || e}`); } }
      if (place?.id === 'schmuck' || rec.entry.kind === 'town') actions.shop?.refresh();
      market.snow.forEach((o) => (o.visible = snowOn));
      if (renderer.shadowMap.autoUpdate === false) renderer.shadowMap.needsUpdate = true;
      picking?.refresh();
      if (place && place.id === guide?.here) glow?.refresh();
      report.streamed = streamer.report();
    },
  });

  const signboard = createSignboard({ order: ORDER, onChoose: (id) => { showStage(); guide.walkTo(id); }, onHome: () => guide.home(), onFocus: (id) => highlightSign(id) });
  stopbar = createStopbar({
    actionsFor: (id) => actions.get(id),
    itemsFor: (id) => goodsList(id),
    readsFor: (id) => readsFor(id),
    onRead: (pid) => guide.read(pid),
    onStep: (id) => guide.walkTo(id),
    playButtonLabel: playLabel,
  });
  guide = createGuide({ camera, rig, stroll, streamer, actions, world, stopbar, signboard, note, key, market, announce, sections: SECTIONS });
  // the reading bar's "Step back" and Escape both come back to the stop

  /** What there is to read at a stop, as buttons for the bar. */
  function readsFor(id) {
    const out = [];
    for (const p of world.pieces()) {
      if (p.placeId !== id || p.decorative || p.id === 'books.book') continue;
      const s = world.surface(p.surface);
      if (!s) continue;
      if (s.kind === 'coaster') continue; // listed below as one entry
      out.push({ id: p.id, label: `Read ${s.label}` });
    }
    const coasters = world.pieces().filter((p) => p.placeId === id && /coaster_/.test(p.id));
    coasters.forEach((p) => out.push({ id: p.id, label: `Pick up: ${p.title}` }));
    return out;
  }

  const showStage = () => {
    const top = stage.getBoundingClientRect().top;
    if (top < 0 || top > innerHeight * 0.4) window.scrollBy({ top: top - 8, behavior: motion.reduced ? 'auto' : 'smooth' });
  };

  // the arrival shimmer and the hover glow on what answers a click at the stop (interaction/glow.js)
  // the writing surfaces of a stop (their top node: a chalkboard, a coaster, a gondola placard), found on arrival
  function readableRoots(id) {
    const out = [];
    scene.traverse((o) => {
      const r = o.userData.readable;
      if (!r || o.parent?.userData.readable === r || o.userData.glowOverlay || o.userData.href) return; // a reading page's links are not on the stall
      let p = o; while (p && !p.userData.place) p = p.parent;
      if (p?.userData.place === id) out.push(o);
    });
    return out;
  }
  glow = createGlow({
    scene, items: actions.items, motion,
    // at the overview (no stop, standing still) the signpost's arms are what answers
    here: () => (actions.rides.riding ? null : guide.arrived && guide.here ? guide.here : !guide.here && !rig.moving ? 'overview' : null),
    extraTargets: (id) => (id === 'overview' ? Object.values(signpost.arms) : [...actions.items.glowTargets(id), ...readableRoots(id)]),
    reading: () => world.isOpen,
  });
  actions.items.onInteract(() => glow.interacted());
  // a button for something to do at the stop (read, an action, an item, a view) is an interaction too
  stopbarEl.addEventListener('click', (e) => { if (e.target.closest?.('button[data-action],button[data-item],button[data-read],button[data-view]')) glow.interacted(); });

  let picking = null;
  function highlightSign(id) {
    if (!outline) return;
    const arm = id && signpost.arms[id];
    outline.selectedObjects = arm ? [arm] : [];
  }
  picking = createPicking({
    dom: renderer.domElement, camera, market, overlay, outline, items: actions.items, glow,
    current: () => (guide.arrived ? guide.here : null),
    labelFor: (id) => (guide.here === id && guide.arrived ? `${SECTIONS[id]?.name} · ${SECTIONS[id]?.sub}` : `Walk to the ${SECTIONS[id]?.name} · ${SECTIONS[id]?.sub}`),
    extraRoots: () => (signpost.group ? [signpost.group] : Object.values(signpost.arms)),
    readingNow: () => world.isOpen,
    // at a stop only the things there answer (items, writing, cabinets, signs); from the overview a stall walks there
    bodyAnswers: () => !(guide.arrived && guide.here),
    readLabel: (sid) => { const s = world.surface(sid); const p = world.pieceFor(sid); return p?.decorative ? p.title : `Read ${s?.label || 'this'}${p?.title && s?.kind === 'coaster' ? `: ${p.title}` : ''}`; },
    signLabel: (id) => `${ARM_NAMES[id] || id}: walk to the ${SECTIONS[id]?.name || id} · ${SECTIONS[id]?.sub || ''}`,
    onSign: (id) => guide.walkTo(id),
    onRead: (sid, p) => readSurface(sid, p),
    onLink: (href) => openLink(href),
    onPick: (id) => {
      if (actions.rides.riding?.place?.id === id) return;
      if (guide.here === id && guide.arrived) { if (!world.isOpen) guide.read(); return; }
      guide.walkTo(id);
    },
    // an item on a counter or shelf: its own action, walking to its stall first when the visitor is elsewhere
    onItem: (item) => {
      if (item.placeId && market.places[item.placeId] && guide.here !== item.placeId) { guide.walkTo(item.placeId); return; }
      if (world.isOpen && item.kind !== 'book') world.close({ silent: true, keepCamera: true });
      actions.items.click(item);
      focusItem(item);
    },
    // a pick proxy: a Bücherstand cabinet (or its sign), opened by the books' handler
    onProxy: (px) => {
      const place = px.place && market.places[px.place];
      if (place && (guide.here !== px.place || !guide.arrived)) { guide.walkTo(px.place); return; }
      if (world.isOpen) world.close({ silent: true, keepCamera: true });
      actions.items.proxyClick(px);
    },
    proxyLabel: (px) => px.label || '',
  });

  /** -1, 0 or +1: which half of a page a click landed on (for page turns). */
  function clickHalf(sid, p) {
    const r = renderer.domElement.getBoundingClientRect();
    const x = p?.x ?? r.width / 2;
    return x > r.width * 0.55 ? 1 : x < r.width * 0.45 ? -1 : 1;
  }
  function openLink(href) {
    // in-site links (the text version) open here; others in a new tab
    if (/^(https?:)?\/\//.test(href)) window.open(href, '_blank', 'noopener');
    else location.href = href;
  }

  const ITEM_NEAR = 1.7;
  function focusItem(item) {
    const at = actions.items.focusOf(item);
    if (!at || rig.riding) return;
    const fr = itemFrame(item, { items: actions.items, people: () => crowd.people() });
    if (fr) { frameRegion(fr); guide.markCloseUp(); return; }
    const dir = camera.position.clone().sub(at);
    const dist = dir.length();
    if (dist < ITEM_NEAR * 1.15) return;
    dir.y = Math.max(dir.y, dist * 0.25);
    const pos = at.clone().addScaledVector(dir.normalize(), ITEM_NEAR);
    const target = at.clone();
    rig.flyTo({ pos, target, near: 1 });
    guide.markCloseUp();
  }
  // How far up the stage the stop bar reaches (px). Round 10: a framed close-up (an open Bücherstand cabinet at
  // 1366 x 768) sat centred on the whole stage, so the bar hid its lowest row of covers; it is now framed in the
  // clear part above the bar. While the bar is away for a book being read, the last measure stands (the view back
  // to the cabinet is worked out then); a bar the stylesheet hides (a phone's open cabinet) covers nothing.
  let barCoverPx = 0;
  function barCover() {
    const bar = stopbarEl;
    if (!bar) return 0;
    if (bar.hidden) return document.documentElement.dataset.cabinet ? barCoverPx : 0;
    if (getComputedStyle(bar).display === 'none') return (barCoverPx = 0);
    const s = stage.getBoundingClientRect(), b = bar.getBoundingClientRect();
    return (barCoverPx = Math.max(0, Math.min(s.height * 0.45, s.bottom - b.top + 8)));
  }
  /** The view frameRegion would fly to (position, target, near), without flying: the box (centre, facing, half width
   *  and height in metres) square to its face; with clearBar, in the clear part of the stage above the stop bar. */
  function frameRegionView({ center, facing, halfW, halfH, depth = 0, lift = 0.25, margin = 1.25, near = 0.5, clearBar = false }) {
    if (!center || !facing) return null;
    const H = Math.max(300, stage.clientHeight);
    const cover = clearBar ? barCover() : 0;
    const fx = 1, fy = 1 - Math.min(0.45, Math.max(70, cover) / H);
    const t = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    const d = Math.max((halfH * margin) / (t * fy), (halfW * margin) / (t * camera.aspect * fx), near + 0.15) + depth / 2;
    const dir = facing.clone().setY(0).normalize();
    dir.y = lift;
    dir.normalize();
    // look a little below the box, so it sits centred in the clear part of the stage above the bar
    const target = center.clone();
    target.y -= (cover / H) * d * t;
    return { pos: target.clone().addScaledVector(dir, d), target, near };
  }
  function frameRegion(o) {
    if (rig.riding) return null;
    const v = frameRegionView(o);
    if (!v) return null;
    const back = { pos: camera.position.clone(), target: rig.controls.target.clone(), near: rig.controls.minDistance };
    rig.flyTo(v);
    return back;
  }

  // ---------- fewer draw calls ----------
  const merges = { before: 0, after: 0, row: 0 };
  const decoRow = new THREE.Group();
  decoRow.name = 'deco_row_merged';
  scene.add(decoRow);
  const snowRow = new THREE.Group();
  snowRow.name = 'snow_row_merged';
  scene.add(snowRow);
  const riderSyncs = [];
  // shadow stand-ins (engine/merge.js shadowProxies): each placed model's static casters as one mesh per side in
  // the shadow passes; shown only while three draws the shadow maps
  const proxies = shadowStandIns; // shared with the crowd's figure stand-ins (crowd.js)
  const shadowsOn = !lite && renderer.shadowMap.enabled && params.get('proxies') !== '0';
  if (shadowsOn) holdShadowProxies(renderer, () => proxies);
  const minCaster = LIGHTING_PROFILES.full.minMoonCaster || 0;
  function standIn(root) {
    if (!shadowsOn) return null;
    try {
      const sp = shadowProxies(root, { minRadius: minCaster });
      if (!sp) return null;
      sp.proxies.forEach((x) => proxies.add(x));
      merges.shadowCasters = (merges.shadowCasters || 0) + sp.count;
      merges.shadowProxies = (merges.shadowProxies || 0) + sp.proxies.length;
      return () => { sp.proxies.forEach((x) => proxies.delete(x)); sp.undo(); };
    } catch (e) { warn(`shadow stand-ins ${root.name}: ${e?.message || e}`); return null; }
  }
  function compact(all) {
    if (params.get('merge') === '0') return;
    // a streamed model (its lite file until the full one is grafted on) is merged reversibly: the streamer undoes it
    // just before the graft (engine/stream.js `before`), and the full model is merged as usual after it
    for (const p of all.filter((x) => x.streamed)) {
      try {
        const r = mergeStatic(p.root, { reversible: true });
        p.unmerge = r.undo;
        merges.streamed = (merges.streamed || 0) + (r.before - r.after);
      } catch (e) { warn(`merge ${p.entry.id} (lite): ${e?.message || e}`); }
      p.unshadow = standIn(p.root);
    }
    const placed = all.filter((x) => !x.streamed);
    for (const p of placed) {
      try { const r = mergeStatic(p.root); merges.before += r.before; merges.after += r.after; } catch (e) { warn(`merge ${p.entry.id}: ${e?.message || e}`); }
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
      standIn(decoRow);
    }
    for (const p of placed) standIn(p.root);
    try {
      const s = mergeSnow(placed.map((p) => p.root), snowRow);
      if (s.added.length) {
        market.snow = market.snow.filter((o) => !s.removed.includes(o)).concat(s.added);
        merges.snow = (merges.snow || 0) + s.saved;
      }
    } catch (e) { warn(`merge snow caps: ${e?.message || e}`); }
    // thin glass in two blended draws instead of three's transmission pass, which drew every opaque mesh twice
    // (engine/glass.js; ?glass=0 keeps transmission)
    if (params.get('glass') !== '0') { try { merges.thinGlass = (merges.thinGlass || 0) + thinGlass(scene); } catch (e) { warn(`thin glass: ${e?.message || e}`); } }
  }
  // the streamed models are merged reversibly until their full model is grafted on (engine/stream.js)
  compact(market.placed);

  // ---------- snow, overview, keyboard ----------
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
  const q = params.get('snow');
  setSnow(q === '1' ? true : q === '0' ? false : inSeason());

  function resetView() {
    actions.rides.endRide(true);
    guide.home();
  }
  $('reset').addEventListener('click', resetView);
  // How to visit: the walking tips and the credits live in a dialog, not under the market
  const about = $('about');
  $('aboutOpen').addEventListener('click', () => { if (about.showModal) about.showModal(); else about.setAttribute('open', ''); });
  about.addEventListener('click', (e) => { if (e.target === about) about.close(); });   // a click on the backdrop closes it
  // Step back: out of a shop moment first (the view over the Schwibbogen, the dive into the mirror ball)
  $('stepBack').addEventListener('click', () => { if (actions.shop?.end()) return; guide.back(); });
  $('cabTurnL').addEventListener('click', () => actions.items.handlers.turnCabinets?.(-1));
  $('cabTurnR').addEventListener('click', () => actions.items.handlers.turnCabinets?.(1));
  setupMute($('mute'), audio);
  bindKeyboard({
    canvas: renderer.domElement, order: ORDER, rig,
    walkTo: (id) => { showStage(); guide.walkTo(id); },
    home: () => { if (!guide.back()) resetView(); },
    step: (d) => guide.step(d),
    read: () => guide.read(),
    reading: () => world.isOpen,
    readPage: (d) => world.goTo((world.current?.view ?? 0) + d),
    closeRead: () => world.close(),
    endRide: () => { if (actions.shop?.end()) return; actions.rides.endRide(false); },
    isRiding: () => !!actions.rides.riding || !!actions.shop?.busy,
    // at the Bücherstand the arrows move between its cabinets and their books first
    localKey: (k) => guide.arrived && guide.here === 'books' && !rig.riding && !!actions.items.handlers.cabinetKey?.(k),
  });

  // ---------- size ----------
  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    composer.setPixelRatio?.(PR);
    composer.setSize(w, h);
    camera.aspect = w / h;
    const baseFov = home.fov || 42;
    camera.fov = w < 600 ? baseFov + 13 : baseFov;
    camera.updateProjectionMatrix();
    if (world.isOpen) world.refly();
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
  function step(dt) {
    const riding = !!actions.rides.riding;
    const still = motion.reduced && !riding;
    if (!still) T += dt;
    audio.update(dt);
    rig.update(dt);
    world.update(dt);
    const L = audio.levels;
    for (const r of market.rides) r.update(still ? 0 : dt, T, 1, !still);
    for (const sync of riderSyncs) sync();
    for (const m of market.mixers) if (!still) m.update(dt);
    const pulse = (L.bass || 0) * 0.35 + (L.drums || 0) * 0.1;
    const snowLift = 1 + 0.3 * (lighting.raw?.snowAmount ?? (snowOn ? 1 : 0));
    market.bulbMaterials.forEach((m, i) => { m.emissiveIntensity = m.userData.baseEmissive * snowLift * (0.9 + (still ? 0 : 0.07 * Math.sin(T * 1.3 + i * 1.7)) + pulse); });
    actions.update(dt, T, still);
    glow.update(dt);
    key?.update(dt);
    // high above the square (the Riesenrad stop's overview, as on the ride) the lit market is small and far
    // below: the exposure opens up the same way
    const high = actions.rides.riding ? 1 : 1 + 0.55 * THREE.MathUtils.clamp((camera.position.y - 12) / 10, 0, 1);
    const wantExp = baseExposure * actions.rides.exposure() * high;
    renderer.toneMappingExposure += (wantExp - renderer.toneMappingExposure) * (motion.reduced ? 1 : 1 - Math.exp(-dt * 2));
    snowfall.update(dt, T, still);
    w0.w = stage.clientWidth; w0.h = stage.clientHeight;
    crowd.update(dt, T, camera, w0.w, w0.h, { still, look: rig.controls.target });
    note.update(dt, camera);
    actions.shop?.pre();
    try { lighting.update(dt, T); } catch { /* the lighting module's own business */ }
    actions.shop?.post(dt);
  }
  /** Draw the market: the shop's mirror reflection first (when it is in view), then the composer. */
  function renderMarket(dt) {
    try { actions.shop?.beforeRender(); } catch (e) { warn(`shop reflection: ${e?.message || e}`); }
    composer.render(dt);
  }
  function frame() {
    if (frozen) { requestAnimationFrame(frame); return; }
    timer.update();
    const rawDt = timer.getDelta();
    const dt = Math.min(rawDt, 0.1);
    step(dt);
    renderMarket(dt);
    perf?.frame(rawDt);
    governor?.frame(rawDt);
    earlyCheck(rawDt);
    frames++;
    if (!lite && !governor && frames > 30 && frames < 330 && dt > 0.045) slowFrames++;
    if (!governor && frames === 330 && slowFrames > 200) suggestLite();
    requestAnimationFrame(frame);
  }
  // Too slow from the start: in the first 4 s after the market is ready, a median frame over 60 ms (under ~16 fps)
  // on a full market the visitor did not choose switches to lite for this visit (not remembered; the button goes back).
  const early = { t: 0, ft: [], done: lite || quality.source !== 'detected' || params.get('governor') === '0' };
  function earlyCheck(rawDt) {
    if (early.done || document.documentElement.dataset.ready !== 'true' || document.hidden || !(rawDt > 0)) return;
    early.t += rawDt;
    early.ft.push(rawDt * 1000);
    if (early.t < 4 || early.ft.length < 6) return;
    early.done = true;
    const sorted = early.ft.slice(2).sort((a, b) => a - b);
    const p50 = sorted[sorted.length >> 1];
    report.early = { p50: +p50.toFixed(1), frames: early.ft.length };
    if (p50 > 60) { console.info('[market] too slow for the full market here', JSON.stringify(report.early)); switchQuality(true, { remember: false }); }
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
  const governor = !lite && params.get('governor') !== '0' ? createGovernor({
    crowd, lightingStats: () => lighting.raw?.stats?.(), suggestLite,
    onStep: (s) => { report.governor = s; console.info('[market] governor', JSON.stringify(s)); },
  }) : null;
  const perf = params.has('perf') ? createPerfMeter({ stage, renderer, lite, governor: () => governor?.state || null, tour: { openPlace: (id) => guide.walkTo(id), resetView, advance: (s) => step(s) } }) : null;
  if (perf && params.get('perf') === 'tour') setTimeout(() => perf.startTour(), 6000);

  // first frame, then reveal: the still of the home view fades into the live market behind it
  performance.mark?.('market-ready');
  frame();
  bar.style.width = '100%';
  $('loading').classList.add('done');
  $('loading').setAttribute('aria-hidden', 'true');
  renderer.domElement.removeAttribute('role');
  document.fonts?.load("700 64px 'Alegreya SC'").then(redrawSigns).catch(() => {});
  setTimeout(() => audio.prefetch(), 4000);
  // the words in the market (troika and its faces) come in just after the first frame
  requestAnimationFrame(() => world.start());

  // ---------- after the first frame ----------
  const crowdReady = crowdFirst ? Promise.resolve(crowdNow) : new Promise((res) => requestAnimationFrame(() => res())).then(loadCrowd).then((c) => { report.crowd = c.count; report.lod = c.lod; return c; });
  // the far crowd (instanced, GPU-animated) on both markets, baked just after the crowd arrives
  const lodReady = crowdReady.then(() => new Promise((res) => setTimeout(res, 300))).then(() => crowd.enableLod()).catch((e) => { warn(`crowd LOD: ${e?.message || e}`); return 0; });
  const deferredReady = !market.deferred.length ? Promise.resolve(null) : new Promise((res) => requestAnimationFrame(() => res())).then(() => market.loadDeferred()).then((added) => {
    const more = placeMarketLights({ scene, lighting, lightingSource, spots: added.spots, lite, focus, reserved: 0, warn, budget: heldForLater, second: true });
    lightInfo.pools.push(...more.pools);
    lightInfo.lights.push(...more.lights);
    instancePools(more.pools, scene);
    for (const p of added.placed) { try { lighting.raw?.tune?.(p.holder); } catch (e) { warn(`lighting.tune failed: ${e?.message || e}`); } }
    added.snow.forEach((o) => (o.visible = snowOn));
    actions.items.addPlaced(added.placed);
    compact(added.placed);
    streamer.track(added.placed);
    market.snow.forEach((o) => (o.visible = snowOn));
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
  // the still stays over the live market until the part loaded just after the first frame (the town ring, both
  // rides, the deco stalls) is in, so the fade shows no gap where they will stand; at most four seconds
  Promise.race([deferredReady, new Promise((res) => setTimeout(res, 4000))]).then(() => $('still')?.classList.add('done'));
  // the first stop comes in at full detail while the visitor looks at the overview; the town and the tree once
  // everything else has arrived
  const streamReady = streamOn ? deferredReady.then(() => new Promise((res) => setTimeout(res, 600))).then(async () => {
    await streamer.upgrade(stroll.first());
    for (const rec of market.placed.filter((p) => p.streamed && !p.entry.place)) await streamer.upgradeRecord(rec);
    document.documentElement.dataset.streamed = 'first';
  }).catch((e) => warn(`streaming: ${e?.message || e}`)) : Promise.resolve();

  /** The stop bar's list of goods for a stall: each clickable item once, with a number when names repeat. */
  function goodsList(id) {
    const featured = new Set(actions.featuredBooks);
    const list = actions.items.of(id).filter((it) => it.clickable && !['tap', 'lid', 'kettle', 'pot', 'served'].includes(it.kind))
      .filter((it) => !/^act_orn_candle_/i.test(it.node.name)) // the Schwibbogen's candles light with the arch
      .filter((it) => it.kind !== 'book' || featured.has(it.node) || !!it.info.slug || /counter/i.test(it.info.where || ''));
    const seen = {};
    const total = {};
    for (const it of list) total[it.label] = (total[it.label] || 0) + 1;
    return list.map((it) => {
      seen[it.label] = (seen[it.label] || 0) + 1;
      const label = total[it.label] > 1 ? `${it.label} (${seen[it.label]})` : it.label;
      return { name: it.node.name, label, fn: () => { actions.items.click(it); focusItem(it); } };
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
    stroll: { stops: stroll.stops, lane: stroll.laneSource, signpost: signpost.source },
    surfaces: Object.fromEntries(surfaces.list.map((s) => [s.id, s.fromModel ? 'model write_ node' : 'engine stand-in'])),
    streamed: [],
    props: market.propCount,
    crowd: crowd.count,
    scene: sceneStats(scene),
    warnings,
  };
  if (debug) console.info('[market] report', report);
  // a small handle for tests and for the curious
  window.__market = {
    ready: true, report, resetView, setSnow, togglePlay,
    /** Walk to a place's stop (the old name is kept for the tests and the perf tour). */
    openPlace: (id) => guide.walkTo(id),
    walkTo: (id) => guide.walkTo(id),
    home: () => guide.home(),
    step: (d) => guide.step(d),
    back: () => guide.back(),
    get stop() { return guide.here; },
    get arrived() { return guide.arrived && !rig.moving; },
    get panel() { return guide.arrived ? guide.here : null; },
    camera, scene, renderer, textures: textureInfo,
    cam: () => ({ mode: rig.mode, moving: rig.moving, progress: rig.progress, look: rig.look, pos: camera.position.toArray().map((v) => +v.toFixed(3)), target: rig.controls.target.toArray().map((v) => +v.toFixed(3)) }),
    nudge: (yaw, zoom, pitch) => rig.nudge(yaw, zoom, pitch),
    /** The lane path a walk from here to a stop would take (tests check it keeps clear of the stalls). */
    pathTo: (id) => stroll.pathTo(camera.position, id)?.points.map((p) => p.toArray().map((v) => +v.toFixed(2))) || null,
    strollInfo: () => ({ stops: stroll.stops, lane: stroll.lane(), source: stroll.laneSource }),
    placeCenters: () => Object.fromEntries(Object.entries(market.places).map(([k, p]) => [k, { pos: p.holder.position.toArray(), radius: p.radius }])),
    // reading
    read: (id) => guide.read(id),
    readPage: (d) => world.goTo((world.current?.view ?? 0) + d),
    /** As a click on a writing surface does (a gondola's placard parks the wheel first). */
    readSurface: (sid) => readSurface(sid),
    /** For tests: a write_<name> quad and its card_<name> backing sheet glow as one (the same material). */
    backing(name) {
      const m = (n) => { const o = scene.getObjectByName(n); return o?.isMesh ? o.material : o?.children.find((c) => c.isMesh)?.material || null; };
      const w = m(`write_${name}`), c = m(`card_${name}`);
      // one shared material, or (the round-7 ticket) a printed card and a plain writing paper of the same cream that
      // both glow when read
      const alike = !!c && !!w && c.color.getHex() === w.color.getHex() && c.emissiveIntensity > 0.1 && w.emissiveIntensity > 0.1;
      return { card: !!c, same: !!c && (c === w || alike), glow: w?.emissiveIntensity ?? null };
    },
    /** For tests: park the wheel (or let it go) as a placard does; returns the seconds the parking takes. */
    parkWheel: (on = true) => wheelRide()?.park(on) ?? null,
    wheel() {
      const r = wheelRide();
      if (!r) return null;
      const vis = (n) => { const o = scene.getObjectByName(n); let v = !!o; for (let q = o; q && v; q = q.parent) v = q.visible; const m = o?.isMesh ? o : o?.children.find((c) => c.isMesh); return { visible: v, glow: m?.material?.emissiveIntensity ?? null }; };
      return { angle: +r.wheel.angle.toFixed(4), dir: Math.sign(r.wheel.speed) || 1, parkTo: r.wheel.parkTo, parking: r.wheel.parkTo != null, parked: r.parked, card: vis('card_question_1'), write: vis('write_question_1') };
    },
    closeRead: () => world.close(),
    reading: () => { const c = world.current; return c ? { open: true, ...c, title: world.piece(c.id)?.title || '' } : { open: false }; },
    textOn: (sid) => world.textOn(sid),
    pieces: () => world.pieces().map((p) => ({ id: p.id, place: p.placeId, surface: p.surface, title: p.title })),
    surfaces: () => surfaces.list.map((s) => ({ id: s.id, kind: s.kind, fromModel: s.fromModel })),
    /**
     * For tests: is a model coaster's writing printed on it? Its write_ cards (front given the print, back hidden
     * under a round card face) and how far its drawn words reach from the disc's middle, as a share of its radius.
     */
    coasterPrint(i = 0) {
      const s = world.surface(`bier.coaster_${i}`);
      if (!s) return null;
      const root = s.root;
      const mesh = (n) => { const o = root.getObjectByName(n); return o?.isMesh ? o : o?.children.find((c) => c.isMesh) || null; };
      const fc = mesh(`write_coaster_${i}_front`), bc = mesh(`write_coaster_${i}_back`), back = root.getObjectByName('engine_coaster_back');
      let disc = null;
      root.traverse((o) => { if (!disc && o.isMesh && !/^(write_|engine_)/.test(o.name) && !/^write_/.test(o.parent?.name || '')) disc = o; });
      const reach = {};
      for (const [face, f] of Object.entries(s.faces)) {
        if (!f.r) continue;
        f.area.updateWorldMatrix(true, true); // the loop may be held (tests): lines added since the last frame
        // each drawn line's block bounds (troika's, in the line's own plane), into the area's frame, one by one
        const inv = f.area.matrixWorld.clone().invert();
        const c = new THREE.Vector3(f.w / 2, -f.h / 2, 0);
        let far = 0, n = 0;
        // a page's runs are members of one batched draw (world/text.js): their frame is the batch's times their own
        const runs = [];
        f.area.traverse((o) => {
          if (o.isText && o.visible && o._members) for (const t of o._members.keys()) { t.updateMatrix(); runs.push({ t, world: o.matrixWorld.clone().multiply(t.matrix) }); }
          else if (o.isText && o.visible) runs.push({ t: o, world: o.matrixWorld });
        });
        for (const { t, world } of runs) {
          const b = t.text?.trim() && t.textRenderInfo?.blockBounds;
          if (!b) continue;
          n++;
          const m = inv.clone().multiply(world);
          for (const [x, y] of [[b[0], b[1]], [b[2], b[1]], [b[0], b[3]], [b[2], b[3]]]) { const p = new THREE.Vector3(x, y, 0).applyMatrix4(m); far = Math.max(far, Math.hypot(p.x - c.x, p.y - c.y)); }
        }
        if (n) reach[face] = +(far / f.r).toFixed(3);
      }
      return { fromModel: !!s.fromModel, frontPrinted: !!fc && !!disc && fc.material === disc.material || (!!fc && /vendor_print/.test(fc.material?.name || '')), backCardHidden: !!bc && !bc.visible, roundBack: !!back?.visible, reach };
    },
    /** For tests: the open book's pages, printed on the paper (no card of another tone under the words). */
    bookPrint() {
      let out = null;
      scene.traverse((o) => { if (!out && /^open_/.test(o.name)) { const l = o.getObjectByName('write_page_left_mesh') || o.getObjectByName('write_page_left'); const m = l?.isMesh ? l : l?.children.find((c) => c.isMesh); out = { model: !!m, material: m?.material?.name || null }; } });
      return out;
    },
    readCopy: () => ({ hidden: $('readCopy').hidden, text: $('readCopy').textContent.slice(0, 600), links: [...$('readCopy').querySelectorAll('a')].map((a) => a.href) }),
    streaming: () => ({ state: streamer.state(), report: streamer.report() }),
    streamReady: () => streamReady,
    act(id, k) { const a = actions.get(id)?.acts.find((x) => x.key === k); if (!a) throw new Error(`no action ${k} at ${id}`); a.fn(); },
    get riding() { return actions.rides.riding?.type || null; },
    get snow() { return snowOn; },
    snowCaps: () => ({ entries: market.snow.length, merged: market.snow.filter((o) => o.userData.snow).length, visible: market.snow.filter((o) => o.visible).length, saved: merges.snow || 0 }),
    freeze(on = true) { frozen = !!on; if (!frozen) timer.reset?.(); },
    advance(seconds) { for (let t = 0; t < seconds; t += 0.05) step(0.05); },
    /** For tests: draw a frame now and return the canvas as a data URL (the market only, no page around it). */
    snapshot(type = 'image/jpeg', quality = 0.86) { renderMarket(0); return renderer.domElement.toDataURL(type, quality); },
    get audio() { return { playing: audio.playing, mode: audio.mode, phase: audio.phase, levels: { ...audio.levels }, where: audio.where(), endings: audio.endings, alternatesReady: audio.alternatesReady }; },
    seekSong: (pos, pass) => audio.seek(pos, pass),
    get rideStage() { return actions.rides.stage; },
    get exposure() { return renderer.toneMappingExposure; },
    governor: () => governor?.state || null,
    keyLight: () => key?.state() || null,
    crowd: () => crowd.stats(),
    saxStand: () => { const st = scene.getObjectByName('instrument_sax_stand'), h = scene.getObjectByName('instrument_sax'); return { stand: !!st, standVisible: !!st?.visible, heldVisible: !!h?.visible }; },
    hiddenPeople: () => crowd.hiddenIds(),
    people: () => crowd.people(),
    sceneStats: () => sceneStats(scene),
    settled: () => Promise.all([lodReady, deferredReady]).then(([lod, deferred]) => ({ lod, deferred })),
    featuredBooks: () => actions.featuredBooks.map((n) => n.name),
    note: () => note.text,
    /** The last stall sounds asked for (tests): name and note. */
    sfxLog: () => sfxLog.slice(),
    bookPicks: () => bookPicks().map((b) => [b[0], b[1]]),
    items: () => itemCounts(),
    clickItem(name, { focus = false } = {}) { const it = actions.items.all().find((i) => i.node.name === name); if (!it) throw new Error(`no item ${name}`); picking.setEnabled(true); const r = actions.items.click(it); if (focus) focusItem(it); return r; },
    item: (name) => { const it = actions.items.all().find((i) => i.node.name === name); if (!it) return null; const n = it.node; return { name: n.name, kind: it.kind, label: it.label, busy: it.busy, position: n.getWorldPosition(new THREE.Vector3()).toArray().map((v) => +v.toFixed(4)), quaternion: n.getWorldQuaternion(new THREE.Quaternion()).toArray().map((v) => +v.toFixed(4)), visible: n.visible }; },
    focusOn(name) { const it = actions.items.all().find((i) => i.node.name === name); if (it) focusItem(it); },
    handlers: actions.items.handlers,
    bookCategory: (slug) => libraryBook({ slug })?.category || null,
    openedBook: () => actions.items.handlers.openedBook?.() || null,
    itemAt: (x, y) => picking.itemAt(x, y),
    pickAt: (x, y) => picking.full(x, y),
    rawAt: (x, y) => picking.rawAt(x, y),
    /** The deco stalls (scenery, tests): their ids, and where one is on screen (the middle of its front). */
    decos: () => (market.blockRoots || []).map((h) => h.userData.entry?.id).filter(Boolean),
    entryPoint(id) {
      const h = (market.blockRoots || []).concat(market.hotRoots).find((o) => o.userData.entry?.id === id);
      if (!h) return null;
      const box = new THREE.Box3().setFromObject(h);
      const c = box.getCenter(new THREE.Vector3());
      c.y = box.min.y + (box.max.y - box.min.y) * 0.4;
      const p = c.project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, onScreen: Math.abs(p.x) < 1 && Math.abs(p.y) < 1 && p.z < 1 };
    },
    tipAt: (x, y, text) => picking.tipAt(x, y, text),
    hoverAt(x, y) { renderer.domElement.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, pointerType: 'mouse', bubbles: true })); },
    get hoveredItem() { return actions.items.hovered?.node.name || null; },
    /** The glow on what can be clicked (tests): the shimmer's state and each glowing node's level. */
    glow: () => glow.state(),
    /** Tune the glow live (tests and screenshots): GLOW's keys (peak, hover, period, hold, ...). */
    glowTune: (o) => Object.assign(GLOW, o || {}),
    renderFrame() { renderMarket(0.016); },
    muted: () => audio.muted,
    screenPoint(name) {
      const o = scene.getObjectByName(name);
      if (!o) return null;
      const box = new THREE.Box3();
      o.traverse((m) => { if (m.isMesh && !m.isText) { m.geometry.computeBoundingBox(); box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld)); } });
      const p = (box.isEmpty() ? o.getWorldPosition(new THREE.Vector3()) : box.getCenter(new THREE.Vector3())).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, onScreen: Math.abs(p.x) < 1 && Math.abs(p.y) < 1 && p.z < 1 };
    },
    /** The size on screen of a node's bounding box, in CSS pixels (tests: a book cover's tap target). */
    screenBox(name) {
      const o = scene.getObjectByName(name);
      if (!o) return null;
      o.updateWorldMatrix(true, true);
      const box = new THREE.Box3();
      o.traverse((m) => { if (m.isMesh && !m.isText) { m.geometry.computeBoundingBox(); box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld)); } });
      if (box.isEmpty()) return null;
      const r = renderer.domElement.getBoundingClientRect();
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (let i = 0; i < 8; i++) {
        const p = new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).project(camera);
        const x = r.left + ((p.x + 1) / 2) * r.width, y = r.top + ((1 - p.y) / 2) * r.height;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      }
      return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0, onScreen: x0 >= r.left - 1 && x1 <= r.right + 1 && y0 >= r.top - 1 && y1 <= r.bottom + 1 };
    },
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
  };
  document.documentElement.dataset.ready = 'true';
  // a visitor who arrives with #glueh (or any place id) walks straight there
  const want = location.hash.slice(1);
  if (want && SECTIONS[want] && ORDER.includes(want)) setTimeout(() => guide.walkTo(want), 400);
}

const SIGN_POS = [-3.4, 0, 19.2];
// the home view on a phone: closer and lower, between the front row's string-light poles
const PHONE_HOME = { position: [3.75, 5.6, 16], target: [3.4, 2.4, -4] };
const DEFERRED_LIGHTS = 2;
const SHOP_LIGHTS = 2; // the ornament shop's two real-time lights, held for it when it comes after the first frame

/** Where a note about a place is pinned: above its counter, or the middle of a landmark. */
function noteAnchor(market, id) {
  const place = market.places[id];
  if (!place) return null;
  if (place.nodes?.slots?.slot_counter) return place.nodes.slots.slot_counter.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.75, 0));
  return place.center.clone().setY(Math.min(place.center.y, 3.2));
}

/**
 * The lite market's close-up key light: one warm spot under the front eave of the stall at the current stop.
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
      if (!place || !['glueh', 'bier', 'wurst', 'books', 'schmuck'].includes(place.id)) { want = 0; placeId = null; return; }
      placeId = place.id;
      const c = counterLocal(place);
      const from = new THREE.Vector3(c.x, 2.35, c.z + 1.25);
      const to = new THREE.Vector3(c.x, 1.05, c.z - 0.1);
      place.holder.localToWorld(from);
      place.holder.localToWorld(to);
      L.position.copy(from);
      L.target.position.copy(to);
      L.target.updateMatrixWorld();
      want = INTENSITY;
    },
    aim(center, facing) {
      if (!placeId || !center || !facing) return;
      // a cabinet's pale face-out covers stand close to it: a softer light from a little further off, so they
      // read as paper and not as a white glare
      L.position.copy(center).addScaledVector(facing.clone().setY(0).normalize(), 1.7).add(new THREE.Vector3(0, 1.0, 0));
      L.target.position.copy(center);
      L.target.updateMatrixWorld();
      want = INTENSITY * 0.3;
    },
    update(dt) { L.intensity += (want - L.intensity) * Math.min(1, dt * 3); },
    state: () => ({ place: placeId, intensity: +L.intensity.toFixed(2), position: L.position.toArray().map((v) => +v.toFixed(2)) }),
  };
}

/** light_ empties become lights: the lighting designer's placement when the module offers one, else the engine's. */
function placeMarketLights({ scene, lighting, lightingSource, spots, lite, focus, reserved, warn, budget, second = false }) {
  const theirs = lightingSource === 'lighting' && typeof lighting.raw?.placeLights === 'function';
  const place = (list, opts) => {
    if (theirs) {
      try { const r = lighting.raw.placeLights(list, { focus, reserved, ...opts }); if (r?.lights) return r; } catch (e) { warn(`lighting.placeLights failed (${e?.message || e}); the engine places the lights.`); }
    }
    return placeLights(scene, list, { lite, focus, reserved, budget: opts.budget });
  };
  if (second || budget === 0) {
    // the rides keep the real-time lights held for them; the town's (deferred with them) become glows, as they were
    // when the town loaded first
    const rides = spots.filter((s) => s.kind !== 'town'), town = spots.filter((s) => s.kind === 'town');
    const a = place(rides, { budget: budget || 0, reserved: 0, shadowed: 0 });
    if (!town.length) return a;
    const b = place(town, { budget: 0, reserved: 0, shadowed: 0 });
    return { lights: [...a.lights, ...b.lights], pools: [...a.pools, ...b.pools], cap: a.cap };
  }
  if (!lite) return place(spots, budget != null ? { budget } : {});
  const first = place(spots.filter((s) => s.kind === 'section'), {});
  const rest = place(spots.filter((s) => s.kind !== 'section'), { budget: Math.max(0, first.cap - first.lights.length) + reserved });
  return { lights: [...first.lights, ...rest.lights], pools: [...first.pools, ...rest.pools], cap: first.cap };
}

function placeOfLight(L) {
  let o = L;
  while (o.parent && !o.parent.isScene) o = o.parent;
  return o.userData.entry?.id || o.name;
}

function sceneStats(scene) {
  let triangles = 0, meshes = 0;
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
