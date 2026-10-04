// End-to-end smoke test (round 5): the built site served by `vite preview`, driven by Playwright on software GL.
// 0. unit checks (tests/unit.mjs)
// 1. stroll (full market, 1280 px): the home still, the first-load size, the architect's stroll and the carpenter's
//    signpost, no orbit (a drag turns the head at most 15°), a click on the signpost walking to a stop at walking pace,
//    the Riesenrad overview, the arrows and number keys, streaming full detail for the stop
// 1b. reading (lite, 1280 px): every section's words drawn in 3D on its board, coasters, menu, paper, card, sheet,
//    noticeboard and ticket, page turns, a coaster flip, a clicked book's words on its own pages, the hidden copy
//    and links, Escape and Enter
// 2. interact (lite, 960 px, reduced motion): every action from the stop bar, both rides, snow, the overview, the
//    keyboard, the on-screen signpost and a click in 3D
// 3. lite market auto-detected on a weak GPU (first-load size); 4. a phone with reduced motion and touch
// 5. plain.html and the credits; 6. every model missing: stand-ins, no errors; 7. recorded stems on the full market
// Fails on any console error, failed request or HTTP error.
// Usage: npm run build && node tests/smoke.mjs [--out ../review/round-5/engineer] [--port 4317] [--only unit,stroll,reading,interact,lite,phone,plain,missing,audio]
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-5/engineer'));
const PORT = +opt('--port', 4317);
const ONLY = opt('--only', 'all');
const READY_S = +opt('--ready', 300); // seconds a market may take to open (a loaded machine needs more)
const DIST = opt('--dist', null); // serve a copy of dist/, so a rebuild during a long run cannot pull files from under it
const run = (name) => ONLY === 'all' || ONLY.split(',').includes(name);
const BASE = `http://localhost:${PORT}/website/`;
mkdirSync(OUT, { recursive: true });

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort', ...(DIST ? ['--outDir', path.resolve(DIST)] : [])], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('preview did not start')), 30000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.on('exit', (c) => rej(new Error('preview exited ' + c)));
});

const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const errors = [];
const log = (...a) => console.log('·', ...a);
const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok, detail }); console.log(ok ? '  ok  ' : '  FAIL', name, detail ? `(${String(detail).slice(0, 140)})` : ''); };
const LONG = +opt('--long', 180) * 1000; // ms a click or wait may take (software GL on a busy machine: raise it)

async function openPage(url, { reducedMotion = 'no-preference', viewport = { width: 1280, height: 860 }, before = null, touch = false } = {}) {
  const ctx = await browser.newContext({ viewport, reducedMotion, deviceScaleFactor: 1, ...(touch ? { hasTouch: true, isMobile: true } : {}) });
  const page = await ctx.newPage();
  before?.(page);
  page.setDefaultTimeout(LONG);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`${url}: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push(`${url}: pageerror ${e.message}`));
  // a media element aborting its first range request to ask for another is normal streaming, not a failure
  page.on('requestfailed', (r) => /ERR_ABORTED/.test(r.failure()?.errorText || '') && /\.(mp3|ogg|m4a|opus|webm)$/.test(r.url()) ? null : errors.push(`${url}: request failed ${r.url()} ${r.failure()?.errorText}`));
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`${url}: HTTP ${r.status()} ${r.url()}`); });
  await page.goto(url, { waitUntil: 'load', timeout: LONG });
  return { ctx, page };
}

async function waitReady(page) {
  const t0 = Date.now();
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true' || /could not/.test(document.getElementById('loadingText')?.textContent || ''), null, { timeout: READY_S * 1000 });
  const ok = await page.evaluate(() => document.documentElement.dataset.ready === 'true');
  if (!ok) throw new Error('market did not start: ' + (await page.textContent('#loadingText')));
  log(`ready in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}

/** Wait for n rendered frames (software GL can be ~1 fps, so waiting on frames beats waiting on time). */
async function frames(page, n) {
  await page.evaluate((n) => new Promise((res) => { let k = 0; const f = () => (++k >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); }), n);
}
const note = (page) => page.evaluate(() => window.__market.note());
/** Wait until the camera stops moving (a flight or a panel's framing still easing on a slow software-GL page). */
async function stillCamera(page, tries = 30) {
  let prev = null;
  for (let i = 0; i < tries; i++) {
    const p = await page.evaluate(() => [...window.__market.camera.position.toArray(), ...window.__market.camera.quaternion.toArray()]);
    if (prev && p.every((v, k) => Math.abs(v - prev[k]) < 1e-4)) return true;
    prev = p;
    await frames(page, 2);
  }
  return false;
}
/** Everything requested before the market opened (the page marks 'market-ready' just before its first frame). */
const bytesAtReady = (page) => page.evaluate(() => {
  const t = performance.getEntriesByName('market-ready')[0]?.startTime ?? Infinity;
  const doc = performance.getEntriesByType('navigation')[0];
  return (doc?.encodedBodySize || 0) + performance.getEntriesByType('resource').filter((r) => r.startTime < t).reduce((a, r) => a + (r.encodedBodySize || r.decodedBodySize || 0), 0);
});
const waitNote = (page, re) => page.waitForFunction((src) => new RegExp(src).test(window.__market.note() || ''), re.source, { timeout: LONG }).then(() => true, () => false);
const state = (page, k) => page.evaluate((k) => window.__market[k], k);
/** A client point where a click would reach the named item (spiral search around its centre), or null. */
const aimAt = (page, name, via = name) => page.evaluate(([name, via]) => {
  // a point off the top of the window cannot be clicked: the whole stage must be in view first
  const st = document.getElementById('stage');
  const r0 = st.getBoundingClientRect();
  if (r0.top < 0 || r0.bottom > innerHeight) st.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  const m = window.__market, c = m.screenPoint(via);
  if (!c) return null;
  // prefer a point well inside the item (its neighbours 3 px away hit it too): a thin spine's edge pixel can
  // land on the next book once the pointer's hover lifts it
  // and only a point where the canvas itself is on top (not under the panel or the reading view)
  const canvas = st.querySelector('canvas');
  const onCanvas = (x, y) => document.elementFromPoint(x, y) === canvas;
  const inside = (x, y) => onCanvas(x, y) && [[0, 0], [3, 0], [-3, 0], [0, 3], [0, -3]].every(([dx, dy]) => m.itemAt(x + dx, y + dy) === name);
  for (const test of [inside, (x, y) => onCanvas(x, y) && m.itemAt(x, y) === name]) for (let r = 0; r <= 16; r += 2) for (let a = 0; a < 12; a++) {
    const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r;
    if (test(x, y)) return { x, y };
  }
  return null;
}, [name, via]);
const shot = async (page, name, sel, { keepScroll = false } = {}) => {
  const file = path.join(OUT, name);
  // hold the last rendered frame so the capture does not wait behind a slow software-GL frame
  if (!sel && !keepScroll) await page.evaluate(() => window.scrollTo(0, 0)); // clicking the place buttons scrolls the page
  // draw the current state first: with the clock held (advance() runs it without drawing) the canvas would still
  // show an older frame
  await page.mouse.move(1, 1).catch(() => {}); // off the market: no hover label left in the picture
  const frozen = await page.evaluate(() => { if (!window.__market?.freeze) return false; window.__market.renderFrame?.(); window.__market.freeze(true); return true; });
  // a frozen page still waits for the frames already queued on the GPU; on SwiftShader those can take minutes
  const SHOT = 900000;
  if (sel) await page.locator(sel).screenshot({ path: file, type: 'jpeg', quality: 86, timeout: SHOT });
  else await page.screenshot({ path: file, type: 'jpeg', quality: 86, timeout: SHOT });
  if (frozen) await page.evaluate(() => window.__market.freeze(false));
  log('screenshot', path.relative(process.cwd(), file));
};
try {
  if (run('unit')) {
    log('unit checks');
    const { execFileSync } = await import('node:child_process');
    let out = '', ok = true;
    try { out = execFileSync(process.execPath, ['tests/unit.mjs'], { encoding: 'utf8' }); } catch (e) { out = e.stdout || String(e); ok = false; }
    const lines = out.split('\n').filter((l) => /^\s+(ok|FAIL)/.test(l));
    for (const l of lines) check(l.replace(/^\s+(ok|FAIL)\s+/, 'unit: '), /^\s+ok/.test(l));
    if (!ok && !lines.some((l) => /FAIL/.test(l))) check('unit checks ran', false, out.slice(0, 200));
  }

  if (run('stroll')) {
    log('full market, 1280 px: the still, the signpost, a walk, the stops, streaming, no orbit and no side panel');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { viewport: { width: 1280, height: 760 } });
    const stillFirst = await page.evaluate(() => { const s = document.getElementById('still'); return !!s && /stills\/home\./.test(s.currentSrc || s.src) && !s.classList.contains('done'); });
    check('a still of the home view shows before the market is ready', stillFirst);
    await waitReady(page);
    const report = await page.evaluate(() => window.__market.report);
    const fullAtReady = await bytesAtReady(page);
    log(`full: ${(fullAtReady / 1e6).toFixed(2)} MB downloaded when the market opens`);
    check('full: the first load is smaller than round 4 (19.70 MB)', fullAtReady < 19.7e6, `${(fullAtReady / 1e6).toFixed(2)} MB`);
    check('full market chosen with ?quality=full', report.quality.lite === false);
    // it stays until the deferred part (town, rides, deco stalls) is in, at most four seconds of the page's own clock
    check('the still fades out once the market is drawn', await page.waitForFunction(() => document.getElementById('still').classList.contains('done'), null, { timeout: 120000 }).then(() => true, () => false));
    check('no side panel or reading aside on the 3D page', await page.evaluate(() => !document.querySelector('#panel, #reader, aside.panel, aside.reader')));
    check('the stroll runs on the architect\'s stops and legs', /stops and legs/.test(report.stroll.lane), report.stroll.lane);
    check('the stroll\'s loop is the architect\'s order', JSON.stringify(report.stroll.stops) === JSON.stringify(['glueh', 'ferris', 'wurst', 'band', 'bier', 'carousel', 'books']), JSON.stringify(report.stroll.stops));
    check('the signpost in the market is the carpenter\'s (act_sign_ boards)', /act_sign_/.test(report.stroll.signpost), report.stroll.signpost);
    check('the on-screen signpost has seven arms and an overview', (await page.locator('#signboard .sb-arm').count()) === 7 && (await page.locator('#signboard .sb-home').count()) === 1);
    check('streaming: the section stalls and the bandstand open at lite detail', await page.evaluate(() => { const s = window.__market.streaming().state; return ['gluehwein', 'bierstand', 'bratwurst', 'buecherstand', 'bandstand'].every((id) => s[id] === 'lite' || s[id] === 'loading' || s[id] === 'full'); }), JSON.stringify(await page.evaluate(() => window.__market.streaming().state)));
    // pass 2: the town ring is not in the first load; it comes with the rides and deco stalls just after the first frame
    check('streaming: the town ring comes just after the first frame, with the rides', await page.evaluate(() => window.__market.report.deferred.includes('town')), JSON.stringify(await page.evaluate(() => window.__market.report.deferred)));
    // the home view drifts by itself, but a drag only turns the head a little: no orbit
    await page.evaluate(() => window.__market.freeze(true));
    const c0 = await page.evaluate(() => window.__market.cam());
    const box = await page.locator('#stage canvas').boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.6);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.95, box.y + box.height * 0.6, { steps: 6 });
    await page.mouse.up();
    await page.evaluate(() => window.__market.advance(2));
    const c1 = await page.evaluate(() => window.__market.cam());
    check('no orbit: a long drag turns the head at most 15°, and the camera stays where it is', Math.abs(c1.look.yaw) <= 0.2619 && Math.hypot(c1.pos[0] - c0.pos[0], c1.pos[2] - c0.pos[2]) < 1.2, JSON.stringify({ c0: c0.pos, c1: c1.pos, look: c1.look }));
    await page.evaluate(() => window.__market.nudge(0, 5));
    await page.evaluate(() => window.__market.advance(2));
    const z = (await page.evaluate(() => window.__market.cam())).look.zoom;
    check('zoom stays in its small band', z >= 0.82 - 1e-6 && z <= 1.12 + 1e-6, String(z));
    await page.evaluate(() => window.__market.freeze(false));
    await page.mouse.move(box.x + box.width * 0.5, box.y - 40); // off the canvas: no hover label in the picture
    await page.evaluate(() => window.__market.settled());
    await shot(page, 'home_signpost.jpg');
    // a click on the signpost's Glühwein board walks there
    const sign = await page.evaluate(() => {
      const m = window.__market;
      const st = document.getElementById('stage'); if (st.getBoundingClientRect().top < 0) st.scrollIntoView({ block: 'nearest', behavior: 'instant' });
      const c = m.screenPoint('act_sign_gluehwein');
      if (!c) return null;
      for (let r = 0; r <= 24; r += 3) for (let a = 0; a < 12; a++) { const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r; const p = m.pickAt(x, y); if (p?.sign === 'glueh') return { x, y }; }
      return { miss: c, pick: m.pickAt(c.x, c.y) };
    });
    // the hover label of the signpost's arm nearest the right edge stays inside the canvas
    const right = await page.evaluate(() => {
      const m = window.__market;
      let best = null;
      for (const id of ['gluehwein', 'bratwurst', 'bierstand', 'buecherstand', 'bandstand', 'riesenrad', 'karussell']) {
        const c = m.screenPoint(`act_sign_${id}`);
        if (!c?.onScreen) continue;
        for (let r = 0; r <= 24; r += 3) for (let a = 0; a < 12; a++) { const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r; if (m.pickAt(x, y)?.sign && (!best || x > best.x)) best = { x, y }; }
      }
      return best;
    });
    if (right) {
      await page.mouse.move(right.x, right.y);
      await page.waitForFunction(() => { const t = document.querySelector('.overlay .tip'); return t && !t.hidden; }, null, { timeout: 30000 }).catch(() => {});
      const fit = await page.evaluate(() => { const t = document.querySelector('.overlay .tip'), c = document.querySelector('#stage canvas'); const a = t.getBoundingClientRect(), b = c.getBoundingClientRect(); return { tip: [a.left, a.top, a.right, a.bottom].map(Math.round), canvas: [b.left, b.top, b.right, b.bottom].map(Math.round), text: t.textContent, hidden: t.hidden }; });
      check('the signpost\'s hover label stays inside the canvas', !fit.hidden && fit.tip[0] >= fit.canvas[0] && fit.tip[2] <= fit.canvas[2] && fit.tip[1] >= fit.canvas[1], JSON.stringify(fit));
      await page.mouse.move(box.x + box.width * 0.5, box.y - 40);
    }
    // and wherever a board stands: the label of a hover at each edge and corner of the canvas stays inside it
    const edges = await page.evaluate(() => {
      const m = window.__market, o = document.querySelector('.overlay'), t = document.querySelector('.overlay .tip');
      const W = o.clientWidth, H = o.clientHeight, ob = o.getBoundingClientRect();
      const out = [];
      for (const [x, y] of [[W - 2, H / 2], [2, H / 2], [W - 2, 4], [2, 4], [W / 2, 3], [W - 2, H - 3]]) {
        m.tipAt(x, y, 'Riesenrad: walk to the Riesenrad · Big questions');
        const a = t.getBoundingClientRect();
        out.push({ at: [Math.round(x), Math.round(y)], inside: a.left >= ob.left - 0.5 && a.right <= ob.right + 0.5 && a.top >= ob.top - 0.5 && a.bottom <= ob.bottom + 0.5 });
      }
      m.tipAt(0, 0, null);
      return out;
    });
    check('the hover label stays inside the canvas at every edge and corner', edges.every((e) => e.inside), JSON.stringify(edges));
    if (sign?.x !== undefined) {
      await page.evaluate(() => window.__market.freeze(true));
      await page.mouse.click(sign.x, sign.y);
      await page.evaluate(() => window.__market.freeze(false));
    } else await page.click('#signboard .sb-arm[data-place="glueh"]');
    check('clicking the signpost\'s Glühwein board walks to the Glühwein stall', sign?.x !== undefined && (await page.evaluate(() => window.__market.stop)) === 'glueh', JSON.stringify(sign));
    // the walk: along the path at walking pace, with gentle ease
    await page.evaluate(() => window.__market.freeze(true));
    const w0 = await page.evaluate(() => window.__market.cam());
    check('the camera walks (not flies) to the stop', w0.mode === 'walk' && w0.progress && w0.progress.dur >= 2.2 && w0.progress.dur <= 12.01, JSON.stringify(w0.progress));
    const pace = w0.progress.length / w0.progress.dur;
    check('walking pace (about 3 m/s; never a dash)', pace < 3.5 || w0.progress.dur >= 11.99, `${pace.toFixed(2)} m/s over ${w0.progress.length.toFixed(1)} m`);
    await page.evaluate((d) => window.__market.advance(d * 0.45), w0.progress.dur);
    const mid = await page.evaluate(() => window.__market.cam());
    check('mid-stroll the camera is on its way, down at eye level and off the straight line', mid.moving && mid.pos[1] < w0.pos[1] - 1, JSON.stringify(mid.pos));
    const midShot = await page.evaluate(() => window.__market.snapshot());
    writeFileSync(path.join(OUT, 'stroll_mid.jpg'), Buffer.from(midShot.split(',')[1], 'base64'));
    await page.evaluate(() => { const m = window.__market; for (let i = 0; i < 40 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    const at = await page.evaluate(() => ({ arrived: window.__market.arrived, cam: window.__market.cam(), bar: !document.getElementById('stopbar').hidden, here: document.getElementById('hereName').textContent }));
    check('arrived at the Glühwein stop, with its bar of things to do', at.arrived && at.bar && /Gl.hwein/.test(at.here), JSON.stringify(at).slice(0, 200));
    await page.evaluate(() => window.__market.nudge(1, 0));
    await page.evaluate(() => window.__market.advance(2));
    check('at a stop the head turns at most 15°', Math.abs((await page.evaluate(() => window.__market.cam())).look.yaw) <= 0.2619);
    // the stall in view streams in at full detail
    await page.evaluate(() => window.__market.streamReady());
    await page.waitForFunction(() => window.__market.streaming().state.gluehwein === 'full', null, { timeout: LONG }).catch(() => {});
    const sr = await page.evaluate(() => window.__market.streaming());
    check('streaming: the stall at the stop comes in at full detail', sr.state.gluehwein === 'full', JSON.stringify(sr.state));
    check('streaming: the swap kept every action\'s nodes (no graft errors)', !sr.report.some((r) => /fail|error/i.test(JSON.stringify(r))), JSON.stringify(sr.report).slice(0, 300));
    // the arrows walk on along the loop: the Riesenrad is next, and its stop is the overview from the top gondola
    await page.focus('#stage canvas');
    await page.keyboard.press('ArrowRight');
    await page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    const fr = await page.evaluate(() => ({ stop: window.__market.stop, cam: window.__market.cam() }));
    check('→ walks on to the next stop (the Riesenrad)', fr.stop === 'ferris');
    check('the Riesenrad stop is the overview, high on the wheel', fr.cam.pos[1] > 14, JSON.stringify(fr.cam.pos));
    await page.evaluate(() => window.__market.freeze(false));
    await shot(page, 'stop_riesenrad_overview.jpg', '#stage');
    await page.evaluate(() => window.__market.freeze(true));
    await page.keyboard.press('ArrowLeft');
    await page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    check('← walks back to the stop before', (await page.evaluate(() => window.__market.stop)) === 'glueh');
    await page.keyboard.press('4');
    check('key 4 walks to the Bücherstand', (await page.evaluate(() => window.__market.stop)) === 'books');
    await page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    await page.waitForFunction(() => window.__market.streaming().state.buecherstand === 'full', null, { timeout: LONG }).catch(() => {});
    check('streaming: walking to a stall brings it in at full detail', (await page.evaluate(() => window.__market.streaming().state.buecherstand)) === 'full');
    await page.keyboard.press('0');
    await page.evaluate(() => window.__market.advance(3));
    check('0 goes back to the overview of the square', (await page.evaluate(() => window.__market.stop)) === null && (await page.evaluate(() => window.__market.cam().mode)) === 'home');
    await page.evaluate(() => window.__market.freeze(false));
    await ctx.close();
  }

  if (run('reading')) {
    // ---------- reading: every section's words are written in the market ----------
    // (the lite market at 1280 px: the same surfaces and words, and software GL draws it in seconds, not minutes)
    log('reading on the writing surfaces (lite market, 1280 px)');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0`, { viewport: { width: 1280, height: 760 } });
    await waitReady(page);
    // the rides (their noticeboard and ticket) come just after the first frame; the open book is fetched ahead
    await page.evaluate(() => window.__market.settled());
    await page.evaluate(() => window.__market.handlers.prefetchBook?.());
    await page.evaluate(() => window.__market.freeze(true));
    const surf = await page.evaluate(() => window.__market.surfaces());
    log(`writing surfaces on the models' own write_ nodes: ${surf.filter((x) => x.fromModel).map((x) => x.id).join(' ')}; stand-ins: ${surf.filter((x) => !x.fromModel).map((x) => x.id).join(' ') || 'none'}`);
    check('the carpenter\'s, vendor\'s and ride builder\'s write_ props carry the words where they exist (Glühwein board, vom Fass board, menu, Marktblatt, sheet music, noticeboard, ticket)', ['glueh.board', 'bier.vomfass', 'wurst.menu', 'wurst.paper', 'band.sheet', 'ferris.notice', 'carousel.ticket'].every((id) => surf.find((x) => x.id === id)?.fromModel), JSON.stringify(surf));
    const pieces = await page.evaluate(() => window.__market.pieces().filter((p) => !/placard/.test(p.id)));
    const want = ['glueh.board', 'bier.vomfass', 'bier.coaster_0', 'wurst.menu', 'wurst.paper', 'books.card', 'band.sheet', 'ferris.notice', 'carousel.ticket'];
    check('a writing surface for each section (board, coasters, menu, paper, card, sheet, noticeboard, ticket)', want.every((id) => pieces.some((p) => p.id === id)), pieces.map((p) => p.id).join(' '));
    const settle = () => page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(1); });
    for (const id of want) {
      await page.evaluate((id) => window.__market.read(id), id);
      await settle();
      await page.waitForFunction((id) => window.__market.reading().id === id && window.__market.textOn(id).length > 10, id, { timeout: LONG }).catch(() => {});
      await page.evaluate(() => window.__market.advance(0.8)); // the words fade in once drawn
      const r = await page.evaluate((id) => ({ reading: window.__market.reading(), text: window.__market.textOn(id), copy: window.__market.readCopy(), bar: !document.getElementById('readbar').hidden }), id);
      check(`${id}: the words are drawn on it in 3D, the camera close in front`, r.reading.id === id && r.text.replace(/\s+/g, '').length > 10, `${r.text.slice(0, 90)}`);
      check(`${id}: a visually hidden copy for screen readers, and the page bar`, r.copy.text.length > 10 && r.bar, r.copy.text.slice(0, 60));
      const file = `read_${id.replace('.', '_')}.jpg`;
      const url = await page.evaluate(() => window.__market.snapshot());
      writeFileSync(path.join(OUT, file), Buffer.from(url.split(',')[1], 'base64'));
      if (id === 'bier.coaster_0') {
        const before = await page.evaluate(() => window.__market.reading());
        await page.keyboard.press('ArrowRight');
        await settle();
        await page.evaluate(() => window.__market.advance(1.5));
        const after = await page.evaluate(() => window.__market.reading());
        check('a Bierdeckel flips over to its back', before.face === 'front' && after.face === 'back', JSON.stringify([before, after]));
        await page.waitForFunction(() => Object.keys(window.__market.coasterPrint(0)?.reach || {}).length === 2, null, { timeout: 60000 }).catch(() => {});
        const cp = await page.evaluate(() => window.__market.coasterPrint(0));
        if (cp?.fromModel) {
          check('a Bierdeckel\'s words are printed on its own round face: no card under them (front in the print, back a round card face)', cp.frontPrinted && cp.backCardHidden && cp.roundBack, JSON.stringify(cp));
          check('a Bierdeckel\'s words stay inside its edge, front and back', cp.reach.front > 0 && cp.reach.front < 0.85 && cp.reach.back > 0 && cp.reach.back < 0.97, JSON.stringify(cp.reach));
        }
        const u2 = await page.evaluate(() => window.__market.snapshot());
        writeFileSync(path.join(OUT, 'read_bier_coaster_back.jpg'), Buffer.from(u2.split(',')[1], 'base64'));
      }
      if (id === 'bier.vomfass') check('the projects board carries clickable links (GitHub)', r.copy.links.some((h) => /github\.com/.test(h)), r.copy.links.join(' '));
      if (r.reading.views > 1 && id !== 'bier.coaster_0') {
        const t0 = r.text;
        await page.keyboard.press('ArrowRight');
        await settle();
        await page.waitForFunction(([id, t0]) => window.__market.textOn(id) !== t0 && window.__market.textOn(id).length > 10, [id, t0], { timeout: 60000 }).catch(() => {});
        await page.evaluate(() => window.__market.advance(0.8));
        const r2 = await page.evaluate((id) => ({ view: window.__market.reading().view, text: window.__market.textOn(id) }), id);
        check(`${id}: long text turns the page instead of scrolling`, r2.view === 1 && r2.text !== t0, `${r2.view}: ${r2.text.slice(0, 60)}`);
      }
      await page.keyboard.press('Escape');
      await settle();
      check(`${id}: Escape stops reading and steps back to the stop`, !(await page.evaluate(() => window.__market.reading().open)));
    }
    // a book: pulled from the shelf, opened, its words on its pages
    await page.evaluate(() => window.__market.walkTo('books'));
    await settle();
    await page.evaluate(() => window.__market.handlers.pickBook());
    // the book comes off the shelf, flies to the counter and opens (each stage starts when the last has ended, so
    // the clock is advanced in steps, letting the page run in between)
    for (let i = 0; i < 40 && (await page.evaluate(() => window.__market.openedBook()?.state)) !== 'open'; i++) await page.evaluate(() => window.__market.advance(0.5));
    await settle();
    await page.waitForFunction(() => window.__market.reading().id === 'books.book' && window.__market.textOn('books.book').length > 40, null, { timeout: LONG }).catch(() => {});
    await page.evaluate(() => window.__market.advance(0.8));
    const bk = await page.evaluate(() => ({ book: window.__market.openedBook(), reading: window.__market.reading(), text: window.__market.textOn('books.book'), print: window.__market.bookPrint() }));
    check('the book that opens is the vendor\'s hardback (book_open.glb), its pages printed on its paper', bk.book?.model === 'book_open.glb' && bk.print?.material === 'vendor_print', JSON.stringify([bk.book?.model, bk.print]));
    check('a clicked book opens with its words on its own 3D pages', bk.book?.state === 'open' && bk.reading.id === 'books.book' && !!bk.book.title && bk.text.includes(bk.book.title.split(':')[0].slice(0, 12)), `${JSON.stringify(bk.book)} ${bk.text.slice(0, 120)}`);
    { const u = await page.evaluate(() => window.__market.snapshot()); writeFileSync(path.join(OUT, 'read_book.jpg'), Buffer.from(u.split(',')[1], 'base64')); }
    await page.waitForFunction(() => window.__market.reading().views > 1, null, { timeout: 30000 }).catch(() => {});
    if ((await page.evaluate(() => window.__market.reading().views)) > 1) {
      const t0 = bk.text;
      await page.keyboard.press('ArrowRight');
      await settle();
      await page.waitForFunction((t0) => window.__market.textOn('books.book') !== t0 && window.__market.textOn('books.book').length > 40, t0, { timeout: 60000 }).catch(() => {});
      await page.evaluate(() => window.__market.advance(0.8));
      const t1 = await page.evaluate(() => window.__market.textOn('books.book'));
      check('the book\'s page turns (a leaf turns over)', t1 !== t0, t1.slice(0, 80));
      const u = await page.evaluate(() => window.__market.snapshot()); writeFileSync(path.join(OUT, 'read_book_page2.jpg'), Buffer.from(u.split(',')[1], 'base64'));
    }
    await page.keyboard.press('Escape');
    await settle();
    check('Escape closes the book and puts it back', (await page.evaluate(() => window.__market.openedBook())) === null);
    // Enter at a stop reads what is written there
    await page.evaluate(() => window.__market.walkTo('carousel'));
    await settle();
    await page.focus('#stage canvas');
    await page.keyboard.press('Enter');
    await settle();
    check('Enter at a stop reads its main piece (the Karussell ticket)', (await page.evaluate(() => window.__market.reading().id)) === 'carousel.ticket');
    await page.keyboard.press('Escape');
    await settle();
    await page.evaluate(() => window.__market.freeze(false));
    await ctx.close();
  }

  if (run('interact')) {
    log('every action, both rides, snow, the overview, the keyboard and a click in 3D (lite market, small viewport)');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0`, { viewport: { width: 960, height: 640 }, reducedMotion: 'reduce' });
    await waitReady(page);
    await page.waitForFunction(() => document.documentElement.dataset.crowd === 'ready', null, { timeout: LONG }).catch(() => {});
    check('the crowd streams in after the first frame', (await page.evaluate(() => window.__market.crowd().people)) > 10);
    const go = async (id) => { await page.evaluate((id) => window.__market.walkTo(id), id); await page.evaluate(() => window.__market.advance(1)); };
    const act = async (id, k) => { await page.evaluate(([id, k]) => window.__market.act(id, k), [id, k]); };
    const noteNow = () => page.evaluate(() => window.__market.note());
    const waitN = (re, s = 20) => page.evaluate(([src, s]) => { const m = window.__market; for (let t = 0; t < s; t += 0.5) { if (new RegExp(src).test(m.note())) return true; m.advance(0.5); } return new RegExp(src).test(m.note()); }, [re.source, s]);
    await page.click('#signboard .sb-arm[data-place="glueh"]');
    await page.evaluate(() => window.__market.advance(1));
    check('the on-screen signpost walks to the Glühwein stall', (await page.evaluate(() => window.__market.stop)) === 'glueh' && (await page.evaluate(() => window.__market.arrived)));
    check('the stop bar offers the actions as buttons', (await page.locator('#stopActs [data-action="pour"]').count()) === 1);
    await page.click('#stopActs [data-action="pour"]');
    check('pour a mug (the ladle fills one of the stall\'s own mugs)', await waitN(/poured tonight: 1/), await noteNow());
    await act('glueh', 'prost');
    // the first voice answers at once, the rest a moment apart (timers, not frames): give them a few seconds
    let bubbles = 0;
    for (let i = 0; i < 6 && !bubbles; i++) { await page.evaluate(() => window.__market.advance(0.5)); bubbles = await page.locator('.bubble').count(); if (!bubbles) await page.waitForTimeout(500); }
    check('Prost: the crowd raises a glass', bubbles > 0, `${bubbles} speaking`);
    await go('bier');
    await act('bier', 'pint');
    // (reduced motion pours at once, so the note may already say the pint is pulled)
    check('pull a pint (starts)', /Pouring|pulled tonight: 1/.test(await noteNow()), await noteNow());
    check('pull a pint (finishes)', await waitN(/pulled tonight: 1/, 30), await noteNow());
    await go('wurst');
    await act('wurst', 'turn');
    check('turn the sausages', /Turned|flare|Almost/.test(await noteNow()), await noteNow());
    await act('wurst', 'bun');
    check('a sausage in a bun', /Brötchen/.test(await noteNow()), await noteNow());
    check('a sausage in a bun: one sits in a roll, with mustard', (await page.evaluate(() => window.__market.handlers.bunCount())) === 1);
    // a click in 3D on one sausage
    const aim = await aimAt(page, 'act_sausage_2');
    if (aim) {
      const q0 = (await page.evaluate(() => window.__market.item('act_sausage_2'))).quaternion;
      await page.mouse.click(aim.x, aim.y);
      await page.evaluate(() => window.__market.advance(1.5));
      const q1 = (await page.evaluate(() => window.__market.item('act_sausage_2'))).quaternion;
      check('clicking one sausage in 3D turns that sausage (its node rotates)', q0.some((v, i) => Math.abs(v - q1[i]) > 0.05), `${q0} -> ${q1}`);
    } else check('clicking one sausage in 3D turns that sausage (its node rotates)', false, 'no clear pixel on act_sausage_2');
    await go('books');
    await act('books', 'book');
    await page.evaluate(() => window.__market.advance(3));
    const ob = await page.evaluate(() => window.__market.openedBook());
    check('pull a book: the bookseller picks one and it opens', !!ob && !!ob.title, JSON.stringify(ob));
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.__market.advance(2));
    await go('band');
    check('lite: the player buttons say they move the spotlight', /Spotlight/.test(await page.textContent('#stopActs [data-action="sax"]')));
    await page.click('#stopActs [data-action="sax"]');
    check('feature a band member', /sax/i.test(await noteNow()), await noteNow());
    await page.click('#stopActs [data-action="whole"]');
    await page.click('#stopActs [data-play]');
    await page.waitForFunction(() => /Pause|could not/.test(document.getElementById('play').textContent), null, { timeout: LONG });
    check('the band plays', /Pause/.test(await page.textContent('#play')), await page.textContent('#nowplaying'));
    await page.click('#stopActs [data-action="drums"]');
    check('featuring while playing', /drums/i.test(await noteNow()));
    await page.click('#stopActs [data-play]');
    check('the band stops', /Play/.test(await page.textContent('#play')));
    const later = await page.evaluate(() => window.__market.settled());
    check('lite: rides and deco stalls arrive after the first frame', later.deferred >= 2, JSON.stringify(later));
    await go('ferris');
    await act('ferris', 'ride');
    check('Riesenrad ride', (await state(page, 'riding')) === 'ferris');
    const rise = await page.evaluate(() => { const m = window.__market; let t = 0; while (m.rideStage === 'rising' && t < 60) { m.advance(0.5); t += 0.5; } return { t, stage: m.rideStage, cam: m.camera.position.y }; });
    check('Riesenrad: the ride stops at the top for the view', rise.stage === 'top' && rise.cam > 14, JSON.stringify(rise));
    await shot(page, 'ride_riesenrad.jpg', '#stage');
    await act('ferris', 'off');
    check('get off the wheel', (await state(page, 'riding')) === null);
    await go('carousel');
    await act('carousel', 'ride');
    check('carousel ride', (await state(page, 'riding')) === 'carousel');
    await page.evaluate(() => window.__market.advance(4));
    await act('carousel', 'bell');
    await page.keyboard.press('Escape');
    check('Escape ends the ride', (await state(page, 'riding')) === null);
    await page.click('#snow');
    check('snow on', (await state(page, 'snow')) === true && (await page.getAttribute('#snow', 'aria-pressed')) === 'true');
    await page.click('#snow');
    check('snow off', (await state(page, 'snow')) === false);
    await page.click('#reset');
    await page.evaluate(() => window.__market.advance(2));
    check('Overview (reset) goes back to the view over the square', (await state(page, 'stop')) === null && (await page.evaluate(() => window.__market.cam().mode)) === 'home');
    // keyboard
    await page.focus('#stage canvas');
    await page.keyboard.press('3');
    await page.evaluate(() => window.__market.advance(1));
    check('key 3 walks to the Bratwurst stand', (await state(page, 'stop')) === 'wurst');
    await page.keyboard.press('ArrowRight');
    await page.evaluate(() => window.__market.advance(1));
    check('→ walks on along the loop (the bandstand after the Bratwurst)', (await state(page, 'stop')) === 'band');
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.__market.advance(1));
    check('Escape at a stop goes back to the overview', (await state(page, 'stop')) === null);
    await page.focus('#signboard .sb-arm[data-place="books"]');
    await page.keyboard.press('Enter');
    await page.evaluate(() => window.__market.advance(1));
    check('Enter on a signpost arm walks there', (await state(page, 'stop')) === 'books');
    await ctx.close();
  }

  if (run('lite')) {
    log('lite market, auto-detected');
    const { ctx, page } = await openPage(`${BASE}?snow=0`);
    await waitReady(page);
    const atReady = await bytesAtReady(page);
    const report = await page.evaluate(() => window.__market.report);
    log(`lite: ${(atReady / 1e6).toFixed(2)} MB downloaded when the market opens`);
    check('lite: the first load is smaller than round 4 (7.44 MB)', atReady < 7.44e6, `${(atReady / 1e6).toFixed(2)} MB`);
    check('lite market detected on a weak GPU', report.quality.lite === true, report.quality.reasons.join('; '));
    check('lite: no shadows', await page.evaluate(() => window.__market.renderer.shadowMap.enabled === false));
    check('lite: fewer lights', report.lights.realtime <= 4, JSON.stringify(report.lights));
    await frames(page, 4);
    await shot(page, 'home_lite_stage.jpg', '#stage');
    await ctx.close();
  }

  if (run('phone')) {
    log('phone, reduced motion, touch');
    const { ctx, page } = await openPage(`${BASE}?snow=0`, { reducedMotion: 'reduce', viewport: { width: 390, height: 844 }, touch: true });
    await waitReady(page);
    check('lite market on a phone-sized screen', (await page.evaluate(() => window.__market.report.quality.lite)) === true);
    const cam0 = await page.evaluate(() => window.__market.camera.position.toArray());
    await frames(page, 6);
    const cam1 = await page.evaluate(() => window.__market.camera.position.toArray());
    check('reduced motion: the home view holds still', cam0.every((v, i) => Math.abs(v - cam1[i]) < 1e-3));
    check('phone: the signpost folds into one button', await page.locator('#signboard .sb-toggle').isVisible());
    await page.tap('#signboard .sb-toggle');
    await page.tap('#signboard .sb-arm[data-place="wurst"]');
    await frames(page, 1);
    check('reduced motion: the walk is a cut', (await page.evaluate(() => window.__market.arrived)) && (await state(page, 'stop')) === 'wurst');
    await frames(page, 2);
    const tAim = await aimAt(page, 'act_sausage_5');
    if (tAim) {
      const q0 = (await page.evaluate(() => window.__market.item('act_sausage_5'))).quaternion;
      await page.touchscreen.tap(tAim.x, tAim.y);
      await frames(page, 2);
      const q1 = (await page.evaluate(() => window.__market.item('act_sausage_5'))).quaternion;
      check('phone: tapping a sausage turns it', q0.some((v, i) => Math.abs(v - q1[i]) > 0.05), `${q0} -> ${q1}`);
    } else check('phone: tapping a sausage turns it', false, 'no clear pixel on act_sausage_5');
    await page.evaluate(() => window.__market.read('wurst.menu'));
    await page.evaluate(() => window.__market.advance(1));
    await page.waitForFunction(() => window.__market.textOn('wurst.menu').length > 10, null, { timeout: LONG }).catch(() => {});
    check('phone: reading the menu board fills the screen with it', (await page.evaluate(() => window.__market.reading().id)) === 'wurst.menu');
    await shot(page, 'phone_reading_menu.jpg', null, { keepScroll: true });
    await ctx.close();
  }
  if (run('plain')) {
    log('plain.html');
    const { ctx, page } = await openPage(`${BASE}plain.html`);
    const n = await page.locator('main section').count();
    check('plain.html has all seven sections', n === 7, `${n} sections`);
    check('plain.html links back to the market', (await page.locator('a[href="./"]').count()) > 0);
    // the credit is the music writer's own line from manifest.json (license.credit), word for word
    const manifest = JSON.parse(readFileSync(new URL('../public/audio/manifest.json', import.meta.url), 'utf8'));
    const want = (manifest.license?.credit || manifest.license?.recording?.credit || '').replace(/\s+/g, ' ').trim();
    const credit = { test: (t) => !!want && t.replace(/\s+/g, ' ').includes(want) };
    check('plain.html credits the music (the manifest\'s credit line)', credit.test(await page.textContent('#credits')), await page.textContent('#credits'));
    check('plain.html lists every third-party asset with its source URL', (await page.locator('.credits-all a[href^="https://github.com/"]').count()) > 5);
    { const t = await page.textContent('#books');
      check('plain.html carries the books the 3D shelf features (they are on Mac\'s shelf), and not the unconfirmed list', /The Order of Time/.test(t) && /The Book of Why/.test(t) && !/On the shelf in the market/.test(t) && !/Gödel, Escher, Bach/.test(t), t.slice(0, 200)); }
    const cats = JSON.parse(readFileSync(path.resolve('../content/books/categories.json'), 'utf8')).categories.flatMap((c) => c.books);
    const libN = await page.locator('#books .library li').count();
    check('plain.html lists Mac\'s whole bookshelf (categories.json), with the writer\'s one-line summaries', libN === cats.length && (await page.locator('#books .library .one-line').count()) > 0, `${libN} of ${cats.length}`);
    const pagesN = await page.locator('#books article.bookpage').count();
    const withPage = cats.filter((b) => existsSync(path.resolve(`../content/books/${b.slug}.md`))).length;
    check('plain.html carries the same notes the reading view shows, one article per book', pagesN === withPage && (await page.locator('#book-the-order-of-time h5').first().textContent()) === 'In short', `${pagesN} of ${withPage}`);
    await shot(page, 'plain_html.jpg');
    await ctx.close();
    // no WebGL: the page shows every section as text in place of the market
    const { ctx: c3, page: p3 } = await openPage(`${BASE}?nowebgl`);
    await p3.waitForSelector('.plainfallback section', { timeout: 60000 }).catch(() => {});
    check('without WebGL the 3D page falls back to the text of all seven sections', (await p3.locator('.plainfallback section').count()) === 7);
    await c3.close();
    const { ctx: c2, page: p2 } = await openPage(`${BASE}?quality=lite`);
    check('the 3D page links to plain.html', (await p2.locator('a[href="plain.html"]').count()) > 0);
    check('the 3D page credits the music in its footer', credit.test(await p2.textContent('footer #credits')), await p2.textContent('footer #credits'));
    const named = (want.match(/CC BY(-SA)? \d\.\d|CC0/g) || []).length;
    check('the credit links every licence it names', named > 0 && (await p2.locator('#credits a[rel="license"]').count()) >= named, `${named} named`);
    check('the 3D page lists every third-party asset with its source URL', (await p2.locator('.credits-all a[href^="https://github.com/"]').count()) > 5);
    check('the canvas has an accessible name', !!(await p2.locator('canvas').getAttribute('aria-label')));
    await p2.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: LONG });
    await p2.click('#mute');
    check('mute covers the band and the stall sounds', await p2.evaluate(() => window.__market.muted()) && (await p2.getAttribute('#mute', 'aria-pressed')) === 'true');
    await p2.click('#mute');
    await c2.close();
  }

  if (run('missing')) {
    log('every model missing and layout.json ignored: the BUILD.md layout with labelled stand-ins');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0&missing=all&layout=builtin`, { viewport: { width: 960, height: 640 }, reducedMotion: 'reduce' });
    await waitReady(page);
    const report = await page.evaluate(() => window.__market.report);
    check('missing glbs: every place is a stand-in', report.models.every((m) => m.source === 'standin'), JSON.stringify(report.models.filter((m) => m.source !== 'standin')));
    check('missing layout.json: the BUILD.md layout', report.layout === 'BUILD.md fallback', report.layout);
    check('missing glbs are reported as bindings that did not resolve (nothing guessed)', report.bindings.length >= 10 && report.bindings.every((b) => /(is|are) not in site\/public\/models|nor .* is in site\/public\/models|no asset/.test(b.problem)), JSON.stringify(report.bindings.filter((b) => !/(is|are) not in site\/public\/models|nor .* is in site\/public\/models|no asset/.test(b.problem)).slice(0, 4)));
    await page.evaluate(() => window.__market.walkTo('glueh'));
    await page.evaluate(() => window.__market.advance(1));
    await page.click('#stopActs [data-action="pour"]');
    await page.evaluate(() => window.__market.advance(6));
    check('stand-ins keep the actions working', /poured tonight: 1/.test(await note(page)), await note(page));
    check('stand-ins keep the writing surfaces (the chalkboard is still read in 3D)', await page.evaluate(() => window.__market.read('glueh.board')) && (await page.evaluate(() => window.__market.pieces().length)) >= 9);
    await page.evaluate(() => window.__market.closeRead());
    await page.click('#reset');
    await frames(page, 3);
    await shot(page, 'missing_models_standins.jpg', '#stage');
    await ctx.close();
    const { ctx: c2, page: p2 } = await openPage(`${BASE}?quality=lite&snow=0&missing=stall_bier,ferris&perf`, { viewport: { width: 960, height: 640 } });
    await waitReady(p2);
    check('?perf shows the frame-time meter with its Tour button', await p2.locator('.perf button', { hasText: 'Tour' }).isVisible());
    await p2.evaluate(() => window.__market.settled());
    const r2 = await p2.evaluate(() => window.__market.report.models);
    check('two missing glbs: just those two are stand-ins', r2.filter((m) => m.source === 'standin').map((m) => m.id).sort().join() === 'bierstand,riesenrad', JSON.stringify(r2.filter((m) => m.source === 'standin')));
    await c2.close();
  }

  if (run('audio')) {
    log('recorded stems on the full market');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { viewport: { width: 800, height: 520 } });
    await waitReady(page);
    // This phase is about sound: hold the picture the whole time. On SwiftShader a full-market frame blocks
    // the main thread for tens of seconds, and the page would not answer. advance() still runs the clock.
    await page.evaluate(() => window.__market.freeze(true));
    await page.evaluate(() => window.__market.settled());
    const mode = (await state(page, 'audio')).mode;
    if (mode !== 'stems') log('no audio manifest yet; the generative band plays instead');
    await page.evaluate(() => window.__market.togglePlay()); // full quality: no click (see the shots phase)
    await page.waitForFunction(() => /Pause|could not/.test(document.getElementById('play').textContent), null, { timeout: LONG });
    const first = (await state(page, 'audio')).phase;
    check('play starts at once', /Pause/.test(await page.textContent('#play')), first);
    if (mode === 'stems') {
      check('the mix bridges the wait for the stems', first === 'mix' || first === 'stems', first);
      const ok = await page.waitForFunction(() => window.__market.audio.phase === 'stems', null, { timeout: 300000 }).then(() => true, () => false);
      check('the stems take over from the mix', ok, (await state(page, 'audio')).phase);
      await page.evaluate(() => window.__market.act('band', 'sax'));
      // the analysers feed the levels on each step; a ballad has quiet bars and a busy machine starves the audio
      // thread now and then, so the levels are sampled for up to half a minute of real time, the loudest kept
      let lv = {};
      for (let i = 0; i < 15; i++) {
        await page.evaluate(() => window.__market.advance(1.5));
        const now = (await state(page, 'audio')).levels;
        for (const [k, v] of Object.entries(now)) lv[k] = Math.max(lv[k] || 0, v);
        if (Object.values(lv).some((v) => v > 0.01)) break;
        await page.waitForTimeout(2000);
      }
      check('stem levels reach the stage', Object.values(lv).some((v) => v > 0.01), JSON.stringify(lv));
      // the road map: on the last pass the stems run on past loopEnd into the written ending
      const w0 = (await state(page, 'audio')).where;
      await page.evaluate(([p, n]) => window.__market.seekSong(p - 1.5, n), [w0.loopEnd, w0.passes]);
      await page.waitForTimeout(3500);
      const w1 = (await state(page, 'audio')).where;
      check('last pass: the stems play on into the out head instead of looping', w1.pos > w0.loopEnd && w1.pass === w0.passes, JSON.stringify(w1));
      await page.evaluate(([p]) => window.__market.seekSong(p - 1.5, 1), [w0.loopEnd]);
      await page.waitForTimeout(3500);
      const w2 = (await state(page, 'audio')).where;
      check('earlier passes: the loop goes round again', w2.pass === 2 && w2.pos < 60, JSON.stringify(w2));
      const altOk = await page.waitForFunction(() => window.__market.audio.alternatesReady, null, { timeout: 240000 }).then(() => true, () => false);
      await page.evaluate(() => window.__market.seekSong(120, 2));
      await page.waitForTimeout(1500);
      const w3 = (await state(page, 'audio')).where;
      check('pass 2 plays the second tenor chorus (alternate stems)', altOk && w3.alt === true, JSON.stringify(w3));
      await page.evaluate(() => window.__market.seekSong(120, 3));
      await page.waitForTimeout(1500);
      check('pass 3 is back on the main chorus', (await state(page, 'audio')).where.alt === false);
    }
    await page.evaluate(() => window.__market.togglePlay());
    check('the band stops (full)', (await state(page, 'audio')).phase === 'idle');
    await ctx.close();
  }
} catch (e) {
  errors.push('test crashed: ' + (e?.stack || e));
} finally {
  await browser.close();
  server.kill();
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (errors.length) console.log('Console errors:\n  ' + errors.join('\n  '));
else console.log('No console errors.');
process.exit(failed.length || errors.length ? 1 : 0);
