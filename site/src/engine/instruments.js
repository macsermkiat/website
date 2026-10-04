// The band's instruments (instr_<player>.glb from the ride builder) go on the bandstand's slot_<player> empties,
// each with a player figure where the instrument's origin says the player stands or sits.
// Any placed model with slot_sax / slot_piano / slot_bass / slot_drums gets them, so a new bandstand needs no code.
import * as THREE from 'three';
import { loadGlb } from './loader.js';
import { liteVariant, modelExists } from '../layout.js';
import { buildPerson } from '../standins/people.js';
import { rng } from '../standins/kit.js';
import { crowdMusicians } from '../crowd.js';

export const PLAYERS = ['sax', 'piano', 'bass', 'drums'];
const SEATED = { piano: true, drums: true };

/** placed: [{ entry, root, source }]. Returns how many instruments were placed; never throws. */
export async function placeInstruments(placed, scanNodes, { lite, manager, warn }) {
  let n = 0;
  const r = rng(77);
  await Promise.all(placed.map(async (p) => {
    if (p.source === 'standin') return;
    const slots = scanNodes(p.root).slots;
    await Promise.all(PLAYERS.map(async (k) => {
      const slot = slots[`slot_${k}`];
      if (!slot) return;
      const full = `instr_${k}.glb`;
      if (!modelExists(full)) return;
      const file = (lite && liteVariant(full)) || full;
      try {
        const obj = await loadGlb(file, manager);
        obj.name = `instrument_${k}`;
        slot.add(obj);
        // the player: the instrument's origin is where they stand (sax, bass) or sit (piano bench, drum throne).
        // The organizer's animated musician when crowd.json has one, else a stand-in figure.
        const person = (await organizerMusician(k, lite, manager, warn)) || standinMusician(r, k);
        person.name = `musician_${k}`;
        person.traverse((o) => { if (o.isMesh) { o.castShadow = !lite; o.receiveShadow = false; } });
        slot.add(person);
        // the band on a break: the tenor rests on its floor stand (instr_sax_stand, same origin) while the
        // player rests, and goes back into his hands when the band plays (actions/band.js). Only with the
        // organizer's player: the stand-in figure always holds the sax.
        if (k === 'sax' && person.userData.musician?.play && person.userData.musician?.rest && modelExists('instr_sax_stand.glb')) {
          const sf = (lite && liteVariant('instr_sax_stand.glb')) || 'instr_sax_stand.glb';
          try {
            const stand = await loadGlb(sf, manager);
            stand.name = 'instrument_sax_stand';
            slot.add(stand);
            obj.userData.live = stand.userData.live = true; // they toggle: never merged into the static mesh
            stand.visible = false;
            person.userData.musician.swap = { held: obj, stand };
          } catch (e) { warn(`${p.entry.id}: could not load ${sf} (${e?.message || e}).`); }
        }
        n++;
      } catch (e) {
        warn(`${p.entry.id}: could not load ${file} (${e?.message || e}).`);
      }
    }));
  }));
  return n;
}

function standinMusician(r, k) {
  const person = buildPerson(r, { seated: !!SEATED[k], arms: 'play' });
  if (SEATED[k]) person.position.y = 0.2;
  return person;
}

/** crowd.json musicians: a skinned figure with "play" and "rest" clips; the band switches between them. */
async function organizerMusician(k, lite, manager, warn) {
  const m = crowdMusicians().find((x) => x.slot === `slot_${k}`);
  if (!m) return null;
  const file = (lite && liteVariant(m.model)) || m.model;
  if (!modelExists(file)) return null;
  try {
    const g = await loadGlb(file, manager);
    const clips = g.userData.animations || [];
    if (clips.length) {
      const mixer = new THREE.AnimationMixer(g);
      const find = (n) => clips.find((c) => c.name === n);
      const play = find(m.clip) && mixer.clipAction(find(m.clip));
      const rest = find(m.rest) && mixer.clipAction(find(m.rest));
      (rest || play)?.play();
      mixer.setTime(Math.random() * 3);
      g.userData.musician = { mixer, play, rest, playing: false };
    }
    return g;
  } catch (e) {
    warn(`band: could not load ${file} (${e?.message || e}).`);
    return null;
  }
}
