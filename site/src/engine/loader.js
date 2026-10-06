// Loads a layout entry's glb (the lite variant on the lite market) with meshopt decoding.
// Any failure falls back to a labelled stand-in, so the market always opens.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { buildStandin } from '../standins/index.js';

const BASE = import.meta.env.BASE_URL;
let loader = null;
// The deco stalls share one set of kit textures by relative URI: fetch and decode each image once.
THREE.Cache.enabled = true;

export function modelUrl(rel) {
  return `${BASE}models/${rel}`;
}

function getLoader(manager) {
  if (!loader) {
    loader = new GLTFLoader(manager);
    loader.setMeshoptDecoder(MeshoptDecoder);
  }
  return loader;
}

// ---------- GPU-compressed textures (round 10) ----------
// Every glb whose textures have a GPU-compressed version has a twin, <name>.ktx2.glb (scripts/ktx2.mjs writes
// them, public/models/ktx2.json lists them): the same file with those textures as Basis Universal KTX2
// (KHR_texture_basisu), which the GPU keeps compressed, a quarter to an eighth of the memory of the decoded
// webp. initTextures() (main.js, once the renderer exists) reads the list and checks the GPU takes a compressed
// format; loadGlb then loads the twin. Should a twin or any texture in it fail to load or transcode, that model
// loads from its webp file, and so does every model after it: the market always opens. ?ktx2=0 turns it off.
const ktx2 = { loader: null, twins: null, sidecars: null, ready: null, broken: false, twinsLoaded: 0, fellBack: 0, format: null, formats: {} };
export function initTextures(renderer, { enabled = true } = {}) {
  if (ktx2.ready) return ktx2.ready;
  ktx2.ready = (async () => {
    if (!enabled || !renderer?.capabilities?.isWebGL2) return;
    try {
      const res = await fetch(`${BASE}models/ktx2.json`);
      if (!res.ok) return;
      const list = await res.json();
      const l = new KTX2Loader();
      l.setTranscoderPath(`${BASE}basis/`);
      l.detectSupport(renderer);
      const c = l.workerConfig || {};
      const ext = (n) => !!renderer.extensions.get(n);
      // a format the GPU keeps compressed, sRGB included (colour textures are sRGB), or the webp files
      ktx2.format = c.astcSupported ? 'astc' : c.bptcSupported ? 'bc7' : c.etc2Supported ? 'etc2' : c.dxtSupported && ext('WEBGL_compressed_texture_s3tc_srgb') ? 'bc1' : null;
      if (!ktx2.format) { l.dispose(); return; }
      ktx2.loader = l;
      ktx2.twins = new Map(Object.entries(list.files || {}));
      ktx2.sidecars = new Map(Object.entries(list.sidecars || {}));
    } catch (e) {
      ktx2.loader = null;
      ktx2.twins = null;
    }
  })();
  return ktx2.ready;
}
/** What the texture path did, for tests and the perf bench. */
export function textureInfo() {
  return { ktx2: !!ktx2.loader && !ktx2.broken, gpu: ktx2.format, formats: { ...ktx2.formats }, twins: ktx2.twins?.size || 0, twinsLoaded: ktx2.twinsLoaded, fellBack: ktx2.fellBack };
}

// what the GPU got, for the report (the transcoder picks the format per GPU)
const FORMAT_NAMES = { [THREE.RGBA_BPTC_Format]: 'BC7', [THREE.RGB_ETC2_Format]: 'ETC2', [THREE.RGBA_ETC2_EAC_Format]: 'ETC2 RGBA', [THREE.RGB_ETC1_Format]: 'ETC1', [THREE.RGBA_ASTC_4x4_Format]: 'ASTC 4x4', [THREE.RGBA_S3TC_DXT1_Format]: 'BC1', [THREE.RGBA_S3TC_DXT5_Format]: 'BC3', [THREE.RGBAFormat]: 'RGBA (uncompressed)' };
function countFormat(t) {
  const k = FORMAT_NAMES[t.format] || String(t.format);
  ktx2.formats[k] = (ktx2.formats[k] || 0) + 1;
}

// external KTX2 files (the deco kit, the vendors' atlases) are shared by several glbs: transcode each once and
// give every glb a clone (one Source, so one GPU upload)
const ktxShared = new Map();
function ktx2Watcher(failures) {
  return {
    load(url, onLoad, onProgress, onError) {
      const own = url.startsWith('blob:') || url.startsWith('data:');
      let p = own ? null : ktxShared.get(url);
      if (!p) {
        p = ktx2.loader.loadAsync(url);
        if (!own) { ktxShared.set(url, p); p.then((t) => { countFormat(t); THREE.Cache.remove(url); }, () => {}); }
      }
      p.then((t) => { if (own) countFormat(t); onLoad(own ? t : t.clone()); }, (e) => { failures.push(e); if (!own) ktxShared.delete(url); onError?.(e); });
    },
  };
}

// an external texture with a .ktx2 beside it (manifest `sidecars`): the glb names the .webp, so swap it in before
// the textures load (a glb that only uses external textures needs no twin)
class SidecarSwap {
  constructor(parser) { this.parser = parser; this.name = 'nachtmarkt_ktx2_sidecars'; }
  beforeRoot() {
    const j = this.parser.json;
    (j.images || []).forEach((im, i) => {
      const side = im.uri && ktx2.sidecars?.get(decodeURIComponent(im.uri));
      if (!side) return;
      im.uri = encodeURI(side);
      im.mimeType = 'image/ktx2';
      for (const t of j.textures || []) {
        if (t.extensions?.EXT_texture_webp?.source !== i) continue;
        delete t.extensions.EXT_texture_webp;
        t.extensions.KHR_texture_basisu = { source: i };
      }
    });
    return null;
  }
}

async function parseGlb(rel, manager, compressed) {
  const url = modelUrl(rel);
  let gltf;
  if (compressed) {
    const failures = [];
    const l = new GLTFLoader(manager);
    l.setMeshoptDecoder(MeshoptDecoder);
    l.setKTX2Loader(ktx2Watcher(failures));
    l.register((parser) => new SidecarSwap(parser));
    gltf = await l.loadAsync(url);
    THREE.Cache.remove(url);
    if (failures.length) throw Object.assign(new Error(`${failures.length} texture(s) did not transcode: ${failures[0]?.message || failures[0]}`), { textures: true });
  } else {
    gltf = await getLoader(manager).loadAsync(url);
    THREE.Cache.remove(url); // keep the decoded images, not the glb's bytes
  }
  return gltf;
}

const cache = new Map();
async function fetchGlb(rel, manager) {
  let gltf = null;
  if (ktx2.ready) await ktx2.ready;
  if (!ktx2.broken && ktx2.loader) {
    const twin = ktx2.twins?.get(rel);
    try {
      gltf = await parseGlb(twin || rel, manager, true);
      if (twin) ktx2.twinsLoaded++;
    } catch (err) {
      // a texture that did not transcode: the webp files from here on; anything else (a missing twin): this file
      if (err?.textures) ktx2.broken = true;
      ktx2.fellBack++;
      console.warn(`textures: ${twin || rel} did not load with KTX2 textures (${err?.message || err}); ${err?.textures ? 'the webp files from here on' : 'its webp file instead'}.`);
    }
  }
  if (!gltf) gltf = await parseGlb(rel, manager, false);
  const root = gltf.scene || gltf.scenes?.[0];
  if (!root) throw new Error(`${rel} has no scene`);
  setClips(root, gltf.animations || []);
  tagGltf(root, gltf.parser?.associations);
  shareSources(root);
  return root;
}

// Which objects the loader made for glTF nodes and primitives, and which materials came from the file:
// the streamer (engine/stream.js) grafts a full model onto its lite twin by these.
function tagGltf(root, assoc) {
  root.traverse((o) => {
    const a = assoc?.get(o);
    if (a && a.nodes !== undefined) o.userData.gltfNode = a.nodes;
    if (a && a.primitives !== undefined) o.userData.gltfPrimitive = true;
    if (o.isMesh) for (const m of Array.isArray(o.material) ? o.material : [o.material]) if (m) m.userData.fromGlb = true;
  });
}

// Textures from different glbs that decoded to the same image get one GPU upload between them.
const sources = new Map();
function shareSources(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m) continue;
      for (const k in m) {
        const t = m[k];
        if (!t?.isTexture || !t.source?.data) continue;
        const img = t.source.data;
        const known = sources.get(img);
        if (known) t.source = known;
        else sources.set(img, t.source);
      }
    }
  });
}

/** Load a glb once; later requests for the same file get a clone (the deco stalls share one model). */
/**
 * A model's clips live on userData.animations, but not as an enumerable field: Object3D.copy() clones userData
 * through JSON, and every clone of a figure would otherwise serialise all its keyframe arrays.
 */
function setClips(obj, clips) {
  Object.defineProperty(obj.userData, 'animations', { value: clips, enumerable: false, writable: true, configurable: true });
}

export async function loadGlb(rel, manager) {
  if (!cache.has(rel)) cache.set(rel, fetchGlb(rel, manager).then((root) => ({ root, used: false })));
  const c = await cache.get(rel);
  if (!c.used) { c.used = true; return c.root; }
  const copy = cloneSkinned(c.root);
  setClips(copy, c.root.userData.animations);
  return copy;
}

/**
 * Returns { root, source } where source is 'lite', 'glb' or 'standin'.
 * `warn` collects messages; nothing here throws.
 */
export async function loadEntry(entry, { lite, manager, warn }) {
  const tries = [];
  // streaming: the full market opens with the lite model of a place and grafts the full one on later
  if (lite && entry.lite) tries.push(['lite', entry.lite]);
  if (entry.model) tries.push(['glb', entry.model]);
  for (const [source, rel] of tries) {
    try {
      const root = await loadGlb(rel, manager);
      root.name = root.name || entry.id;
      return { root, source, file: rel };
    } catch (err) {
      warn(`${entry.id}: could not load ${rel} (${err?.message || err}); ${source === 'lite' ? 'trying the full model' : 'using a stand-in'}.`);
    }
  }
  const root = buildStandin(entry);
  return { root, source: 'standin', file: null };
}

export { THREE };
