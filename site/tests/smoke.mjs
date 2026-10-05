// End-to-end smoke test (round 5, extended in round 8): the built site served by `vite preview`, driven by Playwright on software GL.
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
// 8. (round 8) deco stalls are scenery: not clickable, no close-up, never more than their lite file (in the stroll
//    phase); the Bücherstand cabinets on a 390 px phone (cabinet): tap, open, only its books pickable, covers at
//    least 44 px, arrows, a clear way back
// 9. (round 9) the ornament shop (schmuck): three moments and nothing else to click: the glass harmonica (mouse and
//    touch brushes, taps, the hint, the tune), the Schwibbogen (outside-in candles, the town's windows, the chord,
//    the wave of light, the view over the arch and back), the reflection dive (cube env, in, inside, Escape and a
//    tap), the sparkle (mirror, tinsel, pyramid, smoke); (moments) the same at their peaks on the full market, as
//    screenshots; the phone section runs the reduced-motion versions
// Fails on any console error, failed request or HTTP error.
// Usage: npm run build && node tests/smoke.mjs [--out ../review/round-5/engineer] [--port 4317] [--only unit,stroll,reading,interact,schmuck,moments,cabinet,lite,phone,plain,missing,audio]
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-9/engineer'));
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
const skipped = [];
/** A check whose contract the files on disk have moved past (a later round's set): logged, not counted. */
const skip = (name, why) => { skipped.push({ name, why }); console.log('  skip', name, `(${why})`); };
/** The Bratwurst's set on disk: the round-8 rows of clickable sausages, or the round-10 plate (BUILD.md, ADR 0004). */
const wurstSet = (page) => page.evaluate(() => { const c = window.__market.items(); return c['wurst:sausage'] ? 'sausages' : c['wurst:wurst'] ? 'plate' : 'none'; });
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

// a stop-bar button: open the folded bar first (a small screen at a busy stop folds its buttons away)
async function tapAct(page, sel) {
  if (await page.evaluate(() => document.getElementById('stopbar')?.classList.contains('folded'))) await page.click('#stopFold');
  await page.click(sel);
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
    check('full: the first load stays near 8 MB (round 9: under 9 MB; the deco stalls are their lite files, the rest streams in at the stops)', fullAtReady < 9e6, `${(fullAtReady / 1e6).toFixed(2)} MB`);
    check('full market chosen with ?quality=full', report.quality.lite === false);
    // it stays until the deferred part (town, rides, deco stalls) is in, at most four seconds of the page's own clock
    check('the still fades out once the market is drawn', await page.waitForFunction(() => document.getElementById('still').classList.contains('done'), null, { timeout: 120000 }).then(() => true, () => false));
    check('no side panel or reading aside on the 3D page', await page.evaluate(() => !document.querySelector('#panel, #reader, aside.panel, aside.reader')));
    check('the stroll runs on the architect\'s stops and legs', /stops and legs/.test(report.stroll.lane), report.stroll.lane);
    check('the stroll\'s loop is the architect\'s order', JSON.stringify(report.stroll.stops) === JSON.stringify(['glueh', 'band', 'bier', 'books', 'schmuck', 'carousel', 'ferris', 'wurst']), JSON.stringify(report.stroll.stops));
    check('the signpost in the market is the carpenter\'s (act_sign_ boards)', /act_sign_/.test(report.stroll.signpost), report.stroll.signpost);
    check('the on-screen signpost has eight arms (the ornament shop too) and an overview', (await page.locator('#signboard .sb-arm').count()) === 8 && (await page.locator('#signboard .sb-home').count()) === 1);
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
    // deco stalls are scenery (ADR 0004): their lite file only, even on the full market, and a click on one does nothing
    {
      const deco = await page.evaluate(() => {
        const m = window.__market;
        const models = m.report.models.filter((x) => x.kind === 'deco');
        const full = performance.getEntriesByType('resource').map((r) => r.name).filter((u) => /\/models\/(deco_|prop_deco_)[^/]*\.glb$/.test(u) && !/\.lite\.glb$/.test(u));
        return { ids: m.decos(), files: models.map((x) => x.file), full, streamed: m.decos().filter((id) => m.streaming().state[id] !== 'scenery') };
      });
      check('deco stalls: every one is in the market, at its lite file only (no full-detail download, nothing streams)', deco.ids.length >= 6 && deco.files.length === deco.ids.length && deco.files.every((f) => /\.lite\.glb$/.test(f || '')) && !deco.full.length && !deco.streamed.length, JSON.stringify(deco));
      const hit = await page.evaluate((ids) => {
        const m = window.__market;
        for (const id of ids) {
          const c = m.entryPoint(id);
          if (!c?.onScreen) continue;
          for (let r = 0; r <= 30; r += 5) for (let a = 0; a < 12; a++) {
            const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r;
            const raw = m.rawAt(x, y)[0];
            if (raw?.entry === id) return { id, x, y, pick: m.pickAt(x, y) };
          }
        }
        return null;
      }, deco.ids);
      if (hit) {
        await page.mouse.move(hit.x, hit.y);
        await page.evaluate(() => window.__market.advance(0.5));
        const tip = await page.evaluate(() => { const t = document.querySelector('.overlay .tip'); return t && !t.hidden ? t.textContent : null; });
        await page.mouse.click(hit.x, hit.y);
        await page.evaluate(() => window.__market.advance(2));
        const after = await page.evaluate(() => ({ stop: window.__market.stop, mode: window.__market.cam().mode, reading: window.__market.reading().open, note: window.__market.note() }));
        check(`deco stalls are not clickable: a click on ${hit.id} picks nothing, shows no label, and the view stays home (no close-up)`, !hit.pick && !tip && after.stop === null && after.mode === 'home' && !after.reading, JSON.stringify({ hit, tip, after }));
      } else check('deco stalls are not clickable (a deco stall in the home view to click on)', false, 'no deco stall pixel in view');
      check('no deco stops in the stroll and no deco fly-to', !report.stroll.stops.some((s) => /deco/.test(s)) && !(await page.evaluate(() => 'openDeco' in window.__market || 'decos' in (window.__market.handlers || {}))));
    }
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
      for (const id of ['gluehwein', 'bratwurst', 'bierstand', 'buecherstand', 'bandstand', 'riesenrad', 'karussell', 'schmuck']) {
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
    // the arrows walk on along the loop: the bandstand is next after the Glühwein stall
    await page.focus('#stage canvas');
    const walkOn = () => page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    await page.keyboard.press('ArrowRight');
    await walkOn();
    check('→ walks on to the next stop (the bandstand)', (await page.evaluate(() => window.__market.stop)) === 'band');
    await page.keyboard.press('ArrowLeft');
    await walkOn();
    check('← walks back to the stop before', (await page.evaluate(() => window.__market.stop)) === 'glueh');
    // the number keys follow the signpost's order: 6 is the Riesenrad, whose stop is the overview from the top gondola
    await page.keyboard.press('6');
    await walkOn();
    const fr = await page.evaluate(() => ({ stop: window.__market.stop, cam: window.__market.cam() }));
    check('key 6 walks to the Riesenrad', fr.stop === 'ferris');
    check('the Riesenrad stop is the overview, high on the wheel', fr.cam.pos[1] > 14, JSON.stringify(fr.cam.pos));
    await page.evaluate(() => window.__market.freeze(false));
    await shot(page, 'stop_riesenrad_overview.jpg', '#stage');
    await page.evaluate(() => window.__market.freeze(true));
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
      const backingName = { 'band.sheet': 'music', 'ferris.notice': 'questions_board', 'carousel.ticket': 'contact' }[id];
      if (backingName) {
        const b = await page.evaluate((n) => window.__market.backing(n), backingName);
        if (b.card) check(`${id}: the sheet's card_ backing brightens with its write_ quad (no lighter inset)`, b.same && b.glow > 0.1, JSON.stringify(b));
      }
      if (id === 'bier.vomfass') {
        // the links Mac keeps in content/projects.md (round 9: ProtoCol and a YouTube playlist; GitHub was taken out)
        let want = [];
        try { want = [...readFileSync(path.resolve('../content/projects.md'), 'utf8').matchAll(/\]\((https?:[^)\s]+)\)/g)].map((m) => m[1].replace(/\/$/, '')); } catch { /* no content: any link will do */ }
        const have = r.copy.links.map((h) => h.replace(/\/$/, ''));
        check('the projects board carries the clickable links in content/projects.md', want.length ? want.every((u) => have.includes(u)) : have.length > 0, JSON.stringify({ want, have }));
      }
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
    // a gondola's placard: with a question on it, the wheel brings that gondola down and it is read where it hangs;
    // with none written yet (a production build before Mac confirms them) it opens the noticeboard
    {
      const pl = await page.evaluate(() => window.__market.pieces().find((p) => p.id === 'ferris.placard_0') || null);
      if (pl) {
        await page.evaluate(() => window.__market.walkTo('ferris'));
        await settle();
        // the wheel parks going forward, the way it turns, never backwards (angles sampled as it comes down)
        const asked = await page.evaluate(() => {
          const m = window.__market; m.advance(20); m.readSurface('ferris.placard_0');
          const w0 = m.wheel(), seen = [w0?.angle];
          for (let i = 0; i < 48 && !m.wheel()?.parked; i++) { m.advance(0.25); seen.push(m.wheel().angle); }
          const back = seen.slice(1).filter((a, i) => (a - seen[i]) * (w0?.dir || 1) < -1e-4).length;
          return { ...m.wheel(), seen: seen.length, back };
        });
        // (a production build's placards carry no question yet and open the noticeboard: park the wheel directly)
        const parkRun = asked?.parking ? asked : await page.evaluate(() => {
          const m = window.__market; m.advance(7); const w0 = m.wheel(), T = m.parkWheel(true), seen = [w0.angle];
          for (let i = 0; i < 48 && !m.wheel().parked; i++) { m.advance(0.25); seen.push(m.wheel().angle); }
          const back = seen.slice(1).filter((a, i) => (a - seen[i]) * w0.dir < -1e-4).length;
          const out = { ...m.wheel(), T, from: w0.angle, seen: seen.length, back }; m.parkWheel(false); return out;
        });
        check('the wheel parks forward, the way it turns, never backwards, and eases to a stop on a whole turn', parkRun.back === 0 && parkRun.parked && Math.abs(parkRun.angle / (2 * Math.PI) - Math.round(parkRun.angle / (2 * Math.PI))) < 1e-3, JSON.stringify(parkRun));
        await page.waitForFunction(() => window.__market.reading().open, null, { timeout: 60000 }).catch(() => {});
        await settle();
        const r = await page.evaluate(() => ({ reading: window.__market.reading(), wheel: window.__market.wheel(), cam: window.__market.cam() }));
        const hasQuestion = pl.title && pl.title !== 'Big questions';
        if (hasQuestion && asked?.parking) {
          check('a gondola\'s placard: the wheel parks that gondola at the bottom and the placard is read where it hangs', r.reading.id === 'ferris.placard_0' && r.wheel.parked && r.cam.pos[1] < 6, JSON.stringify([r.reading.id, r.wheel, r.cam.pos]));
          const u = await page.evaluate(() => window.__market.snapshot()); writeFileSync(path.join(OUT, 'read_ferris_placard.jpg'), Buffer.from(u.split(',')[1], 'base64'));
        } else check('a gondola\'s placard with no question written yet opens the noticeboard', r.reading.id === 'ferris.notice', JSON.stringify([pl.title, r.reading.id, asked]));
        await page.keyboard.press('Escape');
        await settle();
        check('after reading, the wheel turns again', !(await page.evaluate(() => window.__market.wheel()?.parking)));
      }
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
    await tapAct(page, '#stopActs [data-action="pour"]');
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
    // the Bratwurst (round 10, ADR 0004 revision): the grill's sausages turn from the button (scenery, not one by one),
    // and four kinds, a roll, three sauces, the curry tin and the paper plate are the clickable set
    check('the Bratwurst has the round-10 plate set (no clickable sausage rows left)', (await wurstSet(page)) === 'plate', await wurstSet(page));
    check('the Bratwurst\'s buttons: Turn the sausages, One in a bun, Mix me a plate', (await page.locator('#stopActs [data-action="turn"]').count()) === 1 && (await page.locator('#stopActs [data-action="bun"]').count()) === 1 && (await page.locator('#stopActs [data-action="plate"]').count()) === 1);
    const g0 = await page.evaluate(() => window.__market.handlers.grill());
    await tapAct(page, '#stopActs [data-action="turn"]');
    check('turn the sausages', /Turned|flare|Almost/.test(await noteNow()), await noteNow());
    await page.evaluate(() => window.__market.advance(1.5));
    const g1 = await page.evaluate(() => window.__market.handlers.grill());
    check('turn the sausages: every sausage on the grate turns over (the vendor\'s merged grill cut into its sausages)', !!g0 && g0.n >= 6 && g1.turns.every((n) => n === 1) && !g1.busy && g1.angles.every((a) => Math.abs(a - Math.PI) < 0.01), JSON.stringify({ g0: g0 && g0.n, g1 }));
    check('the grill\'s sausages are not clickable one by one', await page.evaluate(() => { const m = window.__market; let o = null; m.scene.traverse((x) => { if (!o && /^grill_sausage_\d/.test(x.name) && x.isMesh) o = x; }); return !!o && !m.items()['wurst:sausage']; }));
    const plateNow = () => page.evaluate(() => window.__market.handlers.plate());
    const settlePlate = () => page.evaluate(() => { const m = window.__market; for (let t = 0; t < 20 && m.handlers.plate().busy; t += 0.5) m.advance(0.5); m.advance(0.5); return m.handlers.plate(); });
    await act('wurst', 'bun');
    check('a sausage in a bun', /Brötchen/.test(await noteNow()), await noteNow());
    const pb = await settlePlate();
    check('a sausage in a bun: a roll goes on the plate, a Thüringer into it, with Senf', pb.food.join() === 'roll,thueringer' && pb.filled.join() === 'thueringer' && pb.sauces.join() === 'senf', JSON.stringify(pb));
    // a click in 3D on a kind: a fresh one arcs onto the plate
    await page.evaluate(() => { window.__market.handlers.clearPlate(); });
    const pc = await settlePlate();
    check('tapping the plate hands it over (Guten Appetit) and a fresh, empty plate is set out', pc.food.length === 0 && pc.sauces.length === 0 && pc.served === 1 && /Guten Appetit/.test(await noteNow()), JSON.stringify(pc));
    const kAim = await aimAt(page, 'act_wurst_krakauer');
    if (kAim) {
      const k0 = (await page.evaluate(() => window.__market.item('act_wurst_krakauer'))).position;
      await page.mouse.click(kAim.x, kAim.y);
      const pk = await settlePlate();
      const k1 = (await page.evaluate(() => window.__market.item('act_wurst_krakauer'))).position;
      check('clicking a Krakauer in 3D puts a fresh one on the plate (the one on the board stays)', pk.food.join() === 'krakauer' && k0.every((v, i) => Math.abs(v - k1[i]) < 0.002), JSON.stringify({ pk, k0, k1 }));
    } else check('clicking a Krakauer in 3D puts a fresh one on the plate (the one on the board stays)', false, 'no clear pixel on act_wurst_krakauer');
    await page.evaluate(() => { const m = window.__market; m.clickItem('act_wurst_nuernberger'); m.clickItem('act_sauce_ketchup'); m.clickItem('act_sauce_curry'); m.clickItem('act_shaker_curry'); });
    const ps = await settlePlate();
    check('sauces and curry: each bottle squeezes its own squiggle over the plate, the tin dusts curry powder', ps.food.join() === 'krakauer,nuernberger' && ps.sauces.join() === 'ketchup,curry' && ps.dust > 50, JSON.stringify(ps));
    check('the sauce is a glossy line draped over the food (a tube on the plate, drawn in as it is piped)', await page.evaluate(() => { const m = window.__market; let n = 0, ok = true; m.scene.traverse((o) => { if (/^item_sauce_/.test(o.name) && o.isMesh) { n++; o.geometry.computeBoundingBox(); const b = o.geometry.boundingBox; ok = ok && b.max.x - b.min.x > 0.04 && o.geometry.drawRange.count > 100; } }); return n === 2 && ok; }));
    await page.evaluate(() => { const m = window.__market; for (const k of ['act_wurst_curry', 'act_roll', 'act_wurst_thueringer']) m.clickItem(k); });
    const pf = await settlePlate();
    check('the plate holds four at most (a fifth gets "the plate is full")', pf.food.length === 4 && /full/.test(await noteNow()), JSON.stringify({ food: pf.food, note: await noteNow() }));
    const plAim = await aimAt(page, 'act_plate');
    if (plAim) { await page.mouse.click(plAim.x, plAim.y); } else await page.evaluate(() => window.__market.clickItem('act_plate'));
    const pe = await settlePlate();
    check('clicking the plate clears it: Guten Appetit', pe.food.length === 0 && pe.sauces.length === 0 && pe.dust === 0 && pe.served === 2 && /Guten Appetit/.test(await noteNow()), JSON.stringify({ pe, by: plAim ? '3D click' : 'clickItem', note: await noteNow() }));
    await act('wurst', 'plate');
    const pm = await settlePlate();
    check('mix me a plate: the vendor puts a kind on and a sauce over it', pm.food.length === 1 && pm.sauces.length + (pm.dust ? 1 : 0) === 1, JSON.stringify(pm));
    await shot(page, 'stop_bratwurst_plate.jpg', null, { keepScroll: true });
    await go('books');
    await act('books', 'book');
    await page.evaluate(() => window.__market.advance(3));
    const ob = await page.evaluate(() => window.__market.openedBook());
    check('pull a book: the bookseller picks one and it opens', !!ob && !!ob.title, JSON.stringify(ob));
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.__market.advance(2));
    await go('band');
    check('lite: the player buttons say they move the spotlight', /Spotlight/.test(await page.textContent('#stopActs [data-action="sax"]')));
    await tapAct(page, '#stopActs [data-action="sax"]');
    check('feature a band member', /sax/i.test(await noteNow()), await noteNow());
    await tapAct(page, '#stopActs [data-action="whole"]');
    await tapAct(page, '#stopActs [data-play]');
    await page.waitForFunction(() => /Pause|could not/.test(document.getElementById('play').textContent), null, { timeout: LONG });
    check('the band plays', /Pause/.test(await page.textContent('#play')), await page.textContent('#nowplaying'));
    await tapAct(page, '#stopActs [data-action="drums"]');
    check('featuring while playing', /drums/i.test(await noteNow()));
    await tapAct(page, '#stopActs [data-play]');
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
    check('→ walks on along the loop (the Bratwurst is the last stop, so round to the Glühwein stall)', (await state(page, 'stop')) === 'glueh');
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.__market.advance(1));
    check('Escape at a stop goes back to the overview', (await state(page, 'stop')) === null);
    await page.focus('#signboard .sb-arm[data-place="books"]');
    await page.keyboard.press('Enter');
    await page.evaluate(() => window.__market.advance(1));
    check('Enter on a signpost arm walks there', (await state(page, 'stop')) === 'books');
    await ctx.close();
  }

  if (run('schmuck')) {
    log('the ornament shop (round 9): a stroll stop with three moments and nothing else to click (lite market, 960 px)');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0`, { viewport: { width: 960, height: 640 } });
    await waitReady(page);
    await page.evaluate(() => window.__market.settled());
    const report = await page.evaluate(() => window.__market.report);
    const settle = () => page.evaluate(() => { const m = window.__market; for (let i = 0; i < 60 && m.cam().moving; i++) m.advance(0.5); m.advance(0.5); });
    check('the ornament shop is a stop on the stroll, between the Bücherstand and the Karussell', report.stroll.stops.join() === 'glueh,band,bier,books,schmuck,carousel,ferris,wurst', report.stroll.stops.join());
    check('the signpost has an arm for it, in the market (act_sign_schmuck) and on screen', !!(await page.evaluate(() => window.__market.screenPoint('act_sign_schmuck'))) && (await page.locator('#signboard .sb-arm[data-place="schmuck"]').count()) === 1);
    await page.click('#signboard .sb-arm[data-place="schmuck"]');
    await settle();
    const at = await page.evaluate(() => ({ stop: window.__market.stop, arrived: window.__market.arrived, here: document.getElementById('hereName').textContent }));
    check('the signpost arm walks to the ornament shop', at.stop === 'schmuck' && at.arrived && /Christbaumschmuck/.test(at.here), JSON.stringify(at));
    const models = await page.evaluate(() => window.__market.report.models.filter((m) => m.place === 'schmuck'));
    check('the shop is the vendor\'s stall_schmuck.glb, not a deco stall', models.some((m) => /stall_schmuck/.test(m.file || '') && m.kind !== 'deco'), JSON.stringify(models));
    // small screen (judge note, round 8): the shop's bar folds away, as it does at an open cabinet
    const fb = await page.evaluate(() => { const b = document.getElementById('stopbar'), f = document.getElementById('stopFold'); return { folded: b.classList.contains('folded'), fold: !f.hidden, h: b.getBoundingClientRect().height, vh: innerHeight, expanded: f.getAttribute('aria-expanded') }; });
    check('small screen: the shop\'s stop bar starts folded and keeps off the stall (under 15 % of the view)', fb.folded && fb.fold && fb.expanded === 'false' && fb.h < 0.15 * fb.vh, JSON.stringify(fb));
    await page.click('#stopFold');
    const bar = await page.evaluate(() => [...document.querySelectorAll('#stopActs [data-action]')].map((b) => b.dataset.action));
    check('"Things to do" opens the bar: exactly the three moments (candles, harmonica, dive)', bar.join() === 'candles,harmonica,dive', bar.join());
    await page.click('#stopFold');
    check('"Things to do" folds the bar away again', await page.evaluate(() => document.getElementById('stopbar').classList.contains('folded')));
    const S = () => page.evaluate(() => window.__market.handlers.schmuck());
    const s0 = await S();
    // the round-8 interactions are gone: no spinning baubles, star, nutcracker, smoker puff, tree hanging or pickle
    {
      const gone = await page.evaluate(() => ({ api: ['baubleNames', 'hangableNames', 'ornamentNote'].filter((k) => k in window.__market.handlers), clickable: window.__market.handlers.schmuck().clickable }));
      const odd = gone.clickable.filter((n) => !/^act_orn_(harmonica_\d+|mirrorball|schwibbogen|candle_\d+)$/.test(n));
      check('the round-8 ornament interactions are gone (only the harmonica, the mirror ball and the Schwibbogen answer a click)', !gone.api.length && !odd.length && gone.clickable.filter((n) => /harmonica/.test(n)).length === 12 && gone.clickable.includes('act_orn_mirrorball') && gone.clickable.includes('act_orn_schwibbogen'), JSON.stringify({ api: gone.api, odd, n: gone.clickable.length }));
      const deco = await page.evaluate(() => { const out = {}; for (const n of ['nutcracker', 'smoker', 'act_orn_pickle', 'act_orn_herrnhut', 'act_orn_nutcracker', 'act_orn_smoker']) { const o = window.__market.scene.getObjectByName(n); out[n] = o ? !!window.__market.item(n) : null; } return out; });
      check('the nutcracker and the smoker are decoration (in the shop, not items)', deco.nutcracker === false && deco.smoker === false && !Object.entries(deco).some(([k, v]) => /^act_/.test(k) && v), JSON.stringify(deco));
    }
    // ---- the glass harmonica ----
    const PHRASE = ['D5', 'Bb5', 'A5', 'G5', 'A5', 'C6', 'Eb6', 'D6', 'F#5', 'G5', 'F5', 'Ab5'];
    check('the harmonica\'s twelve baubles are tuned to the opening of the ballad (D Bb A G A C Eb D F# G F Ab)', JSON.stringify(s0.harmonica?.notes) === JSON.stringify(PHRASE), JSON.stringify(s0.harmonica?.notes));
    await page.evaluate(() => { const st = document.getElementById('stage'); st.scrollIntoView({ block: 'nearest', behavior: 'instant' }); window.__market.freeze(true); window.__market.advance(0.5); });
    const brush = async (from, to, steps, wait) => {
      const pts = await page.evaluate(() => window.__market.handlers.harmonicaPoints());
      const a = pts[from], b = pts[to];
      const y = (a.y + b.y) / 2;
      const yaw0 = (await page.evaluate(() => window.__market.cam())).look.yaw;
      const n0 = (await S()).harmonica.log.length;
      const sx = Math.sign(b.x - a.x), x0 = a.x - a.r * 1.6 * sx, x1 = b.x + b.r * 1.6 * sx;
      await page.mouse.move(x0, y);
      await page.mouse.down();
      // a slow stroke: real time between the moves (the brush reads its speed from the events' time stamps)
      for (let k = 1; k <= steps; k++) { await page.mouse.move(x0 + ((x1 - x0) * k) / steps, y); if (wait) await page.waitForTimeout(wait); }
      await page.mouse.up();
      await page.evaluate(() => window.__market.advance(0.3));
      const h = (await S()).harmonica;
      return { strikes: h.log.slice(n0), yaw: (await page.evaluate(() => window.__market.cam())).look.yaw - yaw0, glow: h.glow, swing: h.swing, onCanvas: await page.evaluate(([x, y]) => document.elementFromPoint(x, y)?.tagName, [a.x, y]) };
    };
    const slow = await brush(0, 11, 48, 30);
    const order = slow.strikes.map((x) => x.i);
    check('a mouse brush across the row rings the baubles left to right (the tune)', order.length >= 10 && order.every((v, i) => i === 0 || v > order[i - 1]), JSON.stringify({ order, onCanvas: slow.onCanvas }));
    check('brushing does not turn the head (the row claims the pointer from the look-around)', Math.abs(slow.yaw) < 1e-3, String(slow.yaw));
    check('each bauble glows on its note and swings on its ribbon', slow.glow.filter((g) => g > 0.2).length >= 8 && slow.swing.filter((w) => w > 0.003).length >= 8, JSON.stringify({ glow: slow.glow, swing: slow.swing }));
    await page.evaluate(() => window.__market.advance(4));
    const fast = await brush(11, 0, 5, 0);
    const mean = (a) => a.reduce((x, y) => x + y.v, 0) / Math.max(1, a.length);
    check('velocity follows the brush: a fast stroke rings louder than a slow one', fast.strikes.length >= 6 && mean(fast.strikes) > mean(slow.strikes) + 0.1, JSON.stringify({ slow: +mean(slow.strikes).toFixed(2), fast: +mean(fast.strikes).toFixed(2), n: fast.strikes.length }));
    // tapping in order: the first five notes, then a pause: the sixth glows faintly
    const tapped = await page.evaluate(async () => {
      const m = window.__market;
      m.advance(5);
      const pts = m.handlers.harmonicaPoints();
      const c = document.querySelector('#stage canvas');
      for (let i = 0; i < 5; i++) {
        const p = pts[i];
        const o = { clientX: p.x, clientY: p.y, pointerId: 7, pointerType: 'mouse', bubbles: true, buttons: 1, button: 0 };
        c.dispatchEvent(new PointerEvent('pointerdown', o));
        c.dispatchEvent(new PointerEvent('pointerup', { ...o, buttons: 0 }));
        m.advance(0.4);
      }
      const after = m.handlers.schmuck().harmonica;
      m.advance(4.5);
      return { log: after.log.slice(-5).map((x) => x.i), expect: after.expect, hint: m.handlers.schmuck().harmonica.hint };
    });
    check('tapping the baubles in order plays the phrase, and after a pause the next bauble glows faintly', tapped.log.join() === '0,1,2,3,4' && tapped.hint === 5, JSON.stringify(tapped));
    // touch: a finger drag brushes too (synthetic touch pointers: Playwright's touchscreen only taps)
    const touch = await page.evaluate(() => {
      const m = window.__market, c = document.querySelector('#stage canvas');
      const pts = m.handlers.harmonicaPoints();
      const yaw0 = m.cam().look.yaw, n0 = m.handlers.schmuck().harmonica.log.length;
      const ev = (type, x, y, t) => c.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, pointerId: 31, pointerType: 'touch', isPrimary: true, bubbles: true, cancelable: true, buttons: type === 'pointerup' ? 0 : 1 }));
      const a = pts[2], b = pts[9];
      ev('pointerdown', a.x, a.y);
      for (let k = 1; k <= 24; k++) ev('pointermove', a.x + ((b.x - a.x) * k) / 24, a.y + ((b.y - a.y) * k) / 24);
      ev('pointerup', b.x, b.y);
      m.advance(0.5);
      const log = m.handlers.schmuck().harmonica.log.slice(n0).map((x) => x.i);
      return { log, yaw: m.cam().look.yaw - yaw0 };
    });
    check('touch: a finger drag across the row plays it and leaves the look-around alone', touch.log.length >= 6 && Math.abs(touch.yaw) < 1e-3, JSON.stringify(touch));
    const tune = await page.evaluate(() => { const m = window.__market; m.advance(5); for (let i = 0; i < 12; i++) { m.handlers.harmonicaStrike(i, 0.6); m.advance(0.3); } m.advance(0.4); return { note: m.note(), glow: m.handlers.schmuck().harmonica.glow }; });
    check('played through, the row answers (a ripple of light, and a word about the ballad)', /Lanterns After Closing/.test(tune.note || ''), tune.note);
    await page.evaluate(() => window.__market.act('schmuck', 'harmonica'));
    const auto = await page.evaluate(() => {
      const m = window.__market; const n0 = m.handlers.schmuck().harmonica.log.length;
      m.advance(1.6);
      const lean = { busy: m.handlers.schmuck().busy, mode: m.cam().mode, phase: m.handlers.schmuck().harmonica.lean, moment: document.documentElement.dataset.moment || null };
      const pts = m.handlers.harmonicaPoints(), r = document.querySelector('#stage canvas').getBoundingClientRect();
      lean.span = +((Math.max(...pts.map((p) => p.x)) - Math.min(...pts.map((p) => p.x))) / r.width).toFixed(2);
      m.advance(12);
      const log = m.handlers.schmuck().harmonica.log.slice(n0).map((x) => `${x.i}:${x.source}`);
      for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.25) m.advance(0.25);
      m.advance(0.3);
      return { log, lean, after: { busy: m.handlers.schmuck().busy, mode: m.cam().mode, stop: m.stop } };
    });
    check('"Play the glass harmonica": the camera leans in until the row fills the view', auto.lean.busy === 'harmonica' && auto.lean.mode === 'drive' && auto.lean.phase === 'hold' && auto.lean.span > 0.6, JSON.stringify(auto.lean));
    check('... it plays the phrase in its own rhythm, and eases back to the stop', auto.log.length === 12 && auto.log.every((x, i) => x === `${i}:auto`) && !auto.after.busy && auto.after.mode === 'stop' && auto.after.stop === 'schmuck', JSON.stringify(auto));
    // ---- the Schwibbogen ----
    await page.evaluate(() => window.__market.advance(3));
    const sw = await page.evaluate(() => {
      const m = window.__market;
      m.act('schmuck', 'candles');
      const seen = [];
      for (let t = 0; t < 24; t += 0.25) {
        m.advance(0.25);
        const s = m.handlers.schmuck().schwibbogen;
        seen.push({ t, burning: s.burning, lit: s.windows.lit, wake: s.wake, chord: s.chord, wave: s.wave.running, bloom: s.wave.bloom, cam: s.cam, gain: +m.handlers.waveGainAt(12).toFixed(2) });
      }
      const s = m.handlers.schmuck().schwibbogen;
      const cam = m.cam();
      return { seen, s, cam, busy: m.handlers.schmuck().busy, moment: document.documentElement.dataset.moment || null, barShown: getComputedStyle(document.getElementById('stopbar')).display !== 'none' };
    });
    const lit = sw.seen.map((x) => x.burning);
    check('Schwibbogen: the candles light one by one', lit.at(-1) === sw.s.of && sw.s.of === 7 && new Set(lit).size >= 7 && lit.every((v, i) => i === 0 || v >= lit[i - 1]), lit.join(''));
    check('Schwibbogen: from the outside in (the vendor\'s order)', sw.s.lit.join() === 'act_orn_candle_0,act_orn_candle_6,act_orn_candle_1,act_orn_candle_5,act_orn_candle_2,act_orn_candle_4,act_orn_candle_3', sw.s.lit.join());
    const win = sw.seen.map((x) => x.lit);
    const half = sw.seen.find((x) => x.burning === 4);
    check('Schwibbogen: with each flame a share of the town\'s dark windows turns warm, until most are lit', sw.s.windows.candidates > 100 && half && half.lit > 0 && half.lit < sw.s.windows.lit && sw.s.windows.lit >= 0.9 * sw.s.windows.candidates && win.every((v, i) => i === 0 || v >= win[i - 1]), JSON.stringify({ windows: sw.s.windows, half: half && half.lit }));
    check('Schwibbogen: a low warm chord builds, one voice per flame', sw.s.chord === 7 && sw.seen.find((x) => x.burning === 3)?.chord === 3, JSON.stringify(sw.seen.filter((x, i) => i % 6 === 0).map((x) => x.chord)));
    const crest = Math.max(...sw.seen.map((x) => x.gain)), bloomPeak = Math.max(...sw.seen.map((x) => x.bloom));
    const firstWave = sw.seen.findIndex((x) => x.wave), lastLight = sw.seen.findIndex((x) => x.burning === 7);
    check('Schwibbogen: after the last flame a wave of light runs across the market (bulbs flare in turn, the bloom swells and settles)', firstWave > lastLight && crest > 1.8 && bloomPeak > 1.5 && sw.seen.at(-1).bloom < 1.25, JSON.stringify({ firstWave, lastLight, crest, bloomPeak, end: sw.seen.at(-1).bloom }));
    check('Schwibbogen: the camera stands behind the arch looking out over the candles, the bar steps aside', sw.cam.mode === 'drive' && sw.s.cam === 'hold' && sw.busy === 'schwibbogen' && sw.moment === 'schwibbogen' && !sw.barShown, JSON.stringify({ cam: sw.cam, phase: sw.s.cam, busy: sw.busy, bar: sw.barShown }));
    await page.keyboard.press('Escape');
    const back = await page.evaluate(() => { const m = window.__market; for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.25) m.advance(0.25); m.advance(0.5); return { busy: m.handlers.schmuck().busy, mode: m.cam().mode, stop: m.stop, burning: m.handlers.schmuck().schwibbogen.burning, moment: document.documentElement.dataset.moment || null }; });
    check('Escape steps back round the arch to the stop; the candles keep burning', !back.busy && back.mode === 'stop' && back.stop === 'schmuck' && back.burning === 7 && !back.moment, JSON.stringify(back));
    const out = await page.evaluate(() => { const m = window.__market; m.clickItem('act_orn_schwibbogen'); for (let t = 0; t < 10; t += 0.5) m.advance(0.5); const s = m.handlers.schmuck().schwibbogen; return { phase: s.phase, burning: s.burning, wake: s.wake, hush: s.windows.hush, chord: s.chord, settle: s.wave.settle, label: document.querySelector('#stopActs [data-action="candles"]')?.textContent }; });
    check('a click on the arch again lets it fade back (candles out, the town back as it was, the glow gone)', out.phase === 'off' && out.burning === 0 && out.wake === 0 && out.hush < 0.01 && out.chord === 0 && out.settle < 0.05 && /Light the Schwibbogen/.test(out.label || ''), JSON.stringify(out));
    // ---- the reflection dive ----
    const dv = await page.evaluate(() => {
      const m = window.__market;
      m.act('schmuck', 'dive');
      const seen = [];
      let close = 9, inside = null;
      for (let t = 0; t < 6.5; t += 0.1) {
        m.advance(0.1);
        const d = m.handlers.schmuck().dive;
        if (seen.at(-1) !== d.phase) seen.push(d.phase);
        if (d.phase === 'gaze') close = Math.min(close, d.dist);
        if (d.phase === 'inside' && !inside) inside = d;
      }
      return { seen, close, inside, env: m.handlers.schmuck().dive.env, glass: m.handlers.schmuck().dive.glass, fov: m.camera.fov };
    });
    check('dive: a cube camera renders the market into the ball once at the tap (256 px on the lite market), with a clear coat\'s Fresnel', dv.env?.size === 256 && dv.env.captures >= 1 && dv.glass === 'engine_mirrorball_glass', JSON.stringify({ env: dv.env, glass: dv.glass }));
    check('dive: the camera eases in until the reflection fills the view (within 2 ball radii of its centre)', dv.seen.slice(0, 3).join() === 'approach,gaze,into' && dv.close < 0.2, JSON.stringify({ seen: dv.seen, close: dv.close }));
    check('dive: it crossfades into the market seen from inside the glass (the warped, hushed pass; the ball itself hidden)', !!dv.inside && dv.inside.pass.enabled && dv.inside.pass.warp === 1 && dv.inside.pass.captures >= 1 && !dv.inside.ballVisible && dv.inside.dist < 0.02 && dv.fov > 70, JSON.stringify({ inside: dv.inside, fov: dv.fov }));
    await page.keyboard.press('Escape');
    const dout = await page.evaluate(() => { const m = window.__market; const seen = []; for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.1) { m.advance(0.1); const p = m.handlers.schmuck().dive.phase; if (seen.at(-1) !== p) seen.push(p); } m.advance(0.3); const d = m.handlers.schmuck().dive; return { seen, d, mode: m.cam().mode, fov: m.camera.fov, near: m.camera.near }; });
    check('dive: Escape eases back out to the stop (pass off, ball back, the camera\'s near plane and lens restored)', dout.seen.includes('outof') && dout.seen.includes('back') && !dout.d.phase && !dout.d.pass.enabled && dout.d.ballVisible && dout.mode === 'stop' && dout.near === 0.1 && dout.fov < 60, JSON.stringify(dout));
    const tap = await page.evaluate(async () => {
      const m = window.__market, c = document.querySelector('#stage canvas');
      m.act('schmuck', 'dive');
      for (let t = 0; t < 5.5; t += 0.1) m.advance(0.1);
      await new Promise((r) => setTimeout(r, 450));
      const before = m.handlers.schmuck().dive.phase;
      const r = c.getBoundingClientRect();
      const o = { clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, pointerId: 9, pointerType: 'mouse', bubbles: true, button: 0 };
      c.dispatchEvent(new PointerEvent('pointerdown', o)); c.dispatchEvent(new PointerEvent('pointerup', o));
      for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.1) m.advance(0.1);
      return { before, after: m.handlers.schmuck().dive.phase, mode: m.cam().mode };
    });
    check('dive: a tap ends it too', tap.before === 'inside' && tap.after === null && tap.mode === 'stop', JSON.stringify(tap));
    // ---- the sparkle ----
    const sp = await page.evaluate(() => { const m = window.__market; const a = m.handlers.schmuck(); m.advance(1.3); m.renderFrame(); const b = m.handlers.schmuck(); return { a: a.sparkle, b: b.sparkle, p0: a.pyramid, p1: b.pyramid }; });
    check('sparkle: the foxed mirror gets a reflection (mirror_0, rendered while the visitor is near)', sp.b.mirrors >= 1 && sp.b.mirrorRenders > 0, JSON.stringify(sp.b));
    check('sparkle: the tinsel swags carry the glint shader', sp.b.tinsels >= 2 && sp.b.glintMaterials === sp.b.tinsels, JSON.stringify(sp.b));
    check('sparkle: the candle pyramid turns slowly about its upright axis, its flames flicker', sp.p0?.axis === 'y' && Math.abs(sp.p1.angle - sp.p0.angle) > 0.2 && Math.abs(sp.p1.angle - sp.p0.angle) < 1.0 && sp.b.flames >= 1 && sp.a.flameGlow !== sp.b.flameGlow, JSON.stringify({ p0: sp.p0, p1: sp.p1, f0: sp.a.flameGlow, f1: sp.b.flameGlow }));
    check('sparkle: the Räuchermännchen smokes on his own (fx_smoke_1)', sp.b.smoke > 0.1, JSON.stringify(sp.b));
    await page.evaluate(() => window.__market.freeze(false));
    await shot(page, 'stop_schmuck.jpg', '#stage');
    // a click in 3D on a harmonica bauble rings it
    {
      await page.evaluate(() => { window.__market.freeze(true); window.__market.advance(4); });
      const pts = await page.evaluate(() => window.__market.handlers.harmonicaPoints());
      const p = pts[6];
      const n0 = (await S()).harmonica.log.length;
      await page.mouse.click(p.x, p.y);
      await page.evaluate(() => window.__market.advance(0.5));
      const h = (await S()).harmonica;
      check('a click in 3D on a harmonica bauble rings that bauble once', h.log.length - n0 === 1 && h.log.at(-1).i === 6, JSON.stringify(h.log.slice(n0)));
      await page.evaluate(() => window.__market.freeze(false));
    }
    await ctx.close();
  }

  if (run('moments')) {
    log('the ornament shop\'s three moments at their peaks (full market, 1280 px): screenshots');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { viewport: { width: 1280, height: 720 } });
    await waitReady(page);
    // software GL draws the full market at several seconds a frame: hold the live loop for the whole section and
    // draw only the frames the screenshots need (each snapshot renders one), so the waits below are not starved
    const t0m = Date.now();
    const lap = (what) => log(`${what} (${((Date.now() - t0m) / 1000).toFixed(0)} s)`);
    await page.evaluate(() => window.__market.freeze(true));
    await page.evaluate(() => window.__market.settled());
    lap('settled');
    await page.evaluate(() => window.__market.walkTo('schmuck'));
    await page.evaluate(() => { const m = window.__market; for (let i = 0; i < 80 && !m.arrived; i++) m.advance(0.5); m.advance(0.5); });
    const full = await page.waitForFunction(() => window.__market.streaming().state['deco-schmuck'] === 'full', null, { timeout: LONG, polling: 500 }).then(() => true, () => false);
    lap('at the shop, streamed');
    check('full market: the shop streams in at full detail at its stop', full, JSON.stringify(await page.evaluate(() => window.__market.streaming().state['deco-schmuck'])));
    await page.evaluate(() => { window.__market.freeze(true); window.__market.advance(1); });
    const snapTo = async (name) => {
      const d = await page.evaluate(() => window.__market.snapshot('image/jpeg', 0.88));
      writeFileSync(path.join(OUT, name), Buffer.from(d.split(',')[1], 'base64'));
      log('screenshot', path.relative(process.cwd(), path.join(OUT, name)));
      lap(name);
    };
    const S = () => page.evaluate(() => window.__market.handlers.schmuck());
    await snapTo('shop_stop.jpg');
    const spF = (await S()).sparkle;
    check('full market: the mirror reflection is 640 px wide and drawn every frame at the shop', spF.mirrorSize?.[0] === 640 && spF.mirrorRenders > 0, JSON.stringify(spF));
    // the Schwibbogen: first flames, the town half awake, the wave at its height
    await page.evaluate(() => window.__market.act('schmuck', 'candles'));
    // the view over the arch with the town still dark, four flames and the town waking, the wave of light at its
    // height (the bulbs flaring as it passes, the bloom swelled), and the market settled in its lasting glow
    // (the wave's frame is timed by the wave itself: its front 2.4 s out, about 17 m, over the stalls across the
    // square, so the frame shows it: the near strings flaring, the far ones still dim, the bloom near its height)
    const times = [[4.25, 'schwib_1_town_dark.jpg'], [6.8, 'schwib_2_town_waking.jpg'], ['wave', 'schwib_3_light_wave.jpg'], [19, 'schwib_4_settled.jpg']];
    const WAVE_SNAP = 2.4;
    let at = 0;
    const peaks = [];
    for (const [t, name] of times) {
      if (t === 'wave') at += await page.evaluate((w) => { const m = window.__market; let a = 0; while (a < 12) { const x = m.handlers.schmuck().schwibbogen.wave; if (x.running && x.t >= w) break; m.advance(0.1); a += 0.1; } return a; }, WAVE_SNAP);
      else { await page.evaluate((d) => window.__market.advance(d), t - at); at = t; }
      await snapTo(name);
      const x = (await S()).schwibbogen;
      const near = await page.evaluate(() => +window.__market.handlers.waveBulbGainAt(8).toFixed(2)), far = await page.evaluate(() => +window.__market.handlers.waveBulbGainAt(30).toFixed(2));
      peaks.push({ name, at: +at.toFixed(2), burning: x.burning, windows: x.windows.lit, hush: x.windows.hush, quiet: x.windows.quiet, bloom: x.wave.bloom, waveT: x.wave.t, front: x.wave.front, marketHush: x.wave.hush, near, far, cam: x.cam });
    }
    check('full market: the screenshots catch each beat (the town gone quiet over unlit candles, waking, the wave\'s bloom at its height, settled)', peaks[0].burning === 0 && peaks[0].windows === 0 && peaks[0].hush > 0.9 && peaks[0].quiet > 100 && peaks[0].cam === 'hold' && peaks[1].windows > 0 && peaks[1].burning >= 3 && peaks[2].windows > peaks[1].windows && peaks[2].bloom > 2 && peaks[3].bloom < peaks[2].bloom, JSON.stringify(peaks));
    check('full market: the wave\'s frame shows its front (the market dimmed while it waited; bulbs 8 m out flaring, 30 m out still dim)', peaks[1].marketHush > 0.5 && peaks[2].near > 1.5 && peaks[2].far < 0.6 && peaks[3].marketHush === 0, JSON.stringify(peaks.map((p) => ({ name: p.name, marketHush: p.marketHush, near: p.near, far: p.far, front: p.front }))));
    const swF = (await S()).schwibbogen;
    check('full market: the Schwibbogen sequence ran (seven flames, windows warm, the wave)', swF.burning === 7 && swF.windows.lit > 0.9 * swF.windows.candidates && swF.wave.settle > 0.1, JSON.stringify(swF));
    await page.evaluate(() => { const m = window.__market; m.handlers.shopEnd(); for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.25) m.advance(0.25); m.advance(1); });
    // the harmonica mid-phrase: five notes in, the fifth glowing
    await page.evaluate(() => { const m = window.__market; m.act('schmuck', 'harmonica'); m.advance(1.6 + (6.5 / 72) * 60 + 0.12); });
    await snapTo('harmonica_mid_phrase.jpg');
    const hF = (await S()).harmonica;
    check('full market: a bauble glows mid-phrase on the harmonica (the camera leaned in to the row)', hF.glow[4] > 0.5 && hF.glow[4] > hF.glow[0] && hF.lean === 'hold', JSON.stringify(hF.glow));
    await page.evaluate(() => { const m = window.__market; m.handlers.shopEnd(); for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.25) m.advance(0.25); m.advance(0.5); });
    // the dive: in close, through the glass, inside
    await page.evaluate(() => { const m = window.__market; m.clickItem('act_orn_schwibbogen'); m.advance(8); });
    await page.evaluate(() => window.__market.act('schmuck', 'dive'));
    const dt = [[1.6, 'dive_1_approach.jpg'], [3.0, 'dive_2_reflection.jpg'], [3.85, 'dive_3_into_glass.jpg'], [6.6, 'dive_4_inside.jpg']];
    at = 0;
    for (const [t, name] of dt) { await page.evaluate((d) => window.__market.advance(d), t - at); at = t; await snapTo(name); }
    const dF = (await S()).dive;
    check('full market: the dive reaches the inside of the glass (512 px cube)', dF.phase === 'inside' && dF.env?.size === 512, JSON.stringify(dF));
    await page.evaluate(() => { const m = window.__market; m.handlers.shopEnd(); for (let t = 0; t < 8 && m.handlers.schmuck().busy; t += 0.1) m.advance(0.1); });
    check('full market: the dive comes back out', !(await S()).busy);
    await page.evaluate(() => window.__market.freeze(false));
    await ctx.close();
  }

  if (run('cabinet')) {
    log('the Bücherstand cabinets on a 390 px phone: tap, open, its books only, covers ≥ 44 px, arrows, a way back');
    const { ctx, page } = await openPage(`${BASE}?snow=0`, { reducedMotion: 'reduce', viewport: { width: 390, height: 844 }, touch: true });
    await waitReady(page);
    await page.tap('#signboard .sb-toggle');
    await page.tap('#signboard .sb-arm[data-place="books"]');
    await frames(page, 2);
    check('phone: the signpost walks to the Bücherstand', (await state(page, 'stop')) === 'books' && (await page.evaluate(() => window.__market.arrived)));
    const cabs = await page.evaluate(() => window.__market.handlers.cabinets());
    check('the Bücherstand has its six cabinets, each with a door (act_cab_), a sign (sign_cat_) and a tap target', cabs.length === 6 && cabs.every((c) => c.door && c.sign && c.proxy && c.books > 0), JSON.stringify(cabs));
    // on a 390 px phone the stall's front is wider than the screen: the cabinets stand off either edge, and the
    // ‹ › buttons beside the stall turn the visitor to them, one at a time
    check('phone: ‹ › buttons beside the stall turn to the cabinets', (await page.locator('#cabTurnR').isVisible()) && (await page.locator('#cabTurnL').isVisible()));
    await page.tap('#cabTurnR');
    await frames(page, 2);
    await page.evaluate(() => window.__market.advance(2));
    await stillCamera(page);
    const key = (await page.evaluate(() => window.__market.handlers.facedCabinet())) || cabs[0].key;
    const kIdx = cabs.findIndex((c) => c.key === key);
    const faced = await page.evaluate((key) => { const b = window.__market.screenBox(`engine_cabinet_proxy_${key}`); return b && { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.w), h: Math.round(b.h), onScreen: b.onScreen }; }, key);
    check('› turns to a cabinet, now in view (and big enough to tap)', !!faced && faced.x > 20 && faced.x < 370 && Math.min(faced.w, faced.h) >= 44, JSON.stringify({ key, faced }));
    // a tap on a cabinet's door or sign is a tap on the cabinet, never on one book (and on the canvas, not the bar)
    const tapAt = await page.evaluate((key) => {
      const m = window.__market, cv = document.querySelector('#stage canvas');
      for (const name of [`engine_cabinet_proxy_${key}`, `sign_cat_${key}`, `act_cab_${key}`]) {
        const c = m.screenPoint(name);
        if (!c?.onScreen) continue;
        for (let r = 0; r <= 60; r += 4) for (let a = 0; a < 12; a++) {
          const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r;
          if (document.elementFromPoint(x, y) !== cv) continue;
          if (m.pickAt(x, y)?.proxy === `cabinet:${key}`) return { x, y, via: name };
        }
      }
      return null;
    }, key);
    if (tapAt) await page.touchscreen.tap(tapAt.x, tapAt.y);
    else await page.evaluate((k) => window.__market.handlers.openCabinet(k), key);
    await frames(page, 3);
    await page.evaluate(() => window.__market.advance(2));
    await stillCamera(page);
    const st = await page.evaluate(() => window.__market.handlers.cabinetState());
    check('tapping a cabinet moves to its view, opens its door and brings its books forward', !!tapAt && st?.key === key && st.open && st.door > 1 && (await page.evaluate(() => document.documentElement.dataset.cabinet)) === key, JSON.stringify({ tapAt, st }));
    check('a clear way back is on screen (Step back)', await page.locator('#stepBack').isVisible());
    // only this cabinet's books answer the pointer
    const grid = await page.evaluate((mine) => {
      const m = window.__market, r = document.querySelector('#stage canvas').getBoundingClientRect(), seen = new Set();
      for (let y = r.top + 4; y < r.bottom; y += 12) for (let x = r.left + 4; x < r.right; x += 12) { const n = m.itemAt(x, y); if (n && /book|spine|cover/i.test(n)) seen.add(n); }
      return { seen: [...seen], others: [...seen].filter((n) => !mine.includes(n)) };
    }, st.books);
    check('only the open cabinet\'s books are pickable', grid.seen.length > 0 && !grid.others.length, JSON.stringify(grid).slice(0, 300));
    const sizes = await page.evaluate((names) => {
      // a cover under the bar of things to do (or any other control over the canvas) is not in view
      const bars = [...document.querySelectorAll('#stopbar, #readbar, #signboard')].filter((e) => e.offsetParent !== null).map((e) => e.getBoundingClientRect());
      return names.map((n) => { const b = window.__market.screenBox(n); const hidden = !!b && bars.some((r) => b.x > r.left && b.x < r.right && b.y > r.top && b.y < r.bottom); return { n, ...b, onScreen: !!b?.onScreen && !hidden }; });
    }, st.books);
    const small = sizes.filter((b) => !b.onScreen || Math.min(b.w, b.h) < 44);
    check('every cover in the open cabinet is at least 44 px on a 390 px screen, and in view', !small.length, `${sizes.length} covers; smallest ${Math.min(...sizes.map((b) => Math.min(b.w, b.h))).toFixed(1)} px; ${JSON.stringify(small.map((b) => [b.n, Math.round(b.w), Math.round(b.h)]).slice(0, 4))}`);
    await shot(page, 'phone_cabinet_open.jpg', null, { keepScroll: true });
    // the arrows: ← → between the books, ↑ ↓ between the cabinets
    await page.focus('#stage canvas');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    const f2 = await page.evaluate(() => window.__market.handlers.cabinetState());
    await page.keyboard.press('ArrowLeft');
    const f1 = await page.evaluate(() => window.__market.handlers.cabinetState());
    check('← → move between the open cabinet\'s books', f2.focus === st.books[Math.min(1, st.books.length - 1)] && f1.focus === st.books[0] && (await state(page, 'stop')) === 'books', JSON.stringify([f2.focus, f1.focus]));
    await page.keyboard.press('ArrowDown');
    await frames(page, 2);
    const nextCab = await page.evaluate(() => window.__market.handlers.cabinetState());
    check('↓ opens the next cabinet (the first one shuts)', nextCab?.key === cabs[(kIdx + 1) % cabs.length].key && nextCab.open, JSON.stringify(nextCab));
    await page.keyboard.press('ArrowUp');
    await frames(page, 2);
    check('↑ goes back to the cabinet before', (await page.evaluate(() => window.__market.handlers.cabinetState()?.key)) === key);
    // a tapped cover opens that book; Escape puts it back with the cabinet still open
    const book = st.books[0];
    const bAim = await aimAt(page, book);
    if (bAim) await page.touchscreen.tap(bAim.x, bAim.y);
    else await page.evaluate((n) => window.__market.clickItem(n), book);
    for (let i = 0; i < 30 && (await page.evaluate(() => window.__market.openedBook()?.state)) !== 'open'; i++) await page.evaluate(() => window.__market.advance(0.5));
    const ob = await page.evaluate(() => window.__market.openedBook());
    check('tapping a cover opens that book', !!bAim && ob?.name === book && ob.state === 'open', JSON.stringify({ bAim, ob }));
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.__market.advance(2));
    const afterBook = await page.evaluate(() => ({ book: window.__market.openedBook(), cab: window.__market.handlers.cabinetState()?.key }));
    check('Escape puts the book back, and the cabinet is still open', afterBook.book === null && afterBook.cab === key, JSON.stringify(afterBook));
    await page.tap('#stepBack');
    await page.evaluate(() => window.__market.advance(2));
    const back = await page.evaluate(() => ({ cab: window.__market.handlers.cabinetState(), stop: window.__market.stop, door: document.documentElement.dataset.cabinet || null }));
    check('Step back shuts the cabinet and returns to the stall\'s view', back.cab === null && back.stop === 'books' && !back.door, JSON.stringify(back));
    await stillCamera(page);
    const turnedBack = await page.evaluate((key) => { const m = window.__market, b = m.screenBox(`engine_cabinet_proxy_${key}`); return { faced: m.handlers.facedCabinet(), x: b && Math.round(b.x), onScreen: !!b?.onScreen, closeup: document.documentElement.classList.contains('closeup') }; }, key);
    check('Step back keeps the view turned toward that cabinet (in view, and ‹ › go on from it)', turnedBack.faced === key && turnedBack.onScreen && turnedBack.x > 20 && turnedBack.x < 370 && !turnedBack.closeup, JSON.stringify(turnedBack));
    const closedPick = await page.evaluate((names) => names.filter((n) => { const b = window.__market.screenBox(n); return b && window.__market.itemAt(b.x, b.y) === n; }), st.books);
    check('with the cabinet shut its books no longer answer the pointer', !closedPick.length, closedPick.join(' '));
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
    const tAim = await aimAt(page, 'act_wurst_thueringer');
    if (tAim) {
      await page.evaluate(() => window.__market.handlers.clearPlate());
      await page.evaluate(() => { const m = window.__market; for (let t = 0; t < 10 && m.handlers.plate().busy; t += 0.5) m.advance(0.5); });
      await page.touchscreen.tap(tAim.x, tAim.y);
      const pt = await page.evaluate(() => { const m = window.__market; for (let t = 0; t < 10 && m.handlers.plate().busy; t += 0.5) m.advance(0.5); m.advance(0.5); return m.handlers.plate(); });
      check('phone: tapping a Thüringer puts one on the plate (reduced motion: it lands at once)', pt.food.join() === 'thueringer', JSON.stringify(pt));
    } else check('phone: tapping a Thüringer puts one on the plate (reduced motion: it lands at once)', false, 'no clear pixel on act_wurst_thueringer');
    await page.evaluate(() => window.__market.read('wurst.menu'));
    await page.evaluate(() => window.__market.advance(1));
    await page.waitForFunction(() => window.__market.textOn('wurst.menu').length > 10, null, { timeout: LONG }).catch(() => {});
    check('phone: reading the menu board fills the screen with it', (await page.evaluate(() => window.__market.reading().id)) === 'wurst.menu');
    await shot(page, 'phone_reading_menu.jpg', null, { keepScroll: true });
    // the ornament shop on a phone, reduced motion: the bar folds away, and the moments are short and calm
    await page.evaluate(() => { window.__market.closeRead?.(); window.__market.walkTo('schmuck'); window.__market.advance(0.5); });
    const pf = await page.evaluate(() => ({ stop: window.__market.stop, folded: document.getElementById('stopbar').classList.contains('folded') }));
    check('phone: at the ornament shop the stop bar folds away (judge note, round 8)', pf.stop === 'schmuck' && pf.folded, JSON.stringify(pf));
    const rm = await page.evaluate(() => {
      const m = window.__market, H = () => m.handlers.schmuck();
      m.freeze(true);
      m.act('schmuck', 'candles');
      m.advance(0.05);
      const cut = { mode: m.cam().mode, cam: H().schwibbogen.cam };
      m.advance(3.2);
      const sw = H().schwibbogen;
      m.handlers.shopEnd(); m.advance(0.2);
      const back = { busy: H().busy, mode: m.cam().mode };
      m.clickItem('act_orn_schwibbogen'); m.advance(4);
      m.handlers.harmonicaStrike(3, 0.9); m.advance(0.4);
      const swing = Math.max(...H().harmonica.swing);
      m.act('schmuck', 'dive'); m.advance(0.05);
      const d0 = H().dive.phase; m.advance(1.2);
      const d1 = H().dive.phase; m.handlers.shopEnd(); m.advance(0.6); m.advance(0.1);
      const d2 = { phase: H().dive.phase, mode: m.cam().mode, busy: H().busy };
      m.freeze(false);
      return { cut, sw: { burning: sw.burning, wave: sw.wave.settle > 0 || sw.wave.running, phase: sw.phase }, back, swing, d0, d1, d2 };
    });
    check('reduced motion: the Schwibbogen cuts to the view over the arch, its seven candles light in about three seconds, Escape cuts back', rm.cut.mode === 'drive' && rm.cut.cam === 'hold' && rm.sw.burning === 7 && rm.sw.phase === 'lit' && !rm.back.busy && rm.back.mode === 'stop', JSON.stringify(rm));
    check('reduced motion: the harmonica\'s baubles ring and glow without swinging', rm.swing === 0, String(rm.swing));
    check('reduced motion: the dive cuts in (no glide) and out', ['into', 'inside'].includes(rm.d0) && rm.d1 === 'inside' && !rm.d2.phase && rm.d2.mode === 'stop' && !rm.d2.busy, JSON.stringify(rm));
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
    await tapAct(page, '#stopActs [data-action="pour"]');
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
    // the writing surfaces' troika text used to count Infinity triangles on the frame before its first glyph sync
    await p2.evaluate(() => window.__market.read('glueh.board'));
    await frames(p2, 4);
    await p2.evaluate(() => window.__market.closeRead());
    await frames(p2, 2);
    const ps = await p2.evaluate(() => window.__market.perf());
    check('the triangle count stays finite on every frame (troika text before its first sync)', ps && ps.badTriangles === 0 && Number.isFinite(ps.triangles) && ps.triangles > 0, JSON.stringify({ bad: ps?.badTriangles, tris: ps?.triangles, frames: ps?.frames }));
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
if (skipped.length) console.log(`${skipped.length} skipped (a later round's files on disk): ${skipped.map((x) => x.name).join('; ')}`);
if (errors.length) console.log('Console errors:\n  ' + errors.join('\n  '));
else console.log('No console errors.');
process.exit(failed.length || errors.length ? 1 : 0);
