---
name: verify
description: Drive Mac's Nachtmarkt (the 3D Christmas-market website in site/) the way a visitor does and capture proof. Builds the site with analytics off, serves it on a private port, walks the stroll in headless Chromium, clicks stop-bar buttons and 3D items, and saves screenshots plus a result.json. Use to prove a change to the market, a stall, a reading surface, the bookshop, the ornament shop or plain.html works in the real page, not just in unit tests.
---

# Verify the Nachtmarkt

The app is a static Vite site (`site/`). The surface a visitor touches is one web page: a three.js market on a guided stroll (signpost, stop bar, things to click in 3D), plus `plain.html`, the text-only version. There is no server state, no login and no database. A verification run builds the site, serves it with `vite preview`, drives it with Playwright on software GL, and keeps the evidence.

Everything below is run from the repository root. The scripts live in `.claude/skills/verify/scripts/`.

## Launch

```sh
.claude/skills/verify/scripts/launch.sh          # port 4417
.claude/skills/verify/scripts/launch.sh 4418     # a second instance beside the first
```

It installs `site/node_modules` if missing, builds into `.verify/run-<port>/dist` with `VITE_GA_ID=` (so the run is not counted in Mac's Google Analytics: `site/.env.production` carries the real ID), refuses to serve a build that still has a GA ID, and starts `vite preview --strictPort` in the background. Ready when it prints `ready: http://localhost:<port>/website/`. The `/website/` base path is required; `/` is a 404.

The server answering is not the market being usable. The page is usable when `<html data-ready="true">`; `drive.mjs` waits for that (about 12 s for the lite market on SwiftShader, minutes for the full one).

Isolation: each port has its own build folder and PID file, so instances do not share anything. `tests/smoke.mjs` uses port 4317; keep verify runs off it. launch.sh refuses a port that something else owns.

## Doctor

```sh
.claude/skills/verify/scripts/doctor.sh [port]
```

Read-only. Checks that the preview PID launch.sh recorded is alive, the page answers, the served `main-*.js` is the one in this run's build (not someone else's server), the build is newer than `site/src`, `site/index.html` and `content/`, models and `plain.html` are served, the build has no GA ID, and Playwright imports. Exit 0 means worth driving. Run it first whenever anything looks off; a "source changed after the build" failure means relaunch (cleanup, then launch).

## Drive

```sh
node .claude/skills/verify/scripts/drive.mjs <journey> [--port 4417] [--quality lite|full] [--size 1280x760] [--reduced-motion] [--touch] [--real-time]
```

A journey is a small file in `.claude/skills/verify/journeys/<name>.mjs` exporting `default async (h) => {}`. Write a new one per change you need to prove, next to the existing ones. Shipped journeys:

- `glueh-pour`: signpost to the Glühwein stand, Pour from the stop bar, then a real mouse click on a mug in 3D.
- `plain`: the market page's skip link to `plain.html`, its section headings and outbound links.

The helper object `h`:

| Helper | What it does |
|---|---|
| `h.open(extra, file)` | Opens `/website/<file>?quality=<q>&snow=0<extra>`. `file` is `''` or `'plain.html'`. |
| `h.waitReady()` | Waits for `data-ready="true"`; throws with `#loadingText` if the market could not start. |
| `h.page` | The Playwright page. Use `page.click`, `page.keyboard.press`, `page.mouse` for visitor actions. |
| `h.tap(sel)` | Clicks a stop-bar button, unfolding `#stopFold` first on small screens. |
| `h.click3D(name)` | Real mouse move and click on a 3D item (`act_*`, `write_*`). Returns false if no clear pixel of it is on screen. |
| `h.pass(s)` | Lets `s` seconds of market time pass (see below). |
| `h.waitArrived(id)` | Passes time until the walk ends at stop `id` and the camera rests. |
| `h.waitAnnounce(re)` | Passes time until `#announce` (the live region carrying the vendor's note) matches. |
| `h.state(fn)` | Reads `window.__market` (read-only observation). |
| `h.check(what, ok, detail)` | Records a check. Any failing check fails the run. |
| `h.shot(label)` | Full-page JPEG (DOM bars and note included) into the evidence folder. |

Stable handles (from `site/index.html` and `site/src/ui/`):

- Signpost arms: `#signboard .sb-arm[data-place="<id>"]`, overview `#signboard .sb-home`. Place ids in stroll order: `glueh band bier books schmuck carousel ferris wurst`. Keys `1`–`8` follow the signpost's top-to-bottom order (`glueh bier wurst books band ferris carousel schmuck`); `0`/`Home`/`Escape` return to the overview.
- Stop bar: `#stopbar[data-place]`, `#hereName`, `#prevStop`, `#nextStop`, `#stopFold`; buttons in `#stopActs`: `[data-read="<surface>"]` (Read …), `[data-action="<key>"]`, `[data-view="<cabinet>"]`; goods `#goods [data-item="act_…"]`.
- Reading: `#readbar`, `#readTitle`, `#readPage`, `#readPrev`, `#readNext`, `#readFlip`, `#readClose`; the hidden copy for screen readers `#readCopy`.
- Top bar: `#play`, `#mute`, `#snow`, `#reset` (Overview), `#quality`, `#aboutOpen` (opens `dialog#about`). Toggles report state in `aria-pressed`.
- Page state on `<html>`: `data-ready`, `data-quality` (`lite`/`full`), `data-crowd`, `data-deferred`, `data-cabinet`.

**Time on software GL.** SwiftShader draws about one frame a second and each frame advances the market at most 0.1 s, so a 4 s walk takes minutes of wall time. `h.pass` therefore steps the page's own clock (`window.__market.advance`). That moves time only: it never clicks, walks or acts. On a machine with a real GPU (Mac's laptop) pass `--real-time` to wait on the wall clock instead.

## Evidence

Each run writes `.verify/evidence/<UTC time>-<journey>/`: numbered screenshots and `result.json` (every check with its detail, console errors, failed requests, HTTP errors, the log). drive.mjs exits 1 if any check fails or the page logged an error; a failed run also saves `NN-at-failure.jpg`. `.verify/` is git-ignored.

Proof standards:

- Act through the visitor's path: signpost arms, stop-bar buttons, keys, and `h.click3D` on 3D items. `window.__market.walkTo/act/read/clickItem` are test shortcuts: use them only to reach a precondition you are not proving, and say so. Reading `window.__market` to observe is fine.
- Capture the action and the result: a screenshot before and after, plus a check on what changed (`#announce` text, `#hereName`, `aria-pressed`, `reading()`, a count in the note).
- Check side effects alongside the picture: the note's counter, the plate's contents (`__market.handlers.plate()`), the open cabinet (`data-cabinet`), the stop (`__market.stop`).
- The lite market is the default because SwiftShader draws it in seconds. A change to full-only detail (shadows, streaming, the governor, full models) needs `--quality full` and patience (about 5 minutes to open).
- No mocks: the build is the production build minus the analytics ID.
- Audio cannot be heard here. Prove music by state (`#play[aria-pressed]`, `#nowplaying`), not by ear.

## Cleanup

```sh
.claude/skills/verify/scripts/cleanup.sh [port]
```

Kills the PID launch.sh recorded for that port (never by process name) and removes `.verify/run-<port>/`. It keeps `.verify/evidence/`. Run it after every run, failed ones too.

## Helpers

All in `.claude/skills/verify/scripts/`, all executable:

- `launch.sh [port]`: build (analytics off) and serve.
- `doctor.sh [port]`: read-only health check.
- `drive.mjs <journey> [flags]`: run a journey, save evidence.
- `cleanup.sh [port]`: stop and remove the instance, keep evidence.

Playwright: the cloud container has it preinstalled (drive.mjs falls back to `/opt/node22/lib/node_modules/playwright`). On a laptop without it: `cd site && npm i --no-save playwright && npx playwright install chromium`.

The broader regression suite is `site/tests/smoke.mjs` (`npm run build && node tests/smoke.mjs --only <phase>`); it builds into `site/dist` with the analytics ID and checks dozens of things at once. Use verify for proving one change; use smoke before publishing.

## Feature map

`features/README.md` indexes the user-facing features with a recipe each. Read the matching file before driving. A proof that covers one entry point when the map lists others is incomplete.
