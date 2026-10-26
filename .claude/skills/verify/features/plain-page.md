# Plain page

`plain.html` is the text-only version of the site: every section's words, the book summaries, the questions and the contact, with no 3D. It is for screen readers, slow devices and anyone who prefers text, and is linked from the market.

## Sub-features

- `plain-sections` About, Projects, Writing, Reading, Music, Big questions and Contact are all present.
- `plain-books` the book list with summaries.
- `plain-links` project and contact links work.
- `plain-credits` the credits line (`#credits`).

## How to get to it (user POV)

- Open `/website/plain.html` directly, follow the skip link at the top of the market page (`Skip the 3D market: read the text version`), the link under the loading screen, or `Read every section as plain text` in How to visit.

## Driving it with drive.mjs

Preconditions: an instance from `launch.sh`.

- **Open.** In a journey: `await h.open('', 'plain.html')` (no `waitReady`; the page has no market).
- **Sections.** `page.locator('main#main h2').allTextContents()` lists each section.
- **Links.** Collect `main a[href^="http"]`; compare with links in `content/*.md`.
- **Proof.** `h.shot('plain')` (full page) and the list of headings in a check.

## Gotchas

- The skip link (`a.skip`) is off screen until focused, so `page.click` times out on it. Reach it as a keyboard visitor does: the first `Tab`, then `Enter` (journey `plain`).
- `h.shot` tries to freeze the market first; on plain.html there is none and it just captures.
- The plain page is built from the same `content/` at build time: a content change needs a relaunch (doctor flags it).
