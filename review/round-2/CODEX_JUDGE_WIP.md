# Codex judge, round 2 work in progress (build/round-2 @ 98801ea)

Verdict: Improve. Codex did not rerun builds or tests.

Top fixes, in priority order:
1. The content gate must be mandatory for deploy: .github/workflows/pages.yml:46 has strict mode off.
2. Resolve unverified content: about.md (employment and INTJ are unmarked), reading.md, questions.md and the book summaries. plugins/market.js:211 must not reinstate the unconfirmed book list.
3. Budget accounting: budget.mjs must count deferred assets and desktop LODs, fail when dist is missing, and dedupe textures.
4. Meet the download limits. Lite is 8.05 MB before JS/CSS, and desktop has 6 KB left. The Bücher stand is 3.04 MB against its 3 MB budget; book textures first.
5. Cabinet books in stall_buecher.glb are one merged untitled mesh. Make them individually clickable with named pivots in items.json.
6. Phone and ride framing: a pole in the phone home view, and a beam in the Ferris ride.
7. Close-up lighting: white bulb cores, hard shelf shadows, sign fixtures.
8. Verification: record real smoke results and replace VERIFY_PLACEHOLDER in the engineer NOTES.
9. bandstand plus instruments is 66.8k triangles (limit 50k). The crowd still embeds repeated clips, and people_anims.glb is not loaded at runtime.
10. Matched browser-vs-Cycles comparisons, and reconcile stale statements in role notes.
