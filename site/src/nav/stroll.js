// The guided stroll's stops and the lane paths between them (docs/adr/0003-guided-stroll-navigation.md).
//
// Where the path comes from, first found wins:
//   1. layout.json "stroll" (the architect's, blender/square/stroll.py): "order" (the loop, layout ids, "home"
//      first), "stops" [{ id, eye, target, overview? }] and "legs" [{ from, to, points }], one leg per pair of
//      stops, checked to keep clear of stalls, poles and the standing crowd. A walk takes the leg (backwards when
//      only the other way is listed), joined from wherever the camera is.
//   2. path_<n> empties in square.glb, in order, as one lane round the square
//   3. a temporary lane round the open middle of the square, from the BUILD.md layout (this file)
// On a lane (2, 3) a walk from A to B leaves A's view for the lane, follows it the shorter way round, and comes
// off it to B's view, so it never cuts through a stall.
// The Riesenrad stop is the overview: the walk ends at the foot of the wheel and the camera then rises to the
// view from the top gondola (the stop's "overview"), looking across the whole market.
import * as THREE from 'three';
import { viewFor } from '../engine/market.js';

// the temporary lane: a ring through the open square at eye height (x, z), clockwise from the front
const TEMP_LANE = [[0, 12.5], [-8, 9.5], [-17, 8], [-17.2, -3], [-12.5, -9.5], [-4, -11.6], [5.5, -10.6], [12.5, -6.2], [16.6, 4], [8.5, 9.5]];
const LANE_Y = 2.3;
// the stroll's order round the square (prev / next), when the architect gives none
const LOOP = ['glueh', 'wurst', 'ferris', 'band', 'carousel', 'books', 'bier'];

/**
 * The Riesenrad stop is the overview of the whole market: high on the wheel's side of the square, looking
 * across all of it, with the wheel at the left edge of the picture.
 */
const OVERVIEW_OUT = 4.5;
export const OVERVIEW = { pos: [-10.5, 13.5, 13], target: [0.5, 1.2, -6.5] };

export function createStroll({ market, layout, order, scene }) {
  const raw = layout?.raw?.stroll || null;
  const placeOf = (lid) => (lid === 'home' ? 'home' : market.layout.entries.find((e) => e.id === lid)?.place || lid);
  const V = (a) => new THREE.Vector3(...a);
  // the architect's stops and legs, by place id
  const arch = raw && Array.isArray(raw.legs) && raw.legs.length && Array.isArray(raw.stops) && typeof raw.stops[0] === 'object';
  const stopViews = {}, legs = new Map();
  if (arch) {
    for (const st of raw.stops) {
      if (!st?.eye || !st?.target) continue;
      let overview = null;
      if (st.overview?.eye) {
        // the top gondola's eye sits inside the wheel's rim and spokes: a few metres out along the view, so the
        // picture is the market and not the timber in front of it
        const pos = V(st.overview.eye), target = V(st.overview.target);
        pos.addScaledVector(target.clone().sub(pos).normalize(), OVERVIEW_OUT);
        overview = { pos, target };
      }
      stopViews[placeOf(st.id)] = { pos: V(st.eye), target: V(st.target), overview };
    }
    for (const g of raw.legs) if (g?.points?.length > 1) legs.set(`${placeOf(g.from)}>${placeOf(g.to)}`, g.points.map(V));
  }
  const source = arch ? 'layout.json stroll (stops and legs)' : raw?.lane ? 'layout.json stroll' : null;
  let lane = null;
  if (raw?.lane?.length > 2) lane = raw.lane.map((p) => (p.length === 2 ? new THREE.Vector3(p[0], LANE_Y, p[1]) : new THREE.Vector3(...p)));
  let laneSource = source;
  if (!lane) {
    const pts = [];
    scene?.traverse((o) => { const m = /^path_(\d+)/i.exec(o.name || ''); if (m) pts.push([+m[1], o.getWorldPosition(new THREE.Vector3())]); });
    if (pts.length > 2) {
      lane = pts.sort((a, b) => a[0] - b[0]).map(([, p]) => { if (p.y < 1) p.y = LANE_Y; return p; });
      laneSource = 'square.glb path_ empties';
    }
  }
  if (!lane) { lane = TEMP_LANE.map(([x, z]) => new THREE.Vector3(x, LANE_Y, z)); laneSource = 'temporary lane (engine)'; }
  const loopLane = raw?.loop !== false;
  const loopIds = arch && Array.isArray(raw.order) ? raw.order.map(placeOf) : Array.isArray(raw?.stops) && typeof raw.stops[0] === 'string' ? raw.stops : LOOP;
  const stops = loopIds.filter((id) => order.includes(id));
  for (const id of order) if (!stops.includes(id)) stops.push(id);

  /** Where a walk to the stop ends (for the Riesenrad, the foot of the wheel). */
  function footOf(id) {
    const a = stopViews[id];
    return a ? { pos: a.pos.clone(), target: a.target.clone() } : viewOf(id);
  }
  /** Where the camera rests at a stop after the walk (for the Riesenrad, its overview), or null. */
  function riseOf(id) {
    const o = stopViews[id]?.overview || (!arch && id === 'ferris' ? { pos: V(OVERVIEW.pos), target: V(OVERVIEW.target) } : null);
    return o ? { pos: o.pos.clone(), target: o.target.clone() } : null;
  }
  /** A stop's view (camera position and target) where the visitor rests there. */
  function viewOf(id) {
    const a = stopViews[id];
    if (a) { const v = a.overview || a; return { pos: v.pos.clone(), target: v.target.clone() }; }
    const v = raw?.views?.[id];
    if (v?.pos && v?.target) return { pos: new THREE.Vector3(...v.pos), target: new THREE.Vector3(...v.target) };
    if (id === 'ferris') return { pos: new THREE.Vector3(...OVERVIEW.pos), target: new THREE.Vector3(...OVERVIEW.target) };
    const p = market.places[id];
    if (p) return viewFor(p);
    // a ride still loading: in front of where the layout puts it
    const e = market.layout.entries.find((x) => x.place === id);
    if (!e) return null;
    const c = new THREE.Vector3(e.position[0], 2, e.position[2]);
    const fwd = new THREE.Vector3(Math.sin(e.rotation || 0), 0, Math.cos(e.rotation || 0));
    return { pos: c.clone().addScaledVector(fwd, 12).setY(4), target: c };
  }

  function nearestLane(p) {
    let best = 0, bd = Infinity;
    lane.forEach((q, i) => { const d = Math.hypot(q.x - p.x, q.z - p.z); if (d < bd) { bd = d; best = i; } });
    return best;
  }

  /** The nearest stop to a camera position ('home' included), for a walk that does not say where it starts. */
  function nearestStop(p) {
    let best = null, bd = Infinity;
    for (const [id, v] of Object.entries(stopViews)) for (const w of [v, v.overview].filter(Boolean)) { const d = w.pos.distanceTo(p); if (d < bd) { bd = d; best = id; } }
    return best;
  }

  /**
   * Camera positions from `from` (a Vector3; the stop `fromId` when known) to stop `id`.
   * Returns { points, view (where the walk ends), rise (a view to rise to after it, or null) }.
   */
  function pathTo(from, id, fromId) {
    if (arch && stopViews[id]) {
      const view = footOf(id);
      const start = fromId && stopViews[fromId] ? fromId : nearestStop(from);
      let leg = legs.get(`${start}>${id}`);
      if (!leg && legs.get(`${id}>${start}`)) leg = legs.get(`${id}>${start}`).slice().reverse();
      if (leg && start !== id) {
        const pts = leg.map((q) => q.clone());
        // joined from where the camera is (a close-up, a page, the top of the wheel): skip leg points behind it
        while (pts.length > 2 && from.distanceTo(pts[1]) < pts[0].distanceTo(pts[1])) pts.shift();
        if (from.distanceTo(pts[0]) > 0.3) pts.unshift(from.clone());
        pts[pts.length - 1].copy(view.pos);
        return { points: dedupe(pts), view, rise: riseOf(id) };
      }
      if (start === id) return { points: [from.clone(), view.pos.clone()], view, rise: riseOf(id) };
    }
    const lp = lanePath(from, id);
    return lp ? { ...lp, rise: arch ? null : riseOf(id) } : null;
  }

  function lanePath(from, id) {
    const view = arch ? footOf(id) : (id === 'ferris' ? null : viewOf(id)) || viewOfLane(id);
    if (!view) return null;
    const a = nearestLane(from), b = nearestLane(view.pos);
    const pts = [from.clone()];
    const n = lane.length;
    // the lane, the shorter way round (or straight along an open path)
    let seq = [];
    if (a !== b) {
      const fwd = [], back = [];
      for (let i = a; ; i = (i + 1) % n) { fwd.push(i); if (i === b || fwd.length > n) break; if (!loopLane && i === n - 1) { fwd.length = n + 2; break; } }
      for (let i = a; ; i = (i - 1 + n) % n) { back.push(i); if (i === b || back.length > n) break; if (!loopLane && i === 0) { back.length = n + 2; break; } }
      seq = fwd.length <= back.length ? fwd : back;
    } else seq = [a];
    // skip a lane point that lies behind the start (walking back to it first looks wrong)
    const lanePts = seq.map((i) => lane[i].clone());
    if (lanePts.length > 1 && from.distanceTo(lanePts[1]) < lanePts[0].distanceTo(lanePts[1])) lanePts.shift();
    if (lanePts.length > 1 && view.pos.distanceTo(lanePts[lanePts.length - 2]) < lanePts[lanePts.length - 1].distanceTo(lanePts[lanePts.length - 2])) lanePts.pop();
    // from far away (the home view up high), the first lane point comes down to eye height over the walk
    for (const p of lanePts) if (from.distanceTo(p) > 2 && view.pos.distanceTo(p) > 2) pts.push(p);
    pts.push(view.pos.clone());
    // heights: ease from the start's height to the lane's and on to the stop's
    const total = pts.reduce((acc, p, i) => acc + (i ? p.distanceTo(pts[i - 1]) : 0), 0) || 1;
    let run = 0;
    for (let i = 1; i < pts.length - 1; i++) {
      run += pts[i].distanceTo(pts[i - 1]);
      const u = run / total;
      const laneH = Math.max(LANE_Y, Math.min(from.y, view.pos.y) * 0.5);
      pts[i].y = u < 0.5 ? THREE.MathUtils.lerp(from.y, laneH, Math.min(1, u * 2.4)) : THREE.MathUtils.lerp(laneH, view.pos.y, Math.max(0, (u - 0.5) * 2) ** 2);
    }
    return { points: dedupe(pts), view };
  }
  // the old lane's ferris stop: walk to below the overview, then rise
  function viewOfLane(id) {
    if (id !== 'ferris') return viewOf(id);
    const p = market.places[id];
    return p ? viewFor(p) : viewOf(id);
  }

  const indexOf = (id) => stops.indexOf(id);
  return {
    stops,
    laneSource: arch ? source : laneSource,
    /** The architect's stops and legs are in use. */
    hasStops: !!arch,
    lane: () => lane.map((p) => p.toArray()),
    viewOf,
    footOf,
    riseOf,
    pathTo,
    nearestStop,
    next: (id) => stops[(indexOf(id) + 1 + stops.length) % stops.length],
    prev: (id) => stops[(indexOf(id) - 1 + stops.length) % stops.length],
    /** The stop a visitor at home walks to first. */
    first: () => stops[0],
  };
}

function dedupe(pts) {
  const out = [pts[0]];
  for (const p of pts.slice(1)) if (p.distanceTo(out[out.length - 1]) > 0.6) out.push(p);
  if (out.length === 1) out.push(pts[pts.length - 1]);
  if (!out[out.length - 1].equals(pts[pts.length - 1])) out[out.length - 1] = pts[pts.length - 1];
  return out;
}
