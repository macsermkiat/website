# Nachtmarkt verification map

The maintained source for verifying what a visitor can do on Mac's Nachtmarkt. Read this index, then the feature file, then write or run a journey with `drive.mjs` (see `../SKILL.md`).

## Baseline preconditions

- An instance started by `launch.sh` on your own port, and `doctor.sh <port>` exits 0.
- The lite market at 1280x760 unless the feature says otherwise (`--quality lite` is the default).
- Snow off (`h.open()` adds `snow=0`). Every page load starts fresh: there is no saved state except the quality choice, which a `?quality=` URL overrides.
- Never drive a server you did not start (doctor's "served page is our build" check).

## Driving conventions

- Visitor actions go through `h.page` (clicks, keys), `h.tap` (stop-bar buttons) and `h.click3D` (3D items). `window.__market` is for observing, and for reaching a precondition you are not proving.
- Prefer ids and data attributes (`data-place`, `data-action`, `data-read`, `data-view`, `data-item`) over button text: the labels come from `content/` and change.
- After a click that walks, call `h.waitArrived(id)`; after an action, `h.waitAnnounce(re)`; for anything else that animates, `h.pass(seconds)`.

## Proof and skip reporting

- Screenshot before and after each action that changes the scene, and check the state that changed.
- Name the entry point used with each check (signpost arm, key, stop-bar button, 3D click).
- If an entry point cannot be reached (no clear pixel for `h.click3D`, a button missing), report it as a failure with the reason. Do not count it as verified through another path.

## Feature entry contract

Each file: an H1, one paragraph, then `Sub-features`, `How to get to it (user POV)`, `Driving it with drive.mjs`, `Gotchas`.

## Features

- [Stroll and signpost](./stroll.md): walking between the eight stops by signpost, stop bar, keys, and back to the overview.
- [Stall actions](./stall-actions.md): pour a Glühwein, Prost, pull a pint, the Bratwurst grill and plate. Journey: `glueh-pour`.
- [Reading the market](./reading.md): each section's words on its board, coasters, menu, paper, card, sheet, noticeboard, ticket and placards.
- [Bookshop](./bookshop.md): six category cabinets, picking a book, its pages.
- [Ornament shop](./ornament-shop.md): the Schwibbogen light wave, the glass harmonica, the dive into a bauble.
- [Top bar and music](./top-bar.md): play the ballad, sound, snow, overview, lite/full switch, How to visit; the band's spotlight; the rides.
- [Plain page](./plain-page.md): `plain.html`, the text-only version.
