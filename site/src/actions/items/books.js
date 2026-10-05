// The Bücherstand: click any book and it slides off the shelf, comes to the front of the counter and opens, and
// the camera comes to it: its title page on the left, and its page from content/books/<slug>.md (in short,
// summary, key ideas) printed on its pages (world/reader.js). Turning a page turns a leaf. Step back (Escape,
// or the bar's button) and it closes and goes back to its place. Which book a spine is comes from items.json (`slug`, `title`,
// `author`, `category`), which the vendor keeps in line with content/books/categories.json.
import * as THREE from 'three';
import { boxOf, rest, restore, wrap, esc, UP, worldDirToParent } from './common.js';
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
    // the key light was turned to a cabinet: back to the counter, where the book will stand open
    if (openCab) ctx.keyAt?.(null);
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
      anim.add(0.45, (k) => pull(1 - k), () => {
        restore(n, r0);
        // its cabinet was closed while it was out: home to its place in the closed cabinet, not the forward one
        const cab = cabOf.get(n);
        if (cab && !cab.open && n.userData.cabRest) restore(n, n.userData.cabRest);
        if (item) { item.busy = false; item.keepOwn = !!cab?.open; if (!cab?.open) items.settle(item); }
      });
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

  // ---------- the six category cabinets (docs/adr/0004) ----------
  // Picking a book takes two steps. At rest each glazed cabinet is one target (its glass, its books and its sign
  // answer as the cabinet, through an invisible pick proxy round it). A tap on a cabinet moves the camera to its
  // cam_cat_<key> view (fitted to the screen, so on a 390 px phone each cover is still a thumb's width), swings its
  // door (act_cab_<key>) open and brings its face-out covers forward; only that cabinet's books answer the pointer
  // then (never more than 14 targets). Escape or "Step back" closes it. Keys: ↓ / ↑ open a cabinet and move to the
  // next / previous one, ← / → move between its books, Enter opens the book in focus.
  const shelves = LIBRARY.categories.map((c) => ({ key: c.key, label: c.labelDe || c.label, en: c.label })).filter((c) => c.key);
  const under = (n, anc) => { for (let o = n; o; o = o.parent) if (o === anc) return true; return false; };
  /** A category's books: those standing in its cabinet (under slot_cat_<key>), else by their items.json category. */
  function spinesOf(key) {
    const slot = place.nodes.slots[`slot_cat_${key}`];
    const inSlot = slot ? nodes.filter((n) => under(n, slot)) : [];
    return (inSlot.length ? inSlot : nodes.filter((n) => libraryEntry(n)?.category === key)).sort(byPos);
  }
  // top row first, then left to right as the visitor sees it
  function byPos(a, b) {
    const pa = a.getWorldPosition(new THREE.Vector3()), pb = b.getWorldPosition(new THREE.Vector3());
    if (Math.abs(pa.y - pb.y) > 0.08) return pb.y - pa.y;
    const v = viewFor(place).pos;
    const side = (p) => { const d = p.clone().sub(v); return Math.atan2(d.x, -d.z); };
    return side(pa) - side(pb);
  }
  const cabinets = [];
  const cabOf = new Map(); // book node -> cabinet
  for (const c of shelves) {
    const slot = place.nodes.slots[`slot_cat_${c.key}`];
    const door = place.nodes.acts[`act_cab_${c.key}`] || null;
    let sign = null;
    place.root.traverse((o) => { if (!sign && new RegExp(`^sign_cat_${c.key}$`, 'i').test(o.name || '')) sign = o; });
    const books = spinesOf(c.key);
    if (!slot && !door && !books.length) continue;
    const cab = { ...c, slot, door, sign, books, proxy: null, open: false, r0: door ? rest(door) : null, openAngle: 0, pushed: new Map() };
    if (door) {
      door.userData.live = true; // it swings: never merged into the stall
      // the hinge is the door's origin: the door reaches along +X (left hinge, opens by -170°) or -X (right, +170°)
      const bx = boxOf(door, door);
      cab.openAngle = THREE.MathUtils.degToRad(bx.getCenter(new THREE.Vector3()).x >= 0 ? -170 : 170);
    }
    if (sign) sign.userData.live = true;
    for (const n of books) cabOf.set(n, cab);
    cabinets.push(cab);
  }
  // the pick proxies: an invisible box round each cabinet's glass, books and sign, in the cabinet's own frame
  const PROXY_MAT = new THREE.MeshBasicMaterial({ visible: false });
  for (const cab of cabinets) {
    const frame = cab.slot || cab.door;
    if (!frame) continue;
    const box = new THREE.Box3();
    for (const o of [cab.door, cab.sign, ...cab.books].filter(Boolean)) box.union(boxOf(o, frame));
    if (box.isEmpty()) continue;
    box.expandByScalar(0.025);
    const size = box.getSize(new THREE.Vector3()), center = box.getCenter(new THREE.Vector3());
    const m = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), PROXY_MAT);
    m.name = `engine_cabinet_proxy_${cab.key}`;
    m.position.copy(center);
    m.visible = false; // never drawn; the raycaster still meets it
    m.userData.pickProxy = { kind: 'cabinet', key: cab.key, place: 'books', label: `${cab.label}${cab.en && cab.en !== cab.label ? ` · ${cab.en}` : ''}: open the cabinet (${cab.books.length} book${cab.books.length === 1 ? '' : 's'})`, outline: cab.door || cab.sign || null, off: false };
    frame.add(m);
    cab.proxy = m;
  }
  let openCab = null, focusIdx = -1;

  /** The cabinet's view, fitted to the screen: along its cam_cat_<key> sight line, far enough back for its covers. */
  function cabinetView(cab) {
    const box = new THREE.Box3();
    for (const n of cab.books) box.union(boxOf(n));
    const camN = place.nodes.camCats?.[cab.key], tgtN = place.nodes.camCatTargets?.[cab.key];
    const target = tgtN ? tgtN.getWorldPosition(new THREE.Vector3()) : box.isEmpty() ? null : box.getCenter(new THREE.Vector3());
    if (!target) return null;
    const eye = camN ? camN.getWorldPosition(new THREE.Vector3()) : null;
    const center = box.isEmpty() ? target : box.getCenter(new THREE.Vector3());
    // the cabinet's normal (toward the visitor) and its width axis
    let facing = eye ? eye.clone().sub(target) : null;
    if (!facing && cab.slot) facing = new THREE.Vector3(0, 0, 1).applyQuaternion(cab.slot.getWorldQuaternion(new THREE.Quaternion()));
    facing ||= viewFor(place).pos.sub(center);
    const flat = facing.clone().setY(0).normalize();
    const across = new THREE.Vector3(-flat.z, 0, flat.x);
    let halfW = 0.3, halfH = 0.25;
    if (!box.isEmpty()) {
      const c = box.getCenter(new THREE.Vector3());
      halfW = 0; halfH = 0;
      for (const n of cab.books) {
        const b = boxOf(n);
        for (const x of [b.min.x, b.max.x]) for (const y of [b.min.y, b.max.y]) for (const z of [b.min.z, b.max.z]) {
          const d = new THREE.Vector3(x, y, z).sub(c);
          halfW = Math.max(halfW, Math.abs(d.dot(across)));
          halfH = Math.max(halfH, Math.abs(d.y));
        }
      }
    }
    const lift = eye ? (eye.y - target.y) / Math.max(0.2, Math.hypot(eye.x - target.x, eye.z - target.z)) : 0.12;
    return { center, facing: flat, halfW: halfW + 0.03, halfH: halfH + 0.03, lift, margin: 1.12, near: 0.25, eye, target };
  }

  function setProxies() { for (const c of cabinets) if (c.proxy) c.proxy.userData.pickProxy.off = c === openCab; }

  function openCabinet(key, { focus = 0 } = {}) {
    const cab = cabinets.find((c) => c.key === key);
    if (!cab) return false;
    if (open) close();
    if (openCab && openCab !== cab) shutCabinet(openCab);
    openCab = cab;
    setProxies();
    const v = cabinetView(cab);
    if (v) {
      const back = ctx.frame?.({ center: v.center, facing: v.facing, halfW: v.halfW, halfH: v.halfH, lift: v.lift, margin: v.margin, near: v.near });
      if (!back && v.eye) ctx.flyBack?.({ pos: v.eye, target: v.target, near: 0.3, exact: true });
      ctx.keyAt?.(v.center, v.facing);
    }
    if (!cab.open) {
      cab.open = true;
      sfx('page');
      const door = cab.door, r0 = cab.r0, ang = cab.openAngle;
      if (door) { const q = new THREE.Quaternion(); const ax = new THREE.Vector3(0, 1, 0); anim.add(0.8, (k) => door.quaternion.copy(r0.q).multiply(q.setFromAxisAngle(ax, ang * k))); }
      // the covers come forward a little, out of the cabinet toward the visitor
      const out = v?.facing ? v.facing.clone().multiplyScalar(0.045).setY(0.012) : new THREE.Vector3(0, 0.012, 0.045);
      cab.books.forEach((n, i) => {
        const item = itemOf.get(n);
        if (item) { items.release(item); item.keepOwn = true; }
        const r = rest(n);
        cab.pushed.set(n, r);
        n.userData.cabRest = r;
        const d = worldDirToParent(n, out);
        anim.add(0.5, (k) => n.position.copy(r.p).addScaledVector(d, k), null, 0.25 + i * 0.03);
      });
    }
    focusIdx = Math.min(Math.max(0, focus), cab.books.length - 1);
    if (focus < 0) focusIdx = -1;
    showFocus();
    document.documentElement.dataset.cabinet = cab.key;
    const n = cab.books.length;
    say(`<b lang="de">${esc(cab.label)}</b>${cab.en && cab.en !== cab.label ? ` · ${esc(cab.en)}` : ''}: ${n} book${n === 1 ? '' : 's'}. <em>Tap a cover to open it. ← → move between the books, ↑ ↓ between the cabinets, Escape steps back.</em>`);
    return true;
  }

  function shutCabinet(cab, { quick = false } = {}) {
    if (!cab?.open) return;
    cab.open = false;
    const door = cab.door, r0 = cab.r0, ang = cab.openAngle;
    if (door) {
      const q = new THREE.Quaternion(), ax = new THREE.Vector3(0, 1, 0);
      if (quick) door.quaternion.copy(r0.q);
      else anim.add(0.7, (k) => door.quaternion.copy(r0.q).multiply(q.setFromAxisAngle(ax, ang * (1 - k))), () => door.quaternion.copy(r0.q), 0.2);
    }
    for (const [n, r] of cab.pushed) {
      if (open?.n === n) continue; // out on the counter: it comes home by its own way
      const item = itemOf.get(n);
      const p0 = n.position.clone();
      const done = () => { restore(n, r); if (item && !item.busy) { item.keepOwn = false; items.settle(item); } };
      if (quick) done(); else anim.add(0.4, (k) => n.position.lerpVectors(p0, r.p, k), done);
    }
    cab.pushed.clear();
  }

  function closeCabinet({ quick = false } = {}) {
    if (!openCab) return;
    shutCabinet(openCab, { quick });
    openCab = null;
    focusIdx = -1;
    setProxies();
    ctx.highlight?.(null);
    delete document.documentElement.dataset.cabinet;
  }

  function showFocus() {
    const n = openCab && focusIdx >= 0 ? openCab.books[focusIdx] : null;
    ctx.highlight?.(n || null);
    if (n) { const d = describe(n); ctx.announce?.(`${d.title}${d.author ? `, ${d.author}` : ''}. Book ${focusIdx + 1} of ${openCab.books.length}; Enter opens it.`); }
  }

  /** The arrows at the Bücherstand (keyboard.js asks first). Returns true when the key was used. */
  function cabinetKey(key) {
    if (!cabinets.length) return false;
    const i = openCab ? cabinets.indexOf(openCab) : -1;
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      const d = key === 'ArrowDown' ? 1 : -1;
      const next = i < 0 ? (d > 0 ? 0 : cabinets.length - 1) : (i + d + cabinets.length) % cabinets.length;
      openCabinet(cabinets[next].key);
      return true;
    }
    if (!openCab) return false;
    if (key === 'ArrowLeft' || key === 'ArrowRight') {
      const n = openCab.books.length;
      if (!n) return true;
      focusIdx = focusIdx < 0 ? (key === 'ArrowRight' ? 0 : n - 1) : (focusIdx + (key === 'ArrowRight' ? 1 : -1) + n) % n;
      showFocus();
      return true;
    }
    if (key === 'Enter') {
      const n = focusIdx >= 0 ? openCab.books[focusIdx] : openCab.books[0];
      if (n) openBook(n);
      return true;
    }
    return false;
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
      /** The six cabinets (key, German label, English label, number of books). */
      cabinets: () => cabinets.map((c) => ({ key: c.key, label: c.label, en: c.en, books: c.books.length, door: !!c.door, sign: !!c.sign, proxy: !!c.proxy })),
      openCabinet,
      closeCabinet: () => closeCabinet(),
      /** The open cabinet (tests): its key, door angle, its books and which of them the pointer may pick. */
      cabinetState: () => (openCab ? { key: openCab.key, open: openCab.open, focus: focusIdx >= 0 ? openCab.books[focusIdx]?.name : null, books: openCab.books.map((n) => n.name), door: openCab.door ? +(2 * Math.acos(Math.min(1, Math.abs(openCab.door.quaternion.dot(openCab.r0.q))))).toFixed(3) : null } : null),
      /** Where the camera should rest while a cabinet is open (the reading view comes back here). */
      cabinetView: () => { if (!openCab) return null; const v = cabinetView(openCab); return v ? { center: v.center, facing: v.facing, halfW: v.halfW, halfH: v.halfH, lift: v.lift, margin: v.margin, near: v.near } : null; },
      cabinetKey,
      /** The old "look along a shelf" (round 3-7) now opens that cabinet. */
      showShelf: (key) => openCabinet(key),
      shownShelf: () => openCab?.key || null,
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
    retract: () => { close({ retract: true }); closeCabinet(); },
    /** Books in a cabinet answer the pointer only while that cabinet is open; the rest only while none is. */
    pickable(item) {
      if (item.kind !== 'book' || !cabinets.length) return undefined;
      const cab = cabOf.get(item.node);
      return cab ? cab === openCab : !openCab;
    },
    proxyClick(px) {
      if (px.kind !== 'cabinet') return false;
      if (openCab?.key === px.key) return true;
      openCabinet(px.key);
      return true;
    },
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
    const surface = { id: 'books.book', placeId: 'books', kind: 'book', label: 'the open book', faces: book.faces, theme: 'print', base: book.base, rough: false, glow: book.paper ? [book.paper] : [] };
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
