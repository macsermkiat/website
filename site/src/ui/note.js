// What just happened, said in the market: a small paper note pinned above the stall's counter (the vendor's
// word on the mug just poured, the pint just pulled), fading after a few seconds. Screen readers hear it from
// the live region. This replaces the old panel's note line.
import * as THREE from 'three';

export function createNote({ overlay, announce, anchorFor }) {
  const el = document.createElement('div');
  el.className = 'note';
  el.setAttribute('aria-hidden', 'true');
  el.style.opacity = '0';
  overlay.appendChild(el);
  let anchor = null, left = 0, html = '';
  const p = new THREE.Vector3();
  return {
    /** Say something at a place (or at the current one). */
    say(text, placeId) {
      html = String(text || '');
      el.innerHTML = html;
      const tmp = document.createElement('div');
      tmp.innerHTML = html;
      announce.textContent = tmp.textContent;
      anchor = anchorFor(placeId);
      left = Math.min(9, 4 + tmp.textContent.length / 30);
    },
    get text() { return el.textContent; },
    get html() { return html; },
    hide() { left = 0; },
    update(dt, camera) {
      if (left <= 0 || !anchor) { if (el.style.opacity !== '0') el.style.opacity = '0'; return; }
      left -= dt;
      p.copy(anchor).project(camera);
      const vis = p.z < 1 && Math.abs(p.x) < 1.1 && p.y < 1.1 && p.y > -1;
      const x = THREE.MathUtils.clamp(((p.x + 1) / 2) * overlay.clientWidth, 150, overlay.clientWidth - 150);
      const y = THREE.MathUtils.clamp(((1 - p.y) / 2) * overlay.clientHeight, 70, overlay.clientHeight - 140);
      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
      el.style.opacity = vis ? String(Math.min(1, left * 2)) : '0';
    },
  };
}
