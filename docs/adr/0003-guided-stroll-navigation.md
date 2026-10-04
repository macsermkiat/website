# 3. Guided stroll instead of free camera

Status: accepted (2026-10-04). Mac: "Market signpost is interesting, the camera just follow along the path."

## Context

Mac likes the market but finds free orbit over the whole square hard to control on a website. Loading everything at full detail from any angle is also slow: the desktop first load is 19.7 MB. The free-camera version is kept on the branch `original-free-camera`.

## Decision

Visitors move between fixed stops instead of flying freely.

- Home: one composed view of the square with a slow drift and no free orbit. A pre-rendered still of that view shows first, and the live scene fades in behind it once loaded.
- A wooden finger signpost in the scene (and a small copy of it on screen) lists the seven places. Choosing one moves the camera along an authored lane path to that place's stop (`cam_view`), never through stalls.
- At a stop, look-around is clamped to about ±15° yaw and a small zoom band. Items stay clickable. Prev and next arrows, and arrow keys, walk to the neighbouring stop along the lane.
- The Riesenrad stop is the overview of the whole market.
- Streaming: the home view loads the square, the town ring and lite stand-ins. A stall loads at full detail when it is the current or next stop. Distant stalls stay lite or impostors.
- Phones use the same stops and taps, with the lite assets.

## Consequences

- The first load should drop to roughly 5 MB. This is an estimate to be measured with `npm run budget`.
- Unseen back sides can be culled from the stall exports later.
- The engineer owns the camera, path and streaming code. The architect authors the lane path and stop order in `site/src/layout.json`, and the lighting designer adds a baked home still.

## Text lives in the market, not in panels

Mac (2026-10-04): "I don't want the text as a separate component window from the market. It should be in the environment." So the HTML side panels go. Each section's words sit on an object that belongs to that stall, and the camera moves in close enough to read them:

- Glühwein (About): a chalkboard menu board behind the counter, written in chalk. Wine bottles show their tasting note on the label when turned.
- Bierstand (Projects): one Bierdeckel (beer coaster) per project on the counter. Picking one up shows the name on the front, and flipping it shows the description. A chalk 'vom Fass' board lists the projects like beers on tap.
- Bratwurst (Writing): a menu board lists the pieces like dishes. Choosing one shows it printed on the market-paper the sausage is wrapped in.
- Bücherstand (Reading): a clicked book opens in front of the camera with its summary and key ideas on its pages. Clicking a page corner turns the page.
- Bandstand (Music): the programme and notes on sheet music on the music stand.
- Riesenrad (Big questions): each question on a placard hung in a gondola. The ticket-booth noticeboard holds the short essays.
- Karussell (Contact): a ticket in the ticket-booth window carries the contact details and links.

Long text is paginated (page turns, coaster flips), never scrolled. Text is drawn as crisp 3D text on the object's writing surface. A visually hidden HTML copy of whatever is being read stays in the page for screen readers and keyboard users, and plain.html is unchanged.
