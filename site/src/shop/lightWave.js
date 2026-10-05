// The wave of light (round 9, after the Schwibbogen's last flame): the market's fairy bulbs and lamps brighten in
// sequence by their distance from the ornament shop, and the bloom swells and settles over a few seconds.
// Bulbs: every glowing bulb material (bulbs_, bulb_warm/bulb_cold) gets a small shader patch that scales its
// emission by the wave at that point, so one long string of lights brightens bulb by bulb as the front passes.
// Lamps: the real-time lights, by the distance of each. Bloom: the composer's bloom pass, after the lighting
// module has set it for the frame.
import * as THREE from 'three';

const SPEED = 11; // m/s: the front crosses the square in about four seconds
const WIDTH = 1.4; // s: how long one bulb's flare lasts
const AMP = 1.6; // the flare: up to 2.6x its usual glow at the crest
const SETTLE = 0.18; // and a little brighter afterwards, while the candles burn

export function createLightWave({ getLights, getBloom, motion }) {
  const uniforms = {
    uWaveT: { value: -1e4 }, // seconds since the wave left the origin (very negative: no wave)
    uWaveOrigin: { value: new THREE.Vector3() },
    uWaveAmp: { value: 0 },
    uWaveSettle: { value: 0 },
    uWaveSpeed: { value: SPEED },
    uWaveWidth: { value: WIDTH },
  };
  const patched = new WeakSet();
  let t = -1e4, running = false, settle = 0, settleWant = 0, flat = false;
  let lamps = []; // { L, base, d }
  let bloomK = 1, bloomBase = null, bloomPass = null;

  /** Patch bulb materials so their emission follows the wave (once per material; cheap while no wave runs). */
  function patchBulbs(materials) {
    for (const m of materials) {
      if (!m || patched.has(m)) continue;
      patched.add(m);
      const prev = m.onBeforeCompile;
      m.onBeforeCompile = (shader, r) => {
        prev?.call(m, shader, r);
        Object.assign(shader.uniforms, uniforms);
        shader.vertexShader = shader.vertexShader
          .replace('#include <common>', '#include <common>\nvarying vec3 vWaveWorld;')
          .replace('#include <project_vertex>', `#include <project_vertex>
  vec4 waveP = vec4( transformed, 1.0 );
  #ifdef USE_INSTANCING
    waveP = instanceMatrix * waveP;
  #endif
  vWaveWorld = ( modelMatrix * waveP ).xyz;`);
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <common>', `#include <common>
uniform float uWaveT; uniform vec3 uWaveOrigin; uniform float uWaveAmp; uniform float uWaveSettle; uniform float uWaveSpeed; uniform float uWaveWidth;
varying vec3 vWaveWorld;`)
          .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
  {
    float wd = distance( vWaveWorld.xz, uWaveOrigin.xz );
    float wx = ( uWaveT - wd / uWaveSpeed ) / uWaveWidth;
    float crest = wx > 0.0 ? wx * exp( 1.0 - wx ) : 0.0; // rises fast, falls slowly
    float after = smoothstep( 0.0, 1.0, wx );
    totalEmissiveRadiance *= 1.0 + uWaveAmp * crest + uWaveSettle * after;
  }`);
      };
      const key = m.customProgramCacheKey?.bind(m);
      m.customProgramCacheKey = () => `${key ? key() : ''}|lightwave`;
      m.needsUpdate = true;
    }
  }

  /** The same curve on the CPU (lamps, tests). */
  function gainAt(d, time = t) {
    const x = (time - d / SPEED) / WIDTH;
    const crest = x > 0 ? x * Math.exp(1 - x) : 0;
    const after = x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
    return 1 + uniforms.uWaveAmp.value * crest + uniforms.uWaveSettle.value * after;
  }

  function findBloom() {
    if (bloomPass) return bloomPass;
    bloomPass = getBloom?.() || null;
    return bloomPass;
  }

  return {
    uniforms,
    patchBulbs,
    gainAt,
    get running() { return running; },
    get t() { return t; },
    /** Start the wave from a world point. Reduced motion: everything brightens together, gently. */
    start(origin) {
      uniforms.uWaveOrigin.value.copy(origin);
      flat = !!motion?.reduced;
      uniforms.uWaveSpeed.value = flat ? 1e6 : SPEED;
      uniforms.uWaveWidth.value = flat ? 1.6 : WIDTH;
      uniforms.uWaveAmp.value = flat ? 0.5 : AMP;
      t = 0;
      running = true;
      settleWant = SETTLE;
      lamps = (getLights?.() || []).filter((L) => L.isLight && L.intensity > 0).map((L) => ({ L, base: L.intensity, d: L.getWorldPosition(new THREE.Vector3()).setY(origin.y).distanceTo(origin) }));
    },
    /** The candles went out: the lasting glow fades. */
    fade() { settleWant = 0; },
    get settle() { return settle; },
    /** Before the lighting module's update: take back the bloom change of the last frame. */
    pre() {
      const b = findBloom();
      if (b && bloomBase != null) b.strength = bloomBase;
      bloomBase = null;
    },
    /** After the lighting module's update: the lamps and the bloom for this frame. */
    post(dt) {
      if (running) t += dt;
      settle += (settleWant - settle) * Math.min(1, dt * (settleWant ? 1.5 : 0.6));
      // the wave has crossed everything: its crest is gone, only the lasting glow stays
      if (running && t > 60 / uniforms.uWaveSpeed.value + WIDTH * 6) { running = false; uniforms.uWaveAmp.value = 0; }
      uniforms.uWaveT.value = running ? t : settle > 1e-3 ? 1e4 : -1e4;
      uniforms.uWaveSettle.value = settle;
      for (const l of lamps) l.L.intensity = l.base * (running || settle > 1e-3 ? gainAt(l.d, running ? t : 1e4) : 1);
      if (!running && settle <= 1e-3 && lamps.length) { for (const l of lamps) l.L.intensity = l.base; lamps = []; }
      // bloom: swells with the crest crossing the market, then settles
      const swell = running ? (flat ? 0.25 : 0.85) * Math.sin(Math.min(1, t / (flat ? 2 : 4.5)) * Math.PI) : 0;
      bloomK = 1 + swell + settle * 0.5;
      const b = findBloom();
      if (b && typeof b.strength === 'number' && bloomK !== 1) { bloomBase = b.strength; b.strength *= bloomK; }
    },
    get bloomGain() { return bloomK; },
    stats: () => ({ running, t: +t.toFixed(2), settle: +settle.toFixed(3), bloom: +bloomK.toFixed(3), lamps: lamps.length, amp: uniforms.uWaveAmp.value }),
  };
}
