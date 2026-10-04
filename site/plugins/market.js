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

// Notes for Mac to fill in ("[[Mac: ...]]") and "[check]" markers.
//   'show' (npm run dev, or CONTENT_NOTES=show): a note shows as a marked gap, a check marker as a small tag.
//   'hide' (every production build by default): a note never reaches the page. The paragraph or list item
//          that holds it is left out, a lead-in line ending in ":" whose list is now empty goes too, and a
//          front-matter value holding a note becomes empty. Check markers are dropped.
// "<!-- check -->" comments stay invisible either way. STRICT_CONTENT=1 fails the build while notes remain.
let NOTES_MODE = 'show';
export function setNotesMode(mode) {
  NOTES_MODE = mode === 'hide' ? 'hide' : 'show';
}
const NOTE_RE = /\[\[[\s\S]+?\]\]/;
const CHECK_RE = /\[(?:check|verify|todo|mac to check)(?::\s*([^\]]*))?\]/gi;

/** Leave every [[...]] note out of the markdown: its paragraph or list item goes, and an orphaned lead-in. */
export function stripNotes(md) {
  const blocks = md.split(/\n{2,}/);
  const kept = [];
  for (const block of blocks) {
    if (!NOTE_RE.test(block)) { kept.push(block); continue; }
    const lines = block.split('\n');
    const isList = lines.every((l) => !l.trim() || /^\s*([-*+]|\d+[.)])\s+/.test(l) || /^\s{2,}\S/.test(l));
    if (!isList) continue; // a paragraph (or heading) holding a note is left out whole
    // a list: drop only the items holding a note (an item runs until the next marker line)
    const items = [];
    for (const l of lines) {
      if (/^\s*([-*+]|\d+[.)])\s+/.test(l) || !items.length) items.push([l]);
      else items[items.length - 1].push(l);
    }
    const rest = items.filter((it) => !NOTE_RE.test(it.join('\n'))).map((it) => it.join('\n'));
    if (rest.length) kept.push(rest.join('\n'));
    else if (kept.length && /:\s*(<!--[\s\S]*?-->)?\s*$/.test(kept[kept.length - 1])) kept.pop(); // "What I'm listening to:" with nothing under it
  }
  return kept.join('\n\n').replace(CHECK_RE, '').replace(/[ \t]*<!--[\s\S]*?-->/g, '');
}

/** Front matter with every note-bearing value emptied (strings) or left out (list entries). */
function stripMetaNotes(v) {
  if (typeof v === 'string') return NOTE_RE.test(v) ? '' : v.replace(CHECK_RE, '').trim();
  if (Array.isArray(v)) return v.filter((x) => !(typeof x === 'string' && NOTE_RE.test(x))).map(stripMetaNotes);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, stripMetaNotes(x)]));
  return v;
}

function markChecks(md) {
  if (NOTES_MODE === 'hide') return stripNotes(md);
  return md
    .replace(/\[\[([\s\S]+?)\]\]/g, (_, note) => `<span class="formac">${note.replace(/</g, '&lt;').trim()}</span>`)
    .replace(/\[(?:check|verify|todo|mac to check)(?::\s*([^\]]*))?\]/gi, (_, note) =>
      `<mark class="check" title="${(note || 'For Mac to check').replace(/"/g, '&quot;')}">check</mark>`);
}

const str = (v) => (typeof v === 'string' ? v : '');

function sectionFromMarkdown(id, src, file) {
  const fm = frontMatter(src);
  const data = NOTES_MODE === 'hide' ? stripMetaNotes(fm.data) : fm.data;
  let md = fm.body.trim();
  let title = data.title || '';
  // A leading "# Title" becomes the panel title.
  const h1 = /^#\s+(.+)\r?\n+/.exec(md);
  if (h1) {
    if (!title) title = h1[1].trim();
    md = md.slice(h1[0].length);
  }
  const shown = markChecks(md);
  const html = marked.parse(shown, { async: false });
  const items = [...(NOTES_MODE === 'hide' ? shown : md).matchAll(/^\s*[-*]\s+(.+)$/gm)].map((m) => m[1].trim());
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
    .readdirSync(dir)
    .map(String)
    // the section files only: sub-folders (content/books/, one page per book on Mac's shelf) are read by buildLibrary
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
  // The Bücherstand's front-matter `books:` list is not confirmed by Mac (content/reading.md says so, and its body
  // list shares a block with a note for Mac). It is never written back into the panel or the text page. In a
  // notes-hidden build the 3D shelf keeps only the entries that are on Mac's own shelf (content/books/categories.json);
  // "Pick a book for me" then goes on to his shelf's other books.
  const bk = sections.books;
  const library = buildLibrary();
  if (bk && Array.isArray(bk.meta?.books) && NOTES_MODE === 'hide' && library.books.length) {
    const mine = new Set(library.books.map((b) => normTitle(b.title)));
    const kept = bk.meta.books.filter((b) => mine.has(normTitle(typeof b === 'string' ? b : b?.title)));
    bk.shelfDropped = bk.meta.books.length - kept.length;
    bk.meta = { ...bk.meta, books: kept };
  }
  // Mac's own bookshelf (content/books/categories.json and the writer's content/books/<slug>.md): listed under the
  // bookshop in the panel and on the text page (with every book's reading page there), and read by the 3D shelf.
  if (bk && library.books.length) {
    bk.html += libraryHtml(library);
    bk.libraryAdded = library.books.length;
  }
  // the writer's `order:` (1-7) sets the order of the place buttons and the plain page, when every section has one
  const nums = SECTION_ORDER.map((id) => Number(sections[id]?.meta?.order));
  const order = nums.every((n) => Number.isFinite(n))
    ? [...SECTION_ORDER].sort((a, b) => nums[SECTION_ORDER.indexOf(a)] - nums[SECTION_ORDER.indexOf(b)])
    : SECTION_ORDER;
  return { order, sections, library };
}

export const normTitle = (t) => String(t || '').toLowerCase().normalize('NFC').replace(/[’']/g, '').replace(/[^\p{L}\p{N}]+/gu, '');
const slugTitle = (t) => String(t || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[’']/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/**
 * Mac's bookshelf: content/books/categories.json is the only source of titles, authors, slugs and categories
 * (BUILD.md, "Bücherstand categories"). Each book gets its one-line summary and its reading page from
 * content/books/<slug>.md when the writer has done it. No categories file means an empty library.
 * A book page marked `review: check` is counted by the content gate (STRICT_CONTENT=1 stops on it).
 */
export function buildLibrary(dir = CONTENT_DIR) {
  const cats = readJson(path.join(dir, 'books', 'categories.json'));
  const bookDir = path.join(dir, 'books');
  const books = [];
  const categories = [];
  const pages = {};
  for (const c of Array.isArray(cats?.categories) ? cats.categories : []) {
    const list = [];
    for (const b of Array.isArray(c.books) ? c.books : []) {
      if (!b?.title) continue;
      const slug = String(b.slug || slugTitle(b.title));
      const file = path.join(bookDir, `${slug}.md`);
      const page = fs.existsSync(file) ? bookPage(fs.readFileSync(file, 'utf8')) : null;
      const entry = {
        title: String(b.title),
        author: String(b.author || page?.author || ''),
        slug,
        category: String(c.key || ''),
        categoryDe: String(c.label_de || ''),
        oneLine: page?.oneLine || '',
        page: !!page,
      };
      if (page) pages[slug] = page.html;
      books.push(entry);
      list.push(entry);
    }
    if (list.length) categories.push({ key: String(c.key || ''), label: String(c.label_en || c.label || c.key || ''), labelDe: String(c.label_de || ''), books: list });
  }
  return { books, categories, pages, source: 'content/books/categories.json' };
}

/** One book's reading page: its markdown body (In short, Summary, Key ideas, ...) with notes handled as elsewhere. */
export function bookPage(src) {
  const { data, body } = frontMatter(src);
  const meta = NOTES_MODE === 'hide' ? stripMetaNotes(data) : data;
  // the page's own headings sit under the book's title: "## Summary" becomes an h3
  const md = markChecks(body.trim().replace(/^#\s+.+\r?\n+/, ''));
  const html = marked.parse(md, { async: false }).replace(/<(\/?)h([1-5])>/g, (_, sl, n) => `<${sl}h${Math.min(6, +n + 1)}>`);
  const one = str(meta.one_line || meta.oneline || meta.note);
  const sources = Array.isArray(meta.sources) ? meta.sources.filter((u) => typeof u === 'string' && /^https?:\/\//.test(u)) : [];
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };
  const srcHtml = sources.length ? `<p class="sources">Sources: ${sources.map((u) => `<a href="${esc(u)}" rel="noopener">${esc(host(u))}</a>`).join(', ')}</p>` : '';
  return {
    author: str(meta.author),
    oneLine: NOTES_MODE === 'hide' && NOTE_RE.test(one) ? '' : one.replace(CHECK_RE, '').trim(),
    html: html + srcHtml,
    sources,
  };
}

/** A book's reading page as an HTML fragment (fetched by the 3D reading view, inlined in the text page). */
export function bookFragment(lib, slug, { level = 3 } = {}) {
  const b = lib.books.find((x) => x.slug === slug);
  if (!b || !lib.pages?.[slug]) return '';
  const shift = (html) => html.replace(/<(\/?)h([1-6])>/g, (_, sl, n) => `<${sl}h${Math.min(6, +n + level - 3)}>`);
  return shift(lib.pages[slug]);
}

/**
 * The bookshelf as HTML for the panel and the text page: one list per category. Each title links to its reading
 * page (on the text page an anchor further down; in the 3D market the link opens the book on its shelf).
 */
export function libraryHtml(lib, { open = false } = {}) {
  if (!lib?.books?.length) return '';
  const groups = lib.categories.map((c) => {
    const li = c.books.map((b) => {
      const t = b.page ? `<a href="plain.html#book-${esc(b.slug)}" data-book="${esc(b.slug)}"><em>${esc(b.title)}</em></a>` : `<em>${esc(b.title)}</em>`;
      return `<li>${t}${b.author ? ` · ${esc(b.author)}` : ''}${b.oneLine ? `. <span class="one-line">${esc(b.oneLine)}</span>` : ''}</li>`;
    }).join('');
    return `${c.label ? `<h4>${esc(c.label)}${c.labelDe ? ` <span lang="de">· ${esc(c.labelDe)}</span>` : ''}</h4>` : ''}<ul class="shelf-list">${li}</ul>`;
  }).join('\n');
  return `\n<details class="library" id="bookshelf"${open ? ' open' : ''}><summary>Mac’s bookshelf: ${lib.books.length} books he has read, by subject</summary>\n${groups}\n</details>\n`;
}

/** Every book's reading page, for the text page: one article per book, by category. */
export function libraryPagesHtml(lib) {
  if (!lib?.books?.some((b) => b.page)) return '';
  const parts = lib.categories.map((c) => {
    const arts = c.books.filter((b) => b.page).map((b) => `
      <article class="bookpage" id="book-${esc(b.slug)}" aria-labelledby="book-${esc(b.slug)}-h">
        <h4 id="book-${esc(b.slug)}-h"><em>${esc(b.title)}</em></h4>
        ${b.author ? `<p class="byline">${esc(b.author)}</p>` : ''}
        ${bookFragment(lib, b.slug, { level: 5 })}
        <p class="back"><a href="#bookshelf">Back to the bookshelf</a></p>
      </article>`).join('');
    return arts ? `<h3 class="bookcat">${esc(c.label)}${c.labelDe ? ` <span lang="de">· ${esc(c.labelDe)}</span>` : ''}</h3>${arts}` : '';
  }).join('\n');
  return `\n<section class="booknotes" aria-label="Notes on every book on Mac’s shelf">\n<h3>Notes on every book</h3>\n${parts}\n</section>\n`;
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
    // the vendor's names for its act_ nodes (books carry title and author); keyed by node name
    items: models.includes('items.json') ? readJson(path.join(PUBLIC, 'models', 'items.json'))?.items || null : null,
    audio,
    samples: fs.existsSync(SAMPLES),
  };
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

// Licence names in a credit line become links to the licence deeds (CC BY and CC BY-SA ask for a link).
// Any Creative Commons licence named in a credit links to its deed (the music writer changes samples between
// rounds: MusyngKite CC BY-SA 3.0 gave way to the MTG saxophones under CC BY 4.0).
const LICENCES = [
  [/CC BY(-SA|-NC|-ND|-NC-SA|-NC-ND)? (\d\.\d)/g, (m, kind, v) => `https://creativecommons.org/licenses/by${(kind || '').toLowerCase()}/${v}/`],
  [/CC0(?: 1\.0)?/g, () => 'https://creativecommons.org/publicdomain/zero/1.0/'],
];
// The repository's CREDITS.md. In CI, GITHUB_REPOSITORY names the repository, so a rename (which the Pages
// base path now follows) keeps the link working; blob/HEAD follows the default branch. Local builds use Mac's repo.
export function creditsUrl(env = process.env) {
  const server = (env.GITHUB_SERVER_URL || 'https://github.com').replace(/\/+$/, '');
  const repo = /^[\w.-]+\/[\w.-]+$/.test(env.GITHUB_REPOSITORY || '') ? env.GITHUB_REPOSITORY : 'macsermkiat/website';
  return `${server}/${repo}/blob/HEAD/CREDITS.md`;
}
const CREDITS_URL = creditsUrl();
function linkLicences(text) {
  let out = esc(text);
  const marks = [];
  for (const [re, url] of LICENCES) out = out.replace(re, (m, ...g) => { marks.push(`<a href="${url(m, ...g)}" rel="license">${m}</a>`); return `\u0000${marks.length - 1}\u0000`; });
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

/**
 * Every third-party asset from the repository's CREDITS.md, with its source URL and licence, as a collapsible
 * list for the footer of both pages. Only the tables are taken (one per role); the roles' prose stays in the file.
 */
export function assetCredits(file = path.join(REPO, 'CREDITS.md')) {
  if (!fs.existsSync(file)) return '';
  const md = fs.readFileSync(file, 'utf8');
  const parts = [];
  for (const sec of md.split(/^## /m).slice(1)) {
    const heading = sec.split('\n')[0].trim();
    const tables = [];
    let cur = [];
    for (const line of sec.split('\n').slice(1)) {
      if (/^\s*\|/.test(line)) cur.push(line);
      else if (cur.length) { tables.push(cur.join('\n')); cur = []; }
    }
    if (cur.length) tables.push(cur.join('\n'));
    if (!tables.length) continue;
    const html = tables.map((t) => marked.parse(t, { async: false, gfm: true })).join('');
    parts.push(`<h3>${esc(heading)}</h3>${html}`);
  }
  if (!parts.length) return '';
  const body = parts.join('').replace(/<a href="(https?:[^"]+)"/g, '<a href="$1" rel="noopener"');
  return `<details class="credits-all"><summary>Credits: every third-party asset, with its source and licence</summary>${body}<p><a href="${CREDITS_URL}">CREDITS.md</a> in the repository has the notes behind each entry.</p></details>`;
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
      ${s.libraryAdded ? s.html.replace('<details class="library"', '<details class="library" open') + libraryPagesHtml(content.library) : s.html}
    </section>`;
    })
    .join('\n');
  const intro = sections.site ? sections.site.html : '';
  return { nav, body, intro };
}

/**
 * What still waits for Mac in content/*.md: [[Mac: ...]] notes, and claims marked for checking
 * (<!-- check --> comments and [check] tags). A production build leaves the notes out and hides the markers;
 * STRICT_CONTENT=1 (the release gate) stops the build while any of either is left.
 */
export function contentGate(dir = CONTENT_DIR) {
  const left = [];
  for (const f of listFiles(dir).filter((f) => f.endsWith('.md'))) {
    const src = fs.readFileSync(path.join(dir, f), 'utf8');
    const notes = (src.match(/\[\[[\s\S]+?\]\]/g) || []).length;
    const checks = (src.match(/<!--\s*check\b[\s\S]*?-->/gi) || []).length + (src.match(/\[(?:check|verify|todo|mac to check)(?::[^\]]*)?\]/gi) || []).length
      // a book page the writer has not yet reviewed (front matter `review: check`)
      + (/^books\//.test(f) && /^(check|todo|draft)$/i.test(String(frontMatter(src).data.review || '').trim()) ? 1 : 0);
    if (notes || checks) left.push({ file: f, notes, checks });
  }
  const one = (l) => `${l.file}: ${[l.notes && `${l.notes} note${l.notes > 1 ? 's' : ''}`, l.checks && `${l.checks} check marker${l.checks > 1 ? 's' : ''}`].filter(Boolean).join(', ')}`;
  // the book pages are many and alike: one line for all of them
  const pages = left.filter((l) => /^books\//.test(l.file) && !l.notes && l.checks === 1);
  const parts = left.filter((l) => !pages.includes(l)).map(one);
  if (pages.length) parts.push(`books/: ${pages.length} book page${pages.length > 1 ? 's' : ''} still marked review: check`);
  return { left, message: left.length ? `content still waiting for Mac: ${parts.join('; ')}` : '' };
}

const V_CONTENT = 'virtual:market-content';
const V_INV = 'virtual:market-inventory';

export default function marketPlugin() {
  let isBuild = false;
  return {
    name: 'nachtmarkt-market',
    configResolved(cfg) {
      isBuild = cfg.command === 'build';
      // A production build never shows the notes for Mac unless asked (CONTENT_NOTES=show, for a private preview).
      setNotesMode(isBuild && process.env.CONTENT_NOTES !== 'show' ? 'hide' : 'show');
    },
    buildStart() {
      if (!isBuild) return;
      const r = contentGate();
      if (!r.left.length) return;
      if (process.env.STRICT_CONTENT === '1') this.error(`${r.message} (STRICT_CONTENT=1 stops the build)`);
      else this.warn(`${r.message} (${NOTES_MODE === 'hide' ? 'left out of this build: their paragraphs and list items do not ship' : 'shown as notes, CONTENT_NOTES=show'})`);
    },
    resolveId(id) {
      if (id === V_CONTENT || id === V_INV) return '\0' + id;
      return null;
    },
    load(id) {
      if (id === '\0' + V_CONTENT) {
        for (const f of [...readDir(CONTENT_DIR), ...readDir(FALLBACK_DIR)]) this.addWatchFile?.(f);
        // the reading pages stay out of the bundle: the 3D reading view fetches reading/<slug>.html when a book opens
        const c = buildContent();
        const { pages, ...library } = c.library;
        library.books = library.books.map((b) => ({ ...b, page: !!pages[b.slug] }));
        return `export default ${JSON.stringify({ ...c, library })};`;
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
          let out = html.replace('<!--TAGLINE-->', tagline).replace('<!--AUDIO_CREDIT-->', audioCredit()).replace('<!--ASSET_CREDITS-->', assetCredits());
          if (site?.meta?.description) out = out.replace(/(<meta name="description" content=")[^"]*"/, `$1${esc(site.meta.description)}"`);
          if (hint) out = out.replace(/(<p class="hint" id="hint">)[\s\S]*?(<\/p>)/, `$1${esc(hint)} Keyboard: Tab reaches the places below, or press 1–7.$2`);
          return out;
        }
        const { nav, body, intro } = plainHtml(content);
        return html.replace('<!--PLAIN_NAV-->', nav).replace('<!--PLAIN_BODY-->', body).replace('<!--PLAIN_INTRO-->', intro).replace('<!--AUDIO_CREDIT-->', audioCredit()).replace('<!--ASSET_CREDITS-->', assetCredits());
      },
    },
    configureServer(server) {
      // Serve the prototype's instrument samples for the generative fallback band in dev.
      server.middlewares.use((req, res, next) => {
        const rd = req.url && /\/reading\/([a-z0-9-]+)\.html(?:\?|$)/.exec(req.url);
        if (rd) {
          const html = bookFragment(buildLibrary(), rd[1]);
          if (html) { res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end(html); return; }
        }
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
      // one small HTML fragment per book, fetched by the reading view when that book is opened in the market
      const lib = buildLibrary();
      for (const b of lib.books) {
        const html = bookFragment(lib, b.slug);
        if (html) this.emitFile({ type: 'asset', fileName: `reading/${b.slug}.html`, source: html });
      }
    },
  };
}
