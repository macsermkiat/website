// Thin clear glass without three's transmission pass (round 10).
//
// The vendors' glass (vendor_glass, vendor_glass_pint: white, rough 0.03, transmission 1, no thickness, tinted per
// bottle by its vertex colours) is "thin-walled" glass: three draws it by rendering every opaque object of the
// frame a second time into a transmission target and reading back the background behind each glass pixel. That
// second pass doubles the opaque draw calls of every frame in which any such glass is on screen.
//
// For thin glass three's pixel is: specular + (1 - F) · tint · background (F the Fresnel reflectance, the tint
// the base colour times the vertex colour), and fog over all of it. Two blended draws give the same without the
// pass, in the transparent pass where everything behind the glass is already drawn:
//   - the glass mesh itself multiplies what is behind it by (1 - F) · tint (blend ZERO, SRC_COLOR; with fog by
//     (1 - fog) · (1 - F) · tint),
//   - a child mesh on the same geometry, engine_glass_spec, adds the specular (blend ONE, ONE; the base colour
//     black, so no diffuse; three's fog adds fog · fog colour, which the multiply left room for).
// Both draw their two faces in one pass (multiplying and adding do not depend on order); a back face's specular,
// seen through the front face, is weakened by the glass's own transmittance. Neither writes depth. The child is
// drawn just after its glass (same depth, higher id). It casts no shadow and never takes a pick.
//
// The multiply may be scaled by a rim factor a (NM_GLASS_FA: the ornament shop's glass harmonica,
// shop/harmonica.js, whose shells were premultiplied glass with a Fresnel-like rim alpha over the transmission):
// then (1 - a) + a · (1 - fog) · (1 - F) · tint. The shader terms are added to the end of the standard shader under
// defines (Material.clone drops those: keepThinGlass puts them back on a copy, and the child does so before
// each draw).
// The glass stays transparent with opacity < 1, so the lighting module still gives it a local reflection probe as
// it did for transmission.
import * as THREE from 'three';

const RIM = 'mix( 0.1, 0.78, pow( 1.0 - clamp( abs( dot( geometryNormal, geometryViewDir ) ), 0.0, 1.0 ), 2.5 ) )';
let patched = false;
function patchChunk() {
  if (patched) return;
  patched = true;
  THREE.ShaderChunk.dithering_fragment += /* glsl */ `
#if defined( NM_GLASS_MUL ) || defined( NM_GLASS_ADD )
  {
    vec3 nmGlassF = EnvironmentBRDF( normal, geometryViewDir, material.specularColorBlended, material.specularF90, material.roughness );
    float nmGlassA = 1.0;
    #ifdef NM_GLASS_FA
      nmGlassA = ${RIM};
    #endif
    #ifdef NM_GLASS_MUL
      float nmGlassFog = 0.0;
      #ifdef USE_FOG
        nmGlassFog = fogFactor;
      #endif
      gl_FragColor = vec4( vec3( 1.0 - nmGlassA ) + ( 1.0 - nmGlassFog ) * nmGlassA * ( 1.0 - nmGlassF ) * diffuseColor.rgb, 1.0 );
    #else
      if ( ! gl_FrontFacing ) {
        #if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
          vec3 nmGlassTint = vColor.rgb;
        #else
          vec3 nmGlassTint = vec3( 1.0 );
        #endif
        #ifdef USE_FOG
          gl_FragColor.rgb -= fogFactor * fogColor;
        #endif
        gl_FragColor.rgb *= vec3( 1.0 - nmGlassA ) + nmGlassA * ( 1.0 - nmGlassF ) * nmGlassTint;
      }
      gl_FragColor.a = 1.0;
    #endif
  }
#endif`;
}

/** Is this the thin white transmissive glass the two draws reproduce? */
export function isThinGlass(m) {
  return !!m && m.isMeshPhysicalMaterial && m.transmission >= 0.999 && !(m.thickness > 0) && !m.transmissionMap && !m.thicknessMap
    && !m.map && !m.alphaMap && !(m.dispersion > 0) && !m.transparent && !(m.alphaTest > 0) && !(m.clearcoat > 0) && !(m.sheen > 0) && !(m.iridescence > 0)
    && m.color.r >= 0.99 && m.color.g >= 0.99 && m.color.b >= 0.99 && !(m.metalness > 0);
}

const OFF = typeof location !== 'undefined' && new URLSearchParams(location.search).get('glass') === '0';

/** Turn one material into the multiplying draw, if it is thin white glass (and ?glass=0 is not set). */
export function toThinGlass(m) {
  if (OFF || !m || m.userData.thinGlass || !isThinGlass(m)) return false;
  patchChunk();
  m.userData.thinGlass = true;
  m.transmission = 0;
  m.transparent = true;
  m.opacity = 0.5; // not used by the blend: it keeps the lighting module's reflection probe on the glass
  m.depthWrite = false;
  m.forceSinglePass = true;
  m.blending = THREE.CustomBlending;
  m.blendEquation = THREE.AddEquation;
  m.blendSrc = THREE.ZeroFactor;
  m.blendDst = THREE.SrcColorFactor;
  m.blendSrcAlpha = THREE.ZeroFactor;
  m.blendDstAlpha = THREE.OneFactor;
  keepThinGlass(m);
  return true;
}

/** A copy of a glass material (Material.clone drops custom defines) gets its multiply back. */
export function keepThinGlass(m) {
  if (!m?.userData?.thinGlass || m.defines?.NM_GLASS_MUL !== undefined) return;
  m.defines = { ...(m.defines || {}), NM_GLASS_MUL: '' };
  m.needsUpdate = true;
}

/** The adding draw's material for a glass material (one per glass material). */
const specOf = new WeakMap();
function specFor(m) {
  let s = specOf.get(m);
  if (s) return s;
  s = m.clone();
  s.name = `${m.name}_spec`;
  s.userData = { glassSpec: true };
  s.color.setRGB(0, 0, 0);
  s.blendSrc = THREE.OneFactor;
  s.blendDst = THREE.OneFactor;
  s.blendSrcAlpha = THREE.ZeroFactor;
  s.blendDstAlpha = THREE.OneFactor;
  const defines = { ...(s.defines || {}), NM_GLASS_ADD: '' };
  delete defines.NM_GLASS_MUL;
  s.defines = defines;
  s.needsUpdate = true;
  specOf.set(m, s);
  return s;
}

/** Before each draw: follow the glass (its material may be swapped for a copy; its glow and probe change). */
function follow() {
  const glass = this.parent;
  const m = glass?.material;
  if (!m || !m.userData?.thinGlass) return;
  keepThinGlass(m);
  if (this.material !== specFor(m)) this.material = specFor(m); // drawn from the next frame
  if (this.geometry !== glass.geometry) this.geometry = glass.geometry;
  const s = this.material;
  if (s.envMap !== m.envMap) { s.envMap = m.envMap; s.needsUpdate = true; }
  s.envMapIntensity = m.envMapIntensity;
  if (m.emissive) s.emissive.copy(m.emissive);
  s.emissiveIntensity = m.emissiveIntensity;
  const rim = m.defines?.NM_GLASS_FA !== undefined;
  if (rim !== (s.defines.NM_GLASS_FA !== undefined)) {
    if (rim) s.defines.NM_GLASS_FA = ''; else delete s.defines.NM_GLASS_FA;
    s.needsUpdate = true;
  }
}

function addSpec(o) {
  if (o.children.some((c) => c.userData.glassSpec)) return;
  const s = new THREE.Mesh(o.geometry, specFor(o.material));
  s.name = 'engine_glass_spec';
  s.userData.glassSpec = true;
  s.userData.itemFx = true; // the actions' and the shop's material swaps leave it alone
  s.raycast = () => {};
  s.castShadow = false;
  s.receiveShadow = o.receiveShadow;
  s.renderOrder = o.renderOrder;
  s.frustumCulled = o.frustumCulled;
  s.layers.mask = o.layers.mask;
  s.onBeforeRender = follow;
  o.add(s);
}

/**
 * Swap the transmission of every thin white glass under `root` for the two draws, and give every mesh drawn with
 * such glass its adding child. Returns how many materials were turned. A material also used by a mesh that cannot
 * take the child (instanced, skinned, morphed, several materials) keeps its transmission.
 */
export function thinGlass(root) {
  const meshes = [], keep = new Set();
  root.traverse((o) => {
    if (!o.isMesh || o.userData.glassSpec) return;
    const plain = !o.isInstancedMesh && !o.isSkinnedMesh && !o.isBatchedMesh && !o.morphTargetInfluences && !Array.isArray(o.material);
    if (plain) meshes.push(o);
    else for (const m of [].concat(o.material)) keep.add(m);
  });
  let n = 0;
  for (const o of meshes) {
    const m = o.material;
    if (!m) continue;
    if (!m.userData.thinGlass) {
      if (keep.has(m) || !toThinGlass(m)) continue;
      n++;
    }
    addSpec(o);
  }
  return n;
}
