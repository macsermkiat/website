// Loads a layout entry's glb (the lite variant on the lite market) with meshopt decoding.
// Any failure falls back to a labelled stand-in, so the market always opens.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
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

const cache = new Map();
async function fetchGlb(rel, manager) {
  const url = modelUrl(rel);
  const gltf = await getLoader(manager).loadAsync(url);
  THREE.Cache.remove(url); // keep the decoded images, not the glb's bytes
  const root = gltf.scene || gltf.scenes?.[0];
  if (!root) throw new Error(`${rel} has no scene`);
  root.userData.animations = gltf.animations || [];
  shareSources(root);
  return root;
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
export async function loadGlb(rel, manager) {
  if (!cache.has(rel)) cache.set(rel, fetchGlb(rel, manager).then((root) => ({ root, used: false })));
  const c = await cache.get(rel);
  if (!c.used) { c.used = true; return c.root; }
  const copy = cloneSkinned(c.root);
  copy.userData.animations = c.root.userData.animations;
  return copy;
}

/**
 * Returns { root, source } where source is 'lite', 'glb' or 'standin'.
 * `warn` collects messages; nothing here throws.
 */
export async function loadEntry(entry, { lite, manager, warn }) {
  const tries = [];
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
