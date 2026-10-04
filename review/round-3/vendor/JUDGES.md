# Judges on vendor, round 3 pass 1

## Ship

Fixes:
- Make the beer clearer and more golden in goods.beer_fill; it reads as opaque orange
- Re-render the stale prop_books_counter.jpg wide shot and add wide shots for the mind, people and craft sets
- Reduce lite triangle ratios on the 7 warned sets toward one third

## Ship

Failed:
- {'check': 'The five named titles are legible on book spines in a preview', 'pass': False, 'evidence': "Only The Order of Time (prop_books_physics_hero.jpg) and The Book of Why (prop_books_decisions_hero.jpg) are legible; Gödel Escher Bach, Feynman Lectures and Being You are not in categories.json and BUILD.md's round-3 rule (categories.json is the only source, invented titles go) deliberately removed them. Not a defect against the current contract."}

Fixes:
- Decide on the three dropped round-1 titles (Gödel, Escher, Bach; Feynman Lectures; Being You): either the writer adds them to content/books/categories.json or the brief's named-title list is retired; the vendor needs no change either way.
- Cosmetic: make the Helles clearer and more yellow in goods.beer_fill so the pints read as beer rather than orange juice in the Cycles target render.
- Trim the seven lite sets still above 40 % of full triangles (bier_back, books_counter, mandeln, spielzeug, schmuck, kaese, maroni) toward the one-third guideline, and keep an eye on Kartoffelpuffer's 422-triangle headroom if the carpenter touches that stall.
- Re-render prop_books_counter.jpg (wide) so it matches the easel-leg fix, and add in-stall close-ups of the category sets for the engineer's reading-view camera.
