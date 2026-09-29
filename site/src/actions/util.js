// Small helpers the actions share: a tween list, local/world conversion, and the node lookups.
import * as THREE from 'three';
import { actList } from '../engine/conventions.js';

export function createAnimator(motion) {
  const anims = [];
  const easeInOut = (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);
  return {
    /** Run fn(eased 0..1) over dur seconds after delay; reduced motion jumps to the end. */
    add(dur, fn, done, delay = 0) {
      if (motion.reduced) { fn(1); done && done(); return; }
      anims.push({ t: -delay, dur, fn, done });
    },
    update(dt) {
      for (let i = anims.length - 1; i >= 0; i--) {
        const a = anims[i];
        a.t += dt;
        if (a.t < 0) continue;
        const k = Math.min(1, a.t / a.dur);
        a.fn(easeInOut(k));
        if (k >= 1) { anims.splice(i, 1); a.done && a.done(); }
      }
    },
  };
}

/** World position of a node, or of a point given in the place's local frame. */
export function worldOf(place, nodeOrLocal) {
  if (nodeOrLocal?.isObject3D) return nodeOrLocal.getWorldPosition(new THREE.Vector3());
  return place.holder.localToWorld(new THREE.Vector3().fromArray(nodeOrLocal));
}

/** Convert a world position into the place's local frame. */
export function toLocal(place, world) {
  return place.holder.worldToLocal(world.clone());
}

export function acts(place, prefix) {
  return place ? actList(place.nodes, prefix) : [];
}

export function act(place, name) {
  return place?.nodes.acts[name] || null;
}

/** First node under the place whose name matches (for extra nodes like grill_coals or smoke_origin). */
export function findNode(place, re, { mesh = false } = {}) {
  let hit = null;
  place?.root.traverse((o) => { if (!hit && re.test(o.name) && (!mesh || o.isMesh)) hit = o; });
  return hit;
}

/** The counter top centre in place-local coordinates (slot_counter, or the standard 1.05 m counter). */
export function counterLocal(place) {
  const s = place.nodes.slots.slot_counter;
  if (s) return toLocal(place, s.getWorldPosition(new THREE.Vector3()));
  return new THREE.Vector3(0, 1.075, 1.5);
}

/** The node's longest local axis, for turning sausages whatever way they were modelled. */
export function longAxis(node) {
  const box = new THREE.Box3();
  node.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    box.union(o.geometry.boundingBox);
  });
  if (box.isEmpty()) return new THREE.Vector3(1, 0, 0);
  const s = box.getSize(new THREE.Vector3());
  return s.x >= s.y && s.x >= s.z ? new THREE.Vector3(1, 0, 0) : s.y >= s.z ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
}

/**
 * A small paper tag in the overlay, pinned above a point in the scene (the title of a pulled book).
 * show(text, node) pins it above the node's bounding box; hide() takes it away; update(camera) follows the node.
 */
export function createWorldTag(overlay, className = 'tag') {
  if (!overlay) return { show() {}, hide() {}, update() {} };
  const d = document.createElement('div');
  d.className = className;
  d.setAttribute('aria-hidden', 'true'); // the panel note says the same in words
  d.style.opacity = '0';
  overlay.appendChild(d);
  let node = null;
  const box = new THREE.Box3(), p = new THREE.Vector3();
  return {
    show(text, n) { node = n; d.textContent = text; },
    hide() { node = null; d.style.opacity = '0'; },
    update(camera) {
      if (!node) return;
      box.setFromObject(node);
      if (box.isEmpty()) return;
      box.getCenter(p);
      p.y = box.max.y + 0.03;
      p.project(camera);
      const vis = p.z < 1 && Math.abs(p.x) < 1 && Math.abs(p.y) < 1;
      d.style.opacity = vis ? '1' : '0';
      d.style.left = ((p.x + 1) / 2) * overlay.clientWidth + 'px';
      d.style.top = ((1 - p.y) / 2) * overlay.clientHeight + 'px';
    },
  };
}
