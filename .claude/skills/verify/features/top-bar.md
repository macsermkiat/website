# Top bar and music

The bar above the market: play the jazz ballad, mute all sound, snow on or off, back to the overview, switch between the full and lite market, and the How to visit dialog with tips and credits. At the bandstand the visitor can put the spotlight on one player; the Riesenrad and Karussell offer rides.

## Sub-features

- `bar-play` `▶ Play the ballad` starts the band (enabled once the market opens); `#play[aria-pressed]` follows.
- `bar-mute` `Sound: on/off` silences band and stall sounds.
- `bar-snow` `Snow: on/off` toggles falling snow.
- `bar-quality` `Lite market: on/off` reloads at the other quality.
- `bar-about` `How to visit` opens `dialog#about`; Escape closes it.
- `band-spot` at the bandstand: Sax, Piano, Bass, Drums, Whole band (spotlight; lite plays one mix).
- `rides` Ride to the top (Riesenrad), Ride a horse / Ring the bell (Karussell), Get off.

## How to get to it (user POV)

- Click the buttons in the top bar.
- At `Musik`, `Riesenrad`, `Karussell`: the stop-bar buttons.

## Driving it with drive.mjs

Preconditions: market ready.

- **Play.** `page.click('#play')`, `h.pass(1)`: `#play` has `aria-pressed="true"`, `#nowplaying` is visible.
- **Mute.** `page.click('#mute')`: `aria-pressed="true"`, label reads `Sound: off`.
- **Snow.** `page.click('#snow')`: `aria-pressed="true"`, label `Snow: on`; screenshot shows flakes after `h.pass(2)`.
- **Quality.** `page.click('#quality')` reloads: `page.waitForURL(/quality=full/)`, then `h.waitReady()` (minutes on software GL); `<html data-quality="full">`.
- **About.** `page.click('#aboutOpen')`: `dialog#about[open]`; `#credits` has the audio credit; Escape closes it.
- **Spotlight.** At `band`: `h.tap('#stopActs [data-action="sax"]')`, `h.pass(2)`, screenshot.
- **Ride.** At `ferris`: `h.tap('#stopActs [data-action="ride"]')`, `h.pass(20)`, screenshot from the top; `h.tap('#stopActs [data-action="off"]')` or Escape gets off.
- **Proof.** `aria-pressed` and label before and after, plus a screenshot.

## Gotchas

- `#play` and `#mute` are disabled until the market opens.
- Headless audio is silent; state is the only proof. Stems may stream; an aborted first range request on a media file is normal and drive.mjs ignores it.
- The quality switch remembers the choice in the browser; drive.mjs gets a fresh context per run, and `?quality=` in the URL wins anyway.
- The GA cookie note in How to visit shows only when analytics runs, so it is hidden in verify builds by design.
