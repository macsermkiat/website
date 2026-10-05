// Hover outline and tooltip, and clicks (or taps) on stalls, landmarks and the single items on their counters and
// shelves. One raycast per pointer move: the first thing under the pointer decides, so a roof post in front of a
// book still hides it. Deco stalls are scenery (ADR 0004): they only stop the pointer, so hovering or clicking one
// does nothing. A pick proxy (userData.pickProxy, e.g. a Bücherstand cabinet) answers for the things inside it.
import * as THREE from 'three';

function proxyOf(o) { for (let x = o; x; x = x.parent) { if (x.userData?.pickProxy) return x; if (x.userData?.entry) return null; } return null; }
function signOf(o) { for (let x = o; x; x = x.parent) if (x.userData?.sign) return x.userData.sign; return null; }
function signNode(o) { let arm = null; for (let x = o; x; x = x.parent) if (x.userData?.sign) arm = x; return arm; }
function surfaceRoot(o) { let top = o; for (let x = o; x && x.userData?.readable === o.userData.readable; x = x.parent) top = x; return top; }

// Items answer the pointer only from close by (the stall's close-up, or a visitor who zoomed in); from
// further away the pointer means the whole stall.
export const ITEM_RANGE = 11;

export function createPicking({ dom, camera, market, overlay, outline, items, labelFor, onPick, onItem, onProxy, proxyLabel = (p) => p.label || '', current = () => null, extraRoots = () => [], readLabel = () => '', signLabel = () => '', onRead, onSign, onLink, readingNow = () => false }) {
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.hidden = true;
  overlay.appendChild(tip);

  // coarse boxes first, so a pointer move only tests triangles of the place under it
  let boxes = [];
  const refresh = () => {
    const roots = [...market.hotRoots, ...(market.blockRoots || []), ...extraRoots().filter(Boolean)];
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

  /** What is under the pointer: { id (place), item?, proxy?, x, y, distance } or null (a deco stall: null). */
  function pick(ev) {
    const r = setRay(ev);
    const cands = boxes.filter((b) => ray.ray.intersectsBox(b.box)).map((b) => b.h);
    if (!cands.length) return null;
    const hits = ray.intersectObjects(cands, true);
    // the item under the pointer is lifted a little while hovered: a click on it still means it when the ray meets it
    // within a few centimetres of the first hit (on a tight row of spines seen at an angle, the lift can bring a
    // neighbour's edge in front of the click point)
    const held = items?.hovered;
    if (held && hits.length) {
      const h = hits.find((x) => x.distance - hits[0].distance < 0.08 && items.itemOf(x.object) === held);
      if (h) {
        let o = h.object;
        while (o && !o.userData.place && !o.userData.entry) o = o.parent;
        if (o && o.userData.place) return { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance, id: o.userData.place, item: held };
      }
    }
    for (const h of hits) {
      const o0 = h.object;
      // words in the market: a link on a page, a writing surface, an arm of the signpost
      if (o0.userData.href) return { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance, link: o0.userData.href, linkText: o0.userData.linkText, readable: o0.userData.readable || null };
      const sign = signOf(o0);
      if (sign) return { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance, sign, target: signNode(o0) };
      if (o0.userData.readable) {
        let o = o0; while (o && !o.userData.place && !o.userData.entry) o = o.parent;
        return { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance, readable: o0.userData.readable, id: o?.userData.place || null, target: surfaceRoot(o0) };
      }
      if (o0.userData.bulbs && hits.length > 1) continue;
      // a pick proxy (an invisible box round a Bücherstand cabinet): it answers for what is inside it
      const px = proxyOf(o0);
      if (px) {
        if (px.userData.pickProxy.off) continue;
        let o = px; while (o && !o.userData.place) o = o.parent;
        return { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance, id: o?.userData.place || null, proxy: px.userData.pickProxy, target: px.userData.pickProxy.outline || px };
      } else if (o0.userData.pickProxyHidden) continue;
      // the merged shelf goods: the items' own (hidden) meshes answer for them. A stall's merged body (mergeStatic)
      // still answers as its place.
      if (o0.userData.mergedItems) continue;
      if (o0.isSprite || o0.userData.itemFx === true && !items?.itemOf(o0)) continue;
      let o = o0;
      while (o && !o.userData.place && !o.userData.entry) o = o.parent;
      if (!o) continue;
      const base = { x: ev.clientX - r.left, y: ev.clientY - r.top, distance: h.distance };
      const item = items?.itemOf(o0);
      const place = o.userData.place || null;
      const near = h.distance < ITEM_RANGE || (place && current() === place);
      // an item only answers where its handler lets it (the books in a closed cabinet do not)
      if (item && near && place && (items.pickable?.(item) ?? true)) return { ...base, id: place, item };
      if (place) return { ...base, id: place };
      // a deco stall (scenery) or anything else: it stops the pointer, and nothing answers
      return null;
    }
    return null;
  }

  function show(p) {
    hover = p?.id || null;
    items?.hover(p?.item || null);
    if (outline) {
      const target = p?.link ? null : p?.target ? p.target : p?.item ? p.item.node : p?.id ? market.places[p.id]?.holder : null;
      // while reading, the page itself is not outlined (the words would blur)
      outline.selectedObjects = target && !(p.readable && readingNow()) ? [target] : [];
    }
    if (p) {
      tip.hidden = false;
      tip.textContent = p.link ? `Open: ${p.linkText || p.link}` : p.sign ? signLabel(p.sign) : p.readable ? readLabel(p.readable) : p.proxy ? proxyLabel(p.proxy) : p.item ? p.item.label : p.id ? labelFor(p.id) : p.label || '';
      tip.classList.toggle('item', !!p.item || !!p.readable || !!p.link || !!p.proxy);
      // kept inside the canvas: the tip is centred over the pointer and lifted above it (translate -50%, -150%),
      // so near an edge it slides in, and near the top it drops below the pointer
      const W = overlay.clientWidth || window.innerWidth, Hh = overlay.clientHeight || window.innerHeight;
      const tw = tip.offsetWidth, th = tip.offsetHeight, m = 8;
      tip.style.left = Math.min(Math.max(p.x, tw / 2 + m), Math.max(tw / 2 + m, W - tw / 2 - m)) + 'px';
      tip.style.top = (p.y - th * 1.5 < m ? Math.min(p.y + th * 2.2, Hh - m) : p.y) + 'px';
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
    if (!p) { onMiss?.(); return; }
    if (p.link) { onLink?.(p.link, p); return; }
    if (p.sign) { onSign?.(p.sign); return; }
    if (p.readable) { onRead?.(p.readable, p); return; }
    if (p.item) {
      // on a touch screen there is no hover: the tap lifts the item and shows its name for a moment
      if (e.pointerType === 'touch') { show(p); clearTimeout(tapTimer); tapTimer = setTimeout(() => show(null), 1400); }
      onItem(p.item, p);
      return;
    }
    if (p.proxy) { onProxy?.(p.proxy, p); return; }
    if (p.id) onPick(p.id);
  });
  let tapTimer = 0;
  let onMiss = null;

  return {
    get hover() { return hover; },
    /** Places added after the market opened (the rides and deco stalls). */
    refresh,
    /** The item a click at client (x, y) would reach, or null (tests aim clicks with it). */
    itemAt: (x, y) => pick({ clientX: x, clientY: y })?.item?.node.name || null,
    /** What a click at client (x, y) would reach (tests). */
    at: (x, y) => { const p = pick({ clientX: x, clientY: y }); return p ? { id: p.id || null, item: p.item?.node.name || null, proxy: p.proxy?.key || null } : null; },
    setEnabled(v) { enabled = v; if (!v) show(null); },
    /** Show the hover label with `text` at overlay point (x, y), as a hover there would (tests: edges); null hides. */
    tipAt: (x, y, text) => show(text == null ? null : { x, y, label: text }),
    /** A click on nothing (the sky, the ground far off). */
    onMiss(f) { onMiss = f; },
    /** What is under client (x, y): the full pick (tests). */
    full: (x, y) => { const p = pick({ clientX: x, clientY: y }); return p ? { id: p.id || null, item: p.item?.node.name || null, proxy: p.proxy ? `${p.proxy.kind}:${p.proxy.key}` : null, readable: p.readable || null, sign: p.sign || null, link: p.link || null } : null; },
    /** The raw hit list under client (x, y), nearest first (tests: what stops the pointer). */
    rawAt: (x, y) => { setRay({ clientX: x, clientY: y }); const cands = boxes.filter((b) => ray.ray.intersectsBox(b.box)).map((b) => b.h); return ray.intersectObjects(cands, true).slice(0, 4).map((h) => { let o = h.object; while (o && !o.userData.entry) o = o.parent; return { entry: o?.userData.entry?.id || null, kind: o?.userData.entry?.kind || null, distance: +h.distance.toFixed(2) }; }); },
    /** Highlight a place without a pointer, for keyboard focus on the place buttons. */
    highlight(id) { if (outline) outline.selectedObjects = id && market.places[id] ? [market.places[id].holder] : []; },
  };
}
