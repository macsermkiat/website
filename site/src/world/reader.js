// Reading in the market: the camera comes to a writing surface, its words are drawn on it, and long text turns
// pages (a board wipes, a coaster flips, a book's leaf turns) instead of scrolling. There is no text window:
// a small bar of page buttons is the only screen furniture, and a visually hidden copy of the whole text
// (with real links) stays in the page for screen readers and keyboard users.
import * as THREE from 'three';
import { paginate, renderPage, fontsReady, loadText } from './text.js';

const UP = new THREE.Vector3(0, 1, 0);

export function createWorldReader({ camera, rig, motion, sfx = () => {}, els, onOpen, onClose, stopView, announce = () => {} }) {
  const surfaces = new Map(); // id -> surface
  const pieces = new Map(); // id -> piece
  const shown = new Map(); // surface id -> { view, handles: { face: handle }, views }
  const tweens = new Set();
  let current = null; // { piece, surface, view, views, back, held }
  let fontsOk = false, isReady = false, started = null, resolveReady;
  // the faces and troika come after the market's first frame (start()); surfaces are dressed once they are here
  const ready = new Promise((r) => (resolveReady = r));
  function start() {
    if (!started) started = Promise.all([fontsReady(), loadText().catch(() => false)]).then(([ok]) => { fontsOk = ok; isReady = true; resolveReady(); });
    return started;
  }

  function tween(dur, fn, done) {
    const t = { k: 0, dur: motion.reduced ? 0 : dur, fn, done };
    tweens.add(t);
    if (!t.dur) { fn(1); tweens.delete(t); done?.(); }
    return t;
  }

  // ---------- pages ----------
  function viewsOf(piece, surface) {
    if (piece.views) return piece.views; // a book builds its own spreads
    const out = [];
    const order = piece.sequence || Object.keys(piece.faces);
    for (const face of order) {
      const f = surface.faces[face] || surface.faces.main;
      if (!f || !piece.faces[face]) continue;
      const pages = pagesFor(piece.faces[face], f, surface);
      pages.forEach((pg, i) => out.push({ face, page: pg, index: i, of: pages.length }));
    }
    return out.length ? out : [{ face: 'main', page: { lines: [] }, index: 0, of: 1 }];
  }

  /** A face's pages; a surface with a `fit` range gets the largest type in it that puts the words on one page. */
  function pagesFor(blocks, f, surface) {
    const at = (base) => paginate(blocks, { w: f.w, h: f.h, base, theme: surface.theme });
    if (!surface.fit) return at(surface.base);
    const [lo, hi] = surface.fit;
    let pages = at(hi);
    if (pages.length < 2) return pages;
    // bisect between the smallest and largest size (a few measures; each is a canvas measureText per word)
    let a = lo, b = hi, best = at(lo);
    if (best.length > 1) return best;
    for (let k = 0; k < 7; k++) {
      const m = (a + b) / 2;
      const p = at(m);
      if (p.length < 2) { a = m; best = p; } else b = m;
    }
    return best;
  }

  function draw(surface, view, { fade = true } = {}) {
    const st = shown.get(surface.id) || { handles: {} };
    shown.set(surface.id, st);
    const faces = view.faces || { [view.face]: view.page };
    for (const [face, page] of Object.entries(faces)) {
      const f = surface.faces[face] || surface.faces.main;
      if (!f) continue;
      const old = st.handles[face];
      const h = renderPage(page, { theme: surface.theme, glow: surface.theme === 'chalk' ? 0.32 : 0, rough: surface.rough, align: page.align || surface.align || 'left', w: f.w, z: surface.lift });
      h.setOpacity(0);
      f.area.add(h.group);
      st.handles[face] = h;
      for (const l of h.links) l.userData.readable = surface.id;
      h.ready.then(() => {
        h.drawn = true;
        if (st.handles[face] !== h) return;
        tween(fade ? 0.25 : 0, (k) => h.setOpacity(k));
        if (old) tween(fade ? 0.18 : 0, (k) => old.setOpacity(1 - k), () => old.dispose());
      });
      if (!fade && old) old.dispose();
    }
    st.view = view;
  }

  /** Show a piece's first page on its surface (every surface carries its words, read or not). */
  function dress(piece) {
    const surface = surfaces.get(piece.surface);
    if (!surface) return;
    const views = viewsOf(piece, surface);
    piece._views = views;
    // a coaster lies front up; everything else shows its first page
    draw(surface, views[0], { fade: false });
  }

  // ---------- reading ----------
  function open(id, { view = 0, focus = true } = {}) {
    const piece = pieces.get(id);
    const surface = piece && surfaces.get(piece.surface);
    if (!piece || !surface) return false;
    if (!isReady) { start(); ready.then(() => open(id, { view, focus })); return true; }
    if (current && current.piece !== piece) close({ silent: true, keepCamera: true });
    if (!piece._views) dress(piece);
    const views = piece._views;
    const back = current?.back || stopView?.() || rig.rest;
    current = { piece, surface, view: 0, views, back };
    surface.glow.forEach((m) => { m.userData.readBase ??= m.emissiveIntensity; });
    tween(0.5, (k) => surface.glow.forEach((m) => { m.emissiveIntensity = m.userData.readBase * (1 + 5 * k); }));
    if (surface.kind === 'coaster') holdCoaster(surface, true);
    goTo(Math.min(view, views.length - 1), { first: true });
    flyToRead();
    document.documentElement.classList.add('reading');
    syncBar(focus);
    onOpen?.(piece, surface);
    sfx(surface.kind === 'paper' || surface.kind === 'book' ? 'page' : 'chalk');
    return true;
  }

  function flyToRead() {
    const c = current;
    if (!c) return;
    const v = c.views[c.view];
    const face = v.face || (c.surface.kind === 'book' ? 'spread' : 'main');
    const rv = c.piece.readView ? c.piece.readView() : c.surface.readView(face);
    if (!rv) return;
    if (c.surface.kind === 'coaster' || c.surface.kind === 'book') { camera.near = 0.02; camera.updateProjectionMatrix(); }
    rig.flyTo(rv);
  }

  function goTo(i, { first = false } = {}) {
    const c = current;
    if (!c) return;
    i = THREE.MathUtils.clamp(i, 0, c.views.length - 1);
    const prev = c.views[c.view];
    const next = c.views[i];
    const dir = Math.sign(i - c.view);
    c.view = i;
    if (first && i === 0 && shown.get(c.surface.id)?.view === next) { syncBar(false); return; }
    const flip = c.surface.kind === 'coaster' && prev && next && prev.face !== next.face;
    if (flip) {
      flipCoaster(c.surface, next.face === 'back', () => draw(c.surface, next, { fade: false }));
      sfx('card');
    } else if (c.surface.kind === 'book' && c.piece.turn && !first) {
      c.piece.turn(dir, () => draw(c.surface, next, { fade: true }), prev, next);
      sfx('page');
    } else {
      if (!first) sfx(c.surface.theme === 'chalk' ? 'chalk' : 'page');
      draw(c.surface, next, { fade: true });
    }
    syncBar(false);
  }

  function close({ silent = false, keepCamera = false } = {}) {
    const c = current;
    if (!c) return;
    current = null;
    tween(0.4, (k) => c.surface.glow.forEach((m) => { m.emissiveIntensity = m.userData.readBase * (1 + 5 * (1 - k)); }));
    if (c.surface.kind === 'coaster') holdCoaster(c.surface, false);
    // back to the first page, so the surface shows its start to the next visitor
    if (c.view !== 0 && c.piece._views) {
      if (c.surface.kind === 'coaster' && c.views[c.view].face !== 'front') flipCoaster(c.surface, false, () => draw(c.surface, c.views[0], { fade: false }));
      else draw(c.surface, c.piece._views[0], { fade: true });
    }
    camera.near = 0.1;
    camera.updateProjectionMatrix();
    if (!keepCamera && c.back) rig.flyTo(c.back);
    document.documentElement.classList.remove('reading');
    syncBar(false);
    c.piece.onClose?.();
    if (!silent) onClose?.(c.piece);
  }

  // ---------- the coaster: picked up, held to the eye, flipped ----------
  function holdCoaster(s, up) {
    const g = s.root;
    const parent = g.parent;
    const stall = s.holder || parent; // the stall's frame (the hold point is in it)
    if (!s.home) s.home = { p: g.position.clone(), q: g.quaternion.clone() };
    const from = { p: g.position.clone(), q: g.quaternion.clone() };
    let to = s.home;
    if (up) {
      // how the front's writing sits on this coaster (the engine's or the vendor's, whatever its axes)
      g.position.copy(s.home.p); g.quaternion.copy(s.home.q); g.updateMatrixWorld(true);
      const gInv = g.getWorldQuaternion(new THREE.Quaternion()).invert();
      const rel = gInv.clone().multiply(s.faces.front.area.getWorldQuaternion(new THREE.Quaternion()));
      const relB = gInv.clone().multiply((s.faces.back || s.faces.front).area.getWorldQuaternion(new THREE.Quaternion()));
      // the back reads upright after a turn about the vertical when its text runs the same way up as the front's,
      // else after a turn about the horizontal (like a page)
      const upF = new THREE.Vector3(0, 1, 0).applyQuaternion(rel), upB = new THREE.Vector3(0, 1, 0).applyQuaternion(relB);
      // in front of the counter, at a leaning eye's height, the front's writing upright toward the stop's view
      const stop = stopView?.();
      const holdW = stall.localToWorld(new THREE.Vector3(-1.05, 1.36, 1.82));
      const view = stop?.pos || camera.position;
      const Zd = view.clone().sub(holdW); Zd.y *= 0.35; Zd.normalize();
      const Yd = UP.clone().addScaledVector(Zd, -UP.dot(Zd)).normalize();
      const Xd = new THREE.Vector3().crossVectors(Yd, Zd).normalize();
      s.flipAxisW = upF.dot(upB) >= 0 ? UP.clone() : Xd.clone();
      const qArea = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(Xd, Yd, Zd));
      const qG = qArea.multiply(rel.invert());
      const qLocal = parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(qG);
      // the writing's middle at the hold point
      const f = s.faces.front;
      const mid = new THREE.Vector3(f.w / 2, -f.h / 2, 0).applyMatrix4(f.area.matrixWorld);
      const offW = mid.sub(g.getWorldPosition(new THREE.Vector3())).applyQuaternion(gInv.clone().premultiply(qG)); // rotated with the coaster
      const pLocal = parent.worldToLocal(holdW.clone().sub(offW));
      to = { p: pLocal, q: qLocal };
      s.flipQ = new THREE.Quaternion();
    }
    // move it now for the read view's sake, then animate from where it was
    g.position.copy(to.p); g.quaternion.copy(to.q); g.updateMatrixWorld(true);
    const end = { p: to.p.clone(), q: to.q.clone() };
    const lit = s.fromModel ? coasterLight(s) : [];
    tween(0.6, (k) => {
      const e = k * k * (3 - 2 * k);
      lit.forEach((m) => { m.emissiveIntensity = 0.32 * (up ? e : 1 - e); });
      g.position.lerpVectors(from.p, end.p, e);
      g.position.y += Math.sin(e * Math.PI) * 0.05;
      g.quaternion.slerpQuaternions(from.q, end.q, e);
    });
    s.held = up ? end : null;
  }
  /**
   * A model's coaster, held up to read, turns its face from the stall's lamps; it gets a soft light of its own (its
   * own print as emissive) on its own copy of the material. Done at each pick-up: the stream's graft swaps
   * materials when the full model arrives.
   */
  function coasterLight(s) {
    const out = [];
    const skip = new Set();
    s.root.traverse((o) => { if (o.name === 'engine_write_area') o.traverse((c) => skip.add(c)); });
    s.root.traverse((o) => {
      // the coaster's own meshes only: never the words written on it (troika's material is derived, not copied)
      if (!o.isMesh || o.isText || skip.has(o) || !o.material || Array.isArray(o.material)) return;
      if (o.userData.readMat !== o.material) {
        const m = o.material.clone();
        if (m.emissive) { m.emissive.set(0xfff4e6); m.emissiveMap = m.map || null; m.emissiveIntensity = 0; }
        o.material = o.userData.readMat = m;
      }
      if (o.material.emissive) out.push(o.material);
    });
    return out;
  }
  function flipCoaster(s, toBack, mid) {
    const g = s.root;
    if (!s.held) { mid(); return; }
    const base = s.held.q.clone();
    const axisW = (s.flipAxisW || UP).clone();
    const axisL = axisW.clone().applyQuaternion(g.parent.getWorldQuaternion(new THREE.Quaternion()).invert());
    const a0 = toBack ? 0 : Math.PI, a1 = toBack ? Math.PI : 0;
    let swapped = false;
    tween(0.55, (k) => {
      const e = k * k * (3 - 2 * k);
      const q = new THREE.Quaternion().setFromAxisAngle(axisL, a0 + (a1 - a0) * e);
      g.quaternion.copy(q).multiply(base);
      g.position.y = s.held.p.y + Math.sin(e * Math.PI) * 0.02;
      if (!swapped && e > 0.5) { swapped = true; mid(); }
    }, () => { if (!swapped) mid(); });
  }

  // ---------- the bar and the hidden copy ----------
  function syncBar(focus) {
    const c = current;
    const { bar, title, page, prevBtn, nextBtn, copy, flipBtn } = els;
    bar.hidden = !c;
    if (!c) { copy.innerHTML = ''; copy.hidden = true; return; }
    const v = c.views[c.view];
    const n = c.views.length;
    title.textContent = c.piece.title ? `${c.piece.title} · ${c.surface.label}` : c.surface.label;
    page.textContent = n > 1 ? `${c.view + 1} / ${n}` : '';
    page.hidden = n < 2;
    prevBtn.disabled = c.view === 0;
    nextBtn.disabled = c.view >= n - 1;
    prevBtn.hidden = nextBtn.hidden = n < 2;
    const coaster = c.surface.kind === 'coaster';
    if (flipBtn) { flipBtn.hidden = !coaster; flipBtn.textContent = v.face === 'back' ? 'Turn it over: the front' : 'Turn it over'; }
    nextBtn.textContent = coaster && v.face === 'front' ? 'Turn it over ›' : c.surface.kind === 'book' ? 'Turn the page ›' : 'Next page ›';
    prevBtn.textContent = c.surface.kind === 'book' ? '‹ Page back' : '‹ Previous';
    if (copy.dataset.piece !== c.piece.id) {
      copy.innerHTML = c.piece.html || '';
      copy.querySelectorAll('a[href^="http"]').forEach((a) => { a.target = '_blank'; a.rel = 'noopener'; });
      copy.dataset.piece = c.piece.id;
    }
    copy.hidden = false;
    announce(`${c.surface.label}${n > 1 ? `, page ${c.view + 1} of ${n}` : ''}.`);
    if (focus) title.focus({ preventScroll: true });
  }
  els.prevBtn.addEventListener('click', () => goTo((current?.view ?? 0) - 1));
  els.nextBtn.addEventListener('click', () => goTo((current?.view ?? 0) + 1));
  els.closeBtn.addEventListener('click', () => close());
  els.flipBtn?.addEventListener('click', () => {
    const c = current;
    if (!c) return;
    const i = c.views.findIndex((v) => v.face !== c.views[c.view].face);
    if (i >= 0) goTo(i);
  });

  return {
    ready,
    start,
    get started() { return isReady; },
    get fontsOk() { return fontsOk; },
    addSurface(s) { surfaces.set(s.id, s); for (const p of pieces.values()) if (p.surface === s.id && fontsOk !== null) ready.then(() => dress(p)); },
    addPiece(p) { pieces.set(p.id, p); if (surfaces.has(p.surface)) ready.then(() => dress(p)); },
    removePiece(id) { pieces.delete(id); },
    surface: (id) => surfaces.get(id),
    piece: (id) => pieces.get(id),
    pieces: () => [...pieces.values()],
    pieceFor(surfaceId) { for (const p of pieces.values()) if (p.surface === surfaceId) return p; return null; },
    open, close, goTo,
    next: () => goTo((current?.view ?? 0) + 1),
    prev: () => goTo((current?.view ?? 0) - 1),
    /** Re-dress a piece (new content, e.g. a book's page arrived). */
    redress(id) { const p = pieces.get(id); if (!p) return; p._views = null; dress(p); if (current?.piece === p) { current.views = p._views; current.view = Math.min(current.view, current.views.length - 1); syncBar(false); } },
    get isOpen() { return !!current; },
    get current() { return current ? { id: current.piece.id, surface: current.surface.id, view: current.view, views: current.views.length, face: current.views[current.view]?.face || null } : null; },
    /** What is drawn on a surface right now (tests): its lines' text. */
    textOn(surfaceId) {
      const st = shown.get(surfaceId);
      if (!st) return '';
      // only what has finished drawing (its glyphs built), so a test reading it can trust the picture
      return Object.values(st.handles).filter((h) => h.drawn).map((h) => h.texts.map((t) => t.text).join(' ')).join(' | ');
    },
    /** The view a reading camera is moving to again (after a resize). */
    refly: flyToRead,
    update(dt) {
      for (const t of [...tweens]) {
        t.k = Math.min(1, t.k + dt / t.dur);
        t.fn(t.k);
        if (t.k >= 1) { tweens.delete(t); t.done?.(); }
      }
    },
  };
}
