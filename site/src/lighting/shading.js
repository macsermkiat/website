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
//      - stall interiors: every section and deco stall gets a one-sided glow at its light_ empty,
//        so a stall reads warm from the home view even when the light budget gave it no real light
//        (and, where it has one, the glow stands in for the light its walls bounce).
//    A glow is a segment (a == b for a point) with a colour × intensity, a reach, a floor and a
//    ceiling (world y; nothing outside that band is lit) and a side: two-sided glows (the bulbs)
//    wrap light around a surface, one-sided ones (interiors) light only faces turned toward them,
//    so an interior glow cannot shine out through the stall's own walls. They are not three.js
//    lights, so they do not multiply the cost of every light in the scene.
//
// 3. Moon rim: a faint cool sheen on grazing edges that face the moon (added as radiance, so it
//    shows on near-black coats too), only on dark materials, so figures and posts in front of the
//    stalls read as moonlit shapes instead of black cut-outs while wood walls stay dark.
//
// 4. Interior clip (lite): a point light inside a stall with no shadow would light everything
//    around it: the gable's barge boards, the eave, the edges of the wall planks seen through their
//    gaps, the ground. A clip box in the stall's frame (its inner walls, floor band and roof, with a
//    little room in front below the fascia for the counter top and mugs) limits such a light to the
//    stall's interior, the way the one-sided interior glow is limited. Each clip is keyed by its
//    light's world position, so three's light order does not matter.
//
// 5. Softer point-light shadows: three samples a point light's cube shadow with 5 taps; this takes
//    `pointShadowTaps` (12) over the same Vogel disk, so the wide kernel of the interior lights
//    (a lamp has a size) stays smooth instead of grainy. Only fragments within a light's reach pay.
//
// The uniform data is one Float32Array shared by reference (UniformsUtils.clone keeps typed arrays
// by reference), so updating it once updates every material.
import * as THREE from 'three';

const LIT = ['standard', 'physical', 'lambert', 'phong', 'toon'];
const KEYS = ['lights_pars_begin', 'lights_fragment_begin', 'lights_fragment_end', 'lights_physical_pars_fragment', 'shadowmap_pars_fragment'];
// vec4s: [glowCount, rimStrength, rimPower, clipCount], [rimDir, darkLo], [rimColor, darkHi],
// [town wash colour × intensity, -], [wash inner radius, outer radius, height falloff, facing share],
// round 4: [figure fill colour × intensity, fill near], [fill far, highlight knee, highlight range, cloth specular]
const HEADER = 7;
// vec4s per clip: [light world pos, fade], [box centre, cos yaw], [half size, sin yaw],
// [front extra, front cut, roof slope, ridge z] (box frame; the roof is a tent whose ridge is the box top)
const CLIP = 4;
const OPEN = 1e4; // floor / ceiling of a glow with no height limit
const f = (x) => Number(x).toFixed(4);

export function installShading({ maxGlows = 16, maxClips = 4, minRoughness = 0.3, minClearcoatRoughness = 0.3, pointShadowTaps = 12, ao = null } = {}) {
  const saved = Object.fromEntries(KEYS.map((k) => [k, THREE.ShaderChunk[k]]));
  const CLIP0 = HEADER + maxGlows * 3;
  const size = CLIP0 + Math.max(1, maxClips) * CLIP;
  const data = new Float32Array(size * 4);
  data.set([0, 0, 3, 0, 0, 1, 0, 0.07, 0, 0, 0, 0.16, 0, 0, 0, 0, 1e4, 1e4 + 1, 1, 0, 0, 0, 0, 4, 8, 1e4, 1, 1]); // no rim, town wash or figure fill until set

  THREE.ShaderChunk.lights_pars_begin = saved.lights_pars_begin + /* glsl */ `
uniform vec4 lightingGlow[ ${size} ];
// round 2, fix pass: the baked ambient occlusion of a model that ships one (the carpenter's stalls,
// glTF occlusionTexture). three applies it to the hemisphere and the environment only; the lighting
// also applies it to its local glows (they stand in for bounce light) and in part to the short-reach
// interior lamps, whose light in a real stall is half bounce and is blocked in the corners
float lightingAO() {
  #ifdef USE_AOMAP
    return ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
  #else
    return 1.0;
  #endif
}
// 1 inside the clip box of the point light at lightView (view space), 0 outside, a short fade between;
// 1 for a light with no clip
float lightingClip( vec3 lightView, vec3 posView ) {
  int n = int( lightingGlow[ 0 ].w );
  if ( n == 0 ) return 1.0;
  mat3 toWorld = transpose( mat3( viewMatrix ) );
  vec3 lw = toWorld * ( lightView - viewMatrix[ 3 ].xyz );
  for ( int i = 0; i < ${Math.max(1, maxClips)}; i ++ ) {
    if ( i >= n ) break;
    vec4 c0 = lightingGlow[ ${CLIP0} + i * ${CLIP} ];
    vec3 dl = lw - c0.xyz;
    if ( dot( dl, dl ) > 1e-4 ) continue;
    vec4 c1 = lightingGlow[ ${CLIP0} + i * ${CLIP} + 1 ];
    vec4 c2 = lightingGlow[ ${CLIP0} + i * ${CLIP} + 2 ];
    vec4 c3 = lightingGlow[ ${CLIP0} + i * ${CLIP} + 3 ];
    vec3 d = toWorld * ( posView - viewMatrix[ 3 ].xyz ) - c1.xyz;
    vec3 q = vec3( c1.w * d.x - c2.w * d.z, d.y, c2.w * d.x + c1.w * d.z ); // the stall's frame
    float front = c2.z + ( q.y < c3.y ? c3.x : 0.0 ); // room in front below the fascia (counter, mugs)
    float roof = c2.y - c3.z * abs( q.z - c3.w ); // under the roof's slopes, not just its ridge
    float e = min( min( c2.x - abs( q.x ), min( c2.y + q.y, roof - q.y ) ), min( c2.z + q.z, front - q.z ) );
    return clamp( e / c0.w, 0.0, 1.0 );
  }
  return 1.0;
}
`;

  const pointInfo = 'getPointLightInfo( pointLight, geometryPosition, directLight );';
  if (saved.lights_fragment_begin.includes(pointInfo)) {
    THREE.ShaderChunk.lights_fragment_begin = saved.lights_fragment_begin.replace(pointInfo,
      `${pointInfo}\n\t\tdirectLight.color *= lightingClip( pointLight.position, geometryPosition );` +
      (ao && ao.point > 0 ? `\n\t\tif ( pointLight.distance > 0.0 && pointLight.distance < ${f(ao.pointMaxDistance ?? 6)} ) directLight.color *= mix( 1.0, lightingAO(), ${f(ao.point)} );` : ''));
  } else {
    console.warn('[lighting] three changed the point-light loop; interior clips not installed');
  }

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
    vec4 gc = lightingGlow[ ${HEADER} + i * 3 + 2 ];
    vec3 ab = gb.xyz - ga.xyz;
    float h = clamp( dot( gp - ga.xyz, ab ) / max( dot( ab, ab ), 1e-4 ), 0.0, 1.0 );
    vec3 dl = ga.xyz + ab * h - gp;
    float d2 = dot( dl, dl );
    float r2 = ga.w * ga.w; // the sign of ga.w is the side flag, its square the reach
    if ( d2 >= r2 ) continue;
    // floor and ceiling (world y), each with a 15 cm fade
    float band = clamp( ( gp.y - gb.w ) / 0.15, 0.0, 1.0 ) * clamp( ( gc.w - gp.y ) / 0.15, 0.0, 1.0 );
    float win = 1.0 - d2 / r2;
    // reach > 0: half-wrapped (a line of bulbs lights a surface from many directions at once);
    // reach < 0 (stored as -reach): one-sided Lambert, so an interior glow stops at its walls
    float cosT = dot( gn, dl * inversesqrt( max( d2, 1e-6 ) ) );
    float ndl = ga.w > 0.0 ? clamp( cosT * 0.6 + 0.4, 0.0, 1.0 ) : max( cosT, 0.0 );
    glowIrr += gc.rgb * ( band * win * win * ndl / ( d2 + 0.12 ) );
  }
  // town wash: the facades of the town ring (world radius past lightingGlow[4].x) catch the market's
  // glow and their own street lamps: warm light on walls that face the square, strongest at street
  // level and fading up the facade, so the timbering and doors read while the roofs and upper storeys
  // stay in the blue night
  {
    vec4 tw = lightingGlow[ 3 ];
    vec4 tp = lightingGlow[ 4 ];
    float rr = length( gp.xz );
    float town = smoothstep( tp.x, tp.y, rr );
    if ( town > 0.0 ) {
      float vert = 1.0 - gn.y * gn.y;
      float facing = clamp( dot( normalize( gn.xz + 1e-5 ), -gp.xz / max( rr, 1e-3 ) ), 0.0, 1.0 );
      float lift = exp( -max( gp.y, 0.0 ) / tp.z );
      glowIrr += tw.rgb * ( town * vert * lift * ( 1.0 - tp.w + tp.w * facing ) );
    }
  }
  // moon rim: a faint cool sheen on grazing edges that face the moon. It is added as radiance, not
  // multiplied by the albedo, the way wool and skin catch light at grazing angles, so near-black
  // coats still show their outline
  // coats: only on steep faces (figures, posts, walls), not on the ground or the roofs
  // and only on dark materials (coats, iron posts): wood walls stay near-black on their moon side
  float rimF = pow( 1.0 - clamp( dot( gn, gv ), 0.0, 1.0 ), lightingGlow[ 0 ].z ) * ( 1.0 - gn.y * gn.y );
  vec3 rimAlbedo = material.diffuseColor;
  rimF *= 1.0 - smoothstep( lightingGlow[ 1 ].w, lightingGlow[ 2 ].w, max( rimAlbedo.r, max( rimAlbedo.g, rimAlbedo.b ) ) );
  totalEmissiveRadiance += lightingGlow[ 2 ].rgb * ( lightingGlow[ 0 ].y * rimF * clamp( dot( gn, lightingGlow[ 1 ].xyz ) * 0.5 + 0.5, 0.0, 1.0 ) );
  ${ao && ao.glow > 0 ? `glowIrr *= mix( 1.0, lightingAO(), ${f(ao.glow)} );` : ''}
  #if defined( STANDARD )
    reflectedLight.directDiffuse += glowIrr * BRDF_Lambert( material.diffuseContribution );
  #else
    reflectedLight.directDiffuse += glowIrr * BRDF_Lambert( material.diffuseColor );
  #endif
  // round 4: figures (the crowd and the vendors; materials marked LIGHTING_FIGURE by the module).
  // A vendor stands right under his stall's interior lamp, 0.7 m over his head: the light hits his
  // shoulders, sleeves and a pale scarf from above at 30-50x what it gives the back wall per unit of
  // albedo, so light cloth blew out to white while his face, vertical and turned away from the lamp,
  // stayed a dark smudge. Two terms, both only on figures:
  //  - a highlight shoulder: the direct light on a figure is linear up to the knee (radiance, linear)
  //    and rolls off softly above it, hue kept, so a white sleeve under the lamp reads as lit cloth;
  //    the cloth's specular is scaled too (wool has no sheen to speak of);
  //  - a soft warm fill from the viewer's side (the light the counter, the cobbles and the crowd
  //    bounce back at a figure's face), fading in between fill far and fill near metres from the
  //    camera, so close-ups read and the home view's crowd is unchanged
  #ifdef LIGHTING_FIGURE
  {
    vec4 fa = lightingGlow[ 5 ];
    vec4 fb = lightingGlow[ 6 ];
    reflectedLight.directSpecular *= fb.w;
    vec3 dsum = reflectedLight.directDiffuse + reflectedLight.directSpecular;
    float lum = dot( dsum, vec3( 0.2126, 0.7152, 0.0722 ) );
    if ( lum > fb.y ) {
      float over = lum - fb.y;
      float k = ( fb.y + over / ( 1.0 + over / fb.z ) ) / lum;
      reflectedLight.directDiffuse *= k;
      reflectedLight.directSpecular *= k;
    }
    float near = 1.0 - smoothstep( fa.w, fb.x, length( geometryPosition ) );
    float facing = clamp( dot( geometryNormal, geometryViewDir ), 0.0, 1.0 );
    vec3 fillIrr = fa.rgb * ( near * ( 0.25 + 0.75 * facing ) );
    #if defined( STANDARD )
      reflectedLight.directDiffuse += fillIrr * BRDF_Lambert( material.diffuseContribution );
    #else
      reflectedLight.directDiffuse += fillIrr * BRDF_Lambert( material.diffuseColor );
    #endif
  }
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

  // point-light shadows: N taps over the Vogel disk instead of 5
  const five = /vec2 sample0 = vogelDiskSample\( 0, 5, phi \);[\s\S]*?\) \* 0\.2;/;
  const pcfCube = saved.shadowmap_pars_fragment.indexOf('samplerCubeShadow shadowMap');
  const tail = pcfCube >= 0 ? saved.shadowmap_pars_fragment.slice(pcfCube) : '';
  if (pointShadowTaps > 5 && five.test(tail)) {
    const taps = Math.round(pointShadowTaps);
    THREE.ShaderChunk.shadowmap_pars_fragment = saved.shadowmap_pars_fragment.slice(0, pcfCube) + tail.replace(five, /* glsl */ `shadow = 0.0;
			for ( int k = 0; k < ${taps}; k ++ ) {
				vec2 sk = vogelDiskSample( k, ${taps}, phi );
				shadow += texture( shadowMap, vec4( bd3D + ( tangent * sk.x + bitangent * sk.y ) * texelSize, dp ) );
			}
			shadow *= ${(1 / taps).toFixed(6)};`);
  } else if (pointShadowTaps > 5) {
    console.warn('[lighting] three changed getPointShadow; point shadows keep 5 taps');
  }

  const libUniforms = LIT.map((k) => THREE.ShaderLib[k]?.uniforms).filter(Boolean);
  libUniforms.forEach((u) => (u.lightingGlow = { value: data }));

  const glows = [];
  const clips = [];
  const _c = new THREE.Vector3(), _m = new THREE.Vector3(), _w = new THREE.Vector3();
  function writeClips() {
    const n = Math.min(clips.length, maxClips);
    for (let i = 0; i < n; i++) {
      const c = clips[i];
      c.light.updateWorldMatrix(true, false);
      c.light.getWorldPosition(_w);
      data.set([_w.x, _w.y, _w.z, c.fade, c.center.x, c.center.y, c.center.z, c.cos, c.half.x, c.half.y, c.half.z, c.sin, c.front, c.cut, c.slope || 0, c.ridge || 0], (CLIP0 + i * CLIP) * 4);
    }
    data[3] = n;
  }

  return {
    data,
    maxGlows,
    /**
     * Add a glow: { a:[x,y,z] | Vector3, b?, color: Color | [r,g,b] (linear), intensity, reach, tag,
     * oneSided?, floor?, ceiling? (world y), priority? (higher wins a slot first) }.
     * Returns the entry; remove(entry) takes it out again.
     */
    add(g) {
      const e = {
        a: new THREE.Vector3().copy(g.a),
        b: new THREE.Vector3().copy(g.b || g.a),
        color: g.color?.isColor ? g.color.clone() : new THREE.Color().setRGB(...(g.color || [1, 0.6, 0.3])),
        intensity: g.intensity ?? 1,
        reach: g.reach ?? 1,
        oneSided: !!g.oneSided,
        floor: g.floor ?? -OPEN,
        ceiling: g.ceiling ?? OPEN,
        tag: g.tag || 'glow',
        priority: g.priority ?? 0,
        scale: 1,
        id: g.id, how: g.how, // for diagnostics
      };
      glows.push(e);
      return e;
    },
    remove(e) {
      const i = glows.indexOf(e);
      if (i >= 0) glows.splice(i, 1);
    },
    get glows() { return glows; },
    /**
     * Clip a point light to a box: { light, center: Vector3 (world), half: Vector3 (m, in the box's
     * frame), cos, sin (its yaw), fade (m), front (extra room in front, m), cut (box-frame y below
     * which that room applies), slope, ridge (the roof: box-frame z of its ridge, and how fast it drops
     * from the box top either side of it) }. Returns the entry; removeClip(entry) takes it out again.
     */
    addClip(c) {
      if (clips.length >= maxClips) { console.warn('[lighting] no clip slot left for', c.light?.name); return null; }
      const e = { fade: 0.01, front: 0, cut: -1e4, cos: 1, sin: 0, ...c, center: c.center.clone(), half: c.half.clone() };
      clips.push(e);
      writeClips();
      return e;
    },
    removeClip(e) {
      const i = clips.indexOf(e);
      if (i >= 0) clips.splice(i, 1);
      writeClips();
    },
    get clips() { return clips; },
    /** dark: [lo, hi] albedo over which the rim fades out (it shows only on dark materials). */
    setRim(dir, color, strength, power = 3, dark = [0.07, 0.16]) {
      const d = new THREE.Vector3().copy(dir).normalize();
      data.set([data[0], strength, power, data[3], d.x, d.y, d.z, dark[0], color.r, color.g, color.b, dark[1]], 0);
    },
    setRimStrength(s) { data[1] = s; },
    /** Round 4, figures: fill colour (linear Color) × intensity, fill near/far (m from the camera), highlight knee and range (linear radiance), cloth specular share. */
    setFigure(color, intensity, near, far, knee, range, spec) {
      data.set([color.r * intensity, color.g * intensity, color.b * intensity, near, far, knee, range, spec], 20);
    },
    /** The town wash: colour (linear Color) × intensity, from radius r0 (0) to r1 (full), height falloff, facing share. */
    setTownWash(color, intensity, r0, r1, height, facing) {
      data.set([color.r * intensity, color.g * intensity, color.b * intensity, 0, r0, r1, height, facing], 12);
    },
    /** Write the glows nearest `from` (a Vector3) into the shared uniform. */
    update(from, gain = 1) {
      const ranked = glows
        .filter((e) => e.intensity * e.scale > 0)
        .map((e) => {
          _m.addVectors(e.a, e.b).multiplyScalar(0.5);
          // priority first (stall interiors before bulb strings), then distance
          return { e, d: _m.distanceToSquared(from) - e.priority * 1e6 };
        })
        .sort((x, y) => x.d - y.d)
        .slice(0, maxGlows);
      ranked.forEach(({ e }, i) => {
        const o = (HEADER + i * 3) * 4;
        const k = e.intensity * e.scale * gain;
        data[o] = e.a.x; data[o + 1] = e.a.y; data[o + 2] = e.a.z; data[o + 3] = e.oneSided ? -e.reach : e.reach;
        data[o + 4] = e.b.x; data[o + 5] = e.b.y; data[o + 6] = e.b.z; data[o + 7] = e.floor;
        data[o + 8] = e.color.r * k; data[o + 9] = e.color.g * k; data[o + 10] = e.color.b * k; data[o + 11] = e.ceiling;
      });
      data[0] = ranked.length;
      writeClips();
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
