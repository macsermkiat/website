# Ornament shop

The Christbaumschmuck stall is the one interactive deco stall: a mirror wall, candle pyramid, mercury-glass baubles, tinsel, angels and snow globes. Three moments only: light the Schwibbogen (candles light outside-in, the town's windows answer, a wave of light), play the glass harmonica (the baubles play the ballad), and look into the mirror ball (the camera dives into a bauble's reflection). Nothing else there is clickable.

## Sub-features

- `schmuck-candles` the candle arch lights, the town's windows wake, the view rises over the arch and returns.
- `schmuck-harmonica` brushing or tapping the baubles plays notes; the button plays the tune.
- `schmuck-dive` the camera goes into the mirror ball; Escape or a tap brings it back.
- `schmuck-only-three` no other item at the stall answers a click.

## How to get to it (user POV)

- Walk to `Christbaumschmuck` (key 8), then the stop-bar buttons `Light the candles` (label changes), `Play the glass harmonica`, `Look into the mirror ball`.
- Click the arch, the baubles, or the mirror ball in 3D.

## Driving it with drive.mjs

Preconditions: market ready, at `schmuck`. Use 1280x760 so the bar does not fold.

- **Candles.** `h.tap('#stopActs [data-action="candles"]')`, then `h.pass(2)` steps with a screenshot each, to catch the wave. Check `#announce` or the button label changing.
- **Harmonica.** `h.tap('#stopActs [data-action="harmonica"]')`, `h.pass(4)`; screenshot mid-phrase.
- **Dive.** `h.tap('#stopActs [data-action="dive"]')`, `h.pass(4)`, screenshot inside; `#momentCap` visible; `page.keyboard.press('Escape')`, `h.pass(3)`, back at the stall view.
- **Only three.** Sample canvas points with `__market.pickAt(x, y)` at the stop: only the arch, baubles and mirror ball answer.
- **Proof.** Screenshots before, at the peak, and after each moment.

## Gotchas

- The Schwibbogen wave is hard to see in single stills; take two or three shots a second of market time apart.
- `?mirror=0` turns off the mirror wall (a measuring switch); do not leave it in a verification URL.
- With `--reduced-motion` the moments run their reduced versions (no dive flight); test both when the change touches motion.
- The harmonica's sound cannot be heard here; prove it by state and the hint text.
