// The Bierstand: click a glass and the tap pours into it, the beer rising under a head of foam; click two full
// glasses and they clink (Prost!). The panel's "Pull a pint" and "Prost!" buttons drive the same code.
import * as THREE from 'three';
import { boxOf, meshByMaterial, rest, restore, worldToParent, worldDirToParent, createStream, BEER, FOAM as FOAM_M, UP, esc } from './common.js';
import { actionNote, toastLines } from '../../content.js';

export function createBeer(ctx) {
  const { market, anim, scene, sfx, say, crowdSay, items } = ctx;
  const place = market.places.bier;
  if (!place) return {};
  const stream = createStream(scene, BEER, 0.007);
  const glasses = new Map(); // item -> state
  let pouring = null, selected = null, filled = 0, clinking = false;
  const queue = [];

  const taps = items.of('bier', 'tap');
  const badFoam = []; // glasses whose vendor head was unusable (reported in the api)
  const front = new THREE.Vector3(Math.sin(place.ry), 0, Math.cos(place.ry)); // toward the customer

  function stateOf(item) {
    let s = glasses.get(item);
    if (s) return s;
    const node = item.node;
    const beer = meshByMaterial(node, /beer|lager|ale/i);
    let foam = null;
    node.traverse((o) => { if (!foam && /^foam/i.test(o.name || '')) foam = o; });
    // the glass's own size, without its head (a head mesh that came out of the optimiser the wrong size must
    // not make the glass a metre tall)
    const foamMeshes = [];
    foam?.traverse((o) => { if (o.isMesh) { foamMeshes.push([o, o.userData.itemFx]); o.userData.itemFx = true; } });
    const box = boxOf(node, node);
    for (const [o, fx] of foamMeshes) o.userData.itemFx = fx;
    if (foam && !foamFits(foam, node, box)) {
      badFoam.push(node.name);
      foam.visible = false;
      foam.traverse((o) => { if (o.isMesh) place.merge?.drop?.(o); });
      foam = madeHead(node, beer, box);
    }
    const upside = /upside down/i.test(item.info.name || '') || /upside/i.test(item.info.where || '');
    s = {
      item, beer, foam, box, upside, rest: rest(node),
      foamY: foam?.position.y ?? 0, foamS: foam?.scale.clone() ?? new THREE.Vector3(1, 1, 1),
      level: beer ? 1 : 0, head: foam ? 1 : 0, full: !!beer,
      height: Math.max(0.05, box.max.y - box.min.y), radius: Math.max(0.03, Math.min(box.max.x - box.min.x, box.max.z - box.min.z) / 2),
      tap: tapFor(item),
    };
    glasses.set(item, s);
    return s;
  }

  /** A vendor head sits on the glass: no taller than half the glass, its top not far above the rim. */
  function foamFits(foam, node, glassBox) {
    const fb = boxOf(foam, node);
    if (fb.isEmpty()) return false;
    const h = glassBox.max.y - glassBox.min.y;
    return fb.max.y - fb.min.y < h * 0.5 && fb.max.y < glassBox.max.y + h * 0.35;
  }

  /** A head made here, on top of the vendor's beer (for a glass whose own head is unusable). */
  function madeHead(node, beer, glassBox) {
    const bb = beer ? boxOf(beer, node) : glassBox;
    const r = Math.max(0.015, Math.min(bb.max.x - bb.min.x, bb.max.z - bb.min.z) / 2) * 1.02;
    const hh = Math.max(0.012, (glassBox.max.y - glassBox.min.y) * 0.1);
    const head = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.03, r, hh, 20).translate(0, hh / 2, 0), FOAM_M);
    head.name = 'item_head';
    head.userData.itemFx = true;
    head.position.set((bb.min.x + bb.max.x) / 2, bb.max.y - hh * 0.35, (bb.min.z + bb.max.z) / 2);
    node.add(head);
    return head;
  }

  /** The tap that pours this glass's beer (items.json: glass.beer "Dunkles" -> "Dunkles tap"), else the middle one. */
  function tapFor(item) {
    const beer = String(item.info.beer || '').toLowerCase();
    return taps.find((t) => beer && String(t.info.name || '').toLowerCase().includes(beer)) || taps[Math.min(1, taps.length - 1)] || null;
  }

  /** Where the beer leaves the tap (world): under the handle's pivot, a little toward the customer. */
  function spoutOf(tap) {
    if (!tap) {
      const c = place.nodes.slots.slot_counter?.getWorldPosition(new THREE.Vector3()) || place.center.clone();
      return c.add(new THREE.Vector3(0, 0.45, 0));
    }
    const p = tap.node.getWorldPosition(new THREE.Vector3());
    return p.add(new THREE.Vector3(0, -0.075, 0)).addScaledVector(front, 0.055);
  }

  /** A glass the vendor made empty gets its own beer: a column and a head, standing on the glass floor. */
  function ensureBeer(s) {
    if (s.beer || s.made) return;
    const box = boxOf(s.item.node);
    const size = box.getSize(new THREE.Vector3());
    const r = Math.max(0.02, Math.min(size.x, size.z) / 2) * 0.8;
    const H = size.y * 0.8;
    const g = new THREE.Group();
    g.name = 'item_beer';
    const liq = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 0.92, 1, 20).translate(0, 0.5, 0), BEER);
    const head = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.02, r, 1, 20).translate(0, 0.5, 0), FOAM_M);
    for (const m of [liq, head]) { m.userData.itemFx = true; m.castShadow = false; g.add(m); }
    g.position.set((box.min.x + box.max.x) / 2, box.min.y + size.y * 0.06, (box.min.z + box.max.z) / 2);
    scene.add(g);
    s.item.node.attach(g); // keeps its world pose: its y axis is the world's up, whichever way the pivot faces
    s.made = { g, liq, head, H };
  }

  /** Beer level f (0..1) and head h (0..1) in a glass. The vendor's beer mesh scales up from the glass floor. */
  function setLevel(s, f, h) {
    s.level = f; s.head = h;
    if (s.made) {
      const { liq, head, H } = s.made;
      liq.scale.y = Math.max(0.001, f * H * 0.9);
      liq.visible = f > 0.01;
      head.position.y = f * H * 0.9;
      head.scale.y = Math.max(0.001, H * 0.12 * h);
      head.visible = h > 0.03 && f > 0.05;
    }
    if (s.beer) { s.beer.scale.y = Math.max(0.001, f); s.beer.visible = f > 0.01; }
    if (s.foam) {
      // the head rides on the beer: it sits where the full glass has it, lowered with the level
      const drop = (1 - f) * s.height * 0.82;
      s.foam.position.y = s.foamY - drop / Math.max(1e-6, s.item.node.scale.y);
      s.foam.scale.set(s.foamS.x, s.foamS.y * Math.max(0.05, h), s.foamS.z);
      s.foam.visible = h > 0.03 && f > 0.05;
    }
  }

  // The counter starts with two full Maß and the rest of the glasses clean and empty, waiting to be filled.
  items.of('bier', 'glass').forEach(stateOf); // every glass checked once (a broken vendor head is replaced now)
  const counter = items.of('bier', 'glass').filter((g) => !/upside/i.test(g.info.name || '')).map(stateOf).filter((s) => s.beer);
  counter.forEach((s, i) => {
    if (i < 2) return;
    items.own(s.item);
    s.item.keepOwn = true;
    setLevel(s, 0, 0);
    s.full = false;
  });

  function flip(s, done) {
    // an upside-down glass from the back shelf: turned the right way up where it stands
    const node = s.item.node;
    const r0 = rest(node);
    const axis = worldDirToParent(node, new THREE.Vector3().crossVectors(UP, front).normalize()).normalize();
    const q0 = r0.q.clone(), qf = new THREE.Quaternion().setFromAxisAngle(axis, Math.PI);
    const lift = worldDirToParent(node, UP);
    anim.add(0.7, (k) => {
      node.quaternion.copy(q0).premultiply(new THREE.Quaternion().slerpQuaternions(new THREE.Quaternion(), qf, k));
      node.position.copy(r0.p).addScaledVector(lift, s.height * k + Math.sin(k * Math.PI) * 0.06);
    }, () => { s.upside = false; s.rest = rest(node); done?.(); });
  }

  /** Pour a glass: to the tap, the handle forward, beer and foam rise, back to its place. */
  function pour(item, { fresh = false } = {}) {
    const s = stateOf(item);
    if (pouring) { if (!queue.includes(item) && pouring !== s) queue.push(item); return; }
    if (s.upside) { pouring = s; items.release(item); item.busy = true; flip(s, () => { item.busy = false; pouring = null; pour(item); }); return; }
    pouring = s;
    items.release(item);
    item.busy = true;
    item.keepOwn = true;
    if (selected === s) selected = null;
    ensureBeer(s);
    if (fresh || s.full) setLevel(s, 0, 0);
    const node = item.node;
    const home = s.rest.p.clone();
    const tap = s.tap;
    const spout = spoutOf(tap);
    const baseWorld = node.parent.localToWorld(home.clone());
    const under = worldToParent(node, new THREE.Vector3(spout.x, baseWorld.y, spout.z));
    const up = worldDirToParent(node, UP);
    const tr0 = tap ? tap.node.rotation.x : 0;
    sfx('pour');
    const what = item.info.name ? `${esc(item.info.name)}` : 'A pint';
    say(`<b>${what}</b>, at the ${esc(tap?.info.name || 'middle tap')}. ${actionNote('bier', 'pint', 'Pouring… tilt, fill, then top it off with foam.', { name: item.info.name })}`);
    // 1. slide the glass under the tap
    anim.add(0.6, (k) => { node.position.lerpVectors(home, under, k).addScaledVector(up, Math.sin(k * Math.PI) * 0.05); }, () => {
      // 2. the handle comes forward and the beer runs
      const topWorld = () => node.parent.localToWorld(under.clone()).addScaledVector(UP, s.height * (0.06 + 0.78 * s.level));
      anim.add(2.4, (k) => {
        if (tap) tap.node.rotation.x = tr0 + Math.min(1, k * 7, (1 - k) * 7) * 0.5;
        // the beer rises first, to nine tenths; then the head grows over it as the last of it runs in
        const f = k < 0.72 ? 0.9 * (k / 0.72) : 0.9 + 0.1 * ((k - 0.72) / 0.28);
        const h = k < 0.45 ? k * 0.4 : 0.18 + ((k - 0.45) / 0.55) * 0.82;
        setLevel(s, f, h);
        stream.set(k > 0.04 && k < 0.93 ? spout : null, topWorld());
      }, () => {
        stream.set(null);
        if (tap) tap.node.rotation.x = tr0;
        setLevel(s, 1, 1);
        // 3. back to its place, full
        anim.add(0.6, (k) => { node.position.lerpVectors(under, home, k).addScaledVector(up, Math.sin(k * Math.PI) * 0.05); }, () => {
          node.position.copy(home);
          item.busy = false;
          s.full = true;
          pouring = null;
          filled++;
          say(`<b>${what}</b>, full. ${actionNote('bier', 'pint', `Pints pulled tonight: <b>${filled}</b>. A Helles, with a proper head of foam.`, { n: filled, name: item.info.name }, { done: true })} <em>Click two full glasses to clink them.</em>`);
          const next = queue.shift();
          if (next) pour(next);
          else if (s.then) { const f = s.then; s.then = null; f(); }
        });
      });
    });
  }

  function select(s, on) {
    const node = s.item.node;
    const up = worldDirToParent(node, UP);
    const from = node.position.clone(), to = s.rest.p.clone().addScaledVector(up, on ? 0.045 : 0);
    s.item.busy = true;
    items.release(s.item);
    anim.add(0.25, (k) => node.position.lerpVectors(from, to, k), () => { s.item.busy = false; });
    selected = on ? s : null;
  }

  /** Two full glasses meet over the counter: clink, Prost. */
  function clink(a, b) {
    if (clinking) return;
    clinking = true;
    selected = null;
    const A = a.item.node, B = b.item.node;
    [a, b].forEach((s) => { items.release(s.item); s.item.busy = true; });
    const pa = A.parent.localToWorld(a.rest.p.clone()), pb = B.parent.localToWorld(b.rest.p.clone());
    const mid = pa.clone().add(pb).multiplyScalar(0.5).addScaledVector(front, 0.12);
    const dir = pb.clone().sub(pa).setY(0).normalize();
    const gap = (a.radius + b.radius) * 0.92;
    const ta = mid.clone().addScaledVector(dir, -gap / 2).addScaledVector(UP, 0.16);
    const tb = mid.clone().addScaledVector(dir, gap / 2).addScaledVector(UP, 0.16);
    const tilt = new THREE.Vector3().crossVectors(UP, dir).normalize();
    const la = worldToParent(A, ta), lb = worldToParent(B, tb);
    const qa = a.rest.q.clone(), qb = b.rest.q.clone();
    const axA = worldDirToParent(A, tilt).normalize(), axB = worldDirToParent(B, tilt).normalize();
    const pose = (k, lean) => {
      A.position.lerpVectors(a.rest.p, la, k);
      B.position.lerpVectors(b.rest.p, lb, k);
      A.quaternion.copy(qa).premultiply(new THREE.Quaternion().setFromAxisAngle(axA, -lean));
      B.quaternion.copy(qb).premultiply(new THREE.Quaternion().setFromAxisAngle(axB, lean));
    };
    anim.add(0.7, (k) => pose(k, 0.22 * k), () => {
      sfx('clink');
      const lines = toastLines('bier');
      crowdSay(lines[(Math.random() * lines.length) | 0], place.center.clone().setY(0), 12);
      say(`<b>Prost!</b> ${esc(a.item.info.name || 'A glass')} and ${esc(lowerFirst(b.item.info.name) || 'a glass')} meet over the counter. ${actionNote('bier', 'prost', 'Everyone nearby raises a glass.')}`);
      // a little bounce back from the knock, then home
      anim.add(0.25, (k) => pose(1 - Math.sin(k * Math.PI) * 0.06, 0.22), () => {
        anim.add(0.8, (k) => pose(1 - k, 0.22 * (1 - k)), () => {
          restore(A, a.rest); restore(B, b.rest);
          a.item.busy = b.item.busy = false;
          clinking = false;
        }, 0.5);
      });
    });
  }

  function clickGlass(item) {
    const s = stateOf(item);
    if (item.busy && pouring !== s) return;
    if (!s.full || s.upside) { pour(item); return; }
    // a full glass: pick it up for a toast, or clink with the one already raised
    if (selected === s) { select(s, false); say('Put down. Click two full glasses to clink them.'); return; }
    if (selected && selected.full) { const other = selected; select(other, false); clink(other, s); return; }
    const others = [...glasses.values()].filter((g) => g.full && g !== s);
    select(s, true);
    say(others.length
      ? `${esc(item.info.name || 'A full glass')}, raised. Click another full glass to clink.`
      : `${esc(item.info.name || 'A full glass')}, raised. Click an empty glass to fill a second one, then clink.`);
  }

  function clickTap(item) {
    // the tap pours into the next empty glass of its beer, or any empty glass
    const empty = [...glasses.values()].filter((g) => !g.full && !g.upside && !g.item.busy);
    const s = empty.find((g) => g.tap === item) || empty[0] || counter.find((g) => !g.item.busy);
    if (s) pour(s.item, { fresh: s.full });
  }

  // ---------- the panel buttons ----------
  function pullPint() {
    const all = counter.length ? counter : [...glasses.values()];
    const empty = all.find((g) => !g.full && !g.item.busy);
    if (empty) return pour(empty.item);
    // every glass is full: the oldest one is served, and a fresh one is pulled in its place
    const s = all.find((g) => !g.item.busy);
    if (s) pour(s.item, { fresh: true });
    else return false;
    return true;
  }
  function prost() {
    const full = counter.filter((g) => g.full && !g.item.busy);
    if (full.length >= 2) return clink(full[0], full[1]);
    const empty = counter.find((g) => !g.full && !g.item.busy);
    if (!empty) return false;
    empty.then = () => prost();
    pour(empty.item);
    return true;
  }

  return {
    kinds: { glass: clickGlass, tap: clickTap },
    // an empty glass is filled under its tap: the camera looks there (a full one is clinked where it stands)
    focusOf(item) {
      if (item.kind === 'tap') return spoutOf(item).add(new THREE.Vector3(0, -0.1, 0));
      const s = glasses.get(item);
      if (s && !s.full) return spoutOf(s.tap).add(new THREE.Vector3(0, -0.12, 0));
      return null;
    },
    api: {
      beerReady: counter.length > 0,
      badFoam: () => badFoam.slice(),
      pullPint, prostBier: prost,
      glassState: (name) => { const it = [...glasses.keys()].find((i) => i.node.name === name); const s = it && glasses.get(it); return s ? { level: +s.level.toFixed(3), head: +s.head.toFixed(3), full: s.full, busy: it.busy } : null; },
    },
    retract() { if (selected) select(selected, false); },
  };
}

const lowerFirst = (s) => (s ? String(s).charAt(0).toLowerCase() + String(s).slice(1) : '');
