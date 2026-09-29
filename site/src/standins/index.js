// Build a labelled stand-in for a layout entry whose glb is not there yet.
import * as THREE from 'three';
import { buildStallStandin } from './stall.js';
import {
  buildBandstandStandin, buildFerrisStandin, buildCarouselStandin, buildTreeStandin,
  buildGroundStandin, buildStringsStandin, buildTownStandin, buildChurchStandin,
} from './landmarks.js';
import { mats, mesh, signMesh } from './kit.js';

export { redrawSigns } from './kit.js';

let seed = 1;

export function buildStandin(entry) {
  const place = entry.place;
  if (place === 'band') return buildBandstandStandin();
  if (place === 'ferris') return buildFerrisStandin();
  if (place === 'carousel') return buildCarouselStandin();
  if (place) return buildStallStandin({ label: entry.label || place, place, seed: seed++ });
  switch (entry.kind) {
    case 'deco': return buildStallStandin({ label: entry.label || entry.id, deco: true, kind: String(entry.goods || entry.id).toLowerCase().replace(/^deco[-_]/, ''), seed: seed++ });
    case 'tree': return buildTreeStandin();
    case 'ground': return buildGroundStandin();
    case 'strings': return buildStringsStandin();
    case 'town': return buildTownStandin();
    case 'church': return buildChurchStandin();
    default: return labelledBox(entry.label || entry.id);
  }
}

/** The plainest stand-in: a crate with a sign, for anything the engine has no shape for. */
export function labelledBox(label) {
  const g = new THREE.Group();
  g.name = 'standin_box';
  g.add(mesh(new THREE.BoxGeometry(2, 2, 2), mats().woodDark, { y: 1 }));
  const s = signMesh(label, 2.2, 0.4);
  s.name = 'sign';
  s.position.set(0, 2.3, 1.02);
  g.add(s);
  return g;
}
