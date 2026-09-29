// Three small additions to three's lit materials, installed by patching the shader chunks (like the
// fog), so every built-in lit material in the scene picks them up with no per-model work:
//
// 1. Light size. three's point and spot lights are infinitely small, so on glossy copper or a
//    clear-coated mug their reflection is a single blazing pixel that blooms into a glare star.
//    Real lamps have a size. For direct light only, roughness and clear-coat roughness get a floor
//    (the usual "sphere light" roughness widening); reflections of the environment stay sharp.
//
// 2. Local glows: cheap diffuse-only light, no shadow, short reach, evaluated in the fragment shader
//    from a small shared uniform array. Used for
//      - bulb strings: each string of bulbs_ is a line light about 1 m in reach, so the garland,
//        the lambrequin and the fascia are lit by their bulbs, as in Cycles;
//      - bounce: a dim fill inside a shadowed stall, standing in for light bounced off the walls.
//    A glow is a segment (a == b for a point) with a colour × intensity and a reach. They are not
//    three.js lights, so they do not multiply the cost of every light in the scene.
//
// 3. Moon rim: a faint cool sheen on grazing edges that face the moon (added as radiance, so it
//    shows on near-black coats too), so figures and posts in front of the stalls read as moonlit
//    shapes instead of black cut-outs.
//
// The uniform data is one Float32Array shared by reference (UniformsUtils.clone keeps typed arrays
// by reference), so updating it once updates every material.
import * as THREE from 'three';

const LIT = ['standard', 'physical', 'lambert', 'phong', 'toon'];
const KEYS = ['lights_pars_begin', 'lights_fragment_end', 'lights_physical_pars_fragment'];
const HEADER = 3; // vec4s: [count, rimStrength, rimPower, 0], [rimDir, 0], [rimColor, 0]
const f = (x) => Number(x).toFixed(4);

export function installShading({ maxGlows = 16, minRoughness = 0.3, minClearcoatRoughness = 0.3 } = {}) {
  const saved = Object.fromEntries(KEYS.map((k) => [k, THREE.ShaderChunk[k]]));
  const size = HEADER + maxGlows * 3;
  const data = new Float32Array(size * 4);

  THREE.ShaderChunk.lights_pars_begin = saved.lights_pars_begin + /* glsl */ `
uniform vec4 lightingGlow[ ${size} ];
`;

  // local glows and the moon rim, added as direct diffuse light before the indirect terms
  THREE.ShaderChunk.lights_fragment_end = /* glsl */ `
{
  mat3 glowToWorld = transpose( mat3( viewMatrix ) );
  vec3 gp = glowToWorld * ( geometryPosition - viewMatrix[ 3 ].xyz );
  vec3 gn = glowToWorld * geometryNormal;
  vec3 gv = glowToWorld * geometryViewDir;
  vec3 glowIrr = vec3( 0.0 );
  int glowCount = int( lightingGlow[ 0 ].x );
  for ( int i = 0; i < ${maxGlows}; i ++ ) {
    if ( i >= glowCount ) break;
    vec4 ga = lightingGlow[ ${HEADER} + i * 3 ];
    vec4 gb = lightingGlow[ ${HEADER} + i * 3 + 1 ];
    vec3 ab = gb.xyz - ga.xyz;
    float h = clamp( dot( gp - ga.xyz, ab ) / max( dot( ab, ab ), 1e-4 ), 0.0, 1.0 );
    vec3 dl = ga.xyz + ab * h - gp;
    float d2 = dot( dl, dl );
    float r2 = ga.w * ga.w;
    if ( d2 >= r2 ) continue;
    float win = 1.0 - d2 / r2;
    // half-wrapped: a line of bulbs lights a surface from many directions at once
    float ndl = clamp( dot( gn, dl * inversesqrt( max( d2, 1e-6 ) ) ) * 0.6 + 0.4, 0.0, 1.0 );
    glowIrr += lightingGlow[ ${HEADER} + i * 3 + 2 ].rgb * ( win * win * ndl / ( d2 + 0.12 ) );
  }
  // moon rim: a faint cool sheen on grazing edges that face the moon. It is added as radiance, not
  // multiplied by the albedo, the way wool and skin catch light at grazing angles, so near-black
  // coats still show their outline
  // coats: only on steep faces (figures, posts, walls), not on the ground or the roofs
  float rimF = pow( 1.0 - clamp( dot( gn, gv ), 0.0, 1.0 ), lightingGlow[ 0 ].z ) * ( 1.0 - gn.y * gn.y );
  totalEmissiveRadiance += lightingGlow[ 2 ].rgb * ( lightingGlow[ 0 ].y * rimF * clamp( dot( gn, lightingGlow[ 1 ].xyz ) * 0.5 + 0.5, 0.0, 1.0 ) );
  #if defined( STANDARD )
    reflectedLight.directDiffuse += glowIrr * BRDF_Lambert( material.diffuseContribution );
  #else
    reflectedLight.directDiffuse += glowIrr * BRDF_Lambert( material.diffuseColor );
  #endif
}
` + saved.lights_fragment_end;

  // light size: a roughness floor for direct light only
  const sig = /void RE_Direct_Physical\(([^)]*)const in PhysicalMaterial material, inout ReflectedLight reflectedLight \) \{/;
  if (sig.test(saved.lights_physical_pars_fragment)) {
    THREE.ShaderChunk.lights_physical_pars_fragment = saved.lights_physical_pars_fragment.replace(sig, (m, args) => /* glsl */ `void RE_Direct_Physical(${args}const in PhysicalMaterial materialIn, inout ReflectedLight reflectedLight ) {
  PhysicalMaterial material = materialIn;
  material.roughness = max( material.roughness, ${f(minRoughness)} );
  #ifdef USE_CLEARCOAT
    material.clearcoatRoughness = max( material.clearcoatRoughness, ${f(minClearcoatRoughness)} );
  #endif`);
  } else {
    console.warn('[lighting] three changed RE_Direct_Physical; light-size roughness floor not installed');
  }

  const libUniforms = LIT.map((k) => THREE.ShaderLib[k]?.uniforms).filter(Boolean);
  libUniforms.forEach((u) => (u.lightingGlow = { value: data }));

  const glows = [];
  const _c = new THREE.Vector3(), _m = new THREE.Vector3();
  let rimSet = false;

  return {
    data,
    maxGlows,
    /**
     * Add a glow: { a:[x,y,z] | Vector3, b?, color: Color | [r,g,b] (linear), intensity, reach, tag }.
     * Returns the entry; remove(entry) takes it out again.
     */
    add(g) {
      const e = {
        a: new THREE.Vector3().copy(g.a),
        b: new THREE.Vector3().copy(g.b || g.a),
        color: g.color?.isColor ? g.color.clone() : new THREE.Color().setRGB(...(g.color || [1, 0.6, 0.3])),
        intensity: g.intensity ?? 1,
        reach: g.reach ?? 1,
        tag: g.tag || 'glow',
        priority: g.priority ?? 0,
        scale: 1,
      };
      glows.push(e);
      return e;
    },
    remove(e) {
      const i = glows.indexOf(e);
      if (i >= 0) glows.splice(i, 1);
    },
    get glows() { return glows; },
    setRim(dir, color, strength, power = 3) {
      const d = new THREE.Vector3().copy(dir).normalize();
      data.set([data[0], strength, power, 0, d.x, d.y, d.z, 0, color.r, color.g, color.b, 0], 0);
      rimSet = true;
    },
    setRimStrength(s) { data[1] = s; },
    /** Write the glows nearest `from` (a Vector3) into the shared uniform. */
    update(from, gain = 1) {
      if (!rimSet) data[2] = 3;
      const ranked = glows
        .filter((e) => e.intensity * e.scale > 0)
        .map((e) => {
          _m.addVectors(e.a, e.b).multiplyScalar(0.5);
          return { e, d: _m.distanceToSquared(from) - e.priority * 400 };
        })
        .sort((x, y) => x.d - y.d)
        .slice(0, maxGlows);
      ranked.forEach(({ e }, i) => {
        const o = (HEADER + i * 3) * 4;
        const k = e.intensity * e.scale * gain;
        data[o] = e.a.x; data[o + 1] = e.a.y; data[o + 2] = e.a.z; data[o + 3] = e.reach;
        data[o + 4] = e.b.x; data[o + 5] = e.b.y; data[o + 6] = e.b.z; data[o + 7] = 0;
        data[o + 8] = e.color.r * k; data[o + 9] = e.color.g * k; data[o + 10] = e.color.b * k; data[o + 11] = 0;
      });
      data[0] = ranked.length;
      return ranked.length;
    },
    /** Glow count off (for captures that should not see them), then back with update(). */
    off() { data[0] = 0; },
    restore() {
      for (const k of KEYS) THREE.ShaderChunk[k] = saved[k];
      libUniforms.forEach((u) => delete u.lightingGlow);
    },
    _c,
  };
}

/**
 * Line lights along the strings of a bulbs_ mesh: the bulbs' world positions are binned into 0.35 m
 * cells, neighbouring cells are joined into strings, and each string becomes one segment along
 * its longest horizontal extent (a straight line through a sagging string is close enough for a
 * light of 1 m reach). Returns [{ a, b, count }].
 */
export function bulbStrings(mesh) {
  const pos = mesh.geometry?.attributes?.position;
  if (!pos) return [];
  mesh.updateWorldMatrix(true, false);
  const cell = 0.35;
  const cells = new Map();
  const v = new THREE.Vector3();
  const m = new THREE.Matrix4();
  const instances = mesh.isInstancedMesh ? mesh.count : 1;
  const step = Math.max(1, Math.floor(pos.count / 4000));
  for (let k = 0; k < instances; k++) {
    if (mesh.isInstancedMesh) mesh.getMatrixAt(k, m).premultiply(mesh.matrixWorld);
    else m.copy(mesh.matrixWorld);
    const n = mesh.isInstancedMesh ? 1 : pos.count;
    for (let i = 0; i < n; i += step) {
      if (mesh.isInstancedMesh) v.set(0, 0, 0); else v.fromBufferAttribute(pos, i);
      v.applyMatrix4(m);
      const key = `${Math.floor(v.x / cell)},${Math.floor(v.y / cell)},${Math.floor(v.z / cell)}`;
      let c = cells.get(key);
      if (!c) cells.set(key, (c = { key, sum: new THREE.Vector3(), n: 0, min: v.clone(), max: v.clone() }));
      c.sum.add(v); c.n++; c.min.min(v); c.max.max(v);
    }
  }
  // connected components of cells (26-neighbourhood, one cell of gap allowed)
  const list = [...cells.values()];
  const idx = (c) => c.key.split(',').map(Number);
  const seen = new Set(), out = [];
  for (const c0 of list) {
    if (seen.has(c0.key)) continue;
    const comp = [], stack = [c0];
    seen.add(c0.key);
    while (stack.length) {
      const c = stack.pop();
      comp.push(c);
      const [x, y, z] = idx(c);
      for (let dx = -2; dx <= 2; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -2; dz <= 2; dz++) {
        const k = `${x + dx},${y + dy},${z + dz}`;
        const nb = cells.get(k);
        if (nb && !seen.has(k)) { seen.add(k); stack.push(nb); }
      }
    }
    // the string's direction: principal axis of its cells in plan
    let n = 0;
    const mid = new THREE.Vector3();
    comp.forEach((c) => { mid.add(c.sum); n += c.n; });
    mid.divideScalar(n);
    let xx = 0, xz = 0, zz = 0;
    const cs = comp.map((c) => c.sum.clone().divideScalar(c.n));
    cs.forEach((p) => { const dx = p.x - mid.x, dz = p.z - mid.z; xx += dx * dx; xz += dx * dz; zz += dz * dz; });
    const ang = 0.5 * Math.atan2(2 * xz, xx - zz);
    const dir = new THREE.Vector3(Math.cos(ang), 0, Math.sin(ang));
    let t0 = 0, t1 = 0;
    comp.forEach((c) => {
      for (const p of [c.min, c.max]) {
        const t = (p.x - mid.x) * dir.x + (p.z - mid.z) * dir.z;
        t0 = Math.min(t0, t); t1 = Math.max(t1, t);
      }
    });
    const a = mid.clone().addScaledVector(dir, t0), b = mid.clone().addScaledVector(dir, t1);
    let y0 = Infinity, y1 = -Infinity;
    comp.forEach((c) => { y0 = Math.min(y0, c.min.y); y1 = Math.max(y1, c.max.y); });
    out.push({ a, b, count: comp.length, height: y1 - y0 });
  }
  return out;
}
