// GPU-compressed twins of the market's glb files (round 10).
//
//   node scripts/ktx2.mjs [--min-ratio 150] [--lite-min-ratio N] [--dry] [--basisu /path/to/basisu]
//
// A webp texture is small to download but the GPU holds it decoded: 4 bytes a texel, a third more with its
// mipmaps. A Basis Universal texture (KTX2, ETC1S) is transcoded in the browser to a format the GPU keeps
// compressed (BC7 on most desktops, ETC2 on phones, ASTC where there is one): 1 or 0.5 bytes a texel. This
// script writes, for every glb in public/models with a texture worth converting, a twin <name>.ktx2.glb: the
// same file byte for byte (nodes, meshes, materials, the meshopt data) with those textures as KTX2
// (KHR_texture_basisu) in place of webp. An external texture (the deco kit, the vendors' atlases) gets a
// <name>.ktx2 beside its .webp. public/models/ktx2.json lists the twins; engine/loader.js loads a twin where the
// GPU takes a compressed format and falls back to the webp file when anything in it fails, and
// scripts/budget.mjs counts both paths.
//
// Which textures: power-of-two ones (a block format needs every mip level a multiple of 4), used for one kind
// of data only (colour, normals, or roughness/occlusion), whose ETC1S version stays close to the webp one
// (PSNR against the decoded webp: 32 dB for colour, 30 dB for data; text-like detail such as the book covers
// and the signpost's arms falls below it and stays webp), and whose GPU saving is worth the bytes it adds:
// converted when the KTX2 file is no larger than the webp, or when it saves at least --min-ratio bytes of GPU
// memory for every byte it adds to the download. Colour is ETC1S quality 128 in sRGB; normal maps ETC1S quality
// 64 with basisu's normal-map tuning; roughness, metalness and occlusion ETC1S quality 64, linear. (UASTC keeps
// more detail but is five to ten times the webp's size: the market's first load would grow by half.)
//
// Needs basisu (Basis Universal 1.16, `--basisu` or BASISU, else `basisu` on the PATH) and sharp (from the
// globally installed @gltf-transform/cli, as blender/lib/optimize.mjs uses). Encoded textures are cached by
// content in site/.ktx2-cache, so a run after a re-export only encodes what changed. Run it after exporting or
// re-optimising models; the twins are committed with them.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import { execFileSync, execFile } from 'node:child_process';
import { createRequire } from 'node:module';

const SITE = path.resolve(import.meta.dirname, '..');
const MODELS = path.join(SITE, 'public', 'models');
const CACHE = path.join(SITE, '.ktx2-cache');
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const MIN_RATIO = +opt('--min-ratio', 150);
const LITE_MIN_RATIO = +opt('--lite-min-ratio', MIN_RATIO); // textures only the lite market loads
const DRY = args.includes('--dry');
const BASISU = opt('--basisu', process.env.BASISU || 'basisu');
const MIN_PSNR = { srgb: 32, normal: 30, linear: 30 };
const QUALITY = { srgb: 128, normal: 64, linear: 64 };
const FLAGS = { srgb: [], normal: ['-normal_map'], linear: ['-linear'] };
const MANIFEST = path.join(MODELS, 'ktx2.json');

// ---------- glb in and out ----------
function readGlb(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32LE(0) !== 0x46546c67) throw new Error(`${file}: not a glb`);
  const jsonLen = b.readUInt32LE(12);
  const json = JSON.parse(b.subarray(20, 20 + jsonLen).toString('utf8'));
  let bin = null;
  const at = 20 + jsonLen;
  if (at < b.length) { const binLen = b.readUInt32LE(at); bin = b.subarray(at + 8, at + 8 + binLen); }
  return { json, bin };
}
function writeGlb(file, json, bin) {
  let j = Buffer.from(JSON.stringify(json), 'utf8');
  if (j.length % 4) j = Buffer.concat([j, Buffer.alloc(4 - (j.length % 4), 0x20)]);
  let b = bin || Buffer.alloc(0);
  if (b.length % 4) b = Buffer.concat([b, Buffer.alloc(4 - (b.length % 4))]);
  const head = Buffer.alloc(12);
  const total = 12 + 8 + j.length + (bin ? 8 + b.length : 0);
  head.writeUInt32LE(0x46546c67, 0); head.writeUInt32LE(2, 4); head.writeUInt32LE(total, 8);
  const jh = Buffer.alloc(8); jh.writeUInt32LE(j.length, 0); jh.writeUInt32LE(0x4e4f534a, 4);
  const parts = [head, jh, j];
  if (bin) { const bh = Buffer.alloc(8); bh.writeUInt32LE(b.length, 0); bh.writeUInt32LE(0x004e4942, 4); parts.push(bh, b); }
  fs.writeFileSync(file, Buffer.concat(parts));
}
const binIndex = (json) => (json.buffers || []).findIndex((b) => b.uri === undefined && !b.extensions?.EXT_meshopt_compression?.fallback);
const textureSource = (tex) => tex.extensions?.EXT_texture_webp?.source ?? tex.source;
function imageBytes(json, bin, i) {
  const bv = json.bufferViews[json.images[i].bufferView];
  return bin.subarray(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength);
}

// ---------- the inventory: every texture image, once by content ----------
function webpSize(b) {
  if (b.toString('ascii', 0, 4) !== 'RIFF') return null;
  const t = b.toString('ascii', 12, 16);
  if (t === 'VP8 ') return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff];
  if (t === 'VP8L') { const v = b.readUInt32LE(21); return [(v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1]; }
  if (t === 'VP8X') return [1 + b.readUIntLE(24, 3), 1 + b.readUIntLE(27, 3)];
  return null;
}
const SLOT_KIND = { base: 'srgb', emissive: 'srgb', normal: 'normal', mr: 'linear', ao: 'linear' };
function slots(m) {
  const p = m.pbrMetallicRoughness || {};
  return { base: p.baseColorTexture, mr: p.metallicRoughnessTexture, normal: m.normalTexture, ao: m.occlusionTexture, emissive: m.emissiveTexture };
}

const glbs = fs.readdirSync(MODELS).filter((f) => f.endsWith('.glb') && !f.endsWith('.ktx2.glb')).sort();
const images = new Map(); // hash -> { hash, bytes, size, kinds:Set, webp:Buffer, uses:[{glb, index, external}] }
const files = new Map(); // glb -> { json, bin }
for (const f of glbs) {
  const g = readGlb(path.join(MODELS, f));
  files.set(f, g);
  const { json, bin } = g;
  const kinds = {};
  // a texture used anywhere but a material's five slots (an extension's) is left alone
  const other = new Set();
  for (const m of json.materials || []) {
    for (const [slot, t] of Object.entries(slots(m))) if (t) (kinds[textureSource(json.textures[t.index])] ||= new Set()).add(SLOT_KIND[slot]);
    JSON.stringify(m.extensions || {}, (k, v) => { if (v && typeof v === 'object' && 'index' in v && k !== '') other.add(textureSource(json.textures[v.index])); return v; });
  }
  (json.images || []).forEach((im, i) => {
    const external = im.bufferView === undefined;
    if (external && (!im.uri || /^data:/.test(im.uri))) return;
    const data = external ? fs.readFileSync(path.join(MODELS, decodeURIComponent(im.uri))) : imageBytes(json, bin, i);
    const hash = crypto.createHash('sha1').update(data).digest('hex');
    if (!images.has(hash)) images.set(hash, { hash, bytes: data.length, size: webpSize(data), kinds: new Set(), webp: data, uses: [], blocked: false });
    const e = images.get(hash);
    for (const k of kinds[i] || []) e.kinds.add(k);
    if (other.has(i) || (im.mimeType && im.mimeType !== 'image/webp')) e.blocked = true;
    e.uses.push({ glb: f, index: i, external: external ? decodeURIComponent(im.uri) : null });
  });
}

// ---------- encode (cached) ----------
const pot = (n) => n >= 4 && (n & (n - 1)) === 0;
const candidates = [...images.values()].filter((e) => !e.blocked && e.size && pot(e.size[0]) && pot(e.size[1]) && e.kinds.size === 1);
const kindOf = (e) => [...e.kinds][0];
let sharp = null;
function loadSharp() {
  if (sharp) return sharp;
  const root = execFileSync('npm', ['root', '-g']).toString().trim();
  sharp = createRequire(`${root}/@gltf-transform/cli/package.json`)('sharp');
  return sharp;
}
function run(cmd, argv) {
  return new Promise((resolve, reject) => execFile(cmd, argv, { maxBuffer: 64 << 20 }, (err, stdout, stderr) => (err ? reject(new Error(`${cmd}: ${err.message}\n${stderr}`)) : resolve(stdout))));
}
async function encode(e) {
  const kind = kindOf(e);
  const key = `${e.hash}.${kind}.q${QUALITY[kind]}`;
  const out = path.join(CACHE, `${key}.ktx2`), stats = path.join(CACHE, `${key}.json`);
  if (fs.existsSync(out) && fs.existsSync(stats)) return { ktx2: fs.readFileSync(out), ...JSON.parse(fs.readFileSync(stats, 'utf8')) };
  fs.mkdirSync(CACHE, { recursive: true });
  const png = path.join(os.tmpdir(), `ktx2-${process.pid}-${e.hash}.png`);
  await loadSharp()(e.webp).png({ compressionLevel: 1 }).toFile(png);
  try {
    const log = await run(BASISU, ['-ktx2', '-mipmap', '-stats', '-max_threads', '2', '-q', String(QUALITY[kind]), ...FLAGS[kind], '-file', png, '-output_file', out]);
    const m = /RGB Avg:.*?PSNR:\s*([0-9.]+)/.exec(log);
    const s = { psnr: m ? +m[1] : 0 };
    fs.writeFileSync(stats, JSON.stringify(s));
    return { ktx2: fs.readFileSync(out), ...s };
  } finally { fs.rmSync(png, { force: true }); }
}
async function pool(items, n, fn) {
  const out = new Array(items.length);
  let next = 0;
  await Promise.all(Array.from({ length: n }, async () => { while (next < items.length) { const i = next++; out[i] = await fn(items[i], i); } }));
  return out;
}
try { execFileSync(BASISU, ['-version'], { stdio: 'pipe' }); } catch (err) {
  // basisu exits 0 with -version; any failure here means it is missing
  if (err.code === 'ENOENT') { console.error(`ktx2: basisu not found (${BASISU}); pass --basisu or set BASISU`); process.exit(1); }
}
const t0 = Date.now();
const results = await pool(candidates, Math.max(1, Math.min(4, os.cpus().length) >> 1), async (e) => ({ e, ...(await encode(e)) }));

// ---------- choose ----------
const chosen = new Map(); // hash -> ktx2 Buffer
let gpuBefore = 0, gpuSaved = 0, added = 0;
for (const r of results) {
  const { e, ktx2, psnr } = r;
  const kind = kindOf(e);
  const texels = e.size[0] * e.size[1] * 4 / 3;
  const save = texels * (4 - 1); // against BC7 (1 byte a texel), the least a compressed format saves
  const extra = ktx2.length - e.bytes;
  const lite = e.uses.every((u) => /\.lite\./.test(u.external || u.glb));
  const ok = psnr >= MIN_PSNR[kind] && (extra <= 0 || save / extra >= (lite ? LITE_MIN_RATIO : MIN_RATIO));
  r.ok = ok;
  if (!ok) continue;
  chosen.set(e.hash, ktx2);
  gpuSaved += save; added += extra;
}
for (const e of images.values()) if (e.size) gpuBefore += e.size[0] * e.size[1] * 4 * 4 / 3;

// ---------- write the twins ----------
const sidecarOf = (uri) => uri.replace(/\.webp$/i, '') + '.ktx2';
const twins = {};
const sidecars = {};
const written = new Set();
for (const f of glbs) {
  const { json: src, bin } = files.get(f);
  const conv = new Map(); // image index -> hash
  (src.images || []).forEach((im, i) => {
    for (const [h, e] of images) if (chosen.has(h) && e.uses.some((u) => u.glb === f && u.index === i)) conv.set(i, h);
  });
  if (!conv.size) continue;
  const json = JSON.parse(JSON.stringify(src));
  const bi = binIndex(json);
  // the BIN chunk again, region by region, the converted images' bytes swapped for their KTX2
  const replace = new Map(); // bufferView index -> Buffer
  for (const [i, h] of conv) {
    const im = json.images[i];
    if (im.bufferView !== undefined) {
      const shared = json.images.some((o, k) => k !== i && o.bufferView === im.bufferView && !conv.has(k));
      if (shared) { conv.delete(i); continue; }
      replace.set(im.bufferView, chosen.get(h));
      im.mimeType = 'image/ktx2';
    } else {
      // an external texture: its .ktx2 beside the .webp, swapped in by the loader (manifest `sidecars`), so a
      // glb that only uses external textures needs no twin
      const uri = decodeURIComponent(im.uri);
      const side = sidecarOf(uri);
      if (!written.has(side) && !DRY) fs.writeFileSync(path.join(MODELS, side), chosen.get(h));
      written.add(side);
      sidecars[uri] = side;
      conv.delete(i);
    }
  }
  if (!replace.size) continue;
  // regions of the BIN chunk: each bufferView on it, and each meshopt bufferView's compressed data on it
  const regions = [];
  (json.bufferViews || []).forEach((bv, k) => {
    if (bv.buffer === bi) regions.push({ obj: bv, k, data: replace.get(k) || bin.subarray(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength) });
    const mo = bv.extensions?.EXT_meshopt_compression;
    if (mo && mo.buffer === bi) regions.push({ obj: mo, k: -1, data: bin.subarray(mo.byteOffset || 0, (mo.byteOffset || 0) + mo.byteLength) });
  });
  const chunks = [];
  let off = 0;
  for (const r of regions) {
    const pad = (8 - (off % 8)) % 8;
    if (pad) { chunks.push(Buffer.alloc(pad)); off += pad; }
    r.obj.byteOffset = off;
    r.obj.byteLength = r.data.length;
    chunks.push(r.data);
    off += r.data.length;
  }
  const newBin = Buffer.concat(chunks);
  if (bi >= 0) json.buffers[bi].byteLength = newBin.length;
  for (const tex of json.textures || []) {
    const s = tex.extensions?.EXT_texture_webp?.source;
    if (s === undefined || !conv.has(s)) continue;
    delete tex.extensions.EXT_texture_webp;
    tex.extensions.KHR_texture_basisu = { source: s };
  }
  const webpLeft = (json.textures || []).some((t) => t.extensions?.EXT_texture_webp);
  const fix = (list) => { const out = (list || []).filter((x) => x !== 'EXT_texture_webp' || webpLeft); if (!out.includes('KHR_texture_basisu')) out.push('KHR_texture_basisu'); return out; };
  json.extensionsUsed = fix(json.extensionsUsed);
  json.extensionsRequired = fix(json.extensionsRequired);
  json.asset = { ...json.asset, extras: { ...(json.asset?.extras || {}), ktx2: `scripts/ktx2.mjs: ${conv.size} texture(s) as KTX2 (ETC1S)` } };
  const twin = f.replace(/\.glb$/, '.ktx2.glb');
  if (!DRY) writeGlb(path.join(MODELS, twin), json, newBin);
  written.add(twin);
  twins[f] = twin;
}

// stale twins and sidecars from an earlier run
for (const f of fs.readdirSync(MODELS)) {
  if ((f.endsWith('.ktx2.glb') || f.endsWith('.ktx2')) && !written.has(f)) { if (!DRY) fs.rmSync(path.join(MODELS, f)); console.log(`removed stale ${f}`); }
}
const manifest = {
  about: 'GPU-compressed twins of the glb files (scripts/ktx2.mjs); engine/loader.js loads them where the GPU takes a compressed texture format.',
  encoder: 'Basis Universal ETC1S',
  minRatio: MIN_RATIO,
  liteMinRatio: LITE_MIN_RATIO,
  textures: { candidates: candidates.length, converted: chosen.size, of: images.size },
  files: twins,
  sidecars,
};
if (!DRY) fs.writeFileSync(MANIFEST, `${JSON.stringify(manifest, null, 1)}\n`);
const mb = (b) => `${(b / 1e6).toFixed(2)} MB`;
console.log(`ktx2: ${images.size} textures, ${candidates.length} candidates, ${chosen.size} converted; ${Object.keys(twins).length} twins, ${Object.keys(sidecars).length} external; GPU (all textures, RGBA + mips) ${mb(gpuBefore)}, at least ${mb(gpuSaved)} less; download +${mb(added)} over all files; ${((Date.now() - t0) / 1000).toFixed(0)} s${DRY ? ' (dry run: nothing written)' : ''}`);
if (args.includes('--list')) for (const r of results.sort((a, b) => a.psnr - b.psnr)) console.log(`${r.ok ? '+' : '-'} ${r.e.hash.slice(0, 10)} ${kindOf(r.e).padEnd(6)} ${r.e.size.join('x').padEnd(9)} webp ${String(r.e.bytes).padStart(7)} ktx2 ${String(r.ktx2.length).padStart(7)} psnr ${r.psnr} ${r.e.uses[0].external || `${r.e.uses[0].glb}#${r.e.uses[0].index}`}`);
