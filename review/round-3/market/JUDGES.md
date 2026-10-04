# Whole-market judge (Opus), after round 3

## Improve

Checks:
- pass: 1. Reads as a German Christmas night market from home: In home_full.jpg I can see the Ferris wheel, a striped carousel, the bandstand with the quartet, the lit tree with its star, a church and half-timbered houses, stalls strung with lights, and groups of people. The Bier vom Fass and Bücher stalls are identifiable, but at this distance the Glühwein and Bratwurst signs are small.
- pass: 2. Realistic miniature with warm storybook feel: home_full.jpg and stall_buecher_threejs.jpg show wood grain, shingle roofs, warm bulb light on the cobbles and a moonlit blue sky, so it does not look flat. The people are simple low-poly figures, though.
- pass: 3. Each place opens its section: panel_gluehwein.jpg shows 'Glühwein · About me', item_bier_prost.jpg 'Bierstand · Projects' and item_books_open.jpg 'Physik & Kosmos'. The chips in plain_html.jpg map all seven places correctly (Bratwurst Writing, Bandstand Music, Riesenrad Big questions, Karussell Contact).
- pass: 4. Individual items separately clickable with own animation: The panels list 'The goods, one by one' (39 at Glühwein, 18 at Bier) and have Pour a mug, Pull a pint and Prost actions. A Prost! bubble shows in panel_gluehwein.jpg, and there are separate item shots for the bottle, ladle, wurst bun and turning.
- pass: 5. Bookshop holds 55 books on six labelled shelves, book shows summary/key ideas: stall_buecher_threejs.jpg shows all six category signs, and the carpenter's notes give the per-section counts (10+9+6+11+14+5=55). In item_books_open.jpg, 'The Biggest Ideas in the Universe' opens with In short and Summary.
- pass: 6. Phone lite market works and plain.html carries content: phone_home.jpg shows the lite market rendering in portrait with snow and readable controls. plain_html.jpg has all seven section links and the About text in full.
- pass: 7. First load within budgets: The engineer's NOTES budget table gives first load as 19.69 MB desktop (aim 25) and 7.44 MB lite (aim 8). Only the 'everything' totals, which include deferred files, go over the aims (26.92 and 10.06 MB), and the notes explain why.
- pass: 8. No lab/pathology/clinical imagery: None of the scene images I opened show any lab, pathology or clinical imagery. 'Clinical research' appears only in the bio text.
- FAIL: 9. Nothing visible looks broken: In item_bier_prost.jpg the Bier vendor's white sleeves blow out to glare, his hat reads as a grey blob, the camera sits so close that the pints fill the frame, and the glasses look empty. In panel_gluehwein.jpg the vendor's face is a dark smudge under a white-blown scarf.

Fixes:
- lighting: Tame the glare on the stall vendors' light clothing (Bier vendor's sleeves, Glühwein vendor's scarf): lower light_1 intensity on close-up views or cut the emissive/specular on the people materials, and fill the faces so they read.
- engineer: Pull the Bier item and close-up camera back so the tap, the vendor and a full pint fit the frame, as in the Glühwein panel framing.
- vendor: Fill the pints with clearer, golden beer and a foam head (goods.beer_fill), and fix the Bier vendor's hat so it reads as a hat, not a grey blob.
- carpenter: Enlarge the Glühwein and Bratwurst main signs, or make them emissive, so they read from the home view the way 'Bier vom Fass' does.
- organizer: Re-run crowd_plan.py so the Bücherstand browsers stand in front of the carts and racks (y about -2.6), not inside the carts.
