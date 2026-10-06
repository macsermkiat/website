// Thin clear glass without three's transmission pass (round 10).
//
// The vendors' glass (vendor_glass, vendor_glass_pint: white, rough 0.03, transmission 1, no thickness) is
// "thin-walled" glass: three draws it by rendering every opaque object of the frame a second time into a
// transmission target and reading back the background behind each glass pixel. That second pass doubles the
// opaque draw calls of every frame in which any such glass is on screen (from the overview: always).
//
// For thin glass of a white colour the transmission term is just the background weakened by the Fresnel
// reflectance: pixel = (1 - F) · background + specular. Blending does that without the pass: the glass draws its
// specular (its base colour black, so no diffuse) with alpha F and the blend ONE, ONE_MINUS_SRC_ALPHA, which
// gives specular + (1 - F) · what is behind it. With fog the alpha is 1 - (1 - fog)(1 - F), which is three's own
// fog over the transmitted pixel. The glass stays in front of the same things (it writes depth as before); the
// only difference left is that three's background sample leaves out transparent things behind the glass and is
// blurred by a fraction of a mip level at this roughness.
//
// The Fresnel alpha is added to the end of the standard shader (dithering_fragment, under a define, so a probe's
// material clone keeps it). The shop's glass harmonica (shop/harmonica.js) multiplies its own rim alpha in
// (NM_GLASS_FA). The material keeps opacity < 1 and stays transparent, so the lighting module still gives it a
// local reflection probe as it did for transmission.
import * as THREE from 'three';

let patched = false;
function patchChunk() {
  if (patched) return;
  patched = true;
  THREE.ShaderChunk.dithering_fragment += /* glsl */ `
#ifdef NM_GLASS_BLEND
  {
    float nmGlassF = EnvironmentBRDF( normal, geometryViewDir, material.specularColorBlended, material.specularF90, material.roughness ).g;
    #ifdef USE_FOG
      nmGlassF = 1.0 - ( 1.0 - fogFactor ) * ( 1.0 - nmGlassF );
    #endif
    #ifdef NM_GLASS_FA
      nmGlassF *= nmGlassFa;
    #endif
    gl_FragColor.a = nmGlassF;
  }
#endif`;
}

/** Is this the thin white transmissive glass the blend reproduces? */
export function isThinGlass(m) {
  return !!m && m.isMeshPhysicalMaterial && m.transmission >= 0.999 && !(m.thickness > 0) && !m.transmissionMap && !m.thicknessMap
    && !m.map && !m.alphaMap && !(m.dispersion > 0) && !m.transparent && !(m.alphaTest > 0) && !(m.clearcoat > 0) && !(m.sheen > 0) && !(m.iridescence > 0)
    && m.color.r >= 0.99 && m.color.g >= 0.99 && m.color.b >= 0.99 && !(m.metalness > 0);
}

const OFF = typeof location !== 'undefined' && new URLSearchParams(location.search).get('glass') === '0';

/** Swap one material's transmission for the blend, if it is thin white glass (and ?glass=0 is not set). */
export function toThinGlass(m) {
  if (OFF || !m || m.userData.thinGlass || !isThinGlass(m)) return false;
  patchChunk();
  m.userData.thinGlass = true;
  m.transmission = 0;
  m.color.setRGB(0, 0, 0);
  m.transparent = true;
  m.opacity = 0.5; // not used for the blend (the alpha is the Fresnel term)
  m.depthWrite = true;
  m.blending = THREE.CustomBlending;
  m.blendSrc = THREE.OneFactor;
  m.blendDst = THREE.OneMinusSrcAlphaFactor;
  m.blendSrcAlpha = THREE.OneFactor;
  m.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
  m.defines = { ...(m.defines || {}), NM_GLASS_BLEND: '' };
  m.needsUpdate = true;
  return true;
}

/** Swap the transmission of every thin white glass under `root` for the blend. Returns how many materials. */
export function thinGlass(root) {
  let n = 0;
  root.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) if (toThinGlass(m)) n++;
  });
  return n;
}
