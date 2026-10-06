// The ornament shop's sparkle in the engine (round 9, ADR 0004 revision):
//   mirror_<n> (material mirror_foxed)  a planar reflection: the foxed pier glass doubles the baubles and bulbs. A
//       mirrored camera renders the market into a texture that the carpenter's own mirror material shows through its
//       foxing (rough spots reflect less). Full market: every frame while the visitor is near; lite: now and then.
//   tinsel_<n>                         a view-dependent glint: flecks of the foil catch the shop's lamp as the eye
//       moves, so the Lametta twinkles instead of lying flat
//   flame materials                    the candle pyramid's (and the Schwibbogen's) flames flicker
//   fx_smoke_<n>                       the Räuchermännchen smokes on his own: a thin, slow curl from his mouth
// (rot_pyramid turns with the market's spinners: engine/conventions.js reads its {"axis": "y"} extra.)
import * as THREE from 'three';
const NO_MIRROR = (() => { try { return new URLSearchParams(location.search).get('mirror') === '0'; } catch { return false; } })();

// ---------- the smoker's smoke: one thin curl, not a column of puffs ----------
let wispTex = null;
/** A soft, ragged wisp of smoke (several faint offset blobs, so no sprite reads as a disc). */
function wispTexture() {
  if (wispTex) return wispTex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 9; i++) {
    const x = 32 + (rnd() - 0.5) * 22, y = 32 + (rnd() - 0.5) * 22, r = 9 + rnd() * 14;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, `rgba(255,255,255,${0.16 + rnd() * 0.12})`); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  }
  wispTex = new THREE.CanvasTexture(c);
  wispTex.colorSpace = THREE.SRGBColorSpace;
  return wispTex;
}
/** Incense smoke rising from the Räuchermännchen's mouth: a thread that curls, slows, widens and thins out. */
function createWisp(scene, at, { lite }) {
  const N = lite ? 16 : 30, LIFE = 6.5, RISE = 0.6;
  let seed = 3;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const parts = [];
  for (let i = 0; i < N; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: wispTexture(), color: 0xd8d2c8, transparent: true, depthWrite: false, opacity: 0 }));
    sp.name = 'engine_smoke_wisp';
    sp.renderOrder = 2;
    scene.add(sp);
    parts.push({ sp, t: i / N, a: rnd(), b: rnd(), spin: (rnd() - 0.5) * 0.8 });
  }
  let T = 0;
  const w = {
    base: 0.22,
    update(dt, still) {
      if (!still) T += dt;
      for (const p of parts) {
        if (!still) { p.t += dt / LIFE; if (p.t >= 1) { p.t -= 1; p.a = rnd(); p.b = rnd(); } }
        const t = p.t;
        // the thread: a slow sideways curl that grows with height, and a breath of air leaning it one way
        const curl = 0.004 + 0.05 * t * t;
        const ph = T * 0.55 + t * 9 + p.a * 0.8;
        const x = Math.sin(ph) * curl + 0.07 * t * t + (p.a - 0.5) * 0.02 * t;
        const z = Math.cos(ph * 0.8) * curl * 0.7 + (p.b - 0.5) * 0.02 * t;
        p.sp.position.set(at.x + x, at.y + RISE * t * (1 - 0.3 * t), at.z + z);
        const sc = 0.012 + 0.13 * Math.pow(t, 1.3);
        p.sp.scale.set(sc, sc * (1.25 - 0.3 * t), 1);
        p.sp.material.rotation += dt * p.spin;
        // dense at the mouth, then thinning as it spreads
        const fade = Math.min(1, t / 0.06) * Math.pow(1 - t, 1.8);
        p.sp.material.opacity = w.base * 0.75 * fade * (0.6 + 0.4 * p.b);
        p.sp.visible = p.sp.material.opacity > 0.003;
      }
    },
    dispose() { for (const p of parts) { p.sp.removeFromParent(); p.sp.material.dispose(); } },
  };
  return w;
}

const near = (o, re, up = 2) => { for (let x = o, k = 0; x && k <= up; x = x.parent, k++) if (re.test(x.name || '')) return true; return false; };

export function createSparkle({ place, scene, camera, renderer, lite, motion }) {
  const mirrors = [];
  const tinsels = [];
  const flames = [];
  let smoke = null, smokeAt = null;
  const glint = { uGlintTime: { value: 0 }, uGlintKey: { value: new THREE.Vector3() }, uGlint: { value: lite ? 0.8 : 1.15 } };
  let frame = 0, renders = 0;

  // ---------- the mirror ----------
  const RT_W = lite ? 256 : 640;
  function makeMirror(mesh) {
    const g = mesh.geometry;
    if (!g.boundingBox) g.computeBoundingBox();
    const size = g.boundingBox.getSize(new THREE.Vector3());
    const aspect = Math.max(0.25, Math.min(4, size.x / Math.max(1e-3, size.y)));
    const rt = new THREE.WebGLRenderTarget(RT_W, Math.round(RT_W / aspect), { type: THREE.HalfFloatType, samples: 0 });
    rt.texture.name = 'engine_mirror_reflection';
    const M = { mesh, rt, cam: new THREE.PerspectiveCamera(), textureMatrix: new THREE.Matrix4(), uniforms: null, material: null, normal: new THREE.Vector3(), point: new THREE.Vector3(), seen: false };
    dressMirror(M);
    mesh.userData.live = true;
    // a streamed shop swaps in the full model's mesh and material: dress it again
    mesh.userData.afterGraft = () => { dressMirror(M); };
    return M;
  }
  function dressMirror(M) {
    const mat = Array.isArray(M.mesh.material) ? M.mesh.material[0] : M.mesh.material;
    if (!mat || M.material === mat) return;
    M.material = mat;
    M.uniforms = { tReflect: { value: M.rt.texture }, uReflectMatrix: { value: M.textureMatrix }, uReflect: { value: 1 } };
    const prev = mat.onBeforeCompile;
    mat.onBeforeCompile = (shader, r) => {
      prev?.call(mat, shader, r);
      Object.assign(shader.uniforms, M.uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nuniform mat4 uReflectMatrix;\nvarying vec4 vReflUv;')
        .replace('#include <project_vertex>', '#include <project_vertex>\nvReflUv = uReflectMatrix * vec4( transformed, 1.0 );');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform sampler2D tReflect;\nuniform float uReflect;\nvarying vec4 vReflUv;')
        .replace('#include <lights_fragment_maps>', `#include <lights_fragment_maps>
  {
    // the mirrored market, seen through the glass; a foxed spot (rough, less metal) reflects less of it
    vec3 refl = texture2DProj( tReflect, vReflUv ).rgb;
    float clean = 1.0 - smoothstep( 0.12, 0.42, roughnessFactor );
    #if defined( RE_IndirectSpecular )
      radiance = mix( radiance, refl * 1.6, uReflect * clean );
    #endif
  }`);
    };
    const key = mat.customProgramCacheKey?.bind(mat);
    mat.customProgramCacheKey = () => `${key ? key() : ''}|mirror`;
    mat.needsUpdate = true;
  }

  const _r = new THREE.Vector3(), _cw = new THREE.Vector3(), _look = new THREE.Vector3(), _rot = new THREE.Matrix4(), _target = new THREE.Vector3();
  const _plane = new THREE.Plane(), _clip = new THREE.Vector4(), _q = new THREE.Vector4(), _n = new THREE.Vector3(), _frustum = new THREE.Frustum(), _pm = new THREE.Matrix4(), _box = new THREE.Box3();
  /** Render one mirror's reflection (Reflector.js's oblique mirrored camera). */
  function renderMirror(M) {
    const mesh = M.mesh;
    mesh.updateWorldMatrix(true, false);
    // the glass: its own normals (the carpenter's flat grid faces three.js +Z), through its box centre
    const g = mesh.geometry;
    if (!g.boundingBox) g.computeBoundingBox();
    M.point.copy(g.boundingBox.getCenter(_r)).applyMatrix4(mesh.matrixWorld);
    const na = g.attributes.normal;
    if (na) { _n.set(0, 0, 0); for (let i = 0; i < Math.min(na.count, 8); i++) _n.x += na.getX(i), _n.y += na.getY(i), _n.z += na.getZ(i); M.normal.copy(_n.lengthSq() > 1e-8 ? _n : _n.set(0, 0, 1)).transformDirection(mesh.matrixWorld); }
    else M.normal.set(0, 0, 1).transformDirection(mesh.matrixWorld);
    camera.getWorldPosition(_cw);
    const view = _r.subVectors(M.point, _cw);
    if (view.dot(M.normal) > 0) return false; // seen from behind
    view.reflect(M.normal).negate().add(M.point);
    _rot.extractRotation(camera.matrixWorld);
    _look.set(0, 0, -1).applyMatrix4(_rot).add(_cw);
    _target.subVectors(M.point, _look).reflect(M.normal).negate().add(M.point);
    const vc = M.cam;
    vc.position.copy(view);
    vc.up.set(0, 1, 0).applyMatrix4(_rot).reflect(M.normal);
    vc.lookAt(_target);
    vc.far = camera.far;
    vc.updateMatrixWorld();
    vc.projectionMatrix.copy(camera.projectionMatrix);
    M.textureMatrix.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
    M.textureMatrix.multiply(vc.projectionMatrix).multiply(vc.matrixWorldInverse).multiply(mesh.matrixWorld);
    // oblique near plane on the mirror (nothing behind the glass is drawn)
    _plane.setFromNormalAndCoplanarPoint(M.normal, M.point).applyMatrix4(vc.matrixWorldInverse);
    _clip.set(_plane.normal.x, _plane.normal.y, _plane.normal.z, _plane.constant);
    const p = vc.projectionMatrix;
    _q.x = (Math.sign(_clip.x) + p.elements[8]) / p.elements[0];
    _q.y = (Math.sign(_clip.y) + p.elements[9]) / p.elements[5];
    _q.z = -1.0;
    _q.w = (1.0 + p.elements[10]) / p.elements[14];
    _clip.multiplyScalar(2.0 / _clip.dot(_q));
    p.elements[2] = _clip.x; p.elements[6] = _clip.y; p.elements[10] = _clip.z + 1.0; p.elements[14] = _clip.w;
    const was = { rt: renderer.getRenderTarget(), auto: renderer.shadowMap.autoUpdate, xr: renderer.xr.enabled };
    mesh.visible = false;
    renderer.shadowMap.autoUpdate = false;
    renderer.xr.enabled = false;
    renderer.setRenderTarget(M.rt);
    renderer.state.buffers.depth.setMask(true);
    if (renderer.autoClear === false) renderer.clear();
    renderer.render(scene, vc);
    renderer.setRenderTarget(was.rt);
    renderer.shadowMap.autoUpdate = was.auto;
    renderer.xr.enabled = was.xr;
    mesh.visible = true;
    renders++;
    M.seen = true;
    return true;
  }

  function mirrorInView(M) {
    _pm.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    _frustum.setFromProjectionMatrix(_pm);
    const g = M.mesh.geometry;
    if (!g.boundingBox) g.computeBoundingBox();
    _box.copy(g.boundingBox).applyMatrix4(M.mesh.matrixWorld);
    return _frustum.intersectsBox(_box);
  }

  // ---------- tinsel glint ----------
  function glintMaterial(m) {
    if (m.userData.glint) return m;
    const c = m.clone();
    c.userData.glint = true;
    c.name = `${m.name || 'tinsel'}_glint`;
    const tint = (c.color || new THREE.Color(1, 1, 1)).clone();
    const prev = c.onBeforeCompile;
    c.onBeforeCompile = (shader, r) => {
      prev?.call(c, shader, r);
      Object.assign(shader.uniforms, glint, { uGlintTint: { value: tint } });
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vGlintP;\nvarying vec3 vGlintW;\nvarying vec3 vGlintN;')
        .replace('#include <project_vertex>', `#include <project_vertex>
  vec4 gW = vec4( transformed, 1.0 );
  #ifdef USE_INSTANCING
    gW = instanceMatrix * gW;
  #endif
  gW = modelMatrix * gW;
  vGlintW = gW.xyz;
  vGlintP = transformed;
  vGlintN = normalize( mat3( modelMatrix ) * objectNormal );`);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
uniform float uGlintTime; uniform vec3 uGlintKey; uniform float uGlint; uniform vec3 uGlintTint;
varying vec3 vGlintP; varying vec3 vGlintW; varying vec3 vGlintN;
vec3 glintHash( vec3 p ) { p = fract( p * vec3( 443.897, 441.423, 437.195 ) ); p += dot( p, p.yxz + 19.19 ); return fract( ( p.xxy + p.yxx ) * p.zyx ); }`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
  {
    // each 3 mm fleck of foil has its own tilt: it flashes when it mirrors the lamp into the eye
    vec3 cell = floor( vGlintP * 330.0 );
    vec3 h = glintHash( cell );
    vec3 n = normalize( vGlintN * ( gl_FrontFacing ? 1.0 : -1.0 ) + ( h - 0.5 ) * 1.7 );
    vec3 V = normalize( cameraPosition - vGlintW );
    vec3 L = normalize( uGlintKey - vGlintW );
    float spec = pow( max( dot( reflect( -L, n ), V ), 0.0 ), 90.0 );
    // and a slow shimmer as the swags stir in the air
    float tw = 0.55 + 0.45 * sin( uGlintTime * ( 1.3 + h.z * 2.4 ) + h.x * 40.0 );
    float sparse = step( 0.55, h.y );
    totalEmissiveRadiance += uGlintTint * spec * tw * sparse * 14.0 * uGlint;
  }`);
    };
    const key = c.customProgramCacheKey?.bind(c);
    c.customProgramCacheKey = () => `${key ? key() : ''}|glint`;
    return c;
  }

  // ---------- find the parts ----------
  function scan() {
    mirrors.length = 0; tinsels.length = 0; flames.length = 0;
    place.root.traverse((o) => {
      if (!o.isMesh) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      if (/^mirror_/i.test(o.name || '') || near(o, /^mirror_\d/i) || mats.some((m) => /^mirror_foxed/i.test(m?.name || ''))) {
        if (mats.some((m) => /^mirror_foxed/i.test(m?.name || '')) || /^mirror_/i.test(o.name || '')) mirrors.push(makeMirror(o));
        return;
      }
      if (near(o, /^tinsel_/i)) {
        o.userData.live = true;
        const swap = (m) => glintMaterial(m);
        o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material);
        // the full model's material comes in with a streamed upgrade: glint it again
        o.userData.afterGraft = () => { o.material = Array.isArray(o.material) ? o.material.map(swap) : swap(o.material); };
        tinsels.push(o);
        return;
      }
      for (const m of mats) if (/^flame/i.test(m?.name || '') && !flames.some((f) => f.m === m) && !near(o, /^act_orn_candle_/i, 3)) flames.push({ m, base: m.emissiveIntensity || 1, ph: flames.length * 1.7 });
    });
    // the key light for the glint: the shop's lamp under the ceiling (light_0), else above the counter
    let key = null;
    place.root.traverse((o) => { if (!key && /^light_0/i.test(o.name || '')) key = o; });
    if (key) key.getWorldPosition(glint.uGlintKey.value);
    else glint.uGlintKey.value.copy(place.holder.localToWorld(new THREE.Vector3(0, 2.8, 0.5)));
    // the smoker's ambient smoke
    let fx = null;
    place.root.traverse((o) => { if (!fx && /^fx_smoke_/i.test(o.name || '')) fx = o; });
    if (fx && !smoke) {
      smokeAt = fx.getWorldPosition(new THREE.Vector3());
      smoke = createWisp(scene, smokeAt, { lite });
    }
  }
  scan();

  return {
    get mirrors() { return mirrors; },
    /** A streamed shop got its full model: find the parts again (materials and geometry changed). */
    refresh() { for (const M of mirrors) dressMirror(M); },
    /** Before the market is drawn: the mirror's reflection, when it can be seen. */
    beforeRender({ force = false } = {}) {
      if (NO_MIRROR) return;   // ?mirror=0, for measuring
      if (!mirrors.length) return;
      frame++;
      for (const M of mirrors) {
        const d = camera.position.distanceTo(M.point.lengthSq() ? M.point : place.holder.position);
        if (!force && d > 14) continue;
        // lite: a fresh reflection every 20th frame; full: every frame (the candles and baubles move in it)
        if (!force && lite && M.seen && frame % 20 !== 0) continue;
        if (!force && !mirrorInView(M)) continue;
        try { renderMirror(M); } catch (e) { console.warn('[shop] mirror', e); mirrors.splice(mirrors.indexOf(M), 1); }
      }
    },
    update(dt, t, still) {
      glint.uGlintTime.value = still ? 0 : t;
      for (const f of flames) f.m.emissiveIntensity = f.base * (still ? 1 : 0.86 + 0.1 * Math.sin(t * 11.3 + f.ph) + 0.06 * Math.sin(t * 23.7 + f.ph * 2.3) + 0.05 * Math.sin(t * 3.1 + f.ph));
      if (smoke) {
        const d = camera.position.distanceTo(smokeAt);
        smoke.base = d < 30 ? 0.22 : 0;
        smoke.update(dt, still);
      }
    },
    stats: () => ({ mirrors: mirrors.length, mirrorRenders: renders, mirrorSize: mirrors[0] ? [mirrors[0].rt.width, mirrors[0].rt.height] : null, tinsels: tinsels.length, glintMaterials: tinsels.filter((o) => (Array.isArray(o.material) ? o.material : [o.material]).every((m) => m.userData.glint)).length, flames: flames.length, flameGlow: flames[0] ? +flames[0].m.emissiveIntensity.toFixed(3) : null, smoke: smoke ? +smoke.base.toFixed(3) : null }),
    dispose() { for (const M of mirrors) M.rt.dispose(); smoke?.dispose(); },
  };
}
