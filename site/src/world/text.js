// Words drawn in the market: crisp SDF text (troika-three-text, MIT) on the writing surfaces of the stalls.
//
// The engine wraps and paginates the text itself (a canvas measures every word in the very font files troika
// draws with), so a page is known to fit before it is drawn, and long text turns pages instead of scrolling.
//   blocksFromHtml(html)            section HTML (built from content/*.md) -> blocks of styled runs
//   paginate(blocks, area)          -> pages of positioned line segments for a writing area (metres)
//   renderPage(page, theme)         -> a Group of Text meshes (+ invisible hit quads for links) in the area's plane
// The area's local frame: x to the right, y up, z out of the surface toward the reader; (0, 0) is its top-left.
// troika and the faces stream in after the market's first frame (loadText): until then a page or a label is an
// empty group that fills itself when they arrive, so nothing waits on them and the first load stays small.
import * as THREE from 'three';
import chalkUrl from '@fontsource/caveat/files/caveat-latin-500-normal.woff?url';
import chalkBoldUrl from '@fontsource/caveat/files/caveat-latin-700-normal.woff?url';
import sansUrl from '@fontsource/alegreya-sans/files/alegreya-sans-latin-500-normal.woff?url';
import sansItalicUrl from '@fontsource/alegreya-sans/files/alegreya-sans-latin-500-italic.woff?url';
import sansBoldUrl from '@fontsource/alegreya-sans/files/alegreya-sans-latin-700-normal.woff?url';
import scUrl from '@fontsource/alegreya-sc/files/alegreya-sc-latin-700-normal.woff?url';

// No fallback-font lookups: every character drawn is first mapped into the fonts' latin subset (sanitize), and
// the default font is ours, so troika never reaches for a CDN.
let troika = null, troikaLoading = null;
const waitingForText = [];
/** Fetch troika (once) and draw everything that was waiting for it. */
export function loadText() {
  if (!troikaLoading) {
    troikaLoading = import('troika-three-text').then((m) => {
      m.configureTextBuilder({ defaultFontURL: sansUrl, sdfGlyphSize: 64, useWorker: true });
      troika = m;
      for (const f of waitingForText.splice(0)) { try { f(); } catch (e) { console.warn('[market] text', e); } }
      return true;
    });
  }
  return troikaLoading;
}
/** A troika Text. Its glyph geometry is an InstancedBufferGeometry whose instanceCount starts at Infinity until its
 *  first glyph sync; three draws it before then (no instance attributes yet, so no _maxInstanceCount cap) and adds
 *  Infinity to renderer.info.render.triangles. Nothing is drawn: start the count at 0 (each sync sets the real one). */
function newText() {
  const t = new troika.Text();
  t.geometry.instanceCount = 0;
  return t;
}
const whenText = (f) => (troika ? f() : waitingForText.push(f));

/**
 * Fewer draw calls (round 10): the words of one page (one Text per styled run, often twenty or more) draw as one
 * troika BatchedText instead of one draw each. The runs stay Text objects (their text, font, size, colour and
 * opacity are read from them every frame) but are members of the batch, not children of the page.
 * troika packs a member's colour as an sRGB byte triple and reads it back as a linear value over 256: the
 * vertex shader is patched to decode it as three's Color does (sRGB to linear, over 255), so a batched page
 * keeps exactly the colours its single Texts had.
 */
let PageBatch = null;
function newBatch() {
  if (!PageBatch) {
    PageBatch = class extends troika.BatchedText {
      createDerivedMaterial(base) {
        const m = super.createDerivedMaterial(base);
        // a troika derived material keeps its own onBeforeCompile; one assigned to it runs after it (on the shaders
        // troika has already upgraded)
        m.onBeforeCompile = (shader) => {
          shader.vertexShader = shader.vertexShader.replace(/diffuse\s*=\s*troikaFloatToColor\(\s*data\.x\s*\);/,
            'diffuse = troikaFloatToColor(data.x) * (256.0 / 255.0);\n      diffuse = mix(diffuse * 0.0773993808, pow(diffuse * 0.9478672986 + 0.0521327014, vec3(2.4)), step(0.04045, diffuse));');
        };
        const key = m.customProgramCacheKey?.bind(m);
        m.customProgramCacheKey = () => `${key ? key() : ''}|nmBatchSRGB`;
        return m;
      }
    };
  }
  const b = new PageBatch();
  b.geometry.instanceCount = 0; // as newText(): nothing to draw (and no Infinity triangles) before the first pack
  return b;
}

/** The faces, by role: the URL troika draws with and the family the canvas measures with. */
export const FONTS = {
  chalk: { url: chalkUrl, family: 'NM Chalk' },
  chalkBold: { url: chalkBoldUrl, family: 'NM Chalk Bold' },
  sans: { url: sansUrl, family: 'NM Sans' },
  sansItalic: { url: sansItalicUrl, family: 'NM Sans Italic' },
  sansBold: { url: sansBoldUrl, family: 'NM Sans Bold' },
  sc: { url: scUrl, family: 'NM SC' },
};

let fontsPromise = null;
/** Load the faces into the document for measuring (once). Resolves even if a face fails. */
export function fontsReady() {
  if (fontsPromise) return fontsPromise;
  if (typeof FontFace !== 'function' || !document.fonts) return (fontsPromise = Promise.resolve(false));
  fontsPromise = Promise.all(Object.values(FONTS).map(async (f) => {
    try {
      const face = new FontFace(f.family, `url(${f.url})`);
      await face.load();
      document.fonts.add(face);
      return true;
    } catch { return false; }
  })).then((r) => r.every(Boolean));
  return fontsPromise;
}

/**
 * How text looks on each kind of surface. Sizes are multiples of the area's base size; `lh` is the line height
 * as a multiple of the font size; `gap` the space before a block, in base sizes.
 */
export const THEMES = {
  chalk: {
    color: '#efeadf', muted: '#cfc6b4', link: '#ffd27a', accent: '#f2b6a0',
    p: { font: 'chalk', size: 1, lh: 1.12, gap: 0.45 },
    em: 'chalk', strong: 'chalkBold',
    h1: { font: 'chalkBold', size: 1.75, lh: 1.0, gap: 0.2, color: 'accent' },
    h: { font: 'chalkBold', size: 1.3, lh: 1.05, gap: 0.6 },
    sub: { font: 'chalk', size: 0.95, lh: 1.1, gap: 0.1, color: 'muted' },
    li: { font: 'chalk', size: 1, lh: 1.1, gap: 0.2, bullet: '- ' },
    foot: { font: 'chalk', size: 0.8, color: 'muted' },
  },
  print: {
    color: '#2a1d14', muted: '#6b5a48', link: '#8a2a20', accent: '#8a2a20',
    p: { font: 'sans', size: 1, lh: 1.3, gap: 0.55 },
    em: 'sansItalic', strong: 'sansBold',
    h1: { font: 'sc', size: 1.6, lh: 1.05, gap: 0.2 },
    h: { font: 'sc', size: 1.18, lh: 1.15, gap: 0.8, color: 'accent' },
    sub: { font: 'sansItalic', size: 0.95, lh: 1.25, gap: 0.15, color: 'muted' },
    li: { font: 'sans', size: 1, lh: 1.25, gap: 0.25, bullet: '• ' },
    foot: { font: 'sans', size: 0.75, color: 'muted' },
  },
};
// a printed card on dark board (the ticket, the coaster's back) can use the print theme with light ink
THEMES.printLight = { ...THEMES.print, color: '#f3ead6', muted: '#cdbf9f', link: '#ffd27a', accent: '#f0c27a' };

// ---------------------------------------------------------------------------------------------------------
// characters

const SUBSET = (c) => c <= 0xff || c === 0x131 || c === 0x152 || c === 0x153 || c === 0x2bb || c === 0x2bc || c === 0x2c6 || c === 0x2da || c === 0x2dc
  || (c >= 0x2000 && c <= 0x206f) || c === 0x20ac || c === 0x2122 || c === 0x2212 || c === 0x2215;
const SWAP = { '→': '->', '←': '<-', '≈': '~', '×': 'x', '✓': '', '★': '*', '♪': '', '♫': '' };
/** Map text into the fonts' latin subset (so troika never fetches a fallback font). */
export function sanitize(s) {
  let out = '';
  for (const ch of String(s ?? '')) {
    const c = ch.codePointAt(0);
    if (c === 0xa0) out += ' ';
    else if (SUBSET(c)) out += ch;
    else if (ch in SWAP) out += SWAP[ch];
    else {
      const base = ch.normalize('NFD').replace(/[̀-ͯ]/g, '');
      out += base && [...base].every((x) => SUBSET(x.codePointAt(0))) ? base : '';
    }
  }
  return out;
}

// ---------------------------------------------------------------------------------------------------------
// HTML -> blocks

/**
 * Blocks from section HTML: { kind: 'h'|'p'|'li'|'sub', level?, runs: [{ text, i?, b?, href? }] }.
 * Notes for Mac (span.formac) are left out, as are check marks and the bookshelf list (the shelf is the list).
 */
export function blocksFromHtml(html) {
  const doc = new DOMParser().parseFromString(`<div>${html || ''}</div>`, 'text/html');
  const blocks = [];
  const runsOf = (el, style = {}) => {
    const runs = [];
    const walk = (n, st) => {
      if (n.nodeType === 3) { const t = n.textContent.replace(/\s+/g, ' '); if (t) runs.push({ text: t, ...st }); return; }
      if (n.nodeType !== 1) return;
      const tag = n.tagName.toLowerCase();
      if (n.classList?.contains('formac') || tag === 'mark' || tag === 'details' || tag === 'script' || tag === 'style') return;
      if (tag === 'br') { runs.push({ text: '\n', ...st }); return; }
      const next = { ...st };
      if (tag === 'em' || tag === 'i' || tag === 'cite') next.i = true;
      if (tag === 'strong' || tag === 'b') next.b = true;
      if (tag === 'a' && n.getAttribute('href')) next.href = n.getAttribute('href');
      for (const c of n.childNodes) walk(c, next);
    };
    for (const c of el.childNodes) walk(c, style);
    // trim the ends
    if (runs.length) { runs[0].text = runs[0].text.replace(/^\s+/, ''); runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, ''); }
    return runs.filter((r) => r.text);
  };
  const visit = (el) => {
    for (const n of el.children) {
      const tag = n.tagName.toLowerCase();
      if (n.classList.contains('formac') || tag === 'details' || tag === 'hr') continue;
      if (/^h[1-6]$/.test(tag)) { const runs = runsOf(n); if (runs.length) blocks.push({ kind: 'h', level: +tag[1], runs }); continue; }
      if (tag === 'ul' || tag === 'ol') {
        for (const li of n.children) { const runs = runsOf(li); if (runs.length) blocks.push({ kind: 'li', runs }); }
        continue;
      }
      if (tag === 'p' || tag === 'blockquote') {
        const runs = runsOf(n);
        if (!runs.length) continue;
        // a line that is all italic right under a heading reads as its subtitle (the projects' "Helles · always on tap")
        const prev = blocks[blocks.length - 1];
        const allItalic = runs.every((r) => r.i || !r.text.trim());
        blocks.push({ kind: allItalic && prev?.kind === 'h' ? 'sub' : 'p', runs });
        continue;
      }
      if (tag === 'div' || tag === 'section' || tag === 'article') { visit(n); continue; }
      const runs = runsOf(n);
      if (runs.length) blocks.push({ kind: 'p', runs });
    }
  };
  visit(doc.body.firstElementChild);
  return blocks;
}

/** Plain text of blocks (the visually hidden copy uses the HTML itself; this is for tests and labels). */
export const blocksText = (blocks) => blocks.map((b) => b.runs.map((r) => r.text).join('')).join('\n');

// ---------------------------------------------------------------------------------------------------------
// measuring and wrapping

let ctx2d = null;
function measurer() {
  if (!ctx2d) ctx2d = document.createElement('canvas').getContext('2d');
  return ctx2d;
}
const widthCache = new Map();
/** Width of a string in a face at 1 m font size (em units). */
export function measure(text, fontKey) {
  const key = `${fontKey}|${text}`;
  let w = widthCache.get(key);
  if (w === undefined) {
    const g = measurer();
    g.font = `100px "${FONTS[fontKey].family}", Georgia, serif`;
    w = g.measureText(text).width / 100;
    if (widthCache.size > 20000) widthCache.clear();
    widthCache.set(key, w);
  }
  return w;
}

function styleOf(theme, block) {
  if (block.kind === 'h') return block.level <= 1 || block.top ? theme.h1 : theme.h;
  return theme[block.kind] || theme.p;
}
function fontFor(theme, st, run) {
  if (run.b && st.font !== theme.h.font && st.font !== theme.h1.font) return theme.strong;
  if (run.i && st.font !== theme.sub.font) return theme.em;
  return st.font;
}
const colorOf = (theme, st, run) => (run.href ? theme.link : st.color ? theme[st.color] || st.color : theme.color);

/**
 * Lines of one block at a font size (metres) inside a width: [{ height, segments: [{ text, font, color, x, w, href }] }].
 */
function wrapBlock(block, theme, base, width) {
  const st = styleOf(theme, block);
  const size = base * (block.size || st.size);
  const lineH = size * (st.lh || 1.2);
  // words with their run's look; a run boundary inside a word keeps the pieces together
  const tokens = [];
  const bullet = block.kind === 'li' && st.bullet ? sanitize(st.bullet) : '';
  const indent = bullet ? measure(bullet, st.font) * size : 0;
  for (const run of block.runs) {
    const font = fontFor(theme, st, run);
    const color = colorOf(theme, st, run);
    const parts = sanitize(run.text).split(/(\n| +)/);
    for (const p of parts) {
      if (!p) continue;
      if (p === '\n') tokens.push({ br: true });
      else if (/^ +$/.test(p)) tokens.push({ space: true, font });
      else tokens.push({ text: p, font, color, href: run.href || null });
    }
  }
  const lines = [];
  let line = { segments: [], w: 0 };
  let pendingSpace = null;
  const avail = (l) => width - (lines.length || l !== line ? indent : indent);
  const push = () => { lines.push(line); line = { segments: [], w: 0 }; pendingSpace = null; };
  for (const t of tokens) {
    if (t.br) { push(); continue; }
    if (t.space) { if (line.segments.length) pendingSpace = t; continue; }
    const sw = pendingSpace ? measure(' ', pendingSpace.font) * size : 0;
    let ww = measure(t.text, t.font) * size;
    if (line.segments.length && line.w + sw + ww > avail(line)) push();
    // a word longer than the line: cut it
    while (ww > avail(line) && t.text.length > 1) {
      let k = t.text.length - 1;
      while (k > 1 && measure(t.text.slice(0, k) + '-', t.font) * size > avail(line)) k--;
      addSeg(line, { ...t, text: t.text.slice(0, k) + '-' }, 0, size);
      push();
      t.text = t.text.slice(k);
      ww = measure(t.text, t.font) * size;
    }
    addSeg(line, t, line.segments.length ? sw : 0, size);
    pendingSpace = null;
  }
  if (line.segments.length || !lines.length) push();
  // bullets and indents
  lines.forEach((l, i) => {
    for (const s of l.segments) s.x += indent;
    if (i === 0 && bullet) l.segments.unshift({ text: bullet, font: st.font, color: theme.muted, x: 0, w: indent, size });
    l.height = lineH;
    l.size = size;
  });
  return { lines, gap: base * (st.gap ?? 0.5), keepWithNext: block.kind === 'h' };
}
function addSeg(line, t, space, size) {
  const last = line.segments[line.segments.length - 1];
  const ww = measure(t.text, t.font) * size;
  // the same look as the last segment: extend it (fewer Text meshes)
  if (last && last.font === t.font && last.color === t.color && last.href === t.href) {
    last.text += (space ? ' ' : '') + t.text;
    last.w = measure(last.text, last.font) * size;
    line.w = last.x + last.w;
    return;
  }
  const x = line.w + space;
  line.segments.push({ text: (space && !last ? ' ' : '') + t.text, font: t.font, color: t.color, href: t.href, x, w: ww, size });
  line.w = x + ww;
}

/**
 * Pages for a writing area: area = { w, h, base (font size, m), theme, align? }. A heading never ends a page.
 * Returns [{ lines: [{ y (top, m), height, segments }], used }] — at least one page.
 */
export function paginate(blocks, { w, h, base, theme: themeKey = 'print', firstPageTop = 0 }) {
  const theme = THEMES[themeKey] || THEMES.print;
  const wrapped = blocks.map((b) => wrapBlock(b, theme, base, w));
  const pages = [];
  let page = { lines: [] };
  let y = firstPageTop;
  const newPage = () => { pages.push(page); page = { lines: [] }; y = 0; };
  wrapped.forEach((wb, bi) => {
    const gap = page.lines.length ? wb.gap : 0;
    const blockH = wb.lines.reduce((a, l) => a + l.height, 0);
    // a heading keeps its next block's first two lines with it
    let need = wb.lines[0]?.height || 0;
    if (wb.keepWithNext && wrapped[bi + 1]) need = blockH + wrapped[bi + 1].gap + wrapped[bi + 1].lines.slice(0, 2).reduce((a, l) => a + l.height, 0);
    else if (blockH <= h * 0.35) need = blockH; // a short block is not split
    if (page.lines.length && y + gap + need > h) newPage();
    else y += gap;
    for (const l of wb.lines) {
      if (page.lines.length && y + l.height > h + 1e-6) newPage();
      page.lines.push({ ...l, y });
      y += l.height;
    }
  });
  if (page.lines.length || !pages.length) pages.push(page);
  for (const p of pages) p.used = p.lines.length ? p.lines[p.lines.length - 1].y + p.lines[p.lines.length - 1].height : 0;
  return pages;
}

// ---------------------------------------------------------------------------------------------------------
// drawing

const materials = new Map();
/** The text material of a theme: lit like the surface, with a little of its own glow so it reads at night. */
function textMaterial(kind, glow, glowColor = '#ffffff') {
  const key = `${kind}|${glow}|${glowColor}`;
  if (!materials.has(key)) {
    // the glow takes the ink's own colour (chalk glows chalk-white; printed ink is given no glow)
    const m = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, emissive: new THREE.Color(glowColor), emissiveIntensity: glow, transparent: true });
    m.name = `engine_text_${kind}`;
    materials.set(key, m);
  }
  return materials.get(key);
}

/**
 * Draw one page into a new Group in the area's plane. Options: theme, glow (self-light 0..1), z (lift above the
 * surface), align ('left'|'center'), w (area width, for centring), opacity.
 * Returns { group, links: [mesh], ready: Promise, setOpacity(k), dispose() }.
 */
export function renderPage(page, { theme: themeKey = 'print', glow = 0.12, z = 0.0015, align = 'left', w = 1, rough = false } = {}) {
  const theme = THEMES[themeKey] || THEMES.print;
  const group = new THREE.Group();
  group.name = 'engine_text_page';
  const texts = [];
  const links = [];
  const mat = textMaterial(themeKey, glow, theme.color);
  const specs = [];
  let opacity = 1, disposed = false;
  for (const line of page.lines) {
    const lw = line.segments.length ? Math.max(...line.segments.map((s) => s.x + s.w)) : 0;
    const dx = align === 'center' ? Math.max(0, (w - lw) / 2) : 0;
    for (const s of line.segments) {
      if (!s.text.trim()) continue;
      specs.push({ s, line, dx });
      if (s.href) {
        // the link: a thin underline you can see, and a quad over the words you can click
        const u = new THREE.Mesh(new THREE.PlaneGeometry(s.w, Math.max(0.0008, s.size * 0.06)), new THREE.MeshBasicMaterial({ color: new THREE.Color(s.color), transparent: true, opacity: 0.85 }));
        u.position.set(s.x + dx + s.w / 2, -(line.y + line.height / 2) - s.size * 0.42, z);
        u.raycast = () => {};
        u.name = 'engine_text_underline';
        group.add(u);
        const hit = new THREE.Mesh(new THREE.PlaneGeometry(s.w + s.size * 0.3, line.height), new THREE.MeshBasicMaterial({ visible: false }));
        hit.position.set(s.x + dx + s.w / 2, -(line.y + line.height / 2), z + 0.0005);
        hit.name = 'engine_text_link';
        hit.userData.href = s.href;
        hit.userData.linkText = s.text.trim();
        group.add(hit);
        links.push(hit);
      }
    }
  }
  let batch = null;
  const ready = new Promise((done) => whenText(() => {
    if (disposed) { done(); return; }
    // one draw for the page's words (see newBatch); a page of a single run keeps its plain Text
    if (specs.length > 1) {
      batch = newBatch();
      batch.name = 'engine_text_batch';
      batch.isText = true;
      batch.material = mat;
      batch.userData.itemFx = true;
      batch.raycast = () => {};
      group.add(batch);
    }
    for (const { s, line, dx } of specs) {
      const t = newText();
      t.isText = true;
      t.text = s.text;
      t.font = FONTS[s.font].url;
      t.fontSize = s.size;
      t.color = s.color;
      t.anchorX = 'left';
      t.anchorY = 'middle';
      t.lineHeight = line.height / s.size;
      t.whiteSpace = 'nowrap';
      t.material = mat;
      t.fillOpacity = opacity;
      t.position.set(s.x + dx, -(line.y + line.height / 2), z);
      // chalk is never quite straight
      if (rough) t.rotation.z = Math.sin((line.y * 37 + s.x * 11) * 3.1) * 0.006;
      t.userData.itemFx = true;
      t.raycast = () => {}; // the surface and the link quads answer the pointer, not the glyphs
      if (batch) batch.addText(t); else group.add(t);
      texts.push(t);
    }
    Promise.all(texts.map((t) => new Promise((res) => { try { t.sync(res); } catch { res(); } }))).then(() => done());
  }));
  return {
    group, links, ready, texts,
    setOpacity(k) { opacity = k; for (const t of texts) t.fillOpacity = k; group.children.forEach((c) => { if (c.name === 'engine_text_underline') c.material.opacity = 0.85 * k; }); },
    dispose() {
      disposed = true;
      group.removeFromParent();
      for (const t of texts) { batch?.removeText(t); t.dispose(); }
      batch?.dispose();
      group.traverse((o) => { if (o.isMesh && !o.isText && o.geometry) { o.geometry.dispose(); o.material?.dispose?.(); } });
    },
  };
}

/** A single label (a signpost arm, a coaster's name): one Text (in a group), centred unless told otherwise. */
export function label(text, { font = 'sans', size = 0.05, color = '#2a1d14', glow = 0.15, anchorX = 'center', anchorY = 'middle', maxWidth = Infinity, letterSpacing = 0 } = {}) {
  // a group the caller places now; the Text itself arrives with troika
  const g = new THREE.Group();
  g.name = 'engine_text_label';
  g.userData.text = sanitize(text);
  whenText(() => {
    const t = newText();
    t.text = g.userData.text;
    t.font = FONTS[font].url;
    t.fontSize = size;
    t.color = color;
    t.anchorX = anchorX;
    t.anchorY = anchorY;
    t.letterSpacing = letterSpacing;
    if (Number.isFinite(maxWidth)) t.maxWidth = maxWidth;
    t.material = textMaterial(`label_${font}`, glow, color);
    t.raycast = () => {};
    t.userData.itemFx = true;
    t.sync();
    g.add(t);
  });
  return g;
}

/** Fit a single line into a width: the largest size up to `size` at which it fits. */
export function fitSize(text, font, size, width) {
  const w = measure(sanitize(text), font);
  return w > 0 ? Math.min(size, width / w) : size;
}
