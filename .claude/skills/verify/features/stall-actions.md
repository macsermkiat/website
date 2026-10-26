# Stall actions

At each section stall a visitor can do something that changes the scene: pour a Glühwein, raise a glass with the crowd, pull a pint, turn the sausages, have one in a bun, or build a plate of sausages and sauces. The vendor answers with a paper note over the counter (also read out through the live region).

## Sub-features

- `glueh-pour` Pour a cup / mug: a stall mug fills, the note counts mugs poured tonight.
- `glueh-mug-3d` clicking a mug (`act_mug_<n>`) in 3D pours into that mug.
- `prost` Prost! at the Glühwein stand or Bierstand: speech bubbles (`.bubble`) from the crowd.
- `bier-pint` Pull a pint: the middle tap pours, the note counts pints pulled tonight.
- `wurst-turn` Turn the sausages: every sausage on the grill turns over.
- `wurst-bun` One in a bun, please: a roll and a Thüringer with Senf go on the plate.
- `wurst-plate` clicking a sausage kind, roll, sauce bottle or curry tin adds it to the paper plate (max four foods); clicking the plate clears it ("Guten Appetit"); Mix me a plate adds one kind and one sauce.

## How to get to it (user POV)

- Walk to the stall (see stroll.md), then click a button in the stop bar: `Pour a mug`, `Prost!`, `Pull a pint`, `Turn the sausages`, `One in a bun, please`, `Mix me a plate`.
- Click the glowing things on the counter in 3D (mugs; at the Bratwurst the four kinds, roll, three sauces, curry tin, plate).
- Open `Goods (n)` in the stop bar and click an item there (same as clicking it in 3D).

## Driving it with drive.mjs

Preconditions: market ready, at the stall (`page.click('#signboard .sb-arm[data-place="glueh"]')`, `h.waitArrived('glueh')`).

- **Pour.** `await h.tap('#stopActs [data-action="pour"]')`, `await h.waitAnnounce(/poured tonight: 1\b/i)`. Shipped as journey `glueh-pour`.
- **Mug in 3D.** Find a mug among `__market.glow().targets` (`act_mug_0` …), `await h.click3D(name)`, `h.waitAnnounce(/poured tonight: 2\b/i)`; the note names the mug.
- **Prost.** `await h.tap('#stopActs [data-action="prost"]')`, `h.pass(3)`, `page.locator('.bubble').count() > 0`.
- **Pint.** At `bier`: `h.tap('#stopActs [data-action="pint"]')`, `h.waitAnnounce(/pulled tonight: 1\b/i, 30)`.
- **Plate.** At `wurst`: `h.click3D('act_wurst_krakauer')`, `h.pass(3)`, then `h.state(() => window.__market.handlers.plate())` has `food: ['krakauer']`. Click `act_sauce_ketchup`, the plate's `sauces` gains `ketchup`. `h.click3D('act_plate')` empties it and `#announce` matches `/Guten Appetit/`.
- **Turn.** `h.tap('#stopActs [data-action="turn"]')`, `h.pass(2)`, `__market.handlers.grill().turns` all 1.
- **Proof.** Screenshot at the stall before, and after each action (the note shows on screen); check the counter in `#announce` and the plate/grill state.

## Gotchas

- Labels come from `content/` (`Pour a cup` in code reads `Pour a mug` on screen): select by `data-action`.
- `h.click3D` needs a clear pixel of the item not covered by the note, stop bar or a person; if it returns false, report it, do not swap in `__market.clickItem`.
- Reduced motion pours the pint at once; without it the note first says `Pouring…`.
- The plate holds four foods; a fifth gives "the plate is full".
- Counts are per page load: each journey starts at 0.
