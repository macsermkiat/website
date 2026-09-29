# Latest judges on vendor, end of round 1

## Opus (pass 3): Improve

Failed checks:
- NOTES and builder claims match the files: NOTES says the reading-list titles are act_book_21..27, but those nodes are Road to Reality, Moby-Dick and others; the real titles are act_book_12..18. NOTES and the report also say the previews show each set 'on the carpenter's current stall glb', but vstage.env_counter() renders a generic plain wooden counter.
- Hero close-ups frame the named subject: prop_bier_counter_hero.jpg cuts off the tap tower at the top of the frame, so no tap handle is visible, although NOTES lists this shot as 'foam heads, taps'.
- Books counter reading lamp with a light_ empty (brief): prop_books_counter has no light_ node. Dropping it keeps the stall within the contract's cap of 2 lights, which is a fair choice, but it is documented only in a set_books.py comment and not in NOTES.
- Varied book stock: The 108 act_book nodes have only 55 unique titles. About 40 of shelf 2's 49 books repeat shelf 1, and The Mind's I appears twice on shelf 2 itself (act_book_100 and act_book_148), so clicking around shows the same books again.
- Deco goods read as a well-stocked market stall: The contact sheet shows long empty counters. Lebkuchen has 3 small trays and 11 hearts on a 2.2 m counter, Schmuck has two bauble trays plus a sparse hanging row, and Maroni has one roaster and a few bags. The 20k budget mostly explains it, but the goods don't meet the realistic-miniature bar yet.

Fixes:
- Correct NOTES.md: the five reading-list titles are act_book_12..18 (not 21..27). Also state that the previews use the generic plain counter from vstage.env_counter(), not the carpenter's stall glb, and change the 'all 9 tiles show the stall' wording to match.
- Re-render prop_bier_counter_hero.jpg so the three tap handles and the foam heads are both in frame.
- Make the beer foam read as foam, not white caps. Keep the head inside the glass rim, or only slightly proud of it, and make the domed crown and spill drip visible in the close-up.
- Record the reading-lamp decision in NOTES under contract questions: the brief asks for a light_ empty, and it was dropped to stay within the 2-lights-per-section-stall cap.
- Cut repeated book titles. Give shelf 2 mostly different titles from shelf 1 and remove the second copy of The Mind's I (act_book_148), so every click on a spine shows a new book.
- Fill out the deco counters within budget. Use cheap, instanced shapes: stacked Lebkuchen boxes and more hearts, baubles in open cartons on Schmuck, and bag stacks and cones on Maroni and Mandeln. The long bare stretches of counter should read as crowded, and the 20k limit should still hold (Mandeln, Spielzeug and Schmuck have only 160–230 triangles to spare, so trim first there).

## Fable (pass 3): Improve

Failed checks:
- Reading lamp on prop_books_counter has a light_ empty (brief): No light_ node in any prop glb; set_books.py says it was omitted because the stall already carries its 2 light_ empties (BUILD.md cap), and check_props even FAILs if one is added. Reasonable, but NOTES.md does not report this deviation from the brief.

Fixes:
- Correct NOTES.md (and the report): the five reading-list titles are act_book_12..18 in prop_books_shelf_1, not act_book_21..27; the 'Animation nodes and pivots' section should point to the right node ids.
- Record the missing light_ empty on the reading lamp in NOTES.md as a deliberate deviation from the brief (because BUILD.md caps a section stall at 2 light_ empties, which stall_buecher already uses), and ask the market owner whether the lamp should instead take one of those two.
- Buy back deco headroom: Schmuck (163 tris), Spielzeug (200) and Mandeln (231) leave the carpenter almost no room; trim bauble rings/Spanbäume or agree a split of the 20k with the carpenter so a small stall change does not break the build check.
- Optional polish: deco counters read sparse for a market stall (Käse three wheels and one board; Lebkuchen three items on a 2 m board; Bratwurst counter middle is empty). Add cheap flat goods (paper, price cards, cloth) within the remaining budget. Also note the full atlas is 2048 px versus the contract's 1024 standard step; confirm with the market owner that this is acceptable.

