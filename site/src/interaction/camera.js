// Camera: orbit controls, smooth flights to places (instant with reduced motion), rides, keyboard orbit.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export function createCameraRig({ camera, dom, home, motion }) {
  const HOME = { pos: new THREE.Vector3().fromArray(home.position), target: new THREE.Vector3().fromArray(home.target) };
  camera.position.copy(HOME.pos);
  const controls = new OrbitControls(camera, dom);
  controls.target.copy(HOME.target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.minDistance = 3;
  controls.maxDistance = 62;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minPolarAngle = 0.3;
  controls.screenSpacePanning = false;
  controls.autoRotateSpeed = 0.25;
  controls.autoRotate = !motion.reduced;
  let flight = null;
  let ride = null;
  controls.addEventListener('start', () => { controls.autoRotate = false; flight = null; });

  const ease = (t) => (t < 0.5 ? 4 * t ** 3 : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const tmp = new THREE.Vector3();

  const rig = {
    controls,
    home: HOME,
    get riding() { return ride; },
    flyTo(view) {
      const v = view || HOME;
      controls.autoRotate = false;
      controls.enabled = true;
      controls.minDistance = v.near ?? 3; // an item close-up may come nearer than a stall view
      ride = null;
      flight = { t: motion.reduced ? 1 : 0, fromP: camera.position.clone(), fromT: controls.target.clone(), toP: v.pos.clone(), toT: v.target.clone() };
      if (motion.reduced) rig.update(0);
    },
    /** Follow a moving pose: poseFn() -> { pos, look }. */
    startRide(type, poseFn) {
      flight = null;
      controls.enabled = false;
      controls.autoRotate = false;
      ride = { type, poseFn, ease: 0 };
    },
    endRide(view) {
      if (!ride) return;
      ride = null;
      controls.enabled = true;
      if (view) {
        controls.target.copy(view.target);
        flight = { t: motion.reduced ? 1 : 0, fromP: camera.position.clone(), fromT: view.target.clone(), toP: view.pos.clone(), toT: view.target.clone() };
      }
    },
    /** Keyboard orbit and zoom around the current target. */
    nudge(dAzimuth, dZoom) {
      controls.autoRotate = false;
      flight = null;
      const off = tmp.copy(camera.position).sub(controls.target);
      const sph = new THREE.Spherical().setFromVector3(off);
      sph.theta += dAzimuth;
      sph.radius = THREE.MathUtils.clamp(sph.radius * (1 + dZoom), controls.minDistance, controls.maxDistance);
      camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(sph));
      controls.update();
    },
    setReduced(r) {
      if (r) controls.autoRotate = false;
    },
    update(dt) {
      if (flight) {
        flight.t = Math.min(1, flight.t + dt / 1.6);
        const e = ease(flight.t);
        camera.position.lerpVectors(flight.fromP, flight.toP, e);
        controls.target.lerpVectors(flight.fromT, flight.toT, e);
        if (flight.t >= 1) flight = null;
      }
      if (ride) {
        ride.ease = Math.min(1, ride.ease + dt * (motion.reduced ? 10 : 0.7));
        const pose = ride.poseFn();
        camera.position.lerp(pose.pos, ride.ease);
        camera.lookAt(pose.look);
      } else controls.update();
    },
  };
  return rig;
}
