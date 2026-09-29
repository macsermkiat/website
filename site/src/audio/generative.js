// Fallback band: the prototype's live-written ballad (prototype/audio.js), used when the recorded stems
// are missing or cannot play. Same sound; packaged as a module with the scene hooks passed in.
import * as THREE from 'three';
import { audioContext, noiseBuffer, impulse } from './context.js';

export function createGenerativeBand({ samplesUrl, bandPos, getCamera }) {
  const bpm = 60, SPB = 60 / bpm, SW = 0.6;
  let AC, master, bandBus, bandPan, bandDist, revIn, crowdBus, timer = null, loaded = false, loading = null;
  const ch = {}, SAMP = {}, BASE = {};
  const evq = [];
  let featured = null;
  const api = { playing: false, bpm, mode: 'generative' };

  const FORM = [
    [[2, 'm9', 4]], [[10, 'maj7', 4]], [[7, 'm9', 4]], [[9, '7b9', 4]],
    [[2, 'm9', 4]], [[0, '9', 4]], [[5, 'maj9', 4]], [[4, 'm7b5', 2], [9, '7b9', 2]],
    [[10, 'maj7', 4]], [[9, 'm7', 4]], [[7, 'm9', 4]], [[0, '9', 4]],
    [[5, 'maj9', 4]], [[10, 'maj7', 4]], [[4, 'm7b5', 2], [9, '7b9', 2]], [[2, 'm9', 2], [9, '7b9', 2]],
  ];
  const TONES = { m9: [0, 3, 7, 10, 14], maj7: [0, 4, 7, 11, 14], '7b9': [0, 4, 7, 10, 13], 9: [0, 4, 7, 10, 14], maj9: [0, 4, 7, 11, 14], m7b5: [0, 3, 6, 10], m7: [0, 3, 7, 10, 14] };
  const SCALE = { m9: [0, 2, 3, 5, 7, 9, 10], maj7: [0, 2, 4, 6, 7, 9, 11], '7b9': [0, 1, 4, 5, 7, 8, 10], 9: [0, 2, 4, 5, 7, 9, 10], maj9: [0, 2, 4, 5, 7, 9, 11], m7b5: [0, 1, 3, 5, 6, 8, 10], m7: [0, 2, 3, 5, 7, 8, 10] };
  const UPPER = { m9: [[3, 7, 10, 14], [10, 14, 15, 19]], maj7: [[4, 7, 11, 14], [11, 14, 16, 19]], '7b9': [[4, 8, 10, 13], [10, 13, 16, 20]], 9: [[4, 9, 10, 14], [10, 14, 16, 21]], maj9: [[4, 7, 11, 14], [11, 14, 16, 19]], m7b5: [[3, 6, 10, 12], [10, 12, 15, 18]], m7: [[3, 7, 10, 14], [10, 14, 15, 19]] };
  const pc = (m) => ((m % 12) + 12) % 12;
  function chordAt(bar, b) { const segs = FORM[bar % FORM.length]; let acc = 0; for (const s of segs) { if (b < acc + s[2]) return { root: s[0], q: s[1], start: acc, len: s[2] }; acc += s[2]; } return { root: segs[0][0], q: segs[0][1], start: 0, len: 4 }; }
  function b64(s) { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
  function sat(k) { const n = 2048, c = new Float32Array(n); for (let i = 0; i < n; i++) { const x = (i / (n - 1)) * 2 - 1; c[i] = Math.tanh(k * x) / Math.tanh(k); } return c; }
  function mkCh(pan, send, { lp = 18000, gain = 1 } = {}) { const g = AC.createGain(); g.gain.value = gain; const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = lp; const p = AC.createStereoPanner(); p.pan.value = pan; const s = AC.createGain(); s.gain.value = send; g.connect(f); f.connect(p); p.connect(bandBus); f.connect(s); s.connect(revIn); return g; }
  function mkSax() { const g = AC.createGain(); g.gain.value = 1.3; const warm = AC.createBiquadFilter(); warm.type = 'peaking'; warm.frequency.value = 230; warm.Q.value = 0.8; warm.gain.value = 3.5; const honk = AC.createBiquadFilter(); honk.type = 'peaking'; honk.frequency.value = 1250; honk.Q.value = 1.2; honk.gain.value = -2.5; const lp = AC.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2600; lp.Q.value = 0.5; const p = AC.createStereoPanner(); p.pan.value = 0.3; const s = AC.createGain(); s.gain.value = 0.62; g.connect(warm); warm.connect(honk); honk.connect(lp); lp.connect(p); p.connect(bandBus); lp.connect(s); s.connect(revIn); return g; }

  async function init() {
    AC = audioContext();
    SAMP.noise = noiseBuffer();
    master = AC.createGain(); master.gain.value = 0;
    const lo = AC.createBiquadFilter(); lo.type = 'lowshelf'; lo.frequency.value = 140; lo.gain.value = 2.5;
    const hi = AC.createBiquadFilter(); hi.type = 'highshelf'; hi.frequency.value = 7000; hi.gain.value = -2.5;
    const sh = AC.createWaveShaper(); sh.curve = sat(1.3); sh.oversample = '2x';
    const comp = AC.createDynamicsCompressor(); comp.threshold.value = -18; comp.knee.value = 14; comp.ratio.value = 2.5; comp.attack.value = 0.02; comp.release.value = 0.3;
    master.connect(lo); lo.connect(hi); hi.connect(sh); sh.connect(comp); comp.connect(AC.destination);
    bandBus = AC.createGain(); bandDist = AC.createGain(); bandPan = AC.createStereoPanner();
    bandBus.connect(bandPan); bandPan.connect(bandDist); bandDist.connect(master);
    revIn = AC.createGain(); const rev = AC.createConvolver(); rev.buffer = impulse(3.2); const revOut = AC.createGain(); revOut.gain.value = 0.9;
    revIn.connect(rev); rev.connect(revOut); revOut.connect(bandBus);
    ch.piano = mkCh(-0.28, 0.34, { gain: 0.9 }); ch.bass = mkCh(0.05, 0.1, { lp: 1600, gain: 1.1 }); ch.sax = mkSax(); ch.drums = mkCh(-0.05, 0.25, { gain: 0.8 }); ch.brush = mkCh(0.1, 0.2, { gain: 1 });
    Object.keys(ch).forEach((k) => (BASE[k] = ch[k].gain.value));
    applyFeature();
    crowdBus = AC.createGain(); crowdBus.gain.value = 0; crowdBus.connect(master);
    const res = await fetch(samplesUrl);
    if (!res.ok) throw new Error(`samples: HTTP ${res.status}`);
    const data = await res.json();
    for (const inst of ['piano', 'bass', 'sax']) { SAMP[inst] = {}; await Promise.all(Object.entries(data[inst]).map(async ([m, s]) => { SAMP[inst][+m] = await AC.decodeAudioData(b64(s)); })); }
    SAMP.drums = {}; await Promise.all(Object.entries(data.drums).map(async ([k, s]) => { SAMP.drums[k] = await AC.decodeAudioData(b64(s)); }));
    setupCrowd();
    loaded = true;
  }
  const ev = (t, type) => evq.push({ t, type });
  /** Note events that have sounded since the last call: 'bass' | 'drum' | 'piano' | 'sax'. */
  api.drain = function () { const out = []; if (!AC) return out; const now = AC.currentTime; for (let i = evq.length - 1; i >= 0; i--) if (evq[i].t <= now) { out.push(evq[i].type); evq.splice(i, 1); } return out; };
  const camRight = new THREE.Vector3(), dir = new THREE.Vector3();
  api.updateSpace = function () {
    if (!AC || !bandDist) return;
    const camera = getCamera();
    const d = camera.position.distanceTo(bandPos);
    bandDist.gain.setTargetAtTime(Math.min(1.25, 9 / Math.max(5, d)) + 0.12, AC.currentTime, 0.2);
    camRight.setFromMatrixColumn(camera.matrixWorld, 0);
    dir.copy(bandPos).sub(camera.position).normalize();
    bandPan.pan.setTargetAtTime(Math.max(-0.7, Math.min(0.7, dir.dot(camRight) * 0.8)), AC.currentTime, 0.2);
  };
  function play(inst, m, t, vel, dur, dest, o = {}) {
    const bank = SAMP[inst]; let key = null; for (const k in bank) if (key === null || Math.abs(k - m) < Math.abs(key - m)) key = +k;
    const src = AC.createBufferSource(); src.buffer = bank[key]; src.playbackRate.value = Math.pow(2, (m - key) / 12);
    if (o.scoop) { src.detune.setValueAtTime(-o.scoop, t); src.detune.linearRampToValueAtTime(0, t + 0.12); }
    if (o.fall) { src.detune.setValueAtTime(0, t + dur - 0.1); src.detune.linearRampToValueAtTime(-180, t + dur + 0.25); }
    const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = o.lp || 900 + vel * vel * 7000;
    const g = AC.createGain(), v = vel * vel * (o.gain || 1), rel = o.rel || 0.4;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + (o.att || 0.006));
    g.gain.setValueAtTime(v, t + dur); g.gain.exponentialRampToValueAtTime(0.0004, t + dur + rel);
    src.connect(f); f.connect(g); g.connect(dest); src.start(t); src.stop(t + dur + rel + 0.05);
  }
  function saxNote(m, t, vel, dur, o = {}) {
    const bank = SAMP.sax; let key = null; for (const k in bank) if (key === null || Math.abs(k - m) < Math.abs(key - m)) key = +k;
    const buf = bank[key], rate = Math.pow(2, (m - key) / 12), rel = o.rel || 0.7, att = o.att || 0.12, end = t + dur + rel;
    const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = 0.4; f.frequency.setValueAtTime((o.lp || 1400) * 0.8, t); f.frequency.linearRampToValueAtTime(o.lp || 1400, t + att + 0.25);
    const g = AC.createGain(), v = vel * vel;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v * 0.55, t + att); g.gain.linearRampToValueAtTime(v * 0.9, t + att + 0.3);
    if (dur > 1.3) { g.gain.linearRampToValueAtTime(v * 0.8, t + dur * 0.45); g.gain.linearRampToValueAtTime(v, t + dur * 0.85); }
    g.gain.setValueAtTime(dur > 1.3 ? v : v * 0.9, t + dur); g.gain.exponentialRampToValueAtTime(0.0004, end);
    f.connect(g); g.connect(ch.sax);
    const srcs = [], X = 0.4, SEG = 1.6, OFF = 0.8, firstLen = 2.6;
    const seg = (st, off, len, fadeIn) => { const s = AC.createBufferSource(); s.buffer = buf; s.playbackRate.value = rate; const sg = AC.createGain(); if (fadeIn) { sg.gain.setValueAtTime(0, st); sg.gain.linearRampToValueAtTime(1, st + X); } else sg.gain.setValueAtTime(1, st); if (st + len < end) { sg.gain.setValueAtTime(1, st + len - X); sg.gain.linearRampToValueAtTime(0, st + len); } s.connect(sg); sg.connect(f); s.start(st, off); s.stop(Math.min(end, st + len) + 0.05); srcs.push(s); };
    seg(t, 0, firstLen, false); for (let st = t + firstLen - X; st < end; st += SEG) seg(st, OFF, SEG + X, true);
    if (o.scoop) srcs.forEach((s) => { s.detune.setValueAtTime(-o.scoop, t); s.detune.linearRampToValueAtTime(0, t + 0.22); });
    if (o.fall) srcs.forEach((s) => { s.detune.setValueAtTime(0, t + dur - 0.05); s.detune.linearRampToValueAtTime(-70, end); });
    if (o.vib && dur > 1.4) { const l = AC.createOscillator(); l.frequency.value = 4.2 + Math.random() * 0.5; const lg = AC.createGain(); lg.gain.setValueAtTime(0, t); lg.gain.setValueAtTime(0, t + dur * 0.45); lg.gain.linearRampToValueAtTime(o.vib, t + dur * 0.9); l.connect(lg); srcs.forEach((s) => lg.connect(s.detune)); l.start(t); l.stop(end + 0.05); }
    const n = AC.createBufferSource(); n.buffer = SAMP.noise; n.loop = true;
    const bp = AC.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1500 + Math.random() * 500; bp.Q.value = 0.7;
    const hp = AC.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 800;
    const ng = AC.createGain(), b = v * (o.air || 0.035);
    ng.gain.setValueAtTime(0, Math.max(0, t - 0.03)); ng.gain.linearRampToValueAtTime(b * 2.2, t + att * 0.7); ng.gain.linearRampToValueAtTime(b, t + att + 0.25);
    ng.gain.setValueAtTime(b, t + dur); ng.gain.exponentialRampToValueAtTime(0.00005, t + dur + rel * 0.7);
    n.connect(bp); bp.connect(hp); hp.connect(ng); ng.connect(ch.sax); n.start(Math.max(0, t - 0.03), Math.random() * 1.5); n.stop(end + 0.05);
  }
  function noise(t, dur, { freq = 3000, q = 0.7, type = 'bandpass', gain = 0.05, att = 0.02, dest = ch.brush, sweep = 0 } = {}) { const s = AC.createBufferSource(); s.buffer = SAMP.noise; const f = AC.createBiquadFilter(); f.type = type; f.frequency.setValueAtTime(freq, t); if (sweep) f.frequency.linearRampToValueAtTime(freq + sweep, t + dur); f.Q.value = q; const g = AC.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + att); g.gain.exponentialRampToValueAtTime(0.0003, t + dur); s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random() * 1.2); s.stop(t + dur + 0.05); }
  function ride(t, vel) { const base = [2.0, 3.02, 4.16, 5.43, 6.79, 8.21]; const mix = AC.createGain(); base.forEach((r) => { const o = AC.createOscillator(); o.type = 'square'; o.frequency.value = r * 405; o.connect(mix); o.start(t); o.stop(t + 3); }); const bp = AC.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 6800; bp.Q.value = 0.5; const hp = AC.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 4200; const g = AC.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel * 0.03, t + 0.004); g.gain.exponentialRampToValueAtTime(vel * 0.008, t + 0.25); g.gain.exponentialRampToValueAtTime(0.0002, t + 2.8); mix.connect(bp); bp.connect(hp); hp.connect(g); g.connect(ch.drums); noise(t, 0.12, { freq: 9000, q: 1, gain: vel * 0.03, att: 0.002, dest: ch.drums }); }
  function drum(k, t, vel, rate = 1) { const s = AC.createBufferSource(); s.buffer = SAMP.drums[k]; s.playbackRate.value = rate; const g = AC.createGain(); g.gain.value = vel * vel; const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 2500 + vel * 6000; s.connect(f); f.connect(g); g.connect(ch.drums); s.start(t); }

  let bassPrev = 38, voicePrev = null, melPrev = 60, pianoMelPrev = 74, phraseLeft = 0, restLeft = 0;
  function nearestPc(target, prev, lo, hi) { let best = null; for (let m = lo; m <= hi; m++) if (pc(m) === pc(target) && (best === null || Math.abs(m - prev) < Math.abs(best - prev))) best = m; return best; }
  function voicing(root, q) { const opts = UPPER[q].map((v) => v.map((i) => i + root)); let best = null, bd = 1e9; for (const o of opts) for (let sh = 36; sh <= 72; sh += 12) { const v = o.map((x) => x + sh); if (v[0] < 50 || v[v.length - 1] > 74) continue; const c = v.reduce((a, b) => a + b) / v.length; const d = voicePrev ? Math.abs(c - voicePrev) : Math.abs(c - 61); if (d < bd) { bd = d; best = v; } } voicePrev = best.reduce((a, b) => a + b) / best.length; return best; }
  function melodyNote(prev, root, q, strong, lo, hi) { const set = (strong ? TONES[q] : SCALE[q]).map((i) => pc(i + root)); const c = []; for (let m = prev - 5; m <= prev + 5; m++) if (m >= lo && m <= hi && set.includes(pc(m)) && m !== prev) c.push(m); if (!c.length) return prev; c.sort((a, b) => Math.abs(a - prev) - Math.abs(b - prev)); const w = c.slice(0, Math.min(3, c.length)); return w[(Math.random() * w.length) | 0]; }
  const RHY = [[[0, 1.5], [1.5, 0.5], [2, 2]], [[0, 3], [3, 0.5], [3.5, 0.5]], [[0.6, 0.4], [1, 1], [2, 1.5], [3.5, 0.5]], [[0, 2], [2, 1], [3, 1]], [[1, 1], [2, 0.6], [2.6, 0.4], [3, 1]], [[0, 4]], [[0, 1], [1, 1], [2, 2]]];
  const SAX_RHY = [[[0, 3]], [[0, 2], [2, 2]], [[0.5, 1.5], [2, 2]], [[0, 1.5], [1.5, 0.5], [2, 2]], [[1, 3]], [[0, 2.5], [3, 1]], [[0, 1], [1, 3]], [[0, 4]], [[2, 2]]];
  function scheduleBar(barN, t) {
    const bar = barN % 16, chorus = Math.floor(barN / 16) % 3, lead = chorus === 1 ? 'piano' : 'sax';
    const segs = FORM[bar];
    const walk = chorus === 2 && bar >= 8;
    for (let b = 0; b < 4; b += walk ? 1 : 2) {
      const c = chordAt(bar, b), nextC = b + (walk ? 1 : 2) >= 4 ? chordAt(barN + 1, 0) : chordAt(bar, b + (walk ? 1 : 2));
      let m; if (b === c.start) m = nearestPc(c.root, bassPrev, 31, 50); else if (Math.random() < 0.5) m = nearestPc(nextC.root, bassPrev, 31, 50) + (Math.random() < 0.5 ? 1 : -1); else m = nearestPc(c.root + 7, bassPrev, 31, 50);
      bassPrev = m; const dur = (walk ? 1 : 2) * SPB * 0.96;
      play('bass', m, t + b * SPB + Math.random() * 0.012, 0.78 + Math.random() * 0.1, dur, ch.bass, { rel: 0.25, lp: 1500 }); ev(t + b * SPB, 'bass');
    }
    for (let b = 0; b < 4; b++) {
      const tb = t + b * SPB;
      noise(tb, SPB * 0.95, { freq: 2600, q: 0.9, gain: 0.022 + (b % 2) * 0.008, att: SPB * 0.45, sweep: 900 });
      if (b % 2 === 1) { drum('snare', tb, 0.26 + Math.random() * 0.06, 0.95); noise(tb, 0.25, { freq: 4000, q: 0.6, gain: 0.03, att: 0.003 }); drum('hihat', tb + 0.01, 0.16, 0.8); ev(tb, 'drum'); }
      if (b === 0 && Math.random() < 0.5) drum('kick', tb, 0.22);
      if (Math.random() < 0.18) drum('snare', tb + SW * SPB, 0.12, 1.05);
    }
    if (bar === 0) ride(t, 0.9);
    if (bar === 15) [2, 2.33, 2.66, 3, 3.33, 3.66].forEach((p, i) => drum(i < 3 ? 'snare' : 'tom1', t + p * SPB, 0.18 + i * 0.03, i < 3 ? 1 : 0.8 - i * 0.03));
    segs.forEach((s, si) => {
      const start = segs.slice(0, si).reduce((a, x) => a + x[2], 0), ts = t + start * SPB;
      const v = voicing(s[0], s[1]); const lh = nearestPc(s[0], 45, 38, 50); const lhs = [lh, lh + (TONES[s[1]][3] || 10)];
      const vel = lead === 'piano' ? 0.42 : 0.5;
      lhs.forEach((m, i) => play('piano', m, ts + i * 0.035, vel + 0.05, s[2] * SPB * 0.98, ch.piano, { rel: 1.2 }));
      v.forEach((m, i) => play('piano', m, ts + 0.09 + i * 0.045 + Math.random() * 0.01, vel + Math.random() * 0.06, s[2] * SPB * 0.98, ch.piano, { rel: 1.4 })); ev(ts, 'piano');
      if (s[2] === 4 && Math.random() < 0.45 && lead === 'sax') { const again = v.slice(1); again.forEach((m, i) => play('piano', m + (i === again.length - 1 && Math.random() < 0.5 ? 2 : 0), ts + 2.6 * SPB + i * 0.03, 0.34, 1.2 * SPB, ch.piano, { rel: 1 })); }
    });
    if (restLeft > 0) { restLeft--; if (lead === 'sax') pianoFill(barN, t); return; }
    if (phraseLeft <= 0) phraseLeft = 2 + (Math.random() < 0.4 ? 1 : 0);
    const rh = lead === 'sax' ? SAX_RHY[(Math.random() * SAX_RHY.length) | 0] : RHY[(Math.random() * RHY.length) | 0]; const last = phraseLeft === 1;
    rh.forEach(([pos, dur], i) => {
      const c = chordAt(bar, pos), strong = pos % 1 === 0;
      const tt = t + (pos % 1 ? Math.floor(pos) + (pos % 1 >= 0.5 ? SW : pos % 1) : pos) * SPB;
      if (lead === 'sax') {
        let n = melodyNote(melPrev, c.root, c.q, strong, 50, 67); const fin = last && i === rh.length - 1;
        if (fin) n = nearestPc(c.root + TONES[c.q][1 + ((Math.random() * 3) | 0)], n, 50, 67);
        melPrev = n;
        const d = (fin ? Math.max(dur, 2.5) : dur) * SPB * 0.97, vel = 0.5 + Math.random() * 0.1 - (strong ? 0 : 0.04);
        saxNote(n, tt + Math.random() * 0.04, vel, d, { att: 0.1 + Math.random() * 0.06, rel: 0.7 + (fin ? 0.4 : 0), vib: 11, scoop: strong && Math.random() < 0.15 ? 40 : 0, fall: fin && Math.random() < 0.15, lp: 1150 + vel * vel * 1200 + Math.random() * 200 }); ev(tt, 'sax');
      } else { const n = melodyNote(pianoMelPrev, c.root, c.q, strong, 67, 86); pianoMelPrev = n; play('piano', n, tt, 0.62 + Math.random() * 0.12, dur * SPB, ch.piano, { rel: 1.2 }); if (strong && Math.random() < 0.5) play('piano', n - 12, tt + 0.01, 0.4, dur * SPB, ch.piano, { rel: 1 }); ev(tt, 'piano'); }
    });
    phraseLeft--; if (phraseLeft <= 0) restLeft = Math.random() < 0.6 ? 1 : 0;
  }
  function pianoFill(barN, t) { const bar = barN % 16; let n = pianoMelPrev; [2, 2.5, 3, 3.5].forEach((p, i) => { if (Math.random() < 0.25) return; const cc = chordAt(bar, p); n = melodyNote(n, cc.root, cc.q, i % 2 === 0, 70, 86); play('piano', n, t + (p % 1 ? Math.floor(p) + SW : p) * SPB, 0.4 + Math.random() * 0.1, 0.8 * SPB, ch.piano, { rel: 1 }); }); pianoMelPrev = n; }

  const voices = [];
  function setupCrowd() { for (let i = 0; i < 7; i++) { const s = AC.createBufferSource(); s.buffer = SAMP.noise; s.loop = true; const f = AC.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 500 + Math.random() * 500; f.Q.value = 5; const f2 = AC.createBiquadFilter(); f2.type = 'lowpass'; f2.frequency.value = 2200; const g = AC.createGain(); g.gain.value = 0; const p = AC.createStereoPanner(); p.pan.value = Math.random() * 1.6 - 0.8; s.connect(f); f.connect(f2); f2.connect(g); g.connect(p); p.connect(crowdBus); s.start(); voices.push({ f, g, next: 0 }); } }
  function crowdTick(now) { voices.forEach((v) => { if (now + 0.2 > v.next) { const t = Math.max(now, v.next), d = 0.08 + Math.random() * 0.22; v.g.gain.setTargetAtTime(Math.random() < 0.2 ? 0 : 0.05 + Math.random() * 0.08, t, 0.02); v.g.gain.setTargetAtTime(0, t + d, 0.04); v.f.frequency.setTargetAtTime(380 + Math.random() * 700, t, 0.03); v.next = t + d + 0.03 + Math.random() * (Math.random() < 0.15 ? 1.2 : 0.12); } }); }

  let nextBarT = 0, barN = 0;
  function tick() { const now = AC.currentTime; while (nextBarT < now + 0.4) { scheduleBar(barN, nextBarT); nextBarT += 4 * SPB; barN++; } crowdTick(now); }
  function applyFeature() { if (!AC || !ch.piano) return; const now = AC.currentTime; Object.keys(ch).forEach((k) => { const on = featured && (k === featured || (featured === 'drums' && k === 'brush')); const f = !featured ? 1 : on ? 1.7 : 0.55; ch[k].gain.setTargetAtTime(BASE[k] * f, now, 0.4); }); }

  api.start = async function () {
    if (!loaded) { if (!loading) loading = init(); await loading; }
    await AC.resume();
    master.gain.cancelScheduledValues(AC.currentTime); master.gain.setValueAtTime(master.gain.value, AC.currentTime); master.gain.linearRampToValueAtTime(0.9, AC.currentTime + 1.2);
    crowdBus.gain.setTargetAtTime(0.55, AC.currentTime, 0.8);
    nextBarT = AC.currentTime + 0.15; barN = 0; phraseLeft = 0; restLeft = 1; voicePrev = null; melPrev = 60;
    timer = setInterval(tick, 40); api.playing = true;
  };
  api.stop = function () {
    if (!AC || !master) return;
    master.gain.cancelScheduledValues(AC.currentTime); master.gain.setValueAtTime(master.gain.value, AC.currentTime); master.gain.linearRampToValueAtTime(0, AC.currentTime + 0.8);
    clearInterval(timer); timer = null; api.playing = false; evq.length = 0;
  };
  api.feature = function (name) { featured = name || null; applyFeature(); };
  return api;
}
