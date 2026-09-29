// The bandstand: two spotlights that can feature one player, and the players moving with their stems.
import * as THREE from 'three';
import { act } from './util.js';
import { actionHint, actionNote, SECTIONS } from '../content.js';

// Where the players stand on the bandstand (local metres) when the model has no act_<player> nodes.
export const DEFAULT_PLAYERS = { sax: [0.9, 1.6, 0.9], piano: [-2.1, 1.4, -0.8], bass: [-0.4, 1.6, -1.3], drums: [1.6, 1.4, -1.6] };

/** World positions for the stems' panners: each player plus the stage centre. */
export function bandPositions(market) {
  const band = market.places.band;
  const out = {};
  const center = band ? band.holder.localToWorld(new THREE.Vector3(0, 1.8, 0)) : new THREE.Vector3(0, 2, -5);
  out.center = center;
  for (const k of Object.keys(DEFAULT_PLAYERS)) {
    const node = band && playerNode(band, k);
    const slot = band?.nodes.slots[`slot_${k}`];
    out[k] = node ? node.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 1.2, 0))
      : slot ? slot.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 1.3, 0))
      : band ? band.holder.localToWorld(new THREE.Vector3(...DEFAULT_PLAYERS[k])) : center.clone();
  }
  return out;
}

/** The node that moves with a player: the instrument's act_ pivot, else the player figure at the slot. */
function playerNode(band, k) {
  return act(band, `act_${k}`) || act(band, `act_${k}ist`) || act(band, k === 'drums' ? 'act_drum' : `act_${k}_player`)
    || band.root.getObjectByName(`musician_${k}`) || null;
}

/** A beam and a floor pool that behave like a SpotLight for this file (position, target, intensity). */
function fakeSpot(color) {
  const g = new THREE.Group();
  g.target = new THREE.Object3D();
  const beamMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.035, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false });
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.8, 1, 24, 1, true).translate(0, -0.5, 0), beamMat);
  const poolMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false });
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const x = c.getContext('2d'), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.6, 'rgba(255,255,255,.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
  poolMat.map = new THREE.CanvasTexture(c);
  const pool = new THREE.Mesh(new THREE.CircleGeometry(1.2, 24).rotateX(-Math.PI / 2), poolMat);
  beam.name = 'engine_band_beam'; pool.name = 'engine_band_pool';
  beam.visible = false; // the beam shows only while one player is featured; at a distance it reads as a ghost
  g.add(beam);
  g.userData.fake = { beam, pool, beamMat, poolMat };
  const dir = new THREE.Vector3(), q = new THREE.Quaternion(), down = new THREE.Vector3(0, -1, 0);
  let k = 1;
  Object.defineProperty(g, 'intensity', {
    get: () => k,
    set: (v) => {
      k = v;
      beamMat.opacity = 0.035 * v; poolMat.opacity = 0.35 * v;
      // keep the beam pointing at the target, which feature() moves
      if (!pool.parent && g.target.parent) g.target.parent.add(pool);
      pool.position.copy(g.target.position).setY(g.target.position.y + 0.05);
      dir.subVectors(g.target.position, g.position);
      beam.scale.set(1, dir.length(), 1);
      g.quaternion.copy(q.setFromUnitVectors(down, dir.normalize()));
    },
  });
  return g;
}

export function createBandActions({ market, audio, say, lite, togglePlay }) {
  const band = market.places.band;
  if (!band) return { band: null, update() {} };
  const positions = bandPositions(market);
  const spots = [];
  const defs = lite ? [[[0, 3.8, 2.4], [0, 0.6, -0.5], 0xffc98a, 30]] : [[[-1.5, 3.8, 2.5], [-0.5, 0.6, -0.5], 0xffc98a, 26], [[2, 3.8, 2.2], [1, 0.6, -0.5], 0xff9ab0, 18]];
  for (const [p, t, color, intensity] of defs) {
    // The lite market has no light to spare for the stage: a soft beam and a pool of light stand in for the spot.
    const s = lite ? fakeSpot(color) : new THREE.SpotLight(color, intensity, 14, 0.6, 0.6, 1.6);
    s.name = 'engine_band_spot';
    s.position.fromArray(p);
    s.target.position.fromArray(t);
    band.holder.add(s, s.target);
    spots.push({ s, t0: s.target.position.clone(), base: lite ? 1 : intensity });
  }
  const players = {};
  for (const k of Object.keys(DEFAULT_PLAYERS)) {
    const node = playerNode(band, k);
    if (node) players[k] = { node, q0: node.quaternion.clone(), p0: node.position.clone() };
  }
  // the organizer's musicians: "play" while the band plays, "rest" otherwise
  const musicians = [];
  band.root.traverse((o) => { if (o.userData.musician) musicians.push(o.userData.musician); });
  // the drummer's brushes (instr_drums): they sweep with the drums stem
  const brushes = ['act_brush_l', 'act_brush_r'].map((n) => act(band, n)).filter(Boolean).map((node) => ({ node, q0: node.quaternion.clone() }));
  let featured = null;

  function feature(name) {
    featured = name;
    audio.feature(name);
    spots.forEach((sp) => {
      if (sp.s.userData.fake) sp.s.userData.fake.beam.visible = !!name;
      if (name) sp.s.target.position.copy(band.holder.worldToLocal(positions[name].clone().add(new THREE.Vector3(0, -0.3, 0))));
      else sp.s.target.position.copy(sp.t0);
    });
    const names = { sax: 'tenor sax', piano: 'piano', bass: 'double bass', drums: 'drums' };
    const pm = SECTIONS.band?.meta?.play || {};
    let play = audio.playing ? pm.playing || 'Listen for it in the mix.' : pm.stopped || 'Press play to hear it up front.';
    if (!audio.separable) play = pm.lite || 'The lite market plays the band as one mix, so this spotlight is for the eyes. Switch to the full market to hear it up front.';
    say(actionNote('band', name || 'whole', name ? `The spotlight is on the ${names[name]}. ${play}` : 'The whole band shares the light again.', { play }));
  }

  const e = new THREE.Euler(), q = new THREE.Quaternion();
  return {
    band: {
      hint: actionHint('band', 'Put one player in the spotlight.'),
      // the lite market streams one mix: the player buttons move the light only, and say so
      spotOnly: () => !audio.separable,
      acts: [
        { key: 'play', label: '▶ Play the ballad', fn: () => togglePlay(), play: true },
        { key: 'sax', label: 'Sax', fn: () => feature('sax'), spot: true }, { key: 'piano', label: 'Piano', fn: () => feature('piano'), spot: true },
        { key: 'bass', label: 'Bass', fn: () => feature('bass'), spot: true }, { key: 'drums', label: 'Drums', fn: () => feature('drums'), spot: true },
        { key: 'whole', label: 'Whole band', fn: () => feature(null) },
      ],
    },
    positions,
    update(dt, t, still) {
      const L = audio.levels;
      const on = audio.playing ? 1 : 0;
      for (const m of musicians) {
        if (m.playing !== audio.playing && m.play && m.rest) {
          m.playing = audio.playing;
          const [from, to] = m.playing ? [m.rest, m.play] : [m.play, m.rest];
          to.reset().play();
          from.crossFadeTo(to, 0.6, false);
        }
        if (!still) m.mixer.update(dt);
      }
      spots.forEach((sp, i) => { sp.s.intensity = sp.base * (0.85 + (i ? L.sax : L.bass) * 0.35 + (featured ? 0.2 : 0)); });
      if (still) return;
      const sway = (k, rx, ry, rz, dy = 0) => {
        const p = players[k];
        if (!p) return;
        e.set(rx, ry, rz);
        p.node.quaternion.copy(p.q0).multiply(q.setFromEuler(e));
        p.node.position.y = p.p0.y + dy;
      };
      sway('sax', -L.sax * 0.05, Math.sin(t * 0.7) * 0.06 * on, Math.sin(t * 1.3) * 0.05 * L.sax);
      sway('piano', L.piano * 0.02, 0, 0, L.piano * 0.01);
      sway('bass', 0, Math.sin(t * 0.8) * 0.05, -L.bass * 0.03);
      sway('drums', 0, Math.sin(t * 2.2) * 0.02 * on, 0, L.drums * 0.008);
      brushes.forEach((b, i) => {
        e.set(0, Math.sin(t * (i ? 4.4 : 2.2) + i) * 0.25 * L.drums * on, Math.sin(t * 2.2 + i * 1.3) * 0.12 * L.drums * on);
        b.node.quaternion.copy(b.q0).multiply(q.setFromEuler(e));
      });
      const ride = act(band, 'act_ride');
      if (ride) ride.rotation.x = Math.sin(t * 9) * 0.04 * L.drums;
    },
  };
}
