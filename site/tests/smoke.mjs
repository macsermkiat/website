// End-to-end smoke test: the built site served by `vite preview`, driven by Playwright on software GL.
// 1. full market at 1280 px: home view, a stall panel, snow (screenshots)
// 2. every panel action, both rides, snow, reset, keyboard and a click in 3D (small viewport, for speed)
// 3. lite market auto-detected on a weak GPU (first-paint download, deferred models); a phone with reduced motion
// 4. plain.html and the music credit on both pages
// 5. every model missing (and layout.json ignored): stand-ins, no errors
// Fails on any console error, failed request or HTTP error.
// Usage: npm run build && node tests/smoke.mjs [--out ../review/round-1/engineer] [--port 4317] [--only shots,interact,audio,lite,phone,plain,missing]
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-1/engineer'));
const PORT = +opt('--port', 4317);
const ONLY = opt('--only', 'all');
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
const LONG = 180000;

async function openPage(url, { reducedMotion = 'no-preference', viewport = { width: 1280, height: 860 } } = {}) {
  const ctx = await browser.newContext({ viewport, reducedMotion, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
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
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true' || /could not/.test(document.getElementById('loadingText')?.textContent || ''), null, { timeout: 300000 });
  const ok = await page.evaluate(() => document.documentElement.dataset.ready === 'true');
  if (!ok) throw new Error('market did not start: ' + (await page.textContent('#loadingText')));
  log(`ready in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}

/** Wait for n rendered frames (software GL can be ~1 fps, so waiting on frames beats waiting on time). */
async function frames(page, n) {
  await page.evaluate((n) => new Promise((res) => { let k = 0; const f = () => (++k >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); }), n);
}
const note = (page) => page.textContent('#actNote');
const waitNote = (page, re) => page.waitForFunction((src) => new RegExp(src).test(document.getElementById('actNote')?.textContent || ''), re.source, { timeout: LONG }).then(() => true, () => false);
const state = (page, k) => page.evaluate((k) => window.__market[k], k);
const shot = async (page, name, sel, { keepScroll = false } = {}) => {
  const file = path.join(OUT, name);
  // hold the last rendered frame so the capture does not wait behind a slow software-GL frame
  if (!sel && !keepScroll) await page.evaluate(() => window.scrollTo(0, 0)); // clicking the place buttons scrolls the page
  const frozen = await page.evaluate(() => { if (!window.__market?.freeze) return false; window.__market.freeze(true); return true; });
  // a frozen page still waits for the frames already queued on the GPU; on SwiftShader those can take minutes
  const SHOT = 900000;
  if (sel) await page.locator(sel).screenshot({ path: file, type: 'jpeg', quality: 86, timeout: SHOT });
  else await page.screenshot({ path: file, type: 'jpeg', quality: 86, timeout: SHOT });
  if (frozen) await page.evaluate(() => window.__market.freeze(false));
  log('screenshot', path.relative(process.cwd(), file));
};

try {
  if (run('shots')) {
    log('full market, 1280 px (reduced motion, so flights land in one frame)');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { reducedMotion: 'reduce' });
    await waitReady(page);
    const report = await page.evaluate(() => window.__market.report);
    console.log(JSON.stringify(report).slice(0, 3000));
    console.log('full scene', JSON.stringify(report.scene));
    check('full market chosen with ?quality=full', report.quality.lite === false);
    // the distance LOD for the crowd loads after the first frame; hold the picture so it is not stuck behind frames
    await page.evaluate(() => window.__market.freeze(true));
    const settled = await page.evaluate(() => window.__market.settled());
    await page.evaluate(() => window.__market.freeze(false));
    await frames(page, 2);
    const crowd = await page.evaluate(() => window.__market.crowd());
    const sceneNow = await page.evaluate(() => window.__market.sceneStats());
    console.log('full scene after LOD', JSON.stringify(sceneNow), JSON.stringify(crowd));
    check('crowd distance LOD: far people use their lite figure', settled.lod > 0 && crowd.lite > 0, JSON.stringify({ settled, crowd }));
    check('bookshop spines merged into a few meshes', report.books?.merged?.meshes > 0 && report.books.merged.books > 20, JSON.stringify(report.books));
    await frames(page, 2);
    await shot(page, 'home_full.jpg');
    // Full quality on SwiftShader takes tens of seconds a frame, and clicks wait on frames to check the target.
    // So this phase drives the page through window.__market; the clicks themselves are tested on lite below.
    const go = (fn, ...a) => page.evaluate(fn, ...a);
    await go(() => { window.__market.openPlace('glueh'); window.__market.act('glueh', 'pour'); window.__market.act('glueh', 'prost'); });
    await frames(page, 3);
    const hidden = await page.evaluate(() => window.__market.hiddenPeople());
    check('Glühwein close-up: the vendor stays in view', !hidden.includes('vendor_gluehwein') && (await page.evaluate(() => window.__market.crowd().vendorsVisible)) === 4, hidden.join(' '));
    check('Glühwein close-up: the queue at the counter steps out of the shot', hidden.length > 0, hidden.join(' '));
    await shot(page, 'panel_gluehwein.jpg');
    await go(() => { window.__market.openPlace('books'); window.__market.act('books', 'book'); });
    await frames(page, 3);
    await shot(page, 'panel_buecherstand.jpg');
    await go(() => { window.__market.openPlace('band'); window.__market.act('band', 'sax'); });
    await frames(page, 3);
    await shot(page, 'panel_bandstand.jpg');
    await go(() => { window.__market.resetView(); window.__market.setSnow(true); });
    await page.evaluate(() => window.__market.advance(4)); // let the snow settle in
    await frames(page, 2);
    await shot(page, 'home_full_snow.jpg', '#stage');
    await ctx.close();
  }

  if (run('interact')) {
    log('every interaction (lite, small viewport for speed)');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0`, { viewport: { width: 960, height: 640 } });
    await waitReady(page);

    await page.click('#places button[data-place="glueh"]');
    check('Glühwein panel opens from the place buttons', (await state(page, 'panel')) === 'glueh');
    check('panel content comes from content/*.md or the fallback', (await page.textContent('#pBody')).length > 80);
    await page.click('#pActions [data-action="pour"]');
    check('pour a mug', /poured tonight: 1/.test(await note(page)), await note(page));
    await page.click('#pActions [data-action="prost"]');
    await page.waitForSelector('.bubble', { timeout: 20000 }).catch(() => {});
    check('Prost: the crowd raises a glass', (await page.locator('.bubble').count()) > 0);

    await page.click('#places button[data-place="bier"]');
    await page.click('#pActions [data-action="pint"]');
    check('pull a pint (starts)', /Pouring/.test(await note(page)));
    check('pull a pint (finishes)', await waitNote(page, /pulled tonight: 1/), await note(page));
    await page.click('#pActions [data-action="prost"]');

    await page.click('#places button[data-place="wurst"]');
    await page.click('#pActions [data-action="turn"]');
    check('turn the sausages', /Turned|flare|Almost/.test(await note(page)), await note(page));
    await page.click('#pActions [data-action="bun"]');
    check('a sausage in a bun', /Brötchen/.test(await note(page)), await note(page));

    await page.click('#places button[data-place="books"]');
    await page.click('#pActions [data-action="book"]');
    check('pull a book', /Rovelli|Hofstadter|Feynman|Seth|Pearl|·/.test(await note(page)), await note(page));
    // each of Mac's books sits on its own spine: aim at the second one and click it in 3D
    const spines = await page.evaluate(() => window.__market.featuredBooks());
    check('five named spines for the five books', spines.length === 5, spines.join(' '));
    await frames(page, 2);
    const aim = await page.evaluate((name) => {
      const m = window.__market, c = m.screenPoint(name);
      if (!c) return null;
      for (let r = 0; r <= 12; r += 2) for (let a = 0; a < 8; a++) {
        const x = c.x + Math.cos(a * Math.PI / 4) * r, y = c.y + Math.sin(a * Math.PI / 4) * r;
        if (m.bookAt(x, y) === name) return { x, y };
      }
      return null;
    }, spines[1]);
    if (aim) {
      await page.mouse.click(aim.x, aim.y);
      check('clicking a named spine gives that book', /Hofstadter|Gödel/.test(await note(page)), await note(page));
    } else check('clicking a named spine gives that book', false, `no clear pixel on ${spines[1]}`);

    await page.click('#places button[data-place="band"]');
    check('lite: the player buttons say they move the spotlight', /Spotlight/.test(await page.textContent('#pActions [data-action="sax"]')));
    await page.click('#pActions [data-action="sax"]');
    check('feature a band member', /sax/i.test(await note(page)), await note(page));
    await page.click('#pActions [data-action="whole"]');
    await page.click('#pActions [data-play]');
    await page.waitForFunction(() => /Pause|could not/.test(document.getElementById('play').textContent), null, { timeout: LONG });
    check('the band plays', /Pause/.test(await page.textContent('#play')), await page.textContent('#nowplaying'));
    check('lite: the band streams as one mix', ['mix', 'playing'].includes((await state(page, 'audio')).phase) || (await state(page, 'audio')).mode !== 'stems', JSON.stringify(await state(page, 'audio')));
    await page.click('#pActions [data-action="drums"]');
    check('featuring while playing', /drums/i.test(await note(page)));
    await page.click('#pActions [data-play]');
    check('the band stops', /Play/.test(await page.textContent('#play')));

    // the lite market loads the rides and deco stalls after its first frame
    const later = await page.evaluate(() => window.__market.settled());
    check('lite: rides and deco stalls arrive after the first frame', later.deferred >= 2, JSON.stringify(later));
    await page.click('#places button[data-place="ferris"]');
    await page.click('#pActions [data-action="ride"]');
    check('Riesenrad ride', (await state(page, 'riding')) === 'ferris');
    await page.evaluate(() => window.__market.advance(9)); // up toward the top
    await frames(page, 3);
    await shot(page, 'ride_riesenrad.jpg', '#stage');
    await page.click('#pActions [data-action="off"]');
    check('get off the wheel', (await state(page, 'riding')) === null);

    await page.click('#places button[data-place="carousel"]');
    await page.click('#pActions [data-action="ride"]');
    check('carousel ride', (await state(page, 'riding')) === 'carousel');
    await page.evaluate(() => window.__market.advance(4));
    await frames(page, 3);
    await shot(page, 'ride_karussell.jpg', '#stage');
    await page.click('#pActions [data-action="bell"]');
    await page.keyboard.press('Escape');
    check('Escape ends the ride', (await state(page, 'riding')) === null);

    await page.click('#snow');
    check('snow on', (await state(page, 'snow')) === true && (await page.getAttribute('#snow', 'aria-pressed')) === 'true');
    await page.click('#snow');
    check('snow off', (await state(page, 'snow')) === false);
    await page.click('#reset');
    check('reset view closes the panel', (await state(page, 'panel')) === null);

    // keyboard
    await page.focus('canvas');
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('3');
    check('key 3 opens the Bratwurst stand', (await state(page, 'panel')) === 'wurst');
    check('focus moves into the panel', await page.evaluate(() => document.getElementById('panel').contains(document.activeElement)));
    await page.keyboard.press('Escape');
    check('Escape closes the panel', (await state(page, 'panel')) === null);
    await page.focus('#places button[data-place="books"]');
    await page.keyboard.press('Enter');
    check('Enter on a place button opens it', (await state(page, 'panel')) === 'books');
    await page.keyboard.press('Escape');

    // a click in the 3D view on the Bierstand
    await page.click('#reset');
    await frames(page, 40);
    const hit = await page.evaluate(() => {
      const m = window.__market;
      const V = m.camera.position.constructor;
      const p = new V(7.4, 1.4, -1.4).project(m.camera);
      const r = m.renderer.domElement.getBoundingClientRect();
      return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height };
    });
    await page.mouse.move(hit.x, hit.y);
    await frames(page, 3);
    const tip = await page.locator('.tip').isVisible();
    await page.mouse.click(hit.x, hit.y);
    check('hover shows the place tooltip', tip);
    check('clicking a stall in 3D opens its panel', (await state(page, 'panel')) === 'bier', await state(page, 'panel'));
    await ctx.close();
  }

  if (run('lite')) {
    log('lite market, auto-detected');
    const { ctx, page } = await openPage(`${BASE}?snow=0`);
    let bytes = 0;
    page.on('response', async (r) => { try { bytes += (await r.body()).length; } catch { /* aborted */ } });
    await waitReady(page);
    const atReady = bytes;
    const report = await page.evaluate(() => window.__market.report);
    log(`lite: ${(atReady / 1e6).toFixed(2)} MB downloaded when the market opens`);
    check('lite: under 8.5 MB (code, fonts and models) before the market opens', atReady < 8.5e6, `${(atReady / 1e6).toFixed(2)} MB`);
    const sections = ['gluehwein', 'bierstand', 'bratwurst', 'buecherstand'];
    check('lite: each of the four section stalls has one of the four lights', sections.every((id) => report.lights.places.filter((p) => p === id).length === 1), report.lights.places.join(' '));
    console.log('lite scene', JSON.stringify(report.scene), JSON.stringify(report.lights));
    check('lite market detected on a weak GPU', report.quality.lite === true, report.quality.reasons.join('; '));
    check('lite: no shadows', await page.evaluate(() => window.__market.renderer.shadowMap.enabled === false));
    check('lite: fewer lights', report.lights.realtime <= 4, JSON.stringify(report.lights));
    await frames(page, 4);
    await shot(page, 'home_lite_stage.jpg', '#stage');
    await ctx.close();
  }

  if (run('phone')) {
    log('phone, reduced motion');
    const { ctx, page } = await openPage(`${BASE}?snow=1`, { reducedMotion: 'reduce', viewport: { width: 390, height: 844 } });
    await waitReady(page);
    check('lite market on a phone-sized screen', (await page.evaluate(() => window.__market.report.quality.lite)) === true);
    const cam0 = await page.evaluate(() => window.__market.camera.position.toArray());
    await frames(page, 6);
    const cam1 = await page.evaluate(() => window.__market.camera.position.toArray());
    check('reduced motion: no auto-rotate', cam0.every((v, i) => Math.abs(v - cam1[i]) < 1e-3));
    await page.evaluate(() => window.__market.settled());
    await page.click('#places button[data-place="carousel"]');
    await frames(page, 1);
    check('reduced motion: flights are instant', (await page.evaluate(() => window.__market.camera.position.distanceTo({ x: 19, y: 2.5, z: -12 }))) < 20);
    await frames(page, 3);
    const sheet = await page.evaluate(() => {
      const p = document.getElementById('panel').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect();
      return { panel: p.height / innerHeight, visible: (Math.min(p.top, s.bottom) - Math.max(0, s.top)) / innerHeight };
    });
    check('phone: the bottom sheet takes at most 60% of the screen', sheet.panel <= 0.6, JSON.stringify(sheet));
    check('phone: part of the market stays in view above the sheet', sheet.visible >= 0.3, JSON.stringify(sheet));
    await shot(page, 'phone_reduced_motion.jpg', null, { keepScroll: true });
    await ctx.close();
  }

  if (run('plain')) {
    log('plain.html');
    const { ctx, page } = await openPage(`${BASE}plain.html`);
    const n = await page.locator('main section').count();
    check('plain.html has all seven sections', n === 7, `${n} sections`);
    check('plain.html links back to the market', (await page.locator('a[href="./"]').count()) > 0);
    const credit = /Salamander[\s\S]*CC BY 3\.0[\s\S]*MusyngKite[\s\S]*CC BY-SA 3\.0/;
    check('plain.html credits the music (Salamander CC BY, MusyngKite CC BY-SA)', credit.test(await page.textContent('#credits')), await page.textContent('#credits'));
    await shot(page, 'plain_html.jpg');
    await ctx.close();
    const { ctx: c2, page: p2 } = await openPage(`${BASE}?quality=lite`);
    check('the 3D page links to plain.html', (await p2.locator('a[href="plain.html"]').count()) > 0);
    check('the 3D page credits the music in its footer', credit.test(await p2.textContent('footer #credits')), await p2.textContent('footer #credits'));
    check('the credit links the licences', (await p2.locator('#credits a[href*="creativecommons.org/licenses/by-sa/3.0"]').count()) > 0);
    await c2.close();
  }

  if (run('missing')) {
    log('every model missing and layout.json ignored: the BUILD.md layout with labelled stand-ins');
    const { ctx, page } = await openPage(`${BASE}?quality=lite&snow=0&missing=all&layout=builtin`, { viewport: { width: 960, height: 640 } });
    await waitReady(page);
    const report = await page.evaluate(() => window.__market.report);
    check('missing glbs: every place is a stand-in', report.models.every((m) => m.source === 'standin'), JSON.stringify(report.models.filter((m) => m.source !== 'standin')));
    check('missing layout.json: the BUILD.md layout', report.layout === 'BUILD.md fallback', report.layout);
    await page.click('#places button[data-place="glueh"]');
    await page.click('#pActions [data-action="pour"]');
    check('stand-ins keep the actions working', /poured tonight: 1/.test(await note(page)), await note(page));
    await frames(page, 2);
    await shot(page, 'missing_models_standins.jpg', '#stage');
    await ctx.close();
    const { ctx: c2, page: p2 } = await openPage(`${BASE}?quality=lite&snow=0&missing=stall_bier,ferris`, { viewport: { width: 960, height: 640 } });
    await waitReady(p2);
    await p2.evaluate(() => window.__market.settled());
    const r2 = await p2.evaluate(() => window.__market.report.models);
    check('two missing glbs: just those two are stand-ins', r2.filter((m) => m.source === 'standin').map((m) => m.id).sort().join() === 'bierstand,riesenrad', JSON.stringify(r2.filter((m) => m.source === 'standin')));
    await c2.close();
  }

  if (run('audio')) {
    log('recorded stems on the full market');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { viewport: { width: 800, height: 520 } });
    await waitReady(page);
    const mode = (await state(page, 'audio')).mode;
    if (mode !== 'stems') log('no audio manifest yet; the generative band plays instead');
    await page.evaluate(() => window.__market.togglePlay()); // full quality: no click (see the shots phase)
    await page.waitForFunction(() => /Pause|could not/.test(document.getElementById('play').textContent), null, { timeout: LONG });
    const first = (await state(page, 'audio')).phase;
    check('play starts at once', /Pause/.test(await page.textContent('#play')), first);
    if (mode === 'stems') {
      check('the mix bridges the wait for the stems', first === 'mix' || first === 'stems', first);
      // hold the picture while the stems decode: on SwiftShader every frame blocks the main thread for seconds
      await page.evaluate(() => window.__market.freeze(true));
      const ok = await page.waitForFunction(() => window.__market.audio.phase === 'stems', null, { timeout: 300000 }).then(() => true, () => false);
      await page.evaluate(() => window.__market.freeze(false));
      check('the stems take over from the mix', ok, (await state(page, 'audio')).phase);
      await page.evaluate(() => window.__market.act('band', 'sax'));
      await frames(page, 20);
      const lv = (await state(page, 'audio')).levels;
      check('stem levels reach the stage', Object.values(lv).some((v) => v > 0.01), JSON.stringify(lv));
    }
    await page.evaluate(() => window.__market.togglePlay()); // full quality: no click (see the shots phase)
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
