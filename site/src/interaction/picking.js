// Hover outline and tooltip, and clicks (or taps) on stalls, landmarks, deco stalls and the single items on
// their counters and shelves. One raycast per pointer move: the first thing under the pointer decides, so a
// roof post in front of a book still hides it.
import * as THREE from 'three';

// Items answer the pointer only from close by (the stall's close-up, or a visitor who zoomed in); from
// further away the pointer means the whole stall.
export const ITEM_RANGE = 11;

export function createPicking({ dom, camera, market, overlay, outline, items, labelFor, onPick, onItem, onDeco, current = () => null }) {
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.hidden = true;
  overlay.appendChild(tip);

  // coarse boxes first, so a pointer move only tests triangles of the place under it
  let boxes = [];
  const refresh = () => {
    const roots = [...market.hotRoots, ...(market.decoRoots || [])];
    boxes = roots.map((h) => ({ h, box: new THREE.Box3().setFromObject(h).expandByScalar(0.2) }));
  };
  refresh();
  let hover = null, downAt = null, pending = null, enabled = true;

  function setRay(ev) {
    const r = dom.getBoundingClientRect();
    ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    return r;
  }

  /** What is under the pointer: { id (place) | deco (entry id), item?, x, y, distance } or null. */
  function pick(ev) {
    const r = setRay(ev);
    const cands = boxes.filter((b) => ray.ray.intersectsBox(b.box)).map((b) => b.h);
    if (!cands.length) return null;
    const hits = ray.intersectObjects(cands, true);
    for (const h of hits) {
      const o0 = h.object;
      if (o0.userData.bulbs && hits.length > 1) continue;
      if (o0.userData.merged) continue; // the merged shelf mesh: the items' own (hidden) meshes answer for it
      if (o0.isSprite || o0.userData.itemFx === true && !items?.itemOf(o0)) continue;
      let o = o0;
      while (o && !o.userData.place && !o.userData.entry) o = o.parent;
      if (!o) continue;
      const base = { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance };
      const item = items?.itemOf(o0);
      const place = o.userData.place || null;
      const near = h.distance < ITEM_RANGE || (place && current() === place);
      if (item && near) return { ...base, id: place, deco: place ? null : o.userData.entry?.id, item };
      if (place) return { ...base, id: place };
      if (o.userData.entry?.kind === 'deco') return { ...base, deco: o.userData.entry.id, label: o.userData.entry.label };
      return null;
    }
    return null;
  }

  function show(p) {
    hover = p?.id || null;
    items?.hover(p?.item || null);
    if (outline) {
      const target = p?.item ? p.item.node : p?.id ? market.places[p.id]?.holder : p?.deco ? (market.decoRoots || []).find((h) => h.userData.entry?.id === p.deco) : null;
      outline.selectedObjects = target ? [target] : [];
    }
    if (p) {
      tip.hidden = false;
      tip.textContent = p.item ? p.item.label : p.id ? labelFor(p.id) : p.label || '';
      tip.classList.toggle('item', !!p.item);
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
    // a finger wobbles more than a mouse: a tap may move a little further and still count
    if (moved > (e.pointerType === 'touch' ? 12 : 6)) return;
    const p = pick(e);
    if (!p) return;
    if (p.item) {
      // on a touch screen there is no hover: the tap lifts the item and shows its name for a moment
      if (e.pointerType === 'touch') { show(p); clearTimeout(tapTimer); tapTimer = setTimeout(() => show(null), 1400); }
      onItem(p.item, p);
      return;
    }
    if (p.id) onPick(p.id);
    else if (p.deco) onDeco?.(p.deco);
  });
  let tapTimer = 0;

  return {
    get hover() { return hover; },
    /** Places added after the market opened (the rides and deco stalls). */
    refresh,
    /** The item a click at client (x, y) would reach, or null (tests aim clicks with it). */
    itemAt: (x, y) => pick({ clientX: x, clientY: y })?.item?.node.name || null,
    /** What a click at client (x, y) would reach (tests). */
    at: (x, y) => { const p = pick({ clientX: x, clientY: y }); return p ? { id: p.id || null, deco: p.deco || null, item: p.item?.node.name || null } : null; },
    setEnabled(v) { enabled = v; if (!v) show(null); },
    /** Highlight a place without a pointer, for keyboard focus on the place buttons. */
    highlight(id) { if (outline) outline.selectedObjects = id && market.places[id] ? [market.places[id].holder] : []; },
  };
}
