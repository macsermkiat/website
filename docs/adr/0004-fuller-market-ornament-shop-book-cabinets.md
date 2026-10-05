# 4. A fuller market, an ornament shop and book cabinets

Status: accepted (2026-10-05), except the bookshelf design, which is the recommended option while Mac decides.

Mac (2026-10-05): "The empty, unclickable stalls should fill with something. Should have more people walk around, even outside main stall, it looked too silent. Create ornament shop, with selling variety of ornaments, that we can interact with. Bookstand is hard to select book. Too much book, put in there and it too close to each other."

## Context

The nine deco stalls stand on the outer lanes (x = ±21) and the back row (z ≈ -21). The guided stroll from ADR 0003 never goes near them, they have no vendor, and from the lanes they read as dark, half-empty huts. About 36 people stand or walk, almost all near the four section stalls and the bandstand. The Bücherstand packs 55 spines tightly onto six sections, so a single book is a small, crowded target, worst on a phone.

## Decision

### Deco stalls are full, as cheap scenery

Mac (2026-10-05): "There's no need to fully render object in side stores, because there will be no interaction to save the loading time."

- Every deco stall is visibly stocked from the lane: goods on the counter, on the back shelves, hanging from the eaves or a rail, and a crate or basket out front. No bare boards.
- The goods are low-detail scenery merged into one or two meshes per stall on the shared atlas: no `act_` nodes, no `items.json` entries, no clicks, no close-up, and the stall never streams beyond its light file.
- Each stall has a vendor behind its counter and one or two customers at it.
- The stroll's loop passes the left lane, the back row and the right lane, so the stalls are seen at walking pace.
- The ornament shop is the one side stall that stays interactive.

### More people, everywhere

- The full market holds about 80 people; the lite market keeps its first 40 crowd entries.
- People stand and walk on every lane: the deco lanes, the back row, around the tree, by the rides and at the edges of the square, not only by the section stalls.
- The engine instances people, swaps to the lite variant beyond about 25 m, and updates animation less often for distant people, so frame time stays in budget.

### Christbaumschmuck becomes an ornament shop

- `deco-schmuck` becomes a larger ornament shop (`stall_schmuck.glb`, budget 40k triangles and 2 MB with its goods). It is an eighth stroll stop and has an arm on the signpost. It carries no section text; it is for play.
- Goods, each its own `act_` node: glass baubles in several colours and painted patterns hung on rails, figure ornaments (a Weihnachtsgurke pickle, a pine cone, a clip-on bird, a mushroom, an icicle), straw stars, carved wooden stars and angels, a lit Herrnhut star, a nutcracker, a Räuchermännchen (incense smoker), a Schwibbogen candle arch and a small display tree.
- Interactions: a bauble spins and rings a soft glass note (each bauble a different note, so a row plays a scale); the Herrnhut star lights; the nutcracker's jaw opens; the Räuchermännchen puffs smoke; the Schwibbogen candles light one by one; a clicked ornament can be hung on the display tree; the pickle is hidden somewhere in the shop and finding it gets a small reward.

### Bücherstand: category cabinets (recommended, pending Mac)

- Six glazed cabinets, one per category, each with its German label. At rest each cabinet shows a few covers face-out and the rest as spines, as scenery.
- Picking a book takes two steps: tap a cabinet (or its sign), the camera moves to its `cam_cat_<key>` and its books come forward face-out on angled boards; then tap a book. Never more than 14 targets at once. At 390 px wide each cover is at least 44 px.
- Covers are designed in-house (title and author typography on a colour and pattern per category), not publisher cover art.
- Keyboard: arrows move between cabinets and books; the hidden HTML copy lists the titles.

## Consequences

- First-load size must stay near 8 MB (full) and 6 MB (lite); the extra people and goods stream with their stalls.
- The ornament shop and the cabinets need new node rules (below, and in BUILD.md).
- If Mac picks another bookshelf design, the carpenter, vendor and engineer redo that part.

## Revision: ornament shop sparkle and fewer, bigger interactions

Mac (2026-10-05): "Ornament shop should have more sparkle decoration and goods. No need to be interactive in everything, but the one that interactive must be wow. not slop."

Dressing (sparkle in three tiers, with dark wood left between clusters):
- Hero: an antique foxed mirror on the upper back wall that doubles the baubles, and a slowly turning Erzgebirge candle pyramid on the counter.
- Medium: mercury-glass and high-gloss baubles in silver, gold, copper and teal in several sizes; two or three gold and silver Lametta swags with a view-dependent glint shader; glass icicles and pine cones; Rauschgoldengel gold-foil angels; glass bead garlands; bulb strings inside the canopy with one warm light near the ceiling; a big lit star on the roof ridge.
- Subtle: snow globes, spun-glass birds, two more lit Herrnhut stars at different heights.
- The nutcracker, smoker (smoking on its own), pyramid and the rest are decoration, not clicks.

Interactions (recommended set, pending Mac; three only, each a moment):
1. Hero: the Schwibbogen wakes the town. Its candles light one by one from the outside in; with each flame more windows in the old town turn warm, a low chord builds, and the last flame sends a slow wave of light across the market before it settles.
2. Glass harmonica: the baubles on the front rail are tuned to the ballad's melody. Brushing across them (drag or tap in order) plays it with long glassy decays; after a pause the next bauble glows faintly so visitors find the tune.
3. Reflection dive: tapping the big mercury-glass bauble moves the camera in until the curved, live reflection of the lit market fills the view, then crossfades into the market seen from inside the glass, hushed like a snow globe, and back out.
