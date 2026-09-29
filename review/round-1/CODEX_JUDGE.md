# Codex judge, round 1 snapshot (build/round-1 @ 6b1ebb1)

Verdict: Improve.

Failed checks:
- Naming contract: the assembled Bücher stand has three light markers (stall_buecher light_0/1 plus prop_books_counter light_lamp), over the limit of two.
- Budgets: desktop first load 25.62 MB (limit 25) and lite 10.64 MB (limit 8), counting external textures. Audio loads after interaction.
- Maintainability: layout.json references riesenrad.glb and karussell.glb, but the files are ferris.glb and carousel.glb. The code recovers by guessing filenames.
- Content: unmarked claims (employment, INTJ) in content/about.md; music.md says C minor but the manifest says G minor.

Top fixes, in priority order:
1. Meet both download budgets. Slim the lite town and square, share person animations, and count external textures in budget checks.
2. Recover visible detail in site/src/lighting (settings.js, grade.js). Reduce glare and moon dominance, keep signs readable, and lift crowd and facade detail.
3. Lite light allocation should prioritise the entered stall. Fix the Bücher third light.
4. Gate public content: resolve placeholders and check markers, make the build reject check comments in strict mode, and fix the music key.
5. Show audio and asset credits on index.html and plain.html.
6. A clicked book must identify itself: map act_book_* nodes to their real titles (actions/stalls.js:180).
7. Fix panel and ride framing and foreground obstruction. The phone reduced-motion view shows almost no market.
8. Add AO occlusion textures to the props, people, town and tree glbs.
9. Use exact asset bindings in layout.json, and report invalid ones instead of guessing.
10. Smoke tests should assert node movement and book identity. Refresh the screenshots.

Prototype port notes:
- Add a plain-HTML fallback when WebGL fails.
- Give the canvas an accessible name.
- Mute must cover stall sounds too.
- Credits need source URLs.
