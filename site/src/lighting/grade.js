// The last pass: AgX tone mapping with an adjustable blend toward Blender's "Punchy" look, then
// sRGB encoding, a gentle vignette and a little blue-noise-like grain that also dithers the dark
// sky gradient against 8-bit banding. Replaces three's OutputPass.
import * as THREE from 'three';
import { Pass, FullScreenQuad } from 'three/examples/jsm/postprocessing/Pass.js';

const fragmentShader = /* glsl */ `
uniform sampler2D tDiffuse;
uniform float uExposure, uPunch, uVignette, uGrain, uTime;
uniform vec2 uResolution;
varying vec2 vUv;

// AgX (Blender / Filament implementation, as in three's tonemapping chunk) with the look applied
// between the sigmoid and the outset, where Blender applies it.
vec3 agxContrast(vec3 x) {
  vec3 x2 = x * x, x4 = x2 * x2;
  return + 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
}
vec3 agx(vec3 color) {
  const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
    vec3(0.6274, 0.0691, 0.0164), vec3(0.3293, 0.9195, 0.0880), vec3(0.0433, 0.0113, 0.8956));
  const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
    vec3(1.6605, -0.1246, -0.0182), vec3(-0.5876, 1.1329, -0.1006), vec3(-0.0728, -0.0083, 1.1187));
  const mat3 inset = mat3(
    vec3(0.856627153315983, 0.137318972929847, 0.11189821299995),
    vec3(0.0951212405381588, 0.761241990602591, 0.0767994186031903),
    vec3(0.0482516061458583, 0.101439036467562, 0.811302368396859));
  const mat3 outset = mat3(
    vec3(1.1271005818144368, -0.1413297634984383, -0.14132976349843826),
    vec3(-0.11060664309660323, 1.157823702216272, -0.11060664309660294),
    vec3(-0.016493938717834573, -0.016493938717834257, 1.2519364065950405));
  const float minEv = -12.47393, maxEv = 4.026069;
  color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
  color = inset * color;
  color = max(color, 1e-10);
  color = clamp((log2(color) - minEv) / (maxEv - minEv), 0.0, 1.0);
  color = agxContrast(color);
  // look: Punchy = power 1.35, saturation 1.4
  float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
  vec3 punchy = pow(max(color, 0.0), vec3(1.35));
  punchy = luma + 1.4 * (punchy - luma);
  color = mix(color, punchy, uPunch);
  color = outset * color;
  color = pow(max(vec3(0.0), color), vec3(2.2));
  color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
  return clamp(color, 0.0, 1.0);
}
vec3 toSRGB(vec3 c) {
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}
float ign(vec2 p) { return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }

void main() {
  vec3 hdr = texture2D(tDiffuse, vUv).rgb * uExposure;
  vec2 q = vUv - 0.5;
  q.x *= uResolution.x / uResolution.y;
  hdr *= 1.0 - uVignette * smoothstep(0.35, 1.15, length(q));
  vec3 c = toSRGB(agx(hdr));
  // grain + dither (triangular, ~1-3 code values)
  vec2 fc = gl_FragCoord.xy + fract(uTime * 7.31) * 113.0;
  float n = ign(fc) + ign(fc + 71.3) - 1.0;
  c += n * (1.0 / 255.0 + uGrain * (1.0 - dot(c, vec3(0.333))));
  gl_FragColor = vec4(c, 1.0);
}`;

export class GradePass extends Pass {
  constructor({ exposure = 1, punch = 0.8, vignette = 0.25, grain = 0.01 } = {}) {
    super();
    this.uniforms = {
      tDiffuse: { value: null },
      uExposure: { value: exposure },
      uPunch: { value: punch },
      uVignette: { value: vignette },
      uGrain: { value: grain },
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(1, 1) },
    };
    this.material = new THREE.ShaderMaterial({
      name: 'lighting_grade',
      uniforms: this.uniforms,
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader,
      depthTest: false,
      depthWrite: false,
    });
    this.fsQuad = new FullScreenQuad(this.material);
    this.exposureFrom = null; // a renderer: read toneMappingExposure each frame
  }

  setSize(w, h) { this.uniforms.uResolution.value.set(w, h); }

  render(renderer, writeBuffer, readBuffer) {
    this.uniforms.tDiffuse.value = readBuffer.texture;
    this.uniforms.uTime.value = (this.uniforms.uTime.value + 1 / 60) % 1000;
    if (this.exposureFrom) this.uniforms.uExposure.value = this.exposureFrom.toneMappingExposure;
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer);
    if (this.clear) renderer.clear();
    this.fsQuad.render(renderer);
  }

  dispose() {
    this.material.dispose();
    this.fsQuad.dispose();
  }
}
