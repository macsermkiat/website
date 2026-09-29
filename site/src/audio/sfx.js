// Stall sounds, synthesised live as in the prototype: clink, pour, sizzle, page, chime, whoosh.
// They have their own bus straight to the output and are never faded with the music.
import { audioContext, noiseBuffer, impulse } from './context.js';

let bus = null, rev = null, crackleBuf = null, until = 0;
let isMusicPlaying = () => false;

export function setMusicState(fn) {
  isMusicPlaying = fn;
}

function ensure() {
  const AC = audioContext();
  if (bus) return AC;
  bus = AC.createGain(); bus.gain.value = 0.8;
  const lo = AC.createBiquadFilter(); lo.type = 'highshelf'; lo.frequency.value = 8000; lo.gain.value = -3;
  const comp = AC.createDynamicsCompressor(); comp.threshold.value = -20; comp.knee.value = 12; comp.ratio.value = 3; comp.attack.value = 0.005; comp.release.value = 0.25;
  bus.connect(lo); lo.connect(comp); comp.connect(AC.destination);
  rev = AC.createGain(); rev.gain.value = 0.22;
  const conv = AC.createConvolver(); conv.buffer = impulse(1.4);
  rev.connect(conv); conv.connect(bus);
  return AC;
}

function crackle(AC) {
  if (crackleBuf) return crackleBuf;
  const sr = AC.sampleRate, len = Math.floor(sr * 3), b = AC.createBuffer(1, len, sr), d = b.getChannelData(0);
  for (let i = 0; i < len;) {
    i += Math.floor(sr * (0.002 + Math.random() * Math.random() * 0.03));
    const a = Math.random() ** 2.5 * (Math.random() < 0.06 ? 1 : 0.35), dl = Math.floor(sr * (0.0006 + Math.random() * 0.004));
    for (let j = 0; j < dl && i + j < len; j++) d[i + j] += a * (Math.random() * 2 - 1) * Math.exp((-5 * j) / dl);
  }
  return (crackleBuf = b);
}

function out(AC, pan = 0, send = 1) {
  const p = AC.createStereoPanner(); p.pan.value = pan; p.connect(bus);
  if (send) { const s = AC.createGain(); s.gain.value = send; p.connect(s); s.connect(rev); }
  return p;
}
function sNoise(AC, t, dur, dest, { type = 'bandpass', f = 1000, f2 = 0, q = 0.7, off = Math.random() * 1.5, buf = noiseBuffer() } = {}) {
  const s = AC.createBufferSource(); s.buffer = buf; s.loop = true;
  const fl = AC.createBiquadFilter(); fl.type = type; fl.frequency.setValueAtTime(f, t);
  if (f2) fl.frequency.exponentialRampToValueAtTime(f2, t + dur);
  fl.Q.value = q;
  const g = AC.createGain(); s.connect(fl); fl.connect(g); g.connect(dest);
  s.start(t, off % buf.duration); s.stop(t + dur + 0.05);
  return g.gain;
}
function sTone(AC, t, freq, amp, dec, dest, { att = 0.002, type = 'sine' } = {}) {
  const o = AC.createOscillator(); o.type = type; o.frequency.value = freq;
  const g = AC.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(amp, t + att); g.gain.exponentialRampToValueAtTime(0.00005, t + att + dec);
  o.connect(g); g.connect(dest); o.start(t); o.stop(t + att + dec + 0.05);
  return o;
}
function env(p, t, pts) { p.setValueAtTime(0, t); pts.forEach(([dt, v]) => p.linearRampToValueAtTime(v, t + dt)); }

const SFX = {
  clink(AC, t) {
    const o = out(AC, (Math.random() - 0.5) * 0.4, 0.8);
    const tick = sNoise(AC, t, 0.03, o, { type: 'highpass', f: 3500, q: 0.5 });
    tick.setValueAtTime(0, t); tick.linearRampToValueAtTime(0.05, t + 0.001); tick.exponentialRampToValueAtTime(0.0001, t + 0.025);
    [[1870, 0], [2140, 0.004]].forEach(([f0, dt], k) => {
      f0 *= 1 + Math.random() * 0.03;
      [[1, 0.03, 0.5], [2.37, 0.018, 0.28], [4.1, 0.009, 0.14], [6.3, 0.004, 0.07]].forEach(([r, a, d]) => sTone(AC, t + dt, f0 * r, a * (k ? 0.8 : 1), d, o));
    });
  },
  pour(AC, t) {
    const o = out(AC, 0.1, 0.5), D = 1.9;
    const st = sNoise(AC, t, D + 0.2, o, { f: 520, f2: 1250, q: 2.2 }); env(st, t, [[0.12, 0.05], [D - 0.2, 0.045], [D, 0]]);
    for (let k = 0; k < 22; k++) { const tt = t + 0.1 + Math.random() * (D - 0.3); st.setValueAtTime(0.03 + Math.random() * 0.025, tt); }
    const body = sNoise(AC, t, D + 0.2, o, { type: 'lowpass', f: 380, q: 0.6 }); env(body, t, [[0.1, 0.035], [D - 0.2, 0.03], [D, 0]]);
    for (let k = 0; k < 16; k++) { const tt = t + 0.15 + Math.random() * (D - 0.3), f0 = 500 + Math.random() * 700, osc = sTone(AC, tt, f0, 0.012, 0.04, o); osc.frequency.setValueAtTime(f0, tt); osc.frequency.exponentialRampToValueAtTime(f0 * 1.7, tt + 0.04); }
    const fz = sNoise(AC, t, D + 1.2, o, { type: 'highpass', f: 5500, q: 0.4, buf: crackle(AC) });
    fz.setValueAtTime(0, t); fz.linearRampToValueAtTime(0.05, t + D * 0.7); fz.linearRampToValueAtTime(0.07, t + D); fz.exponentialRampToValueAtTime(0.0005, t + D + 1.15);
  },
  sizzle(AC, t) {
    const o = out(AC, -0.15, 0.3), D = 2.5;
    const bed = sNoise(AC, t, D, o, { f: 5200, q: 0.5 }); bed.setValueAtTime(0, t); bed.linearRampToValueAtTime(0.022, t + 0.2);
    for (let k = 1; k < 10; k++) bed.linearRampToValueAtTime(0.014 + Math.random() * 0.014, t + 0.2 + (k * (D - 0.8)) / 9);
    bed.linearRampToValueAtTime(0, t + D);
    const cr = sNoise(AC, t, D, o, { type: 'highpass', f: 2200, q: 0.5, buf: crackle(AC) });
    cr.setValueAtTime(0, t); cr.linearRampToValueAtTime(0.12, t + 0.12); cr.setValueAtTime(0.12, t + D - 0.7); cr.linearRampToValueAtTime(0, t + D);
    for (let k = 0; k < 5; k++) { const tt = t + 0.2 + Math.random() * (D - 0.6), sp = sNoise(AC, tt, 0.08, o, { f: 900 + Math.random() * 900, q: 1.5 }); sp.setValueAtTime(0, tt); sp.linearRampToValueAtTime(0.05, tt + 0.003); sp.exponentialRampToValueAtTime(0.0002, tt + 0.07); }
  },
  page(AC, t) {
    const o = out(AC, (Math.random() - 0.5) * 0.3, 0.4), D = 0.42;
    const sw = sNoise(AC, t, D, o, { f: 1300, f2: 3800, q: 1.1 }); sw.setValueAtTime(0, t);
    for (let k = 1; k <= 9; k++) sw.linearRampToValueAtTime((k < 7 ? 0.012 + k * 0.004 : 0.04 - (k - 6) * 0.012) * (0.7 + Math.random() * 0.6), t + (k * D) / 10);
    sw.linearRampToValueAtTime(0, t + D);
    const cr = sNoise(AC, t + 0.05, 0.25, o, { type: 'highpass', f: 3000, q: 0.5, buf: crackle(AC) });
    cr.setValueAtTime(0, t + 0.05); cr.linearRampToValueAtTime(0.05, t + 0.15); cr.linearRampToValueAtTime(0, t + 0.3);
    const flap = sNoise(AC, t + D - 0.06, 0.12, o, { type: 'lowpass', f: 500, q: 0.7 });
    flap.setValueAtTime(0, t + D - 0.06); flap.linearRampToValueAtTime(0.06, t + D - 0.04); flap.exponentialRampToValueAtTime(0.0002, t + D + 0.08);
  },
  chime(AC, t) {
    const o = out(AC, (Math.random() - 0.5) * 0.5, 1.2), N = [79, 83, 84, 86, 88, 91], a = N[(Math.random() * N.length) | 0], b = N[(Math.random() * N.length) | 0];
    [[a, 0, 1], [b, 0.16, 0.7]].forEach(([m, dt, s]) => { const f = 440 * Math.pow(2, (m - 69) / 12), tt = t + dt; sTone(AC, tt, f, 0.035 * s, 1.6, o); sTone(AC, tt, f * 2, 0.008 * s, 0.5, o); sTone(AC, tt, f * 5.4, 0.004 * s, 0.12, o); });
  },
  whoosh(AC, t) {
    const p = AC.createStereoPanner(); p.pan.setValueAtTime(-0.6, t); p.pan.linearRampToValueAtTime(0.6, t + 1.6); p.connect(bus);
    const s = AC.createGain(); s.gain.value = 0.5; p.connect(s); s.connect(rev);
    const w = sNoise(AC, t, 1.7, p, { f: 280, f2: 900, q: 1.3 }); env(w, t, [[0.65, 0.07], [1.65, 0]]);
    const w2 = sNoise(AC, t, 1.7, p, { type: 'lowpass', f: 260, q: 0.5 }); env(w2, t, [[0.7, 0.04], [1.65, 0]]);
  },
};

/** Play a stall sound. Safe to call anywhere; it never throws. */
export function sfx(name) {
  let AC;
  try { AC = ensure(); } catch { return; }
  const fn = SFX[name];
  if (!fn) return;
  const go = () => {
    const t = AC.currentTime + 0.02;
    try { fn(AC, t); } catch { return; }
    until = Math.max(until, t + 3.5);
    // let the context sleep again when neither music nor sounds need it
    if (!isMusicPlaying()) setTimeout(() => { if (!isMusicPlaying() && AC.state === 'running' && AC.currentTime > until) AC.suspend(); }, 4000);
  };
  if (AC.state !== 'running') AC.resume().then(go, () => {});
  else go();
}

export function sfxBusy() {
  return bus ? audioContext().currentTime < until : false;
}
