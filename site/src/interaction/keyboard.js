// Keyboard access to the stroll (docs/adr/0003):
//   1–7          walk to a place (the signpost's order)          0 or Home   the overview of the square
//   ← / →        the previous / next stop; while reading, the previous / next page (PageUp / PageDown too)
//   Enter        read what is written at this stop
//   Shift + ← →  turn the head a little at a stop     ↑ ↓ or + −  step in and back a little
//   Escape       stop reading, get off a ride, or back to the overview
export function bindKeyboard({ canvas, order, walkTo, home, step, read, reading, readPage, closeRead, endRide, isRiding, rig }) {
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'application');
  canvas.setAttribute('aria-roledescription', 'Christmas market');
  canvas.setAttribute('aria-label', "Mac's Nachtmarkt: a 3D Christmas market at night, seen on a guided stroll. Keys 1 to 7 walk to a place, the arrow keys walk to the previous or next stop, Enter reads what is written there, Escape steps back, 0 returns to the overview. The signpost in the top left corner lists the places too.");
  addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    const onControl = t && t !== canvas && /^(BUTTON|A|SUMMARY)$/.test(t.tagName);
    if (e.key === 'Escape') {
      if (reading()) closeRead();
      else if (isRiding()) endRide();
      else home();
      e.preventDefault();
      return;
    }
    if (/^[0-9]$/.test(e.key)) {
      const n = +e.key;
      if (n === 0) { home(); e.preventDefault(); return; }
      if (n <= order.length) { e.preventDefault(); walkTo(order[n - 1]); }
      return;
    }
    // the arrows walk (or turn pages) from anywhere on the page but a text field; on a button, Enter and Space are the button's
    switch (e.key) {
      case 'ArrowLeft': case 'ArrowRight': {
        const d = e.key === 'ArrowLeft' ? -1 : 1;
        if (e.shiftKey && !reading()) rig.nudge(-d * 0.09, 0);
        else if (reading()) readPage(d);
        else step(d);
        break;
      }
      case 'PageUp': case 'PageDown':
        if (!reading()) return;
        readPage(e.key === 'PageUp' ? -1 : 1);
        break;
      case 'ArrowUp': case '+': case '=':
        if (reading()) return;
        rig.nudge(0, -0.06);
        break;
      case 'ArrowDown': case '-': case '_':
        if (reading()) return;
        rig.nudge(0, 0.06);
        break;
      case 'Home': home(); break;
      case 'Enter':
        if (onControl || reading()) return;
        if (!read()) return;
        break;
      default: return;
    }
    e.preventDefault();
  });
}

/** prefers-reduced-motion, kept live. */
export function watchMotion() {
  const mq = matchMedia('(prefers-reduced-motion: reduce)');
  const motion = { reduced: mq.matches, listeners: [] };
  mq.addEventListener?.('change', (e) => { motion.reduced = e.matches; motion.listeners.forEach((f) => f(e.matches)); });
  return motion;
}
