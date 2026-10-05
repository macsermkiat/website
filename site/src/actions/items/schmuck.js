// The ornament shop (Christbaumschmuck, docs/adr/0004): the one side stall that stays interactive. Every ornament is
// the vendor's act_orn_<kind>_<n> node with an items.json entry (`name`, `label`, `action`, a bauble's `note`):
//   ring     a glass bauble spins on its ribbon and rings its own soft note (a row of them plays a scale)
//   light    the Herrnhut star lights from inside (and a Schwibbogen candle lights the arch)
//   jaw      the nutcracker's jaw opens and cracks a nut
//   smoke    the Räuchermännchen puffs fir-scented smoke from its mouth (fx_smoke_<n>)
//   candles  the Schwibbogen's candles light one by one (act_orn_candle_<n>), and go out together
//   hang     the ornament comes off the rail and hangs on the display tree's next free hook (hook_tree_<n>);
//            clicked again it goes back to its rail. A bauble rings when clicked; the stop bar hangs it.
//   find     the Weihnachtsgurke, hidden among the green baubles: finding it gives a gentle chime and a line of
//            words in the shop
// Round 9 (ADR 0004 revision) is arriving from the vendor while round 8 closes: its glass harmonica
// (act_orn_harmonica_<n>, action "harmonica") rings like the baubles, and its mirror ball (action "dive") spins and
// rings a low note until the round-9 camera dive lands. The stop bar offers only what the shop's set has.
// The sounds are synthesised in the market's own stall-sound bus (audio/sfx.js), quiet and warm.
import * as THREE from 'three';
import { boxOf, rest, restore, worldDirToParent, UP } from './common.js';
import { createEmitter } from '../effects.js';
import { label } from '../../world/text.js';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const NOTES = ['C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5', 'C6', 'D6', 'E6', 'F6', 'G6', 'A6', 'B6', 'C7', 'D7', 'E7', 'F7', 'G7', 'A7', 'B7', 'C8'];
const byIndex = (a, b) => a.node.name.localeCompare(b.node.name, 'en', { numeric: true });

/** What an ornament does: items.json `action`, else its kind word (act_orn_<kind>_<n>). */
export function ornamentAction(item) {
  const a = item.info?.action || item.node.userData?.item?.action;
  if (a === 'harmonica' || a === 'dive') return 'ring';
  if (a) return String(a);
  const k = /^act_orn_([a-z]+)/i.exec(item.node.name)?.[1]?.toLowerCase();
  return { bauble: 'ring', harmonica: 'ring', mirrorball: 'ring', herrnhut: 'light', nutcracker: 'jaw', smoker: 'smoke', schwibbogen: 'candles', candle: 'candles', pickle: 'find' }[k] || 'hang';
}

export function createSchmuck(ctx) {
  const { market, anim, sfx, say, items, scene, camera } = ctx;
  let place = null;
  let S = null; // the shop's parts, once its place is there

  function setup(p) {
    if (place === p || !p) return;
    place = p;
    const all = items.of('schmuck', 'orn');
    const named = (re) => all.find((i) => re.test(i.node.name)) || null;
    const baubles = all.filter((i) => /^act_orn_(bauble|harmonica)_/i.test(i.node.name)).sort(byIndex);
    const candles = all.filter((i) => /^act_orn_candle_/i.test(i.node.name)).sort(byIndex);
    const hooks = [];
    p.root.traverse((o) => { if (/^hook_tree_\d+/i.test(o.name || '')) hooks.push(o); });
    hooks.sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }));
    const fx = (() => { let f = null; p.root.traverse((o) => { if (!f && /^fx_smoke_/i.test(o.name || '')) f = o; }); return f; })();
    S = {
      all, baubles, candles, hooks,
      star: named(/^act_orn_herrnhut$/i),
      nut: named(/^act_orn_nutcracker$/i),
      jaw: named(/^act_orn_nutcracker_jaw$/i),
      smoker: named(/^act_orn_smoker$/i),
      arch: named(/^act_orn_schwibbogen$/i),
      pickle: named(/^act_orn_pickle$/i),
      fx,
      hung: new Map(), // item -> hook
      starOn: false, starK: 0, starMats: [],
      candlesOn: 0, candleTimers: [],
      smoke: null, smokeLeft: 0,
      found: false, rings: 0, selected: null,
    };
    for (const i of all) i.node.userData.live = true; // they move: never merged into the stall
    // the star's paper and its core: dark until lit (the core is not one of the market's always-on bulbs)
    if (S.star) {
      S.star.node.traverse((o) => {
        if (!o.isMesh || Array.isArray(o.material)) return;
        const core = /bulb_|core/i.test(o.material.name || '') || /core/i.test(o.name || '');
        const m = o.material.clone();
        delete m.userData.fromGlb; // the streaming graft keeps an engine-owned material
        m.name = core ? 'orn_herrnhut_core' : 'orn_herrnhut_paper';
        if (!m.emissive) m.emissive = new THREE.Color(0);
        m.emissive.set(core ? 0xffc27a : 0xffb35c);
        if (!core && m.map) m.emissiveMap = m.map;
        m.userData.litMax = core ? 7 : 1.6;
        m.userData.restGlow = core ? 0.25 : 0;
        m.emissiveIntensity = m.userData.restGlow;
        o.material = m;
        S.starMats.push(m);
      });
    }
    // the Schwibbogen's flames: out until lit
    for (const c of candles) {
      c.node.visible = false;
      c.flame = c.node.children.find((o) => o.isMesh) || c.node;
      c.r0 = rest(c.node);
    }
    if (S.fx) {
      S.smoke = createEmitter(scene, S.fx.getWorldPosition(new THREE.Vector3()), { color: 0xd8d2c8, n: 9, rise: 0.55, spread: 0.07, scale: 0.16, opacity: 0 });
      S.smoke.base = 0;
    }
    // the reward's words, ready to show over the counter
    for (const i of all) i.home = { parent: i.node.parent, ...rest(i.node) };
  }
  if (market.places.schmuck) setup(market.places.schmuck);

  // ---------- each ornament's action ----------

  /** A bauble's note: items.json `note`, else its place in the row up the scale (the mirror ball rings low). */
  function noteOf(item) {
    const n = item.info?.note || item.node.userData?.item?.note;
    if (n) return n;
    const i = S.baubles.indexOf(item);
    return i >= 0 ? NOTES[i % NOTES.length] : /mirrorball/i.test(item.node.name) ? 'G4' : 'C5';
  }

  function ring(item, { quiet = false } = {}) {
    const note = noteOf(item);
    sfx('glass', { note, pan: panOf(item.node) });
    S.rings++;
    if (!quiet) say(`${esc(item.info?.label || item.label)}: <b>${esc(note)}</b>. <em>A row of them plays a scale.</em>`);
    spin(item, 2.2, 1.5);
  }

  /** A turn on its ribbon about the vertical through its pivot, easing out, with a small swing. */
  function spin(item, dur = 2, turns = 1.5) {
    if (item.busy) return;
    items.release(item);
    item.busy = true;
    const node = item.node, r0 = rest(node);
    const ax = worldDirToParent(node, UP).normalize();
    const sw = worldDirToParent(node, new THREE.Vector3(1, 0, 0)).normalize();
    const q = new THREE.Quaternion(), q2 = new THREE.Quaternion();
    anim.add(dur, (k) => {
      const e = 1 - Math.pow(1 - k, 3);
      q.setFromAxisAngle(ax, e * turns * Math.PI * 2);
      q2.setFromAxisAngle(sw, Math.sin(k * Math.PI * 5) * 0.14 * (1 - k));
      node.quaternion.copy(r0.q).premultiply(q).premultiply(q2);
    }, () => { restore(node, r0); item.busy = false; items.settle(item); if (item.hangNext) { item.hangNext = false; hang(item); } });
  }

  function lightStar(on = !S.starOn) {
    S.starOn = on;
    sfx(on ? 'lamp' : 'puff');
    if (S.star) spin(S.star, 1.6, 0.25);
    say(on ? `${esc(S.star?.info?.label || 'Herrnhuter Stern')}: <b>lit</b>. ${esc(S.star?.info?.detail || 'A paper star that lights from inside.')}` : 'The Herrnhut star goes dark.');
  }

  function jaw() {
    const J = S.jaw;
    if (!J || J.busy) { sfx('crack'); return; }
    J.busy = true;
    const node = J.node, r0 = rest(node);
    const ax = new THREE.Vector3(1, 0, 0);
    const q = new THREE.Quaternion();
    sfx('crack');
    // open, hold for the nut, and close on it
    anim.add(0.28, (k) => { node.quaternion.copy(r0.q).multiply(q.setFromAxisAngle(ax, -0.5 * k)); }, () => {
      anim.add(0.32, (k) => { node.quaternion.copy(r0.q).multiply(q.setFromAxisAngle(ax, -0.5 * (1 - k))); }, () => { restore(node, r0); J.busy = false; }, 0.35);
    });
    if (motion().reduced) { restore(node, r0); J.busy = false; }
    S.cracks = (S.cracks || 0) + 1;
    say(`${esc(S.nut?.info?.label || 'Nussknacker')}: his jaw opens and <b>cracks</b> a walnut. Nuts cracked tonight: <b>${S.cracks}</b>.`);
  }

  function smoke() {
    if (!S.smoke) { sfx('puff'); say('The Räuchermännchen has no incense cone in it yet.'); return; }
    S.smokeLeft = 6;
    S.smoke.boost = 1.4;
    sfx('match');
    setTimeout(() => sfx('puff'), 700);
    S.puffs = (S.puffs || 0) + 1;
    say(`${esc(S.smoker?.info?.label || 'Räuchermännchen')}: a cone of incense is lit, and fir-scented smoke <b>curls from his mouth</b>.`);
  }

  function candles() {
    S.candleTimers.forEach(clearTimeout);
    S.candleTimers = [];
    if (S.candlesOn) {
      // all out with one breath
      S.candlesOn = 0;
      for (const c of S.candles) c.node.visible = false;
      sfx('puff');
      say(`${esc(S.arch?.info?.label || 'Schwibbogen')}: the candles go out.`);
      return;
    }
    const n = S.candles.length;
    if (!n) { say('This Schwibbogen has no candles yet.'); return; }
    say(`${esc(S.arch?.info?.label || 'Schwibbogen')}: its <b>${n} candles</b> light one by one.`);
    const gap = motion().reduced ? 0 : 420;
    S.candles.forEach((c, i) => {
      const go = () => {
        c.node.visible = true;
        S.candlesOn = i + 1;
        c.litAt = T;
        if (i % 2 === 0 || gap === 0) sfx('match');
      };
      if (!gap) go(); else S.candleTimers.push(setTimeout(go, i * gap));
    });
  }

  // ---------- hanging on the display tree ----------

  function freeHook() {
    const used = new Set(S.hung.values());
    return S.hooks.find((h) => !used.has(h)) || null;
  }

  function hang(item) {
    if (!item) return false;
    if (S.hung.has(item)) { unhang(item); return true; }
    // still spinning from a ring: it goes up as soon as it comes to rest
    if (item.busy) { item.hangNext = true; say(`${esc(item.info?.label || item.label)} goes on the tree as soon as it stops spinning.`); return true; }
    let hook = freeHook();
    if (!hook) {
      // the tree is full: the first one hung goes back to its rail to make room
      const [first] = S.hung.keys();
      if (first) unhang(first, { quick: true });
      hook = freeHook();
    }
    if (!hook) { say('There is no display tree here yet.'); return false; }
    items.release(item);
    item.busy = true;
    S.hung.set(item, hook);
    const node = item.node;
    const from = node.getWorldPosition(new THREE.Vector3());
    hook.attach(node); // keeps its world pose; now it moves in the hook's frame
    const p0 = node.position.clone();
    const up = worldDirToParent(node, UP).multiplyScalar(0.18);
    anim.add(0.9, (k) => { node.position.copy(p0).multiplyScalar(1 - k).addScaledVector(up, Math.sin(k * Math.PI)); }, () => {
      node.position.set(0, 0, 0);
      item.busy = false;
      settleSwing(item);
    });
    if (motion().reduced) node.position.set(0, 0, 0);
    sfx(ornamentAction(item) === 'ring' ? 'glass' : 'chime', { note: item.info?.note || 'G5', pan: panOf(node) });
    void from;
    say(`${esc(item.info?.label || item.label)} <b>hangs on the tree</b> (${S.hung.size} of ${S.hooks.length} hooks). <em>Click it again to put it back on the rail.</em>`);
    return true;
  }

  function unhang(item, { quick = false } = {}) {
    const h = item.home;
    if (!h) return;
    S.hung.delete(item);
    items.release(item);
    item.busy = true;
    const node = item.node;
    h.parent.attach(node);
    const p0 = node.position.clone(), q0 = node.quaternion.clone();
    const done = () => { restore(node, h); item.busy = false; items.settle(item); if (item.hangNext) { item.hangNext = false; hang(item); } };
    if (quick) { done(); return; }
    anim.add(0.8, (k) => { node.position.lerpVectors(p0, h.p, k); node.quaternion.slerpQuaternions(q0, h.q, k); }, done);
    if (!quick) say(`${esc(item.info?.label || item.label)} goes back on the rail.`);
  }

  function settleSwing(item) {
    const node = item.node, r0 = rest(node);
    const ax = worldDirToParent(node, new THREE.Vector3(1, 0, 0)).normalize();
    const q = new THREE.Quaternion();
    item.busy = true;
    anim.add(1.4, (k) => { node.quaternion.copy(r0.q).premultiply(q.setFromAxisAngle(ax, Math.sin(k * Math.PI * 4) * 0.16 * (1 - k))); }, () => { restore(node, r0); item.busy = false; });
  }

  // ---------- the pickle ----------

  let reward = null, rewardLeft = 0;
  function find(item) {
    const first = !S.found;
    S.found = true;
    sfx('reward');
    spin(item, 1.2, 0.5);
    say(`<b>${esc(item.info?.label || 'Weihnachtsgurke')}</b>. ${esc(item.info?.detail || 'You found the Christmas pickle!')}`);
    showReward(first ? 'Du hast die Weihnachtsgurke gefunden! Ein Extrageschenk für dich.' : 'Die Gurke! Gut gefunden.');
    document.documentElement.dataset.pickle = 'found';
  }

  /** A line of words in the shop, over the counter, that rises a little and goes after a few seconds. */
  function showReward(text) {
    reward?.removeFromParent();
    const slot = place.nodes.slots.slot_counter || place.holder;
    const g = label(text, { font: 'sc', size: 0.075, color: '#ffe2a8', glow: 0.9 });
    g.name = 'engine_pickle_reward';
    const at = slot.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.95, 0));
    // face the shop's own view (the visitor), upright
    const view = place.nodes.camView ? place.nodes.camView.getWorldPosition(new THREE.Vector3()) : camera.position.clone();
    g.position.copy(at);
    g.lookAt(view.x, at.y, view.z);
    g.userData.y0 = at.y;
    g.scale.setScalar(0.01);
    scene.add(g);
    reward = g;
    rewardLeft = 7;
  }

  // ---------- clicks ----------

  function click(item) {
    if (!S) setup(market.places.schmuck);
    if (!S) return;
    // a hung ornament clicked again goes home, whatever it is
    if (S.hung.has(item)) { unhang(item); return; }
    const a = ornamentAction(item);
    if (item.info?.hangable || a === 'hang') S.selected = item;
    if (a === 'ring') ring(item);
    else if (a === 'light' && /candle/i.test(item.node.name)) candles();
    else if (a === 'light') lightStar();
    else if (a === 'jaw') jaw();
    else if (a === 'smoke') smoke();
    else if (a === 'candles') candles();
    else if (a === 'find') find(item);
    else hang(item);
  }

  /** A row of baubles rung in turn: their notes run up a scale. */
  function ringScale() {
    if (!S) return;
    const row = S.baubles.filter((b) => !S.hung.has(b)).slice(0, 16);
    if (!row.length) { say('The baubles are all on the tree.'); return; }
    const gap = 0.24;
    row.forEach((b, i) => setTimeout(() => ring(b, { quiet: true }), i * gap * 1000));
    say(`The <b>${row.length} glass baubles</b> on the front rail, one after another: each rings its own note, so the row plays a scale.`);
  }

  /** The stop bar's "hang": the last ornament clicked, or the next one still on its rail. */
  function hangSelected() {
    if (!S) return;
    const pick = S.selected && !S.hung.has(S.selected) ? S.selected : S.all.find((i) => (i.info?.hangable || ornamentAction(i) === 'hang') && !S.hung.has(i) && ornamentAction(i) !== 'find');
    S.selected = null;
    if (!pick) { say('Every ornament that can hang is on the tree.'); return; }
    hang(pick);
  }

  let hinted = false;
  function lookForPickle() {
    if (!S?.pickle) { say('No pickle in this shop tonight.'); return; }
    if (!hinted && !S.found) { hinted = true; say('Somewhere among the <b>green baubles</b> on the inner rail hangs a glass gherkin. <em>Look closely, or press again to be shown.</em>'); return; }
    find(S.pickle);
    ctx.focus?.(S.pickle);
  }

  function panOf(node) {
    const p = node.getWorldPosition(new THREE.Vector3()).project(camera);
    return Math.max(-0.8, Math.min(0.8, p.x * 0.8));
  }
  const motion = () => ctx.motion || { reduced: false };

  let T = 0;
  const self = {
    kinds: { orn: click },
    addPlace(p) { if (p.id === 'schmuck') setup(p); },
    /** The stop bar's buttons at the ornament shop. */
    actsList: () => [
      { key: 'ring', label: S?.baubles.some((b) => /harmonica/i.test(b.node.name)) ? 'Play the glass harmonica' : 'Ring the baubles', fn: ringScale, has: () => S.baubles.length > 0 },
      { key: 'star', label: 'Light the Herrnhut star', fn: () => S && lightStar(), has: () => !!S.star },
      { key: 'nut', label: 'Crack a nut', fn: () => S && jaw(), has: () => !!(S.jaw || S.nut) },
      { key: 'smoke', label: 'Light the Räuchermännchen', fn: () => S && smoke(), has: () => !!S.smoker },
      { key: 'candles', label: 'Light the Schwibbogen', fn: () => S && candles(), has: () => S.candles.length > 0 },
      { key: 'hang', label: 'Hang an ornament on the tree', fn: hangSelected, has: () => S.hooks.length > 0 && S.all.some((i) => i.info?.hangable || ornamentAction(i) === 'hang') },
      { key: 'pickle', label: 'Look for the pickle', fn: lookForPickle, has: () => !!S.pickle },
    ].filter((a) => !S || a.has()),
    api: {
      schmuckActs: () => self.actsList(),
      /** For tests: the shop's state. */
      schmuck: () => (S ? {
        baubles: S.baubles.length, hooks: S.hooks.length, hung: [...S.hung.keys()].map((i) => i.node.name),
        star: { on: S.starOn, glow: +(S.starMats[0]?.emissiveIntensity ?? 0).toFixed(3) },
        candles: { lit: S.candles.filter((c) => c.node.visible).length, of: S.candles.length },
        smoke: { left: +S.smokeLeft.toFixed(2), opacity: +(S.smoke?.base ?? 0).toFixed(3) },
        jaw: S.jaw ? { busy: !!S.jaw.busy, angle: +(2 * Math.acos(Math.min(1, Math.abs(S.jaw.node.quaternion.dot(S.jaw.home.q))))).toFixed(3) } : null,
        pickle: { found: S.found, reward: !!reward && reward.parent != null, text: reward?.userData.text || null },
        rings: S.rings, cracks: S.cracks || 0,
        has: Object.fromEntries(self.actsList().map((x) => [x.key, true])),
      } : null),
      ornamentNote: (name) => { const it = S?.all.find((i) => i.node.name === name); return it ? noteOf(it) : null; },
      /** For tests: the baubles' node names, in order along the row. */
      baubleNames: () => (S ? S.baubles.map((b) => b.node.name) : []),
    },
    retract() {
      if (!S) return;
      S.selected = null;
    },
    update(dt, t, still) {
      T = t;
      if (!S) return;
      // the star's glow eases up or down
      const want = S.starOn ? 1 : 0;
      S.starK += (want - S.starK) * (still ? 1 : Math.min(1, dt * 3));
      const flick = S.starOn && !still ? 1 + Math.sin(t * 7.3) * 0.02 + Math.sin(t * 2.1) * 0.03 : 1;
      for (const m of S.starMats) m.emissiveIntensity = THREE.MathUtils.lerp(m.userData.restGlow, m.userData.litMax, S.starK) * flick;
      // candle flames flicker
      if (!still) for (const c of S.candles) if (c.node.visible) { const s = 1 + Math.sin(t * 13 + c.node.id) * 0.06 + Math.sin(t * 5.7 + c.node.id * 3) * 0.05; c.node.scale.set(1, s, 1); }
      // the smoker's puffs fade after a few seconds
      if (S.smoke) {
        if (S.smokeLeft > 0) S.smokeLeft = Math.max(0, S.smokeLeft - dt);
        const target = S.smokeLeft > 0 ? 0.42 : 0;
        S.smoke.base += (target - S.smoke.base) * Math.min(1, dt * (target ? 2.5 : 0.8));
        if (still && S.smokeLeft > 0) S.smoke.base = 0.42;
        S.smoke.update(dt, still);
      }
      // the reward's words rise in, stay, and shrink away
      if (reward) {
        rewardLeft -= dt;
        const k = rewardLeft > 6.4 ? (7 - rewardLeft) / 0.6 : rewardLeft < 0.6 ? Math.max(0, rewardLeft / 0.6) : 1;
        reward.scale.setScalar(still ? (rewardLeft > 0 ? 1 : 0.01) : Math.max(0.01, k));
        reward.position.y = reward.userData.y0 + (still ? 0 : (7 - rewardLeft) * 0.015);
        if (rewardLeft <= 0) { reward.removeFromParent(); reward = null; }
      }
    },
  };
  return self;
}

export { boxOf };
