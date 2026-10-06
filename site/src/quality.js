// Decide between the full market and the lite market (phones and weak GPUs).
// Order of precedence: ?quality=lite|full in the URL, the visitor's saved choice, then detection.
const KEY = 'nachtmarkt.quality';

function storageGet() {
  try { return localStorage.getItem(KEY); } catch { return null; }
}
function storageSet(v) {
  try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch { /* private mode */ }
}

export function gpuInfo() {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    if (!gl) return { webgl: false, renderer: '' };
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    const maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return { webgl: true, webgl2: !!c.getContext && gl instanceof WebGL2RenderingContext, renderer: String(renderer || ''), maxTex };
  } catch {
    return { webgl: false, renderer: '' };
  }
}

// GPU classes from the WebGL renderer string (ANGLE on Windows and Chrome for Mac, Mesa on Linux, masked on Safari).
// Only software renderers and clearly old or low-end parts go to the lite market by name. Mid-range integrated
// graphics (UHD 620/630/7xx, Iris, Iris Xe, Radeon Vega, Apple) get the full market with the crowd's distance LOD
// pulled in; the frame-time governor in main.js takes it from there on the visitor's own machine (and offers the
// lite market if even that is too slow). The pass-1 rule sent every "Intel(R) UHD Graphics" to lite, which is
// most laptops of the last six years.
const SOFTWARE = /swiftshader|llvmpipe|softpipe|lavapipe|software|basic render|microsoft basic/i;
const WEAK = [
  /mali-(4\d{2}|t\d{3,4})\b|mali-g(3|5[0-2])\d?\b/i, // old and low-end Mali
  /adreno \(tm\) [3-5]\d{2}\b|adreno [3-5]\d{2}\b/i, // Adreno 300-500 series
  /powervr|sgx|videocore|vivante/i,
  /\bgma\b|gen[4-7]|ironlake|sandybridge|ivybridge|haswell/i,
  // Intel HD Graphics by number: 2000-6000 (2011-2015) and 4xx/5xx (Atom, Celeron, Skylake GT1/GT2)
  /intel.*\bhd graphics(\s+(\d{3,4}|p\d{3,4}))?\b(?!.*iris)/i,
  // UHD 600/605/610 (Celeron, Pentium Silver, Gemini Lake) and Mesa's names for them
  /\buhd graphics 6(00|05|10)\b|\((glk|apl|bxt|jsl|ehl)\b/i,
];
const INTEGRATED = /intel|iris|\buhd\b|radeon(\(tm\))? (graphics|vega|r[4-7]\b)|vega \d+|apple gpu|apple m\d|adreno|mali|immortalis/i;
const DISCRETE = /nvidia|geforce|quadro|rtx|gtx|radeon (rx|pro)|\brx \d{3,4}|apple m\d (pro|max|ultra)|\barc\b/i;

/** 'software' | 'weak' | 'integrated' | 'discrete' | 'unknown' for a WebGL renderer string. */
export function gpuTier(renderer = '') {
  const r = String(renderer);
  if (!r) return 'unknown';
  if (SOFTWARE.test(r)) return 'software';
  if (DISCRETE.test(r)) return 'discrete';
  if (WEAK.some((re) => re.test(r))) return 'weak';
  if (INTEGRATED.test(r)) return 'integrated';
  return 'unknown';
}

/**
 * The crowd's distance LOD for a GPU class (metres beyond which people draw their lite figure). Starting
 * points until real measurements replace them (NOTES.md); the frame-time governor lowers them at run time.
 */
// Round 8 (docs/adr/0004): the far crowd is instanced and animated on the GPU (crowdFar.js), so the switch can sit
// at about 25 m on a real graphics card and still cost less than round 7's 18 m with a skinned figure each.
export const LOD_BY_TIER = { discrete: 25, unknown: 20, integrated: 18, weak: 12, software: 12 };

export function detectLite(info = gpuInfo(), env = globalThis) {
  const reasons = [];
  const nav = env.navigator || {};
  const ua = nav.userAgent || '';
  const coarse = env.matchMedia ? env.matchMedia('(pointer: coarse)').matches : false;
  const phone = /Android.+Mobile|iPhone|iPod|Windows Phone|Mobile Safari/i.test(ua) ||
    (coarse && env.screen && Math.min(env.screen.width, env.screen.height) < 600);
  if (phone) reasons.push('phone');
  if (/iPad|Android/i.test(ua) && !phone) reasons.push('tablet');
  const tier = gpuTier(info.renderer);
  if (tier === 'software' || tier === 'weak') reasons.push(`${tier} GPU: ${info.renderer}`);
  // Measured 2026-10-06 on an Apple M3 MacBook Air: the full market ran at 1-5 fps, the lite one smoothly. Built-in
  // GPUs (Apple M base chips, Intel Iris/UHD, AMD Radeon Graphics) start on lite; the full market is one click away.
  if (tier === 'integrated') reasons.push(`built-in GPU: ${info.renderer}`);
  if (info.maxTex && info.maxTex < 8192) reasons.push('small textures');
  if (nav.deviceMemory && nav.deviceMemory <= 4) reasons.push('low memory');
  if (nav.hardwareConcurrency && nav.hardwareConcurrency <= 2) reasons.push('few cores');
  if (nav.connection?.saveData) reasons.push('data saver');
  return { lite: reasons.length > 0, reasons, tier };
}

export function chooseQuality() {
  const info = gpuInfo();
  const q = new URLSearchParams(location.search).get('quality');
  const detected = detectLite(info);
  // the crowd's distance LOD: ?lod=<metres> for measuring, else by GPU class
  const lodQ = Number(new URLSearchParams(location.search).get('lod'));
  const lodFar = Number.isFinite(lodQ) && lodQ >= 0 && new URLSearchParams(location.search).has('lod') ? lodQ : LOD_BY_TIER[detected.tier] ?? 14;
  if (q === 'lite' || q === 'full') return { lite: q === 'lite', source: 'url', detected, info, lodFar };
  const saved = storageGet();
  if (saved === 'lite' || saved === 'full') return { lite: saved === 'lite', source: 'saved', detected, info, lodFar };
  return { lite: detected.lite, source: 'detected', detected, info, lodFar };
}

/** Switch quality and reload; the choice is remembered for this browser. */
export function switchQuality(lite, { remember = true } = {}) {
  if (remember) storageSet(lite ? 'lite' : 'full');
  const url = new URL(location.href);
  url.searchParams.delete('quality');
  // an automatic switch (the full market was too slow here) is not remembered: the URL carries it for this visit
  if (!remember) { url.searchParams.set('quality', lite ? 'lite' : 'full'); url.searchParams.set('auto', '1'); }
  location.href = url.toString();
}
