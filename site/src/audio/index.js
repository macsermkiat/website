// The market's sound: the band (recorded stems, or the prototype's generative ballad as a fallback)
// and the synthesised stall sounds.
import { createStemsBand } from './stems.js';
import { createGenerativeBand } from './generative.js';
import { sfx, setMusicState } from './sfx.js';
import { setMuted, isMuted } from './context.js';

export function createAudio({ manifest, positions, getCamera, lite, warn }) {
  const samplesUrl = `${import.meta.env.BASE_URL}fallback/samples.json`;
  let band = manifest ? createStemsBand({ manifest, positions, getCamera, lite }) : null;
  let fallback = null;
  const levels = { sax: 0, piano: 0, bass: 0, drums: 0 };
  const useFallback = () => (fallback ??= createGenerativeBand({ samplesUrl, bandPos: positions.center, getCamera }));
  if (!band) band = useFallback();
  setMusicState(() => band.playing);

  const api = {
    levels,
    get playing() { return band.playing; },
    get mode() { return band.mode; },
    get bpm() { return band.bpm; },
    /** Whether featuring changes what you hear (false for the lite market's single mix). */
    get phase() { return band.phase || (band.playing ? band.mode : 'idle'); },
    get separable() { return band.separable !== false; },
    prefetch() { band.prefetch?.(); },
    /** The recorded band's place in its road map (null for the improvising fallback). */
    where() { return band.where?.() || null; },
    seek(pos, pass) { band.seek?.(pos, pass); },
    get endings() { return band.endings || 0; },
    get alternatesReady() { return !!band.alternatesReady; },
    async start() {
      try {
        await band.start();
      } catch (err) {
        if (band.mode !== 'stems') throw err;
        warn(`The recorded stems could not play (${err?.message || err}); the band improvises instead.`);
        band = useFallback();
        await band.start();
      }
    },
    stop() { band.stop(); },
    feature(name) { band.feature(name); },
    /** Stall sounds; silent while muted (no AudioContext is started for them either). */
    sfx: (name, ...a) => { if (!isMuted()) sfx(name, ...a); },
    /** The mute button: silences the band and the stall sounds together. */
    get muted() { return isMuted(); },
    setMuted,
    update(dt) {
      if (!band.playing) {
        for (const k in levels) levels[k] *= Math.exp(-dt * 3);
        return;
      }
      band.updateSpace();
      if (band.mode === 'stems') Object.assign(levels, band.levels);
      else {
        for (const k in levels) levels[k] *= Math.exp(-dt * (k === 'drums' ? 8 : k === 'sax' ? 2 : 4));
        for (const e of band.drain()) levels[e === 'drum' ? 'drums' : e] = 1;
      }
    },
  };
  return api;
}
