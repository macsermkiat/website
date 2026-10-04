# Writer, round 2

Edits only in `content/` and this folder. No third-party assets. No previews re-rendered (text-only changes, to save usage).

## Changes
- `about.md`: `<!-- check -->` on the employment sentence and on INTJ. New `wines` map in front matter: a short shelf-talker for each of the 18 `act_bottle_*` nodes in `site/public/models/items.json` (12 wines, 4 Glühwein, rum, Kinderpunsch). Written for the stall, not as Mac's own tasting, so no claim about Mac. Books get none. The engine does not read `wines` yet: the engineer can show it where a bottle label is read (`stalls.js:163`).
- `music.md`: states G minor and three-four, matching `manifest.json` (key "G minor", 3/4, title "Lanterns After Closing", brushes). Re-check if the music writer changes them.
- `questions.md`: judges' fix. Intro, headings and bodies now share blocks with `[[Mac: ...]]` notes, so a production build (checked with `stripNotes`) shows only "Nothing is written up here yet."
- `reading.md`: front-matter `books` is now `[]`, so the 3D shelf takes its picks from Mac's bookshelf (`content/bookshelf.json`, 55 titles) instead of the five unconfirmed examples. The five prototype titles stay in the body in a gated list with a note for Mac: three of them (Gödel Escher Bach, Feynman Lectures, Being You) are not on his Audible shelf. Production shows only the shelf line.
- `projects.md`: menu matches the taps (ProtoCol Helles, Target Trial Emulation Dunkles, audit "Cellar reserve"); the pour note no longer names a beer, since the middle tap is the Dunkles. Hint says "the dark one".
- `site.md`: tagline is one voice ("I'm a physician in Bangkok and I write software for clinical research."). `toggle_labels` and `titles` renamed `reference_only_*` because `main.js` does not read them.

## Open for Mac
- 21 check markers remain (`grep -o '<!-- check -->' content/*.md | wc -l`), plus the `[[Mac: ...]]` placeholders. Launch needs both at zero.
- Confirm the five example books or drop them; fill email, links, department, current book, records.
- Check markers are stripped silently by a production build, so only the `[[ ]]` notes gate. The engineer's `STRICT_CONTENT` count of check markers (round 1 request) is still wanted.

## Checks
All 9 files parse as YAML front matter with `actions`. No em or en dashes. Prose kept short and plain; no clinical imagery beyond the description of Mac's real work.

## Judges' fixes (pass 2b)
- `contact.md`: the issues link to github.com/macsermkiat/website now carries `<!-- check -->` (repo existence and visibility not confirmed from here). 22 check markers remain.
- Engineer items (wire `wines` map; STRICT_CONTENT counting check markers and `[[Mac: ...]]`) are outside content/ and not done by the writer.
- Mac items (confirm or drop GEB, Feynman Lectures, Being You; fill email, links, department, current book, records) still open.
- No previews: writer output is text only.
