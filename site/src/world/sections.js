// Which words go on which surface (docs/adr/0003, "Text lives in the market"): each section's text, built at
// build time from content/*.md (content.js), cut into the pieces its stall reads them on.
//   piece = { id, placeId, surface (id) | surfaces, title, where, html (the visually hidden copy), faces: { <face>: blocks },
//             sequence?: [face, ...] }
import { SECTIONS } from '../content.js';
import { blocksFromHtml } from './text.js';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const h1 = (text) => ({ kind: 'h', level: 1, runs: [{ text }] });
const p = (text, extra = {}) => ({ kind: 'p', runs: [{ text, ...extra }] });
const sub = (text) => ({ kind: 'sub', runs: [{ text }] });
const textOf = (b) => b.runs.map((r) => r.text).join('').trim();
/** The section's own HTML without the bookshelf list (the shelf itself is that list in the market). */
const bodyHtml = (S) => String(S?.html || '').replace(/<details class="library"[\s\S]*?<\/details>/, '');

/** Group blocks under their h2/h3 headings: { intro, groups: [{ head, blocks }], outro }. */
function byHeading(blocks) {
  const intro = [], groups = [];
  for (const b of blocks) {
    if (b.kind === 'h' && b.level >= 2) groups.push({ head: b, blocks: [] });
    else if (groups.length) groups[groups.length - 1].blocks.push(b);
    else intro.push(b);
  }
  // a last paragraph with a link after the last group's own text reads as the section's closing line
  const outro = [];
  const last = groups[groups.length - 1];
  if (last && last.blocks.length > 2) {
    const tail = last.blocks[last.blocks.length - 1];
    if (tail.kind === 'p' && tail.runs.some((r) => r.href)) outro.push(last.blocks.pop());
  }
  return { intro, groups, outro };
}

export function sectionPieces() {
  const out = {};
  const add = (piece) => { out[piece.id] = piece; };
  const S = SECTIONS;
  const name = (id) => S[id]?.name || id;
  const heading = (id) => S[id]?.title || S[id]?.sub || name(id);
  const copy = (id, extra = '') => `<h2>${esc(heading(id))}</h2><p class="eyebrow">${esc(name(id))} · ${esc(S[id]?.sub || '')}</p>${extra || bodyHtml(S[id])}`;

  // Glühwein (About): the chalkboard behind the counter
  if (S.glueh) add({ id: 'glueh.board', placeId: 'glueh', surface: 'glueh.board', title: heading('glueh'), where: 'the chalkboard at the Glühwein stall', html: copy('glueh'), faces: { main: [h1(heading('glueh')), ...blocksFromHtml(bodyHtml(S.glueh))] } });

  // Bierstand (Projects): one Bierdeckel per project, and the "vom Fass" board listing them like beers on tap
  if (S.bier) {
    const { intro, groups, outro } = byHeading(blocksFromHtml(bodyHtml(S.bier)));
    const projects = groups.map((g, i) => {
      const style = g.blocks.find((b) => b.kind === 'sub');
      const rest = g.blocks.filter((b) => b !== style);
      return { i, name: textOf(g.head), style: style ? textOf(style) : '', front: [h1(textOf(g.head)), ...(style ? [sub(textOf(style))] : [])], back: rest.length ? [{ ...g.head, level: 3 }, ...rest] : [{ ...g.head, level: 3 }, p('More soon.')] };
    });
    const list = projects.map((pr) => ({ kind: 'li', runs: [{ text: pr.name, b: true }, ...(pr.style ? [{ text: ` · ${pr.style}` }] : [])], coaster: pr.i }));
    add({ id: 'bier.vomfass', placeId: 'bier', surface: 'bier.vomfass', title: heading('bier'), where: 'the “vom Fass” board at the Bierstand', html: copy('bier'), faces: { main: [h1(heading('bier')), ...intro, ...list, ...outro] }, projects: projects.map((pr) => pr.name) });
    for (const pr of projects) {
      add({ id: `bier.coaster_${pr.i}`, placeId: 'bier', surface: `bier.coaster_${pr.i}`, title: pr.name, where: 'a Bierdeckel on the Bierstand counter', html: `<h2>${esc(pr.name)}</h2>${pr.style ? `<p><em>${esc(pr.style)}</em></p>` : ''}${groups[pr.i].blocks.filter((b) => b.kind !== 'sub').map(blockHtml).join('')}`, faces: { front: pr.front, back: pr.back }, sequence: ['front', 'back'] });
    }
  }

  // Bratwurst (Writing): the menu board lists the pieces like dishes; a piece is printed on the wrapping paper
  if (S.wurst) {
    const blocks = blocksFromHtml(bodyHtml(S.wurst));
    const dishes = blocks.filter((b) => b.kind === 'li');
    const prose = blocks.filter((b) => b.kind !== 'li');
    const menu = [h1(heading('wurst')), ...(dishes.length ? dishes : [p('Noch nichts vom Grill.', { i: true }), ...prose.slice(0, 1)])];
    add({ id: 'wurst.menu', placeId: 'wurst', surface: 'wurst.menu', title: heading('wurst'), where: 'the menu board at the Bratwurst stall', html: copy('wurst'), faces: { main: menu } });
    add({ id: 'wurst.paper', placeId: 'wurst', surface: 'wurst.paper', title: heading('wurst'), where: 'the wrapping paper on the Bratwurst counter', html: copy('wurst'), faces: { main: [h1(heading('wurst')), ...blocks] } });
  }

  // Bücherstand (Reading): its introduction on a card on the counter (the books themselves open on their own pages)
  if (S.books) add({ id: 'books.card', placeId: 'books', surface: 'books.card', title: heading('books'), where: 'the reading card on the Bücherstand counter', html: copy('books'), faces: { main: [h1(heading('books')), ...blocksFromHtml(bodyHtml(S.books))] } });

  // Bandstand (Music): the programme and notes on the sheet music on the music stand
  if (S.band) add({ id: 'band.sheet', placeId: 'band', surface: 'band.sheet', title: heading('band'), where: 'the sheet music on the bandstand', html: copy('band'), faces: { main: [h1(heading('band')), ...blocksFromHtml(bodyHtml(S.band))] } });

  // Riesenrad (Big questions): the noticeboard by the wheel; each question also hangs on a gondola's placard
  if (S.ferris) {
    const blocks = blocksFromHtml(bodyHtml(S.ferris));
    const questions = blocks.filter((b) => b.kind === 'h' && b.level >= 2).map(textOf);
    add({ id: 'ferris.notice', placeId: 'ferris', surface: 'ferris.notice', title: heading('ferris'), where: 'the noticeboard by the Riesenrad', html: copy('ferris'), faces: { main: [h1(heading('ferris')), ...blocks] }, questions });
  }

  // Karussell (Contact): the ticket in the ticket-booth window
  if (S.carousel) add({ id: 'carousel.ticket', placeId: 'carousel', surface: 'carousel.ticket', title: heading('carousel'), where: 'the ticket in the Karussell’s ticket booth', html: copy('carousel'), faces: { main: [h1(heading('carousel')), ...blocksFromHtml(bodyHtml(S.carousel))] } });
  return out;
}

/** A block back to HTML (the coasters' hidden copy). */
function blockHtml(b) {
  const inner = b.runs.map((r) => {
    let t = esc(r.text);
    if (r.i) t = `<em>${t}</em>`;
    if (r.b) t = `<strong>${t}</strong>`;
    if (r.href) t = `<a href="${esc(r.href)}">${t}</a>`;
    return t;
  }).join('');
  if (b.kind === 'h') return `<h${Math.min(6, (b.level || 2) + 1)}>${inner}</h${Math.min(6, (b.level || 2) + 1)}>`;
  if (b.kind === 'li') return `<ul><li>${inner}</li></ul>`;
  return `<p>${inner}</p>`;
}

/** Blocks for a book's pages: its title page and the reading page from content/books/<slug>.md. */
export function bookBlocks(d, html) {
  const title = [
    { kind: 'h', level: 1, runs: [{ text: d.title || 'A book' }], size: 1.7, align: 'center' },
    ...(d.author ? [{ kind: 'sub', runs: [{ text: d.author }], align: 'center' }] : []),
  ];
  const body = html ? blocksFromHtml(html).filter((b) => !(b.kind === 'p' && b.runs.some((r) => /^Sources?:/i.test(r.text)))) : [];
  const lead = d.note ? [{ kind: 'p', runs: [{ text: d.note, i: true }] }] : [];
  return { title, body: body.length ? body : lead.length ? lead : [p('A secondhand copy from the bookseller’s stock.', { i: true })] };
}
