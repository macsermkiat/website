// The mute button: one switch for everything the market plays, the band and the stall sounds alike.
// The choice is remembered on this device.
const KEY = 'nachtmarkt.muted';

export function setupMute(btn, audio) {
  let on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch { /* private mode: not remembered */ }
  const sync = () => {
    btn.textContent = on ? '🔇 Sound: off' : '🔈 Sound: on';
    btn.setAttribute('aria-pressed', String(on));
    btn.title = on ? 'Sound is off (the band and the stall sounds). Press to turn it on.' : 'Silence the band and the stall sounds';
  };
  const set = (v) => {
    on = !!v;
    audio.setMuted(on);
    try { localStorage.setItem(KEY, on ? '1' : '0'); } catch { /* not remembered */ }
    sync();
  };
  audio.setMuted(on);
  sync();
  btn.addEventListener('click', () => set(!on));
  return { set, get muted() { return on; } };
}
