# Writer, round 1 (pass 3)

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

All front matter parses with a YAML loader and with the engine's own loader (`buildContent()` in `site/plugins/market.js`). Every action label has an entry in `notes`. The prose has no em or en dashes. The humanize skill's `sloplint` scores every file 0 or 1 out of 100.

Preview: `content_overview.jpg` shows every file as a panel, now with its notes, the site's toggle labels and the crowd lines. Check markers show as red tags and placeholders as amber boxes. It is a proofing view only. The engineer owns the real panel design.

## Changes in pass 3

- `music.md`: the stale key is gone. Pass 2 said C minor; the ballad is in G minor (`site/public/audio/manifest.json`). The prose now gives only the title and the instrumentation, and drops the key, the metre and the length, which move as the music writer revises. The `<!-- check -->` stays on the tune title only, because Mac may rename it. The "Play the ballad" note no longer names the tune ("The band starts the ballad. Walk closer to hear it better."). The now-playing bar already takes the title from the manifest.
- `music.md`: "Pick a player to hear them up front" is now "On the full market, pick a player to hear them up front", because the lite market plays one mix (`band.js`). A new `play.lite` string holds the lite-market spotlight line, which `band.js:105` currently hard-codes.
- `site.md`: the second intro paragraph no longer repeats About's opening ("I'm Mac, a physician... clinical research."). It only lists the sections. About follows the intro on the plain page, so the bio now appears once.
- `about.md`: "jazz, ballads most of all" and "physics, philosophy and books about the brain" are gone from About. It now says "Outside work I mostly listen to jazz and read. The bandstand and the bookshop say more about both." Each interest line appears once: the ballads in `music.md`, the reading topics in `reading.md`.
- `questions.md`: the restatement lines under "What is a cause?" and "Is time something the brain makes?" are cut. Each `<!-- check -->` sits on its own line under the heading, since the topics are still unconfirmed. "A good solo sounds planned once it's over. Nobody planned it." stays.
- `site.md`: the header's fourth toggle is covered. "Lite market" is in `actions`, `toggle_labels` ("Lite market: off" / "Lite market: on") and `titles` (an off/on pair of tooltips). The engine adds the detected reasons to the "on" tooltip itself.
- Totals: 12 check markers and 16 placeholders, as before (the music marker moved from the key sentence to the title).

## Facts that depend on other specialists

Re-check these every round. Pass 2's key went stale within three hours.

| Fact in `content/` | Where | Source of truth | Owner |
|---|---|---|---|
| Ballad title "Lanterns After Closing" | `music.md` body | `site/public/audio/manifest.json` `title` | music writer |
| Band line-up: tenor sax, piano, double bass, drums with brushes | `music.md` body, `Sax`/`Piano`/`Bass`/`Drums` notes and actions | manifest `stems` (sax, piano, bass, drums) and `band.js` names | music writer, organizer |
| "Each player sits in their own place, so the sound follows where you stand" | `music.md` body | stems mode in `src/audio/stems.js` | engineer |
| The lite market plays one mix | `music.md` body, `play.lite` | `band.js` `audio.separable` | engineer |
| Header buttons (Play, Snow, Reset view, Plain version, Lite market) | `site.md` `actions`, `toggle_labels`, `titles` | `site/index.html`, `src/main.js` | engineer |
| "Pull a pint from the middle tap" | `projects.md` hint | the Bierstand model's tap handles | carpenter, vendor |
| Glühwein ingredients, Bratwurst "4 euros" | `about.md`, `writing.md` notes | prototype text, vendor props | vendor |

Key, metre and length are deliberately not in the prose. If the engine wants them, it can read them from the manifest.

## Requests to the engineer

- `STRICT_CONTENT=1`: please count `<!-- check -->` markers as well as `[[...]]` placeholders in `buildStart()` (`site/plugins/market.js`, around line 253). A public launch should not go out with unconfirmed claims. The comments are invisible on the page, so nothing else catches them.
- Header labels: please read `site.md` `toggle_labels` and `titles` instead of the hard-coded strings in `src/main.js:42` (Lite market), `:128` (Play/Pause the ballad) and `:186` (Snow). The icons (▶, ❚❚, ❄) are the engineer's; `site.md` supplies only the words. If the engineer prefers to keep the header strings in code, `site.md` stays the reference text and the header set remains the engineer's call.
- `band.js:105`: please read `play.lite` from `music.md` instead of the hard-coded lite-market line.

## Changes in pass 2

- `music.md`: the ballad placeholder is gone and the title "Lanterns After Closing" is in (pass 2 also gave a key and length; pass 3 removed them, see above).
- `about.md`: "The questions I like best are about causes..." now has a `<!-- check -->` (the prototype called it placeholder text). The word "German" is gone from "I like Christmas markets", so the file no longer claims which markets Mac likes. "For what it's worth," is gone, and the list of where each stall is became one line ("Each stall opens a part of it."), since the plain-page intro already lists the sections. I also cut "I also like tools that make a hard question easier to ask properly", an unmarked inference.
- `phrases.md` (new): sixteen crowd lines. The engine reads its list items through the `phrases` section, so it no longer falls back to the prototype list. I checked this with `buildContent()`. The two lines that assumed the example shelf ("Have you read Rovelli?", "Found a Feynman at the bookshop.") are dropped. "Anything good at the bookshop?" replaces them. They can come back once Mac confirms the books.
- `site.md`: `notes` means one thing everywhere: the line shown after an action. The header buttons show no line, so their notes are empty. The button labels that change live in a new `toggle_labels` map with plain `off` and `on` strings ("Play the ballad" / "Pause the ballad", "Snow: off" / "Snow: on"). The `{on|off}` template is gone. The plain-version tooltip is in a new `titles` map.
- `reading.md`: the "Pull a book" note starts with "Example pick:", as in the prototype. The body says "For now the front shelf holds example picks." Both go once Mac confirms or replaces the five books.
- `projects.md`: the finished pour says "A Helles, with a proper head of foam." again, as in the prototype. The hint still says the middle tap. The `taps` list is the chalkboard menu, top to bottom, and has a YAML comment saying it does not map to the three tap handles. (Pass 1 said the middle handle poured the House Pils while the menu's middle entry was Target Trial Emulation. That mismatch is gone.)
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
- `taps` in `projects.md`: the chalkboard menu, top to bottom: name, style label and link. It does not map to the tap handles.
- `books` in `reading.md`: the five spines, with a one-line note each.
- `tagline`, `description` and `ui` in `site.md`: the header line, the meta description, and the loading, hint, no-WebGL and back-link strings.
- `toggle_labels` in `site.md`: for a button whose label changes, `off` is the label while the thing is off and `on` while it is on. Covers Play the ballad, Snow and Lite market. The engine currently builds these itself; it can read them instead.
- `titles` in `site.md`: tooltip (`title` attribute) text for a button. A string, or an `off`/`on` pair for a toggle (Lite market).
- `play` in `music.md`: `playing`, `stopped` and `lite`, the three endings of a spotlight note.
- `phrases.md`: the body's list items are the crowd's speech-bubble lines, picked at random. `strip()` removes any HTML comment, so a `<!-- check -->` on a line would not show.

Two markers appear in the bodies and the build must handle them:

- `<!-- check -->` follows a claim about Mac that is not in the source material. Markdown renderers drop HTML comments, so it stays invisible. Treat it as blocking for the public launch: the site should not go public while any remain.
- `[[Mac: ...]]` is a fact Mac has to supply. Today these render as visible amber notes: `plainHtml()` gives 13 `formac` spans in the plain page body, and 3 more placeholders sit in the `taps` links in front matter. The build warns about them and stops under `STRICT_CONTENT=1`. **The content cannot ship until they are filled, or the build hides them.** `STRICT_CONTENT=1` should also count `<!-- check -->` (see Requests to the engineer).

## Choices worth knowing

- Action labels follow the brief where it differs from the prototype: "Pour a mug" (prototype: "Pour a cup"), "One in a bun" ("One in a bun, please"), "Pull a book" ("Pick a book for me"), "Ride the wheel" ("Ride to the top") and "Ride the carousel" ("Ride a horse"). The notes use the prototype's wording otherwise. The market owner may want to confirm this.
- The music text describes recorded stems, following ADR 0002, not notes written live in the browser.
- Nothing in the text uses clinical or lab imagery as decoration. Clinical research appears only where it describes Mac's actual work (projects, the about line, one writing title).
- The plain-page intro does not mention phones, because phones get the lite market, not the plain page.

## For Mac to check

- 12 `<!-- check -->` markers: the "causes" line in About, the ProtoCol interaction line, each of the three writing titles, the reading shelf, the ballad title, the big-questions intro and its three topics, and the contact invitation.
- Employment at Chulalongkorn and INTJ are in the brief, so they carry no marker.
- 16 placeholders: your department line; the ProtoCol link and who it's for; the YouTube playlist link and lesson count; where the transfusion audit runs and whether it can be shown; real writing titles; the five books and the one you're reading now; three records; your email and other profiles. (Three of these are the `taps` links in `projects.md`.)
- Nothing is invented about credentials, dates, employers or publications.

## Next

- Replace the placeholders once Mac answers, and drop the check markers he confirms.
- After Mac answers: fill the 16 placeholders (including the 3 `taps` links in `projects.md` front matter), resolve the 12 check markers, then remove "Example pick:" and "For now".
- Once the shelf is confirmed, write the spine notes for his real books in different shapes. The five example notes share one rhythm (sloplint uniformity 2 on `reading.md`); they are prototype text and marked as examples, so they stay until then. Then add book-specific crowd lines back to `phrases.md`.
- Re-check the "Facts that depend on other specialists" table against the manifest and the engine each round.
- Write short notes for the Riesenrad questions once Mac picks topics.

## Contract

No breaks. Writes only in `content/` and `review/round-1/writer/`. No third-party assets, so nothing added to `CREDITS.md`. Nothing to report on triangle or file budgets: the nine files total about 11 KB.
