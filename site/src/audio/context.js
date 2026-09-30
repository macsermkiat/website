// One AudioContext for the band and the stall sounds, created on the first user gesture.
let AC = null;
let noise = null;

export function audioContext() {
  if (!AC) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) throw new Error('Web Audio is not available');
    AC = new Ctor({ latencyHint: 'playback' });
  }
  return AC;
}

// Everything the market plays (the band and the stall sounds) goes through one output gain, so the mute
// button silences all of it at once.
let out = null;
let muted = false;
export function output() {
  const ac = audioContext();
  if (!out) {
    out = ac.createGain();
    out.gain.value = muted ? 0 : 1;
    out.connect(ac.destination);
  }
  return out;
}

/** Mute or unmute every sound (band and stall sounds). Works before the context exists. */
export function setMuted(on) {
  muted = !!on;
  if (out) out.gain.setTargetAtTime(muted ? 0 : 1, out.context.currentTime, 0.03);
}
export const isMuted = () => muted;

export function hasContext() {
  return !!AC;
}

/** Two seconds of white noise, shared. */
export function noiseBuffer() {
  const ac = audioContext();
  if (!noise) {
    noise = ac.createBuffer(1, ac.sampleRate * 2, ac.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  return noise;
}

/** A synthetic room impulse response (early reflections + filtered noise tail). */
export function impulse(dur) {
  const ac = audioContext();
  const sr = ac.sampleRate, len = Math.floor(sr * dur), b = ac.createBuffer(2, len, sr);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    let lp = 0;
    [[0.013, 0.5], [0.021, 0.38], [0.029, 0.3], [0.041, 0.26], [0.053, 0.2], [0.067, 0.16]].forEach(([t, a]) => { d[Math.floor((t + (c ? 0.003 : 0)) * sr)] += a * (Math.random() < 0.5 ? -1 : 1); });
    const pre = Math.floor(0.02 * sr);
    for (let i = pre; i < len; i++) {
      const t = (i - pre) / sr, env = Math.exp((-6.9 * t) / (dur - 0.02)), a = 0.85 * Math.exp(-t * 1.6) + 0.08;
      lp += a * (Math.random() * 2 - 1 - lp);
      d[i] += lp * env * 0.55;
    }
  }
  return b;
}
