// Falling snow, animated entirely on the GPU. Three layers of flakes in boxes that wrap around the
// camera: big soft flakes close by (out of focus), a mid layer, and fine flakes far out that fade
// into the fog. Wind drifts every flake with slow gusts; each flake also flutters on its own.
import * as THREE from 'three';

const vertexShader = /* glsl */ `
attribute vec4 aSeed;
uniform float uTime, uBox, uHeight, uScale, uFall, uFlutter, uSizeMin, uSizeMax, uSoft;
uniform vec2 uWind;
uniform vec3 uCam;
uniform vec4 uWarmPos[4];   // xyz, intensity
uniform vec3 uWarmColor;
varying vec3 vLight;
varying float vAlpha;
varying float vSoft;
varying float vSeed;
void main() {
  // each flake: a random spot in the box, falling at its own speed, drifting with the wind
  float speed = uFall * (0.6 + 0.8 * aSeed.w);
  vec3 p = position * vec3(uBox, uHeight, uBox);
  p.y -= uTime * speed;
  p.xz += uWind * (0.75 + 0.5 * aSeed.z);
  float ph = aSeed.x * 6.2831;
  p.x += sin(uTime * (0.7 + aSeed.y) + ph) * uFlutter;
  p.z += cos(uTime * (0.5 + aSeed.z) + ph * 1.3) * uFlutter;
  // wrap: horizontally around the camera, vertically between the ground and uHeight
  vec2 o = uCam.xz - 0.5 * uBox;
  p.xz = mod(p.xz - o, uBox) + o;
  float oy = max(uCam.y - 0.5 * uHeight, 0.0);
  p.y = mod(p.y - oy, uHeight) + oy;

  // flakes drifting past a stall light catch it
  vec3 warm = vec3(0.0);
  for (int i = 0; i < 4; i++) {
    vec3 dl = uWarmPos[i].xyz - p;
    warm += uWarmPos[i].w / (dot(dl, dl) + 0.6);
  }
  vLight = uWarmColor * warm;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float z = max(-mv.z, 0.05);
  float size = mix(uSizeMin, uSizeMax, aSeed.y);
  float px = size * uScale / z;
  // near flakes grow a little extra (out of focus), dust-sized ones keep their coverage as alpha
  px *= 1.0 + uSoft * smoothstep(3.0, 0.4, z) * 1.5;
  gl_PointSize = clamp(px, 1.0, 64.0);
  float cover = clamp(px, 0.0, 1.0);
  // fade at the box edge so the wrap is invisible, and near the camera plane
  vec2 e = abs(p.xz - uCam.xz) / (0.5 * uBox);
  float edge = 1.0 - smoothstep(0.75, 1.0, max(e.x, e.y));
  float nearFade = smoothstep(0.25, 0.8, z);
  float topFade = smoothstep(0.0, 2.0, oy + uHeight - p.y);
  vAlpha = cover * cover * edge * nearFade * topFade * (0.55 + 0.45 * aSeed.z);
  vSoft = uSoft * smoothstep(4.0, 0.6, z);
  vSeed = aSeed.x;
}`;

const fragmentShader = /* glsl */ `
uniform vec3 uColor, uFogColor;
varying vec3 vLight;
uniform float uOpacity, uFogDensity;
varying float vAlpha;
varying float vSoft;
varying float vSeed;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float r = length(c) * 2.0;
  // crisp small flakes, soft large out-of-focus ones
  float a = 1.0 - smoothstep(0.55 - 0.45 * vSoft, 1.0, r);
  a *= mix(1.0, a, vSoft);
  if (a < 0.01) discard;
  float fogD = uFogDensity * gl_FragCoord.z / gl_FragCoord.w;
  float fog = 1.0 - exp(-fogD * fogD);
  vec3 col = mix(uColor * (0.8 + 0.4 * vSeed) + vLight, uFogColor, fog);
  gl_FragColor = vec4(col, a * vAlpha * uOpacity * (1.0 - 0.55 * vSoft));
}`;

export function createSnow({ layers, camera, renderer }) {
  const group = new THREE.Group();
  group.name = 'lighting_snow';
  const shared = {
    uTime: { value: 0 },
    uWind: { value: new THREE.Vector2() },
    uCam: { value: new THREE.Vector3() },
    uScale: { value: 400 },
    uOpacity: { value: 0 },
    uColor: { value: new THREE.Color(0.66, 0.74, 0.95) },
    uFogColor: { value: new THREE.Color() },
    uFogDensity: { value: 0.02 },
    uFall: { value: 0.85 },
    uWarmPos: { value: [0, 1, 2, 3].map(() => new THREE.Vector4(0, -100, 0, 0)) },
    uWarmColor: { value: new THREE.Color(1.0, 0.62, 0.32) },
  };
  let s = 17;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const mats = [];
  for (const L of layers) {
    const pos = new Float32Array(L.count * 3);
    const seed = new Float32Array(L.count * 4);
    for (let i = 0; i < L.count; i++) {
      pos[i * 3] = R(); pos[i * 3 + 1] = R(); pos[i * 3 + 2] = R();
      seed[i * 4] = R(); seed[i * 4 + 1] = R(); seed[i * 4 + 2] = R(); seed[i * 4 + 3] = R();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
    const mat = new THREE.ShaderMaterial({
      name: 'lighting_snow',
      uniforms: {
        ...shared,
        uBox: { value: L.box },
        uHeight: { value: Math.max(14, L.box * 0.45) },
        uSizeMin: { value: L.size[0] },
        uSizeMax: { value: L.size[1] },
        uSoft: { value: L.soft },
        uFlutter: { value: 0.12 + 0.1 * L.soft },
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      fog: false,
    });
    mats.push(mat);
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    pts.renderOrder = 10;
    pts.raycast = () => {};
    group.add(pts);
  }
  group.visible = false;

  const size = new THREE.Vector2();
  return {
    group,
    uniforms: shared,
    materials: mats,
    /** t: scene time (frozen under reduced motion), wind: current wind (m/s), windOffset integrated by the caller. */
    /** Up to 4 warm lights near the camera light the flakes: [{ position: Vector3, intensity }]. */
    setWarmLights(list) {
      shared.uWarmPos.value.forEach((v, i) => {
        const L = list[i];
        if (L) v.set(L.position.x, L.position.y, L.position.z, L.intensity); else v.set(0, -100, 0, 0);
      });
    },
    update({ t, windOffset, fog, opacity }) {
      shared.uTime.value = t;
      shared.uWind.value.copy(windOffset);
      camera.getWorldPosition(shared.uCam.value);
      renderer.getDrawingBufferSize(size);
      const fov = THREE.MathUtils.degToRad(camera.fov || 50);
      shared.uScale.value = size.y / (2 * Math.tan(fov / 2));
      shared.uOpacity.value = opacity;
      if (fog) { shared.uFogColor.value.copy(fog.color); shared.uFogDensity.value = fog.density ?? 0.02; }
      group.visible = opacity > 0.002;
    },
    dispose() {
      group.children.forEach((p) => p.geometry.dispose());
      mats.forEach((m) => m.dispose());
      group.removeFromParent();
    },
  };
}
