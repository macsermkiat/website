// The wave of light (round 9, after the Schwibbogen's last flame): the market's fairy bulbs and lamps brighten in
// sequence by their distance from the ornament shop, and the bloom swells and settles over a few seconds.
// Bulbs: every glowing bulb material (bulbs_, bulb_warm/bulb_cold) gets a small shader patch that scales its
// emission by the wave at that point, so one long string of lights brightens bulb by bulb as the front passes.
// Lamps: the real-time lights, by the distance of each. Bloom: the composer's bloom pass, after the lighting
// module has set it for the frame.
// The hush (round 9, pass 2): while the candles are lit the market's own lights dim with the town, so when the wave
// comes it relights them as it passes, and a still frame shows the front: lit behind it, dim ahead.
// The wash (round 9, pass 2, judge note "make the wave readable"): the light runs over the ground too. The square's
// cobbles, setts, granite bands and puddles get a patch that adds warm light to their own colour where the front is
// passing (a ragged band, wider than a bulb's flare, that fades out by the square's edge) and a faint lasting warmth
// behind it, so a still frame shows where the wave has got to from across the square.
import * as THREE from 'three';

const SPEED = 7; // m/s: the front crosses the square in about five seconds, slow enough to follow
const WIDTH = 1.2; // s: how long one bulb's flare lasts
const AMP = 2.6; // the flare: up to 3.6x its usual glow at the crest
const SETTLE = 0.2; // and a little brighter afterwards, while the candles burn
const HUSH_BULBS = 0.7; // how far the bulbs dim while the market waits for the wave (to 30 %)
const HUSH_LAMPS = 0.55; // and the lamps (to 45 %)
const SWELL = 2.1; // bloom: up to 3.1x at the swell's height
const WASH_K = 2.2; // the ground at the band's height: its own colour lit by about a strong lamp's worth of warm light
const WASH_WIDTH = 1.0; // s: the band on the ground peaks 7 m behind the front and is about 8 m across
const WASH_SHARP = 0.55; // the band's half-width, in WASH_WIDTH units
const WASH_SETTLE = 0.4; // the lasting warmth on the ground behind the front, while the candles burn
const WASH_REACH = 40; // m: the wash fades out by the square's edge
const WASH_NEAR = 2.5; // m: and does not light the ground under the arch itself
/** The square's ground materials, by name (the architect's square.glb; a stand-in ground has `ground` meshes). */
const GROUND_MAT = /^(cobble|setts|granite_bands|puddle)/i;
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
    uWashK: { value: 0 },
    uWashColor: { value: new THREE.Color(1.0, 0.6, 0.28) },
  };
  const patched = new WeakSet(), washed = new WeakSet();
  let washCount = 0;
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

  /**
   * Patch the square's ground so the wave washes over it (once per material). `root` is the scene: every mesh on a
   * ground material (or a stand-in mesh named ground) is found.
   */
  let groundRoot = null;
  function patchGround(root) {
    groundRoot = root;
    const mats = new Set();
    root?.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (m && (m.isMeshStandardMaterial || m.isMeshLambertMaterial || m.isMeshPhongMaterial) && (GROUND_MAT.test(m.name || '') || /^ground/i.test(o.name))) mats.add(m);
      }
    });
    let n = 0;
    for (const m of mats) {
      if (washed.has(m)) continue;
      washed.add(m); n++;
      const prev = m.onBeforeCompile;
      m.onBeforeCompile = (shader, r) => {
        prev?.call(m, shader, r);
        Object.assign(shader.uniforms, uniforms);
        shader.vertexShader = shader.vertexShader
          .replace('#include <common>', '#include <common>\nvarying vec3 vWashWorld;')
          .replace('#include <project_vertex>', `#include <project_vertex>
  vec4 washP = vec4( transformed, 1.0 );
  #ifdef USE_INSTANCING
    washP = instanceMatrix * washP;
  #endif
  vWashWorld = ( modelMatrix * washP ).xyz;`);
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <common>', `#include <common>
uniform float uWaveT; uniform vec3 uWaveOrigin; uniform float uWaveSettle; uniform float uWaveSpeed; uniform float uWashK; uniform vec3 uWashColor;
varying vec3 vWashWorld;`)
          .replace('#include <opaque_fragment>', `{
    vec2 wv = vWashWorld.xz - uWaveOrigin.xz;
    float wd = length( wv );
    // a ragged front: it arrives a little sooner or later along the way round, as light finds its way between stalls
    float wa = atan( wv.y, wv.x );
    float rag = 0.9 * sin( wa * 7.0 + 1.3 ) + 0.6 * sin( wa * 13.0 - 0.7 ) + 0.35 * sin( wd * 0.9 );
    float wx = ( uWaveT - ( wd + rag ) / uWaveSpeed ) / ${WASH_WIDTH.toFixed(2)};
    float wb = ( wx - 1.0 ) / ${WASH_SHARP.toFixed(2)};
    float crest = exp( -wb * wb ); // a band that passes over: bright where it is, back to a warm glow behind it
    float after = smoothstep( 0.0, 1.0, wx );
    float reach = ( 1.0 - smoothstep( ${(WASH_REACH * 0.55).toFixed(1)}, ${WASH_REACH.toFixed(1)}, wd ) ) * smoothstep( ${(WASH_NEAR * 0.4).toFixed(2)}, ${WASH_NEAR.toFixed(2)}, wd );
    outgoingLight += diffuseColor.rgb * uWashColor * ( uWashK * crest + ${WASH_SETTLE.toFixed(2)} * uWaveSettle / ${SETTLE.toFixed(2)} * after ) * reach;
  }
  #include <opaque_fragment>`);
      };
      const key = m.customProgramCacheKey?.bind(m);
      m.customProgramCacheKey = () => `${key ? key() : ''}|lightwash`;
      m.needsUpdate = true;
    }
    washCount += n;
    return n;
  }

  /** The ground's wash at a distance from the origin, now (the shader's curve without the ragged front; tests). */
  function washAt(d, time = t) {
    const x = (time - d / uniforms.uWaveSpeed.value) / WASH_WIDTH;
    const b = (x - 1) / WASH_SHARP, crest = Math.exp(-b * b);
    const after = x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
    return uniforms.uWashK.value * crest + WASH_SETTLE * (uniforms.uWaveSettle.value / SETTLE) * after;
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
    patchGround,
    washAt,
    get washedCount() { return washCount; },
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
      uniforms.uWashK.value = flat ? 0.6 : WASH_K;
      if (groundRoot) patchGround(groundRoot); // a ground streamed in since the shop was set up
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
      if (running && t > 60 / uniforms.uWaveSpeed.value + WIDTH * 6) { running = false; uniforms.uWaveAmp.value = 0; uniforms.uWashK.value = 0; hushWant = 0; hush = 0; }
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
    stats: () => ({ washed: washCount, running, t: +t.toFixed(2), front: running ? +(t * uniforms.uWaveSpeed.value).toFixed(1) : null, hush: +hush.toFixed(3), settle: +settle.toFixed(3), bloom: +bloomK.toFixed(3), lamps: lamps.length, amp: uniforms.uWaveAmp.value }),
  };
}
