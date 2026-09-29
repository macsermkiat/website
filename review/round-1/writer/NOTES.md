# Writer, round 1 (pass 5)

## What was built

Nine Markdown files in `content/`: one per section, the site file, and the crowd's lines.

| File | Stall / place | Title | Actions |
|---|---|---|---|
| `site.md` | Nachtmarkt (header, plain page) | Mac's Nachtmarkt | Play the ballad, Snow, Reset view, Plain version, Lite market |
| `about.md` | Glühwein | A warm cup with Mac | Pour a mug, Prost! |
| `projects.md` | Bierstand | On tap | Pull a pint, Prost! |
| `writing.md` | Bratwurst | Off the grill | Turn the sausages, One in a bun |
| `reading.md` | Bücherstand | The bookshop | Pull a book |
| `music.md` | Bandstand | The Nachtmarkt Quartett | Play the ballad, Sax, Piano, Bass, Drums, Whole band |
| `questions.md` | Riesenrad | View from the top | Ride the wheel, Get off |
| `contact.md` | Karussell | Come round again | Ride the carousel, Ring the bell, Get off |
| `phrases.md` | (crowd) | Crowd chatter | none |

All front matter parses with a YAML loader and with the engine's own loader (`buildContent()` in `site/plugins/market.js`). Every action label has an entry in `notes`. The prose has no em or en dashes. The humanize skill's `sloplint` scores every file between 0 and 6 out of 100 (target: under 25).

Two previews, both proofing views only (the engineer owns the real panel design):

- `content_overview.jpg` (draft view): every file as a panel, with its notes, the site's toggle labels and the crowd lines. Check markers show as red tags and placeholders as amber boxes.
- `content_production.jpg` (production view, new): the same panels after the engine's own `stripNotes()` from `site/plugins/market.js`, so it shows what a visitor gets from a production build today. No placeholder text reaches the page, and none of the gated claims do.

## Launch conditions (the market owner enforces these before publishing)

The site must not go public until all three hold. The first is the only guard for one claim, so it is a hard condition, not a suggestion.

1. **No check markers left.** `grep -o '<!-- check -->' content/*.md | wc -l` prints `0`. Today it prints `11`. Ten of the eleven also sit in a block with a `[[Mac: ...]]` note (condition 2 covers them). One does not: the Riesenrad intro ("These are the questions I keep coming back to. I don't have answers to them..."). That one reaches a production build today with nothing but the invisible marker.
2. **`STRICT_CONTENT=1 npm run build` passes.** Today it fails (see "Evidence" below) with 18 placeholders in 7 files.
3. **Mac confirms the five books.** The `books` list in `reading.md` front matter feeds the 3D shelf and the "Pull a book" note, and the engine calls them "Mac's picks". A production build drops the shelf line and the list from the plain page, but the 3D shelf still names them. Mac confirms them and the YAML comment above `books` is removed, or the books are replaced.

Until the engineer's gate counts check markers, condition 1 is a manual step. After that, condition 2 covers all three except the books' front matter.

## Evidence (run in this pass, 29 Sep 2026)

`cd site && STRICT_CONTENT=1 npm run build` fails with:

```
RolldownError: content placeholders still to fill: about.md: 2, contact.md: 2, music.md: 3, projects.md: 4, questions.md: 4, reading.md: 2, writing.md: 1 (STRICT_CONTENT=1 stops the build)
```

There is no check-marker line yet, because `buildStart()` (`site/plugins/market.js:340`) still counts only `[[...]]`. The engineer was not reachable this pass (no other session was running), so the request below stands with a ready patch. Running the patch's counting logic by hand over `content/` gives the line the build would add:

```
content check markers still to confirm: about.md: 1, contact.md: 1, projects.md: 1, questions.md: 4, reading.md: 1, writing.md: 3
```

When the patch is in, re-run the build and paste its real failure line here.

The gating was checked with the engine itself: `setNotesMode('hide')` then `buildContent()` from `site/plugins/market.js`. None of these strings appear in the production content: "on the coals", "Every clinical question", "front shelf", "leans on the word", "asks for what", "causes: what made", "Write if you want". These do: "open an issue", "What is a cause", "These are the questions". "The Order of Time" also appears, from the `books` front matter (launch condition 3).

## Counts (checked with grep against the files)

- Files: 9 (`site.md`, the seven section files, `phrases.md`).
- `<!-- check -->` markers: 11. about 1, projects 1, writing 3, reading 1, questions 4 (the intro and one per question body), contact 1. music has none now (see changes).
- Of these, 10 are gated: they sit in the same block as a `[[Mac: ...]]` note, so a production build drops the claim with the note. The one ungated marker is the Riesenrad intro.
- `[[Mac: ...]]` placeholders: 18, all in bodies. about 2, projects 4, writing 1, reading 2, music 3, questions 4, contact 2. None are in front matter now that `taps` is gone.
- sloplint (`score`): about 2, contact 0, music 3, phrases 0, projects 0, questions 6, reading 0, site 0, writing 0, all out of 100. No em or en dashes anywhere in `content/`.

## Changes in pass 5 (panel fixes)

- **Unconfirmed claims are now held back by a guard that works today.** Each of these shares a block with a `[[Mac: confirm ...]]` note, so `stripNotes()` drops it from a production build:
  - `reading.md`: the shelf line "These five are on the front shelf." and the five-book list are one block (the list follows the line with no blank line, which Markdown still renders as a list). Production shows only "I read physics, philosophy and books about the brain."
  - `writing.md`: "These are on the coals." and the three working titles are one block. Production shows only the opening paragraph.
  - `questions.md`: each of the three one-line bodies carries its own confirm note. Production shows the intro and the three questions as headings, with no bodies.
  - `about.md`: the "causes" sentence is now its own paragraph with a confirm note.
  - `projects.md`: "You tell it about the study you have in mind, and it asks for what's missing." is its own paragraph with a confirm note. Production keeps only the source-material line about ProtoCol.
  - `contact.md`: the invitation ("Write if you want to talk about...") now shares the email paragraph, since it only makes sense with an address. Both go until Mac fills the email.
  - The draft view still shows every claim with its check tag and the note beside it.
- **Hard launch condition** added above, with today's count (11) and the one ungated claim named.
- **Book notes rewritten** (`reading.md`, front matter and body). They are the writer's own text, not the prototype's; pass 4's notes wrongly said otherwise. They now differ in shape and length: two short sentences (Rovelli), one long sentence (Hofstadter), a fragment (Feynman), a sentence with a colon (Seth), and a question with its answer (Pearl). Each describes the book, not Mac's view of it.
- **`taps` removed from `projects.md`.** Nothing reads it: `site/src` has no `taps` key (the only `taps` in `stalls.js` is the Bierstand's tap-handle nodes), and its three `[[Mac: ...]]` links counted as placeholders with no visible effect. The style labels ("House Pils · always on tap" and so on) stay in the body, where the panel shows them. If the engineer later wants a chalkboard menu, the body's `###` headings and italic lines hold the same data.
- **Contact has a line that survives the build**: "If you have something to say about this website, open an issue on its GitHub repository." It links to `github.com/macsermkiat/website/issues`. The repository is public with issues on (checked with the GitHub API). Production Contact is now the GitHub profile line plus this one.
- `music.md`: the check marker on the ballad title is gone. The title is not a claim about Mac; it matches `title` in `site/public/audio/manifest.json`, and the music writer owns it.
- `questions.md`: the intro opens "These are the questions I keep coming back to." Its marker also covers the choice of the three topics, which the last placeholder asks Mac to confirm. New `Ride the wheel (done)` note ("At the top. The stalls, the bandstand and the tree are all below you, and the old town round them."), which `rides.js:119` reads when the gondola reaches the top. "Ride the wheel" is now "Riding up. The market drops away below you."
- Previews re-rendered. The draft view now also lists the five books with their notes. The production view applies `stripNotes()` from `site/plugins/market.js` to the bodies.

## Changes in pass 4 (panel fixes)

- `questions.md`: every question now has one body line, each with its own `<!-- check -->`. "What is a cause?": "Science leans on the word all the time and rarely says what it means." "Is time something the brain makes?": "Physics has trouble finding a flow of time. We feel one every second." Both state what is at stake in the question and put no opinion in Mac's mouth. The improvisation line stays. In production the page now shows the intro and three questions, each with a line under it.
- `projects.md`: the closing line is now "More of my code is on [GitHub](https://github.com/macsermkiat)." It no longer suggests the three projects' code is on GitHub. The full URL is written out only in `contact.md`.
- `reading.md`: visitors no longer see placeholder admissions. "For now the front shelf holds example picks." is gone; the line is now "These five are on the front shelf." with a `<!-- check -->`. The "Pull a book" note drops its "Example pick:" prefix (`"{title} · {author}. {note}"`). A YAML comment on `books` says Mac has not confirmed them. The shelf is held back from launch by the check marker, which needs the `STRICT_CONTENT` request below.
- `music.md`: "the band gets nearer" is now "the band sounds nearer", as in the prototype.
- `about.md`: the opening is one sentence ("I'm Mac, a physician at Chulalongkorn University in Bangkok who builds software for clinical research."). The bare closing "I'm an INTJ." is gone; the interests paragraph now opens "On the Myers-Briggs I come out as an INTJ." and goes on to jazz and reading.
- `site.md`: the tagline no longer repeats About's list of interests. It is now "Physician in Bangkok. I write software for clinical research."
- This report and the builder report now give the same counts (above).


## Changes in pass 3 (earlier)

- `music.md`: the stale key is gone. Pass 2 said C minor; the ballad is in G minor (`site/public/audio/manifest.json`). The prose now gives only the title and the instrumentation, and drops the key, the metre and the length, which move as the music writer revises. The `<!-- check -->` stays on the tune title only, because Mac may rename it. The "Play the ballad" note no longer names the tune ("The band starts the ballad. Walk closer to hear it better."). The now-playing bar already takes the title from the manifest.
- `music.md`: "Pick a player to hear them up front" is now "On the full market, pick a player to hear them up front", because the lite market plays one mix (`band.js`). A new `play.lite` string holds the lite-market spotlight line, which `band.js:105` currently hard-codes.
- `site.md`: the second intro paragraph no longer repeats About's opening ("I'm Mac, a physician... clinical research."). It only lists the sections. About follows the intro on the plain page, so the bio now appears once.
- `about.md`: "jazz, ballads most of all" and "physics, philosophy and books about the brain" are gone from About. It now says "Outside work I mostly listen to jazz and read. The bandstand and the bookshop say more about both." Each interest line appears once: the ballads in `music.md`, the reading topics in `reading.md`.
- `questions.md`: the restatement lines under "What is a cause?" and "Is time something the brain makes?" are cut. Each `<!-- check -->` sits on its own line under the heading, since the topics are still unconfirmed. "A good solo sounds planned once it's over. Nobody planned it." stays.
- `site.md`: the header's fourth toggle is covered. "Lite market" is in `actions`, `toggle_labels` ("Lite market: off" / "Lite market: on") and `titles` (an off/on pair of tooltips). The engine adds the detected reasons to the "on" tooltip itself.
- Totals at the end of pass 3: 12 check markers and 16 placeholders.

## Facts that depend on other specialists

Re-checked in pass 5 against the files as they are now. Pass 2's key went stale within three hours, so re-check every round.

| Fact in `content/` | Where | Source of truth | State in pass 5 |
|---|---|---|---|
| Ballad title "Lanterns After Closing" | `music.md` body | `site/public/audio/manifest.json` `title` | Matches. |
| Drums played with brushes | `music.md` body | manifest `brushes: "swirly"`; credit names Swirly Drums (brushes) | Matches. |
| Line-up: tenor sax, piano, double bass, drums | `music.md` body, `Sax`/`Piano`/`Bass`/`Drums` | manifest `stems` (sax, piano, bass, drums, room) | Matches. |
| The lite market plays one mix | `music.md` body, `play.lite` | `band.js` `audio.separable` | Matches. |
| `play.playing`, `play.stopped`, `play.lite` | `music.md` front matter | `band.js:103-105` | **Wired.** `band.js:105` reads `pm.lite` and keeps its own line only as a fallback. Pass 4 said this was hard-coded; that was wrong or out of date. |
| Header toggle labels and tooltips | `site.md` `toggle_labels`, `titles` | `src/main.js:47` and `:49` (Lite market), `:153` (Play/Pause), `:250` (Snow) | **Not wired.** `main.js` still builds these strings itself. They are reference text only. |
| Tagline and `ui` strings | `site.md` | `content.js` `taglineHtml()` and `ui` lookup | Wired. |
| "At the top..." line | `questions.md` `Ride the wheel (done)` | `rides.js:119` | Wired (reads the `(done)` note). |
| "Pull a pint from the middle tap" | `projects.md` hint | `stalls.js:88-89` picks the middle `act_tap` | Matches. |
| Glühwein ingredients, Bratwurst "4 euros" | `about.md`, `writing.md` notes | prototype text, vendor props | Unchanged. |

## Requests to the engineer

- **`STRICT_CONTENT=1` must count check markers (most important).** In `buildStart()` (`site/plugins/market.js:340`), count `<!-- check -->` as well as `[[...]]`, and fail under `STRICT_CONTENT=1` when either is non-zero. Suggested patch, inside the existing loop:

  ```js
  const src = fs.readFileSync(path.join(CONTENT_DIR, f), 'utf8');
  const n = (src.match(/\[\[[\s\S]+?\]\]/g) || []).length;
  const c = (src.match(/<!--\s*check\s*-->/g) || []).length;
  if (n) left.push(`${f}: ${n}`);
  if (c) checks.push(`${f}: ${c}`);
  ```

  then build the message from both lists (`content check markers still to confirm: ...`). Until this is in, launch condition 1 above is manual.
- Header labels: read `site.md` `toggle_labels` and `titles` instead of the strings in `src/main.js:47`, `:49`, `:153` and `:250`. The icons (▶, ❚❚, ❄) stay the engineer's. If the engineer prefers to keep them in code, `site.md` stays reference text.
- The 3D bookshop calls the five books "Mac's picks" whatever the plain page shows. If the engineer wants a code-side guard for launch condition 3, the books could be skipped while `reading.md` still holds a placeholder. That is the engineer's call.

## Changes in pass 2 (earlier; some items were superseded in passes 3 and 4)

- `music.md`: the ballad placeholder is gone and the title "Lanterns After Closing" is in (pass 2 also gave a key and length; pass 3 removed them, see above).
- `about.md`: "The questions I like best are about causes..." now has a `<!-- check -->` (the prototype called it placeholder text). The word "German" is gone from "I like Christmas markets", so the file no longer claims which markets Mac likes. "For what it's worth," is gone, and the list of where each stall is became one line ("Each stall opens a part of it."), since the plain-page intro already lists the sections. I also cut "I also like tools that make a hard question easier to ask properly", an unmarked inference.
- `phrases.md` (new): sixteen crowd lines. The engine reads its list items through the `phrases` section, so it no longer falls back to the prototype list. I checked this with `buildContent()`. The two lines that assumed the example shelf ("Have you read Rovelli?", "Found a Feynman at the bookshop.") are dropped. "Anything good at the bookshop?" replaces them. They can come back once Mac confirms the books.
- `site.md`: `notes` means one thing everywhere: the line shown after an action. The header buttons show no line, so their notes are empty. The button labels that change live in a new `toggle_labels` map with plain `off` and `on` strings ("Play the ballad" / "Pause the ballad", "Snow: off" / "Snow: on"). The `{on|off}` template is gone. The plain-version tooltip is in a new `titles` map.
- `reading.md`: the "Pull a book" note starts with "Example pick:", as in the prototype. The body says "For now the front shelf holds example picks." Both go once Mac confirms or replaces the five books.
- `projects.md`: the finished pour says "A Helles, with a proper head of foam." again, as in the prototype. The hint still says the middle tap. The `taps` list (removed in pass 5) was the chalkboard menu. (Pass 1 said the middle handle poured the House Pils while the menu's middle entry was Target Trial Emulation. That mismatch is gone.)
- `questions.md`: each question is now its heading plus one short line that restates the question, with a `<!-- check -->` on each. The framing paragraph stays. No opinions are put in Mac's mouth.
- `writing.md`: the `<!-- check -->` moved from "These are on the coals." to each of the three working titles.

## Front matter schema (for the engineer)

Every section file has these keys:

- `section`: the key (`about`, `projects`, `writing`, `reading`, `music`, `questions`, `contact`, `site`, `phrases`).
- `stall`: the German name shown in the eyebrow. `phrases.md` has none.
- `eyebrow`: the English sub-label ("About me", "Projects" and so on). `site.md` and `phrases.md` have none.
- `title`: the panel heading. The body does not repeat it.
- `order`: the order in the places nav and on the plain page (1 to 7).
- `hint`: the line shown above the action buttons.
- `actions`: the button labels, in order. `phrases.md` has an empty list.
- `notes`: a map from action label to the line shown after pressing it. It means only that.
  - A string is shown as is. An empty string means the action shows no line (it only plays a sound or changes state).
  - A list rotates, one item per press (`Turn the sausages`).
  - `{n}` is the running count for that action tonight.
  - `Pull a pint (done)` is the line shown when the pour finishes. `Pull a pint` is the line shown while it pours.
  - In `music.md`, `{play}` is replaced by `play.playing` or `play.stopped`, or by `play.lite` on the lite market.
  - In `reading.md`, `{title}`, `{author}` and `{note}` come from the book that was pulled.
  - No other templates are used.

Extra keys some files carry:

- `crowd`: lines the nearby crowd says after an action (the `Prost!` toasts, "Smells good!").
- `books` in `reading.md`: the five spines, with a one-line note each.
- `tagline`, `description` and `ui` in `site.md`: the header line, the meta description, and the loading, hint, no-WebGL and back-link strings.
- `toggle_labels` in `site.md`: for a button whose label changes, `off` is the label while the thing is off and `on` while it is on. Covers Play the ballad, Snow and Lite market. The engine currently builds these itself; it can read them instead.
- `titles` in `site.md`: tooltip (`title` attribute) text for a button. A string, or an `off`/`on` pair for a toggle (Lite market).
- `play` in `music.md`: `playing`, `stopped` and `lite`, the three endings of a spotlight note.
- `phrases.md`: the body's list items are the crowd's speech-bubble lines, picked at random. `strip()` removes any HTML comment, so a `<!-- check -->` on a line would not show.

Two markers appear in the bodies and the build must handle them:

- `<!-- check -->` follows a claim about Mac that is not in the source material. Markdown renderers drop HTML comments, so it stays invisible, and a production build drops it silently. It is therefore never the only guard where that can be avoided: 10 of the 11 share a block with a `[[Mac: confirm ...]]` note. It blocks the public launch (Launch conditions, 1).
- `[[Mac: ...]]` is a fact Mac has to supply, or a claim he has to confirm. In development they render as visible amber notes. A production build drops the whole paragraph or list item that holds one, so an unconfirmed claim placed in the same block goes with it. The build warns about them and stops under `STRICT_CONTENT=1`. `STRICT_CONTENT=1` should also count `<!-- check -->` (see Requests to the engineer and Launch conditions).

## Choices worth knowing

- Action labels follow the brief where it differs from the prototype: "Pour a mug" (prototype: "Pour a cup"), "One in a bun" ("One in a bun, please"), "Pull a book" ("Pick a book for me"), "Ride the wheel" ("Ride to the top") and "Ride the carousel" ("Ride a horse"). The notes use the prototype's wording otherwise. The market owner may want to confirm this.
- The music text describes recorded stems, following ADR 0002, not notes written live in the browser.
- Nothing in the text uses clinical or lab imagery as decoration. Clinical research appears only where it describes Mac's actual work (projects, the about line, one writing title).
- The plain-page intro does not mention phones, because phones get the lite market, not the plain page.

## For Mac to check

- 11 `<!-- check -->` markers: the "causes" line in About, the ProtoCol interaction line, each of the three writing titles, the reading shelf, the big-questions intro (and with it the three topics), the three one-line question bodies, and the contact invitation.
- Employment at Chulalongkorn and INTJ are in the brief, so they carry no marker.
- 18 placeholders. Facts to supply: your department line; the ProtoCol link and who it's for; the YouTube playlist link and lesson count; where the transfusion audit runs and whether it can be shown; the book you're reading now; three records; your email; other profiles. Claims to confirm: the causes line, the ProtoCol line, the writing titles, the five books, the three question lines and the three topics.
- Nothing is invented about credentials, dates, employers or publications.

## Next

- Once Mac answers: fill the placeholders, delete each confirm note with the claim it guards (or rewrite the claim), and remove the matching check markers. Then add book-specific crowd lines back to `phrases.md`.
- Paste the real `STRICT_CONTENT=1` failure line once the engineer's check count is in.
- Re-check the "Facts that depend on other specialists" table each round.

## Contract

No breaks. Writes only in `content/` and `review/round-1/writer/`. No third-party assets, so nothing added to `CREDITS.md`. Nothing to report on triangle or file budgets: the nine files total about 11 KB. The two preview JPEGs are 1280 px wide, about 700 KB (draft) and 470 KB (production).
