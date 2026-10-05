// The reflection dive (round 9, ADR 0004 revision): a tap on the big mercury-glass ball (act_orn_mirrorball) on its
// forged bracket. At the tap a cube camera renders the market once from the ball's centre (256 px on the lite
// market, 512 on the full one) and the ball's glass takes it, with a clear-coat's Fresnel over the mercury, so the
// lit market curves round it. The camera eases in (cam_dive_approach, then cam_dive, the vendor's empties) until
// the reflection fills the view, the view crossfades into the market seen from inside the glass (a gently warped,
// slightly hushed fisheye with a snow globe's drift; the sound goes muffled, as through glass), holds there, and
// eases back out. Escape or a tap ends it at any point. Reduced motion: no glide (a cut in and a cut out), a short
// hold, and no drift.
import * as THREE from 'three';
import { DivePass } from './divePass.js';
import { setHush } from '../audio/context.js';
import { shimmer } from '../audio/glass.js';

const easeInOut = (x) => { const k = THREE.MathUtils.clamp(x, 0, 1); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };
const UP = new THREE.Vector3(0, 1, 0);
const GAZE_FOV = 36;

export function createDive({ place, ball, scene, camera, renderer, composer, rig, lite, motion, stopView, renderNow, onDrive, announce, dom }) {
  const node = ball.node;
  node.userData.live = true;
  const find = (re) => { let f = null; place.root.traverse((o) => { if (!f && re.test(o.name || '')) f = o; }); return f; };
  const camDive = find(/^cam_dive$/i), camTarget = find(/^cam_dive_target$/i), camApproach = find(/^cam_dive_approach$/i);
  // the glass: the ball's own mesh (its mercury), not the crown
  let glass = null, best = -1;
  node.traverse((o) => {
    if (!o.isMesh || o.userData.itemFx) return;
    const m = Array.isArray(o.material) ? o.material[0] : o.material;
    if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
    const score = (/mercury|glass/i.test(m?.name || '') ? 10 : 0) + o.geometry.boundingSphere.radius;
    if (score > best) { best = score; glass = o; }
  });
  const SIZE = lite ? 256 : 512;
  let cube = null, cubeCam = null, captures = 0;
  let pass = null;
  if (composer?.passes && typeof composer.insertPass === 'function') {
    pass = new DivePass();
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    pass.setSize(size.x, size.y);
    composer.insertPass(pass, Math.max(1, composer.passes.length - 1));
  }

  function centre() {
    if (camTarget) return camTarget.getWorldPosition(new THREE.Vector3());
    const s = new THREE.Box3().setFromObject(glass || node).getBoundingSphere(new THREE.Sphere());
    return s.center;
  }
  function radius() { return new THREE.Box3().setFromObject(glass || node).getBoundingSphere(new THREE.Sphere()).radius; }

  /** The market in the glass: one cube render from the ball's centre, the ball itself hidden. */
  function captureEnv() {
    if (!glass) return false;
    if (!cube) {
      cube = new THREE.WebGLCubeRenderTarget(SIZE, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
      cube.texture.name = 'engine_mirrorball_env';
      cubeCam = new THREE.CubeCamera(0.03, 250, cube);
      const src = Array.isArray(glass.material) ? glass.material[0] : glass.material;
      const tint = (src?.color || new THREE.Color(0.8, 0.78, 0.74)).clone();
      // mercury behind clear glass: a metal mirror, and a clear coat on top whose reflection rises at the rim
      const m = new THREE.MeshPhysicalMaterial({ name: 'engine_mirrorball_glass', color: tint.lerp(new THREE.Color(0.86, 0.84, 0.8), 0.35), metalness: 1, roughness: 0.035, envMap: cube.texture, envMapIntensity: 1.15, clearcoat: 1, clearcoatRoughness: 0.02 });
      glass.material = m;
    }
    const c = centre();
    cubeCam.position.copy(c);
    cubeCam.updateMatrixWorld(true);
    const was = { vis: node.visible, auto: renderer.shadowMap.autoUpdate, rt: renderer.getRenderTarget() };
    node.visible = false;
    renderer.shadowMap.autoUpdate = false;
    try { cubeCam.update(renderer, scene); captures++; } finally {
      renderer.setRenderTarget(was.rt);
      renderer.shadowMap.autoUpdate = was.auto;
      node.visible = was.vis;
    }
    return true;
  }

  // ---------- the camera ----------
  let S = null; // { phase, t, from, curve, ... }
  function poses() {
    const C = centre();
    const r = radius();
    const dive = camDive ? camDive.getWorldPosition(new THREE.Vector3()) : C.clone().add(new THREE.Vector3(0, 0, 1).transformDirection(place.holder.matrixWorld).multiplyScalar(r * 1.7));
    const approach = camApproach ? camApproach.getWorldPosition(new THREE.Vector3()) : C.clone().addScaledVector(dive.clone().sub(C).normalize(), 0.7);
    const out = dive.clone().sub(C).setY(0).normalize(); // from the ball toward the lane and the market
    return { C, r, dive, approach, out };
  }
  function insidePose(P, t) {
    const yaw = motion.reduced ? 0 : 0.09 * Math.sin(t * 0.42) + 0.025 * t;
    const dir = P.out.clone().applyAxisAngle(UP, yaw);
    dir.y = -0.07 + (motion.reduced ? 0 : 0.02 * Math.sin(t * 0.31));
    const pos = P.C.clone().addScaledVector(UP, motion.reduced ? 0 : 0.002 * Math.sin(t * 0.8));
    return { pos, target: pos.clone().addScaledVector(dir.normalize(), 10), fov: 84 };
  }

  const TIMES = motion.reduced ? { approach: 0.01, gaze: 0.3, into: 0.6, inside: 3.0, outof: 0.5, back: 0.01 } : { approach: 2.7, gaze: 0.4, into: 1.5, inside: 5.5, outof: 0.9, back: 2.4 };

  function poseFn(dt) {
    if (!S) return null;
    S.t += dt;
    const P = S.P, T = TIMES;
    if (S.phase === 'approach') {
      const k = easeInOut(S.t / T.approach);
      const pos = S.curve.getPoint(k);
      const target = S.from.target.clone().lerp(P.C, easeInOut(Math.min(1, (S.t / T.approach) * 1.6)));
      if (S.t >= T.approach) go('gaze');
      // the lens narrows a little on the way in, so the ball's reflection fills the frame at the end
      return { pos, target, fov: THREE.MathUtils.lerp(S.from.fov, GAZE_FOV, k) };
    }
    if (S.phase === 'gaze') {
      if (S.t >= T.gaze) go('into');
      return { pos: P.dive, target: P.C, fov: GAZE_FOV };
    }
    if (S.phase === 'into') {
      const k = easeInOut(S.t / T.into);
      if (pass) { pass.uniforms.uMix.value = k; pass.uniforms.uPrevZoom.value = 1 + 0.9 * k; }
      if (S.t >= T.into) go('inside');
      return insidePose(P, S.t);
    }
    if (S.phase === 'inside') {
      if (pass) pass.uniforms.uTime.value += dt;
      if (S.t >= T.inside) go('outof');
      return insidePose(P, T.into + S.t);
    }
    if (S.phase === 'outof') {
      const k = S.t / T.outof;
      if (pass) {
        pass.uniforms.uTime.value += dt;
        // the glass comes across the eye; behind it the view is outside again
        pass.uniforms.uVeil.value = k < 0.5 ? easeInOut(k * 2) : 1 - easeInOut((k - 0.5) * 2);
        if (k >= 0.5 && !S.cut) { S.cut = true; pass.uniforms.uWarp.value = 0; node.visible = true; setHush(0, 1.2); }
      }
      if (S.t >= T.outof) { go('back'); if (!S) return null; } // reduced motion: 'back' is a cut, and the dive is over
      return S.cut ? { pos: P.dive, target: P.C, fov: GAZE_FOV } : insidePose(P, T.into + T.inside + S.t);
    }
    if (S.phase === 'back') {
      const k = easeInOut(S.t / T.back);
      const pos = S.backCurve.getPoint(k);
      const target = P.C.clone().lerp(S.back.target, easeInOut(Math.min(1, (S.t / T.back) * 1.3)));
      if (S.t >= T.back) { const b = S.back; finish(); rig.release(b, { cut: true }); return { pos: b.pos, target: b.target }; }
      return { pos, target, fov: THREE.MathUtils.lerp(GAZE_FOV, S.from.fov, k) };
    }
    return null;
  }

  function go(phase) {
    S.phase = phase; S.t = 0;
    const P = S.P;
    if (phase === 'gaze') return;
    if (phase === 'into') {
      // hold the frame with the reflection filling it, then pass into the glass
      if (pass) {
        pass.enabled = true;
        pass.uniforms.uMix.value = 0; pass.uniforms.uWarp.value = 1; pass.uniforms.uPrevZoom.value = 1; pass.uniforms.uVeil.value = 0;
        pass.uniforms.uFlakes.value = motion.reduced ? 0.35 : 1;
        pass.capture = true;
        try { renderNow(); } catch (e) { console.warn('[shop] dive capture', e); }
      }
      node.visible = false;
      setHush(1, 1.4);
      shimmer();
      announce?.('Inside the mercury-glass ball: the market, curved and hushed. Tap or press Escape to come back out.');
      return;
    }
    if (phase === 'outof') { S.cut = false; return; }
    if (phase === 'back') {
      if (pass) { pass.enabled = false; pass.uniforms.uVeil.value = 0; pass.uniforms.uWarp.value = 0; }
      node.visible = true;
      setHush(0, 1);
      const from = camera.position.clone();
      S.back = stopView();
      S.backCurve = new THREE.CatmullRomCurve3([from, P.approach, S.back.pos], false, 'centripetal');
      if (motion.reduced) { const b = S.back; finish(); rig.release(b, { cut: true }); }
    }
  }

  function finish() {
    S = null;
    if (pass) { pass.enabled = false; pass.uniforms.uVeil.value = 0; }
    node.visible = true;
    setHush(0, 0.8);
    onDrive?.(false);
  }

  function start() {
    if (S) return false;
    captureEnv();
    const P = poses();
    S = { phase: 'approach', t: 0, P, from: { pos: camera.position.clone(), target: rig.controls.target.clone(), fov: camera.fov }, startedAt: performance.now() };
    S.curve = new THREE.CatmullRomCurve3([S.from.pos, P.approach, P.dive], false, 'centripetal');
    rig.drive('dive', poseFn, { near: 0.012, onCancel: () => { if (S) finish(); } });
    onDrive?.(true, 'dive');
    if (motion.reduced) go('into');
    announce?.('The mercury-glass ball: the camera moves in until its reflection fills the view.');
    return true;
  }

  /** Escape or a tap: come back out from wherever the dive is. */
  function end() {
    if (!S) return false;
    if (S.phase === 'approach' || S.phase === 'gaze') {
      go('back');
      return true;
    }
    if (S.phase === 'into' || S.phase === 'inside') { go('outof'); return true; }
    return true;
  }

  // a tap anywhere ends it (not the tap that started it)
  dom.addEventListener('pointerup', (e) => {
    if (!S || performance.now() - S.startedAt < 400) return;
    if (e.button > 0) return;
    end();
  });

  return {
    start, end,
    get active() { return !!S; },
    get phase() { return S?.phase || null; },
    captureEnv,
    resize(w, h) { pass?.setSize(w, h); },
    stats: () => {
      const P = S?.P;
      return {
        phase: S?.phase || null,
        env: cube ? { size: SIZE, captures } : null,
        glass: glass ? (Array.isArray(glass.material) ? glass.material[0] : glass.material).name : null,
        pass: pass ? { enabled: pass.enabled, mix: +pass.uniforms.uMix.value.toFixed(3), warp: pass.uniforms.uWarp.value, veil: +pass.uniforms.uVeil.value.toFixed(3), captures: pass.captures } : null,
        dist: +camera.position.distanceTo(P ? P.C : centre()).toFixed(3),
        radius: +radius().toFixed(3),
        ballVisible: node.visible,
        cams: { dive: !!camDive, target: !!camTarget, approach: !!camApproach },
      };
    },
  };
}
