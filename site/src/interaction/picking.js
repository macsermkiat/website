// Hover outline and tooltip, and clicks on stalls, landmarks and single books.
import * as THREE from 'three';

export function createPicking({ dom, camera, market, overlay, outline, labelFor, onPick, onBook }) {
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.hidden = true;
  overlay.appendChild(tip);

  // coarse boxes first, so a pointer move only tests triangles of the place under it
  const boxes = market.hotRoots.map((h) => ({ h, box: new THREE.Box3().setFromObject(h).expandByScalar(0.2) }));
  const books = market.places.books ? Object.entries(market.places.books.nodes.acts).filter(([k]) => k.startsWith('act_book_')).map(([, o]) => o) : [];
  let hover = null, downAt = null, pending = null, enabled = true;

  function setRay(ev) {
    const r = dom.getBoundingClientRect();
    ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    return r;
  }

  function pick(ev) {
    const r = setRay(ev);
    const cands = boxes.filter((b) => ray.ray.intersectsBox(b.box)).map((b) => b.h);
    if (!cands.length) return null;
    const hits = ray.intersectObjects(cands, true);
    for (const h of hits) {
      if (h.object.userData.bulbs && hits.length > 1) continue;
      let o = h.object;
      while (o && !o.userData.place) o = o.parent;
      if (o) return { id: o.userData.place, x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance };
    }
    return null;
  }

  function pickBook(ev) {
    if (!books.length) return null;
    setRay(ev);
    const h = ray.intersectObjects(books, true)[0];
    if (!h || h.distance > 14) return null;
    let o = h.object;
    while (o && !/^act_book_/i.test(o.name)) o = o.parent;
    return o;
  }

  function show(p) {
    hover = p && p.id;
    if (outline) outline.selectedObjects = p ? [market.places[p.id].holder] : [];
    if (p) {
      tip.hidden = false;
      tip.textContent = labelFor(p.id);
      tip.style.left = p.x + 'px';
      tip.style.top = p.y + 'px';
      dom.style.cursor = 'pointer';
    } else {
      tip.hidden = true;
      dom.style.cursor = 'grab';
    }
  }

  dom.addEventListener('pointermove', (e) => {
    if (!enabled || e.pointerType === 'touch') return;
    if (pending) { pending = e; return; }
    pending = e;
    requestAnimationFrame(() => { const ev = pending; pending = null; show(pick(ev)); });
  });
  dom.addEventListener('pointerleave', () => show(null));
  dom.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
  dom.addEventListener('pointerup', (e) => {
    if (!downAt || !enabled) return;
    const moved = Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]);
    downAt = null;
    if (moved > 6) return;
    const book = pickBook(e);
    if (book) return onBook(book);
    const p = pick(e);
    if (p) onPick(p.id);
  });

  return {
    get hover() { return hover; },
    setEnabled(v) { enabled = v; if (!v) show(null); },
    /** Highlight a place without a pointer, for keyboard focus on the place buttons. */
    highlight(id) { if (outline) outline.selectedObjects = id ? [market.places[id].holder] : []; },
  };
}
