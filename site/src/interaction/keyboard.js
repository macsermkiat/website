// Keyboard access: 1–7 open places, Escape closes the panel or ends a ride,
// arrows orbit and +/- zoom when the market has focus, Home resets the view.
export function bindKeyboard({ canvas, order, openPlace, closePanel, endRide, isRiding, resetView, rig }) {
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'application');
  canvas.setAttribute('aria-label', 'The 3D market. Arrow keys look around, plus and minus zoom, 1 to 7 open a place, Home resets the view.');
  addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if (e.key === 'Escape') {
      if (isRiding()) endRide();
      else closePanel();
      return;
    }
    if (/^[1-9]$/.test(e.key) && +e.key <= order.length) {
      e.preventDefault();
      openPlace(order[+e.key - 1]);
      return;
    }
    if (t !== canvas) return;
    const step = e.shiftKey ? 0.2 : 0.08;
    switch (e.key) {
      case 'ArrowLeft': rig.nudge(step, 0); break;
      case 'ArrowRight': rig.nudge(-step, 0); break;
      case 'ArrowUp': case '+': case '=': rig.nudge(0, -0.1); break;
      case 'ArrowDown': case '-': case '_': rig.nudge(0, 0.1); break;
      case 'Home': resetView(); break;
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
