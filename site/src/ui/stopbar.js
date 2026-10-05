// The bar along the foot of the market at a stop: the way back and on (the neighbouring stops), the things to do
// here (pour a mug, pull a pint, Prost, turn the sausages, a sausage in a bun, pick a book, feature a player, the
// rides), what there is to read here, and the goods one by one for the keyboard. No section text lives here:
// that is in the market, on its boards, coasters, papers and pages.
import { SECTIONS, panelActions } from '../content.js';
import { ARM_NAMES } from '../nav/signpost.js';

const $ = (id) => document.getElementById(id);

export function createStopbar({ actionsFor, itemsFor, readsFor, onRead, onStep, playButtonLabel }) {
  const bar = $('stopbar'), acts = $('stopActs'), goods = $('goods'), here = $('hereName'), hereSub = $('hereSub');
  const prev = $('prevStop'), next = $('nextStop'), fold = $('stopFold');
  let current = null;
  let steps = { prev: null, next: null };
  // On a small screen a busy stop (the ornament shop's seven things to do) would cover the lower third of the
  // stall, so its buttons fold into one "Things to do" button. A visitor who opens it keeps it open.
  const small = window.matchMedia?.('(max-width: 640px), (max-height: 720px)');
  let userOpen = false;

  function setFolded(on) {
    bar.classList.toggle('folded', on);
    fold.setAttribute('aria-expanded', String(!on));
  }
  function autoFold() {
    if (!current) return;
    setFolded(false);
    fold.hidden = true;
    const count = acts.children.length + (goods.hidden ? 0 : 1);
    const tall = bar.offsetHeight > 0.2 * window.innerHeight;
    const can = !!small?.matches && count > 3 && tall;
    fold.hidden = !can;
    fold.textContent = `Things to do (${acts.children.length})`;
    if (can && !userOpen) setFolded(true);
  }
  fold.addEventListener('click', () => {
    const open = bar.classList.contains('folded');
    userOpen = open;
    setFolded(!open);
    if (open) acts.querySelector('button')?.focus({ preventScroll: true });
  });
  small?.addEventListener?.('change', autoFold);
  window.addEventListener('resize', () => { if (current && !bar.hidden) autoFold(); });

  prev.addEventListener('click', () => steps.prev && onStep(steps.prev));
  next.addEventListener('click', () => steps.next && onStep(steps.next));

  function show(id, { prevId, nextId } = {}) {
    current = id;
    steps = { prev: prevId || null, next: nextId || null };
    const S = SECTIONS[id] || {};
    bar.hidden = !id;
    bar.dataset.place = id || '';
    if (!id) return;
    here.textContent = S.name || id;
    hereSub.textContent = S.sub || '';
    const nm = (x) => ARM_NAMES[x] || SECTIONS[x]?.name || x;
    prev.hidden = !prevId; next.hidden = !nextId;
    if (prevId) { prev.querySelector('span').textContent = nm(prevId); prev.setAttribute('aria-label', `Walk back to the ${SECTIONS[prevId]?.name || prevId} (left arrow)`); }
    if (nextId) { next.querySelector('span').textContent = nm(nextId); next.setAttribute('aria-label', `Walk on to the ${SECTIONS[nextId]?.name || nextId} (right arrow)`); }
    acts.replaceChildren();
    acts.setAttribute('aria-label', `Things to do at the ${S.name || id}`);
    // what to read here first: the board, the coasters, the paper, the sheet, the ticket
    for (const r of readsFor(id)) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn small read';
      b.dataset.read = r.id;
      b.textContent = r.label;
      b.addEventListener('click', () => onRead(r.id));
      acts.appendChild(b);
    }
    const A = actionsFor(id);
    if (A) {
      for (const a of panelActions(id, A.acts)) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = a.play ? 'btn small primary' : 'btn small';
        b.dataset.action = a.key;
        if (a.play) { b.dataset.play = ''; b.textContent = playButtonLabel(); } else b.textContent = a.label;
        if (a.spot && A.spotOnly?.()) { b.textContent = `Spotlight: ${a.label}`; b.title = 'The lite market plays the band as one mix, so this moves the spotlight only.'; }
        b.addEventListener('click', a.fn);
        acts.appendChild(b);
      }
      for (const v of A.views?.list?.() || []) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn small view';
        b.lang = 'de';
        b.dataset.view = v.key;
        b.textContent = v.label;
        b.title = v.title && v.title !== v.label ? `Open the cabinet: ${v.title}` : 'Open this cabinet';
        b.setAttribute('aria-label', `Open the cabinet: ${v.label}${v.title && v.title !== v.label ? ` (${v.title})` : ''}`);
        b.addEventListener('click', v.fn);
        acts.appendChild(b);
      }
    }
    // the goods, one by one (the same as clicking them in the market), folded away
    const list = itemsFor?.(id) || [];
    goods.hidden = !list.length;
    const box = goods.querySelector('.goodslist');
    box.replaceChildren();
    goods.querySelector('summary').textContent = `Goods (${list.length})`;
    for (const it of list) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn small';
      b.textContent = it.label;
      b.dataset.item = it.name;
      b.addEventListener('click', it.fn);
      box.appendChild(b);
    }
    goods.open = false;
    autoFold();
  }

  return {
    show,
    hide() { show(null); },
    get folded() { return bar.classList.contains('folded'); },
    unfold() { userOpen = true; setFolded(false); },
    get current() { return current; },
    syncPlay(label) { bar.querySelectorAll('[data-play]').forEach((b) => (b.textContent = label)); },
    refresh() { if (current) show(current, { prevId: steps.prev, nextId: steps.next }); },
  };
}
