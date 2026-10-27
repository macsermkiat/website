# Stroll and signpost

The market is a guided stroll, not a free camera. A visitor walks between eight stops on a fixed lane, from the signpost (in 3D and on screen), the stop bar's previous/next buttons, or the keyboard, and can always return to the overview. Dragging only turns the head a little.

## Sub-features

- `stroll-signpost` an on-screen arm walks to its stop; the 3D signpost boards do the same.
- `stroll-step` the stop bar's ‹ › buttons and ← → keys walk to the neighbouring stop in stroll order.
- `stroll-keys` keys 1–8 walk to a stop, 0 / Home / Escape return to the overview.
- `stroll-overview` the Overview button and the signpost's Overview arm return to the view over the square.
- `stroll-no-orbit` a drag turns the head at most about 15° and does not move the camera.

## How to get to it (user POV)

- Click an arm of the signpost in the top-left of the market (`Glühwein … Christbaumschmuck`, `Overview`).
- Click a signpost board in 3D at the overview (`act_sign_<id>`).
- At a stop, click `‹ <name>` / `<name> ›` in the stop bar, or press ← / →.
- Press 1–8 or 0 with focus on the page (not in a text field, no dialog open).
- Click `Overview` in the top bar.

## Driving it with drive.mjs

Preconditions: market ready (`h.waitReady()`), at the overview.

- **Signpost arm.** `await h.page.click('#signboard .sb-arm[data-place="bier"]'); await h.waitArrived('bier')`. `#hereName` reads `Bier vom Fass` (or the content's name), `#stopbar` is visible with `data-place="bier"`.
- **Step.** `await h.page.click('#nextStop'); await h.waitArrived('books')` (stroll order `glueh band bier books schmuck carousel ferris wurst`, wrapping). `ArrowRight` does the same.
- **Keys.** `await h.page.keyboard.press('3'); await h.waitArrived('wurst')`. Keys follow the signpost's top-to-bottom order: 1 glueh, 2 bier, 3 wurst, 4 books, 5 band, 6 ferris, 7 carousel, 8 schmuck.
- **Overview.** `await h.page.click('#reset')` or `keyboard.press('0')`, then `h.pass(6)`. `h.state(() => window.__market.stop)` is `null` and `#stopbar` is hidden.
- **3D board.** At the overview, `await h.click3D('act_sign_bier')` (board names come from `__market.glow().targets` at the overview), then `h.waitArrived('bier')`.
- **No orbit.** Drag across the canvas with `page.mouse.down/move/up`, `h.pass(2)`, compare `__market.cam()` before and after: `look.yaw` within ±0.262 rad, position moved < 1.2 m.
- **Proof.** `h.shot` at the overview and at the stop; checks on `#hereName`, `__market.stop`, `#stopbar[hidden]`.

## Gotchas

- The walk takes several seconds of market time: always `h.waitArrived`, never check right after the click.
- The keys do nothing while `dialog#about` is open or focus is in a text field; Enter on a focused button presses the button.
- Stroll order (‹ ›) and signpost order (1–8) differ.
- A small screen (≤ 640 px wide or ≤ 720 px tall) may fold the stop bar; `h.tap` unfolds it, a raw `page.click` on `#stopActs` buttons does not.
