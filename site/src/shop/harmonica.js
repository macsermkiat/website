// The glass harmonica (round 9, ADR 0004 revision): the twelve baubles on the ornament shop's front rail
// (act_orn_harmonica_0..11, left to right) are tuned to the opening of the band's ballad, "Lanterns After Closing"
// (music/score/LEADSHEET.md, the head in G minor): the first twelve notes of the tune, from the pickup D through
// bar 5 (D Bb A | G A C | Eb D F# | G, F Ab), two octaves up where glass rings best. So a brush across the row,
// left to right, plays the tune; tapping them in order does too.
//   - A drag (mouse or finger) that starts on the row brushes it: each bauble the pointer crosses rings, louder and
//     brighter the faster the brush, swings a little on its ribbon away from the stroke and glows on its note. The
//     row claims that pointer, so the head does not turn while brushing (a phone's look-around keeps the rest of
//     the screen).
//   - Left alone for a few seconds at the shop, the next bauble of the phrase glows faintly, so a visitor finds
//     the tune note by note. Played through, the row answers with a soft ripple of light.
//   - The stop bar's "Play the glass harmonica" plays the phrase in its own rhythm.
// Reduced motion: the baubles glow and ring but do not swing.
import * as THREE from 'three';
import { toThinGlass, keepThinGlass, thinGlass } from '../engine/glass.js';
import { strike as glassStrike } from '../audio/glass.js';
import { worldDirToParent } from '../actions/items/common.js';

export const PHRASE = ['D5', 'Bb5', 'A5', 'G5', 'A5', 'C6', 'Eb6', 'D6', 'F#5', 'G5', 'F5', 'Ab5'];
// the tune's rhythm in beats (the long A of bar 2 shortened to two beats: a glass note has rung out by then)
const ONSETS = [0, 1, 3.5, 6, 6.5, 7, 8, 9.5, 10, 11, 13, 13.5];
const TEMPO = 72;
const IDLE_HINT = 3.2; // seconds left alone before the next note glows
const GLOW = new THREE.Color(1.0, 0.6, 0.26); // a warm candle amber, so a ringing bauble reads as lit from inside

let haloTex = null;
function halo() {
  if (haloTex) return haloTex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,226,170,0.95)'); gr.addColorStop(0.22, 'rgba(255,176,90,0.5)'); gr.addColorStop(0.55, 'rgba(255,130,40,0.14)'); gr.addColorStop(1, 'rgba(255,110,30,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  haloTex = new THREE.CanvasTexture(c);
  haloTex.colorSpace = THREE.SRGBColorSpace;
  return haloTex;
}

/**
 * The clear-glass shells (vendor_glass, an opaque white in the file) made see-through: the body lets the inner
 * mercury bauble and the glow show, while the reflections stay at full strength and thicken toward the rim
 * (premultiplied blending: the diffuse scaled by a Fresnel alpha, the specular and the glow added whole).
 */
function clearGlass(m) {
  // round 10: glass whose transmission engine/glass.js has turned into two blended draws (a multiply by its
  // transmittance, and a child mesh adding the specular) takes the rim alpha into the multiply, which draws what the
  // premultiplied blend over the transmission drew
  if (m.userData.thinGlass || toThinGlass(m)) {
    keepThinGlass(m);
    m.defines = { ...(m.defines || {}), NM_GLASS_FA: '' };
    m.envMapIntensity = Math.max(m.envMapIntensity ?? 1, 1.6);
    m.needsUpdate = true;
    return;
  }
  m.transparent = true;
  m.depthWrite = false;
  m.blending = THREE.CustomBlending;
  m.blendSrc = THREE.OneFactor;
  m.blendDst = THREE.OneMinusSrcAlphaFactor;
  m.blendSrcAlpha = THREE.OneFactor;
  m.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
  m.envMapIntensity = Math.max(m.envMapIntensity ?? 1, 1.6);
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (shader, r) => {
    prev?.call(m, shader, r);
    shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>', `
  {
    float nv = clamp( abs( dot( geometryNormal, geometryViewDir ) ), 0.0, 1.0 );
    float fa = mix( 0.1, 0.78, pow( 1.0 - nv, 2.5 ) );
    gl_FragColor = vec4( totalDiffuse * fa + totalSpecular + totalEmissiveRadiance, fa );
  }`);
  };
  const key = m.customProgramCacheKey?.bind(m);
  m.customProgramCacheKey = () => `${key ? key() : ''}|clearglass`;
  m.needsUpdate = true;
}

export function createHarmonica({ items, dom, camera, rig, motion, sfxLog, canPlay, say, onBusy, place = null, stopView = null, onDrive = null }) {
  const baubles = items.slice().sort((a, b) => indexOf(a) - indexOf(b)).map((item, i) => setupBauble(item, i));
  let idle = 0, expect = 0, claimed = null, auto = null, ripple = -1;
  const log = []; // strikes, for the tests: { i, note, v, t }
  let T = 0;

  function indexOf(item) {
    const n = item.info?.index ?? /_(\d+)$/.exec(item.node.name)?.[1];
    return Number(n) || 0;
  }

  function setupBauble(item, i) {
    const node = item.node;
    node.userData.live = true;
    // the glass of this bauble (mercury and clear shells: plain factors, no textures) gets its own copy, so it
    // can glow on its own note
    const mats = [];
    node.traverse((o) => {
      if (!o.isMesh || o.userData.itemFx) return;
      const swap = (m) => {
        if (!m || m.map || !/mercury|glass|gloss/i.test(m.name || '')) return m;
        const c = m.clone();
        delete c.userData.fromGlb; // a streamed upgrade keeps this engine copy
        c.name = `${m.name}_harmonica_${i}`;
        if (!c.emissive) c.emissive = new THREE.Color(0);
        c.emissive.copy(GLOW);
        c.emissiveIntensity = 0;
        if (!/mercury/i.test(m.name || '')) clearGlass(c);
        mats.push(c);
        return c;
      };
      o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material);
    });
    thinGlass(node); // the specular draw of glass turned above (engine/glass.js)
    const box = new THREE.Box3().setFromObject(node);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    // the halo sits on the glass itself (the node's box takes in the ribbon and the cap too)
    const gbox = new THREE.Box3();
    node.updateWorldMatrix(true, true);
    node.traverse((o) => { if (o.isMesh && !o.userData.itemFx && [].concat(o.material).some((m) => mats.includes(m))) gbox.expandByObject(o); });
    const gs = (gbox.isEmpty() ? box : gbox).getBoundingSphere(new THREE.Sphere());
    const local = node.worldToLocal(gs.center.clone());
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: halo(), color: 0xffffff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
    sp.name = `engine_harmonica_halo_${i}`;
    sp.userData.itemFx = true;
    sp.position.copy(local);
    const ws = node.getWorldScale(new THREE.Vector3()).x || 1;
    sp.scale.setScalar((gs.radius * 5.4) / ws);
    sp.visible = false;
    node.add(sp);
    const q0 = node.quaternion.clone();
    // swing axes in the bauble's parent frame: sideways (about the shop's forward axis) and fore-aft (about the rail)
    const fwd = new THREE.Vector3(0, 0, 1).transformDirection(node.parent.matrixWorld);
    const rail = new THREE.Vector3(1, 0, 0).transformDirection(node.parent.matrixWorld);
    return {
      item, i, node, mats, sp, q0, local, radius: sphere.radius * 0.8,
      note: PHRASE[i % PHRASE.length],
      axA: worldDirToParent(node, fwd).normalize(), axB: worldDirToParent(node, rail).normalize(),
      a: 0, va: 0, b: 0, vb: 0, glow: 0, hint: 0, lastStrike: -10,
    };
  }

  const _w = new THREE.Vector3(), _c = new THREE.Vector3();
  /** Screen positions (CSS px, canvas-relative) and radii of the baubles. */
  function screen() {
    const r = dom.getBoundingClientRect();
    const out = [];
    camera.updateMatrixWorld();
    const tanH = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    for (const B of baubles) {
      B.node.localToWorld(_w.copy(B.local));
      _c.copy(_w).project(camera);
      const dist = camera.position.distanceTo(_w);
      out.push({ B, x: ((_c.x + 1) / 2) * r.width, y: ((1 - _c.y) / 2) * r.height, rpx: (B.radius / (dist * tanH)) * (r.height / 2), front: _c.z < 1 });
    }
    return { pts: out, rect: r };
  }

  function hitAt(x, y, pts, touch) {
    let best = null, bd = Infinity;
    for (const p of pts) {
      if (!p.front) continue;
      const reach = Math.max(p.rpx * 1.3, touch ? 15 : 8);
      const d = Math.hypot(x - p.x, y - p.y);
      if (d < reach && d < bd) { bd = d; best = p.B; }
    }
    return best;
  }

  /** Ring bauble B. velocity 0..1; dir -1/+1 the stroke's direction on screen (0: a tap). */
  function strike(B, { velocity = 0.55, dir = 0, source = 'tap' } = {}) {
    const v = THREE.MathUtils.clamp(velocity, 0.15, 1);
    const pan = THREE.MathUtils.clamp(((B.i / 11) - 0.5) * 0.9, -0.6, 0.6);
    glassStrike(B.note, { velocity: v, pan });
    sfxLog?.({ name: 'harmonica', note: B.note });
    B.glow = Math.max(B.glow, 0.55 + 0.45 * v);
    B.lastStrike = T;
    if (!motion.reduced) {
      // a push from the stroke: sideways with the brush, and a little away from the visitor
      B.va += (dir || (B.i % 2 ? 0.35 : -0.35)) * (0.6 + 1.3 * v);
      B.vb += -0.35 - 0.5 * v;
    }
    log.push({ i: B.i, note: B.note, v: +v.toFixed(2), source, t: +T.toFixed(2) });
    if (log.length > 64) log.shift();
    idle = 0;
    // following the tune?
    if (B.i === expect) expect++;
    else expect = B.i === 0 ? 1 : 0;
    if (expect >= baubles.length) { expect = 0; played(); }
  }

  function played() {
    ripple = 0;
    say?.('The glass harmonica: you played the opening of <b>Lanterns After Closing</b>, the ballad the band plays at the bandstand.');
  }

  // ---------- the brush: a pointer that starts on the row ----------
  let last = null;
  function claim(e) {
    if (!canPlay() || auto) return false;
    const { pts, rect } = screen();
    const x = e.clientX - rect.left, y = e.clientY - rect.top, touch = e.pointerType === 'touch';
    const vis = pts.filter((p) => p.front);
    if (!vis.length) return false;
    // the row's band: from the first bauble to the last, a bauble's height above and below
    const pad = Math.max(...vis.map((p) => p.rpx)) * 1.6 + (touch ? 12 : 4);
    const x0 = Math.min(...vis.map((p) => p.x)) - pad, x1 = Math.max(...vis.map((p) => p.x)) + pad;
    const y0 = Math.min(...vis.map((p) => p.y)) - pad, y1 = Math.max(...vis.map((p) => p.y)) + pad;
    if (x < x0 || x > x1 || y < y0 || y > y1) return false;
    claimed = { id: e.pointerId, touch, moved: 0 };
    try { dom.setPointerCapture(e.pointerId); } catch { /* a synthetic pointer */ }
    last = { x, y, t: e.timeStamp || performance.now(), hit: null };
    const B = hitAt(x, y, pts, touch);
    if (B) { strike(B, { velocity: 0.5, source: 'brush' }); last.hit = B; B.gestureAt = performance.now(); }
    onBusy?.(true);
    return true;
  }
  function move(e) {
    if (!claimed || e.pointerId !== claimed.id) return;
    const { pts, rect } = screen();
    const x = e.clientX - rect.left, y = e.clientY - rect.top, t = e.timeStamp || performance.now();
    const dx = x - last.x, dy = y - last.y, len = Math.hypot(dx, dy);
    if (len < 0.5) return;
    claimed.moved += len;
    const speed = len / Math.max(4, t - last.t); // px per ms
    const v = THREE.MathUtils.clamp(0.22 + speed * 0.55, 0.2, 1);
    const dir = Math.sign(dx) || 0;
    // walk the stroke in small steps so a fast brush still rings every bauble it crosses
    const steps = Math.max(1, Math.ceil(len / 5));
    for (let k = 1; k <= steps; k++) {
      const px = last.x + (dx * k) / steps, py = last.y + (dy * k) / steps;
      const B = hitAt(px, py, pts, claimed.touch);
      if (B && B !== last.hit) { strike(B, { velocity: v, dir, source: 'brush' }); B.gestureAt = performance.now(); }
      last.hit = B;
    }
    last.x = x; last.y = y; last.t = t;
    e.preventDefault?.();
  }
  function up(e) {
    if (!claimed || e.pointerId !== claimed.id) return;
    try { dom.releasePointerCapture(e.pointerId); } catch { /* fine */ }
    claimed = null; last = null;
    onBusy?.(false);
  }
  rig.claim(claim);
  // a tap while the camera leans in to the played phrase ends it
  dom.addEventListener('pointerup', (e) => { if (lean && lean.phase !== 'out' && e.button <= 0 && performance.now() - lean.startedAt > 400) stop(); });
  dom.addEventListener('pointermove', move);
  dom.addEventListener('pointerup', up);
  dom.addEventListener('pointercancel', up);

  // ---------- the phrase, played for the visitor ----------
  // "Play the glass harmonica": the camera leans in to the row (it fills the view; on a narrow screen it follows
  // the note along the row), the phrase rings in its own rhythm, and the camera eases back to the stop.
  const UP = new THREE.Vector3(0, 1, 0);
  const ease = (x) => { const k = THREE.MathUtils.clamp(x, 0, 1); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };
  let lean = null; // { phase: 'in'|'hold'|'out', t, from, back }
  const worldOf = (B) => B.node.localToWorld(B.local.clone());
  function leanPose(k) {
    const ends = [worldOf(baubles[0]), worldOf(baubles[baubles.length - 1])];
    const mid = ends[0].clone().add(ends[1]).multiplyScalar(0.5);
    const F = new THREE.Vector3(0, 0, 1).transformDirection(place.holder.matrixWorld).setY(0).normalize();
    const hw = ends[0].distanceTo(ends[1]) / 2 + 0.16;
    const tanV = Math.tan(THREE.MathUtils.degToRad(50) / 2), tanH = tanV * camera.aspect;
    const d = THREE.MathUtils.clamp(hw / tanH, 0.95, 2.4);
    const pos = mid.clone().addScaledVector(F, d).addScaledVector(UP, -0.16);
    const fit = Math.min(1, (d * tanH) / hw);
    const now = auto ? baubles[Math.max(0, Math.min(baubles.length - 1, auto.k - 1))] : null;
    const target = mid.clone().addScaledVector(UP, -0.02);
    if (fit < 1 && now) target.lerp(worldOf(now), (1 - fit) * 1.1);
    return { pos, target, fov: 50, k };
  }
  function leanFn(dt) {
    if (!lean) return null;
    lean.t += dt;
    const IN = motion.reduced ? 0 : 1.5, OUT = motion.reduced ? 0 : 1.5;
    if (lean.phase === 'in') {
      const k = IN ? ease(lean.t / IN) : 1;
      const P = leanPose(1);
      if (lean.t >= IN) { lean.phase = 'hold'; lean.t = 0; if (!auto) auto = { t: 0, k: 0 }; }
      lean.cur = P.target.clone();
      return { pos: lean.from.pos.clone().lerp(P.pos, k), target: lean.from.target.clone().lerp(P.target, k), fov: THREE.MathUtils.lerp(lean.from.fov, P.fov, k) };
    }
    if (lean.phase === 'hold') {
      const P = leanPose(1);
      lean.cur.lerp(P.target, Math.min(1, dt * 2.2));
      if (!auto && lean.t > 0.2) { lean.done = (lean.done || 0) + dt; if (lean.done > (motion.reduced ? 0.8 : 1.8)) leanOut(); }
      return { pos: P.pos, target: lean.cur.clone(), fov: P.fov };
    }
    if (lean.phase === 'out') {
      const k = OUT ? ease(lean.t / OUT) : 1;
      if (lean.t >= OUT) { const b = lean.back; leanEnd(); rig.release(b, { cut: true }); return { pos: b.pos, target: b.target }; }
      return { pos: lean.at.pos.clone().lerp(lean.back.pos, k), target: lean.at.target.clone().lerp(lean.back.target, k), fov: THREE.MathUtils.lerp(lean.at.fov, lean.from.fov, k) };
    }
    return null;
  }
  function leanOut() {
    if (!lean || lean.phase === 'out') return;
    lean.at = { pos: camera.position.clone(), target: lean.cur ? lean.cur.clone() : rig.controls.target.clone(), fov: camera.fov };
    lean.back = stopView();
    lean.phase = 'out'; lean.t = 0;
  }
  function leanEnd() { lean = null; onDrive?.(false); }
  function play() {
    if (auto || lean) { stop(); return; }
    idle = 0;
    if (!place || !stopView || !onDrive) { auto = { t: 0, k: 0 }; return; }
    lean = { phase: 'in', t: 0, from: { pos: camera.position.clone(), target: rig.controls.target.clone(), fov: camera.fov } };
    rig.drive('harmonica', leanFn, { onCancel: () => { auto = null; if (lean) leanEnd(); } });
    onDrive(true, 'harmonica');
    lean.startedAt = performance.now();
    if (motion.reduced) leanFn(0);
  }
  /** Escape, Step back or a tap: the phrase stops and the camera eases back. */
  function stop() {
    auto = null;
    if (lean) leanOut();
  }

  /** A click on a bauble (or its button in the goods list): ring it, unless the brush already did. */
  function click(item) {
    const B = baubles.find((b) => b.item === item);
    if (!B) return false;
    if (B.gestureAt && performance.now() - B.gestureAt < 700) return true;
    strike(B, { velocity: 0.55, source: 'click' });
    return true;
  }

  const qA = new THREE.Quaternion(), qB = new THREE.Quaternion();
  return {
    baubles,
    claim,
    click,
    play,
    strike: (i, o) => baubles[i] && strike(baubles[i], o),
    get playing() { return !!auto; },
    get leaning() { return lean ? lean.phase : null; },
    stop,
    /** Where the brush is: a pointer on the row. */
    get brushing() { return !!claimed; },
    update(dt, t, { here, still }) {
      T += dt;
      if (auto) {
        auto.t += dt;
        const beat = 60 / TEMPO;
        while (auto && auto.k < baubles.length && auto.t >= ONSETS[auto.k] * beat) {
          strike(baubles[auto.k], { velocity: auto.k === 0 || auto.k === 3 || auto.k === 9 ? 0.7 : 0.5, dir: 1, source: 'auto' });
          auto.k++;
        }
        if (auto && auto.k >= baubles.length) auto = null;
      }
      if (here && !claimed && !auto) idle += dt; else idle = 0;
      const hintOn = here && idle > IDLE_HINT;
      if (ripple >= 0) ripple += dt;
      const w = 2 * Math.PI * 1.25, z = 0.07; // a bauble on a 16 cm ribbon swings at about 1.25 Hz, and keeps on a while
      for (const B of baubles) {
        // glow: the note's, the hint's, and the answering ripple when the tune is played through
        B.glow *= Math.exp(-dt / 1.3);
        const wantHint = hintOn && B.i === expect ? 0.22 + 0.12 * Math.sin((idle - IDLE_HINT) * 2.6) : 0;
        B.hint += (wantHint - B.hint) * Math.min(1, dt * 3);
        let rip = 0;
        if (ripple >= 0) { const x = ripple * 6 - B.i; rip = x > 0 && x < 3 ? Math.sin((x / 3) * Math.PI) * 0.5 : 0; }
        const g = Math.min(1.4, B.glow + B.hint + rip);
        for (const m of B.mats) m.emissiveIntensity = g * 4.2;
        B.sp.visible = g > 0.01;
        B.sp.material.opacity = Math.min(1, g * 1.25);
        // swing: a damped pendulum on each axis
        if (!still && !motion.reduced) {
          B.va += (-w * w * B.a - 2 * z * w * B.va) * dt; B.a += B.va * dt;
          B.vb += (-w * w * B.b - 2 * z * w * B.vb) * dt; B.b += B.vb * dt;
          B.a = THREE.MathUtils.clamp(B.a, -0.35, 0.35); B.b = THREE.MathUtils.clamp(B.b, -0.3, 0.3);
        } else { B.a = B.b = B.va = B.vb = 0; }
        if (Math.abs(B.a) + Math.abs(B.b) > 1e-5 || B.swinging) {
          B.swinging = Math.abs(B.a) + Math.abs(B.b) > 1e-5;
          B.node.quaternion.copy(B.q0).premultiply(qA.setFromAxisAngle(B.axA, B.a)).premultiply(qB.setFromAxisAngle(B.axB, B.b));
        }
      }
      if (ripple > 4) ripple = -1;
    },
    stats: () => ({
      notes: baubles.map((b) => b.note),
      names: baubles.map((b) => b.node.name),
      log: log.slice(),
      glow: baubles.map((b) => +(b.glow + b.hint).toFixed(3)),
      swing: baubles.map((b) => +Math.hypot(b.a, b.b).toFixed(4)),
      hint: baubles.find((b) => b.hint > 0.05)?.i ?? null,
      expect, idle: +idle.toFixed(2), playing: !!auto, brushing: !!claimed, lean: lean ? lean.phase : null,
    }),
    /** Screen points of the baubles (tests aim a brush with them). */
    points: () => { const { pts, rect } = screen(); return pts.map((p) => ({ i: p.B.i, x: +(p.x + rect.left).toFixed(1), y: +(p.y + rect.top).toFixed(1), r: +p.rpx.toFixed(1), front: p.front })); },
    reset() { expect = 0; idle = 0; auto = null; if (lean) leanOut(); },
  };
}
