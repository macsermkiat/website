// Stand-ins for the landmarks and scenery: bandstand, Riesenrad, Karussell, tree, square, strings, town, church.
import * as THREE from 'three';
import { mats, mesh, empty, bulbString, catenary, colorMat, mergeStatic, rng, canvas, tex, signMesh } from './kit.js';
import { buildPerson } from './people.js';

export function buildBandstandStandin() {
  const M = mats();
  const g = new THREE.Group();
  g.name = 'standin_bandstand';
  const r = 3.8;
  g.add(mesh(new THREE.CylinderGeometry(r, r + 0.1, 0.6, 8), M.woodDark, { y: 0.3 }));
  g.add(mesh(new THREE.CylinderGeometry(r + 0.02, r + 0.02, 0.06, 8), M.counter, { y: 0.62 }));
  for (let i = 0; i < 3; i++) g.add(mesh(new THREE.BoxGeometry(1.6, 0.2, 0.4), M.woodDark, { y: 0.1 + i * 0.2, z: r + 0.5 - i * 0.3 }));
  for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2 + Math.PI / 8; g.add(mesh(new THREE.CylinderGeometry(0.08, 0.09, 3.6, 10), M.cream, { x: Math.cos(a) * (r - 0.2), y: 2.4, z: Math.sin(a) * (r - 0.2) })); }
  g.add(mesh(new THREE.ConeGeometry(r + 0.6, 1.8, 8, 1, true), M.canopy, { y: 5.1, ry: Math.PI / 8 }));
  g.add(mesh(new THREE.ConeGeometry(r + 0.66, 1.86, 8, 1, true), M.snow, { y: 5.15, ry: Math.PI / 8, name: 'snow_roof' }));
  g.add(mesh(new THREE.CircleGeometry(r + 0.6, 8), colorMat(0x2a1a22, 0.9), { y: 4.2, rx: Math.PI / 2, rz: Math.PI / 8 }));
  g.add(mesh(new THREE.SphereGeometry(0.18, 16, 12), M.brass, { y: 6.1 }));
  const eb = [];
  for (let i = 0; i < 8; i++) {
    const a0 = (i / 8) * Math.PI * 2, a1 = ((i + 1) / 8) * Math.PI * 2;
    for (let k = 0; k < 7; k++) { const a = a0 + ((a1 - a0) * k) / 7; eb.push(new THREE.Vector3(Math.cos(a) * (r + 0.62), 4.2, Math.sin(a) * (r + 0.62))); }
  }
  g.add(bulbString('bulbs_0', eb, { size: 1.2 }));
  const y = 0.63;
  const rr = rng(301);
  // piano + pianist
  const piano = new THREE.Group(); piano.name = 'act_piano'; piano.position.set(-2.1, y, -0.8); piano.rotation.y = 0.5;
  const pianoM = new THREE.MeshPhysicalMaterial({ color: 0x0c0a09, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.08 });
  piano.add(mesh(new THREE.BoxGeometry(1.5, 1.25, 0.6), pianoM, { y: 0.625 }));
  piano.add(mesh(new THREE.BoxGeometry(1.3, 0.03, 0.16), M.cream, { y: 0.78, z: 0.4 }));
  piano.add(mesh(new THREE.BoxGeometry(0.6, 0.08, 0.35), M.woodDark, { y: 0.5, z: 0.95 }));
  const pianist = buildPerson(rr, { seated: true, arms: 'play' }); pianist.position.set(0, 0.22, 0.95); pianist.rotation.y = Math.PI; piano.add(pianist);
  g.add(piano);
  // double bass
  const bass = new THREE.Group(); bass.name = 'act_bass'; bass.position.set(-0.4, y, -1.3); bass.rotation.y = 0.2;
  const bp = buildPerson(rr); bp.position.set(0.3, 0, 0); bass.add(bp);
  const bassWood = new THREE.MeshPhysicalMaterial({ color: 0x7a3a14, roughness: 0.35, clearcoat: 0.8 });
  const body = new THREE.Group(); body.position.set(-0.05, 0.2, 0.35); body.rotation.z = 0.15; bass.add(body);
  const low = mesh(new THREE.SphereGeometry(1, 20, 14), bassWood, { y: 0.42 }); low.scale.set(0.34, 0.42, 0.13); body.add(low);
  const up = mesh(new THREE.SphereGeometry(1, 20, 14), bassWood, { y: 0.95 }); up.scale.set(0.26, 0.32, 0.12); body.add(up);
  body.add(mesh(new THREE.CylinderGeometry(0.025, 0.03, 1.1, 8), colorMat(0x120c08, 0.4), { y: 1.7 }));
  g.add(bass);
  // drums
  const kit = new THREE.Group(); kit.name = 'act_drums'; kit.position.set(1.6, y, -1.6); kit.rotation.y = -0.35;
  const dr = buildPerson(rr, { seated: true, arms: 'play' }); dr.position.set(0, 0.22, -0.55); kit.add(dr);
  const shell = new THREE.MeshPhysicalMaterial({ color: 0x5a1320, roughness: 0.3, clearcoat: 1 });
  kit.add(mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.4, 24), shell, { y: 0.3, z: 0.25, rx: Math.PI / 2 }));
  kit.add(mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.14, 20), shell, { x: -0.35, y: 0.62 }));
  kit.add(mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.01, 28), M.brass, { x: 0.55, y: 1.05, z: 0.1, rz: -0.15, name: 'act_ride' }));
  kit.add(mesh(new THREE.CylinderGeometry(0.012, 0.012, 1, 6), M.metal, { x: 0.55, y: 0.52, z: 0.1 }));
  kit.add(mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.01, 24), M.brass, { x: -0.62, y: 0.9, z: 0.05 }));
  g.add(kit);
  // tenor sax
  const sx = new THREE.Group(); sx.name = 'act_sax'; sx.position.set(0.9, y, 0.9); sx.rotation.y = -0.3;
  const sp = buildPerson(rr, { arms: 'play' }); sx.add(sp);
  const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 1.5, 0.12), new THREE.Vector3(0.02, 1.3, 0.26), new THREE.Vector3(0.03, 0.9, 0.25), new THREE.Vector3(0.05, 0.72, 0.28), new THREE.Vector3(0.1, 0.72, 0.38), new THREE.Vector3(0.12, 0.86, 0.42)]);
  sx.add(mesh(new THREE.TubeGeometry(curve, 32, 0.035, 8), M.brass));
  sx.add(mesh(new THREE.CylinderGeometry(0.11, 0.04, 0.2, 16, 1, true), M.brass, { x: 0.12, y: 0.95, z: 0.42 }));
  g.add(sx);
  g.add(empty('light_0', 0, 3.6, 1.5));
  g.add(empty('cam_view', 0, 3.6, 11.5));
  g.add(empty('cam_target', 0, 1.9, 0));
  mergeStatic(g);
  return g;
}

export function buildFerrisStandin() {
  const M = mats();
  const g = new THREE.Group();
  g.name = 'standin_riesenrad';
  const Rw = 9, cy = 10.5;
  for (const sz of [-1, 1]) for (const sxx of [-1, 1]) {
    const a = new THREE.Vector3(0, cy, sz * 0.9), b = new THREE.Vector3(sxx * 5.2, 0, sz * 2.4);
    const m = mesh(new THREE.CylinderGeometry(0.14, 0.2, a.distanceTo(b), 8), M.frame);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    g.add(m);
  }
  g.add(mesh(new THREE.BoxGeometry(12, 0.3, 6), M.woodDark, { y: 0.15 }));
  const wheel = new THREE.Group(); wheel.name = 'rot_wheel'; wheel.position.y = cy; wheel.userData.axis = 'z';
  for (const z of [-0.7, 0.7]) {
    wheel.add(mesh(new THREE.TorusGeometry(Rw, 0.1, 6, 96), M.frame, { z }));
    wheel.add(mesh(new THREE.TorusGeometry(Rw - 0.8, 0.06, 5, 96), M.frame, { z }));
  }
  const N = 16;
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    for (const z of [-0.7, 0.7]) {
      const sp = mesh(new THREE.CylinderGeometry(0.04, 0.04, Rw, 5), M.frame, { z });
      sp.position.x = (Math.cos(a) * Rw) / 2; sp.position.y = (Math.sin(a) * Rw) / 2; sp.rotation.z = a - Math.PI / 2;
      wheel.add(sp);
    }
    wheel.add(mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.4, 6), M.frame, { x: Math.cos(a) * Rw, y: Math.sin(a) * Rw, rx: Math.PI / 2 }));
  }
  wheel.add(mesh(new THREE.CylinderGeometry(0.55, 0.55, 2.2, 16), M.frame, { rx: Math.PI / 2 }));
  const rim = [];
  for (const z of [-0.78, 0.78]) for (let i = 0; i < 80; i++) { const a = (i / 80) * Math.PI * 2; rim.push(new THREE.Vector3(Math.cos(a) * Rw, Math.sin(a) * Rw, z)); }
  wheel.add(bulbString('bulbs_rim', rim, { size: 1.6 }));
  mergeStatic(wheel);
  g.add(wheel);
  const cols = [0x9e1f33, 0x2f5c7a, 0xc99a2e, 0x3f6a3a];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    const gg = new THREE.Group(); gg.name = `gondola_${i}`;
    gg.position.set(Math.cos(a) * Rw, cy + Math.sin(a) * Rw, 0);
    const c = colorMat(cols[i % 4], 0.4, 0.3);
    gg.add(mesh(new THREE.CylinderGeometry(0.62, 0.55, 0.75, 14), c, { y: -1.05 }));
    gg.add(mesh(new THREE.CylinderGeometry(0.66, 0.66, 0.06, 14), M.cream, { y: -0.66 }));
    gg.add(mesh(new THREE.ConeGeometry(0.7, 0.35, 14), c, { y: -0.1 }));
    gg.add(mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 6), M.frame, { y: -0.4 }));
    gg.add(mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.18, 14, 1, true), M.lampGlass, { y: -0.82 }));
    mergeStatic(gg, /(?!)/);
    g.add(gg);
  }
  g.add(empty('light_0', 0, 2.2, 3));
  g.add(empty('cam_view', 8, 7.5, 26));
  g.add(empty('cam_target', 0, 9, 0));
  const sign = signMesh('Riesenrad', 3.4, 0.55); sign.name = 'sign'; sign.position.set(0, 1.4, 3.05); g.add(sign);
  mergeStatic(g);
  return g;
}

function horseGeo() {
  const s = new THREE.Shape();
  s.moveTo(-0.55, 0.05); s.bezierCurveTo(-0.6, 0.2, -0.45, 0.3, -0.25, 0.3); s.lineTo(0.25, 0.3); s.bezierCurveTo(0.4, 0.32, 0.48, 0.45, 0.52, 0.62);
  s.lineTo(0.58, 0.78); s.bezierCurveTo(0.62, 0.86, 0.75, 0.82, 0.8, 0.72); s.lineTo(0.74, 0.66); s.lineTo(0.62, 0.66); s.bezierCurveTo(0.6, 0.55, 0.55, 0.45, 0.5, 0.35);
  s.bezierCurveTo(0.5, 0.2, 0.45, 0.08, 0.38, 0.02); s.lineTo(0.62, -0.25); s.lineTo(0.56, -0.3); s.lineTo(0.3, -0.05);
  s.lineTo(0.15, -0.08); s.lineTo(0.05, -0.45); s.lineTo(-0.03, -0.44); s.lineTo(0, -0.08);
  s.lineTo(-0.3, -0.06); s.lineTo(-0.5, -0.4); s.lineTo(-0.57, -0.37); s.lineTo(-0.42, -0.02);
  s.bezierCurveTo(-0.55, 0, -0.7, 0.1, -0.78, 0.02); s.lineTo(-0.8, -0.02); s.bezierCurveTo(-0.7, -0.05, -0.6, -0.02, -0.55, 0.05);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.18, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.04, bevelSegments: 1, curveSegments: 6 });
  g.translate(0, 0, -0.09);
  return g;
}

export function buildCarouselStandin() {
  const M = mats();
  const g = new THREE.Group();
  g.name = 'standin_karussell';
  g.add(mesh(new THREE.CylinderGeometry(4.4, 4.5, 0.45, 40), colorMat(0x5a1a24, 0.5), { y: 0.22 }));
  g.add(mesh(new THREE.TorusGeometry(4.45, 0.05, 6, 64), M.brass, { y: 0.45, rx: Math.PI / 2 }));
  const rot = new THREE.Group(); rot.name = 'rot_platform'; rot.userData.axis = 'y';
  rot.add(mesh(new THREE.CylinderGeometry(4.2, 4.2, 0.08, 40), M.counter, { y: 0.5 }));
  rot.add(mesh(new THREE.CylinderGeometry(0.8, 0.8, 3.3, 24), M.brass, { y: 2.1 }));
  rot.add(mesh(new THREE.CylinderGeometry(0.82, 0.82, 2.2, 16, 1, true), M.lampGlass, { y: 2.1 }));
  rot.add(mesh(new THREE.ConeGeometry(5, 1.7, 40, 1, true), M.canopy, { y: 4.55 }));
  rot.add(mesh(new THREE.ConeGeometry(5.05, 1.75, 40, 1, true), M.snow, { y: 4.6, name: 'snow_canopy' }));
  rot.add(mesh(new THREE.CylinderGeometry(5, 5, 0.6, 40, 1, true), M.canopy, { y: 3.45 }));
  rot.add(mesh(new THREE.CircleGeometry(5, 40), colorMat(0x2a1a22, 0.9), { y: 3.7, rx: Math.PI / 2 }));
  rot.add(mesh(new THREE.SphereGeometry(0.22, 14, 10), M.brass, { y: 5.5 }));
  const eb = [];
  for (let i = 0; i < 60; i++) { const a = (i / 60) * Math.PI * 2; eb.push(new THREE.Vector3(Math.cos(a) * 5.05, 3.15, Math.sin(a) * 5.05)); }
  rot.add(bulbString('bulbs_ring', eb, { size: 1.3 }));
  const hg = horseGeo();
  const horseM = new THREE.MeshPhysicalMaterial({ color: 0xf3ece0, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.1 });
  const saddle = colorMat(0x9e1f33, 0.4);
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2, r = i % 2 ? 2.4 : 3.4;
    rot.add(mesh(new THREE.CylinderGeometry(0.035, 0.035, 3.1, 8), M.brass, { x: Math.cos(a) * r, y: 2.05, z: Math.sin(a) * r }));
    const h = new THREE.Group(); h.name = `horse_${i}`;
    h.position.set(Math.cos(a) * r, 1.5, Math.sin(a) * r); h.rotation.y = -a + Math.PI / 2;
    h.add(mesh(hg, horseM));
    h.add(mesh(new THREE.BoxGeometry(0.32, 0.06, 0.3), saddle, { x: -0.05, y: 0.32 }));
    h.add(mesh(new THREE.BoxGeometry(0.18, 0.3, 0.06), M.brass, { x: 0.48, y: 0.55, rz: -0.6 }));
    rot.add(h);
  }
  mergeStatic(rot);
  g.add(rot);
  g.add(empty('light_0', 0, 2.6, 0));
  g.add(empty('cam_view', -8, 5, 11));
  g.add(empty('cam_target', 0, 2.5, 0));
  mergeStatic(g);
  return g;
}

export function buildTreeStandin() {
  const M = mats();
  const g = new THREE.Group(); g.name = 'standin_tree';
  const r = rng(99);
  g.add(mesh(new THREE.CylinderGeometry(0.35, 0.45, 1.4, 10), M.woodDark, { y: 0.7 }));
  for (let i = 0; i < 6; i++) {
    const rad = 3.4 - i * 0.52, h = 2.7;
    g.add(mesh(new THREE.ConeGeometry(rad, h, 24, 3), M.needles, { y: 1.6 + i * 1.45 + h / 2, ry: r() * 6 }));
    g.add(mesh(new THREE.ConeGeometry(rad * 0.92, h * 0.4, 24, 1, true), M.snow, { y: 1.6 + i * 1.45 + h * 0.82, name: `snow_${i}` }));
  }
  const st = new THREE.Shape();
  for (let i = 0; i < 10; i++) { const a = (i / 10) * Math.PI * 2 + Math.PI / 2, rr = i % 2 ? 0.22 : 0.55; i ? st.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : st.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
  const star = mesh(new THREE.ExtrudeGeometry(st, { depth: 0.1, bevelEnabled: false }), new THREE.MeshStandardMaterial({ name: 'bulb_warm', color: 0xffe2a0, emissive: 0xffc860, emissiveIntensity: 6 }), { y: 11.3, z: -0.05, name: 'bulbs_star' });
  g.add(star);
  const warm = [], cold = [];
  for (let i = 0; i < 180; i++) { const t = i / 180, y = 1.8 + t * 9, rr = (1 - t) * 3.2 + 0.15, a = t * Math.PI * 2 * 9; (i % 6 === 0 ? cold : warm).push(new THREE.Vector3(Math.cos(a) * rr, y, Math.sin(a) * rr)); }
  g.add(bulbString('bulbs_0', warm, { size: 1.2 }));
  g.add(bulbString('bulbs_1', cold, { cold: true, size: 1.2 }));
  const om = [M.red, M.brass, colorMat(0x2f5c7a, 0.25, 0.6)];
  for (let i = 0; i < 46; i++) { const t = r() * 0.9, y = 1.9 + t * 9, rr = (1 - t) * 3.1, a = r() * 6.28; g.add(mesh(new THREE.SphereGeometry(0.11, 10, 8), om[i % 3], { x: Math.cos(a) * rr, y, z: Math.sin(a) * rr })); }
  g.add(empty('light_0', 0, 5, 3.5));
  mergeStatic(g);
  return g;
}

export function buildGroundStandin() {
  const M = mats();
  const g = new THREE.Group(); g.name = 'standin_square';
  g.add(mesh(new THREE.PlaneGeometry(260, 260), M.cobble, { rx: -Math.PI / 2 }));
  const R = rng(5);
  const sn = canvas(512, 512, (c, w, h) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 2500; i++) { const x = R() * w, y = R() * h, rr = 4 + R() * 22; const gr = c.createRadialGradient(x, y, 0, x, y, rr); gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = gr; c.fillRect(x - rr, y - rr, rr * 2, rr * 2); }
  });
  const cover = mesh(new THREE.PlaneGeometry(220, 220), new THREE.MeshStandardMaterial({ color: 0xf2f5ff, roughness: 0.8, alphaMap: tex(sn, { srgb: false, repeat: [16, 16] }), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }), { rx: -Math.PI / 2, y: 0.01, name: 'snow_ground' });
  cover.receiveShadow = true;
  g.add(cover);
  return g;
}

export function buildStringsStandin() {
  const M = mats();
  const g = new THREE.Group(); g.name = 'standin_strings';
  const poles = [[-15, 4], [-7.5, 6.5], [0, 7.5], [7.5, 6.5], [15, 4], [-10.5, -6.5], [10.5, -6.5], [-3.5, -9.5], [3.5, -9.5], [-17.5, -3], [-17.5, 5], [-17.5, 13], [17.5, -3], [17.5, 5], [17.5, 13], [-7, -18], [1, -18], [10, -18]];
  const H = 6.2;
  const lamp = new THREE.MeshStandardMaterial({ name: 'bulb_warm', color: 0xffe0b0, emissive: 0xffb45a, emissiveIntensity: 5 });
  const lamps = [];
  poles.forEach(([x, z], i) => {
    g.add(mesh(new THREE.CylinderGeometry(0.08, 0.11, H, 8), M.woodDark, { x, y: H / 2, z }));
    g.add(mesh(new THREE.BoxGeometry(0.28, 0.4, 0.28), M.darkMetal, { x, y: H - 0.1, z }));
    g.add(mesh(new THREE.ConeGeometry(0.24, 0.2, 4), M.darkMetal, { x, y: H + 0.18, z, ry: Math.PI / 4 }));
    lamps.push(mesh(new THREE.BoxGeometry(0.2, 0.3, 0.2), lamp, { x, y: H - 0.12, z }));
    if (i % 3 === 0) g.add(empty(`light_pole_${i}`, x, H - 0.4, z));
  });
  lamps.forEach((l, i) => { l.name = `bulbs_lamp_${i}`; g.add(l); });
  const spans = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [4, 6], [5, 7], [7, 8], [8, 6], [1, 7], [3, 8], [2, 7], [2, 8], [1, 5], [3, 6], [9, 10], [10, 11], [12, 13], [13, 14], [9, 12], [11, 1], [14, 3], [10, 13], [5, 9], [6, 12], [15, 16], [16, 17], [15, 7], [17, 8], [15, 5], [17, 6]];
  const wire = new THREE.MeshBasicMaterial({ name: 'standin_wire', color: 0x111318 });
  const bulbPts = [];
  spans.forEach(([i, j]) => {
    const a = new THREE.Vector3(poles[i][0], H - 0.3, poles[i][1]), b = new THREE.Vector3(poles[j][0], H - 0.3, poles[j][1]);
    const len = a.distanceTo(b);
    const pts = catenary(a, b, len * 0.09, Math.ceil(len * 2));
    g.add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length * 2, 0.012, 3), wire));
    pts.forEach((p, k) => { if (k && k < pts.length - 1) bulbPts.push(p.clone().add(new THREE.Vector3(0, -0.08, 0))); });
  });
  g.add(bulbString('bulbs_strings', bulbPts, { size: 1.1 }));
  mergeStatic(g);
  return g;
}

function facade(seed, lit) {
  const r = rng(seed);
  const col = ['#d9c7a8', '#c9a98a', '#b9b0a0', '#d6b48c', '#a9b3b8', '#caa8a0'][seed % 6];
  const c = canvas(256, 256, (g, w, h) => {
    g.fillStyle = col; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.05})`; g.fillRect(r() * w, r() * h, 3, 3); }
    g.fillStyle = '#3a2418'; [0, 84, 168, 252].forEach((y) => g.fillRect(0, y - 4, w, 8)); [0, 64, 128, 192, 252].forEach((x) => g.fillRect(x - 4, 0, 8, h));
    g.lineWidth = 7; g.strokeStyle = '#3a2418';
    for (let rr = 0; rr < 3; rr++) { g.beginPath(); g.moveTo(0, rr * 84); g.lineTo(64, rr * 84 + 84); g.moveTo(256, rr * 84); g.lineTo(192, rr * 84 + 84); g.stroke(); }
    for (let rr = 0; rr < 3; rr++) for (let cc = 0; cc < 2; cc++) { const x = 76 + cc * 64, y = 18 + rr * 84; g.fillStyle = '#1a1a22'; g.fillRect(x, y, 40, 50); g.fillStyle = '#3a2418'; g.fillRect(x + 18, y, 4, 50); g.fillRect(x, y + 23, 40, 4); }
  });
  const e = canvas(256, 256, (g, w, h) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, w, h);
    for (let rr = 0; rr < 3; rr++) for (let cc = 0; cc < 2; cc++) {
      if (r() < lit) { const x = 76 + cc * 64, y = 18 + rr * 84; const gr = g.createLinearGradient(0, y, 0, y + 50); gr.addColorStop(0, '#ffcf7a'); gr.addColorStop(1, '#d9812e'); g.fillStyle = gr; g.fillRect(x, y, 40, 50); g.fillStyle = '#000'; g.fillRect(x + 18, y, 4, 50); g.fillRect(x, y + 23, 40, 4); }
    }
  });
  return { map: c, emissiveMap: e };
}

export function buildTownStandin({ withChurch = true } = {}) {
  const M = mats();
  const g = new THREE.Group(); g.name = 'standin_town';
  const R = rng(64);
  const variants = []; for (let i = 0; i < 6; i++) variants.push(facade(i + 3, 0.45));
  const roofM = new THREE.MeshStandardMaterial({ name: 'standin_town_roof', map: M.roof.map.clone(), color: 0xa05a44, roughness: 0.85 });
  roofM.map.repeat.set(3, 3);
  const matsBy = new Map();
  const place = (x, z, ry, w, h, d, v) => {
    const f = variants[v % variants.length];
    const key = `${v % 6}_${Math.round(w)}_${Math.round(h)}`;
    if (!matsBy.has(key)) {
      const map = tex(f.map, { repeat: [w / 6, h / 8] }), em = tex(f.emissiveMap, { repeat: [w / 6, h / 8] });
      matsBy.set(key, new THREE.MeshStandardMaterial({ name: `standin_facade_${key}`, map, emissiveMap: em, emissive: 0xffffff, emissiveIntensity: 1.3, roughness: 0.9 }));
    }
    const house = new THREE.Group(); house.position.set(x, 0, z); house.rotation.y = ry;
    house.add(mesh(new THREE.BoxGeometry(w, h, d), matsBy.get(key), { y: h / 2 }));
    const tri = new THREE.Shape(); tri.moveTo(-w / 2 - 0.3, 0); tri.lineTo(0, w * 0.55); tri.lineTo(w / 2 + 0.3, 0); tri.closePath();
    house.add(mesh(new THREE.ExtrudeGeometry(tri, { depth: d + 0.6, bevelEnabled: false }), roofM, { y: h, z: -d / 2 - 0.3 }));
    g.add(house);
  };
  let v = 0;
  for (let i = 0; i < 22; i++) { const a = -Math.PI * 0.95 + (i / 21) * Math.PI * 0.9, r = 47 + R() * 6; place(Math.cos(a) * r, Math.sin(a) * r, -a - Math.PI / 2, 5 + R() * 3, 7 + R() * 6, 7, v++); }
  for (let i = 0; i < 8; i++) { const a = Math.PI * 0.12 + (i / 7) * Math.PI * 0.76, r = 58 + R() * 6; place(Math.cos(a) * r, Math.sin(a) * r, -a - Math.PI / 2, 5 + R() * 3, 7 + R() * 5, 7, v++); }
  g.userData.roofMaterial = roofM;
  mergeStatic(g);
  return g;
}

export function buildChurchStandin() {
  const M = mats();
  const ch = new THREE.Group(); ch.name = 'standin_church';
  const roofM = colorMat(0x8a4a38, 0.85);
  ch.add(mesh(new THREE.BoxGeometry(12, 14, 24), M.stone, { y: 7, z: -10 }));
  const nr = new THREE.Shape(); nr.moveTo(-6.4, 0); nr.lineTo(0, 6); nr.lineTo(6.4, 0); nr.closePath();
  ch.add(mesh(new THREE.ExtrudeGeometry(nr, { depth: 24, bevelEnabled: false }), roofM, { y: 14, z: -22 }));
  ch.add(mesh(new THREE.BoxGeometry(6, 28, 6), M.stone, { y: 14, z: 3 }));
  ch.add(mesh(new THREE.ConeGeometry(4.4, 16, 4), colorMat(0x3a5a52, 0.6, 0.4), { y: 36, z: 3, ry: Math.PI / 4 }));
  ch.add(mesh(new THREE.CircleGeometry(1.3, 24), new THREE.MeshStandardMaterial({ color: 0xfff0d0, emissive: 0xffe0a0, emissiveIntensity: 2.4 }), { y: 22, z: 6.02 }));
  const win = new THREE.MeshStandardMaterial({ color: 0x302010, emissive: 0xffa040, emissiveIntensity: 1.8 });
  for (let i = 0; i < 3; i++) ch.add(mesh(new THREE.PlaneGeometry(1.2, 3.4), win, { y: 9, x: -6.02, z: -4 - i * 6, ry: -Math.PI / 2 }));
  mergeStatic(ch);
  return ch;
}
