// Actions at the four section stalls: pour a mug, pull a pint, Prost, turn the sausages,
// a sausage in a bun, and pull a book. They work on the act_ nodes of the real glbs and of the stand-ins.
import * as THREE from 'three';
import { act, acts, counterLocal, toLocal, worldOf, longAxis, findNode, createWorldTag } from './util.js';
import { createEmitter } from './effects.js';
import { viewFor } from '../engine/market.js';
import inventory from 'virtual:market-inventory';
import { actionHint, actionNote, toastLines, crowdLine } from '../content.js';

const MUG = new THREE.MeshStandardMaterial({ name: 'action_mug', color: 0xa3162c, roughness: 0.35 });
const WINE = new THREE.MeshStandardMaterial({ name: 'action_wine', color: 0x4a0612, roughness: 0.1, emissive: 0x1a0205 });
// No transmission: it re-renders the whole scene every frame for one glass. A thin see-through shell reads as glass at this size.
const GLASS = new THREE.MeshStandardMaterial({ name: 'action_glass', color: 0xdfe8ee, roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.28, depthWrite: false, side: THREE.DoubleSide });
const BEER = new THREE.MeshStandardMaterial({ name: 'action_beer', color: 0xe39a1e, roughness: 0.15, emissive: 0x3a1c00, transparent: true, opacity: 0.92 });
const FOAM = new THREE.MeshStandardMaterial({ name: 'action_foam', color: 0xfff5de, roughness: 0.9 });
const mugGeo = new THREE.LatheGeometry([[0.001, 0], [0.07, 0], [0.075, 0.02], [0.075, 0.14], [0.068, 0.145], [0.064, 0.02]].map((p) => new THREE.Vector2(p[0], p[1])), 20);
const handleGeo = new THREE.TorusGeometry(0.04, 0.012, 8, 16, Math.PI);

function newMug() {
  const m = new THREE.Group();
  m.name = 'action_mug';
  m.add(new THREE.Mesh(mugGeo, MUG));
  const h = new THREE.Mesh(handleGeo, MUG);
  h.position.set(0.075, 0.075, 0); h.rotation.z = -Math.PI / 2;
  m.add(h);
  const wine = new THREE.Mesh(new THREE.CircleGeometry(0.064, 20), WINE);
  wine.position.y = 0.13; wine.rotation.x = -Math.PI / 2;
  m.add(wine);
  m.traverse((o) => { o.castShadow = true; });
  return m;
}

export function createStallActions(ctx) {
  const { market, anim, say, sfx, crowdSay, scene, lite } = ctx;
  const bookTag = createWorldTag(ctx.overlay, 'booktag');
  const P = market.places;
  const counts = { mugs: 0, pints: 0, wurst: 0 };
  const emitters = [];

  // ---------- Glühwein ----------
  const glueh = P.glueh;
  let steam = null;
  if (glueh) {
    const pot = act(glueh, 'act_pot') || act(glueh, 'act_pot_lid') || act(glueh, 'act_ladle');
    const c = counterLocal(glueh);
    const src = act(glueh, 'act_steam') || pot;
    const pos = src ? worldOf(glueh, src).add(new THREE.Vector3(0, src === pot ? 0.55 : 0, 0)) : worldOf(glueh, [c.x + 1.3, c.y + 0.55, c.z - 0.05]);
    steam = createEmitter(scene, pos, { color: 0xf2eee8, n: 10, rise: 1.6, spread: 0.25, scale: 0.7, opacity: 0.35 });
    emitters.push(steam);
  }
  const poured = [];
  function pourMug() {
    if (!glueh) return;
    const c = counterLocal(glueh);
    const pot = act(glueh, 'act_pot') || act(glueh, 'act_ladle');
    const lid = act(glueh, 'act_pot_lid');
    const from = pot ? toLocal(glueh, worldOf(glueh, pot)).add(new THREE.Vector3(0, 0.55, 0)) : new THREE.Vector3(c.x + 1.3, c.y + 0.55, c.z - 0.05);
    const slot = counts.mugs % 6;
    const to = new THREE.Vector3(c.x - 1.5 + slot * 0.32, c.y, c.z + 0.14);
    if (poured[slot]) poured[slot].removeFromParent();
    const m = newMug();
    m.position.copy(from);
    glueh.holder.add(m);
    poured[slot] = m;
    anim.add(1.1, (k) => { m.position.lerpVectors(from, to, k); m.position.y += Math.sin(k * Math.PI) * 0.3; });
    if (lid) { const r0 = lid.rotation.x; anim.add(0.5, (k) => { lid.rotation.x = r0 - Math.sin(k * Math.PI) * 0.35; }); }
    if (steam) steam.boost = 1;
    sfx('pour');
    counts.mugs++;
    say(actionNote('glueh', 'pour', `Cups poured tonight: <b>${counts.mugs}</b>. Red wine, cinnamon, clove and orange. Careful, it's hot.`, { n: counts.mugs }));
  }
  function prost(id) {
    sfx('clink');
    const p = P[id];
    const lines = toastLines(id);
    crowdSay(lines[(Math.random() * lines.length) | 0], p ? p.center.clone().setY(0) : new THREE.Vector3(), 12);
    say(actionNote(id, 'prost', 'Everyone nearby raises a glass.'));
  }

  // ---------- Bierstand ----------
  const bier = P.bier;
  let pintBusy = false;
  const pints = [];
  function pullPint() {
    if (!bier || pintBusy) return;
    pintBusy = true;
    const c = counterLocal(bier);
    const taps = acts(bier, 'act_tap');
    const tap = taps[Math.min(1, taps.length - 1)] || null;
    const tapPos = tap ? toLocal(bier, worldOf(bier, tap)) : new THREE.Vector3(c.x + 0.6, c.y + 0.55, c.z - 0.1);
    const grp = new THREE.Group();
    grp.name = 'action_pint';
    grp.position.set(tapPos.x, c.y, tapPos.z);
    bier.holder.add(grp);
    const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.078, 0.062, 0.32, 24, 1, true), GLASS);
    glass.position.y = 0.16;
    grp.add(glass);
    const beer = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.058, 0.3, 24), BEER);
    beer.scale.y = 0.01; beer.position.y = 0.01;
    grp.add(beer);
    const foam = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.06, 24), FOAM);
    foam.visible = false;
    grp.add(foam);
    const r0 = tap ? tap.rotation.x : 0;
    sfx('pour');
    say(actionNote('bier', 'pint', 'Pouring… tilt, fill, then top it off with foam.'));
    anim.add(2.3, (k) => {
      if (tap) tap.rotation.x = r0 + Math.min(1, k * 8, (1 - k) * 8) * 0.55;
      const f = Math.min(1, k / 0.85);
      beer.scale.y = Math.max(0.01, f);
      beer.position.y = 0.01 + 0.15 * f;
      if (k > 0.55) { foam.visible = true; const q = (k - 0.55) / 0.45; foam.scale.y = Math.max(0.05, q); foam.position.y = 0.02 + 0.3 * f + 0.03 * q; }
    }, () => {
      if (tap) tap.rotation.x = r0;
      const slot = counts.pints % 4;
      const to = new THREE.Vector3(c.x - 1.2 + slot * 0.3, c.y, c.z + 0.2), from = grp.position.clone();
      if (pints[slot]) pints[slot].removeFromParent();
      pints[slot] = grp;
      anim.add(0.7, (k) => grp.position.lerpVectors(from, to, k), () => { pintBusy = false; });
      counts.pints++;
      say(actionNote('bier', 'pint', `Pints pulled tonight: <b>${counts.pints}</b>. A Helles, with a proper head of foam.`, { n: counts.pints }, { done: true }));
    });
  }

  // ---------- Bratwurst ----------
  const wurst = P.wurst;
  let smoke = null, grillFlare = 0, grillLight = null, grillMats = [], swing = null;
  const sausageState = [];
  if (wurst) {
    const grill = act(wurst, 'act_grill') || findNode(wurst, /grill|coals|ember/i, { mesh: true });
    // a Schwenkgrill: the grate hangs from a tripod and swings a little
    const sw = act(wurst, 'act_grill_swing');
    if (sw) swing = { node: sw, q0: sw.quaternion.clone(), e: new THREE.Euler(), q: new THREE.Quaternion() };
    const c = counterLocal(wurst);
    const smokeSrc = act(wurst, 'act_smoke') || findNode(wurst, /^smoke/i) || grill;
    const sp = smokeSrc ? worldOf(wurst, smokeSrc).add(new THREE.Vector3(0, smokeSrc === grill ? 0.12 : 0, 0)) : worldOf(wurst, [c.x, c.y + 0.25, c.z - 0.05]);
    smoke = createEmitter(scene, sp, { color: 0xbab4bc, n: 16, rise: 3.2, spread: 0.9, scale: 1.5, opacity: 0.28 });
    emitters.push(smoke);
    if (grill) {
      grill.traverse((o) => {
        if (!o.isMesh) return;
        o.material = o.material.clone();
        o.material.userData.baseEmissive = o.material.emissiveIntensity || 1;
        if (o.material.emissive && o.material.emissive.getHex() === 0) o.material.emissive.set(0xff5a14);
        grillMats.push(o.material);
      });
    }
    if (!lite) {
      grillLight = new THREE.PointLight(0xff5a1a, 4, 5, 2);
      grillLight.name = 'engine_grill_light';
      grillLight.position.copy(toLocal(wurst, sp)).add(new THREE.Vector3(0, 0.2, 0.3));
      wurst.holder.add(grillLight);
    }
    for (const s of acts(wurst, 'act_sausage')) sausageState.push({ node: s, q0: s.quaternion.clone(), y0: s.position.y, axis: longAxis(s), angle: 0 });
  }
  const _q = new THREE.Quaternion();
  function turnSausages() {
    if (!wurst) return;
    sausageState.forEach((s, i) => {
      const a0 = s.angle;
      s.angle += Math.PI;
      anim.add(0.55, (k) => {
        s.node.quaternion.copy(s.q0).multiply(_q.setFromAxisAngle(s.axis, a0 + k * Math.PI));
        s.node.position.y = s.y0 + Math.sin(k * Math.PI) * 0.06;
      }, null, i * 0.07);
    });
    grillFlare = 1.6;
    sfx('sizzle');
    counts.wurst++;
    say(actionNote('wurst', 'turn', ['Turned. Nicely browned on this side.', 'The coals flare up and the smoke drifts over the crowd.', 'Almost ready. Mustard or ketchup?'][(counts.wurst - 1) % 3], { n: counts.wurst - 1 }));
  }
  function bun() {
    sfx('sizzle');
    say(actionNote('wurst', 'bun', 'One Bratwurst im Brötchen with mustard. <em>That will be 4 euros.</em>'));
    if (wurst) crowdSay(crowdLine('wurst', 'bun', 'Smells good!'), wurst.center.clone().setY(0), 9);
  }

  // ---------- Bücherstand ----------
  // Mac's books (reading.md) are on named spines, so clicking a spine gives that book. The vendor printed the
  // five titles on real spines in the middle of the lower shelf and names every book (bookInfo); a book of
  // Mac's with no printed spine gets a free spine near the middle of the view, wearing a red paper band.
  // Every other spine is the bookseller's stock, and says which book it is.
  const booksPlace = P.books;
  const bookNodes = acts(booksPlace, 'act_book_');
  const picks = ctx.books;
  const pickOf = booksPlace ? titledSpines(bookNodes, picks) : new Map();
  const untitled = picks.map((_, i) => i).filter((i) => ![...pickOf.values()].includes(i));
  const banded = booksPlace ? chooseSpines(booksPlace, bookNodes.filter((n) => !pickOf.has(n)), untitled.length) : [];
  banded.forEach((n, k) => { pickOf.set(n, untitled[k]); const b = paperBand(n); if (b) b.name = `band_pick_${untitled[k]}`; });
  // the spine the bookseller pulls for each book (the first volume of a set)
  const spineFor = picks.map((_, i) => [...pickOf.entries()].filter(([, j]) => j === i).map(([n]) => n).sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }))[0] || null);
  const featured = spineFor.filter(Boolean);
  const where = banded.length ? 'His picks wear a red paper band.' : 'His five stand together in the middle of the lower shelf.';
  const bookBase = new Map();
  const bookQ = new Map();
  const busy = new Set();
  let bookIdx = 0;
  let pulled = null; // the book standing out of the shelf: { n, set, left }
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
  function pullBook(node) {
    // the button lets the bookseller choose: Mac's books in turn
    let i, n = node;
    if (node) i = pickOf.has(node) ? pickOf.get(node) : -1;
    else { i = bookIdx++ % picks.length; n = spineFor[i] || (bookNodes.length ? bookNodes[(Math.random() * bookNodes.length) | 0] : null); }
    sfx('page');
    if (i >= 0) {
      const b = picks[i];
      const fallback = `<b>${esc(b[0])}</b>${b[1] ? ' · ' + esc(b[1]) : ''}${b[2] ? '<br>' + esc(b[2]) : ''}`;
      say(`${actionNote('books', 'book', fallback, { title: b[0], author: b[1], note: b[2] })}<br><em>Click another spine to keep browsing.</em>`);
    } else {
      const b = n && bookInfo(n);
      const what = b ? `<b>${esc(b.title)}</b>${b.author ? ' · ' + esc(b.author) : ''}. ` : '';
      say(actionNote('books', 'other', `${what}A secondhand copy from the bookseller’s stock, not one of Mac’s. <em>${where}</em>`, b ? { title: b.title, author: b.author } : {}));
    }
    if (!booksPlace || !n || busy.has(n)) return;
    if (pulled?.n === n) { pulled.left = BOOK_HOLD; return; }
    if (pulled) putBack();
    if (!bookBase.has(n)) bookBase.set(n, n.position.clone());
    const p0 = bookBase.get(n);
    // out toward the front of the stall, in the book's own parent frame
    const holderQ = booksPlace.holder.getWorldQuaternion(new THREE.Quaternion());
    // half out and up, its top tipped toward the customer, the way a bookseller shows a book: from the front
    // a straight pull alone barely changes the picture
    const worldOut = new THREE.Vector3(0, 0.075, 0.17).applyQuaternion(holderQ);
    const parentQ = n.parent.getWorldQuaternion(new THREE.Quaternion()).invert();
    const parentScale = n.parent.getWorldScale(new THREE.Vector3());
    const out = worldOut.applyQuaternion(parentQ).divide(parentScale);
    const tipAxis = new THREE.Vector3(1, 0, 0).applyQuaternion(holderQ).applyQuaternion(parentQ).normalize();
    if (!bookQ.has(n)) bookQ.set(n, n.quaternion.clone());
    const q0 = bookQ.get(n);
    const tip = new THREE.Quaternion();
    busy.add(n);
    booksPlace.merge?.lift(n); // out of the merged shelf mesh while it moves
    const set = (k) => {
      n.position.copy(p0).addScaledVector(out, k);
      n.quaternion.copy(q0).premultiply(tip.setFromAxisAngle(tipAxis, 0.3 * k));
    };
    // The book stays out while it is being read: until the next book is pulled, or BOOK_HOLD seconds of market
    // time (so a paused or slow frame never puts it back before it has been seen; reduced motion keeps it too).
    anim.add(0.45, set, () => { pulled = { n, set, left: BOOK_HOLD }; });
    // a paper tag with its title above the book while it stands out
    const title = i >= 0 ? picks[i][0] : bookInfo(n)?.title;
    if (title) bookTag.show(title, n);
  }
  function putBack() {
    const { n, set } = pulled;
    pulled = null;
    bookTag.hide();
    anim.add(0.45, (k) => set(1 - k), () => { booksPlace.merge?.settle(n); busy.delete(n); });
  }

  return {
    glueh: { hint: actionHint('glueh', 'Pour a cup of Glühwein, then raise it with the crowd.'), acts: [{ key: 'pour', label: 'Pour a cup', fn: pourMug }, { key: 'prost', label: 'Prost!', fn: () => prost('glueh') }] },
    bier: { hint: actionHint('bier', 'Pull a pint from the middle tap.'), acts: [{ key: 'pint', label: 'Pull a pint', fn: pullPint }, { key: 'prost', label: 'Prost!', fn: () => prost('bier') }] },
    wurst: { hint: actionHint('wurst', 'Turn the sausages on the grill.'), acts: [{ key: 'turn', label: 'Turn the sausages', fn: turnSausages }, { key: 'bun', label: 'One in a bun, please', fn: bun }] },
    books: { hint: actionHint('books', 'Click any spine on the shelves, or let the bookseller choose.') + (banded.length ? ' <em>Mac’s picks wear a red paper band.</em>' : ''), acts: [{ key: 'book', label: 'Pick a book for me', fn: () => pullBook(null) }] },
    pullBook,
    /** The spine for each of Mac's books, in reading.md order (for tests and the curious). */
    featuredBooks: featured,
    bookOf: (node) => (pickOf.has(node) ? picks[pickOf.get(node)][0] : null),
    /** The book standing out of the shelf, if any (for tests). */
    pulledBook: () => pulled?.n || null,
    update(dt, t, still) {
      if (pulled && (pulled.left -= dt) <= 0) putBack();
      if (ctx.camera) bookTag.update(ctx.camera);
      grillFlare *= Math.exp(-dt * 1.2);
      if (smoke) smoke.base = 0.28 + grillFlare * 0.1;
      for (const m of grillMats) m.emissiveIntensity = m.userData.baseEmissive * (1 + (still ? 0 : Math.sin(t * 13) * 0.08 + Math.sin(t * 7.1) * 0.06) + grillFlare * 1.2);
      if (grillLight) grillLight.intensity = 4 + (still ? 0 : Math.sin(t * 13) * 0.6 + Math.sin(t * 7.1) * 0.5) + grillFlare * 6;
      emitters.forEach((e) => e.update(dt, still));
      if (swing && !still) {
        const a = Math.sin(t * 1.15) * (0.035 + grillFlare * 0.05);
        swing.e.set(a, 0, Math.sin(t * 0.8 + 1) * 0.02);
        swing.node.quaternion.copy(swing.q0).multiply(swing.q.setFromEuler(swing.e));
      }
    },
  };
}

// What each act_ book is: the vendor's node extras { title, author } (GLTFLoader puts them in userData), else
// the vendor's items.json, keyed by node name (the lite glbs carry no extras, but their books have the same names).
const norm = (t) => String(t || '').toLowerCase().normalize('NFC').replace(/[^\p{L}\p{N}]+/gu, '');
export function bookInfo(n) {
  const u = n.userData || {};
  if (u.title) return { title: String(u.title), author: u.author ? String(u.author) : '' };
  const it = inventory.items?.[n.name];
  return it?.title ? { title: String(it.title), author: it.author ? String(it.author) : '' } : null;
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
  // not behind the bookseller: skip spines within 0.5 m (sideways, as seen from the view) of the vendor's spot
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

const BOOK_HOLD = 9; // seconds a pulled book stands out before the bookseller puts it back

const BAND = new THREE.MeshStandardMaterial({ name: 'action_book_band', color: 0xb3342a, roughness: 0.72 });
/** A paper band round the lower part of a book (like a bookshop's belly band), as a child of its pivot. */
function paperBand(pivot) {
  pivot.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(pivot.matrixWorld).invert();
  const box = new THREE.Box3(), tmp = new THREE.Box3();
  pivot.traverse((m) => {
    if (!m.isMesh) return;
    if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
    box.union(tmp.copy(m.geometry.boundingBox).applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, m.matrixWorld)));
  });
  if (box.isEmpty()) return null;
  const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const h = Math.min(0.05, size.y * 0.24);
  const band = new THREE.Mesh(new THREE.BoxGeometry(size.x + 0.004, h, size.z + 0.004), BAND);
  band.position.set(c.x, box.min.y + size.y * 0.4, c.z);
  band.castShadow = false;
  pivot.add(band);
  return band;
}
