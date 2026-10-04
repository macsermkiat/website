// The Bücherstand: click any book and it slides off the shelf, comes to the front of the counter and opens, and
// the camera comes to it: its title page on the left, and its page from content/books/<slug>.md (in short,
// summary, key ideas) printed on its pages (world/reader.js). Turning a page turns a leaf. Step back (Escape,
// or the bar's button) and it closes and goes back to its place. Which book a spine is comes from items.json (`slug`, `title`,
// `author`, `category`), which the vendor keeps in line with content/books/categories.json.
import * as THREE from 'three';
import { boxOf, rest, restore, wrap, esc, UP } from './common.js';
import { viewFor } from '../../engine/market.js';
import inventory from 'virtual:market-inventory';
import { actionNote, LIBRARY } from '../../content.js';
import { libraryBook, fetchPage } from '../../ui/reading.js';
import { paginate } from '../../world/text.js';
import { bookBlocks } from '../../world/sections.js';
import { loadVendorBook, buildVendorBook } from './bookOpen.js';

const _p = new THREE.Vector3(), _q = new THREE.Quaternion();
const BOOK_HOLD = 14; // seconds an open book stays out before the bookseller puts it back (not while it is being read)
const MIN_HEIGHT = 0.3; // an open book is shown at least this tall (metres), so its pages can be read
const byName = (a, b) => a.name.localeCompare(b.name, 'en', { numeric: true });

export function createBooks(ctx) {
  const { market, anim, sfx, say, items } = ctx;
  const world = () => ctx.world?.();
  const place = market.places.books;
  const picks = ctx.books || [];
  const none = { api: { featuredBooks: [], openBook: () => null, openBySlug: (slug) => readOnly(slug) } };
  if (!place) return none;
  const nodes = items.of('books', 'book').map((i) => i.node).sort(byName);
  const itemOf = new Map(items.of('books', 'book').map((i) => [i.node, i]));

  // each of Mac's books once: the spine whose items.json slug (or printed title) is that book
  const spineOf = new Map(); // slug -> node
  for (const n of nodes) {
    const e = libraryEntry(n);
    if (e && !spineOf.has(e.slug)) spineOf.set(e.slug, n);
  }
  // "Pick a book for me": the writer's picks on his shelf first (reading.md), then the rest of the shelf in its order
  const featured = picks.map((b) => libraryBook({ title: b[0] })).filter(Boolean).map((e) => spineOf.get(e.slug)).filter(Boolean);
  const rotation = [...new Set([...featured, ...LIBRARY.books.map((b) => spineOf.get(b.slug)).filter(Boolean), ...nodes])];
  let turn = 0;

  /** What a book is: one of Mac's (the bookshelf entry for its slug, with the writer's summary) or secondhand stock. */
  const standIn = new Map(); // a shelf book standing in for one of Mac's books that has no spine of its own
  function describe(n) {
    const b = bookInfo(n);
    const lib = standIn.has(n) ? libraryBook({ slug: standIn.get(n).slug }) : libraryEntry(n);
    if (lib) return { mac: true, slug: lib.slug, title: lib.title || b?.title, author: lib.author || b?.author || '', note: lib.oneLine || b?.note || 'One of the books on Mac’s own shelf.', category: lib.categoryDe || '' };
    return { mac: false, slug: '', title: b?.title || 'A secondhand book', author: b?.author || '', note: b?.note || 'A secondhand copy from the bookseller’s stock, not one of Mac’s.' };
  }

  // the vendor's open hardback (book_open.glb): fetched once, after the market is up or at the first click
  let vendor = null, vendorP = null;
  const wantVendor = () => (vendorP ||= loadVendorBook({ lite: ctx.lite, warn: ctx.warn }).then((t) => (vendor = t)));
  // (a long first frame can starve idle callbacks: a plain timer; the guide also asks for it on the way here)
  if (typeof window !== 'undefined') setTimeout(() => wantVendor(), 12000);

  let open = null; // { n, item, group, left, state }
  function openBook(n, { focus = true } = {}) {
    if (!n) return;
    const item = itemOf.get(n);
    if (open?.n === n) { close(); return; }
    if (item?.busy) return;
    if (open) close();
    // the key light was turned to a shelf: back to the counter, where the book will stand open
    if (shelfOpen) { shelfOpen = null; ctx.keyAt?.(null); }
    const d = describe(n);
    sfx('page');
    const text = d.mac
      ? actionNote('books', 'book', `<b>${esc(d.title)}</b>${d.author ? ' · ' + esc(d.author) : ''}${d.note ? '<br>' + esc(d.note) : ''}`, { title: d.title, author: d.author, note: d.note })
      : actionNote('books', 'other', `<b>${esc(d.title)}</b>${d.author ? ' · ' + esc(d.author) : ''}. ${esc(d.note)}`, { title: d.title, author: d.author, note: d.note });
    say(`${text}<br><em>Click the open book, or close its page, to put it back.</em>`);
    if (item) { items.release(item); item.busy = true; item.keepOwn = true; }
    const r0 = rest(n);
    // 1. half out of the shelf, its top tipped toward the customer, the way a bookseller takes a book down
    const holderQ = place.holder.getWorldQuaternion(new THREE.Quaternion());
    const parentQ = n.parent.getWorldQuaternion(new THREE.Quaternion()).invert();
    const pscale = n.parent.getWorldScale(new THREE.Vector3());
    const out = new THREE.Vector3(0, 0.075, 0.17).applyQuaternion(holderQ).applyQuaternion(parentQ).divide(pscale);
    const tipAxis = new THREE.Vector3(1, 0, 0).applyQuaternion(holderQ).applyQuaternion(parentQ).normalize();
    const tip = new THREE.Quaternion();
    const pull = (k) => { n.position.copy(r0.p).addScaledVector(out, k); n.quaternion.copy(r0.q).premultiply(tip.setFromAxisAngle(tipAxis, 0.3 * k)); };
    const o = { n, item, d, r0, pull, left: BOOK_HOLD, state: 'pulling', group: null };
    open = o;
    o.focus = focus;
    const tplReady = Promise.race([wantVendor(), new Promise((r) => setTimeout(r, 5000))]);
    anim.add(0.45, pull, () => tplReady.then(() => {
      if (open !== o) return; // closed while it was coming out
      // 2. the book itself is swapped for a copy that can open (the vendor's hardback, with this book's cover;
      // the engine's own when that model is missing), which comes to the front of the counter
      let book = null;
      console.info('[market] opening a book; vendor model', !!vendor);
      if (vendor) { try { book = buildVendorBook(vendor, n, d, place.holder); } catch (e) { console.warn('[market] book_open could not be dressed; the engine\'s own book opens', e); } }
      book ||= buildOpenBook(n, d, place.holder);
      o.group = book;
      if (item) book.group.userData.itemProxy = item; // a click on the open book is a click on that book
      n.visible = false;
      const from = book.poseOf(n);
      const to = presentPose(book);
      book.set(from.p, from.q, 1);
      o.state = 'flying';
      anim.add(0.75, (k) => {
        book.set(_p.lerpVectors(from.p, to.p, k).addScaledVector(UP, Math.sin(k * Math.PI) * 0.12), _q.slerpQuaternions(from.q, to.q, k), THREE.MathUtils.lerp(1, book.S, k));
        book.setClosedOffset(1 - k);
      }, () => {
        if (open !== o) return;
        o.state = 'opening';
        sfx('page');
        // 3. open to the title page
        anim.add(0.7, (k) => book.setOpen(k), () => { if (open === o) { o.state = 'open'; readOpenBook(o); } });
      });
    }));
  }

  /** In front of the middle of the counter, facing the stall's close-up view, leaning back a little. */
  function presentPose(book) {
    const view = viewFor(place);
    const c = place.nodes.slots.slot_counter?.getWorldPosition(new THREE.Vector3()) || place.center.clone().setY(1.05);
    const toView = view.pos.clone().sub(c).setY(0).normalize();
    const p = c.clone().addScaledVector(toView, 0.12);
    p.y = c.y + 0.03 + book.H * book.S * 0.47;
    const look = view.pos.clone();
    look.y = THREE.MathUtils.lerp(p.y, look.y, 0.6); // a lectern's lean, not straight at the eye
    const m = new THREE.Matrix4().lookAt(look, p, UP); // +Z of the book toward the viewer
    return { p, q: new THREE.Quaternion().setFromRotationMatrix(m) };
  }

  function close({ fromReader = false, retract = false } = {}) {
    const o = open;
    if (!o) return;
    open = null;
    // the camera came to the book: back to where it was, unless the visitor has gone elsewhere
    // the camera steps back from the pages (unless the reader already did, or the visitor has gone elsewhere)
    const w = world();
    if (!fromReader && w?.current?.id === 'books.book') w.close({ silent: true, keepCamera: retract });
    const { n, item, r0, pull, group: book } = o;
    const home = () => {
      n.visible = true;
      anim.add(0.45, (k) => pull(1 - k), () => { restore(n, r0); if (item) { item.busy = false; item.keepOwn = false; items.settle(item); } });
    };
    if (!book) { home(); return; } // still sliding out: straight back
    const from = book.world();
    const s0 = from.s;
    const k0 = book.openK;
    anim.add(0.4, (k) => book.setOpen(k0 * (1 - k)), () => {
      const to = book.poseOf(n);
      anim.add(0.6, (k) => {
        book.set(_p.lerpVectors(from.p, to.p, k).addScaledVector(UP, Math.sin(k * Math.PI) * 0.1), _q.slerpQuaternions(from.q, to.q, k), THREE.MathUtils.lerp(s0, 1, k));
        book.setClosedOffset(k);
      }, () => { book.dispose(); home(); });
    });
  }

  // ---------- looking along one category's shelf ----------
  // A cam_cat_<key> empty in the stall (looking at cam_cat_<key>_target, or else at that section's books) frames a
  // section exactly. Without one, the view is worked out from the section's own books: square to the shelf
  // (its long axis is the spread of its spines), from the side the stall's close-up looks from, and far enough
  // back that the section fills the part of the screen the panel leaves free.
  const shelves = LIBRARY.categories.map((c) => ({ key: c.key, label: c.labelDe || c.label, en: c.label })).filter((c) => c.key);
  function spinesOf(key) { return nodes.filter((n) => libraryEntry(n)?.category === key); }
  function shelfView(key) {
    const cam = place.nodes.camCats?.[key];
    const spines = spinesOf(key);
    const box = new THREE.Box3();
    for (const n of spines) box.union(boxOf(n));
    const slot = place.nodes.slots[`slot_cat_${key}`];
    if (box.isEmpty() && slot) box.setFromCenterAndSize(slot.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0.3, 0.12, 0)), new THREE.Vector3(0.6, 0.3, 0.25));
    if (box.isEmpty()) return null;
    const center = box.getCenter(new THREE.Vector3());
    if (cam) {
      const t = place.nodes.camCatTargets?.[key];
      return { pos: cam.getWorldPosition(new THREE.Vector3()), target: t ? t.getWorldPosition(new THREE.Vector3()) : center, near: 0.5, exact: true };
    }
    // the shelf's long axis: the spread of its spines on the ground plane (or the slot's own X for one book)
    let axis = new THREE.Vector3(1, 0, 0);
    if (spines.length > 1) {
      let sxx = 0, szz = 0, sxz = 0;
      const ps = spines.map((n) => n.getWorldPosition(new THREE.Vector3()));
      const m = ps.reduce((a, p) => a.add(p), new THREE.Vector3()).divideScalar(ps.length);
      for (const p of ps) { const x = p.x - m.x, z = p.z - m.z; sxx += x * x; szz += z * z; sxz += x * z; }
      const ang = 0.5 * Math.atan2(2 * sxz, sxx - szz);
      axis.set(Math.cos(ang), 0, Math.sin(ang));
    } else if (slot) axis.set(1, 0, 0).applyQuaternion(slot.getWorldQuaternion(new THREE.Quaternion())).setY(0).normalize();
    const facing = new THREE.Vector3(-axis.z, 0, axis.x);
    const front = viewFor(place).pos.clone().sub(center).setY(0);
    if (facing.dot(front) < 0) facing.negate();
    const size = box.getSize(new THREE.Vector3());
    const halfW = (Math.abs(axis.x) * size.x + Math.abs(axis.z) * size.z) / 2 + 0.08;
    return { center, facing, halfW, halfH: size.y / 2 + 0.08, depth: Math.abs(facing.x) * size.x + Math.abs(facing.z) * size.z };
  }
  let shelfOpen = null;
  function showShelf(key) {
    const v = shelfView(key);
    if (!v) return false;
    shelfOpen = key;
    if (v.exact) ctx.flyBack?.(v);
    else ctx.frame?.({ ...v, lift: 0.3, margin: 1.3, near: 0.5 });
    // the lite market's close-up key light turns to the shelf (the full market's own lights reach it)
    if (v.center) ctx.keyAt?.(v.center, v.facing || v.pos.clone().sub(v.target));
    const c = shelves.find((x) => x.key === key);
    const n = spinesOf(key).length;
    say(`<b lang="de">${esc(c?.label || key)}</b>${c?.en && c.en !== c.label ? ` · ${esc(c.en)}` : ''}: ${n} book${n === 1 ? '' : 's'} on this shelf. <em>Click a spine to open it.</em>`);
    return true;
  }

  function pickForMe() {
    const n = rotation.length ? rotation[turn++ % rotation.length] : null;
    if (n) { openBook(n); return; }
    // no shelf at all (a stand-in without books): the reading view alone
    const b = LIBRARY.books[turn++ % Math.max(1, LIBRARY.books.length)];
    if (b) readOnly(b.slug);
  }

  /** A link in the bookshelf list: open that book on its shelf, or only its page when it has no spine. */
  function openBySlug(slug, opts) {
    const n = spineOf.get(slug);
    if (n) { if (open?.n !== n) openBook(n, opts); return true; }
    return readOnly(slug);
  }

  return {
    kinds: { book: (item) => openBook(item.node) },
    api: {
      featuredBooks: featured,
      /** The category shelves (key, German label) and a view along one of them. */
      shelves: () => shelves.filter((c) => spinesOf(c.key).length || place.nodes.slots[`slot_cat_${c.key}`]),
      showShelf,
      shelfView: (key) => { const v = shelfView(key); return v && { exact: !!v.exact, center: v.center?.toArray?.(), halfW: v.halfW, halfH: v.halfH }; },
      shownShelf: () => shelfOpen,
      pickBook: pickForMe,
      openBook: (n) => openBook(n),
      openBySlug,
      /** Fetch the vendor's open hardback ahead of a click (the stroll calls this on the way to the Bücherstand). */
      prefetchBook: () => wantVendor(),
      bookOf: (n) => describe(n),
      /** Mac's books with a spine (tests): slug -> node name. */
      macSpines: () => Object.fromEntries([...spineOf].map(([k, n]) => [k, n.name])),
      /** The book standing open (for tests): its node name, title and state. */
      openedBook: () => (open ? { name: open.n.name, slug: open.d.slug, title: open.d.title, author: open.d.author, note: open.d.note, mac: !!open.d.mac, state: open.state, model: open.group?.fromModel ? 'book_open.glb' : open.group ? 'engine' : null } : null),
    },
    retract: () => { shelfOpen = null; close({ retract: true }); },
    update(dt) {
      if (open?.state === 'open' && world()?.current?.id !== 'books.book' && (open.left -= dt) <= 0) close();
    },
  };

  function readOnly(slug) {
    const b = LIBRARY.books.find((x) => x.slug === slug);
    if (!b) return false;
    // no spine for it on the shelf: the bookseller hands over a copy anyway (the nearest shelf book stands in)
    const n = nodes.find((x) => !libraryEntry(x)) || nodes[0];
    if (!n) return false;
    spineOf.set(slug, n);
    standIn.set(n, b);
    openBook(n);
    return true;
  }

  /** The open book's pages in the market: title page, then the book's reading page, spread by spread. */
  function readOpenBook(o) {
    const w = world();
    const book = o.group;
    if (!w || !book) return;
    // the pages are measured in the faces the text is drawn with: wait for them if they are still on their way
    if (w.started === false) { w.start(); w.ready.then(() => { if (open === o) readOpenBook(o); }); return; }
    const surface = { id: 'books.book', placeId: 'books', kind: 'book', label: 'the open book', faces: book.faces, theme: 'print', base: book.base, rough: false, glow: [book.paper] };
    const piece = { id: 'books.book', placeId: 'books', surface: 'books.book', title: o.d.title, where: 'an open book at the Bücherstand', html: bookCopy(o.d, null), views: spreads(o.d, null, book), readView: () => book.readView(ctx.camera), turn: (dir, mid, from, to) => book.turn(dir, mid, anim, from, to), onClose: () => { if (open === o) close({ fromReader: true }); } };
    w.addSurface(surface);
    w.addPiece(piece);
    w.open('books.book', { focus: o.focus !== false });
    if (!o.d.slug) return;
    fetchPage(o.d.slug).then((html) => {
      if (open !== o) return;
      piece.html = bookCopy(o.d, html);
      piece.views = spreads(o.d, html, book);
      w.redress('books.book');
    }).catch(() => {});
  }
}

// ---------- the words on the open book ----------

/** Spreads for the reader: the title page on the left of the first, then the reading page, page after page. */
function spreads(d, html, book) {
  const { title, body } = bookBlocks(d, html);
  const L = book.faces.left, R = book.faces.right;
  const tp = paginate(title, { w: L.w, h: L.h, base: book.base, theme: 'print' })[0];
  // the title stands a third of the way down, centred
  const drop = Math.max(0, (L.h - tp.used) * 0.36);
  tp.lines.forEach((l) => { l.y += drop; });
  tp.align = 'center';
  // a little imprint at the foot of the title page
  const foot = paginate([{ kind: 'sub', runs: [{ text: d.mac ? 'from Mac’s shelf' : 'Antiquariat · Nachtmarkt' }] }], { w: L.w, h: L.h, base: book.base * 0.85, theme: 'print' })[0];
  foot.lines.forEach((l) => { l.y = L.h - l.height; tp.lines.push(l); });
  const pages = paginate(body, { w: R.w, h: R.h, base: book.base, theme: 'print' });
  const views = [{ faces: { left: tp, right: pages[0] || { lines: [] } } }];
  for (let i = 1; i < pages.length; i += 2) views.push({ faces: { left: pages[i], right: pages[i + 1] || { lines: [] } } });
  return views;
}

const escHtml = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
/** The visually hidden copy of an open book: its title, author and reading page. */
function bookCopy(d, html) {
  const more = d.slug ? `<p><a href="plain.html#book-${escHtml(d.slug)}">This book in the text version</a></p>` : '';
  return `<h2><em>${escHtml(d.title)}</em></h2>${d.author ? `<p>${escHtml(d.author)}</p>` : ''}${html || (d.note ? `<p>${escHtml(d.note)}</p>` : '')}${more}`;
}

// ---------- the book that opens ----------

const PAPER = new THREE.MeshStandardMaterial({ name: 'item_book_paper', color: 0xefe6d0, roughness: 0.92 });
const BOARD = new THREE.MeshStandardMaterial({ name: 'item_book_board', color: 0x5a2a20, roughness: 0.7 });

/**
 * A copy of a book that can open: two halves hinged at the spine, the pages printed with its title, author and
 * note. Local frame: X across the cover, Y up the spine, Z out of the front cover. Closed, it spans x 0..W.
 */
function buildOpenBook(n, d, frame) {
  const box = boxOf(n, n);
  const size = box.getSize(new THREE.Vector3());
  // the book's own axes: the longest is its height, the shortest its thickness
  const axes = [['x', size.x], ['y', size.y], ['z', size.z]].sort((a, b) => a[1] - b[1]);
  const T = Math.max(0.012, axes[0][1]), W = Math.max(0.08, axes[1][1]), H = Math.max(0.1, axes[2][1]);
  const S = Math.max(1, MIN_HEIGHT / H);
  const cover = coverMaterial(n);
  const pages = pageTextures(d, W / H);
  const faces = {};
  const group = new THREE.Group();
  group.name = `open_${n.name}`;
  const t = T / 2;
  const half = (side) => {
    const g = new THREE.Group();
    const sx = side; // -1 left, +1 right
    const block = new THREE.Mesh(new THREE.BoxGeometry(W * 0.97, H * 0.96, t * 0.9), PAPER);
    block.position.set(sx * W * 0.485, 0, -t * 0.45);
    const page = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.95, H * 0.94), new THREE.MeshStandardMaterial({ map: sx < 0 ? pages.left : pages.right, roughness: 0.9, emissive: 0xfff2dc, emissiveIntensity: 0.06 }));
    page.position.set(sx * W * 0.485, 0, 0.0008);
    // the writing area: the page less its margins (wider at the outer edge and the foot)
    const aw = W * 0.95 * 0.8, ah = H * 0.94 * 0.84;
    const area = new THREE.Object3D();
    area.name = 'engine_write_area';
    area.position.set(-aw / 2 + sx * W * 0.01, ah / 2 + H * 0.01, 0.0006);
    page.add(area);
    faces[sx < 0 ? 'left' : 'right'] = { area, w: aw, h: ah };
    const board = new THREE.Mesh(new THREE.BoxGeometry(W, H, 0.003), BOARD);
    board.position.set(sx * W / 2, 0, -t - 0.0015);
    g.add(block, page, board);
    if (sx < 0 && cover) {
      // the front cover: the vendor's own cover art, on the outside of the left board
      const face = new THREE.Mesh(coverGeometry(W, H, cover.uv), cover.material);
      face.position.set(-W / 2, 0, -t - 0.0032);
      face.rotation.y = Math.PI;
      g.add(face);
    }
    g.traverse((m) => { if (m.isMesh) { m.castShadow = true; m.userData.itemFx = true; } });
    return g;
  };
  const left = half(-1), right = half(1);
  const spine = new THREE.Group();
  spine.add(left, right);
  group.add(spine);
  // the leaf that turns: hinged at the spine, as wide as a page
  const leafMat = new THREE.MeshStandardMaterial({ map: pages.right, roughness: 0.9, side: THREE.DoubleSide, emissive: 0xfff2dc, emissiveIntensity: 0.06 });
  const leafGeo = new THREE.PlaneGeometry(W * 0.95, H * 0.94, 8, 1);
  leafGeo.translate(W * 0.485, 0, 0);
  const leaf = new THREE.Mesh(leafGeo, leafMat);
  leaf.visible = false;
  leaf.userData.itemFx = true;
  spine.add(leaf);
  // the whole spread, for the reading camera
  const spread = new THREE.Object3D();
  spread.position.set(-W * 0.97, H * 0.47, 0.002);
  group.add(spread);
  // open: 0 closed (the left half folded over the right, front cover out) .. 1 open flat with a slight V
  let openK = 0;
  const setOpen = (k) => {
    openK = k;
    left.rotation.y = -Math.PI + k * (Math.PI - 0.16);
    right.rotation.y = -0.16 * k;
  };
  setOpen(0);
  // while closed and flying, the book's centre (x = W/2) is where the shelf book's centre was
  const setClosedOffset = (k) => { spine.position.x = -(W / 2) * k; };
  setClosedOffset(1);
  // the shelf book's pose, in this frame: its axes (width, height, thickness) onto X, Y, Z
  const basis = (() => {
    const v = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
    const X = v[axes[1][0]].clone(), Y = v[axes[2][0]].clone();
    const Z = new THREE.Vector3().crossVectors(X, Y);
    return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(X, Y, Z));
  })();
  // it lives in the stall's frame (so the pointer finds it with the stall); poses are given in the world
  frame.add(group);
  frame.updateWorldMatrix(true, false);
  const fInv = frame.matrixWorld.clone().invert();
  const fQ = frame.getWorldQuaternion(new THREE.Quaternion());
  const fQi = fQ.clone().invert();
  const fS = frame.getWorldScale(new THREE.Vector3()).x || 1;
  let world = { p: new THREE.Vector3(), q: new THREE.Quaternion(), s: 1 };
  return {
    group, W, H, T, S, faces, paper: PAPER,
    base: H * 0.94 * 0.84 / 21, // about 16 lines of body text to a page
    get openK() { return openK; },
    /** The reading view of the open spread. */
    readView(camera) {
      group.updateWorldMatrix(true, true);
      const c = new THREE.Vector3(W * 0.97, -H * 0.47, 0).applyMatrix4(spread.matrixWorld);
      const n = new THREE.Vector3(0, 0, 1).transformDirection(group.matrixWorld).normalize();
      const s = new THREE.Vector3().setFromMatrixScale(group.matrixWorld).x || 1;
      const t = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      const d = Math.max((H * 0.94 * s) / (2 * t * 0.86), (W * 1.94 * s) / (2 * t * camera.aspect * 0.86));
      const dir = n.clone(); dir.y += 0.12; dir.normalize();
      return { pos: c.clone().addScaledVector(dir, d), target: c, near: 0.05 };
    },
    /** Turn a leaf: forward (dir > 0) from the right page over to the left, or back. mid() swaps the words. */
    turn(dir, mid, anim) {
      const a0 = dir > 0 ? right.rotation.y : left.rotation.y - Math.PI + 0.02;
      const a1 = dir > 0 ? left.rotation.y - Math.PI + 0.02 : right.rotation.y;
      leaf.visible = true;
      leaf.position.z = 0.001;
      let swapped = false;
      anim.add(0.7, (k) => {
        const e = k * k * (3 - 2 * k);
        leaf.rotation.y = a0 + (a1 - a0) * e;
        leaf.position.z = 0.001 + Math.sin(e * Math.PI) * W * 0.05;
        if (!swapped && e > 0.35) { swapped = true; mid(); }
      }, () => { leaf.visible = false; if (!swapped) mid(); });
    },
    /** Place it in world terms: position, rotation and uniform scale. */
    set(p, q, s) {
      world = { p: p.clone(), q: q.clone(), s };
      group.position.copy(p).applyMatrix4(fInv);
      group.quaternion.copy(fQi).multiply(q);
      group.scale.setScalar(s / fS);
    },
    world: () => ({ p: world.p.clone(), q: world.q.clone(), s: world.s }),
    setOpen, setClosedOffset,
    poseOf(node) {
      node.updateWorldMatrix(true, false);
      const c = box.getCenter(new THREE.Vector3()).applyMatrix4(node.matrixWorld);
      const q = node.getWorldQuaternion(new THREE.Quaternion()).multiply(basis);
      return { p: c, q };
    },
    dispose() {
      group.removeFromParent();
      group.traverse((m) => { if (m.isMesh && !m.isText) { m.geometry.dispose(); if (m.material !== PAPER && m.material !== BOARD && m.material !== cover?.material) m.material.dispose(); } });
      leafGeo.dispose(); leafMat.dispose();
      if (!pages.shared) { pages.left.dispose(); pages.right.dispose(); }
    },
  };
}

/** The book's cover: its mesh's material (the vendor's cover atlas) and its rect in items.json. */
function coverMaterial(n) {
  const it = inventory.items?.[n.name];
  let mat = null;
  n.traverse((o) => { if (!mat && o.isMesh && o.material?.map) mat = o.material; });
  if (!mat) return null;
  const uv = Array.isArray(it?.cover_uv) && it.cover_uv.length === 4 ? it.cover_uv.map(Number) : null;
  return uv ? { material: mat, uv } : null;
}

function coverGeometry(W, H, [u0, v0, u1, v1]) {
  const g = new THREE.PlaneGeometry(W, H);
  const uv = g.attributes.uv;
  // PlaneGeometry: vertices top-left, top-right, bottom-left, bottom-right; glTF UVs have v down from the top
  uv.setXY(0, u0, v0); uv.setXY(1, u1, v0); uv.setXY(2, u0, v1); uv.setXY(3, u1, v1);
  uv.needsUpdate = true;
  return g;
}

/** The title page (left) and the note (right), drawn on canvases in the site's type. */
function pageTextures(d, aspect) {
  const w = 512, h = Math.round(512 / Math.max(0.45, Math.min(1, aspect)));
  const mk = (draw) => {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d');
    g.fillStyle = '#f1e8d3'; g.fillRect(0, 0, w, h);
    // a little foxing and the gutter shadow
    const gr = g.createLinearGradient(0, 0, w, 0);
    gr.addColorStop(0, 'rgba(90,60,30,0.10)'); gr.addColorStop(0.12, 'rgba(90,60,30,0)'); gr.addColorStop(0.88, 'rgba(90,60,30,0)'); gr.addColorStop(1, 'rgba(90,60,30,0.10)');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.fillStyle = '#2b1f16'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    draw(g);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  };
  // the words are drawn in 3D on these pages (world/reader.js); the canvas is the paper only
  if (pageTextures.blank) return pageTextures.blank;
  const blankPaper = mk(() => {});
  pageTextures.blank = { left: blankPaper, right: blankPaper, shared: true };
  return pageTextures.blank;
  // eslint-disable-next-line no-unreachable
  const left = mk((g) => {
    let size = 58;
    g.font = `700 ${size}px 'Alegreya SC', Georgia, serif`;
    let lines = wrap(g, d.title, w * 0.78);
    while (lines.length > 3 && size > 30) { size -= 6; g.font = `700 ${size}px 'Alegreya SC', Georgia, serif`; lines = wrap(g, d.title, w * 0.78); }
    const y0 = h * 0.34 - ((lines.length - 1) * size * 1.1) / 2;
    lines.forEach((l, i) => g.fillText(l, w / 2, y0 + i * size * 1.1));
    g.fillStyle = '#8a2a20';
    g.fillRect(w * 0.42, y0 + lines.length * size * 1.1 - size * 0.4, w * 0.16, 3);
    if (d.author) {
      g.fillStyle = '#3a2a1c';
      g.font = `italic 500 34px 'Alegreya Sans', Georgia, serif`;
      g.fillText(d.author, w / 2, y0 + lines.length * size * 1.1 + 40);
    }
    g.font = `500 22px 'Alegreya Sans', Georgia, serif`;
    g.fillStyle = '#6b5a48';
    g.fillText(d.mac ? 'from Mac’s shelf' : 'Antiquariat · Nachtmarkt', w / 2, h * 0.9);
  });
  const right = mk((g) => {
    g.textAlign = 'left';
    g.font = `italic 400 30px 'Alegreya Sans', Georgia, serif`;
    const lines = wrap(g, d.note || '', w * 0.74);
    const lh = 40;
    const y0 = Math.max(h * 0.2, h * 0.45 - (lines.length * lh) / 2);
    lines.slice(0, 12).forEach((l, i) => g.fillText(l, w * 0.13, y0 + i * lh));
    g.textAlign = 'center';
    g.font = `500 22px 'Alegreya Sans', Georgia, serif`;
    g.fillStyle = '#6b5a48';
    g.fillText('— i —', w / 2, h * 0.93);
  });
  return { left, right };
}

// ---------- which spine is which ----------

// What each act_ book is: the vendor's items.json entry, keyed by node name (title, author, slug, category), else
// the node's own glTF extras (GLTFLoader puts them in userData).
export function bookInfo(n) {
  const u = n.userData || {};
  const it = inventory.items?.[n.name];
  const title = it?.title || it?.name || u.title;
  if (!title) return null;
  return { title: String(title), author: String(it?.author || u.author || ''), slug: String(it?.slug || u.slug || ''), note: it?.note ? String(it.note) : '' };
}

/** The bookshelf entry (content/books/categories.json) for a spine: by its slug, else by its exact title. */
export function libraryEntry(n) {
  const b = bookInfo(n);
  if (!b) return null;
  return libraryBook({ slug: b.slug, title: b.title });
}
