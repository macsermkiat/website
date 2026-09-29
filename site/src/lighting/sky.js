// The night sky: a gradient dome with procedural stars, a faint Milky Way, thin moonlit clouds,
// a warm glow of light pollution on the horizon and a limb-darkened moon with a soft halo.
// Drawn first, at infinite depth, centred on whichever camera renders it (also the PMREM cube camera).
import * as THREE from 'three';

const vertexShader = /* glsl */ `
varying vec3 vDir;
void main() {
  vDir = position;
  vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  gl_Position = vec4(p.xy, p.w * 0.99999, p.w); // on the far plane
}`;

const fragmentShader = /* glsl */ `
uniform vec3 uZenith, uMid, uHorizon, uGround, uGlow;
uniform vec3 uMoonDir, uMoonColor, uHalo;
uniform float uMoonRadius, uHaloStrength, uStars, uMilky, uClouds, uTime, uOvercast;
uniform vec3 uFogColor;
varying vec3 vDir;

float hash13(vec3 p) { p = fract(p * 0.1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
vec3 hash33(vec3 p) {
  p = fract(p * vec3(0.1031, 0.1030, 0.0973));
  p += dot(p, p.yxz + 33.33);
  return fract((p.xxy + p.yxx) * p.zyx);
}
float hash12(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float noise2(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) { s += a * noise2(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
  return s;
}

// one layer of stars on a grid of cells; each cell may hold one star
vec3 starLayer(vec3 d, float scale, float density, float px, float seed) {
  vec3 p = d * scale;
  vec3 cell = floor(p);
  vec3 h = hash33(cell + seed);
  if (h.x > density) return vec3(0.0);
  vec3 sp = normalize(cell + 0.2 + 0.6 * hash33(cell + seed + 7.0));
  float a = length(cross(d, sp)); // ~ angle for small angles
  if (dot(d, sp) < 0.0) return vec3(0.0);
  float w = px * 0.85;
  float mag = pow(h.y, 14.0) * 5.0 + 0.035 + 0.1 * h.z * h.z;
  float tw = 1.0 + 0.35 * sin(uTime * (1.3 + 3.0 * h.z) + 40.0 * h.y);
  vec3 tint = mix(vec3(0.72, 0.8, 1.0), vec3(1.0, 0.86, 0.68), smoothstep(0.55, 1.0, h.z));
  return tint * mag * tw * exp(-(a * a) / (w * w));
}

void main() {
  vec3 d = normalize(vDir);
  float h = d.y;
  float px = length(fwidth(d)) + 1e-5;

  // gradient
  vec3 col = mix(uHorizon, uMid, smoothstep(0.0, 0.28, h));
  col = mix(col, uZenith, smoothstep(0.22, 0.95, h));
  // overcast (snow) lifts and greys the sky toward the fog colour
  col = mix(col, uFogColor * 1.05, uOvercast * (1.0 - smoothstep(0.0, 0.9, h)) * 0.85);
  col = mix(col, uFogColor * 0.7, uOvercast * 0.35);
  // light pollution: warm glow hugging the horizon all round
  col += uGlow * exp(-max(h, 0.0) * 9.0) * (0.75 + 0.25 * noise2(vec2(atan(d.z, d.x) * 3.0, 0.0)));
  // below the horizon: the fog colour fading to dark ground
  col = mix(col, mix(uFogColor, uGround, smoothstep(0.0, -0.35, h)), smoothstep(0.0, -0.03, h));

  // moon: soft halo
  float cm = dot(d, uMoonDir);
  float am = acos(clamp(cm, -1.0, 1.0));
  float haloWidth = 1.0 + uOvercast * 1.5;
  vec3 halo = uHalo * uHaloStrength * (0.9 * exp(-am * 9.0 / haloWidth) + 0.35 * exp(-am * 2.4 / haloWidth));
  // a faint 22-degree ice ring
  halo += uHalo * uHaloStrength * 0.05 * exp(-pow((am - 0.384) / 0.03, 2.0)) * (1.0 - uOvercast);
  col += halo;

  // Milky Way: a band along a tilted great circle, broken up by dust lanes
  vec3 mwN = normalize(vec3(0.35, 0.55, 0.76));
  float mwd = dot(d, mwN);
  vec2 mwUv = vec2(atan(d.z, d.x), mwd) * vec2(2.2, 6.0);
  float band = exp(-mwd * mwd * 22.0) * smoothstep(0.02, 0.35, h);
  float dust = fbm(mwUv * 1.7 + 3.0);
  col += vec3(0.05, 0.06, 0.1) * uMilky * band * (0.4 + fbm(mwUv * 3.1)) * smoothstep(0.3, 0.6, dust + 0.1);

  // stars
  float starFade = smoothstep(0.03, 0.3, h) * smoothstep(0.05, 0.45, am) * uStars * (1.0 - uOvercast);
  vec3 stars = vec3(0.0);
  if (starFade > 0.001) {
    stars += starLayer(d, 60.0, 0.07, px, 0.0);
    stars += starLayer(d, 150.0, 0.025, px, 13.0) * 0.6;
    stars += starLayer(d, 320.0, 0.012, px, 29.0) * 0.4 * (0.3 + 4.0 * band);
  }

  // thin clouds, lit silver near the moon and warm from the town below
  float cloud = 0.0;
  if (uClouds > 0.001 && h > -0.02) {
    vec2 cp = d.xz / (h + 0.18) * 0.9 + vec2(uTime * 0.004, uTime * 0.0015);
    float n = fbm(cp * 1.3);
    cloud = smoothstep(0.52 - 0.25 * uOvercast, 0.9, n + 0.1 * noise2(cp * 7.0)) * uClouds;
    cloud *= smoothstep(-0.02, 0.12, h) * (1.0 - 0.6 * smoothstep(0.5, 0.95, h));
    vec3 cc = mix(uMid * 1.6 + uGlow * 1.4 * exp(-max(h, 0.0) * 5.0), uHalo * 1.4, exp(-am * 3.0));
    col = mix(col, cc, cloud * 0.8);
  }
  col += stars * starFade * (1.0 - cloud);

  // moon disc: limb darkening and grey maria
  float R = uMoonRadius;
  if (am < R * 1.6) {
    vec3 right = normalize(cross(uMoonDir, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, uMoonDir);
    vec2 uv = vec2(dot(d, right), dot(d, up)) / R;
    float r = length(uv);
    float mu = sqrt(max(0.0, 1.0 - r * r));
    float maria = fbm(uv * 2.2 + 4.0);
    float lum = (0.62 + 0.38 * mu) * (1.0 - 0.32 * smoothstep(0.45, 0.7, maria));
    float edge = 1.0 - smoothstep(1.0 - px / R * 1.2, 1.0, r);
    float veil = 1.0 - 0.7 * cloud;
    col = mix(col, uMoonColor * lum * veil * (1.0 - 0.55 * uOvercast), edge);
  }

  gl_FragColor = vec4(col, 1.0);
}`;

export function createSky(N, { clouds = true } = {}) {
  const c = (hex) => new THREE.Color(hex);
  const uniforms = {
    uZenith: { value: c(N.sky.zenith) },
    uMid: { value: c(N.sky.mid) },
    uHorizon: { value: c(N.sky.horizon) },
    uGround: { value: c(N.sky.ground) },
    uGlow: { value: c(N.sky.glow).multiplyScalar(N.sky.glowStrength) },
    uFogColor: { value: c(N.fog.color) },
    uMoonDir: { value: new THREE.Vector3(...N.moon.skyDirection).normalize() },
    uMoonColor: { value: new THREE.Color(1.0, 0.95, 0.86).multiplyScalar(N.moon.discIntensity) },
    uHalo: { value: c(N.moon.halo) },
    uHaloStrength: { value: N.moon.haloStrength },
    uMoonRadius: { value: N.moon.angularRadius },
    uStars: { value: N.sky.starIntensity },
    uMilky: { value: N.sky.milkyWay },
    uClouds: { value: clouds ? N.sky.clouds : 0 },
    uOvercast: { value: 0 },
    uTime: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    name: 'lighting_sky',
    uniforms,
    vertexShader,
    fragmentShader,
    side: THREE.BackSide,
    depthWrite: false,
    depthTest: false,
    fog: false,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(10, 64, 32), material);
  mesh.name = 'lighting_sky';
  mesh.frustumCulled = false;
  mesh.renderOrder = -1e6;
  mesh.castShadow = mesh.receiveShadow = false;
  mesh.raycast = () => {};
  // centre on whichever camera draws it (main view, PMREM cube faces, outline depth pass),
  // sized just inside its far plane so any depth-only pass sees it behind everything
  mesh.onBeforeRender = (_r, _s, camera) => {
    camera.getWorldPosition(mesh.position);
    mesh.scale.setScalar(Math.max(1, (camera.far || 100) * 0.09));
    mesh.updateMatrixWorld(true);
  };
  return { mesh, material, uniforms };
}
