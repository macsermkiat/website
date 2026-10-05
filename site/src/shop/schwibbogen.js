// The hero moment (round 9, ADR 0004 revision): the Schwibbogen wakes the town.
// A click on the candle arch (act_orn_schwibbogen, flames act_orn_candle_0..6) and the camera comes round the arch
// to stand behind it, looking out over its candles at the market. The candles light one by one from the outside in
// (the vendor's items.json `order`), each with a small flare, a soft flicker and its own small glow. With every
// flame a share of the old town's dark windows turns warm, spreading outward from the market, and one more voice
// joins a low warm chord (G minor, the ballad's key). After the last flame a slow wave of light runs out across the
// market from the shop: the stall bulbs and lamps brighten in turn by their distance, the bloom swells and
// settles. A tap or Escape steps back; the candles keep burning. A click on the arch again lets it all fade back.
// Reduced motion: a cut to the view, the candles light quickly with no flicker, and the light rises gently
// everywhere at once instead of travelling.
import * as THREE from 'three';
import { createChord } from '../audio/glass.js';

const UP = new THREE.Vector3(0, 1, 0);
const EYE = 0.035; // the eye above the candle tips, behind the arch
const GAP = 0.72; // seconds between flames
const OUT_GAP = 0.22;

let glowTex = null;
function flameGlow() {
  if (glowTex) return glowTex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 34, 0, 32, 34, 32);
  gr.addColorStop(0, 'rgba(255,230,170,1)'); gr.addColorStop(0.18, 'rgba(255,180,90,0.55)'); gr.addColorStop(0.5, 'rgba(255,130,40,0.14)'); gr.addColorStop(1, 'rgba(255,100,20,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  glowTex = new THREE.CanvasTexture(c);
  glowTex.colorSpace = THREE.SRGBColorSpace;
  return glowTex;
}

const smooth = (x) => { const k = THREE.MathUtils.clamp(x, 0, 1); return k * k * (3 - 2 * k); };
const easeInOut = (x) => { const k = THREE.MathUtils.clamp(x, 0, 1); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };

export function createSchwibbogen({ place, arch, candles, town, wave, rig, camera, motion, sfx, announce, stopView, onDrive, stepOut }) {
  const chord = createChord();
  // the candles in the order they light: the vendor's `order` (0 outermost), left before right
  const C = candles.map((item, i) => {
    const node = item.node;
    node.userData.live = true;
    const order = Number(item.info?.order ?? node.userData?.item?.order);
    const flame = [];
    node.traverse((o) => { if (o.isMesh && !o.userData.itemFx) flame.push(o); });
    // each flame its own material, so it can flare and flicker on its own
    for (const m of flame) {
      const src = Array.isArray(m.material) ? m.material[0] : m.material;
      const c = src.clone();
      delete c.userData.fromGlb;
      c.name = `${src.name || 'flame'}_candle_${i}`;
      if (!c.emissive || c.emissive.getHex() === 0) c.emissive = new THREE.Color(1, 0.62, 0.25);
      c.userData.base = Math.max(1.5, src.emissiveIntensity || 2.5);
      m.material = c;
    }
    const box = new THREE.Box3().setFromObject(node);
    const size = box.getSize(new THREE.Vector3());
    const tip = node.worldToLocal(box.getCenter(new THREE.Vector3()));
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: flameGlow(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
    sp.name = `engine_candle_glow_${i}`;
    sp.userData.itemFx = true;
    sp.position.copy(tip);
    const ws = node.getWorldScale(new THREE.Vector3()).x || 1;
    sp.scale.setScalar(Math.max(0.07, size.y * 3.2) / ws);
    sp.visible = false;
    node.add(sp);
    node.visible = false;
    return { item, node, flame, sp, i, order: Number.isFinite(order) ? order : Math.min(i, candles.length - 1 - i), k: 0, want: 0, lit: false, ph: i * 2.17, s0: node.scale.clone() };
  });
  const seq = C.slice().sort((a, b) => a.order - b.order || a.i - b.i); // outside in
  let phase = 'off', t = 0, nextFlame = 0, litOrder = [];
  let wake = 0, wakeWant = 0;
  let cam = null; // { phase: 'in'|'hold'|'out', t, from, path }
  let waved = false;

  // ---------- geometry of the view ----------
  function frame() {
    const A = arch.node.getWorldPosition(new THREE.Vector3());
    // the height of the candle tips (the arch's own meshes, not the glow sprites round the flames)
    const box = new THREE.Box3();
    arch.node.updateWorldMatrix(true, true);
    arch.node.traverse((o) => { if (o.isMesh && !o.userData.itemFx) box.expandByObject(o); });
    const h = THREE.MathUtils.clamp(box.isEmpty() ? 0.3 : box.max.y - A.y, 0.12, 0.8);
    const F = new THREE.Vector3(0, 0, 1).transformDirection(place.holder.matrixWorld).setY(0).normalize(); // the shop's front
    const X = new THREE.Vector3(1, 0, 0).transformDirection(place.holder.matrixWorld).setY(0).normalize(); // the visitor's right
    // round the arch on the side away from the shop's middle (the vendor stands there)
    const side = X.dot(new THREE.Vector3().subVectors(A, place.holder.position)) < 0 ? -1 : 1;
    const look = A.clone().addScaledVector(UP, h * 0.55);
    const out = A.clone().addScaledVector(F, 14).addScaledVector(UP, h + EYE + 1.0);
    return { A, F, X, side, h, look, out };
  }
  /** The camera on its way round the arch: u 0 (in front) .. 1 (behind, looking out over the candles). */
  function orbit(G, u) {
    const th = Math.PI * easeInOut(u);
    const rho = THREE.MathUtils.lerp(0.95, 0.5, u);
    // behind the arch the eye sits just above the candle tips: the flames stand along the lower third, the market
    // and the town fill the rest
    const lift = THREE.MathUtils.lerp(0.62, G.h + EYE, u) + Math.sin(th) * 0.14;
    const pos = G.A.clone().addScaledVector(G.F, Math.cos(th) * rho).addScaledVector(G.X, G.side * Math.sin(th) * rho).addScaledVector(UP, lift);
    return pos;
  }
  function holdPose(G, k) {
    // behind the arch, a touch to its outer side; through the wave the camera rises a little to see further
    const pos = orbit(G, 1).addScaledVector(UP, 0.12 * k).addScaledVector(G.F, -0.1 * k);
    const target = G.out.clone().addScaledVector(UP, 0.35 * k);
    return { pos, target };
  }

  const _t = new THREE.Vector3();
  function poseFn(dt) {
    if (!cam) return null;
    cam.t += dt;
    const G = cam.G;
    if (cam.phase === 'in') {
      // glide from the stop to the front of the arch (1.2 s), round it (2.4 s), then lift the eyes to the market (1 s)
      const T1 = 1.2, T2 = 2.4, T3 = 1.0;
      const t1 = cam.t;
      if (t1 < T1) {
        const k = easeInOut(t1 / T1);
        const pos = cam.from.pos.clone().lerp(orbit(G, 0), k);
        const target = cam.from.target.clone().lerp(G.look, k);
        return { pos, target };
      }
      if (t1 < T1 + T2) return { pos: orbit(G, (t1 - T1) / T2), target: G.look };
      const k = easeInOut((t1 - T1 - T2) / T3);
      const H = holdPose(G, 0);
      if (k >= 1) { cam.phase = 'hold'; cam.t = 0; }
      return { pos: H.pos, target: _t.copy(G.look).lerp(H.target, k).clone() };
    }
    if (cam.phase === 'hold') {
      const k = waved ? smooth(cam.rise / 7) : 0;
      if (waved) cam.rise = Math.min(7, (cam.rise || 0) + dt);
      return holdPose(G, k);
    }
    if (cam.phase === 'out') {
      // the way back: eyes down to the arch, round it to the front, and out to the stop
      const T1 = 0.9, T2 = 2.0, T3 = 1.2;
      const t1 = cam.t;
      const H = holdPose(G, cam.k0);
      if (t1 < T1) { const k = easeInOut(t1 / T1); return { pos: H.pos.clone().lerp(orbit(G, 1), k), target: H.target.clone().lerp(G.look, k) }; }
      if (t1 < T1 + T2) return { pos: orbit(G, 1 - (t1 - T1) / T2), target: G.look };
      const k = easeInOut((t1 - T1 - T2) / T3);
      const v = cam.back;
      if (k >= 1) { const b = cam.back; cam = null; rig.release(b, { cut: true }); onDrive?.(false); stepOut?.(false); return { pos: b.pos, target: b.target }; }
      return { pos: orbit(G, 0).lerp(v.pos, k), target: G.look.clone().lerp(v.target, k) };
    }
    return null;
  }

  function startCamera() {
    const G = frame();
    cam = { phase: 'in', t: 0, G, from: { pos: camera.position.clone(), target: rig.controls.target.clone() }, rise: 0 };
    rig.drive('schwibbogen', poseFn, { near: 0.05, onCancel: () => { cam = null; onDrive?.(false); stepOut?.(false); } });
    stepOut?.(true);
    onDrive?.(true, 'schwibbogen');
    if (motion.reduced) { cam.phase = 'hold'; cam.t = 0; }
  }

  /** Step back from the view over the arch to the stop (the candles keep burning). */
  function stepBack() {
    if (!cam) return false;
    const back = stopView();
    if (motion.reduced || cam.phase === 'in' && cam.t < 0.3) {
      cam = null; rig.release(back, { cut: motion.reduced }); onDrive?.(false); stepOut?.(false);
      return true;
    }
    if (cam.phase === 'out') return true;
    cam.k0 = waved ? smooth((cam.rise || 0) / 7) : 0;
    cam.phase = 'out'; cam.t = 0; cam.back = back;
    return true;
  }

  // ---------- the candles ----------
  function light(c) {
    c.lit = true; c.want = 1; c.node.visible = true; c.sp.visible = true;
    litOrder.push(c.node.name);
    sfx('match');
    chord.add(litOrder.length - 1);
    wakeWant = Math.min(1.06, (litOrder.length / seq.length) * 1.06);
  }

  function wakeUp() {
    town.check();
    for (const c of C) { c.lit = false; c.want = 0; }
    phase = 'waking'; t = 0; litOrder = []; waved = false;
    nextFlame = motion.reduced ? 0.2 : 2.9; // the first flame as the camera comes round behind the arch
    startCamera();
    announce?.('The Schwibbogen: its seven candles light one by one, and the old town wakes.');
  }

  function sleep() {
    phase = 'sleeping'; t = 0;
    wakeWant = 0;
    chord.release(3.5);
    wave.fade();
    sfx('puff');
    announce?.('The candles go out, and the town settles back to sleep.');
  }

  return {
    get phase() { return phase; },
    get driving() { return !!cam; },
    /** A click on the arch (or a candle, or the stop bar's button). */
    toggle() {
      if (phase === 'off') wakeUp();
      else if (phase === 'sleeping') wakeUp();
      else { sleep(); if (cam) stepBack(); }
    },
    stepBack,
    update(dt, T, still) {
      t += dt;
      if (phase === 'waking') {
        while (seq.some((c) => !c.lit) && t >= nextFlame) {
          light(seq.find((c) => !c.lit));
          nextFlame += motion.reduced ? 0.25 : GAP;
        }
        if (!seq.some((c) => !c.lit) && !waved && t >= nextFlame - (motion.reduced ? 0 : GAP) + (motion.reduced ? 0.3 : 0.9)) {
          waved = true;
          // the wave leaves from the arch, out across the market
          wave.start(arch.node.getWorldPosition(new THREE.Vector3()));
          chord.swell(motion.reduced ? 2.5 : 4.5);
          phase = 'lit';
        }
      } else if (phase === 'sleeping') {
        // out from the middle, quickly
        const lit = seq.filter((c) => c.lit).reverse();
        if (lit.length && t >= (seq.length - lit.length) * OUT_GAP) { const c = lit[0]; c.lit = false; c.want = 0; }
        if (!seq.some((c) => c.lit) && C.every((c) => c.k < 0.01)) phase = 'off';
      }
      // the windows follow the flames, a little behind (and go out far ones first)
      const rate = phase === 'sleeping' ? 0.35 : motion.reduced ? 2.5 : 0.9;
      wake += THREE.MathUtils.clamp(wakeWant - wake, -rate * dt, rate * dt);
      town.wake = wake;
      // the flames: a flare as they catch, then a soft flicker; out with a small shrink
      for (const c of C) {
        const was = c.k;
        c.k += (c.want - c.k) * Math.min(1, dt * (c.want ? 4 : 7));
        if (motion.reduced) c.k = c.want ? Math.min(1, was + dt * 6) : 0;
        const on = c.k > 0.01;
        c.node.visible = on; c.sp.visible = on;
        if (!on) continue;
        const flare = c.want && c.k < 0.98 ? 1 + 0.5 * Math.sin(c.k * Math.PI) : 1;
        const fl = still || motion.reduced ? 1 : 1 + 0.07 * Math.sin(T * 13.1 + c.ph) + 0.05 * Math.sin(T * 7.3 + c.ph * 1.7) + 0.03 * Math.sin(T * 29 + c.ph * 0.3);
        const sy = c.k * fl * flare, sx = c.k * (2 - fl) * Math.min(1.2, flare);
        c.node.scale.set(c.s0.x * sx, c.s0.y * sy, c.s0.z * sx);
        for (const m of c.flame) m.material.emissiveIntensity = m.material.userData.base * c.k * fl * flare;
        c.sp.material.opacity = Math.min(1, 0.75 * c.k * fl * flare);
      }
    },
    stats: () => ({
      phase,
      lit: litOrder.slice(),
      burning: C.filter((c) => c.lit).length,
      of: C.length,
      order: seq.map((c) => c.node.name),
      wake: +wake.toFixed(3),
      windows: town.stats(),
      chord: chord.voices,
      wave: wave.stats(),
      cam: cam ? cam.phase : null,
    }),
  };
}
