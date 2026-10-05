# Round 8 judges: carpenter

Final: Ship / Ship after 1 pass(es).

## Pass 1

### Judge Opus: Ship
- FAIL User's goal: less loading for the side stalls: The deco assets are now lighter, but main.js STREAMED (line 61) leaves out kind 'deco', so the full market still loads the full deco glbs. This needs an engineer change

### Judge Fable: Ship

Open issues from the builder:
- Engine (engineer): main.js still loads the full deco_<key>.glb on the full market, because STREAMED leaves out kind 'deco'. ADR 0004 says a deco stall never loads more than its lite file; pointing the deco entries at the .lite.glb on both markets would save about 1 MB more of first load. Both levels have the same node tree.
- Deco stalls keep cam_view/cam_target only because the node check and layout.json still read them. The camera never flies there any more.
- The deco contact sheet shows the vendor's goods as they are on disk mid-round. Their scenery goods (rail and crate sets) are still in progress, so it needs a re-render once they are done.
- Carried over: the ornament shop and cabinet previews use stand-in goods until the vendor's prop_schmuck_* and new prop_books_<key> sets are final. The cabinet signs are small from the home view. The ornament shop's sides are simpler than its front. The emissive stand-in materials remain. Bevels are real geometry on the section stalls.
