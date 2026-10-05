// Every item on the counters and shelves is its own clickable object: a book, a glass, a mug, a wine bottle,
// a sausage, a roll, and the ornament shop's ornaments. This module finds them (the act_ nodes of the vendor's
// prop sets, named in site/public/models/items.json), lifts them a little under the pointer, and hands a click
// to the stall's own handler (beer.js, gluehwein.js, wurst.js, books.js, schmuck.js). The deco stalls' goods are
// scenery with no act_ nodes (ADR 0004), so nothing here touches them.
import * as THREE from 'three';
import { infoOf, kindOf, worldDirToParent, boxOf, UP } from './common.js';
import { createBeer } from './beer.js';
import { createGluehwein } from './gluehwein.js';
import { createWurst } from './wurst.js';
import { createBooks } from './books.js';
import { createSchmuck } from './schmuck.js';

// act_ kinds a visitor can click; the rest (steam, smoke, the grill, the ladle) only move for them
const CLICKABLE = new Set(['book', 'glass', 'tap', 'mug', 'bottle', 'wineglass', 'kettle', 'pot', 'lid', 'sausage', 'roll', 'served', 'orn']);
// kinds whose click the camera comes in close for (a book comes to the visitor instead; an ornament plays where it
// hangs, seen from the shop's own view)
const FOCUS = new Set(['glass', 'tap', 'mug', 'bottle', 'wineglass', 'kettle', 'pot', 'lid', 'sausage', 'roll', 'served']);
const HOVER_LIFT = 0.018; // metres an item rises under the pointer

export function createItems(ctx) {
  const { market, anim } = ctx;
  const byNode = new Map(); // pivot -> item
  const byPlace = {}; // place id -> [item]
  let hovered = null;

  /** Make an item record for an act_ pivot. */
  function add(node, placeId, place, kind = kindOf(node)) {
    if (!kind || byNode.has(node)) return null;
    const info = infoOf(node);
    const item = {
      node, kind, info, placeId, place,
      label: info.title || info.name || node.userData?.label || prettify(node.name),
      clickable: CLICKABLE.has(kind),
      busy: false, // a handler is moving it
      keepOwn: false, // drawn by its own mesh, not the merged shelf mesh (its look changed)
      lifted: false,
      hoverBase: null,
    };
    node.userData.live = true; // never merged by mergeStatic: it moves
    node.userData.item = node.userData.item || null;
    byNode.set(node, item);
    (byPlace[placeId] ||= []).push(item);
    return item;
  }

  function scanPlace(place) {
    for (const node of Object.values(place.nodes.acts)) add(node, place.id, place);
  }
  for (const place of Object.values(market.places)) scanPlace(place);

  const sub = { ...ctx, items: { of: (id, kind) => (byPlace[id] || []).filter((i) => !kind || i.kind === kind), add, own, release, settle } };
  const shop = createSchmuck(sub);
  const handlers = [createBeer(sub), createGluehwein(sub), createWurst(sub), createBooks(sub), shop];
  const onClick = {};
  for (const h of handlers) Object.assign(onClick, h.kinds || {});

  /** Draw the item with its own mesh (out of the merged shelf mesh), so it can move or change. */
  function own(item) {
    if (item.lifted) return;
    item.lifted = true;
    item.place?.merge?.lift(item.node);
  }
  /** Back into the merged mesh once it is home and unchanged. */
  function settle(item) {
    if (!item.lifted || item.busy || item.keepOwn || hovered === item || item.hoverBase) return;
    item.lifted = false;
    item.place?.merge?.settle(item.node);
  }
  /** A handler takes the item: drop any hover lift at once. */
  function release(item) {
    if (item.hoverBase) { item.node.position.copy(item.hoverBase); item.hoverBase = null; item.hoverK = 0; }
    own(item);
  }

  // hover lift, eased every frame: the item rises HOVER_LIFT metres while the pointer is on it
  const lifting = new Set();
  function hoverOn(item) {
    if (item.busy) return;
    own(item);
    if (!item.hoverBase) {
      item.hoverBase = item.node.position.clone();
      item.hoverUp = worldDirToParent(item.node, UP).multiplyScalar(HOVER_LIFT);
      item.hoverK = 0;
    }
    item.hoverWant = 1;
    lifting.add(item);
  }
  function hoverOff(item) { item.hoverWant = 0; }
  function stepHover(dt, still) {
    for (const item of lifting) {
      if (!item.hoverBase) { lifting.delete(item); continue; }
      if (item.busy) { lifting.delete(item); continue; }
      item.hoverK += (item.hoverWant - item.hoverK) * (still ? 1 : Math.min(1, dt * 14));
      item.node.position.copy(item.hoverBase).addScaledVector(item.hoverUp, item.hoverK);
      if (!item.hoverWant && item.hoverK < 0.01) {
        item.node.position.copy(item.hoverBase);
        item.hoverBase = null;
        lifting.delete(item);
        settle(item);
      }
    }
  }

  return {
    /** The item a scene object belongs to (walks up to the act_ pivot), or null. */
    itemOf(obj) {
      for (let o = obj; o; o = o.parent) {
        const it = byNode.get(o) || o.userData.itemProxy;
        if (it) return it.clickable ? it : null;
        if (o.userData.place || o.userData.entry) return null;
      }
      return null;
    },
    /** Pointer over an item (or null): lift it and say what it is. */
    hover(item) {
      if (hovered === item) return;
      const prev = hovered;
      hovered = item;
      if (prev) hoverOff(prev);
      if (item) hoverOn(item);
    },
    get hovered() { return hovered; },
    /** May the pointer pick this item now? (a Bücherstand cabinet's books only while that cabinet is open) */
    pickable(item) {
      for (const h of handlers) { const v = h.pickable?.(item); if (v === false) return false; }
      return true;
    },
    /** A click on a pick proxy (a cabinet): its handler's. */
    proxyClick(px) { for (const h of handlers) if (h.proxyClick?.(px)) return true; return false; },
    click(item) {
      const fn = onClick[item.kind];
      if (!fn) return false;
      fn(item);
      return true;
    },
    /** Places that arrive after the first frame (the rides, a deferred ornament shop). */
    addPlaced(placed) {
      for (const p of placed) {
        if (!p.entry.place || !market.places[p.entry.place]) continue;
        scanPlace(market.places[p.entry.place]);
        for (const h of handlers) h.addPlace?.(market.places[p.entry.place]);
      }
    },
    /** Where a click on this item plays out (world): the camera comes in close to it. Books present
     *  themselves in front of the stall view, so they have none. */
    focusOf(item) {
      if (!FOCUS.has(item.kind)) return null;
      for (const h of handlers) { const p = h.focusOf?.(item); if (p) return p; }
      return boxOf(item.node).getCenter(new THREE.Vector3());
    },
    all: () => [...byNode.values()],
    /** The ornament shop's moments (round 9): the main loop calls its pre/post/beforeRender hooks. */
    shop,
    of: (id, kind) => (byPlace[id] || []).filter((i) => !kind || i.kind === kind),
    handlers: Object.assign({}, ...handlers.map((h) => h.api || {})),
    /** A place was closed or the view went home: put everything that stands out back. */
    retract() { for (const h of handlers) h.retract?.(); },
    update(dt, t, still) { stepHover(dt, still); for (const h of handlers) h.update?.(dt, t, still); },
  };
}

function prettify(name) {
  return String(name || '').replace(/^act_/, '').replace(/_\d+$/, '').replace(/_/g, ' ');
}

export { THREE };
