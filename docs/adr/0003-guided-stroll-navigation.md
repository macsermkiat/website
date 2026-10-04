# 3. Guided stroll instead of free camera

Status: proposed (2026-10-04), waiting on Mac's choice

## Context

Mac likes the market but finds free orbit over the whole square hard to control on a website. Loading everything at full detail from any angle is also slow: the desktop first load is 19.7 MB. The free-camera version is kept on the branch `original-free-camera`.

## Decision (proposed)

Visitors move between fixed stops instead of flying freely.

- Home: one composed view of the square with a slow drift and no free orbit. A pre-rendered still of that view shows first, and the live scene fades in behind it once loaded.
- A market signpost that is always visible lists the seven places. Choosing one moves the camera along an authored lane path to that place's stop (`cam_view`), never through stalls.
- At a stop, look-around is clamped to about ±15° yaw and a small zoom band. Items stay clickable. Prev and next arrows, and arrow keys, walk to the neighbouring stop along the lane.
- The Riesenrad stop is the overview of the whole market.
- Streaming: the home view loads the square, the town ring and lite stand-ins. A stall loads at full detail when it is the current or next stop. Distant stalls stay lite or impostors.
- Phones use the same stops and taps, with the lite assets.

## Consequences

- The first load should drop to roughly 5 MB. This is an estimate to be measured with `npm run budget`.
- Unseen back sides can be culled from the stall exports later.
- The engineer owns the camera, path and streaming code. The architect authors the lane path and stop order in `site/src/layout.json`, and the lighting designer adds a baked home still.
