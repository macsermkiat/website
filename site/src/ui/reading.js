// The reading view: a book opened on the Bücherstand shows its page from content/books/<slug>.md (in short,
// summary, key ideas) beside the open book. The page is a small HTML fragment the build emits as
// reading/<slug>.html, fetched only when that book is opened, so the 55 summaries never weigh on the first load.
// Keyboard: focus moves to the book's title, Tab stays inside the view, Escape (or the button) puts the book back
// and returns focus to where it was.
import { LIBRARY } from '../content.js';

const $ = (id) => document.getElementById(id);
const cache = new Map();
const BASE = (import.meta.env?.BASE_URL || '/').replace(/\/?$/, '/');

/** The bookshelf entry for a slug or a title, or null. */
export function libraryBook({ slug, title } = {}) {
  if (slug) { const b = LIBRARY.books.find((x) => x.slug === slug); if (b) return b; }
  const norm = (t) => String(t || '').toLowerCase().normalize('NFC').replace(/[’']/g, '').replace(/[^\p{L}\p{N}]+/gu, '');
  const t = norm(title);
  return t ? LIBRARY.books.find((x) => norm(x.title) === t) || null : null;
}

async function fetchPage(slug) {
  if (cache.has(slug)) return cache.get(slug);
  const p = fetch(`${BASE}reading/${encodeURIComponent(slug)}.html`)
    .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
    .then((html) => (/<h\d|<p/.test(html) ? html : Promise.reject(new Error('not a reading page'))));
  cache.set(slug, p);
  p.catch(() => cache.delete(slug));
  return p;
}

export function createReader() {
  const root = $('reader');
  if (!root) return { open() {}, close() {}, get isOpen() { return false; }, get slug() { return null; } };
  const title = $('rTitle'), author = $('rAuthor'), eyebrow = $('rEyebrow'), body = $('rBody');
  let current = null; // { slug, onClose }
  let returnFocus = null;
  let token = 0;

  function open(book, { onClose, focus = true } = {}) {
    if (!book) return;
    const entry = libraryBook(book) || {};
    const slug = entry.slug || book.slug || '';
    if (current && current.slug !== slug) close({ silent: true });
    if (focus && document.activeElement && !root.contains(document.activeElement)) returnFocus = document.activeElement;
    current = { slug, onClose };
    const t = book.title || entry.title || 'A book';
    eyebrow.textContent = [entry.categoryDe || '', 'from Mac’s shelf'].filter(Boolean).join(' · ');
    title.textContent = t;
    author.textContent = book.author || entry.author || '';
    author.hidden = !author.textContent;
    const oneLine = entry.oneLine || book.note || '';
    body.replaceChildren();
    const lead = document.createElement('p');
    lead.className = 'lead';
    lead.textContent = oneLine || 'Opening the book…';
    body.appendChild(lead);
    root.hidden = false;
    root.dataset.slug = slug;
    root.dataset.state = 'loading';
    if (focus) title.focus({ preventScroll: true });
    const my = ++token;
    if (!slug || entry.page === false) { done(false); return; }
    fetchPage(slug).then((html) => {
      if (my !== token) return;
      body.innerHTML = html;
      body.querySelectorAll('a[href^="http"]').forEach((a) => { a.target = '_blank'; a.rel = 'noopener'; });
      root.dataset.state = 'ready';
    }).catch(() => { if (my === token) done(false); });
    function done(ok) {
      root.dataset.state = ok ? 'ready' : 'short';
      const more = document.createElement('p');
      more.className = 'more';
      const a = document.createElement('a');
      a.href = `plain.html${slug ? `#book-${slug}` : '#books'}`;
      a.textContent = 'Read the notes on this book in the text version';
      more.appendChild(a);
      body.appendChild(more);
    }
  }

  function close({ silent = false } = {}) {
    if (!current) return;
    const was = current;
    current = null;
    token++;
    root.hidden = true;
    delete root.dataset.slug;
    if (!silent) was.onClose?.();
    if (returnFocus && document.contains(returnFocus) && !silent) returnFocus.focus({ preventScroll: true });
    if (!silent) returnFocus = null;
  }

  $('rClose')?.addEventListener('click', () => close());
  root.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (e.key !== 'Tab') return;
    // keep Tab inside the reading view while it is open
    const f = [...root.querySelectorAll('a[href], button:not([disabled]), [tabindex="0"], h2[tabindex]')].filter((el) => !el.hidden && el.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  return {
    open, close,
    get isOpen() { return !!current; },
    get slug() { return current?.slug || null; },
  };
}
