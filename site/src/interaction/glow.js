// A subtle glow on what a visitor can click (Mac, 2026-10-06: "There should be a subtle glow which object user
// can interact"). Two parts:
//   - arrival shimmer: when the visitor arrives at a stop, the things there that answer a click (the act_ items the
//     picker treats as clickable, the ornament shop's three moments, the Bratwurst plate, the Bücherstand's closed
//     cabinets) breathe a faint warm light, about one breath every 2.6 s. It fades after the first interaction at
//     that stop, or after about 20 s, and comes back on the next arrival. On a phone (no hover) this is how a
//     visitor finds what to tap. With reduced motion it is a steady faint glow instead of a breath.
//   - hover: the item under the pointer glows a little brighter (picking.js keeps its lift and label).
// Cheap by design: no extra pass and no outline. Items often share one material (the vendor's atlas, the merged
// shelf goods), so nothing here touches a model's material: each glowing mesh gets a thin additive copy that draws
// its geometry again with a warm rim-weighted colour (one shared shader, one small material per item). The copies
// live in their own group outside the models, follow their mesh's world matrix at draw time, take its geometry
// again each frame (a lite-to-full graft swaps it), and are only drawn while they glow. Picking, the merges and
// the graft never see them.
import * as THREE from 'three';

export const GLOW = {
  color: [1.0, 0.72, 0.42], // warm lamplight (linear)
  peak: 0.3, // breath at its fullest: the item's colour x this, added (before exposure; bloom starts near 1)
  tint: 0.12, // plus this much of the light itself (dark things still show it)
  low: 0.3, // the breath's trough, as a share of the peak
  steady: 0.62, // reduced motion: a steady glow at this share of the peak
  period: 2.6, // seconds per breath
  hold: 20, // seconds the shimmer lasts after an arrival
  fadeIn: 1.2,
  fadeOut: 1.6,
  hover: 0.55, // the hovered item
  rim: 1.1, // extra toward the silhouette (1 - n.v)^2: reads as light catching the edges
};

const vertexShader = /* glsl */ `
#include <common>
#include <fog_pars_vertex>
varying vec3 vN;
varying vec3 vV;
#ifdef GLOW_MAP
uniform mat3 uMapTransform;
varying vec2 vUv;
#endif
void main() {
#ifdef GLOW_MAP
  vUv = (uMapTransform * vec3(uv, 1.0)).xy;
#endif
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
#ifdef GLOW_NORMALS
  vN = normalize(normalMatrix * normal);
#else
  vN = vec3(0.0, 0.0, 1.0);
#endif
  vV = -mvPosition.xyz;
  gl_Position = projectionMatrix * mvPosition;
#include <fog_vertex>
}`;
const fragmentShader = /* glsl */ `
uniform vec3 uColor;
uniform vec3 uAlbedo;
uniform float uLevel;
uniform float uRim;
uniform float uTint;
uniform float uScale;
varying vec3 vN;
varying vec3 vV;
#ifdef GLOW_MAP
uniform sampler2D uMap;
varying vec2 vUv;
#endif
#include <common>
#include <fog_pars_fragment>
void main() {
  float ndv = abs(dot(normalize(vN), normalize(vV)));
  float rim = (1.0 - ndv) * (1.0 - ndv);
  // the item's own colour lit by warm lamplight (its hue kept), plus a little of the light itself for dark things
  vec3 albedo = uAlbedo;
#ifdef GLOW_MAP
  albedo *= texture2D(uMap, vUv).rgb;
#endif
  vec3 c = uColor * (albedo + uTint) * uLevel * uScale * (0.55 + uRim * rim);
#ifdef USE_FOG
#ifdef FOG_EXP2
  float fogFactor = 1.0 - exp(-fogDensity * fogDensity * vFogDepth * vFogDepth);
#else
  float fogFactor = smoothstep(fogNear, fogFar, vFogDepth);
#endif
  c *= 1.0 - fogFactor; // additive: fade to nothing in the haze, not to the fog colour
#endif
  gl_FragColor = vec4(c, 1.0);
}`;

const templates = {};
const warm = new THREE.Color(...GLOW.color);
/** A glow material for a mesh drawn with `src` (its colour and colour map, so the glow keeps the item's hue). */
function glowMaterial(normals, src, hasUv) {
  const map = hasUv && src?.map?.isTexture ? src.map : null;
  const key = (normals ? 'n' : 'f') + (map ? 'm' : '');
  templates[key] ||= new THREE.ShaderMaterial({
    name: 'engine_glow',
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { uColor: { value: warm }, uAlbedo: { value: new THREE.Color(1, 1, 1) }, uLevel: { value: 0 }, uRim: { value: GLOW.rim }, uTint: { value: GLOW.tint }, uScale: { value: 1 }, uMap: { value: null }, uMapTransform: { value: new THREE.Matrix3() } }]),
    vertexShader, fragmentShader,
    defines: { ...(normals ? { GLOW_NORMALS: '' } : {}), ...(map ? { GLOW_MAP: '' } : {}) },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: true,
    // drawn over its own surface (or the merged copy of it, transformed on the CPU): a nudge toward the camera
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -4,
  });
  // one program for every item; each item its own uniforms
  const m = templates[key].clone();
  m.uniforms.uColor.value = warm;
  if (src?.color?.isColor) m.uniforms.uAlbedo.value.copy(src.color);
  // see-through things (a cabinet's glass, a glass of Glühwein) glow about as much as they show
  if (src?.transparent) m.uniforms.uScale.value = THREE.MathUtils.clamp((src.opacity ?? 1) * 2, 0.15, 1);
  if (map) { map.updateMatrix(); m.uniforms.uMap.value = map; m.uniforms.uMapTransform.value.copy(map.matrix); }
  return m;
}

const SKIP_MESH = /^(fx_|write_|card_|cam_|engine_|open_|steam|smoke)/i;
const shown = (o) => { for (let x = o; x; x = x.parent) if (!x.visible) return false; return true; };

/**
 * createGlow({ scene, items, motion, here: () => stop id or null (arrived), extraTargets: (stop) => [Object3D] })
 * update(dt) once a frame; hover(node|null); interacted(); refresh() after a graft; state() for tests.
 */
export function createGlow({ scene, items, motion, here, extraTargets = () => [] }) {
  const group = new THREE.Group();
  group.name = 'engine_glow_overlays';
  group.matrixAutoUpdate = false;
  scene.add(group);
  const recs = new Map(); // target node -> { node, overlays: [{ o, m }], level, mat }
  let stop = null; // the stop the shimmer belongs to
  let t = 0; // seconds since the arrival
  let shimmer = 0; // envelope 0..1
  let ending = false; // the visitor interacted (or the hold ran out): fading out
  let hovered = null;

  function build(node) {
    const mats = new Map(); // one glow material per source material (and normals / uv)
    const matFor = (m) => {
      const src = Array.isArray(m.material) ? m.material[0] : m.material;
      const n = !!m.geometry.attributes.normal, uv = !!m.geometry.attributes.uv;
      const k = `${src?.uuid}|${n}|${uv}`;
      if (!mats.has(k)) mats.set(k, glowMaterial(n, src, uv));
      return mats.get(k);
    };
    const overlays = [];
    node.traverse((m) => {
      if (!m.isMesh || m.isSkinnedMesh || m.isInstancedMesh || m.isText || m.isSprite || m.morphTargetInfluences) return;
      if (SKIP_MESH.test(m.name || '') || m.userData.pickProxyHidden || m.userData.pickProxy || m.userData.glowSkip) return;
      if (!m.geometry?.attributes?.position) return;
      const o = new THREE.Mesh(m.geometry, matFor(m));
      o.name = 'engine_glow';
      o.userData.glowOverlay = true;
      o.matrixAutoUpdate = false;
      o.matrixWorldAutoUpdate = false;
      o.frustumCulled = false; // its world matrix is taken at draw time (after culling)
      o.castShadow = o.receiveShadow = false;
      o.renderOrder = 2;
      o.raycast = () => {};
      o.visible = false;
      o.onBeforeRender = () => { o.matrixWorld.copy(m.matrixWorld); };
      group.add(o);
      overlays.push({ o, m });
    });
    return { node, overlays, level: 0, hk: 0, mats: [...mats.values()] };
  }
  function recOf(node) {
    let r = recs.get(node);
    if (!r) { r = build(node); recs.set(node, r); }
    return r;
  }
  function drop(r) {
    for (const { o } of r.overlays) o.removeFromParent();
    r.mats.forEach((m) => m.dispose());
    recs.delete(r.node);
  }

  /** The nodes at a stop that answer a click now. */
  function targets(id) {
    if (!id) return [];
    const out = new Set();
    for (const it of items.of(id)) if (it.clickable && it.node && (items.pickable?.(it) ?? true)) out.add(it.node);
    for (const n of extraTargets(id) || []) if (n) out.add(n);
    // a node inside another target (the Schwibbogen's candles) glows with it, not twice
    return [...out].filter((n) => { for (let p = n.parent; p; p = p.parent) if (out.has(p)) return false; return true; });
  }
  let current = []; // the nodes the shimmer lights

  function arrive(id) {
    stop = id;
    t = 0;
    ending = false;
    current = targets(id);
    for (const n of current) recOf(n);
  }

  function breath() {
    if (motion.reduced) return GLOW.steady;
    const s = 0.5 - 0.5 * Math.cos((t / GLOW.period) * Math.PI * 2);
    return GLOW.low + (1 - GLOW.low) * s;
  }

  return {
    group,
    update(dt) {
      const id = here();
      if (id !== stop) {
        // leaving (or arriving somewhere new): the old stop's glows go at once
        if (stop) for (const r of [...recs.values()]) if (r.node !== hovered) drop(r);
        stop = null; shimmer = 0; current = [];
        if (id) arrive(id);
      }
      if (stop) {
        t += dt;
        if (t > GLOW.hold) ending = true;
        const want = ending ? 0 : 1;
        const rate = dt / (want ? GLOW.fadeIn : GLOW.fadeOut);
        shimmer = want > shimmer ? Math.min(want, shimmer + rate) : Math.max(want, shimmer - rate);
      }
      const ease = (x) => x * x * (3 - 2 * x);
      const base = GLOW.peak * ease(shimmer) * breath();
      if (hovered) recOf(hovered);
      const here_ = new Set(current);
      for (const r of [...recs.values()]) {
        // the hover glow eases in and out (about a sixth of a second)
        r.hk = r.node === hovered ? Math.min(1, r.hk + dt * 6) : Math.max(0, r.hk - dt * 6);
        r.level = Math.max(here_.has(r.node) && shimmer > 0 ? base : 0, GLOW.hover * ease(r.hk));
        if (r.level <= 0.0005 && r.node !== hovered && !here_.has(r.node)) { drop(r); continue; }
        for (const m of r.mats) { m.uniforms.uLevel.value = r.level; m.uniforms.uRim.value = GLOW.rim; m.uniforms.uTint.value = GLOW.tint; }
        const on = r.level > 0.0005;
        for (const ov of r.overlays) {
          const { o, m } = ov;
          // the mesh draws (or its copy in a merged shelf mesh does) and is still in the scene
          const vis = on && !!m.parent && (m.visible || m.userData.inMerge) && shown(m.parent);
          o.visible = vis;
          if (vis && o.geometry !== m.geometry) o.geometry = m.geometry; // a graft swapped it
        }
      }
    },
    /** The node under the pointer (an item's pivot, or a cabinet's door), or null. */
    hover(node) { hovered = node || null; },
    /** The visitor did something at this stop: the shimmer fades. */
    interacted() { if (stop) ending = true; },
    /** After a graft or a change in what can be clicked here (a cabinet opened): rebuild the copies. */
    refresh() {
      for (const r of [...recs.values()]) drop(r);
      if (stop) { current = targets(stop); for (const n of current) recOf(n); }
    },
    /** For tests: the shimmer's state and each glowing node's level. */
    state() {
      const list = [...recs.values()].map((r) => ({ name: r.node.name, level: +r.level.toFixed(4), drawn: r.overlays.filter((x) => x.o.visible).length, meshes: r.overlays.length }));
      return { stop, t: +t.toFixed(2), shimmer: +shimmer.toFixed(3), ending, reduced: !!motion.reduced, hovered: hovered?.name || null, targets: current.map((n) => n.name), items: list, peak: GLOW.peak, hover: GLOW.hover };
    },
  };
}
