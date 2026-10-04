// The small signpost on the screen: a copy of the market's finger signpost, one arm per place (with its key,
// 1 to 7), and the market overview. It is how the keyboard, a screen reader or a phone walks the stroll.
import { SECTIONS } from '../content.js';
import { ARM_NAMES } from '../nav/signpost.js';

const $ = (id) => document.getElementById(id);

export function createSignboard({ order, onChoose, onHome, onFocus }) {
  const nav = $('signboard');
  nav.replaceChildren();
  const post = document.createElement('div');
  post.className = 'sb-post';
  post.setAttribute('aria-hidden', 'true');
  nav.appendChild(post);
  const list = document.createElement('ul');
  list.className = 'sb-arms';
  const buttons = {};
  order.forEach((id, i) => {
    const S = SECTIONS[id] || {};
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button';
    b.className = `sb-arm ${i % 2 ? 'right' : 'left'}`;
    b.dataset.place = id;
    b.setAttribute('aria-current', 'false');
    b.innerHTML = `<kbd aria-hidden="true"></kbd><b lang="de"></b><span></span>`;
    b.querySelector('kbd').textContent = String(i + 1);
    b.querySelector('b').textContent = ARM_NAMES[id] || S.name || id;
    b.querySelector('span').textContent = S.sub || '';
    b.setAttribute('aria-label', `Walk to the ${S.name || id}: ${S.sub || ''}. Key ${i + 1}`);
    b.addEventListener('click', () => onChoose(id));
    b.addEventListener('focus', () => onFocus?.(id));
    b.addEventListener('blur', () => onFocus?.(null));
    b.addEventListener('pointerenter', () => onFocus?.(id));
    b.addEventListener('pointerleave', () => onFocus?.(null));
    li.appendChild(b);
    list.appendChild(li);
    buttons[id] = b;
  });
  const home = document.createElement('li');
  const hb = document.createElement('button');
  hb.type = 'button';
  hb.className = 'sb-home';
  hb.innerHTML = '<kbd aria-hidden="true">0</kbd><b>Overview</b>';
  hb.setAttribute('aria-label', 'Back to the view over the whole square. Key 0 or Home');
  hb.addEventListener('click', () => onHome());
  home.appendChild(hb);
  list.appendChild(home);
  nav.appendChild(list);
  // phones: the signpost folds into one button until it is needed
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'sb-toggle';
  toggle.setAttribute('aria-expanded', 'false');
  toggle.textContent = 'Wegweiser · places';
  toggle.addEventListener('click', () => { const open = nav.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); });
  nav.prepend(toggle);
  return {
    setCurrent(id) {
      for (const [k, b] of Object.entries(buttons)) b.setAttribute('aria-current', String(k === id));
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    },
    focus(id) { buttons[id]?.focus(); },
  };
}
