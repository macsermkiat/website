// Exponential-squared fog with a ground mist: denser in the first few metres above the cobbles,
// thinning with height, so the town ring sinks into blue haze while roofs and the Ferris wheel
// stand out against the sky. Implemented by patching three's fog chunks (every built-in material
// picks it up); `restore()` puts the stock chunks back.
import * as THREE from 'three';

const KEYS = ['fog_pars_vertex', 'fog_vertex', 'fog_pars_fragment', 'fog_fragment'];

export function installHeightFog({ mist, mistHeight, base = 0 }) {
  const saved = Object.fromEntries(KEYS.map((k) => [k, THREE.ShaderChunk[k]]));
  const f = (x) => Number(x).toFixed(4);

  THREE.ShaderChunk.fog_pars_vertex = /* glsl */ `
#ifdef USE_FOG
  varying float vFogDepth;
  varying float vFogHeight;
#endif`;

  // world height from the view-space position (works for instanced, skinned, points and sprites)
  THREE.ShaderChunk.fog_vertex = /* glsl */ `
#ifdef USE_FOG
  vFogDepth = - mvPosition.z;
  vFogHeight = ( transpose( mat3( viewMatrix ) ) * ( mvPosition.xyz - viewMatrix[ 3 ].xyz ) ).y;
#endif`;

  THREE.ShaderChunk.fog_pars_fragment = /* glsl */ `
#ifdef USE_FOG
  uniform vec3 fogColor;
  varying float vFogDepth;
  varying float vFogHeight;
  #ifdef FOG_EXP2
    uniform float fogDensity;
  #else
    uniform float fogNear;
    uniform float fogFar;
  #endif
#endif`;

  THREE.ShaderChunk.fog_fragment = /* glsl */ `
#ifdef USE_FOG
  #ifdef FOG_EXP2
    float fogMist = 1.0 + ${f(mist)} * exp( - max( vFogHeight - ${f(base)}, 0.0 ) / ${f(mistHeight)} );
    float fogD = fogDensity * fogMist * vFogDepth;
    float fogFactor = 1.0 - exp( - fogD * fogD );
  #else
    float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
  #endif
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`;

  return {
    restore() {
      for (const k of KEYS) THREE.ShaderChunk[k] = saved[k];
    },
  };
}

/** Force materials already in the scene to recompile with the current chunks. */
export function recompile(scene) {
  scene.traverse((o) => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    for (const m of mats) if (m && m.fog !== false) m.needsUpdate = true;
  });
}
