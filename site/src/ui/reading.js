// A book's reading page: content/books/<slug>.md (in short, summary, key ideas) as an HTML fragment the build
// emits as reading/<slug>.html, fetched only when that book is opened, so the 55 summaries never weigh on the
// first load. The words are printed on the open 3D book's pages (actions/items/books.js, world/reader.js).
import { LIBRARY } from '../content.js';

const cache = new Map();
const BASE = (import.meta.env?.BASE_URL || '/').replace(/\/?$/, '/');

/** The bookshelf entry for a slug or a title, or null. */
export function libraryBook({ slug, title } = {}) {
  if (slug) { const b = LIBRARY.books.find((x) => x.slug === slug); if (b) return b; }
  const norm = (t) => String(t || '').toLowerCase().normalize('NFC').replace(/[’']/g, '').replace(/[^\p{L}\p{N}]+/gu, '');
  const t = norm(title);
  return t ? LIBRARY.books.find((x) => norm(x.title) === t) || null : null;
}

/** The reading page of a book on Mac's shelf (HTML fragment), or a rejected promise. */
export function fetchPage(slug) {
  if (!slug) return Promise.reject(new Error('no slug'));
  const b = LIBRARY.books.find((x) => x.slug === slug);
  if (b && b.page === false) return Promise.reject(new Error('no page'));
  if (cache.has(slug)) return cache.get(slug);
  const p = fetch(`${BASE}reading/${encodeURIComponent(slug)}.html`)
    .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
    .then((html) => (/<h\d|<p/.test(html) ? html : Promise.reject(new Error('not a reading page'))));
  cache.set(slug, p);
  p.catch(() => cache.delete(slug));
  return p;
}
