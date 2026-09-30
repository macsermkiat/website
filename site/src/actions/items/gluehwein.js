// The Glühwein stand: click a mug and the ladle fills it from the copper pot, with steam; click a wine bottle
// and it is turned to show its label, with a short tasting note; a wine glass is swirled; the pot's lid lifts.
import * as THREE from 'three';
import { boxOf, meshByMaterial, rest, restore, worldToParent, worldDirToParent, rotateAbout, createStream, createSurface, WINE, UP, esc } from './common.js';
import { createEmitter } from '../effects.js';
import { createWorldTag } from '../util.js';
import { actionNote, SECTIONS } from '../../content.js';

// Tasting notes for the vendor's bottles when neither items.json (`note`) nor the writer (about.md front
// matter `bottles:`) gives one. Matched on the bottle's name, first match wins.
const TASTING = [
  [/eiswein/i, 'Pressed from grapes frozen on the vine: apricot, honey and a bright, clean acidity.'],
  [/spätlese/i, 'Late-picked Riesling: ripe peach and honey, still lifted by its acidity.'],
  [/feinherb/i, 'Off-dry Riesling: green apple, lime and wet slate.'],
  [/riesling trocken|riesling, dry/i, 'Dry and crisp: lemon zest, white peach and a flinty finish.'],
  [/white glühwein|weißer glühwein|from riesling/i, 'Mulled Riesling with vanilla, star anise and a little honey.'],
  [/spätburgunder|pinot noir/i, 'Pinot Noir: sour cherry, a little smoke, soft tannins.'],
  [/dornfelder halbtrocken/i, 'Deep purple and just off-dry: plum and blackberry.'],
  [/dornfelder/i, 'Dark berries, dry, with a hint of oak.'],
  [/bocksbeutel/i, 'Silvaner in the flat, round Bocksbeutel of Franken: pear, fresh hay, a mineral edge.'],
  [/silvaner/i, 'Quiet and dry: pear, green herbs and a mineral edge.'],
  [/winzer-glühwein|glühwein, red/i, 'The stall’s own mulled red: clove, cinnamon, star anise and orange peel.'],
  [/blueberry|heidelbeer/i, 'Mulled blueberry wine: jammy, sweet and very purple.'],
  [/rum/i, 'Dark rum, for a Schuss in your mug.'],
  [/kinderpunsch|alcohol-free/i, 'Hot punch with no alcohol: apple, grape, cinnamon and orange.'],
];

export function tastingNote(info) {
  if (info.note) return String(info.note);
  if (info.tasting) return String(info.tasting);
  const w = SECTIONS.glueh?.meta?.bottles;
  const name = String(info.name || '');
  if (w && typeof w === 'object') {
    for (const [k, v] of Object.entries(w)) if (typeof v === 'string' && v.trim() && name.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return TASTING.find(([re]) => re.test(name))?.[1] || 'A bottle from the vintner’s shelf.';
}

export function createGluehwein(ctx) {
  const { market, anim, scene, sfx, say, items, camera, overlay } = ctx;
  const place = market.places.glueh;
  if (!place) return {};
  const tag = createWorldTag(overlay, 'booktag itemtag');
  const stream = createStream(scene, WINE, 0.0055);
  const front = new THREE.Vector3(Math.sin(place.ry), 0, Math.cos(place.ry));
  const ladle = items.of('glueh', 'ladle')[0] || null;
  const pot = items.of('glueh', 'kettle')[0] || items.of('glueh', 'pot')[0] || null;
  const lid = items.of('glueh', 'lid')[0] || null;
  if (ladle) items.own(ladle);
  const mugs = new Map();
  const steams = [];
  let ladling = null, poured = 0;
  const queue = [];

  function mugState(item) {
    let s = mugs.get(item);
    if (s) return s;
    const node = item.node;
    const liquid = meshByMaterial(node, /liquid|wine/i);
    const name = String(item.info.name || '');
    s = {
      item, liquid, rest: rest(node), surface: null,
      upside: /upside down/i.test(name),
      full: !!liquid && !/upside down/i.test(name),
      liquidY: liquid?.position.y ?? 0,
    };
    mugs.set(item, s);
    return s;
  }
  for (const m of items.of('glueh', 'mug')) mugState(m);

  /** A mug's wine at level f: the vendor's own wine surface lowered into the mug, or one made for it. */
  function level(s, f) {
    if (s.liquid) {
      const h = boxOf(s.item.node, s.item.node);
      const depth = (h.max.y - h.min.y) * 0.7;
      s.liquid.position.y = s.liquidY - (1 - f) * depth;
      s.liquid.visible = f > 0.02;
      return;
    }
    s.surface ||= createSurface(s.item.node, WINE, { fill: 0.86, radius: 0.36 });
    s.surface.level(f);
  }

  function flipUp(s, done) {
    // a mug drying upside down on the tray is turned the right way up first
    const node = s.item.node;
    const r0 = rest(node);
    const size = boxOf(node).getSize(new THREE.Vector3());
    const axis = worldDirToParent(node, new THREE.Vector3().crossVectors(UP, front).normalize()).normalize();
    const lift = worldDirToParent(node, UP);
    const qf = new THREE.Quaternion().setFromAxisAngle(axis, Math.PI), qi = new THREE.Quaternion();
    anim.add(0.6, (k) => {
      node.quaternion.copy(r0.q).premultiply(new THREE.Quaternion().slerpQuaternions(qi, qf, k));
      node.position.copy(r0.p).addScaledVector(lift, size.y * k + Math.sin(k * Math.PI) * 0.07);
    }, () => { s.upside = false; s.rest = rest(node); done(); });
  }

  /** The ladle dips into the pot, carries wine over the mug and pours; the level rises and it steams. */
  function fill(item) {
    const s = mugState(item);
    if (ladling) { if (ladling !== s && !queue.includes(item)) queue.push(item); return; }
    ladling = s;
    items.release(item);
    item.busy = true;
    item.keepOwn = true;
    if (s.upside) { flipUp(s, () => { ladling = null; fill(item); }); return; }
    level(s, s.full ? 0.35 : 0); // a full mug has been drunk from: topped up
    const top = boxOf(item.node).max.y;
    const mugTop = item.node.getWorldPosition(new THREE.Vector3()).setY(top);
    sfx('pour');
    say(`The ladle goes into the copper pot for the <b>${esc(lower(item.info.name).replace(/, (full and steaming|upside down to dry)$/, '') || 'mug')}</b>…`);
    if (lid) { const l = lid.node, r0 = l.rotation.x; anim.add(1.4, (k) => { l.rotation.x = r0 - Math.sin(k * Math.PI) * 0.6; }); }
    const done = () => {
      level(s, 1);
      s.full = true;
      item.busy = false;
      ladling = null;
      poured++;
      steamOver(s, mugTop);
      say(`<b>${esc(String(item.info.name || 'Your mug').replace(/, (full and steaming|upside down to dry)$/, ''))}</b>, filled. ${actionNote('glueh', 'pour', `Mugs poured tonight: <b>${poured}</b>. Red wine, cinnamon, clove and orange. Careful, it’s hot.`, { n: poured, name: item.info.name })}`);
      const next = queue.shift();
      if (next) fill(next);
      else if (s.then) { const f = s.then; s.then = null; f(); }
    };
    if (!ladle) {
      // no ladle in this stall (a stand-in): the wine simply rises
      anim.add(1.2, (k) => level(s, (s.full ? 0.35 : 0) + k * (1 - (s.full ? 0.35 : 0))), done);
      return;
    }
    const L = ladle.node;
    const r0 = rest(L);
    const box0 = boxOf(L);
    // the bowl is the lowest part of a ladle standing in the pot
    const bowl0 = new THREE.Vector3((box0.min.x + box0.max.x) / 2, box0.min.y + 0.03, (box0.min.z + box0.max.z) / 2);
    const lift = 0.26;
    const over = mugTop.clone().add(new THREE.Vector3(0, 0.1, 0)).addScaledVector(front, -0.05);
    const shiftW = over.clone().sub(bowl0.clone().add(new THREE.Vector3(0, lift, 0)));
    const up = worldDirToParent(L, UP).multiplyScalar(lift);
    const shift = worldDirToParent(L, shiftW);
    // tip the bowl toward the mug: about the horizontal axis across the carry direction
    const carry = shiftW.clone().setY(0);
    const tiltAxis = new THREE.Vector3().crossVectors(UP, carry.lengthSq() > 1e-6 ? carry.normalize() : front).normalize();
    const start = s.full ? 0.35 : 0;
    const at = (p) => ({ p, q: r0.q });
    // 1. out of the pot
    anim.add(0.5, (k) => { L.position.copy(r0.p).addScaledVector(up, k); }, () => {
      // 2. across to the mug
      const pUp = r0.p.clone().add(up);
      anim.add(0.7, (k) => { L.position.copy(pUp).addScaledVector(shift, k); }, () => {
        const pOver = pUp.clone().add(shift);
        const bowl = bowl0.clone().add(new THREE.Vector3(0, lift, 0)).add(shiftW);
        // 3. tip and pour
        anim.add(1.5, (k) => {
          const a = Math.min(1, k * 3) * 0.95 * (k > 0.85 ? (1 - k) / 0.15 : 1);
          rotateAbout(L, at(pOver), bowl, tiltAxis, a);
          level(s, start + (1 - start) * Math.min(1, Math.max(0, (k - 0.15) / 0.7)));
          stream.set(k > 0.15 && k < 0.88 ? bowl.clone().add(new THREE.Vector3(0, -0.02, 0)) : null, mugTop.clone().add(new THREE.Vector3(0, -0.03, 0)));
        }, () => {
          stream.set(null);
          restore(L, at(pOver));
          // 4. back into the pot
          anim.add(0.55, (k) => { L.position.lerpVectors(pOver, pUp, k); }, () => {
            anim.add(0.45, (k) => { L.position.lerpVectors(pUp, r0.p, k); }, () => restore(L, r0));
          });
          done();
        });
      });
    });
  }

  function steamOver(s, at) {
    const e = createEmitter(scene, at.clone().add(new THREE.Vector3(0, 0.02, 0)), { color: 0xf2eee8, n: 6, rise: 0.55, spread: 0.06, scale: 0.16, opacity: 0.4 });
    e.boost = 1.5;
    e.left = 30;
    steams.push(e);
  }

  // ---------- bottles ----------
  let shown = null; // { item, s, left }
  function bottle(item) {
    if (item.busy) return;
    if (shown?.item === item) { putBack(); return; }
    if (shown) putBack();
    items.release(item);
    item.busy = true;
    item.keepOwn = true;
    const node = item.node;
    const r0 = rest(node);
    const size = boxOf(node).getSize(new THREE.Vector3());
    // toward the visitor (the camera), off the shelf, a little up; turned all the way round so the label
    // passes the eye, ending face-on
    const worldPos = node.getWorldPosition(new THREE.Vector3());
    const toCam = camera.position.clone().sub(worldPos).setY(0).normalize();
    const out = worldDirToParent(node, toCam.clone().multiplyScalar(0.12).add(new THREE.Vector3(0, 0.03 + size.y * 0.05, 0)));
    const spin = worldDirToParent(node, UP).normalize();
    const tiltAx = worldDirToParent(node, new THREE.Vector3().crossVectors(UP, toCam).normalize()).normalize();
    const set = (k, turn) => {
      node.position.copy(r0.p).addScaledVector(out, k);
      node.quaternion.copy(r0.q)
        .premultiply(new THREE.Quaternion().setFromAxisAngle(spin, turn))
        .premultiply(new THREE.Quaternion().setFromAxisAngle(tiltAx, -0.22 * k));
    };
    sfx('clink');
    const note = tastingNote(item.info);
    say(actionNote('glueh', 'bottle', `<b>${esc(item.info.name || 'A bottle')}</b><br>${esc(note)}`, { name: item.info.name, note }));
    tag.show(shortName(item.info.name), node);
    anim.add(0.5, (k) => set(k, 0), () => {
      anim.add(2.2, (k) => set(1, k * Math.PI * 2), () => { set(1, 0); item.busy = false; });
    });
    shown = { item, set, left: 10 };
  }
  function putBack() {
    if (!shown) return;
    const { item, set } = shown;
    shown = null;
    tag.hide();
    item.busy = true;
    anim.add(0.45, (k) => set(1 - k, 0), () => { item.busy = false; item.keepOwn = false; items.settle(item); });
  }

  function wineglass(item) {
    if (item.busy) return;
    items.release(item);
    item.busy = true;
    const node = item.node, r0 = rest(node);
    const up = worldDirToParent(node, UP).normalize();
    const side = worldDirToParent(node, front).normalize();
    anim.add(1.6, (k) => {
      // swirled on the counter: a small circle of tilt
      const a = Math.sin(k * Math.PI) * 0.12;
      const ax = side.clone().applyAxisAngle(up, k * Math.PI * 6);
      node.quaternion.copy(r0.q).premultiply(new THREE.Quaternion().setFromAxisAngle(ax, a));
    }, () => { restore(node, r0); item.busy = false; items.settle(item); });
    sfx('clink');
    say(`${esc(item.info.name || 'A glass of wine')}, swirled. ${/riesling/i.test(item.info.name || '') ? 'Lime and slate on the nose.' : /spätburgunder/i.test(item.info.name || '') ? 'Cherry and a little smoke.' : 'Clean and ready for the next pour.'}`);
  }

  function kettle() {
    if (lid) { const l = lid.node, r0 = l.rotation.x; anim.add(1.6, (k) => { l.rotation.x = r0 - Math.sin(k * Math.PI) * 0.7; }); }
    steamBoost();
    sfx('pour');
    say('The copper kettle: red wine kept hot, never boiling, with cinnamon, cloves, star anise and orange.');
  }
  let potSteam = null;
  function steamBoost() { if (potSteam) potSteam.boost = 1.5; }

  // ---------- the panel buttons ----------
  const counterMugs = () => [...mugs.values()].filter((s) => /counter|tray/i.test(s.item.info.where || '') || !s.item.info.where);
  function pourNext() {
    const list = counterMugs();
    const s = list.find((m) => !m.full && !m.upside && !m.item.busy) || list.find((m) => !m.full && !m.item.busy) || list.find((m) => !m.item.busy);
    if (!s) return false;
    fill(s.item);
    return true;
  }
  let raising = false;
  function prost() {
    // two full mugs are raised together
    const full = counterMugs().filter((m) => m.full && !m.item.busy);
    if (full.length < 2) { const s = counterMugs().find((m) => !m.full && !m.item.busy); if (s) { s.then = prost; fill(s.item); } return; }
    if (raising) return;
    raising = true;
    const [a, b] = full;
    const nodes = [a, b].map((s) => { items.release(s.item); s.item.busy = true; return { s, n: s.item.node, r: rest(s.item.node), up: worldDirToParent(s.item.node, UP) }; });
    const pa = a.item.node.getWorldPosition(new THREE.Vector3()), pb = b.item.node.getWorldPosition(new THREE.Vector3());
    const mid = pa.clone().add(pb).multiplyScalar(0.5).addScaledVector(front, 0.1);
    const dir = pb.clone().sub(pa).setY(0).normalize();
    const to = [mid.clone().addScaledVector(dir, -0.055).add(new THREE.Vector3(0, 0.14, 0)), mid.clone().addScaledVector(dir, 0.055).add(new THREE.Vector3(0, 0.14, 0))].map((w, i) => worldToParent(nodes[i].n, w));
    const pose = (k) => nodes.forEach((o, i) => o.n.position.lerpVectors(o.r.p, to[i], k));
    anim.add(0.6, pose, () => {
      sfx('clink');
      anim.add(0.9, (k) => pose(1 - k), () => { nodes.forEach((o) => { restore(o.n, o.r); o.s.item.busy = false; }); raising = false; }, 0.4);
    });
  }

  // the pot keeps steaming (the stall's own steam comes from stalls.js); mugs filled here steam on their own
  return {
    kinds: { mug: fill, bottle, wineglass, kettle, pot: kettle, lid: kettle },
    // the ladle pours just above the mug
    focusOf(item) { return item.kind === 'mug' ? boxOf(item.node).getCenter(new THREE.Vector3()).add(new THREE.Vector3(0, 0.1, 0)) : null; },
    api: {
      mugsReady: counterMugs().length > 0,
      pourNext, prostMugs: prost,
      setPotSteam: (e) => { potSteam = e; },
      mugState: (name) => { const it = [...mugs.keys()].find((i) => i.node.name === name); const s = it && mugs.get(it); return s ? { full: s.full, upside: s.upside, busy: it.busy, ladle: ladle ? ladle.node.position.toArray().map((v) => +v.toFixed(3)) : null } : null; },
      shownBottle: () => shown?.item.node.name || null,
    },
    retract() { putBack(); },
    update(dt, t, still) {
      if (camera) tag.update(camera);
      if (shown && !shown.item.busy && (shown.left -= dt) <= 0) putBack();
      for (let i = steams.length - 1; i >= 0; i--) {
        const e = steams[i];
        e.update(dt, still);
        e.left -= dt;
        e.base = 0.4 * Math.min(1, e.left / 8);
        if (e.left <= 0) { e.dispose?.(); steams.splice(i, 1); }
      }
    },
  };
}

const lower = (s) => (s ? String(s).charAt(0).toLowerCase() + String(s).slice(1) : '');
const shortName = (s) => String(s || 'A bottle').replace(/\s*\([^)]*\)\s*$/, '');
