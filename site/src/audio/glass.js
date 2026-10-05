// The ornament shop's sounds (round 9, ADR 0004 revision), synthesised live like the other stall sounds and
// silenced by the mute button with them (everything ends in the market's one output):
//   strike(note, { velocity, pan })   a glass-harmonica bauble: a sine with inharmonic partials, a slow swell, a long
//                                      decay and a gentle feedback-delay room (velocity from the brush's speed)
//   chord                             the Schwibbogen's low warm chord, one voice per candle, swelling with the
//                                      wave of light and fading back when the candles go out
//   shimmer()                          the soft high ring of the mirror ball as the view passes into the glass
import { audioContext, output, isMuted } from './context.js';
import { noteHz } from './sfx.js';

let room = null, glassBus = null;

/** The harmonica's own small room: two cross-fed delays in a low-passed feedback loop. */
function ensureRoom(AC) {
  if (glassBus) return glassBus;
  glassBus = AC.createGain();
  glassBus.gain.value = 0.9;
  const warm = AC.createBiquadFilter(); warm.type = 'lowpass'; warm.frequency.value = 6500; warm.Q.value = 0.3;
  glassBus.connect(warm); warm.connect(output());
  // feedback-delay room: L 137 ms, R 193 ms, each feeding the other through a gentle low-pass
  const send = AC.createGain(); send.gain.value = 0.34;
  const dl = AC.createDelay(1), dr = AC.createDelay(1);
  dl.delayTime.value = 0.137; dr.delayTime.value = 0.193;
  const fl = AC.createBiquadFilter(), fr = AC.createBiquadFilter();
  fl.type = fr.type = 'lowpass'; fl.frequency.value = 2600; fr.frequency.value = 2300;
  const gl = AC.createGain(), gr = AC.createGain(); gl.gain.value = gr.gain.value = 0.42;
  const merge = AC.createChannelMerger(2);
  glassBus.connect(send);
  send.connect(dl); send.connect(dr);
  dl.connect(fl); fl.connect(gl); gl.connect(dr);
  dr.connect(fr); fr.connect(gr); gr.connect(dl);
  fl.connect(merge, 0, 0); fr.connect(merge, 0, 1);
  const wet = AC.createGain(); wet.gain.value = 0.55;
  merge.connect(wet); wet.connect(warm);
  room = { send };
  return glassBus;
}

// glass partials, above the harmonic series (a free glass shell), each dying faster than the one below
const PARTIALS = [[1, 1, 3.6], [2.32, 0.16, 1.6], [4.25, 0.07, 0.9], [6.63, 0.035, 0.55]];

/** A glass-harmonica note. velocity 0..1 (brush speed); pan -1..1. Returns false when silent (muted). */
export function strike(note, { velocity = 0.6, pan = 0, gain = 1 } = {}) {
  if (isMuted()) return false;
  let AC;
  try { AC = audioContext(); } catch { return false; }
  if (AC.state === 'suspended') AC.resume?.();
  const bus = ensureRoom(AC);
  const t = AC.currentTime + 0.005, f0 = typeof note === 'number' ? note : noteHz(note);
  const v = Math.max(0.15, Math.min(1, velocity));
  const p = AC.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, pan)); p.connect(bus);
  const amp = (0.05 + 0.13 * v) * gain;
  // a slow swell: a wet finger on a glass rim, not a tap (faster for a quick brush)
  const att = 0.11 - 0.06 * v;
  PARTIALS.forEach(([ratio, a, dec], i) => {
    const level = amp * a * (i === 0 ? 1 : 0.5 + v); // a harder brush is brighter
    const o = AC.createOscillator(); o.type = 'sine'; o.frequency.value = f0 * ratio;
    const g = AC.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(level, t + att * (i ? 0.6 : 1));
    g.gain.setTargetAtTime(0, t + att, dec / 4.5);
    o.connect(g); g.connect(p);
    o.start(t); o.stop(t + att + dec * 1.4);
  });
  // the shimmer of a glass harmonica: a twin a hair sharp, so the note beats slowly as it rings
  const o2 = AC.createOscillator(); o2.type = 'sine'; o2.frequency.value = f0 * 1.0014 + 0.6;
  const g2 = AC.createGain();
  g2.gain.setValueAtTime(0, t); g2.gain.linearRampToValueAtTime(amp * 0.38, t + att * 1.6); g2.gain.setTargetAtTime(0, t + att * 1.6, 0.9);
  o2.connect(g2); g2.connect(p); o2.start(t); o2.stop(t + 5.5);
  return true;
}

/** The mirror ball's ring as the view passes into it: high, soft and long. */
export function shimmer() {
  ['G6', 'D7'].forEach((n, i) => strike(n, { velocity: 0.3, pan: i ? 0.25 : -0.25, gain: 0.55 }));
}

// Gm9 in a warm low spread, built from the bottom up, one voice per candle: G2 D3 Bb3 F3... (seven voices)
const CHORD = ['G2', 'D3', 'Bb3', 'F3', 'A3', 'D4', 'G4'];

/** The Schwibbogen's chord: add(i) brings in voice i, swell() opens it with the wave, release() lets it go. */
export function createChord() {
  let nodes = null;
  const voices = new Map();
  function ensure() {
    if (isMuted()) return null;
    let AC;
    try { AC = audioContext(); } catch { return null; }
    if (nodes) return AC;
    const master = AC.createGain(); master.gain.value = 0.0;
    const lp = AC.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520; lp.Q.value = 0.7;
    master.connect(lp); lp.connect(output());
    const sendRoom = AC.createGain(); sendRoom.gain.value = 0.25; lp.connect(sendRoom); sendRoom.connect(ensureRoom(AC));
    nodes = { master, lp };
    return AC;
  }
  return {
    get voices() { return voices.size; },
    /** Voice i (0..6) fades in over a second and a half. */
    add(i) {
      const AC = ensure();
      if (!AC || voices.has(i)) return;
      const t = AC.currentTime;
      nodes.master.gain.cancelScheduledValues(t);
      nodes.master.gain.setTargetAtTime(0.22, t, 0.6);
      const f = noteHz(CHORD[i % CHORD.length]);
      const g = AC.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.11 / (1 + i * 0.12), t + 1.6);
      const os = [-4, 5].map((cents, k) => {
        const o = AC.createOscillator(); o.type = k ? 'triangle' : 'sawtooth';
        o.frequency.value = f * Math.pow(2, cents / 1200);
        const og = AC.createGain(); og.gain.value = k ? 0.9 : 0.35;
        o.connect(og); og.connect(g); o.start(t);
        return o;
      });
      g.connect(nodes.master);
      voices.set(i, { g, os });
    },
    /** The wave of light: the chord opens up and settles. */
    swell(seconds = 4) {
      if (!nodes) return;
      const t = nodes.master.context.currentTime, f = nodes.lp.frequency, m = nodes.master.gain;
      f.cancelScheduledValues(t); f.setValueAtTime(f.value, t); f.linearRampToValueAtTime(1500, t + seconds * 0.35); f.linearRampToValueAtTime(700, t + seconds);
      m.cancelScheduledValues(t); m.setValueAtTime(m.value, t); m.linearRampToValueAtTime(0.34, t + seconds * 0.35); m.linearRampToValueAtTime(0.16, t + seconds);
      // and then it lingers, very low, while the candles burn
      m.setTargetAtTime(0.07, t + seconds, 6);
    },
    /** Let the chord go over `seconds`, top voice first. */
    release(seconds = 3) {
      if (!nodes || !voices.size) return;
      const AC = nodes.master.context, t = AC.currentTime;
      [...voices.entries()].sort((a, b) => b[0] - a[0]).forEach(([, v], k) => {
        v.g.gain.cancelScheduledValues(t);
        v.g.gain.setValueAtTime(v.g.gain.value, t + k * 0.12);
        v.g.gain.setTargetAtTime(0, t + k * 0.12, seconds / 4);
        v.os.forEach((o) => o.stop(t + seconds + 2));
      });
      voices.clear();
    },
  };
}
