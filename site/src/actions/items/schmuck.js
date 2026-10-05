// The ornament shop (Christbaumschmuck, docs/adr/0004 and its round-9 revision): Mac asked for fewer interactions,
// each one a moment ("No need to be interactive in everything, but the one that interactive must be wow"). Only
// three things in the shop answer a click; everything else (the nutcracker, the smoking Räuchermännchen, the
// Herrnhut stars, the pickle, the display tree, the turning candle pyramid) is decoration.
//   act_orn_schwibbogen (+ act_orn_candle_0..6)  the hero: the candles wake the town   (shop/schwibbogen.js)
//   act_orn_harmonica_0..11                       the glass harmonica                  (shop/harmonica.js)
//   act_orn_mirrorball (cam_dive, cam_dive_target) the reflection dive                (shop/dive.js)
// and the shop's sparkle in the engine: the foxed mirror's reflection, the tinsel's glint, the pyramid's flickering
// candles and the smoker's smoke (shop/sparkle.js).
// The camera moments drive the camera themselves (interaction/camera.js drive); while one runs, the stop bar steps
// aside, the pointer picks nothing, and Escape, the Step back button or a tap brings the visitor back.
import * as THREE from 'three';
import { createHarmonica } from '../../shop/harmonica.js';
import { createSchwibbogen } from '../../shop/schwibbogen.js';
import { createDive } from '../../shop/dive.js';
import { createSparkle } from '../../shop/sparkle.js';
import { createTownWindows } from '../../shop/townWindows.js';
import { createLightWave } from '../../shop/lightWave.js';

const byIndex = (a, b) => a.node.name.localeCompare(b.node.name, 'en', { numeric: true });

/** What an ornament does, by its node name (the shop's items.json `action` says the same). */
export function ornamentAction(item) {
  const n = item.node.name;
  if (/^act_orn_harmonica_/i.test(n)) return 'harmonica';
  if (/^act_orn_mirrorball/i.test(n)) return 'dive';
  if (/^act_orn_(schwibbogen|candle_)/i.test(n)) return 'candles';
  return null; // decoration (no round-8 interactions are left)
}

export function createSchmuck(ctx) {
  const { market, items, scene, camera, motion, lite } = ctx;
  let place = null;
  let S = null; // the shop's parts and moments, once its place is there
  let town = null, wave = null;
  let driving = null;

  function onDrive(on, type) {
    driving = on ? type : null;
    const html = document.documentElement;
    if (on) html.dataset.moment = type; else delete html.dataset.moment;
    html.classList.toggle('closeup', !!on);
    ctx.picking?.()?.setEnabled(!on);
    ctx.onMoment?.(on ? type : null);
    if (!on) refreshBar();
  }

  const here = () => { const g = ctx.guide?.(); return !!g && g.here === 'schmuck' && g.arrived; };

  function setup(p) {
    if (place === p || !p) return;
    place = p;
    const all = items.of('schmuck', 'orn');
    const pick = (re) => all.filter((i) => re.test(i.node.name)).sort(byIndex);
    const harmonicaItems = pick(/^act_orn_harmonica_\d+$/i);
    const ball = pick(/^act_orn_mirrorball$/i)[0] || null;
    const arch = pick(/^act_orn_schwibbogen$/i)[0] || null;
    const candles = pick(/^act_orn_candle_\d+$/i);
    for (const i of all) i.node.userData.live = true;
    town ||= createTownWindows({ scene, market });
    wave ||= createLightWave({ getLights: () => ctx.lights?.() || [], getBloom: () => ctx.bloom?.() || null, motion });
    wave.patchBulbs(market.bulbMaterials);
    wave.patchGround(scene); // the light runs over the cobbles too
    const stopView = () => { const g = ctx.guide?.(); return g ? g.stopView() : { pos: camera.position.clone(), target: ctx.rig.controls.target.clone() }; };
    const dom = ctx.dom;
    S = {
      sparkle: createSparkle({ place: p, scene, camera, renderer: ctx.renderer, lite, motion }),
      harmonica: harmonicaItems.length && dom ? createHarmonica({
        items: harmonicaItems, dom, camera, rig: ctx.rig, motion,
        sfxLog: (e) => ctx.sfxLog?.(e),
        canPlay: () => here() && !driving && !ctx.reading?.(),
        say: (h) => ctx.say(h),
        place: p, stopView, onDrive,
      }) : null,
      schwibbogen: arch && candles.length ? createSchwibbogen({
        place: p, arch, candles, town, wave, rig: ctx.rig, camera, motion,
        sfx: (n, o) => ctx.sfx(n, o), announce: ctx.announce, stopView, onDrive,
        stepOut: (on) => ctx.stepOut?.(on),
      }) : null,
      dive: ball && dom ? createDive({
        place: p, ball, scene, camera, renderer: ctx.renderer, composer: ctx.composer?.(), rig: ctx.rig, lite, motion, stopView,
        renderNow: () => ctx.renderNow?.(), onDrive, announce: ctx.announce, dom,
      }) : null,
    };
    // the round-8 shop's interactions are gone: any old ornament left in a set is decoration
    for (const i of all) if (!ornamentAction(i)) i.clickable = false;
  }
  if (market.places.schmuck) setup(market.places.schmuck);

  function refreshBar() {
    const b = document.querySelector('#stopActs [data-action="candles"]');
    if (b && S?.schwibbogen) b.textContent = candleLabel();
  }
  const candleLabel = () => (S?.schwibbogen && ['waking', 'lit'].includes(S.schwibbogen.phase) ? 'Let the candles go out' : 'Light the Schwibbogen');

  function candles() {
    if (!S?.schwibbogen) return;
    if (S.dive?.active) S.dive.end();
    S.schwibbogen.toggle();
    refreshBar();
  }
  function diveIn() {
    if (!S?.dive || S.dive.active) return;
    S.dive.start(); // its drive takes the camera from the Schwibbogen's view, if that is where the visitor stands
  }

  function click(item) {
    if (!S) setup(market.places.schmuck);
    if (!S) return;
    const a = ornamentAction(item);
    if (a === 'harmonica') S.harmonica?.click(item);
    else if (a === 'dive') diveIn();
    else if (a === 'candles') candles();
  }

  /** Escape, Step back or a tap during a moment: come back out of it. True when there was one. */
  function end() {
    if (S?.dive?.active) { S.dive.end(); return true; }
    if (S?.schwibbogen?.driving) { S.schwibbogen.stepBack(); return true; }
    if (S?.harmonica?.leaning || S?.harmonica?.playing) { S.harmonica.stop(); return true; }
    return false;
  }

  const self = {
    kinds: { orn: click },
    addPlace(p) { if (p.id === 'schmuck') setup(p); },
    /** The stop bar's three buttons at the ornament shop. */
    actsList: () => [
      { key: 'candles', label: candleLabel(), fn: candles, has: () => !!S?.schwibbogen },
      { key: 'harmonica', label: 'Play the glass harmonica', fn: () => { if (!S?.dive?.active) S?.harmonica?.play(); }, has: () => !!S?.harmonica },
      { key: 'dive', label: 'Look into the mirror ball', fn: diveIn, has: () => !!S?.dive },
    ].filter((a) => !S || a.has()),
    get busy() { return driving; },
    end,
    /** Before the lighting module's update, and after it (the wave of light on lamps and bloom). */
    pre() { wave?.pre(); },
    post(dt) { wave?.post(dt); },
    /** Before the market is drawn (the mirror's reflection). */
    beforeRender() { S?.sparkle.beforeRender(); },
    /** A streamed shop got its full model. */
    refresh() { S?.sparkle.refresh(); if (S?.schwibbogen) town?.check(); },
    api: {
      schmuckActs: () => self.actsList(),
      /** For tests: the shop's state. */
      schmuck: () => (S ? {
        acts: self.actsList().map((a) => a.key),
        has: Object.fromEntries(self.actsList().map((x) => [x.key, true])),
        clickable: items.of('schmuck', 'orn').filter((i) => i.clickable).map((i) => i.node.name),
        busy: driving,
        harmonica: S.harmonica?.stats() || null,
        schwibbogen: S.schwibbogen?.stats() || null,
        dive: S.dive?.stats() || null,
        sparkle: S.sparkle.stats(),
        pyramid: (() => { const r = market.rides.find((x) => x.spinners?.some((s) => /^rot_pyramid/i.test(s.obj.name))); const s = r?.spinners.find((x) => /^rot_pyramid/i.test(x.obj.name)); return s ? { axis: s.axis, angle: +s.angle.toFixed(3) } : null; })(),
      } : null),
      /** For tests: the harmonica's baubles on screen (client px). */
      harmonicaPoints: () => S?.harmonica?.points() || [],
      /** For tests: ring bauble i as a brush would (velocity 0..1). */
      harmonicaStrike: (i, v = 0.6) => S?.harmonica?.strike(i, { velocity: v, source: 'test' }),
      /** For tests: the market's bulb gain at a distance from the wave's origin, now. */
      waveGainAt: (d) => wave?.gainAt(d) ?? 1,
      /** For tests: the bulbs' gain (the shader's curve) at a distance from the wave's origin, now. */
      waveBulbGainAt: (d) => wave?.bulbGainAt(d) ?? 1,
      /** For tests: the ground's wash (added warm light) at a distance from the wave's origin, now. */
      waveWashAt: (d) => wave?.washAt(d) ?? 0,
      shopEnd: () => end(),
    },
    retract() {
      // a walk away or home: the camera's new move cancels a moment's drive by itself
    },
    update(dt, t, still) {
      if (!S) return;
      S.sparkle.update(dt, t, still);
      S.harmonica?.update(dt, t, { here: here() && !driving, still });
      S.schwibbogen?.update(dt, t, still);
      if (S.schwibbogen && S.schwibbogen.phase === 'off' && S.lastPhase !== 'off') refreshBar();
      S.lastPhase = S.schwibbogen?.phase;
    },
  };
  return self;
}

export { THREE };
