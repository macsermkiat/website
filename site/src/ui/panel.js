// The panel that opens over the market, the row of place buttons, and the live "what just happened" note.
import { SECTIONS, ORDER, panelActions } from '../content.js';

const $ = (id) => document.getElementById(id);

export function createPanel({ actionsFor, itemsFor, onOpen, onClose, playButtonLabel }) {
  const panel = $('panel'), body = $('pBody'), actionsBox = $('pActions'), title = $('pTitle'), eyebrow = $('pEyebrow');
  const announce = $('announce');
  let current = null;
  let returnFocus = null;

  function say(html) {
    const note = $('actNote');
    if (note) note.innerHTML = html;
    // screen readers get the plain text
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    announce.textContent = tmp.textContent;
  }

  function open(id, { focus = true } = {}) {
    const S = SECTIONS[id];
    if (!S) return;
    if (focus && document.activeElement && !panel.contains(document.activeElement)) returnFocus = document.activeElement;
    current = id;
    eyebrow.textContent = `${S.name} · ${S.sub}`;
    title.textContent = S.title || S.sub;
    body.innerHTML = S.html;
    actionsBox.replaceChildren();
    const A = actionsFor(id);
    if (A) {
      const note = document.createElement('p');
      note.className = 'actnote';
      note.id = 'actNote';
      note.innerHTML = A.hint;
      const box = document.createElement('div');
      box.className = 'acts';
      box.setAttribute('role', 'group');
      box.setAttribute('aria-label', `Things to do at the ${S.name}`);
      for (const a of panelActions(id, A.acts)) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = a.play ? 'btn primary' : 'btn';
        b.dataset.action = a.key;
        if (a.play) { b.dataset.play = ''; b.textContent = playButtonLabel(); } else b.textContent = a.label;
        if (a.spot && A.spotOnly?.()) {
          b.textContent = `Spotlight: ${a.label}`;
          b.title = 'The lite market plays the band as one mix, so this moves the spotlight only.';
        }
        b.addEventListener('click', a.fn);
        box.appendChild(b);
      }
      actionsBox.append(box, note);
      // views of one part of the place (the Bücherstand's category shelves)
      const views = A.views?.list?.() || [];
      if (views.length) {
        const row = document.createElement('div');
        row.className = 'views';
        row.setAttribute('role', 'group');
        row.setAttribute('aria-label', A.views.label);
        const lab = document.createElement('span');
        lab.className = 'views-label';
        lab.textContent = `${A.views.label}:`;
        lab.setAttribute('aria-hidden', 'true');
        row.appendChild(lab);
        for (const v of views) {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'btn small';
          b.lang = 'de';
          b.dataset.view = v.key;
          b.textContent = v.label;
          if (v.title && v.title !== v.label) { b.title = v.title; b.setAttribute('aria-label', `${v.label} (${v.title})`); }
          b.addEventListener('click', v.fn);
          row.appendChild(b);
        }
        actionsBox.appendChild(row);
      }
      // the goods one by one, for the keyboard and screen readers (the same as clicking them in the market)
      const list = itemsFor?.(id) || [];
      if (list.length) {
        const d = document.createElement('details');
        d.className = 'goods';
        const sum = document.createElement('summary');
        sum.textContent = `The goods, one by one (${list.length})`;
        const ul = document.createElement('div');
        ul.className = 'goodslist';
        ul.setAttribute('role', 'group');
        ul.setAttribute('aria-label', `Goods at the ${S.name}`);
        for (const it of list) {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'btn small';
          b.textContent = it.label;
          b.dataset.item = it.name;
          b.addEventListener('click', it.fn);
          ul.appendChild(b);
        }
        d.append(sum, ul);
        actionsBox.appendChild(d);
      }
    }
    body.querySelectorAll('a[href^="http"]').forEach((a) => { a.target = '_blank'; a.rel = 'noopener'; });
    panel.hidden = false;
    document.querySelectorAll('#places button').forEach((b) => b.setAttribute('aria-current', String(b.dataset.place === id)));
    if (focus) title.focus({ preventScroll: true });
    onOpen?.(id);
  }

  function close() {
    if (panel.hidden) return;
    panel.hidden = true;
    const was = current;
    current = null;
    document.querySelectorAll('#places button').forEach((b) => b.setAttribute('aria-current', 'false'));
    onClose?.(was);
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus({ preventScroll: true });
    returnFocus = null;
  }

  $('pClose').addEventListener('click', close);

  return {
    open, close, say,
    get current() { return current; },
    get isOpen() { return !panel.hidden; },
    syncPlay(label) { panel.querySelectorAll('[data-play]').forEach((b) => (b.textContent = label)); },
  };
}

/** The row of place buttons under the market (the keyboard route into every section). */
export function buildPlaceNav(onChoose, onFocus) {
  const nav = $('places');
  nav.replaceChildren();
  ORDER.forEach((id, i) => {
    const S = SECTIONS[id];
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.place = id;
    b.setAttribute('aria-current', 'false');
    b.innerHTML = `<kbd aria-hidden="true">${i + 1}</kbd><b></b><span></span>`;
    b.querySelector('b').textContent = S.name;
    b.querySelector('span').textContent = S.sub;
    b.setAttribute('aria-label', `${S.name}: ${S.sub}. Shortcut ${i + 1}`);
    b.addEventListener('click', () => {
      // the buttons sit under the market: bring the whole stage back into view to watch the flight (instant, so a
      // pointer aimed at the scene right after lands where it was aimed)
      const st = document.getElementById('stage')?.getBoundingClientRect();
      if (st && (st.top < 0 || st.bottom > innerHeight)) document.getElementById('stage').scrollIntoView({ block: 'nearest', behavior: 'instant' });
      onChoose(id);
    });
    b.addEventListener('focus', () => onFocus?.(id));
    b.addEventListener('blur', () => onFocus?.(null));
    nav.appendChild(b);
  });
}
