// The wave of light (round 9, after the Schwibbogen's last flame): the market's fairy bulbs and lamps brighten in
// sequence by their distance from the ornament shop, and the bloom swells and settles over a few seconds.
// Bulbs: every glowing bulb material (bulbs_, bulb_warm/bulb_cold) gets a small shader patch that scales its
// emission by the wave at that point, so one long string of lights brightens bulb by bulb as the front passes.
// Lamps: the real-time lights, by the distance of each. Bloom: the composer's bloom pass, after the lighting
// module has set it for the frame.
// The hush (round 9, pass 2): while the candles are lit the market's own lights dim with the town, so when the wave
// comes it relights them as it passes, and a still frame shows the front: lit behind it, dim ahead.
import * as THREE from 'three';

const SPEED = 7; // m/s: the front crosses the square in about five seconds, slow enough to follow
const WIDTH = 1.2; // s: how long one bulb's flare lasts
const AMP = 2.6; // the flare: up to 3.6x its usual glow at the crest
const SETTLE = 0.2; // and a little brighter afterwards, while the candles burn
const HUSH_BULBS = 0.7; // how far the bulbs dim while the market waits for the wave (to 30 %)
const HUSH_LAMPS = 0.55; // and the lamps (to 45 %)
const SWELL = 1.5; // bloom: up to 2.5x at the swell's height
const SWELL_T = 6; // s: the swell rises and settles over this

export function createLightWave({ getLights, getBloom, motion }) {
  const uniforms = {
    uWaveT: { value: -1e4 }, // seconds since the wave left the origin (very negative: no wave)
    uWaveOrigin: { value: new THREE.Vector3() },
    uWaveAmp: { value: 0 },
    uWaveSettle: { value: 0 },
    uWaveSpeed: { value: SPEED },
    uWaveWidth: { value: WIDTH },
    uWaveHush: { value: 0 },
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
uniform float uWaveT; uniform vec3 uWaveOrigin; uniform float uWaveAmp; uniform float uWaveSettle; uniform float uWaveSpeed; uniform float uWaveWidth; uniform float uWaveHush;
varying vec3 vWaveWorld;`)
          .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
  {
    float wd = distance( vWaveWorld.xz, uWaveOrigin.xz );
    float wx = ( uWaveT - wd / uWaveSpeed ) / uWaveWidth;
    float crest = wx > 0.0 ? wx * exp( 1.0 - wx ) : 0.0; // rises fast, falls slowly
    float after = smoothstep( 0.0, 1.0, wx );
    float hushK = 1.0 - ${HUSH_BULBS.toFixed(3)} * uWaveHush * ( 1.0 - after );
    totalEmissiveRadiance *= hushK * ( 1.0 + uWaveAmp * crest + uWaveSettle * after );
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
    return (1 - HUSH_LAMPS * uniforms.uWaveHush.value * (1 - after)) * (1 + uniforms.uWaveAmp.value * crest + uniforms.uWaveSettle.value * after);
  }
  /** Bulb gain (the shader's curve, for tests). */
  function bulbGainAt(d, time = t) {
    const x = (time - d / uniforms.uWaveSpeed.value) / uniforms.uWaveWidth.value;
    const crest = x > 0 ? x * Math.exp(1 - x) : 0;
    const after = x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
    return (1 - HUSH_BULBS * uniforms.uWaveHush.value * (1 - after)) * (1 + uniforms.uWaveAmp.value * crest + uniforms.uWaveSettle.value * after);
  }
  let hush = 0, hushWant = 0;
  const grabLamps = (origin) => {
    if (lamps.length) { for (const l of lamps) l.d = l.L.getWorldPosition(new THREE.Vector3()).setY(origin.y).distanceTo(origin); return; }
    lamps = (getLights?.() || []).filter((L) => L.isLight && L.intensity > 0).map((L) => ({ L, base: L.intensity, d: L.getWorldPosition(new THREE.Vector3()).setY(origin.y).distanceTo(origin) }));
  };

  function findBloom() {
    if (bloomPass) return bloomPass;
    bloomPass = getBloom?.() || null;
    return bloomPass;
  }

  return {
    uniforms,
    patchBulbs,
    gainAt,
    bulbGainAt,
    /** The market waits for the wave (1) or not (0): its bulbs and lamps dim with the town, from `origin`. */
    setHush(v, origin) {
      hushWant = v;
      if (v > 0 && origin) { uniforms.uWaveOrigin.value.copy(origin); grabLamps(origin); }
    },
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
      grabLamps(origin);
    },
    /** The candles went out: the lasting glow fades (and the market is no longer hushed). */
    fade() { settleWant = 0; hushWant = 0; },
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
      // the hush comes on with the town's (slowly) and lifts quickly; reduced motion: no dimming at all
      hush += THREE.MathUtils.clamp((motion?.reduced ? 0 : hushWant) - hush, -1.2 * dt, 0.5 * dt);
      // the wave has crossed everything: its crest is gone, only the lasting glow stays (and nothing is hushed)
      // once the front is past the market's edge (40 m) nothing is waiting for it any more
      if (running && t > 40 / uniforms.uWaveSpeed.value + WIDTH * 2) { hushWant = 0; hush = 0; }
      if (running && t > 60 / uniforms.uWaveSpeed.value + WIDTH * 6) { running = false; uniforms.uWaveAmp.value = 0; hushWant = 0; hush = 0; }
      uniforms.uWaveT.value = running ? t : settle > 1e-3 ? 1e4 : -1e4;
      uniforms.uWaveSettle.value = settle;
      uniforms.uWaveHush.value = hush;
      const active = running || settle > 1e-3 || hush > 1e-3;
      for (const l of lamps) l.L.intensity = l.base * (active ? gainAt(l.d, running ? t : settle > 1e-3 ? 1e4 : -1e4) : 1);
      if (!active && lamps.length) { for (const l of lamps) l.L.intensity = l.base; lamps = []; }
      // bloom: swells with the crest crossing the market, then settles
      const swell = running ? (flat ? 0.25 : SWELL) * Math.sin(Math.min(1, t / (flat ? 2 : SWELL_T)) * Math.PI) : 0;
      bloomK = 1 + swell + settle * 0.5;
      const b = findBloom();
      if (b && typeof b.strength === 'number' && bloomK !== 1) { bloomBase = b.strength; b.strength *= bloomK; }
    },
    get bloomGain() { return bloomK; },
    stats: () => ({ running, t: +t.toFixed(2), front: running ? +(t * uniforms.uWaveSpeed.value).toFixed(1) : null, hush: +hush.toFixed(3), settle: +settle.toFixed(3), bloom: +bloomK.toFixed(3), lamps: lamps.length, amp: uniforms.uWaveAmp.value }),
  };
}
