# Latest judges on writer, end of round 1

## Opus (pass 3): Improve

Failed checks:
- Unconfirmed claims stay out of a production build (independent run of setNotesMode('hide') + buildContent): Two unconfirmed claims still reach production. First, the Riesenrad panel ships the intro 'These are the questions I keep coming back to...' with three topic headings; the prototype labelled these 'Example topics'. Second, meta.books still holds all five titles, and stalls.js:190-205 presents them in 3D as Mac's own, while other spines are 'not one of Mac's'. The prototype's 'Example pick' hedge was removed in pass 4. Both could be fixed from content/ today.
- The production view reads as finished (look at content_production.jpg): In the production image and in my buildContent output, the Riesenrad panel is the intro followed by three bare <h3> headings with nothing under them. It looks broken, not deliberate. Writing is down to one paragraph and Reading to one sentence. Both are acceptable but thin.
- Content strings are actually consumed by the engine: The engine never reads site.md toggle_labels or titles. The strings are built in main.js instead, as NOTES.md itself admits. That is about 15 lines of dead reference text that can drift from the real UI. The fix belongs to the engineer, but the text is still in content/ with nothing to show it isn't used.

Fixes:
- Keep the unconfirmed Riesenrad topics out of production using content alone. Put a [[Mac: confirm the topics]] note in the same block as the intro paragraph, and join each '### question' heading to its body line with no blank line, so stripNotes drops heading and line together. Also give the Riesenrad one short production line that needs no confirmation, for example 'Nothing is written up here yet.', so the panel is not three bare headings (or empty).
- Keep the unconfirmed books off the 3D shelf using content alone. Either put a [[Mac: confirm]] note in each books[].title, so stripMetaNotes empties the titles and bookPicks falls back to its neutral 'Mac will add his reading list here.' entry, or bring back an honest hedge in the 'Pull a book' note (e.g. 'Example pick.'). Don't rely on launch condition 3 by hand.
- Once both are done, re-run setNotesMode('hide') + buildContent and re-render content_production.jpg. Then confirm that no check-marked claim, including the topic headings and book titles, appears in production output, and update the 'one ungated claim' wording in NOTES.md.
- Move site.md toggle_labels and titles under a clearly named key (e.g. reference_only) or drop them until main.js reads them. Otherwise they are content that silently disagrees with the live UI.
- Small things: make the tagline one voice ('I'm a physician in Bangkok and I write software for clinical research.'). Align the reading hint 'or let the bookseller choose' with the 'Pull a book' label.

## Fable (pass 3): Improve

Failed checks:
- Nothing about Mac is invented without a check marker or placeholder: The plain page is clean (dist/plain.html has 0 hits for every gated claim), but `reading.md` front matter `books` reaches production unguarded: `content.js:88` `bookPicks()` reads `meta('books').books` first, and `stalls.js:193` then tells visitors 'His picks wear a red paper band' / 'His five stand together', so five unconfirmed titles ship as Mac's in the 3D market with only a YAML comment (not a marker or placeholder) on them.

Fixes:
- Gate the five books inside content/ instead of leaving it to a launch condition: remove the `books:` array from reading.md front matter (or replace it with a single `[[Mac: confirm the five books]]` string, which `stripMetaNotes` empties). `bookPicks()` in site/src/content.js:88-106 then falls back to the body list, which it already parses as `title · author. note` in dev and which production already strips, so the 3D shelf stops presenting unconfirmed titles as 'His picks'. Verify with `setNotesMode('hide'); buildContent()` that `sections.books.meta.books` is gone and `items` is empty.
- Give the Riesenrad intro a real guard. 'the questions I keep coming back to' is prototype text, but 'I don't have answers to them' and 'When I write something on one, it will go on this page' are new; either cut them to the prototype wording and drop the marker, or move that sentence into the block that holds the final `[[Mac: confirm or replace these three topics]]` note so production drops it.
- Make the Bierstand pour match its menu: projects.md lists ProtoCol as 'House Pils · always on tap' but the 'Pull a pint (done)' note says 'A Helles'. Change one of them (e.g. 'A Pils, with a proper head of foam').
- Once the engineer's check-marker count lands in buildStart() (site/plugins/market.js:340), re-run `STRICT_CONTENT=1 npm run build` and replace the hand-computed check line in NOTES.md with the real one.
- Decide the fate of site.md `toggle_labels` and `titles`: either the engineer reads them in main.js:47/153/250 or mark them in site.md as reference text so nobody edits them expecting a change.

