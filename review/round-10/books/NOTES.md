# Bücherstand: English groupings and readable covers (round 10)

Mac (2026-10-06): "Bookshelf groupings should be in English. Some of the book titles are hard to read."

What changed
- Cabinet signs on stall_buecher.glb / .lite.glb, the head band on every cover, the stop-bar buttons, the hover
  labels, the cabinet notes and the bookshelf lists on the text page use `label_en`. `label_de` stays in
  content/books/categories.json. No label was shortened: the signs set themselves on one or two lines
  (buecher.py `sign_layout`), letters 0.094 m (lives, the narrow cabinet) to 0.13 m; the German two-line signs were 0.10 m.
- Covers (atlas_books.g_cover): the title panel takes two thirds of the cover; every title is set in Oswald 700
  capitals, light on a dark panel; up to six lines before the type shrinks, never below a cap height of 8.4 % of
  the cover; very long words break at a syllable (Super-communi-cators). The emblem is gone and the author band
  is smaller. The people cabinet's cream panel washed out in the browser, so it is dark brown like the others
  (its spines keep their dark lettering), and its covers glow at a third.
- Books atlas 4096 x 3072 (was 2048 x 3584), covers at 22 px/cm (was 15). Lite colour map 1024 x 768 (was 512 x 896),
  so this one lite texture is above the 512 px rule.
- An open cabinet folds the stop bar on every screen and is framed in the clear part of the stage above it (at
  1366 x 768 the bar used to hide the people cabinet's bottom row).

Sizes: Bücherstand 61.7k triangles, 3.49 MB with props and shared textures (budget 80k / 4 MB). First load
unchanged: full 8.48 MB, lite 6.38 MB (the books textures stream with the stall).

Still soft: on a 390 px phone at device pixel ratio 1 a cover is about 55 px wide, so the four-line titles
(Unreasonable Hospitality, Set Boundaries, Find Peace) read only on a close look, and authors do not read there.
The people cabinet's cream lettering blooms a little under the hut lamp.
