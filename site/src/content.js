// Panel content, built at build time from content/*.md (the writer's files) with the prototype text as fallback.
// Besides the body, the writer's front matter can set each panel's hint, action labels and notes,
// the bookshop's books and the crowd's lines. Anything missing falls back to the prototype wording.
import content from 'virtual:market-content';
import { PLACE_ORDER } from './places.js';

export const SECTIONS = content.sections;
// the writer's order when the build found one, else the market's walking order
export const ORDER = (content.order?.length ? content.order : PLACE_ORDER).filter((id) => SECTIONS[id]);

const strip = (s) => String(s).replace(/<[^>]+>/g, '').replace(/\*\*|__|\*|_|`/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').trim();
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const meta = (id) => SECTIONS[id]?.meta || {};

// Which of the engine's actions a writer's label means.
const KEYS = {
  pour: /pour|mug|cup|glühwein/i,
  prost: /prost|cheers|toast/i,
  pint: /pint|tap|pull(?! a book)/i,
  turn: /turn|flip|grill/i,
  bun: /bun|brötchen|roll/i,
  book: /book|pick/i,
  play: /play|ballad/i,
  sax: /\bsax/i, piano: /piano/i, bass: /\bbass/i, drums: /drum/i, whole: /whole|\ball\b|band$/i,
  ride: /ride|climb|sit|wheel|horse|carousel|top/i,
  bell: /bell|ring/i,
  off: /get off|off|down/i,
};

function writerLabelFor(id, key, taken) {
  const list = meta(id).actions;
  if (!Array.isArray(list)) return null;
  // "Get off" must not be read as a ride, so check the specific keys first
  const order = ['off', 'bell', 'whole', 'sax', 'piano', 'bass', 'drums', 'play', 'prost', 'bun', 'pour', 'pint', 'turn', 'book', 'ride'];
  for (const label of list) {
    if (typeof label !== 'string' || taken.has(label)) continue;
    const k = order.find((kk) => KEYS[kk].test(label));
    if (k === key) return label;
  }
  return null;
}

/**
 * The panel's actions for a place, labelled with the writer's words and in the writer's order.
 * acts: [{ key, label, fn }] with the prototype labels as defaults.
 */
export function panelActions(id, acts) {
  const taken = new Set();
  const out = acts.map((a) => {
    const w = writerLabelFor(id, a.key, taken);
    if (w) taken.add(w);
    return { ...a, label: w || a.label, writer: w };
  });
  const list = Array.isArray(meta(id).actions) ? meta(id).actions : [];
  out.sort((a, b) => (a.writer ? list.indexOf(a.writer) : 99) - (b.writer ? list.indexOf(b.writer) : 99));
  return out;
}

export function actionHint(id, fallback) {
  const h = meta(id).hint;
  return typeof h === 'string' && h.trim() ? esc(h) : fallback;
}

/** The writer's line about clicking the goods themselves (`item_hint:` in the front matter), or the fallback. */
export function itemHint(id, fallback) {
  const h = meta(id).item_hint;
  return typeof h === 'string' && h.trim() ? esc(h) : fallback;
}

/**
 * The note shown after an action. The writer's notes are keyed by action label; a list rotates with {n}.
 * Templates: {n}, {title}, {author}, {note}, {play}. `fallback` is prototype HTML.
 */
export function actionNote(id, key, fallback, vars = {}, { done = false } = {}) {
  const notes = meta(id).notes;
  if (notes && typeof notes === 'object') {
    const labels = Object.keys(notes);
    const pick = labels.find((l) => (done ? /\(done\)/i.test(l) : !/\(done\)/i.test(l)) && (() => {
      const order = ['off', 'bell', 'whole', 'sax', 'piano', 'bass', 'drums', 'play', 'prost', 'bun', 'pour', 'pint', 'turn', 'book', 'ride'];
      return order.find((kk) => KEYS[kk].test(l.replace(/\(done\)/i, ''))) === key;
    })());
    let v = pick !== undefined ? notes[pick] : undefined;
    if (Array.isArray(v)) v = v[(vars.n ?? 0) % v.length];
    if (typeof v === 'string' && v.trim()) {
      let html = esc(v).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? (k === 'n' ? `<b>${esc(vars[k])}</b>` : esc(vars[k])) : ''));
      if (/^\s*$/.test(html)) return fallback;
      return html;
    }
  }
  return fallback;
}

/** Books for "pull a book": [title, author, note], from the Reading front matter or its list. */
export function bookPicks() {
  const m = meta('books').books;
  if (Array.isArray(m) && m.length) {
    const b = m.map((x) => (typeof x === 'string' ? [x, '', ''] : [x.title || '', x.author || '', x.note || x.why || ''])).filter((x) => x[0]);
    if (b.length) return b;
  }
  const items = SECTIONS.books?.items || [];
  const books = items.map((raw) => {
    const s = strip(raw);
    let parts = s.split(/\s+[·•|—–]\s+|\s+-\s+/);
    if (parts.length === 2 && /\.\s/.test(parts[1])) { const i = parts[1].indexOf('. '); parts = [parts[0], parts[1].slice(0, i), parts[1].slice(i + 2)]; }
    if (parts.length < 2) {
      const mm = /^(.+?)\s+by\s+(.+?)(?:[:.]\s+(.*))?$/i.exec(s);
      if (mm) parts = [mm[1], mm[2], mm[3] || ''];
    }
    return [parts[0], parts[1] || '', parts.slice(2).join(' · ')];
  }).filter((b) => b[0] && !/^Mac:/.test(b[0]));
  return books.length ? books : [['A book from the shelf', '', 'Mac will add his reading list here.']];
}

/** What people say when a stall calls "Prost!" (writer's crowd lines, or the prototype's). */
export function toastLines(id) {
  const c = meta(id).crowd;
  if (c && typeof c === 'object') for (const v of Object.values(c)) if (Array.isArray(v) && v.length) return v.map(String);
  return ['Prost!', 'Zum Wohl!', 'ชนแก้ว!', 'Cheers!'];
}

export function crowdLine(id, key, fallback) {
  const c = meta(id).crowd;
  if (c && typeof c === 'object') {
    for (const [label, v] of Object.entries(c)) if (KEYS[key]?.test(label) && Array.isArray(v) && v.length) return String(v[(Math.random() * v.length) | 0]);
  }
  return fallback;
}

/** Background chatter for the crowd's speech bubbles. */
export function phrases() {
  const list = (SECTIONS.phrases?.items || []).map(strip).filter(Boolean);
  return list.length ? list : ['Prost!', 'Zum Wohl!', 'Cheers!', 'What a night.'];
}

export function taglineHtml() {
  const s = SECTIONS.site;
  if (s?.meta?.tagline) return `<p>${esc(s.meta.tagline)}</p>`;
  return s && !s.fromWriter ? s.html : '';
}

export function uiText(key, fallback) {
  const v = SECTIONS.site?.meta?.ui?.[key];
  return typeof v === 'string' && v.trim() ? v : fallback;
}
