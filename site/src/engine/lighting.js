// Loads the lighting designer's module when it exists and works, otherwise the stand-in.
import { createLighting as fallbackLighting } from '../lighting-fallback.js';

// Resolved at build time: an empty object until site/src/lighting/index.js exists.
const modules = import.meta.glob('../lighting/index.js');

function valid(L) {
  return L && L.composer && typeof L.composer.render === 'function';
}

function complete(L) {
  return {
    composer: L.composer,
    update: typeof L.update === 'function' ? L.update.bind(L) : () => {},
    setSnow: typeof L.setSnow === 'function' ? L.setSnow.bind(L) : () => {},
    dispose: typeof L.dispose === 'function' ? L.dispose.bind(L) : () => {},
    raw: L,
  };
}

export async function setupLighting(ctx, warn) {
  const load = modules['../lighting/index.js'];
  if (load) {
    let L = null;
    try {
      const mod = await load();
      const create = mod.createLighting || mod.default?.createLighting || mod.default;
      if (typeof create !== 'function') throw new Error('lighting/index.js does not export createLighting');
      L = await create(ctx);
      if (!valid(L)) throw new Error('createLighting did not return { composer }');
      return { lighting: complete(L), source: 'lighting' };
    } catch (err) {
      warn(`Lighting module failed (${err?.message || err}); using the stand-in lighting.`);
      try { L?.dispose?.(); } catch { /* ignore */ }
    }
  }
  return { lighting: complete(fallbackLighting(ctx)), source: 'fallback' };
}
