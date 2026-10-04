// The camera: a guided stroll, not a free orbit (docs/adr/0003-guided-stroll-navigation.md).
//
//   home   one composed view of the square that drifts slowly (still with reduced motion)
//   walk   along a lane path to a stop, at walking pace with a gentle ease, looking ahead, then at the stop
//   stop   resting at a view; the visitor may turn the head about ±15° and zoom a little, nothing more
//   fly    a short direct move (an item close-up, a reading view, back to the stop)
//   ride   following a gondola or a horse
// Reduced motion: every move is a cut.
//
// `rig.controls` keeps the small part of OrbitControls' shape the rest of the market reads: its `target` (where
// the camera looks; the crowd steps out of that line) and `minDistance`.
import * as THREE from 'three';

export const LOOK_YAW = THREE.MathUtils.degToRad(15);
export const LOOK_PITCH = THREE.MathUtils.degToRad(9);
export const ZOOM_BAND = [0.82, 1.12]; // fraction of the stop's distance to its target
const WALK_SPEED = 3.2; // m/s: an unhurried walk, a little brisker than real
const WALK_MIN = 2.2, WALK_MAX = 9; // seconds

const smooth = (t) => t * t * (3 - 2 * t);
const ease = (t) => (t < 0.5 ? 4 * t ** 3 : 1 - Math.pow(-2 * t + 2, 3) / 2);
/** A walk's ease: gentle start and stop, steady in the middle. */
const walkEase = (t) => { const a = 0.22; if (t < a) return (t * t) / (2 * a * (1 - a)); if (t > 1 - a) return 1 - ((1 - t) ** 2) / (2 * a * (1 - a)); return (t - a / 2) / (1 - a); };

export function createCameraRig({ camera, dom, home, motion }) {
  const HOME = { pos: new THREE.Vector3().fromArray(home.position), target: new THREE.Vector3().fromArray(home.target) };
  // the resting view (home or a stop) and the visitor's small look-around on top of it
  const rest = { pos: HOME.pos.clone(), target: HOME.target.clone() };
  const look = { yaw: 0, pitch: 0, zoom: 1, wantYaw: 0, wantPitch: 0, wantZoom: 1 };
  const controls = { target: HOME.target.clone(), minDistance: 0.5, enabled: true };
  let mode = 'home';
  let move = null; // walk or fly in progress
  let ride = null;
  let T = 0, idle = 0;
  const listeners = { arrive: [] };
  camera.position.copy(HOME.pos);
  camera.lookAt(HOME.target);

  function cancelLook() { look.wantYaw = look.wantPitch = 0; look.wantZoom = 1; }

  /** Start a move along `points` (Vector3[], camera positions) to `view`. Direct when points has two entries. */
  function start(kind, points, view, { onArrive, duration } = {}) {
    if (ride) { camera.near = 0.1; camera.updateProjectionMatrix(); ride = null; }
    const fromT = controls.target.clone();
    const pts = points.map((p) => p.clone());
    const curve = pts.length > 2 ? new THREE.CatmullRomCurve3(pts, false, 'centripetal', 0.5) : null;
    const len = curve ? curve.getLength() : pts[0].distanceTo(pts[1]);
    const dur = duration ?? (kind === 'walk' ? THREE.MathUtils.clamp(len / WALK_SPEED, WALK_MIN, WALK_MAX) : THREE.MathUtils.clamp(0.9 + len * 0.18, 1.0, 1.8));
    move = { kind, curve, from: pts[0], to: pts[pts.length - 1], fromT, toT: view.target.clone(), t: 0, dur, onArrive, len };
    mode = kind;
    cancelLook();
    look.yaw = look.pitch = 0; look.zoom = 1;
    rest.pos.copy(view.pos);
    rest.target.copy(view.target);
    controls.minDistance = view.near ?? 0.5;
    if (motion.reduced || dur <= 0) finish();
  }
  function finish() {
    const m = move;
    move = null;
    mode = rest.home ? 'home' : 'stop';
    camera.position.copy(rest.pos);
    controls.target.copy(rest.target);
    camera.lookAt(controls.target);
    m?.onArrive?.();
    listeners.arrive.forEach((f) => f(m?.kind));
  }

  const _p = new THREE.Vector3(), _t = new THREE.Vector3(), _a = new THREE.Vector3(), _d = new THREE.Vector3();

  const rig = {
    controls,
    home: HOME,
    get mode() { return mode; },
    get moving() { return !!move; },
    get riding() { return ride; },
    get rest() { return { pos: rest.pos.clone(), target: rest.target.clone() }; },
    get look() { return { yaw: look.yaw, pitch: look.pitch, zoom: look.zoom }; },
    get progress() { return move ? { kind: move.kind, t: move.t, dur: move.dur, length: move.len } : null; },
    onArrive(f) { listeners.arrive.push(f); },
    /** Walk the lane path (camera positions) to a stop's view. */
    walkTo(points, view, opts) { rest.home = !!opts?.home; start('walk', points, view, opts); },
    /** A short direct move (null: home). */
    flyTo(view, opts = {}) {
      const v = view || HOME;
      rest.home = !view || !!opts.home;
      start('fly', [camera.position.clone(), v.pos.clone()], v, opts);
    },
    /** Follow a moving pose: poseFn() -> { pos, look }. */
    startRide(type, poseFn, { near = 0.1 } = {}) {
      move = null;
      camera.near = near;
      camera.updateProjectionMatrix();
      mode = 'ride';
      ride = { type, poseFn, ease: 0 };
    },
    endRide(view) {
      if (!ride) return;
      ride = null;
      camera.near = 0.1;
      camera.updateProjectionMatrix();
      mode = 'stop';
      if (view) { controls.target.copy(view.target); start('fly', [camera.position.clone(), view.pos.clone()], view); }
    },
    /** Turn the head (radians) and zoom (fraction) within the stop's small band. */
    nudge(dYaw, dZoom = 0, dPitch = 0) {
      if (mode !== 'stop' && mode !== 'home') return;
      idle = 0;
      look.wantYaw = THREE.MathUtils.clamp(look.wantYaw + dYaw, -LOOK_YAW, LOOK_YAW);
      look.wantPitch = THREE.MathUtils.clamp(look.wantPitch + dPitch, -LOOK_PITCH, LOOK_PITCH);
      look.wantZoom = THREE.MathUtils.clamp(look.wantZoom * (1 + dZoom), ZOOM_BAND[0], ZOOM_BAND[1]);
      if (motion.reduced) { look.yaw = look.wantYaw; look.pitch = look.wantPitch; look.zoom = look.wantZoom; }
    },
    setReduced() {},
    update(dt) {
      T += dt;
      idle += dt;
      if (ride) {
        ride.ease = Math.min(1, ride.ease + dt * (motion.reduced ? 10 : 0.7));
        const pose = ride.poseFn();
        camera.position.lerp(pose.pos, ride.ease);
        camera.lookAt(pose.look);
        controls.target.copy(pose.look);
        return;
      }
      if (move) {
        move.t = Math.min(1, move.t + dt / move.dur);
        if (move.kind === 'walk' && move.curve) {
          const u = walkEase(move.t);
          move.curve.getPointAt(u, _p);
          // look ahead along the lane, then settle on the stop's target
          move.curve.getPointAt(Math.min(1, u + 0.07), _a);
          _d.subVectors(_a, _p);
          if (_d.lengthSq() < 1e-6) _d.subVectors(move.toT, _p);
          _d.y = 0;
          _d.normalize();
          // eyes on the way ahead, a little down: from high up (coming down off the home view) the gaze stays on
          // the market rather than the cobbles at one's feet
          const ahead = _a.copy(_p).addScaledVector(_d, 14);
          ahead.y = Math.max(1.2, _p.y - 0.35 * Math.max(0, _p.y - 1.6) - 0.5);
          _t.lerpVectors(move.fromT, ahead, smooth(Math.min(1, move.t / 0.22)));
          _t.lerp(move.toT, smooth(THREE.MathUtils.clamp((move.t - 0.55) / 0.45, 0, 1)));
          camera.position.copy(_p);
          controls.target.copy(_t);
        } else {
          const e = ease(move.t);
          camera.position.lerpVectors(move.from, move.to, e);
          controls.target.lerpVectors(move.fromT, move.toT, e);
        }
        camera.lookAt(controls.target);
        if (move.t >= 1) finish();
        return;
      }
      // resting: home drifts, a stop holds still; either takes the visitor's small look-around
      const k = motion.reduced ? 1 : 1 - Math.exp(-dt * 6);
      look.yaw += (look.wantYaw - look.yaw) * k;
      look.pitch += (look.wantPitch - look.pitch) * k;
      look.zoom += (look.wantZoom - look.zoom) * k;
      _p.copy(rest.pos);
      _t.copy(rest.target);
      if (mode === 'home' && !motion.reduced) {
        // a slow sway, as if standing at the edge of the square, shifting weight
        const a = Math.sin(T * (2 * Math.PI / 46)) * 1.1, b = Math.sin(T * (2 * Math.PI / 31) + 1.3) * 0.25;
        _d.subVectors(_t, _p).setY(0).normalize();
        _p.x += -_d.z * a; _p.z += _d.x * a; _p.y += b;
      }
      // zoom: along the line to the target; look: turn the head about the eye
      _d.subVectors(_p, _t);
      _p.copy(_t).addScaledVector(_d, look.zoom);
      _d.subVectors(_t, _p);
      const dist = _d.length();
      const sph = new THREE.Spherical().setFromVector3(_d);
      sph.theta += look.yaw;
      sph.phi = THREE.MathUtils.clamp(sph.phi - look.pitch, 0.05, Math.PI - 0.05);
      _d.setFromSpherical(sph).setLength(dist);
      camera.position.copy(_p);
      controls.target.copy(_p).add(_d);
      camera.lookAt(controls.target);
    },
  };

  // ---------- pointer: turn the head and zoom, within the band ----------
  let drag = null;
  const pinch = new Map();
  dom.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'touch') pinch.set(e.pointerId, [e.clientX, e.clientY]);
    drag = { x: e.clientX, y: e.clientY, id: e.pointerId };
  });
  dom.addEventListener('pointermove', (e) => {
    if (pinch.has(e.pointerId)) {
      const before = pinchDist();
      pinch.set(e.pointerId, [e.clientX, e.clientY]);
      if (pinch.size === 2 && before) { rig.nudge(0, (before / pinchDist() - 1) * 0.8); return; }
    }
    if (!drag || drag.id !== e.pointerId || !(e.buttons & 1) && e.pointerType !== 'touch') return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY;
    const s = 1.1 / Math.max(300, dom.clientWidth); // a full drag across turns about one look band
    rig.nudge(dx * s, 0, dy * s * 0.7);
  });
  const up = (e) => { pinch.delete(e.pointerId); if (drag?.id === e.pointerId) drag = null; };
  dom.addEventListener('pointerup', up);
  dom.addEventListener('pointercancel', up);
  dom.addEventListener('pointerleave', up);
  dom.addEventListener('wheel', (e) => {
    if (mode !== 'stop' && mode !== 'home') return;
    e.preventDefault();
    rig.nudge(0, Math.sign(e.deltaY) * 0.05);
  }, { passive: false });
  function pinchDist() { const [a, b] = [...pinch.values()]; return a && b ? Math.hypot(a[0] - b[0], a[1] - b[1]) : 0; }

  return rig;
}
