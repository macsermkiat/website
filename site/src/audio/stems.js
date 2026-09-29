// The recorded ballad from site/public/audio/manifest.json:
//   { bpm, duration, loopStart, loopEnd, stems: { sax, piano, bass, drums, room }: url, mix?: url, events?: url }
//
// Two ways to play it:
// - Mix: one <audio> element, streamed, through a single PannerNode at the bandstand. It starts at once and
//   costs almost no memory. The lite market only ever uses this; the full market uses it while the stems load.
// - Stems (full market): each stem is decoded once, folded to mono at a lower rate (a player on the bandstand
//   is a point source, so a stereo copy would only double the memory), cut after the written ending, and
//   played from AudioBufferSources scheduled segment by segment on the AudioContext clock (songplan.js):
//   the head, the loop `passes` times (every second pass with the tenor's second chorus from the manifest's
//   `alternates`), then the out head to the fermata, a rest, and from the top. Every stem's segment starts on
//   the same tick, so the players stay locked. Each player is a PannerNode at their place on the bandstand; the
//   room return stays stereo and centred. When the stems are ready the mix hands over to them at the same bar.
// Featuring raises one player and lowers the others (stems only; the mix cannot be taken apart).
// Visual levels come from analysers on the stems, or from the note list in `events` while the mix plays.
import * as THREE from 'three';
import { audioContext } from './context.js';
import { songPlan } from './songplan.js';

const PLAYERS = ['sax', 'piano', 'bass', 'drums'];
const FEATURE_UP = 1.6, FEATURE_DOWN = 0.5;
// Sample rates the stems are kept at after decoding. Brushes keep more air than the sax and bass need.
const KEEP_RATE = { drums: 32000, room: 24000, default: 24000 };
const XFADE = 0.35;
const LOOKAHEAD = 6; // seconds of music kept scheduled ahead of the clock
const REST = 7; // seconds of quiet after the fermata before the band starts again from the top

export function stemUrl(url) {
  if (/^(https?:|blob:|data:)/.test(url)) return url;
  const clean = String(url).replace(/^(\.\/|\/)+/, '').replace(/^(site\/)?(public\/)?/, '').replace(/^audio\//, '');
  return `${import.meta.env.BASE_URL}audio/${clean}`;
}

function fetchBuf(url, label) {
  return fetch(url).then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(`${label}: HTTP ${r.status}`))));
}

/** Decode, fold to `channels`, resample to `rate` and cut at `end` seconds, with the browser's own resampler. */
async function shrink(AC, data, { channels, rate, end }) {
  const full = await AC.decodeAudioData(data);
  const secs = Math.min(full.duration, end || full.duration);
  const frames = Math.max(1, Math.ceil(secs * rate));
  const Off = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  if (!Off) return full;
  try {
    const off = new Off(channels, frames, rate);
    const s = off.createBufferSource();
    s.buffer = full;
    s.connect(off.destination);
    s.start(0);
    return await off.startRendering();
  } catch {
    return full;
  }
}

/** Per-player loudness from the note list, for the mix (where there are no stems to measure). */
function eventLevels(events) {
  const lists = {};
  for (const k of PLAYERS) {
    const v = events?.[k];
    if (!Array.isArray(v)) continue;
    lists[k] = v
      .map((e) => (k === 'drums' ? { t: +e[0], d: 0.12, v: +e[2] || 0.5 } : { t: +e[0], d: +e[1] || 0.3, v: +e[3] || 0.5 }))
      .filter((e) => Number.isFinite(e.t))
      .sort((a, b) => a.t - b.t);
  }
  const lookback = { sax: 6, piano: 6, bass: 3, drums: 0.3 };
  return (pos, out) => {
    for (const [k, list] of Object.entries(lists)) {
      // binary search for the last note starting before pos
      let lo = 0, hi = list.length - 1, i = -1;
      while (lo <= hi) { const m = (lo + hi) >> 1; if (list[m].t <= pos) { i = m; lo = m + 1; } else hi = m - 1; }
      let v = 0;
      for (let j = i; j >= 0 && pos - list[j].t < lookback[k]; j--) {
        const e = list[j], since = pos - e.t;
        if (since <= e.d) v = Math.max(v, e.v * (k === 'drums' ? Math.exp(-since * 14) : 0.55 + 0.45 * Math.exp(-since * 3)));
      }
      out[k] = v > out[k] ? v : out[k] * 0.88 + v * 0.12;
    }
  };
}

export function createStemsBand({ manifest, positions, getCamera, lite }) {
  const api = { playing: false, bpm: Number(manifest.bpm) || 60, mode: 'stems', levels: { sax: 0, piano: 0, bass: 0, drums: 0 }, endings: 0, section: null };
  const urls = Object.fromEntries(Object.entries(manifest.stems).map(([k, u]) => [k, stemUrl(u)]));
  const mixUrl = manifest.mix ? stemUrl(manifest.mix) : null;
  const eventsUrl = manifest.events ? stemUrl(manifest.events) : null;
  // the road map: head, loop passes (alternate choruses), the written ending; see songplan.js
  const decoded = Number(manifest.decodedDuration) || 0;
  const song = songPlan(manifest, { fileEnd: decoded || undefined });
  const loopStart = song.loopStart;
  const loopEndRaw = song.loopEnd;
  const hasLoop = song.hasLoop;
  const useStems = !lite || !mixUrl;

  let AC = null, master = null, nodes = {}, buffers = null, altBuffers = null, loading = null, featured = null;
  // where play resumes (song seconds and loop pass), and the segments scheduled on the clock
  let cursor = { pos: 0, pass: 1 };
  let sched = [], ticker = null;
  // the mix's own place in the road map (it has no alternates: the recorded mix is the main take)
  let mixPass = 1, mixRestUntil = 0;
  let mix = null, stemsPlaying = false, mixPlaying = false, fromEvents = null, eventsLoading = null;
  const scratch = new Float32Array(512);

  function ensureGraph() {
    if (master) return;
    AC = audioContext();
    master = AC.createGain();
    master.gain.value = 0;
    const comp = AC.createDynamicsCompressor();
    comp.threshold.value = -14; comp.knee.value = 10; comp.ratio.value = 2; comp.attack.value = 0.02; comp.release.value = 0.3;
    master.connect(comp); comp.connect(AC.destination);
  }

  function panner(pos) {
    const p = AC.createPanner();
    p.panningModel = lite ? 'equalpower' : 'HRTF';
    p.distanceModel = 'inverse';
    p.refDistance = 9; p.rolloffFactor = 0.85; p.maxDistance = 120;
    p.positionX.value = pos.x; p.positionY.value = pos.y; p.positionZ.value = pos.z;
    return p;
  }

  // ---------- the mix, streamed ----------
  function ensureMix() {
    if (mix || !mixUrl) return mix;
    ensureGraph();
    const el = new Audio();
    el.preload = 'auto';
    el.src = mixUrl;
    const src = AC.createMediaElementSource(el);
    const gain = AC.createGain();
    gain.gain.value = 0;
    const p = panner(positions.center);
    // a wider source than one player: the whole quartet
    p.refDistance = 12;
    src.connect(gain); gain.connect(p); p.connect(master);
    mix = { el, gain };
    if (eventsUrl && !eventsLoading) {
      eventsLoading = fetch(eventsUrl).then((r) => (r.ok ? r.json() : null)).then((ev) => { if (ev) fromEvents = eventLevels(ev); }).catch(() => {});
    }
    return mix;
  }

  async function playMix(at) {
    const m = ensureMix();
    m.el.currentTime = at;
    await m.el.play();
    const now = AC.currentTime;
    m.gain.gain.cancelScheduledValues(now);
    m.gain.gain.setValueAtTime(m.gain.gain.value, now);
    m.gain.gain.linearRampToValueAtTime(1, now + 0.05);
    mixPlaying = true;
  }

  function stopMix(when, fade) {
    if (!mix || !mixPlaying) return;
    const g = mix.gain.gain;
    g.cancelScheduledValues(AC.currentTime);
    g.setValueAtTime(g.value, when);
    g.linearRampToValueAtTime(0, when + fade);
    mixPlaying = false;
    const el = mix.el;
    setTimeout(() => { if (!mixPlaying) el.pause(); }, (when - AC.currentTime + fade) * 1000 + 80);
  }

  // ---------- the stems, decoded ----------
  async function loadStems() {
    ensureGraph();
    const end = song.end + 0.05;
    const out = {};
    // one at a time, so only one full-size decode is in memory at once
    for (const [k, u] of Object.entries(urls)) {
      const data = await fetchBuf(u, k);
      out[k] = await shrink(AC, data, { channels: k === 'room' ? 2 : 1, rate: KEEP_RATE[k] || KEEP_RATE.default, end });
    }
    if (!PLAYERS.some((k) => out[k])) throw new Error('no player stems');
    for (const k of Object.keys(out)) {
      const gain = AC.createGain();
      const an = AC.createAnalyser();
      an.fftSize = 512;
      gain.connect(an);
      if (k === 'room') {
        // the reverb return is the space itself: centred, softer with distance
        const roomDist = AC.createGain();
        gain.connect(roomDist); roomDist.connect(master);
        nodes[k] = { gain, an, roomDist };
      } else {
        const p = panner(positions[k] || positions.center);
        gain.connect(p); p.connect(master);
        nodes[k] = { gain, an, panner: p };
      }
    }
    buffers = out;
    applyFeature(0);
    // the tenor's second chorus, for alternate passes: loaded after the main stems, never in the way of playing
    if (song.alt) loadAlternates().catch((e) => console.info('[audio] alternate chorus unavailable:', e?.message || e));
  }

  async function loadAlternates() {
    const out = {};
    for (const [k, u] of Object.entries(song.alt.stems)) {
      if (!buffers[k]) continue;
      const data = await fetchBuf(stemUrl(u), `${k} (alternate)`);
      out[k] = await shrink(AC, data, { channels: k === 'room' ? 2 : 1, rate: KEEP_RATE[k] || KEEP_RATE.default, end: 0 });
    }
    if (Object.keys(out).length) altBuffers = out;
  }

  /** Where the song is at AudioContext time `t` (from the scheduled segments). */
  function songPos(t) {
    for (const e of sched) if (t >= e.when && t < e.when + (e.seg.to - e.seg.from)) return { pos: e.seg.from + (t - e.when), pass: e.seg.pass };
    const last = sched[sched.length - 1];
    if (!last) return { ...cursor };
    if (t < sched[0].when) return { pos: sched[0].seg.from, pass: sched[0].seg.pass };
    return { pos: 0, pass: 1 }; // in the rest after the fermata
  }

  /** Schedule one segment for every stem at AudioContext time `when`. */
  function scheduleSegment(seg, when) {
    const len = seg.to - seg.from;
    const srcs = [];
    for (const [k, main] of Object.entries(buffers)) {
      const alt = seg.alt && altBuffers?.[k];
      const buf = alt || main;
      const at = alt ? seg.from - song.alt.start : seg.from;
      if (at >= buf.duration - 0.01) continue;
      const s = AC.createBufferSource();
      s.buffer = buf;
      s.connect(nodes[k].gain);
      s.start(Math.max(when, AC.currentTime), at, Math.min(len, buf.duration - at));
      srcs.push(s);
    }
    sched.push({ seg, when, srcs });
    api.section = seg.alt ? 'tenor chorus B' : null;
  }

  /** Keep LOOKAHEAD seconds scheduled: the next segment, or after the ending a rest and the top again. */
  function topUp() {
    if (!stemsPlaying || !AC) return;
    const now = AC.currentTime;
    // forget segments that have finished
    while (sched.length > 1 && sched[0].when + (sched[0].seg.to - sched[0].seg.from) < now - 1) sched.shift();
    for (let guard = 0; guard < 8; guard++) {
      const last = sched[sched.length - 1];
      const lastEnd = last.when + (last.seg.to - last.seg.from);
      if (lastEnd - now > LOOKAHEAD) return;
      const nx = song.next(last.seg);
      if (nx) scheduleSegment(nx, lastEnd);
      else { api.endings++; scheduleSegment(song.segment(0, 1), lastEnd + REST); }
    }
  }

  function startSources(when, at, pass = 1) {
    stopStems(AC.currentTime, 0);
    sched = [];
    const first = song.segment(Math.min(Math.max(0, at), song.end - 0.05), pass);
    stemsPlaying = true;
    scheduleSegment(first, when);
    topUp();
    // the clock keeps the music going when the tab is in the background (rAF stops there)
    clearInterval(ticker);
    ticker = setInterval(topUp, 500);
  }

  function applyFeature(tc = 0.4) {
    if (!AC) return;
    const now = AC.currentTime;
    for (const [k, n] of Object.entries(nodes)) {
      const f = !featured || k === 'room' ? 1 : k === featured ? FEATURE_UP : FEATURE_DOWN;
      n.gain.gain.setTargetAtTime(f, now, tc || 0.001);
    }
  }

  function stopStems(when, fade) {
    for (const e of sched) for (const s of e.srcs) {
      try { s.stop(Math.max(when + fade + 0.05, AC.currentTime)); } catch { /* already stopped */ }
    }
    sched = [];
    clearInterval(ticker);
    ticker = null;
    stemsPlaying = false;
  }

  /** Hand the mix over to the stems at the same point in the song. */
  function handOver() {
    if (!api.playing || !mixPlaying || !buffers) return;
    const when = AC.currentTime + 0.15;
    // the same bar of the same pass (in the rest after the fermata: the top, when the rest is over)
    const resting = mixRestUntil > AC.currentTime;
    const p = resting ? { pos: 0, pass: 1 } : song.advance(mix.el.currentTime, mixPass, 0.15);
    startSources(resting ? mixRestUntil : when, p.ended ? 0 : p.pos, p.ended ? 1 : p.pass);
    // stems fade in over the crossfade while the mix fades out
    for (const n of Object.values(nodes)) {
      const g = n.gain.gain;
      const target = !featured || !n.panner ? 1 : n === nodes[featured] ? FEATURE_UP : FEATURE_DOWN;
      g.cancelScheduledValues(0);
      g.setValueAtTime(0, when);
      g.linearRampToValueAtTime(target, when + XFADE);
    }
    stopMix(when, XFADE);
  }

  // ---------- public ----------
  /** Nothing is fetched until the visitor asks for music: the mix streams the moment play is pressed. */
  api.prefetch = function () {};

  api.start = async function () {
    ensureGraph();
    await AC.resume();
    const now = AC.currentTime;
    master.gain.cancelScheduledValues(now);
    master.gain.setValueAtTime(master.gain.value, now);
    master.gain.linearRampToValueAtTime(0.95, now + 1.2);
    api.playing = true;
    if (useStems && buffers) {
      startSources(AC.currentTime + 0.12, cursor.pos, cursor.pass);
      return;
    }
    if (mixUrl) {
      mixPass = cursor.pass;
      mixRestUntil = 0;
      await playMix(cursor.pos);
      if (useStems) {
        if (!loading) loading = loadStems();
        loading.then(handOver, (err) => { console.info('[audio] stems unavailable, staying on the mix:', err?.message || err); });
      }
      return;
    }
    // stems only, no mix to bridge the wait
    if (!loading) loading = loadStems();
    await loading;
    if (!api.playing) return;
    startSources(AC.currentTime + 0.12, cursor.pos, cursor.pass);
  };

  api.stop = function () {
    if (!AC || !api.playing) return;
    const now = AC.currentTime;
    // remember where we are, so play resumes mid-song
    if (stemsPlaying) cursor = songPos(now);
    else if (mixPlaying) cursor = { pos: mix.el.currentTime, pass: mixPass };
    master.gain.cancelScheduledValues(now);
    master.gain.setValueAtTime(master.gain.value, now);
    master.gain.linearRampToValueAtTime(0, now + 0.8);
    stopStems(now, 0.8);
    stopMix(now + 0.8, 0.02);
    api.playing = false;
  };

  api.feature = function (name) {
    featured = PLAYERS.includes(name) ? name : null;
    if (stemsPlaying || buffers) applyFeature();
  };

  /** True when featuring can be heard (the stems are playing), false while only the mix plays. */
  Object.defineProperty(api, 'separable', { get: () => useStems });
  /** What is sounding: 'stems', 'mix' or 'idle' (for tests and the now-playing line). */
  Object.defineProperty(api, 'phase', { get: () => (!api.playing ? 'idle' : stemsPlaying ? 'stems' : mixPlaying ? 'mix' : 'loading') });

  const fwd = new THREE.Vector3(), up = new THREE.Vector3();
  api.updateSpace = function () {
    if (!AC || !api.playing) return;
    const cam = getCamera();
    const L = AC.listener;
    const now = AC.currentTime;
    cam.getWorldDirection(fwd);
    up.set(0, 1, 0).applyQuaternion(cam.quaternion);
    if (L.positionX) {
      L.positionX.setTargetAtTime(cam.position.x, now, 0.05); L.positionY.setTargetAtTime(cam.position.y, now, 0.05); L.positionZ.setTargetAtTime(cam.position.z, now, 0.05);
      L.forwardX.setTargetAtTime(fwd.x, now, 0.05); L.forwardY.setTargetAtTime(fwd.y, now, 0.05); L.forwardZ.setTargetAtTime(fwd.z, now, 0.05);
      L.upX.setTargetAtTime(up.x, now, 0.05); L.upY.setTargetAtTime(up.y, now, 0.05); L.upZ.setTargetAtTime(up.z, now, 0.05);
    } else {
      L.setPosition(cam.position.x, cam.position.y, cam.position.z);
      L.setOrientation(fwd.x, fwd.y, fwd.z, up.x, up.y, up.z);
    }
    if (nodes.room) {
      const d = cam.position.distanceTo(positions.center);
      nodes.room.roomDist.gain.setTargetAtTime(Math.min(1, 12 / Math.max(6, d)) * 0.8 + 0.1, now, 0.2);
    }
    if (mixPlaying && !stemsPlaying) {
      // the <audio> element plays the file straight through: fold it back into the loop region by hand for
      // the passes before the last, then let it run on into the written ending; after the fermata, rest, and
      // start again from the top
      const el = mix.el;
      if (mixRestUntil) {
        if (now >= mixRestUntil) { mixRestUntil = 0; mixPass = 1; el.currentTime = 0; el.play().catch(() => {}); }
      } else if (hasLoop && mixPass < song.passes && el.currentTime >= loopEndRaw) {
        el.currentTime = loopStart + (el.currentTime - loopEndRaw);
        mixPass++;
      } else if (el.ended || el.currentTime >= song.end) {
        el.pause();
        api.endings++;
        mixRestUntil = now + REST;
      }
      if (fromEvents) fromEvents(el.currentTime, api.levels);
      return;
    }
    // loudness of each player drives the musicians and the bulbs
    for (const k of PLAYERS) {
      const n = nodes[k];
      if (!n) continue;
      n.an.getFloatTimeDomainData(scratch);
      let sum = 0;
      for (let i = 0; i < scratch.length; i++) sum += scratch[i] * scratch[i];
      const rms = Math.sqrt(sum / scratch.length);
      const v = Math.min(1, rms * 6);
      api.levels[k] = v > api.levels[k] ? v : api.levels[k] * 0.9 + v * 0.1;
    }
  };

  /** Where the song is: { pos, pass, alt, phase } (tests, and the curious in the console). */
  api.where = function () {
    if (!AC) return { pos: cursor.pos, pass: cursor.pass, alt: false, phase: api.phase };
    if (stemsPlaying) {
      const t = AC.currentTime;
      const e = sched.find((x) => t >= x.when && t < x.when + (x.seg.to - x.seg.from));
      const p = songPos(t);
      return { pos: +p.pos.toFixed(2), pass: p.pass, alt: !!(e?.seg.alt && altBuffers), resting: !e, phase: api.phase, passes: song.passes, loopEnd: song.loopEnd, end: song.end };
    }
    if (mixPlaying) return { pos: +mix.el.currentTime.toFixed(2), pass: mixPass, alt: false, resting: mixRestUntil > AC.currentTime, phase: api.phase, passes: song.passes, loopEnd: song.loopEnd, end: song.end };
    return { pos: cursor.pos, pass: cursor.pass, alt: false, phase: api.phase };
  };
  /** Jump to a point of the road map (tests: hear the ending without waiting ten minutes). */
  api.seek = function (pos, pass = 1) {
    if (stemsPlaying) startSources(AC.currentTime + 0.05, pos, pass);
    else if (mixPlaying) { mix.el.currentTime = pos; mixPass = pass; mixRestUntil = 0; }
    else cursor = { pos, pass };
  };
  Object.defineProperty(api, 'alternatesReady', { get: () => !!altBuffers });
  api.plan = song;

  return api;
}
