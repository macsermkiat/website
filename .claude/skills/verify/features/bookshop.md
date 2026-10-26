# Bookshop

The Bücherstand holds 55 books from Mac's library in six glazed cabinets, covers out, by category. A visitor opens a cabinet, picks a cover, and the book stands open on the counter with Claude's summary on its pages. The bookseller can also pick one.

## Sub-features

- `books-cabinet` a cabinet opens (camera turns to it, door opens, covers come forward); only its books are clickable then.
- `books-pick` clicking a cover opens that book; its pages read like other surfaces (reading.md).
- `books-for-me` Pick a book for me opens a random book.
- `books-turn` ‹ › beside the cabinet (`#cabTurnL`, `#cabTurnR`) move to the neighbouring cabinet.
- `books-keys` ↓ / ↑ open the cabinets one after another, ← → move between books, Enter opens the one in focus.
- `books-back` Step back (`#stepBack`) or Escape closes the cabinet.

## How to get to it (user POV)

- Walk to `Bücher`, then click a cabinet in 3D, or a cabinet button in the stop bar (`Physik & Kosmos`, `Lebensgeschichten`, `Geist & Körper`, `Menschen & Gespräche`, `Risiko & Entscheidungen`, `Handwerk & Gewohnheit`).
- Click `Pick a book for me`.
- Use the arrow keys at the stop.

## Driving it with drive.mjs

Preconditions: market ready, at `books`. Cabinet keys: `physics lives mind people decisions craft`.

- **Open cabinet.** `await h.tap('#stopActs [data-view="physics"]')`, `h.pass(3)`. `document.documentElement.dataset.cabinet` is `physics`; `__market.handlers.cabinetState()` has `open` and its `books`.
- **Pick a cover.** Take a name from `cabinetState().books`, `await h.click3D(name)`, `h.pass(4)`. `reading().open` is true and `#readTitle` names the book.
- **For me.** `h.tap('#stopActs [data-action="book"]')`, `h.pass(4)`, `reading().open`.
- **Turn.** `page.click('#cabTurnR')`, `h.pass(3)`, `data-cabinet` changes.
- **Back.** `page.click('#stepBack')` or Escape, `h.pass(3)`: `data-cabinet` empty.
- **Proof.** Screenshots of the closed stall, the open cabinet, the open book.

## Gotchas

- An open cabinet folds the stop bar on every screen: use `h.tap`, which unfolds it.
- At rest a whole cabinet is one click target (an invisible proxy); individual covers only answer once it is open.
- On a 390 px phone (`--size 390x844 --touch`) covers should be at least 44 px; check that when the change touches the cabinets.
- Book text lives in `content/books/*.md`; pages marked `review: check` fail the production build, not the local one.
