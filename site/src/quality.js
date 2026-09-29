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

const WEAK_GPU = /swiftshader|llvmpipe|softpipe|software|basic render|microsoft basic|mali-[4t][0-9]{2}\b|mali-g5[0-2]|adreno \(tm\) [3-5][0-9]{2}|powervr|sgx|intel\(r\) (hd|uhd) graphics( [0-9]{3,4})?$|intel hd graphics [0-9]{3,4}|gma/i;

export function detectLite(info = gpuInfo()) {
  const reasons = [];
  const ua = navigator.userAgent || '';
  const phone = /Android.+Mobile|iPhone|iPod|Windows Phone|Mobile Safari/i.test(ua) ||
    (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 600);
  if (phone) reasons.push('phone');
  if (/iPad|Android/i.test(ua) && !phone) reasons.push('tablet');
  if (info.renderer && WEAK_GPU.test(info.renderer)) reasons.push('weak GPU: ' + info.renderer);
  if (info.maxTex && info.maxTex < 8192) reasons.push('small textures');
  if (navigator.deviceMemory && navigator.deviceMemory <= 4) reasons.push('low memory');
  if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) reasons.push('few cores');
  if (navigator.connection?.saveData) reasons.push('data saver');
  return { lite: reasons.length > 0, reasons };
}

export function chooseQuality() {
  const info = gpuInfo();
  const q = new URLSearchParams(location.search).get('quality');
  const detected = detectLite(info);
  if (q === 'lite' || q === 'full') return { lite: q === 'lite', source: 'url', detected, info };
  const saved = storageGet();
  if (saved === 'lite' || saved === 'full') return { lite: saved === 'lite', source: 'saved', detected, info };
  return { lite: detected.lite, source: 'detected', detected, info };
}

/** Switch quality and reload; the choice is remembered for this browser. */
export function switchQuality(lite) {
  storageSet(lite ? 'lite' : 'full');
  const url = new URL(location.href);
  url.searchParams.delete('quality');
  location.href = url.toString();
}
