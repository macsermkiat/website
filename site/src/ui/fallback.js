// When the 3D market cannot run (no WebGL, or it failed to start), every section is shown as text in place of
// the market: the same content as plain.html, so nobody is left with an empty box.
import { SECTIONS, ORDER } from '../content.js';

const $ = (id) => document.getElementById(id);

export function showPlainFallback(reason) {
  const stage = $('stage');
  if (!stage || stage.dataset.fallback) return;
  stage.dataset.fallback = 'plain';
  document.documentElement.dataset.fallback = 'plain';
  const box = document.createElement('div');
  box.className = 'plainfallback';
  box.setAttribute('role', 'region');
  box.setAttribute('aria-label', 'The market as text');
  const lead = document.createElement('p');
  lead.className = 'lead';
  lead.textContent = `${reason} `;
  const link = document.createElement('a');
  link.href = 'plain.html';
  link.textContent = 'Open the text version on its own page.';
  lead.appendChild(link);
  box.appendChild(lead);
  for (const id of ORDER) {
    const s = SECTIONS[id];
    if (!s) continue;
    const sec = document.createElement('section');
    sec.id = `fallback-${id}`;
    const eyebrow = document.createElement('p');
    eyebrow.className = 'eyebrow';
    eyebrow.textContent = `${s.name} · ${s.sub}`;
    const h = document.createElement('h2');
    h.textContent = s.title || s.sub;
    const body = document.createElement('div');
    body.className = 'prose';
    body.innerHTML = s.html; // built at build time from content/*.md (the writer's files)
    sec.append(eyebrow, h, body);
    box.appendChild(sec);
  }
  $('loading')?.remove();
  stage.querySelector('canvas')?.remove();
  stage.appendChild(box);
  // the 3D controls have nothing to act on
  for (const id of ['snow', 'reset', 'quality']) { const b = $(id); if (b) b.hidden = true; }
  $('places')?.setAttribute('hidden', '');
  $('hint')?.setAttribute('hidden', '');
}
