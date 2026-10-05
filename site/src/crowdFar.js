// The far crowd (round 8, docs/adr/0004): about 80 people on the full market, so everyone beyond the LOD distance
// (about 25 m) is drawn by one instanced mesh per figure instead of a skinned figure each.
//
// Each lite figure's clips are baked once, after the first frame, into a vertex animation texture (VAT): one row per
// frame at 8 frames a second, one texel per vertex, holding the skinned position in the figure's own frame. The
// vertex shader reads the two frames either side of the instance's clip time and blends them, so a far person keeps
// walking, sipping and talking with no CPU skinning and no mixer at all; each instance carries its clip (first row,
// frame count, phase, speed), its coat, hat and scarf colours and whether it holds a mug. One draw call per figure
// file draws every far person who wears it. The crowd's own logic (walking the lanes, stepping out of a close-up)
// still moves each person; the instance just follows them.
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';

export const VAT_FPS = 8;
const PART_ID = { coat: 0, body: 1, hat: 2, scarf: 3 };
const MUG = 4;

/**
 * Bake a figure (the compacted lite figure root) for the clips given. Returns
 * (a promise of) { geometry, texture, clips: Map(name -> { start, frames, duration }), vertices, rows, ms (busy time) } or null.
 */
export async function bakeFigure(src, clips, { yieldEvery = 24 } = {}) {
  const t0 = performance.now();
  let waited = 0; // time handed back to the page between batches (not the bake's own cost)
  const fig = cloneSkinned(src);
  fig.position.set(0, 0, 0); fig.quaternion.identity(); fig.scale.set(1, 1, 1);
  fig.updateMatrixWorld(true);
  const meshes = [];
  // every mesh that draws the figure: the skinned body, and anything carried rigidly by a bone (the mug)
  fig.traverse((o) => { if (o.isMesh && o.visible !== false && o.geometry?.getAttribute('position')) meshes.push(o); });
  if (!meshes.length || !clips.length) return null;
  // the static attributes: colour (each part's own COLOR_0; the body's colour baked in), part id, uv, normal
  const pos = [], nor = [], col = [], part = [], uv = [], index = [];
  let base = 0;
  const rootInv = new THREE.Matrix4().copy(fig.matrixWorld).invert();
  const v = new THREE.Vector3(), n = new THREE.Vector3(), c = new THREE.Color();
  for (const m of meshes) {
    const g = m.geometry, P = g.getAttribute('position'), N = g.getAttribute('normal'), U = g.getAttribute('uv'), C = g.getAttribute('color');
    const parts = g.userData.parts || null;
    const isMug = /^mug/i.test(m.name || '') || /mug/i.test(m.material?.name || '');
    const toRoot = new THREE.Matrix4().multiplyMatrices(rootInv, m.matrixWorld);
    const nm = new THREE.Matrix3().getNormalMatrix(toRoot);
    const own = new THREE.Color().copy(m.material?.color || c.set(1, 1, 1));
    for (let i = 0; i < P.count; i++) {
      v.fromBufferAttribute(P, i).applyMatrix4(toRoot); pos.push(v.x, v.y, v.z);
      if (N) { n.fromBufferAttribute(N, i).applyMatrix3(nm).normalize(); nor.push(n.x, n.y, n.z); } else nor.push(0, 1, 0);
      uv.push(U ? U.getX(i) : 0, U ? U.getY(i) : 0);
      let id = isMug ? MUG : 1;
      let r = 1, gg = 1, b = 1;
      if (parts) {
        const pt = parts.find((p) => i >= p.start && i < p.start + p.count);
        if (pt) {
          id = PART_ID[pt.name] ?? 1;
          const j = (i - pt.start) * 3;
          r = pt.base[j]; gg = pt.base[j + 1]; b = pt.base[j + 2];
          if (id === 1) { r *= pt.color.r; gg *= pt.color.g; b *= pt.color.b; }
        }
      } else {
        if (C) { r = C.getX(i); gg = C.getY(i); b = C.getZ(i); }
        r *= own.r; gg *= own.g; b *= own.b;
      }
      col.push(r, gg, b);
      part.push(id);
    }
    const I = g.index;
    if (I) for (let k = 0; k < I.count; k++) index.push(base + I.getX(k));
    else for (let k = 0; k < P.count; k++) index.push(base + k);
    base += P.count;
  }
  const V = base;
  if (V > 8192) return null; // wider than a texture row should be; this figure stays skinned
  // the frames: every clip at VAT_FPS
  const plan = [];
  let rows = 0;
  for (const clip of clips) {
    const frames = Math.max(2, Math.min(240, Math.round(clip.duration * VAT_FPS)));
    plan.push({ clip, start: rows, frames });
    rows += frames;
  }
  const data = new Float32Array(V * rows * 4);
  const mixer = new THREE.AnimationMixer(fig);
  const mats = meshes.map((m) => new THREE.Matrix4().multiplyMatrices(rootInv, m.matrixWorld));
  for (const p of plan) {
    mixer.stopAllAction();
    const action = mixer.clipAction(p.clip);
    action.reset().play();
    for (let f = 0; f < p.frames; f++) {
      // a breath between batches of frames, so the bake never holds a frame of the market for long
      if (yieldEvery && f && f % yieldEvery === 0) { const t = performance.now(); await new Promise((r) => setTimeout(r, 0)); waited += performance.now() - t; }
      mixer.setTime((f / p.frames) * p.clip.duration);
      fig.updateMatrixWorld(true);
      let o = 0;
      meshes.forEach((m, mi) => {
        if (m.isSkinnedMesh) m.skeleton.update();
        const toRoot = mats[mi].copy(rootInv).multiply(m.matrixWorld);
        const count = m.geometry.getAttribute('position').count;
        for (let i = 0; i < count; i++) {
          m.getVertexPosition(i, v); // skinned (or as modelled), in the mesh's own frame
          v.applyMatrix4(toRoot);
          const k = ((p.start + f) * V + o + i) * 4;
          data[k] = v.x; data[k + 1] = v.y; data[k + 2] = v.z; data[k + 3] = 1;
        }
        o += count;
      });
    }
    action.stop();
  }
  mixer.uncacheRoot(fig);
  const texture = new THREE.DataTexture(data, V, rows, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = texture.magFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  geometry.setAttribute('part', new THREE.Float32BufferAttribute(part, 1));
  geometry.setIndex(index);
  geometry.computeBoundingSphere();
  geometry.boundingSphere.radius += 1; // a walk cycle reaches beyond the rest pose
  const clipMap = new Map(plan.map((p) => [p.clip.name, { start: p.start, frames: p.frames, duration: p.clip.duration }]));
  return { geometry, texture, clips: clipMap, vertices: V, rows, ms: Math.round(performance.now() - t0 - waited) };
}

/** A material that draws a baked figure from its VAT, per instance. `lift(m)` adds the crowd's own lift. */
export function vatMaterial(baked, { ao = null, lift = (m) => m, time }) {
  const m = new THREE.MeshStandardMaterial({ name: 'crowd_far_figure', vertexColors: true, roughness: 0.86, metalness: 0, side: THREE.DoubleSide, aoMap: ao });
  m.userData.vat = true;
  m.onBeforeCompile = (shader) => {
    shader.uniforms.vatTex = { value: baked.texture };
    shader.uniforms.vatTime = time;
    shader.uniforms.vatFps = { value: VAT_FPS };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>
uniform highp sampler2D vatTex;
uniform float vatTime;
uniform float vatFps;
attribute vec4 vatClip;
attribute vec3 iCoat;
attribute vec3 iHat;
attribute vec3 iScarf;
attribute float iMug;
attribute float part;`)
      .replace('#include <color_vertex>', `#include <color_vertex>
  vec3 vatTint = part < 0.5 ? iCoat : ( part < 1.5 ? vec3( 1.0 ) : ( part < 2.5 ? iHat : ( part < 3.5 ? iScarf : vec3( 1.0 ) ) ) );
  vColor.rgb *= vatTint;`)
      .replace('#include <begin_vertex>', `
  float vatF = mod( ( vatTime * vatClip.w + vatClip.z ) * vatFps, vatClip.y );
  float vatF0 = floor( vatF );
  float vatF1 = mod( vatF0 + 1.0, vatClip.y );
  vec3 vatP0 = texelFetch( vatTex, ivec2( gl_VertexID, int( vatClip.x + vatF0 ) ), 0 ).xyz;
  vec3 vatP1 = texelFetch( vatTex, ivec2( gl_VertexID, int( vatClip.x + vatF1 ) ), 0 ).xyz;
  vec3 transformed = mix( vatP0, vatP1, vatF - vatF0 );
  if ( part > 3.5 && iMug < 0.5 ) transformed = vec3( 0.0 );`);
  };
  m.customProgramCacheKey = () => 'crowd_far_vat';
  return lift(m);
}

/**
 * One instanced mesh per figure: add(person) reserves a slot; show(slot, matrix, clip, phase, speed) puts the person
 * there; hide(slot) parks them. The shared clock is `time.value` (seconds).
 */
export function createFarFigure(baked, { capacity, ao, lift, time, colors }) {
  const geo = baked.geometry.clone();
  const n = Math.max(1, capacity);
  const clipA = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4);
  const coat = new THREE.InstancedBufferAttribute(new Float32Array(n * 3).fill(1), 3);
  const hat = new THREE.InstancedBufferAttribute(new Float32Array(n * 3).fill(1), 3);
  const scarf = new THREE.InstancedBufferAttribute(new Float32Array(n * 3).fill(1), 3);
  const mug = new THREE.InstancedBufferAttribute(new Float32Array(n), 1);
  for (const a of [clipA, coat, hat, scarf, mug]) a.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('vatClip', clipA);
  geo.setAttribute('iCoat', coat);
  geo.setAttribute('iHat', hat);
  geo.setAttribute('iScarf', scarf);
  geo.setAttribute('iMug', mug);
  const mesh = new THREE.InstancedMesh(geo, vatMaterial(baked, { ao, lift, time }), n);
  mesh.name = 'crowd_far';
  mesh.frustumCulled = false; // instances spread over the square; one bound would be the whole market anyway
  mesh.castShadow = false; // beyond 25 m a figure's shadow is a few pixels: not worth a shadow-pass draw
  mesh.receiveShadow = false;
  mesh.count = 0;
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  const slots = []; // slot -> person
  const live = new Set();
  let used = 0;
  const api = {
    mesh, baked,
    get visibleCount() { return live.size; },
    /** Reserve a slot for a person with their colours (defaults: the figure's own) and mug. */
    add(person, { coat: cc, hat: hh, scarf: ss, mug: mm } = {}) {
      if (used >= n) return -1;
      const s = used++;
      slots[s] = person;
      const put = (attr, hex, def) => { const c = new THREE.Color(hex || def || '#ffffff'); attr.setXYZ(s, c.r, c.g, c.b); };
      put(coat, cc, colors?.coat); put(hat, hh, colors?.hat); put(scarf, ss, colors?.scarf);
      mug.setX(s, mm ? 1 : 0);
      coat.needsUpdate = hat.needsUpdate = scarf.needsUpdate = mug.needsUpdate = true;
      mesh.setMatrixAt(s, zero);
      mesh.count = used;
      return s;
    },
    /** Draw slot s at the world matrix m playing clip (name) from phase (s) at speed. */
    show(s, m, clipName, phase = 0, speed = 1) {
      if (s < 0) return false;
      const c = baked.clips.get(clipName) || baked.clips.values().next().value;
      if (!c) return false;
      // phase in seconds of the clip -> the shader's frame offset (vatTime * speed + phase) * fps
      const ph = ((phase % c.duration) + c.duration) % c.duration;
      clipA.setXYZW(s, c.start, c.frames, ph * (c.frames / c.duration) / VAT_FPS, speed * (c.frames / c.duration) / VAT_FPS);
      clipA.needsUpdate = true;
      mesh.setMatrixAt(s, m);
      mesh.instanceMatrix.needsUpdate = true;
      live.add(s);
      return true;
    },
    move(s, m) { if (s < 0 || !live.has(s)) return; mesh.setMatrixAt(s, m); mesh.instanceMatrix.needsUpdate = true; },
    hide(s) { if (s < 0 || !live.has(s)) return; live.delete(s); mesh.setMatrixAt(s, zero); mesh.instanceMatrix.needsUpdate = true; },
    dispose() { mesh.removeFromParent(); geo.dispose(); mesh.material.dispose(); },
  };
  return api;
}
