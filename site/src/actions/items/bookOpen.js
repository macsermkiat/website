// The vendor's open hardback (site/public/models/book_open.glb, blender/props/set_bookopen.py) as the book a
// visitor opens at the Bücherstand: the clicked book's own cover on its front board, the words printed on its
// write_page_left / write_page_right, and its act_page_turn leaf turning with the next spread's words on it.
//
// The model stands open. To fly to the counter closed and open there, the static mesh is split at the spine
// once (each triangle by the side its centre lies on) and the left half, with its cover and page, is hinged
// on the spine so it can fold over the right one.
//
// buildVendorBook() returns the same object as books.js buildOpenBook(), so the reading and the flights are the
// same for both; books.js falls back to its own procedural book when the model is missing.
import * as THREE from 'three';
import inventory from 'virtual:market-inventory';
import { loadGlb } from '../../engine/loader.js';
import { areaFromWriteMesh, printOnto } from '../../world/surfaces.js';
import { renderPage } from '../../world/text.js';
import { boxOf } from './common.js';

const V = THREE.MathUtils.degToRad(10); // each half's lean (set_bookopen.py OPEN_V)
const FOLD = Math.PI - 2 * V; // the left half laid over the right
const TURN = -FOLD; // act_page_turn: the leaf from under the right page to under the left

const templates = new Map(); // file -> Promise<template | null>

/** The model, prepared once (null when it cannot be loaded). Later books are clones of it. */
export function loadVendorBook({ lite = false, warn = (m) => console.warn('[market]', m) } = {}) {
  const sets = inventory.props?.standalone || [];
  const entry = sets.find((s) => /book_open/.test(s.model || '')) || { model: 'book_open.glb', lite: 'book_open.lite.glb' };
  const have = (f) => f && (!inventory.models || inventory.models.includes(f));
  const file = [lite ? entry.lite : null, entry.model, entry.lite].find(have);
  if (!file) return Promise.resolve(null);
  if (!templates.has(file)) {
    templates.set(file, loadGlb(file).then((root) => prepare(root)).catch((e) => { warn(`book_open: ${e?.message || e}; the engine's own book opens instead`); return null; }));
  }
  return templates.get(file);
}

/** Split the static mesh at the spine and hinge the left half; find the pages, the leaf and the camera. */
function prepare(root) {
  root.updateWorldMatrix(true, true);
  const get = (n) => root.getObjectByName(n);
  const pageL = get('write_page_left'), pageR = get('write_page_right'), act = get('act_page_turn');
  if (!pageL || !pageR) throw new Error('no write_page_left / write_page_right');
  const left = new THREE.Group();
  left.name = 'engine_book_left';
  root.add(left);
  const inv = root.matrixWorld.clone().invert();
  const meshes = [];
  root.traverse((o) => { if (o.isMesh) meshes.push(o); });
  const actNodes = new Set();
  act?.traverse((o) => actNodes.add(o));
  for (const m of meshes) {
    if (actNodes.has(m)) continue;
    const named = (re) => { for (let p = m; p && p !== root; p = p.parent) if (re.test(p.name || '')) return p; return null; };
    // the left page and the cover go over whole with the left half
    const whole = named(/^(write_page_left|book_open_cover)$/);
    if (whole) { reparent(whole, left, root); continue; }
    if (named(/^write_page_right/)) continue;
    // a static mesh: its triangles left of the spine go to the left half
    const g = m.geometry;
    const pos = g.attributes.position;
    const idx = g.index ? g.index.array : [...Array(pos.count).keys()];
    const toRoot = inv.clone().multiply(m.matrixWorld);
    const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
    const L = [], R = [];
    for (let i = 0; i < idx.length; i += 3) {
      a.fromBufferAttribute(pos, idx[i]).applyMatrix4(toRoot);
      b.fromBufferAttribute(pos, idx[i + 1]).applyMatrix4(toRoot);
      c.fromBufferAttribute(pos, idx[i + 2]).applyMatrix4(toRoot);
      ((a.x + b.x + c.x) / 3 < 0 ? L : R).push(idx[i], idx[i + 1], idx[i + 2]);
    }
    if (!L.length) continue;
    const half = (list) => {
      const h = new THREE.BufferGeometry();
      for (const [k, attr] of Object.entries(g.attributes)) h.setAttribute(k, attr);
      h.setIndex(list);
      h.boundingBox = null; h.boundingSphere = null;
      return h;
    };
    const lm = new THREE.Mesh(half(L), m.material);
    lm.name = `${m.name}_left`;
    lm.matrix.copy(toRoot); lm.matrix.decompose(lm.position, lm.quaternion, lm.scale);
    left.add(lm);
    m.geometry = half(R);
  }
  // the pages are printed on the paper itself: each write_ page (which fills the opening the vendor left in the
  // page) takes the paper's own print, with the UVs of the paper's vertices at its corners, so no lighter card
  // shows under the words (world/surfaces.js printOnto, as for the Bierdeckel)
  const paperMeshes = [];
  root.traverse((o) => { if (o.isMesh && !/^write_/.test(o.name || '')) paperMeshes.push(o); });
  const pages = [];
  root.traverse((o) => { if (o.isMesh && /^write_page/.test(o.name || '')) pages.push(o); });
  for (const o of pages) printOnto(o, root, paperMeshes);
  const box = new THREE.Box3().setFromObject(root);
  return { root, size: box.getSize(new THREE.Vector3()), box };
}

/** Move `node` under `to` keeping where it is (both under `root`). */
function reparent(node, to, root) {
  root.updateWorldMatrix(true, true);
  const m = to.matrixWorld.clone().invert().multiply(node.matrixWorld);
  to.add(node);
  m.decompose(node.position, node.quaternion, node.scale);
}

/**
 * An open book for shelf book `n` (description `d`), in `frame` (the stall's holder), from the prepared model.
 * Local frame of the returned group, as books.js expects: X across the cover, Y up the spine, Z out of the front
 * cover; s = 1 is the shelf book's size, `S` the size it is read at; the group's origin is the middle of the spine.
 */
export function buildVendorBook(tpl, n, d, frame) {
  const root = tpl.root.clone(true);
  const Hv = tpl.size.y;
  const shelf = boxOf(n, n);
  const ss = shelf.getSize(new THREE.Vector3());
  const axes = [['x', ss.x], ['y', ss.y], ['z', ss.z]].sort((a, b) => a[1] - b[1]);
  const H = Math.max(0.1, axes[2][1]);
  const k0 = H / Hv; // model units -> shelf size
  const group = new THREE.Group();
  group.name = `open_${n.name}`;
  const spine = new THREE.Group(), tilt = new THREE.Group();
  group.add(spine);
  spine.add(tilt);
  tilt.add(root);
  root.scale.setScalar(k0);
  root.position.set(0, -tpl.box.min.y * k0 - (Hv * k0) / 2, 0);
  const left = root.getObjectByName('engine_book_left');
  const act = root.getObjectByName('act_page_turn');
  const get = (name) => root.getObjectByName(name);
  // the clicked book's own cover on the front board
  const coverNode = get('book_open_cover');
  const cover = coverOf(n);
  const coverMesh = coverNode && (coverNode.isMesh ? coverNode : coverNode.children.find((c) => c.isMesh));
  let coverGeo = null;
  if (coverMesh && cover) {
    coverGeo = coverMesh.geometry.clone();
    const uv = coverGeo.attributes.uv;
    const [u0, v0, u1, v1] = cover.uv;
    const out = new Float32Array(uv.count * 2);
    for (let i = 0; i < uv.count; i++) { out[i * 2] = u0 + uv.getX(i) * (u1 - u0); out[i * 2 + 1] = v0 + uv.getY(i) * (v1 - v0); }
    coverGeo.setAttribute('uv', new THREE.BufferAttribute(out, 2));
    coverMesh.geometry = coverGeo;
    coverMesh.material = cover.material;
  } else if (coverMesh) {
    coverMesh.material = coverMesh.material.clone();
    coverMesh.material.map = null;
    coverMesh.material.color.set(0x5a2a20);
  }
  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.userData.itemFx = true; } });
  // the writing areas (from the pages' own UVs) and the leaf's two sides
  root.updateWorldMatrix(true, true);
  const faces = {};
  const L = areaFromWriteMesh(get('write_page_left')), R = areaFromWriteMesh(get('write_page_right'));
  if (!L || !R) { console.warn('[market] book_open: no writing area on its pages', !!L, !!R); return null; }
  faces.left = L; faces.right = R;
  const tf = act && get('write_page_turn_front') && areaFromWriteMesh(get('write_page_turn_front'), act);
  const tb = act && get('write_page_turn_back') && areaFromWriteMesh(get('write_page_turn_back'), act);
  const camR = get('cam_read_book'), camT = get('cam_read_book_target');
  // closed: the left half folded over the right, the whole turned flat; its centre on the group's origin
  let openK = 1;
  const setOpen = (k) => {
    openK = k;
    if (left) left.rotation.y = FOLD * (1 - k);
    tilt.rotation.y = V * (1 - k);
  };
  setOpen(0);
  tilt.updateWorldMatrix(true, true);
  const closedC = new THREE.Box3().setFromObject(tilt).getCenter(new THREE.Vector3()).applyMatrix4(spine.matrixWorld.clone().invert());
  const setClosedOffset = (k) => { spine.position.copy(closedC).multiplyScalar(-k); };
  setClosedOffset(1);
  // the shelf book's pose, in this frame: its axes (width, height, thickness) onto X, Y, Z
  const basis = (() => {
    const v = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
    const X = v[axes[1][0]].clone(), Y = v[axes[2][0]].clone();
    const Z = new THREE.Vector3().crossVectors(X, Y);
    return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(X, Y, Z));
  })();
  frame.add(group);
  frame.updateWorldMatrix(true, false);
  const fInv = frame.matrixWorld.clone().invert();
  const fQi = frame.getWorldQuaternion(new THREE.Quaternion()).invert();
  const fS = frame.getWorldScale(new THREE.Vector3()).x || 1;
  let world = { p: new THREE.Vector3(), q: new THREE.Quaternion(), s: 1 };
  const leafPages = [];
  const clearLeaf = () => { while (leafPages.length) leafPages.pop().dispose(); };
  return {
    group, W: (tpl.size.x / 2) * k0, H, T: tpl.size.z * k0, S: 1 / k0, faces, paper: null, fromModel: true,
    // about 19 lines of body text to a page (the procedural book's 21 lines are on a taller page)
    base: R.h / 19,
    get openK() { return openK; },
    /** The reading view: from the maker's cam_read_book side, as far back as the whole spread needs on this screen. */
    readView(camera) {
      group.updateWorldMatrix(true, true);
      const s = new THREE.Vector3().setFromMatrixScale(root.matrixWorld).x || 1;
      const target = camT ? camT.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0, 0, 0).applyMatrix4(group.matrixWorld);
      const dir = camR ? camR.getWorldPosition(new THREE.Vector3()).sub(target).normalize() : new THREE.Vector3(0, 0, 1).transformDirection(group.matrixWorld);
      const t = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      const fill = 0.86;
      const d = Math.max((tpl.size.y * s) / (2 * t * fill), (tpl.size.x * s) / (2 * t * (camera.aspect || 16 / 9) * fill));
      return { pos: target.clone().addScaledVector(dir, d), target, near: 0.02 };
    },
    /**
     * Turn the leaf: forward (dir > 0) from the right page over to the left, or back. The leaf carries the pages
     * it is turning (from, to: { faces: { left, right } }); mid() changes the words on the pages under it.
     */
    turn(dir, mid, anim, from, to) {
      if (!act) { mid(); return; }
      clearLeaf();
      const put = (face, pg) => {
        if (!face || !pg) return;
        const h = renderPage(pg, { theme: 'print', glow: 0, align: pg.align || 'left', w: face.w, z: 0.0004 });
        face.area.add(h.group);
        leafPages.push(h);
      };
      // forward: the front lifts the page being left (the old right), the back lands as the new left page
      if (dir > 0) { put(tf, from?.faces?.right); put(tb, to?.faces?.left); } else { put(tb, from?.faces?.left); put(tf, to?.faces?.right); }
      const a0 = dir > 0 ? 0 : TURN, a1 = dir > 0 ? TURN : 0;
      let swapped = false;
      act.rotation.y = a0;
      anim.add(0.8, (k) => {
        const e = k * k * (3 - 2 * k);
        act.rotation.y = a0 + (a1 - a0) * e;
        // the leaf lifts a little off the block as it goes over
        act.position.z = act.userData.z0 ??= act.position.z;
        act.position.z = act.userData.z0 + Math.sin(e * Math.PI) * 0.012;
        if (!swapped && e > 0.35) { swapped = true; mid(); }
      }, () => { act.rotation.y = 0; act.position.z = act.userData.z0 ?? act.position.z; clearLeaf(); if (!swapped) mid(); });
    },
    set(p, q, s) {
      world = { p: p.clone(), q: q.clone(), s };
      group.position.copy(p).applyMatrix4(fInv);
      group.quaternion.copy(fQi).multiply(q);
      group.scale.setScalar(s / fS);
    },
    world: () => ({ p: world.p.clone(), q: world.q.clone(), s: world.s }),
    setOpen, setClosedOffset,
    poseOf(node) {
      node.updateWorldMatrix(true, false);
      const c = shelf.getCenter(new THREE.Vector3()).applyMatrix4(node.matrixWorld);
      const q = node.getWorldQuaternion(new THREE.Quaternion()).multiply(basis);
      return { p: c, q };
    },
    dispose() {
      clearLeaf();
      group.removeFromParent();
      coverGeo?.dispose();
      if (coverMesh && !cover) coverMesh.material.dispose();
    },
  };
}

/** The shelf book's cover: its mesh's material (the vendor's cover atlas) and its rect in items.json. */
function coverOf(n) {
  const it = inventory.items?.[n.name];
  let mat = null;
  n.traverse((o) => { if (!mat && o.isMesh && o.material?.map) mat = o.material; });
  const uv = Array.isArray(it?.cover_uv) && it.cover_uv.length === 4 ? it.cover_uv.map(Number) : null;
  return mat && uv ? { material: mat, uv } : null;
}
