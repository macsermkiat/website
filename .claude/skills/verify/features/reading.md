# Reading the market

Each section's text is written on things in the market, not in a side panel: the Glühwein chalkboard (About), the vom Fass board and Bierdeckel coasters (Projects), the menu board and wrapping paper (Writing), the reading card (Reading), the sheet music (Music), the noticeboard and gondola placards (Big questions), the ticket (Contact). Reading moves the camera close; long text turns pages; a coaster turns over.

## Sub-features

- `read-open` a Read button, Enter, or a click on the writing opens it close up with `#readbar`.
- `read-pages` Next page / Previous (or ← → / PageUp PageDown) turn pages of long text.
- `read-flip` a Bierdeckel turns over to its back (`Turn it over` / →).
- `read-copy` a visually hidden copy (`#readCopy`) carries the text and real links for screen readers.
- `read-close` Step back / Escape returns to the stop.
- `read-placard` a gondola placard at the Riesenrad parks the wheel and is read where it hangs.

## How to get to it (user POV)

- At a stop, click `Read the chalkboard` (etc.) or `Pick up: <coaster>` in the stop bar.
- At a stop, press Enter.
- Click the glowing writing in 3D (`write_*` surfaces).

## Driving it with drive.mjs

Preconditions: market ready, at the stop. Surface ids: `glueh.board`, `bier.vomfass`, `bier.coaster_0`…, `wurst.menu`, `wurst.paper`, `books.card`, `band.sheet`, `ferris.notice`, `ferris.placard_<n>`, `carousel.ticket`.

- **Open by button.** `await h.tap('#stopActs [data-read="glueh.board"]')`, `h.pass(4)`. `h.state(() => window.__market.reading())` has `open: true, id: 'glueh.board'`; `#readbar` is visible; `__market.textOn('glueh.board')` has the words.
- **Open by key.** At the stop, `page.keyboard.press('Enter')`, `h.pass(4)`, same checks.
- **Pages.** If `reading().views > 1`: `page.click('#readNext')`, `h.pass(2)`, `reading().view === 1` and the text changed; `#readPage` shows the page number.
- **Flip.** At `bier`: open `bier.coaster_0`, `page.click('#readFlip')` or `ArrowRight`, `h.pass(2)`, `reading().face === 'back'`.
- **Copy and links.** `page.textContent('#readCopy')` holds the text; at `bier.vomfass` its links match those in `content/projects.md`.
- **Close.** `page.keyboard.press('Escape')` or `page.click('#readClose')`, `h.pass(3)`: `reading().open === false`, still at the stop.
- **Proof.** Screenshot open (words visible in 3D, bar at the bottom) and after closing.

## Gotchas

- Text drawn in 3D (troika) appears a moment after the camera arrives: pass time before the screenshot or the board looks blank.
- A production build hides lines marked for Mac (`[[Mac: …]]`); the local build shows or hides them by `CONTENT_NOTES`. Do not report a hidden note as missing text.
- Escape while reading closes the reading; a second Escape goes to the overview.
- The placards need the wheel to park first; it takes several seconds of market time.
