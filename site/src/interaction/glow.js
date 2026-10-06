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
  color: [1.0, 0.7, 0.4], // warm lamplight (linear)
  peak: 0.07, // breath at its fullest (added radiance, before exposure; bloom starts near 1)
  low: 0.3, // the breath's trough, as a share of the peak
  steady: 0.62, // reduced motion: a steady glow at this share of the peak
  period: 2.6, // seconds per breath
  hold: 20, // seconds the shimmer lasts after an arrival
  fadeIn: 1.2,
  fadeOut: 1.6,
  hover: 0.13, // the hovered item
  rim: 1.1, // extra toward the silhouette (1 - n.v)^2: reads as light catching the edges
};

const vertexShader = /* glsl */ `
#include <common>
#include <fog_pars_vertex>
varying vec3 vN;
varying vec3 vV;
void main() {
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
uniform float uLevel;
uniform float uRim;
varying vec3 vN;
varying vec3 vV;
#include <common>
#include <fog_pars_fragment>
void main() {
  float ndv = abs(dot(normalize(vN), normalize(vV)));
  float rim = (1.0 - ndv) * (1.0 - ndv);
  vec3 c = uColor * uLevel * (0.6 + uRim * rim);
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
function glowMaterial(normals) {
  const key = normals ? 'n' : 'f';
  templates[key] ||= new THREE.ShaderMaterial({
    name: 'engine_glow',
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { uColor: { value: new THREE.Color(...GLOW.color) }, uLevel: { value: 0 }, uRim: { value: GLOW.rim } }]),
    vertexShader, fragmentShader,
    defines: normals ? { GLOW_NORMALS: '' } : {},
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: true,
    // drawn over its own surface (or the merged copy of it, transformed on the CPU): a nudge toward the camera
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -4,
  });
  // one program for every item; each item its own uniforms
  const m = templates[key].clone();
  m.uniforms.uColor.value = templates[key].uniforms.uColor.value;
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
  let hoverK = 0;
  let lastHovered = null;

  function build(node) {
    const mat = glowMaterial(true);
    const flat = glowMaterial(false);
    const overlays = [];
    node.traverse((m) => {
      if (!m.isMesh || m.isSkinnedMesh || m.isInstancedMesh || m.isText || m.isSprite || m.morphTargetInfluences) return;
      if (SKIP_MESH.test(m.name || '') || m.userData.pickProxyHidden || m.userData.pickProxy || m.userData.glowSkip) return;
      if (!m.geometry?.attributes?.position) return;
      const normals = !!m.geometry.attributes.normal;
      const o = new THREE.Mesh(m.geometry, normals ? mat : flat);
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
    return { node, overlays, level: 0, mats: [mat, flat] };
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
      if (hovered !== lastHovered) { hoverK = 0; lastHovered = hovered; }
      hoverK = Math.min(1, hoverK + dt * 6);
      if (hovered) recOf(hovered);
      const lit = new Set(shimmer > 0 ? current : []);
      for (const r of [...recs.values()]) {
        const hov = r.node === hovered ? GLOW.hover * ease(hoverK) : 0;
        r.level = Math.max(lit.has(r.node) ? base : 0, hov);
        if (r.level <= 0.0005 && !lit.has(r.node) && r.node !== hovered && stop && !current.includes(r.node)) { drop(r); continue; }
        for (const m of r.mats) m.uniforms.uLevel.value = r.level;
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
