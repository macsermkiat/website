// The Bücherstand: click any book and it slides off the shelf, comes to the front of the counter and opens,
// showing its own title, author and a one-line note on its pages (and in the panel). Click it again and it
// closes and goes back to its place. Mac's books (reading.md) are found on the vendor's titled spines; a book of
// his with no printed spine gets a free spine near the middle of the view, wearing a red paper band.
import * as THREE from 'three';
import { boxOf, rest, restore, wrap, esc, UP } from './common.js';
import { viewFor } from '../../engine/market.js';
import inventory from 'virtual:market-inventory';
import { actionNote } from '../../content.js';

const _p = new THREE.Vector3(), _q = new THREE.Quaternion();
const BOOK_HOLD = 14; // seconds an open book stays out before the bookseller puts it back
const MIN_HEIGHT = 0.3; // an open book is shown at least this tall (metres), so its pages can be read

export function createBooks(ctx) {
  const { market, anim, sfx, say, items } = ctx;
  const place = market.places.books;
  const picks = ctx.books || [];
  if (!place) return { api: { featuredBooks: [], openBook: () => null } };
  const nodes = items.of('books', 'book').map((i) => i.node).sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }));
  const itemOf = new Map(items.of('books', 'book').map((i) => [i.node, i]));

  const pickOf = titledSpines(nodes, picks);
  const untitled = picks.map((_, i) => i).filter((i) => ![...pickOf.values()].includes(i));
  const banded = chooseSpines(place, nodes.filter((n) => !pickOf.has(n)), untitled.length);
  banded.forEach((n, k) => { pickOf.set(n, untitled[k]); const b = paperBand(n); if (b) b.name = `band_pick_${untitled[k]}`; });
  const spineFor = picks.map((_, i) => [...pickOf.entries()].filter(([, j]) => j === i).map(([n]) => n).sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }))[0] || null);
  const featured = spineFor.filter(Boolean);
  const where = banded.length ? 'His picks wear a red paper band.' : 'His five stand together in the middle of the lower shelf.';
  let turn = 0;

  /** What a book is: Mac's pick (title, author, note from reading.md) or the vendor's stock (items.json). */
  function describe(n) {
    const i = pickOf.has(n) ? pickOf.get(n) : -1;
    if (i >= 0) { const b = picks[i]; return { mac: true, title: b[0], author: b[1], note: b[2] }; }
    const b = bookInfo(n);
    return { mac: false, title: b?.title || 'A secondhand book', author: b?.author || '', note: b?.note || 'A secondhand copy from the bookseller’s stock, not one of Mac’s.' };
  }

  let open = null; // { n, item, group, left, state }
  function openBook(n) {
    if (!n) return;
    const item = itemOf.get(n);
    if (open?.n === n) { close(); return; }
    if (item?.busy) return;
    if (open) close();
    const d = describe(n);
    sfx('page');
    const text = d.mac
      ? actionNote('books', 'book', `<b>${esc(d.title)}</b>${d.author ? ' · ' + esc(d.author) : ''}${d.note ? '<br>' + esc(d.note) : ''}`, { title: d.title, author: d.author, note: d.note })
      : actionNote('books', 'other', `<b>${esc(d.title)}</b>${d.author ? ' · ' + esc(d.author) : ''}. ${esc(d.note)} <em>${where}</em>`, { title: d.title, author: d.author, note: d.note });
    say(`${text}<br><em>Click the open book to put it back, or another spine to keep browsing.</em>`);
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
    anim.add(0.45, pull, () => {
      if (open !== o) return; // closed while it was coming out
      // 2. the book itself is swapped for a copy that can open, which comes to the front of the counter
      const book = buildOpenBook(n, d, place.holder);
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
        anim.add(0.7, (k) => book.setOpen(k), () => { if (open === o) o.state = 'open'; });
      });
    });
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

  function close() {
    const o = open;
    if (!o) return;
    open = null;
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

  function pickForMe() {
    const i = turn++ % Math.max(1, picks.length);
    const n = spineFor[i] || nodes[(Math.random() * nodes.length) | 0];
    if (n) openBook(n);
    else {
      // no shelf at all (a stand-in without books): the note alone
      const b = picks[i];
      if (b) say(actionNote('books', 'book', `<b>${esc(b[0])}</b>${b[1] ? ' · ' + esc(b[1]) : ''}${b[2] ? '<br>' + esc(b[2]) : ''}`, { title: b[0], author: b[1], note: b[2] }));
    }
  }

  return {
    kinds: { book: (item) => openBook(item.node) },
    api: {
      featuredBooks: featured,
      pickBook: pickForMe,
      openBook: (n) => openBook(n),
      bookOf: (n) => describe(n),
      /** The book standing open (for tests): its node name, title and state. */
      openedBook: () => (open ? { name: open.n.name, title: open.d.title, author: open.d.author, state: open.state } : null),
    },
    retract: close,
    update(dt) {
      if (open?.state === 'open' && (open.left -= dt) <= 0) close();
    },
  };
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
  const group = new THREE.Group();
  group.name = `open_${n.name}`;
  const t = T / 2;
  const half = (side) => {
    const g = new THREE.Group();
    const sx = side; // -1 left, +1 right
    const block = new THREE.Mesh(new THREE.BoxGeometry(W * 0.97, H * 0.96, t * 0.9), PAPER);
    block.position.set(sx * W * 0.485, 0, -t * 0.45);
    const page = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.95, H * 0.94), new THREE.MeshStandardMaterial({ map: sx < 0 ? pages.left : pages.right, roughness: 0.9 }));
    page.position.set(sx * W * 0.485, 0, 0.0008);
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
    group, W, H, T, S,
    get openK() { return openK; },
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
      group.traverse((m) => { if (m.isMesh) { m.geometry.dispose(); if (m.material !== PAPER && m.material !== BOARD && m.material !== cover?.material) m.material.dispose(); } });
      pages.left.dispose(); pages.right.dispose();
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

// What each act_ book is: the vendor's node extras { title, author } (GLTFLoader puts them in userData), else
// the vendor's items.json, keyed by node name (the lite glbs carry no extras, but their books have the same names).
const norm = (t) => String(t || '').toLowerCase().normalize('NFC').replace(/[^\p{L}\p{N}]+/gu, '');
export function bookInfo(n) {
  const u = n.userData || {};
  const it = inventory.items?.[n.name];
  const title = u.title || it?.title;
  if (!title) return null;
  return { title: String(title), author: String(u.author || it?.author || ''), note: it?.note ? String(it.note) : '' };
}

/** Map spine node -> index into `picks` for spines whose printed title is one of Mac's books. */
function titledSpines(nodes, picks) {
  const out = new Map();
  const wanted = picks.map((b) => norm(b[0]));
  for (const n of nodes) {
    const t = norm(bookInfo(n)?.title);
    if (!t) continue;
    // "The Feynman Lectures on Physics, Vol. II" is still the Feynman lectures
    const i = wanted.findIndex((w) => w && (w === t || (w.length > 5 && t.includes(w)) || (t.length > 5 && w.includes(t))));
    if (i >= 0) out.set(n, i);
  }
  return out;
}

/** A book standing on a shelf (not lying on the counter). */
function onShelf(place, n) {
  for (let o = n.parent; o && o !== place.root; o = o.parent) if (/counter/i.test(o.name || '')) return false;
  return true;
}

/**
 * Pick `count` spines for Mac's books: shelf books nearest the middle of the bookshop's view, at least
 * 0.3 m apart, then in order along the shelves (left to right, top shelf first), so the list reads as it stands.
 */
function chooseSpines(place, nodes, count) {
  if (!nodes.length || !count) return [];
  const view = viewFor(place);
  const ray = new THREE.Ray(view.pos, view.target.clone().sub(view.pos).normalize());
  const vendor = place.nodes.slots.slot_vendor?.getWorldPosition(new THREE.Vector3());
  const side = (p) => {
    if (!vendor) return Infinity;
    const a = new THREE.Vector2(vendor.x - view.pos.x, vendor.z - view.pos.z).normalize();
    const b = new THREE.Vector2(p.x - view.pos.x, p.z - view.pos.z);
    return Math.abs(a.x * b.y - a.y * b.x);
  };
  const cands = nodes.filter((n) => onShelf(place, n)).map((n) => ({ n, p: n.getWorldPosition(new THREE.Vector3()) })).filter((c) => side(c.p) > 0.5);
  cands.forEach((c) => { c.d = ray.distanceToPoint(c.p); });
  cands.sort((a, b) => a.d - b.d);
  const chosen = [];
  for (const c of cands) {
    if (chosen.length >= count) break;
    if (chosen.every((o) => o.p.distanceTo(c.p) > 0.3)) chosen.push(c);
  }
  const right = new THREE.Vector3(Math.cos(place.ry), 0, -Math.sin(place.ry));
  chosen.sort((a, b) => (Math.abs(a.p.y - b.p.y) > 0.15 ? b.p.y - a.p.y : a.p.dot(right) - b.p.dot(right)));
  return chosen.map((c) => c.n);
}

const BAND = new THREE.MeshStandardMaterial({ name: 'action_book_band', color: 0xb3342a, roughness: 0.72 });
/** A paper band round the lower part of a book (like a bookshop's belly band), as a child of its pivot. */
function paperBand(pivot) {
  const box = boxOf(pivot, pivot);
  if (box.isEmpty()) return null;
  const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const h = Math.min(0.05, size.y * 0.24);
  const band = new THREE.Mesh(new THREE.BoxGeometry(size.x + 0.004, h, size.z + 0.004), BAND);
  band.position.set(c.x, box.min.y + size.y * 0.4, c.z);
  band.castShadow = false;
  band.userData.itemFx = true;
  pivot.add(band);
  return band;
}
