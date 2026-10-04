// The rides: sit in a Riesenrad gondola, or on a carousel horse, and see the market move past.
import * as THREE from 'three';
import { viewFor } from '../engine/market.js';
import { actionHint, actionNote } from '../content.js';

const SEAT = /(^|_)seat(_|$)/i;
/** The seat empty's position in `node`'s frame (gondola_seat_0, horse_seat_2, seat, cam_seat), or null. */
function seatIn(node) {
  let seat = null;
  node.traverse((o) => { if (!seat && o !== node && SEAT.test(o.name)) seat = o; });
  if (!seat) return null;
  const p = new THREE.Vector3();
  for (let o = seat; o && o !== node; o = o.parent) { o.updateMatrix(); p.applyMatrix4(o.matrix); }
  return p;
}

/**
 * Where the rider's eyes go, in the rider node's frame. A seat empty in this node wins; else one in a sibling
 * rider (gondolas are built alike, and only gondola_0 carries a seat); else the middle of the node's bounds.
 */
function seatOffset(node, fallbackY, siblings = []) {
  const own = seatIn(node);
  if (own) return own;
  for (const s of siblings) { const p = s !== node && seatIn(s); if (p) return p; }
  const box = new THREE.Box3();
  node.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    const m = new THREE.Matrix4();
    // bounding box in the node's own frame
    let p = o;
    const chain = [];
    while (p && p !== node) { chain.push(p); p = p.parent; }
    chain.reverse().forEach((c) => { c.updateMatrix(); m.multiply(c.matrix); });
    box.union(o.geometry.boundingBox.clone().applyMatrix4(m));
  });
  if (box.isEmpty()) return new THREE.Vector3(0, fallbackY, 0);
  const c = box.getCenter(new THREE.Vector3());
  return new THREE.Vector3(c.x, c.y + fallbackY, c.z);
}

export function createRideActions({ market, rig, say, sfx, motion }) {
  // the lite market loads the rides just after it opens: look them up when they are used
  const place = (id) => market.places[id];
  /** Run `start` once the ride is in the market (at once, or when a deferred ride arrives). */
  function whenReady(id, start) {
    if (place(id) || !market.whenPlace) return start();
    say('One moment, the ride is still being set up…');
    market.whenPlace(id, { load: true }).then(() => start());
  }
  // from a gondola: over the square toward the church, the stalls below and the town beyond
  const lookAtMarket = new THREE.Vector3(8, 3, 4);
  const FERRIS_LEAN = 0.5;
  const tmp = new THREE.Vector3();
  let riding = null;

  function endRide(silent) {
    if (!riding) return;
    const place = riding.place;
    if (riding.rides?.wheel) riding.rides.wheel.boost = 1;
    stage = null;
    riding = null;
    rig.endRide(silent ? null : viewFor(place));
    if (!silent) say(actionNote(place.id, 'off', 'Back on the ground.'));
  }

  function startFerris() {
    const ferris = place('ferris');
    const r = ferris?.rides;
    if (!r || !r.gondolas.length) return say('This Riesenrad has no gondolas to sit in yet.');
    if (riding) endRide(true);
    // board the gondola nearest the ground; the wheel then turns faster until that gondola is at the top,
    // stops there for the view (HOLD seconds, barely moving), and goes on at its own pace
    let best = r.gondolas[0], by = Infinity, top = -Infinity;
    for (const g of r.gondolas) { const y = g.obj.getWorldPosition(tmp).y; if (y < by) { by = y; best = g; } top = Math.max(top, y); }
    const seat = seatOffset(best.obj, 0.2, r.gondolas.map((g) => g.obj));
    if (r.wheel) r.wheel.boost = 1;
    riding = { type: 'ferris', place: ferris, rides: r, gondola: best.obj, bottom: by, top, held: 0, peak: -Infinity };
    stage = r.wheel ? 'rising' : 'top';
    // the rider leans out over the gondola's front rail toward the view (FERRIS_LEAN metres, level), so the
    // gondola's own roof edge and the wheel's rim stay out of the top of the picture
    const lean = new THREE.Vector3();
    rig.startRide('ferris', () => {
      const pos = best.obj.localToWorld(seat.clone());
      lean.set(lookAtMarket.x - pos.x, 0, lookAtMarket.z - pos.z).setLength(FERRIS_LEAN);
      return { pos: pos.add(lean), look: lookAtMarket };
    }, { near: 0.45 });
    sfx('whoosh');
    say(actionNote('ferris', 'ride', 'Riding up. The whole market opens out below you.'));
  }

  function startCarousel() {
    const carousel = place('carousel');
    const r = carousel?.rides;
    if (!r || !r.horses.length) return say('This carousel has no horses to ride yet.');
    if (riding) endRide(true);
    const h = (r.horses.find((x) => seatIn(x.obj)) || r.horses[Math.min(2, r.horses.length - 1)]).obj;
    const seat = seatOffset(h, 1.0, r.horses.map((x) => x.obj));
    const c = carousel.holder.position;
    riding = { type: 'carousel', place: carousel, rides: r };
    rig.startRide('carousel', () => {
      const pos = h.localToWorld(seat.clone());
      const out = new THREE.Vector3(pos.x - c.x, 0, pos.z - c.z).normalize();
      const dir = r.platform && r.platform.speed > 0 ? -1 : 1;
      const tan = new THREE.Vector3(out.z, 0, -out.x).multiplyScalar(dir);
      // forward along the ride, turned a little inward to the mirrors, the lights and the other horses
      return { pos, look: new THREE.Vector3(pos.x + tan.x * 3 - out.x * 3, pos.y - 0.4, pos.z + tan.z * 3 - out.z * 3) };
    });
    sfx('chime');
    say(actionNote('carousel', 'ride', 'Hold on to the pole. Round and round under the lights.'));
  }

  // ---------- the ride up: rising -> top (the view) -> round ----------
  let stage = null;
  const HOLD = 14, RISE_BOOST = 7, TOP_BOOST = 0.12;
  function update(dt) {
    if (!riding || riding.type !== 'ferris' || !riding.rides.wheel) return;
    const w = riding.rides.wheel;
    const y = riding.gondola.getWorldPosition(tmp).y;
    const span = Math.max(1, riding.top - riding.bottom);
    const up = (y - riding.bottom) / span; // 0 at the bottom, 1 at the top
    if (stage === 'rising') {
      // ease in, then run, and ease out over the last fifth of the way up; stop at the very top (or, past
      // halfway, as soon as the gondola starts coming down again; the lowest gondola may first dip a little)
      const k = up < 0.1 ? 0.35 + up * 6.5 : up > 0.8 ? Math.max(0.12, (1 - up) * 5) : 1;
      w.boost = Math.max(TOP_BOOST, RISE_BOOST * k);
      if (up > 0.985 || (up > 0.6 && y < riding.peak - 0.02)) { stage = 'top'; riding.held = 0; say(actionNote('ferris', 'ride', 'At the top. The whole market lies below you: the stalls, the bandstand, the tree and the old town round it.', {}, { done: true })); }
      riding.peak = Math.max(riding.peak, y);
    } else if (stage === 'top') {
      w.boost = TOP_BOOST;
      if ((riding.held += dt) > HOLD) { stage = 'round'; w.boost = 1; }
    } else w.boost = 1;
  }
  /** Brighter exposure while riding: from a gondola the lit market is far below and small (1 = none). */
  function exposure() {
    if (!riding) return 1;
    if (riding.type === 'carousel') return 1.15;
    const y = riding.gondola.getWorldPosition(tmp).y;
    const up = THREE.MathUtils.clamp((y - riding.bottom) / Math.max(1, riding.top - riding.bottom), 0, 1);
    return 1.2 + 0.45 * up;
  }

  return {
    update,
    exposure,
    /** 'rising', 'top' or 'round' on the Riesenrad, else null (tests wait for the top). */
    get stage() { return riding?.type === 'ferris' ? stage : null; },
    ferris: { hint: actionHint('ferris', 'Take a ride to the top for the view over the market.'), acts: [{ key: 'ride', label: 'Ride to the top', fn: () => whenReady('ferris', startFerris) }, { key: 'off', label: 'Get off', fn: () => endRide(false) }] },
    carousel: { hint: actionHint('carousel', 'Climb on a horse and go round.'), acts: [{ key: 'ride', label: 'Ride a horse', fn: () => whenReady('carousel', startCarousel) }, { key: 'bell', label: 'Ring the bell', fn: () => sfx('chime') }, { key: 'off', label: 'Get off', fn: () => endRide(false) }] },
    endRide,
    get riding() { return riding; },
    /** While riding, rides keep turning even with reduced motion (the visitor asked for the motion). */
    ridingActive: () => !!riding,
    motion,
  };
}
