// The panel buttons of the four section stalls: pour a mug, pull a pint, Prost, turn the sausages, a sausage in
// a bun, and pick a book. Each drives the same code as clicking the item itself (actions/items/*); a stand-in
// stall without those items falls back to the prototype's versions made here.
import * as THREE from 'three';
import { act, acts, counterLocal, toLocal, worldOf } from './util.js';
import { createEmitter } from './effects.js';
import { actionHint, actionNote, toastLines, crowdLine, itemHint as writerItemHint } from '../content.js';

const MUG = new THREE.MeshStandardMaterial({ name: 'action_mug', color: 0xa3162c, roughness: 0.35 });
const WINE = new THREE.MeshStandardMaterial({ name: 'action_wine', color: 0x4a0612, roughness: 0.1, emissive: 0x1a0205 });
// No transmission: it re-renders the whole scene every frame for one glass. A thin see-through shell reads as glass at this size.
const GLASS = new THREE.MeshStandardMaterial({ name: 'action_glass', color: 0xdfe8ee, roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.28, depthWrite: false, side: THREE.DoubleSide });
const BEER = new THREE.MeshStandardMaterial({ name: 'action_beer', color: 0xe39a1e, roughness: 0.15, emissive: 0x3a1c00, transparent: true, opacity: 0.92 });
const FOAM = new THREE.MeshStandardMaterial({ name: 'action_foam', color: 0xfff5de, roughness: 0.9 });
const mugGeo = new THREE.LatheGeometry([[0.001, 0], [0.07, 0], [0.075, 0.02], [0.075, 0.14], [0.068, 0.145], [0.064, 0.02]].map((p) => new THREE.Vector2(p[0], p[1])), 20);
const handleGeo = new THREE.TorusGeometry(0.04, 0.012, 8, 16, Math.PI);

function newMug() {
  const m = new THREE.Group();
  m.name = 'action_mug';
  m.add(new THREE.Mesh(mugGeo, MUG));
  const h = new THREE.Mesh(handleGeo, MUG);
  h.position.set(0.075, 0.075, 0); h.rotation.z = -Math.PI / 2;
  m.add(h);
  const wine = new THREE.Mesh(new THREE.CircleGeometry(0.064, 20), WINE);
  wine.position.y = 0.13; wine.rotation.x = -Math.PI / 2;
  m.add(wine);
  m.traverse((o) => { o.castShadow = true; });
  return m;
}

export function createStallActions(ctx) {
  const { market, anim, say, sfx, crowdSay, scene, items } = ctx;
  const H = items.handlers;
  const P = market.places;
  const counts = { mugs: 0, pints: 0 };
  const emitters = [];

  // ---------- Glühwein ----------
  const glueh = P.glueh;
  let steam = null;
  if (glueh) {
    const pot = act(glueh, 'act_pot') || act(glueh, 'act_pot_lid') || act(glueh, 'act_ladle');
    const c = counterLocal(glueh);
    const src = act(glueh, 'act_steam') || pot;
    const pos = src ? worldOf(glueh, src).add(new THREE.Vector3(0, src === pot ? 0.55 : 0, 0)) : worldOf(glueh, [c.x + 1.3, c.y + 0.55, c.z - 0.05]);
    steam = createEmitter(scene, pos, { color: 0xf2eee8, n: 10, rise: 1.6, spread: 0.25, scale: 0.7, opacity: 0.35 });
    emitters.push(steam);
    H.setPotSteam?.(steam);
  }
  const poured = [];
  /** A stand-in stall has no mugs of its own: a new mug is poured and set on the counter (the prototype's way). */
  function pourNewMug() {
    if (!glueh) return;
    const c = counterLocal(glueh);
    const pot = act(glueh, 'act_pot') || act(glueh, 'act_ladle');
    const lid = act(glueh, 'act_pot_lid');
    const from = pot ? toLocal(glueh, worldOf(glueh, pot)).add(new THREE.Vector3(0, 0.55, 0)) : new THREE.Vector3(c.x + 1.3, c.y + 0.55, c.z - 0.05);
    const slot = counts.mugs % 6;
    const to = new THREE.Vector3(c.x - 1.5 + slot * 0.32, c.y, c.z + 0.14);
    if (poured[slot]) poured[slot].removeFromParent();
    const m = newMug();
    m.position.copy(from);
    glueh.holder.add(m);
    poured[slot] = m;
    anim.add(1.1, (k) => { m.position.lerpVectors(from, to, k); m.position.y += Math.sin(k * Math.PI) * 0.3; });
    if (lid) { const r0 = lid.rotation.x; anim.add(0.5, (k) => { lid.rotation.x = r0 - Math.sin(k * Math.PI) * 0.35; }); }
    if (steam) steam.boost = 1;
    sfx('pour');
    counts.mugs++;
    say(actionNote('glueh', 'pour', `Cups poured tonight: <b>${counts.mugs}</b>. Red wine, cinnamon, clove and orange. Careful, it's hot.`, { n: counts.mugs }));
  }
  function pourMug() {
    if (H.mugsReady && H.pourNext()) { if (steam) steam.boost = 1; return; }
    pourNewMug();
  }
  function prost(id) {
    sfx('clink');
    const p = P[id];
    const lines = toastLines(id);
    crowdSay(lines[(Math.random() * lines.length) | 0], p ? p.center.clone().setY(0) : new THREE.Vector3(), 12);
    say(actionNote(id, 'prost', 'Everyone nearby raises a glass.'));
  }

  // ---------- Bierstand ----------
  const bier = P.bier;
  let pintBusy = false;
  const pints = [];
  /** A stand-in stall has no glasses of its own: a glass appears under the middle tap (the prototype's way). */
  function pullNewPint() {
    if (!bier || pintBusy) return;
    pintBusy = true;
    const c = counterLocal(bier);
    const taps = acts(bier, 'act_tap');
    const tap = taps[Math.min(1, taps.length - 1)] || null;
    const tapPos = tap ? toLocal(bier, worldOf(bier, tap)) : new THREE.Vector3(c.x + 0.6, c.y + 0.55, c.z - 0.1);
    const grp = new THREE.Group();
    grp.name = 'action_pint';
    grp.position.set(tapPos.x, c.y, tapPos.z);
    bier.holder.add(grp);
    const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.078, 0.062, 0.32, 24, 1, true), GLASS);
    glass.position.y = 0.16;
    grp.add(glass);
    const beer = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.058, 0.3, 24), BEER);
    beer.scale.y = 0.01; beer.position.y = 0.01;
    grp.add(beer);
    const foam = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.06, 24), FOAM);
    foam.visible = false;
    grp.add(foam);
    const r0 = tap ? tap.rotation.x : 0;
    sfx('pour');
    say(actionNote('bier', 'pint', 'Pouring… tilt, fill, then top it off with foam.'));
    anim.add(2.3, (k) => {
      if (tap) tap.rotation.x = r0 + Math.min(1, k * 8, (1 - k) * 8) * 0.55;
      const f = Math.min(1, k / 0.85);
      beer.scale.y = Math.max(0.01, f);
      beer.position.y = 0.01 + 0.15 * f;
      if (k > 0.55) { foam.visible = true; const q = (k - 0.55) / 0.45; foam.scale.y = Math.max(0.05, q); foam.position.y = 0.02 + 0.3 * f + 0.03 * q; }
    }, () => {
      if (tap) tap.rotation.x = r0;
      const slot = counts.pints % 4;
      const to = new THREE.Vector3(c.x - 1.2 + slot * 0.3, c.y, c.z + 0.2), from = grp.position.clone();
      if (pints[slot]) pints[slot].removeFromParent();
      pints[slot] = grp;
      anim.add(0.7, (k) => grp.position.lerpVectors(from, to, k), () => { pintBusy = false; });
      counts.pints++;
      say(actionNote('bier', 'pint', `Pints pulled tonight: <b>${counts.pints}</b>. A Helles, with a proper head of foam.`, { n: counts.pints }, { done: true }));
    });
  }
  const pullPint = () => (H.beerReady ? H.pullPint() : pullNewPint());
  const prostBier = () => { if (H.beerReady) H.prostBier(); else prost('bier'); };
  const prostGlueh = () => { prost('glueh'); if (H.mugsReady) H.prostMugs(); };

  // ---------- Bratwurst ----------
  function turnSausages() {
    if (H.sausagesReady) return H.turnAll();
    sfx('sizzle');
    say(actionNote('wurst', 'turn', 'Turned. Nicely browned on this side.', { n: 0 }));
  }
  function bun() {
    if (H.rollsReady && H.bunNext()) return;
    sfx('sizzle');
    say(actionNote('wurst', 'bun', 'One Bratwurst im Brötchen with mustard. <em>That will be 4 euros.</em>'));
    if (P.wurst) crowdSay(crowdLine('wurst', 'bun', 'Smells good!'), P.wurst.center.clone().setY(0), 9);
  }

  // ---------- Bücherstand ----------
  const banded = market.places.books ? !!market.places.books.root.getObjectByName('band_pick_0') : false;

  return {
    glueh: { hint: actionHint('glueh', 'Pour a cup of Glühwein, then raise it with the crowd.') + itemHint('glueh'), acts: [{ key: 'pour', label: 'Pour a cup', fn: pourMug }, { key: 'prost', label: 'Prost!', fn: prostGlueh }] },
    bier: { hint: actionHint('bier', 'Pull a pint from the middle tap.') + itemHint('bier'), acts: [{ key: 'pint', label: 'Pull a pint', fn: pullPint }, { key: 'prost', label: 'Prost!', fn: prostBier }] },
    wurst: { hint: actionHint('wurst', 'Turn the sausages on the grill.') + itemHint('wurst'), acts: [{ key: 'turn', label: 'Turn the sausages', fn: turnSausages }, { key: 'bun', label: 'One in a bun, please', fn: bun }] },
    books: { hint: actionHint('books', 'Click any spine on the shelves, or let the bookseller choose.') + (banded ? ' <em>Mac’s picks wear a red paper band.</em>' : ''), acts: [{ key: 'book', label: 'Pick a book for me', fn: () => H.pickBook?.() }] },
    update(dt, t, still) {
      emitters.forEach((e) => e.update(dt, still));
    },
  };
}

/** A line under the hint saying the goods themselves can be clicked (the writer can set it as `item_hint:`). */
function itemHint(id) {
  const fallback = {
    glueh: 'Or click a mug to have it filled, or a wine bottle to read its label.',
    bier: 'Or click a glass to fill it at the tap; click two full glasses to clink them.',
    wurst: 'Or click a sausage to turn it, or a roll to have one put in it.',
  }[id];
  return fallback ? ` <em>${writerItemHint(id, fallback)}</em>` : '';
}
