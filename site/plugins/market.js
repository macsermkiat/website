// Build-time plugin for the Nachtmarkt site.
//
// It provides three virtual modules and one HTML transform:
//   virtual:market-content    panel content built from ../content/*.md (the writer's files),
//                             falling back to site/content-fallback/*.md (the prototype text)
//   virtual:market-inventory  which model, props and audio files exist in site/public, so the
//                             page never requests a file that is not there (no 404s in the console)
//   plain.html                the text version, filled with the same content at build time
// It also serves / emits the prototype's instrument samples for the generative band fallback.

import fs from 'node:fs';
import path from 'node:path';
import { marked } from 'marked';
import YAML from 'yaml';

const SITE = path.resolve(import.meta.dirname, '..');
const REPO = path.resolve(SITE, '..');
const CONTENT_DIR = path.join(REPO, 'content');
const FALLBACK_DIR = path.join(SITE, 'content-fallback');
const PUBLIC = path.join(SITE, 'public');
const SAMPLES = path.join(REPO, 'prototype', 'samples.json');

export const SECTION_ORDER = ['glueh', 'bier', 'wurst', 'books', 'band', 'ferris', 'carousel'];

// Words that identify a section in a file name, a front-matter field or a heading.
const ALIASES = {
  glueh: ['glueh', 'gluehwein', 'glühwein', 'gluhwein', 'about', 'about-me', 'aboutme'],
  bier: ['bier', 'bierstand', 'beer', 'projects', 'project'],
  wurst: ['wurst', 'bratwurst', 'writing', 'essays', 'writings'],
  books: ['books', 'book', 'buecher', 'bücher', 'buecherstand', 'bücherstand', 'bookshop', 'reading'],
  band: ['band', 'bandstand', 'music'],
  ferris: ['ferris', 'riesenrad', 'big-questions', 'bigquestions', 'questions', 'big questions'],
  carousel: ['carousel', 'karussell', 'contact'],
  site: ['site', 'home', 'index', 'intro', 'homepage', 'market', 'tagline'],
  phrases: ['phrases', 'crowd', 'chatter', 'crowd-phrases'],
};

function slug(s) {
  return String(s || '')
    .toLowerCase()
    .normalize('NFC')
    .replace(/^\d+[-_ .]*/, '')
    .replace(/[_\s]+/g, '-')
    .replace(/\.md$/, '')
    .trim();
}

function idFor(word) {
  const w = slug(word);
  if (!w) return null;
  for (const [id, list] of Object.entries(ALIASES)) {
    if (list.some((a) => slug(a) === w)) return id;
  }
  // loose match: "01-about-mac", "stall-gluehwein", "section-reading"
  for (const [id, list] of Object.entries(ALIASES)) {
    if (list.some((a) => w.split('-').includes(slug(a)))) return id;
  }
  return null;
}

// YAML front matter (the writer keeps hints, action notes, books and crowd lines there).
function frontMatter(src) {
  const m = /^\uFEFF?---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(src);
  if (!m) return { data: {}, body: src };
  let data = {};
  try {
    data = YAML.parse(m[1]) || {};
  } catch (e) {
    console.warn(`[content] front matter could not be read: ${e.message}`);
  }
  const lower = {};
  for (const [k, v] of Object.entries(data)) lower[k.toLowerCase()] = v;
  return { data: lower, body: src.slice(m[0].length) };
}

// Notes for Mac to fill in ("[[Mac: ...]]") show as a marked gap; "[check]" style markers as a small tag.
// "<!-- check -->" comments stay invisible.
function markChecks(md) {
  return md
    .replace(/\[\[([\s\S]+?)\]\]/g, (_, note) => `<span class="formac">${note.replace(/</g, '&lt;').trim()}</span>`)
    .replace(/\[(?:check|verify|todo|mac to check)(?::\s*([^\]]*))?\]/gi, (_, note) =>
      `<mark class="check" title="${(note || 'For Mac to check').replace(/"/g, '&quot;')}">check</mark>`);
}

const str = (v) => (typeof v === 'string' ? v : '');

function sectionFromMarkdown(id, src, file) {
  const { data, body } = frontMatter(src);
  let md = body.trim();
  let title = data.title || '';
  // A leading "# Title" becomes the panel title.
  const h1 = /^#\s+(.+)\r?\n+/.exec(md);
  if (h1) {
    if (!title) title = h1[1].trim();
    md = md.slice(h1[0].length);
  }
  const html = marked.parse(markChecks(md), { async: false });
  const items = [...md.matchAll(/^\s*[-*]\s+(.+)$/gm)].map((m) => m[1].trim());
  return {
    id,
    name: str(data.name) || str(data.stall) || str(data.place) || '',
    sub: str(data.sub) || str(data.eyebrow) || str(data.subtitle) || (typeof data.section === 'string' && !idFor(data.section) ? data.section : '') || '',
    title,
    html,
    items, // raw list items, used for the bookshop picks and crowd phrases
    meta: data, // everything else from the front matter: hint, actions, notes, books, crowd, tagline, ui...
    source: path.relative(REPO, file),
  };
}

// A file may hold several sections under "## Heading" lines whose text names a section.
function splitByHeadings(src, file) {
  const out = [];
  const parts = src.split(/^(?=#{1,2}\s)/m);
  for (const part of parts) {
    const h = /^#{1,2}\s+(.+)$/m.exec(part);
    if (!h) continue;
    const id = idFor(h[1]) || idFor(h[1].split(/[·:(—-]/)[0]);
    if (!id) continue;
    const body = part.replace(/^#{1,2}\s+.+\r?\n/, '');
    out.push(sectionFromMarkdown(id, `# ${h[1]}\n\n${body}`, file));
  }
  return out;
}

function readDir(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { recursive: true })
    .map(String)
    .filter((f) => f.toLowerCase().endsWith('.md') && !/readme\.md$/i.test(f))
    .sort()
    .map((f) => path.join(dir, f));
}

function loadSections(dir) {
  const found = {};
  for (const file of readDir(dir)) {
    const src = fs.readFileSync(file, 'utf8');
    const { data } = frontMatter(src);
    const id =
      idFor(data.id) || idFor(data.section_id) || idFor(data.place) || idFor(data.stall) ||
      idFor(path.basename(file)) || idFor(data.section) || idFor(data.title);
    if (id) {
      if (!found[id]) found[id] = sectionFromMarkdown(id, src, file);
    } else {
      for (const s of splitByHeadings(src, file)) if (!found[s.id]) found[s.id] = s;
    }
  }
  return found;
}

export function buildContent() {
  const fallback = loadSections(FALLBACK_DIR);
  const writer = loadSections(CONTENT_DIR);
  const sections = {};
  for (const id of [...SECTION_ORDER, 'site', 'phrases']) {
    const w = writer[id];
    const f = fallback[id];
    if (!w && !f) continue;
    // Take the writer's text; keep the stall name and subtitle from the fallback when the writer left them out.
    sections[id] = w
      ? { ...w, name: w.name || f?.name || '', sub: w.sub || f?.sub || '', title: w.title || f?.title || '', fromWriter: true }
      : { ...f, fromWriter: false };
  }
  // the writer's `order:` (1-7) sets the order of the place buttons and the plain page, when every section has one
  const nums = SECTION_ORDER.map((id) => Number(sections[id]?.meta?.order));
  const order = nums.every((n) => Number.isFinite(n))
    ? [...SECTION_ORDER].sort((a, b) => nums[SECTION_ORDER.indexOf(a)] - nums[SECTION_ORDER.indexOf(b)])
    : SECTION_ORDER;
  return { order, sections };
}

function listFiles(dir, base = dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listFiles(p, base));
    else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out;
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

export function buildInventory() {
  const models = listFiles(path.join(PUBLIC, 'models')).filter((f) => /\.(glb|gltf|json)$/i.test(f));
  const audioFiles = listFiles(path.join(PUBLIC, 'audio'));
  const manifest = readJson(path.join(PUBLIC, 'audio', 'manifest.json'));
  let audio = null;
  if (manifest && manifest.stems && typeof manifest.stems === 'object') {
    // Keep only stems whose files exist (absolute URLs are trusted as-is).
    const stems = {};
    for (const [k, url] of Object.entries(manifest.stems)) {
      if (typeof url !== 'string') continue;
      const rel = url.replace(/^\.?\//, '').replace(/^audio\//, '');
      if (/^https?:/.test(url) || audioFiles.includes(rel)) stems[k] = url;
    }
    if (Object.keys(stems).length) audio = { ...manifest, stems };
  }
  return {
    models,
    props: models.includes('props.json') ? readJson(path.join(PUBLIC, 'models', 'props.json')) : null,
    audio,
    samples: fs.existsSync(SAMPLES),
  };
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

// Licence names in a credit line become links to the licence deeds (CC BY and CC BY-SA ask for a link).
const LICENCES = [
  [/CC BY-SA 3\.0/g, 'https://creativecommons.org/licenses/by-sa/3.0/'],
  [/CC BY 3\.0/g, 'https://creativecommons.org/licenses/by/3.0/'],
  [/CC0(?: 1\.0)?/g, 'https://creativecommons.org/publicdomain/zero/1.0/'],
];
const CREDITS_URL = 'https://github.com/macsermkiat/website/blob/main/CREDITS.md';
function linkLicences(text) {
  let out = esc(text);
  const marks = [];
  for (const [re, url] of LICENCES) out = out.replace(re, (m) => { marks.push(`<a href="${url}" rel="license">${m}</a>`); return `\u0000${marks.length - 1}\u0000`; });
  return out.replace(/\u0000(\d+)\u0000/g, (_, i) => marks[+i]);
}

/**
 * The music credit shown in the footer of both pages, drawn from the music writer's manifest.license.credit
 * (the recording holds CC BY and CC BY-SA samples, which must be credited where the music plays).
 * The generative fallback band's samples (FluidR3 GM, CC BY 3.0) are credited as well, since it can play instead.
 */
export function audioCredit(inv = buildInventory()) {
  const m = inv.audio;
  const lines = [];
  const lic = m?.license || m?.licence || {};
  const credit = lic.credit || lic.recording?.credit || (typeof lic.recording === 'string' ? lic.recording : '');
  if (credit) {
    const title = m.title ? `Music: “${esc(m.title)}”, an original ballad for this site. ` : 'Music: ';
    lines.push(`${title}${linkLicences(credit)}`);
  }
  if (inv.samples) lines.push(`If the recording cannot play, a stand-in band uses the ${linkLicences('FluidR3 GM soundfont by Frank Wen (CC BY 3.0)')} and Tone.js drum samples (MIT).`);
  if (!lines.length) return '';
  lines.push(`<a href="${CREDITS_URL}">All credits</a>.`);
  return lines.join(' ');
}

export function plainHtml(content) {
  const { sections, order } = content;
  const nav = order
    .filter((id) => sections[id])
    .map((id) => `<li><a href="#${id}">${esc(sections[id].name)} <span>${esc(sections[id].sub)}</span></a></li>`)
    .join('\n        ');
  const body = order
    .filter((id) => sections[id])
    .map((id) => {
      const s = sections[id];
      return `
    <section id="${id}" aria-labelledby="${id}-h">
      <p class="eyebrow">${esc(s.name)} · ${esc(s.sub)}</p>
      <h2 id="${id}-h">${esc(s.title || s.sub)}</h2>
      ${s.html}
    </section>`;
    })
    .join('\n');
  const intro = sections.site ? sections.site.html : '';
  return { nav, body, intro };
}

const V_CONTENT = 'virtual:market-content';
const V_INV = 'virtual:market-inventory';

export default function marketPlugin() {
  let isBuild = false;
  return {
    name: 'nachtmarkt-market',
    configResolved(cfg) {
      isBuild = cfg.command === 'build';
    },
    buildStart() {
      if (!isBuild) return;
      // The writer's [[Mac: ...]] placeholders show as amber notes on the site. Say how many are left, and
      // stop the build when STRICT_CONTENT=1 (for the day the site goes public).
      const left = [];
      for (const f of listFiles(CONTENT_DIR).filter((f) => f.endsWith('.md'))) {
        const n = (fs.readFileSync(path.join(CONTENT_DIR, f), 'utf8').match(/\[\[[\s\S]+?\]\]/g) || []).length;
        if (n) left.push(`${f}: ${n}`);
      }
      if (!left.length) return;
      const msg = `content placeholders still to fill: ${left.join(', ')}`;
      if (process.env.STRICT_CONTENT === '1') this.error(msg);
      else this.warn(msg);
    },
    resolveId(id) {
      if (id === V_CONTENT || id === V_INV) return '\0' + id;
      return null;
    },
    load(id) {
      if (id === '\0' + V_CONTENT) {
        for (const f of [...readDir(CONTENT_DIR), ...readDir(FALLBACK_DIR)]) this.addWatchFile?.(f);
        return `export default ${JSON.stringify(buildContent())};`;
      }
      if (id === '\0' + V_INV) {
        return `export default ${JSON.stringify(buildInventory())};`;
      }
      return null;
    },
    transformIndexHtml: {
      order: 'pre',
      handler(html, ctx) {
        const content = buildContent();
        if (!/plain\.html$/.test(ctx.filename || ctx.path || '')) {
          const site = content.sections.site;
          const tagline = site?.meta?.tagline ? `<p>${esc(site.meta.tagline)}</p>` : site && !site.fromWriter ? site.html : '';
          const hint = site?.meta?.ui?.hint;
          let out = html.replace('<!--TAGLINE-->', tagline).replace('<!--AUDIO_CREDIT-->', audioCredit());
          if (site?.meta?.description) out = out.replace(/(<meta name="description" content=")[^"]*"/, `$1${esc(site.meta.description)}"`);
          if (hint) out = out.replace(/(<p class="hint" id="hint">)[\s\S]*?(<\/p>)/, `$1${esc(hint)} Keyboard: Tab reaches the places below, or press 1–7.$2`);
          return out;
        }
        const { nav, body, intro } = plainHtml(content);
        return html.replace('<!--PLAIN_NAV-->', nav).replace('<!--PLAIN_BODY-->', body).replace('<!--PLAIN_INTRO-->', intro).replace('<!--AUDIO_CREDIT-->', audioCredit());
      },
    },
    configureServer(server) {
      // Serve the prototype's instrument samples for the generative fallback band in dev.
      server.middlewares.use((req, res, next) => {
        if (req.url && req.url.endsWith('/fallback/samples.json') && fs.existsSync(SAMPLES)) {
          res.setHeader('Content-Type', 'application/json');
          fs.createReadStream(SAMPLES).pipe(res);
          return;
        }
        next();
      });
      // Content, model or audio changes: reload so the inventory is fresh.
      const watchDirs = [CONTENT_DIR, path.join(PUBLIC, 'models'), path.join(PUBLIC, 'audio')];
      server.watcher.add(watchDirs);
      server.watcher.on('all', (_e, file) => {
        if (watchDirs.some((d) => file.startsWith(d))) {
          for (const v of [V_CONTENT, V_INV]) {
            const mod = server.moduleGraph.getModuleById('\0' + v);
            if (mod) server.moduleGraph.invalidateModule(mod);
          }
          server.ws.send({ type: 'full-reload' });
        }
      });
    },
    generateBundle() {
      if (!isBuild) return;
      // The generative band is only a fallback; its samples are emitted from prototype/ rather than copied into git.
      // They are fetched only if the stems cannot play.
      if (fs.existsSync(SAMPLES)) {
        this.emitFile({ type: 'asset', fileName: 'fallback/samples.json', source: fs.readFileSync(SAMPLES) });
      }
    },
  };
}
