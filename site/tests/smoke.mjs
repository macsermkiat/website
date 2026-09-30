// End-to-end smoke test: the built site served by `vite preview`, driven by Playwright on software GL.
// 0. unit checks (tests/unit.mjs): GPU classes and the ballad's road map
// 1. full market at 1280 px: home view, a stall panel, snow (screenshots); first-load size, deferred rides,
//    draw calls after the static merge, the second light pass
// 2. every panel action, both rides, snow, reset, keyboard and a click in 3D (small viewport, for speed)
// 3. lite market auto-detected on a weak GPU (first-paint download, deferred models); a phone with reduced motion
// 4. plain.html and the music credit on both pages
// 5. every model missing (and layout.json ignored): stand-ins, no errors
// Fails on any console error, failed request or HTTP error.
// 6. items: every book, glass, mug, bottle and sausage is its own clickable object; mid-animation screenshots,
//    node movement and book identity asserted
// Usage: npm run build && node tests/smoke.mjs [--out ../review/round-2/engineer] [--port 4317] [--only shots,items,interact,audio,lite,phone,plain,missing]
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-2/engineer'));
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
const note = (page) => page.textContent('#actNote');
/** Everything requested before the market opened (the page marks 'market-ready' just before its first frame). */
const bytesAtReady = (page) => page.evaluate(() => {
  const t = performance.getEntriesByName('market-ready')[0]?.startTime ?? Infinity;
  const doc = performance.getEntriesByType('navigation')[0];
  return (doc?.encodedBodySize || 0) + performance.getEntriesByType('resource').filter((r) => r.startTime < t).reduce((a, r) => a + (r.encodedBodySize || r.decodedBodySize || 0), 0);
});
const waitNote = (page, re) => page.waitForFunction((src) => new RegExp(src).test(document.getElementById('actNote')?.textContent || ''), re.source, { timeout: LONG }).then(() => true, () => false);
const state = (page, k) => page.evaluate((k) => window.__market[k], k);
/** A client point where a click would reach the named item (spiral search around its centre), or null. */
const aimAt = (page, name, via = name) => page.evaluate(([name, via]) => {
  const m = window.__market, c = m.screenPoint(via);
  if (!c) return null;
  for (let r = 0; r <= 16; r += 2) for (let a = 0; a < 12; a++) {
    const x = c.x + Math.cos(a * Math.PI / 6) * r, y = c.y + Math.sin(a * Math.PI / 6) * r;
    if (m.itemAt(x, y) === name) return { x, y };
  }
  return null;
}, [name, via]);
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
  if (run('unit')) {
    log('unit checks');
    const { execFileSync } = await import('node:child_process');
    let out = '', ok = true;
    try { out = execFileSync(process.execPath, ['tests/unit.mjs'], { encoding: 'utf8' }); } catch (e) { out = e.stdout || String(e); ok = false; }
    const lines = out.split('\n').filter((l) => /^\s+(ok|FAIL)/.test(l));
    for (const l of lines) check(l.replace(/^\s+(ok|FAIL)\s+/, 'unit: '), /^\s+ok/.test(l));
    if (!ok && !lines.some((l) => /FAIL/.test(l))) check('unit checks ran', false, out.slice(0, 200));
  }

  if (run('shots')) {
    log('full market, 1280 px (reduced motion, so flights land in one frame)');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`, { reducedMotion: 'reduce' });
    await waitReady(page);
    const report = await page.evaluate(() => window.__market.report);
    console.log(JSON.stringify(report).slice(0, 3000));
    console.log('full scene', JSON.stringify(report.scene));
    check('full market chosen with ?quality=full', report.quality.lite === false);
    const fullAtReady = await bytesAtReady(page);
    log(`full: ${(fullAtReady / 1e6).toFixed(2)} MB downloaded when the market opens`);
    check('full: under the 25 MB first-load aim (code, fonts and models)', fullAtReady < 25e6, `${(fullAtReady / 1e6).toFixed(2)} MB`);
    check('full: the rides and deco stalls wait until after the first frame', ['riesenrad', 'karussell'].every((id) => report.deferred.includes(id)) && report.deferred.length >= 11, report.deferred.join(' '));
    check('the frame-time governor runs on the full market', !!(await page.evaluate(() => window.__market.governor())));
    // the distance LOD for the crowd loads after the first frame; hold the picture so it is not stuck behind frames
    await page.evaluate(() => window.__market.freeze(true));
    const settled = await page.evaluate(() => window.__market.settled());
    await page.evaluate(() => window.__market.freeze(false));
    await frames(page, 2);
    const crowd = await page.evaluate(() => window.__market.crowd());
    const sceneNow = await page.evaluate(() => window.__market.sceneStats());
    console.log('full scene after LOD', JSON.stringify(sceneNow), JSON.stringify(crowd));
    check('crowd distance LOD: far people use their lite figure', settled.lod > 0 && crowd.lite > 0, JSON.stringify({ settled, crowd }));
    const after = await page.evaluate(() => window.__market.report);
    const lp = after.lights.places;
    check('full: the second light pass gives each ride its real light when it arrives', lp.includes('riesenrad') && lp.includes('karussell') && after.lights.realtime === 12, lp.join(' '));
    check('full: static meshes merged (fewer draw calls)', after.merges.after < after.merges.before * 0.75 && after.merges.row > 5 && after.merges.riders > 50, JSON.stringify(after.merges));
    check('full: under 800 meshes drawn in the home view', sceneNow.meshes < 800, JSON.stringify(sceneNow));
    check('shelf goods merged into a few meshes (books, mugs, glasses, bottles)', report.books?.merged?.meshes > 0 && report.books.merged.books > 20, JSON.stringify(report.books));
    check('layout.json and props.json bindings all resolve exactly', (report.bindings || []).length === 0, JSON.stringify(report.bindings));
    const ic = report.items || {};
    check('clickable items found: books, glasses, mugs, bottles, sausages, rolls', ['books:book', 'bier:glass', 'glueh:mug', 'glueh:bottle', 'wurst:sausage', 'wurst:roll'].every((k) => ic[k] > 0), JSON.stringify(ic));
    await frames(page, 2);
    await shot(page, 'home_full.jpg');
    // Full quality on SwiftShader takes tens of seconds a frame, and clicks wait on frames to check the target.
    // So this phase drives the page through window.__market; the clicks themselves are tested on lite below.
    const go = (fn, ...a) => page.evaluate(fn, ...a);
    await go(() => { window.__market.openPlace('glueh'); window.__market.act('glueh', 'pour'); window.__market.act('glueh', 'prost'); });
    await frames(page, 3);
    const hidden = await page.evaluate(() => window.__market.hiddenPeople());
    check('Glühwein close-up: the vendor stays in view', !hidden.includes('vendor_gluehwein') && (await page.evaluate(() => window.__market.crowd().vendorsVisible)) === 4, hidden.join(' '));
    // nobody left in the picture stands on the line from the camera to the vendor's chest (checked here, not by the page)
    const shotInfo = await page.evaluate(() => ({ cam: window.__market.camera.position.toArray(), people: window.__market.people() }));
    const vendor = shotInfo.people.find((p) => p.name === 'vendor_gluehwein');
    const blockers = vendor ? shotInfo.people.filter((p) => p.visible && !p.vendor).filter((p) => {
      const a = shotInfo.cam, b = [vendor.pos[0], vendor.pos[1] + 1.25, vendor.pos[2]];
      const d = b.map((v, i) => v - a[i]), len2 = d.reduce((x, v) => x + v * v, 0);
      return [1.0, 1.55].some((h) => {
        const q = [p.pos[0], p.pos[1] + h, p.pos[2]];
        const t = d.reduce((x, v, i) => x + v * (q[i] - a[i]), 0) / len2;
        if (t < 0.05 || t > 0.95) return false;
        return Math.hypot(...q.map((v, i) => v - (a[i] + d[i] * t))) < 0.3;
      });
    }).map((p) => p.name) : ['no vendor'];
    check('Glühwein close-up: nobody in the picture stands between the camera and the vendor', blockers.length === 0, `blocking: ${blockers.join(' ')}; stepped aside: ${hidden.join(' ') || 'none needed'}`);
    await shot(page, 'panel_gluehwein.jpg');
    await go(() => { window.__market.openPlace('books'); window.__market.act('books', 'book'); });
    await frames(page, 3);
    // Mac's five spines are in clear view: nobody visible stands on the line from the camera to any of them
    const five = await page.evaluate(() => window.__market.featuredBooks().map((n) => ({ n, who: window.__market.blockers(n) })));
    check('Bücherstand view: all five of Mac\'s spines in clear view (the bookseller stands aside)', five.length === 5 && five.every((b) => !b.who.length), JSON.stringify(five));
    const out = await page.evaluate(() => window.__market.openedBook());
    check('the chosen book is open in front of the counter when the picture is taken', out?.name === five[0]?.n && out.state === 'open', `${JSON.stringify(out)} vs ${five[0]?.n}`);
    await shot(page, 'panel_buecherstand.jpg');
    await go(() => window.__market.resetView());
    await frames(page, 1);
    const tag = await page.evaluate(() => ({ open: window.__market.openedBook(), visible: window.__market.item(window.__market.featuredBooks()[0])?.visible }));
    check('reset view closes the open book and puts it back on the shelf', tag.open === null && tag.visible === true, JSON.stringify(tag));
    await go(() => { window.__market.openPlace('band'); window.__market.act('band', 'sax'); });
    await frames(page, 3);
    await shot(page, 'panel_bandstand.jpg');
    await go(() => { window.__market.resetView(); window.__market.setSnow(true); });
    await page.evaluate(() => window.__market.advance(4)); // let the snow settle in
    await frames(page, 2);
    await shot(page, 'home_full_snow.jpg', '#stage');
    await ctx.close();
  }

  if (run('items')) {
    // Mid-animation close-ups on the full market. The clock is driven by hand: freeze the picture, run the
    // market forward with advance(), draw one frame, take it. Software GL needs tens of seconds per frame.
    log('items: every book, glass, mug, bottle and sausage, clicked one by one (full market, mid-animation)');
    const { ctx, page } = await openPage(`${BASE}?quality=full&snow=0`);
    await waitReady(page);
    const M = (fn, ...a) => page.evaluate(fn, ...a);
    await M(() => window.__market.freeze(true));
    await M(() => window.__market.settled());
    const pose = async (name, fn, arg) => { await M(fn, arg); await M(() => window.__market.renderFrame()); await shot(page, name); await M(() => window.__market.freeze(true)); };
    const at = (n) => M((n) => window.__market.item(n), n);
    const moved = (a, b, eps = 0.01) => a.position.some((v, i) => Math.abs(v - b.position[i]) > eps) || a.quaternion.some((v, i) => Math.abs(v - b.quaternion[i]) > eps);

    // Glühwein: the ladle fills a mug
    await M(() => { window.__market.openPlace('glueh'); window.__market.advance(2.5); });
    const lad0 = await at('act_ladle');
    await M(() => { window.__market.focusOn('act_mug_2'); window.__market.advance(1.7); window.__market.clickItem('act_mug_2'); window.__market.advance(2.05); });
    const lad1 = await at('act_ladle');
    check('Glühwein: clicking a mug sends the ladle to it (the ladle node moves)', lad0 && lad1 && moved(lad0, lad1, 0.05), `${lad0?.position} -> ${lad1?.position}`);
    check('Glühwein: the note names that mug', /blue mug/i.test(await note(page)), await note(page));
    await pose('item_gluehwein_ladle.jpg', () => {});
    await M(() => window.__market.advance(3));
    check('Glühwein: the mug is full afterwards', (await M(() => window.__market.handlers.mugState('act_mug_2')))?.full === true);
    // a wine bottle turns to show its label, with a tasting note
    const b0 = await at('act_bottle_3');
    await M(() => { window.__market.focusOn('act_bottle_3'); window.__market.advance(1.7); window.__market.clickItem('act_bottle_3'); window.__market.advance(1.3); });
    const b1 = await at('act_bottle_3');
    check('Glühwein: clicking a wine bottle turns it out to show its label (the node moves)', moved(b0, b1), `${b0.position} -> ${b1.position}`);
    check('Glühwein: the bottle\'s own name and a tasting note', /Spätburgunder/.test(await note(page)) && /cherry|tannin/i.test(await note(page)), await note(page));
    await pose('item_gluehwein_bottle.jpg', () => {});
    await M(() => window.__market.resetView());

    // Bierstand: the tap pours into the clicked glass; two full glasses clink
    await M(() => { window.__market.openPlace('bier'); window.__market.advance(2.5); });
    const g0 = await at('act_glass_2');
    await M(() => { window.__market.focusOn('act_glass_2'); window.__market.advance(1.7); window.__market.clickItem('act_glass_2'); window.__market.advance(1.9); });
    const gs = await M(() => window.__market.handlers.glassState('act_glass_2'));
    const g1 = await at('act_glass_2');
    check('Bierstand: clicking a glass carries it to the tap (the node moves)', moved(g0, g1), `${g0.position} -> ${g1.position}`);
    check('Bierstand: mid-pour the beer is rising in that glass', gs && gs.level > 0.15 && gs.level < 0.98, JSON.stringify(gs));
    await pose('item_bier_pouring.jpg', () => {});
    await M(() => window.__market.advance(3));
    check('Bierstand: the glass ends full, with its head', (await M(() => window.__market.handlers.glassState('act_glass_2')))?.full === true);
    await M(() => { window.__market.focusOn('act_glass_0'); window.__market.advance(1.7); window.__market.clickItem('act_glass_0'); window.__market.advance(0.5); window.__market.clickItem('act_glass_2'); window.__market.advance(0.75); });
    check('Bierstand: two full glasses clicked in turn clink (Prost)', /Prost/.test(await note(page)), await note(page));
    await pose('item_bier_prost.jpg', () => {});
    await M(() => { window.__market.advance(2); window.__market.resetView(); });

    // Bratwurst: one sausage turns; a roll gets a sausage and mustard
    await M(() => { window.__market.openPlace('wurst'); window.__market.advance(2.5); });
    const s0 = await at('act_sausage_3');
    await M(() => { window.__market.focusOn('act_sausage_3'); window.__market.advance(1.7); window.__market.clickItem('act_sausage_3'); window.__market.advance(0.28); });
    const s1 = await at('act_sausage_3');
    check('Bratwurst: clicking a sausage turns that sausage (its node rotates)', moved(s0, s1, 0.05), `${s0.quaternion} -> ${s1.quaternion}`);
    const other = await at('act_sausage_4');
    check('Bratwurst: its neighbour stays put', !moved(await at('act_sausage_4'), other));
    await pose('item_wurst_turning.jpg', () => {});
    await M(() => { window.__market.focusOn('act_roll_1'); window.__market.advance(1.7); window.__market.clickItem('act_roll_1'); window.__market.advance(1.4); });
    check('Bratwurst: clicking a roll puts a sausage in it, with mustard', (await M(() => window.__market.handlers.bunCount())) === 1);
    await pose('item_wurst_bun.jpg', () => window.__market.advance(0.3));
    await M(() => window.__market.resetView());

    // Bücherstand: a clicked book opens at the counter, showing its own title
    await M(() => { window.__market.openPlace('books'); window.__market.advance(2.5); });
    const five = await M(() => window.__market.featuredBooks());
    await M((n) => { window.__market.clickItem(n); window.__market.advance(1.55); }, five[1]);
    const mid = await M(() => window.__market.openedBook());
    check('Bücherstand: the clicked book is opening, and it is that book', mid?.name === five[1] && /Gödel/.test(mid.title), JSON.stringify(mid));
    await M(() => window.__market.advance(0.8));
    check('Bücherstand: the note gives its title and author', /Gödel/.test(await note(page)) && /Hofstadter/.test(await note(page)), await note(page));
    await pose('item_books_open.jpg', () => {});
    await M(() => window.__market.resetView());

    // a deco stall: fly to its close-up, hover an iced Lebkuchen heart
    await M(() => { window.__market.openDeco('deco-lebkuchen'); window.__market.advance(2.5); });
    const hearts = await M(() => Object.keys(window.__market.items()).filter((k) => k.startsWith('deco-lebkuchen')));
    check('Lebkuchen stall: its goods are items (iced hearts)', hearts.length > 0, JSON.stringify(await M(() => window.__market.items())));
    const h0 = await at('act_heart_1');
    await M(() => { window.__market.focusOn('act_heart_1'); window.__market.advance(1.7); window.__market.clickItem('act_heart_1'); });
    check('Lebkuchen heart: a click shows its icing text', /Für Dich/.test((await M(() => window.__market.handlers.decoDetail()))?.detail || ''), JSON.stringify(await M(() => window.__market.handlers.decoDetail())));
    await pose('item_deco_lebkuchen.jpg', () => window.__market.advance(0.3));
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
    await page.evaluate(() => window.__market.advance(4)); // the ladle's trip, without waiting on slow frames
    check('pour a mug (the ladle fills one of the stall\'s own mugs)', await waitNote(page, /poured tonight: 1/), await note(page));
    await page.click('#pActions [data-action="prost"]');
    await page.waitForSelector('.bubble', { timeout: 20000 }).catch(() => {});
    check('Prost: the crowd raises a glass', (await page.locator('.bubble').count()) > 0);

    await page.click('#places button[data-place="bier"]');
    await page.click('#pActions [data-action="pint"]');
    check('pull a pint (starts)', /Pouring/.test(await note(page)), await note(page));
    await page.evaluate(() => window.__market.advance(5)); // run the pour without waiting on slow frames
    check('pull a pint (finishes)', await waitNote(page, /pulled tonight: 1/), await note(page));
    await page.click('#pActions [data-action="prost"]');

    await page.click('#places button[data-place="wurst"]');
    await page.evaluate(() => window.__market.advance(2));
    const keyOn = await page.evaluate(() => window.__market.keyLight());
    check('lite: the close-up key light lights the Bratwurst counter front', keyOn?.place === 'wurst' && keyOn.intensity > 5, JSON.stringify(keyOn));
    await page.click('#pActions [data-action="turn"]');
    check('turn the sausages', /Turned|flare|Almost/.test(await note(page)), await note(page));
    await page.click('#pActions [data-action="bun"]');
    check('a sausage in a bun', /Brötchen/.test(await note(page)), await note(page));
    await page.evaluate(() => window.__market.advance(2.5));
    check('a sausage in a bun: one sits in a roll, with mustard', (await page.evaluate(() => window.__market.handlers.bunCount())) === 1);
    // a single sausage, clicked in 3D: aim at its pixels and click it
    const sAim = await aimAt(page, 'act_sausage_2');
    if (sAim) {
      const q0 = (await page.evaluate(() => window.__market.item('act_sausage_2'))).quaternion;
      await page.mouse.click(sAim.x, sAim.y);
      await page.evaluate(() => window.__market.advance(1));
      const q1 = (await page.evaluate(() => window.__market.item('act_sausage_2'))).quaternion;
      check('clicking one sausage in 3D turns that sausage (its node rotates)', q0.some((v, i) => Math.abs(v - q1[i]) > 0.05) && /turned/i.test(await note(page)), `${q0} -> ${q1}; ${await note(page)}`);
    } else check('clicking one sausage in 3D turns that sausage (its node rotates)', false, 'no clear pixel on act_sausage_2');

    await page.click('#places button[data-place="books"]');
    await page.click('#pActions [data-action="book"]');
    check('pull a book', /Rovelli|Hofstadter|Feynman|Seth|Pearl|·/.test(await note(page)), await note(page));
    // each of Mac's books sits on its own spine: aim at the second one and click it in 3D
    const spines = await page.evaluate(() => window.__market.featuredBooks());
    check('five named spines for the five books', spines.length === 5, spines.join(' '));
    await page.evaluate(() => window.__market.advance(4)); // finish the flight to the bookshop
    await frames(page, 2);
    await page.evaluate(() => window.__market.resetView());
    await page.click('#places button[data-place="books"]');
    await page.evaluate(() => window.__market.advance(4));
    await frames(page, 2);
    const aim = await aimAt(page, spines[1]);
    if (aim) {
      await page.mouse.move(aim.x, aim.y);
      await frames(page, 3);
      check('hovering a book lifts it and names it', (await page.evaluate(() => window.__market.hoveredItem)) === spines[1] && /Gödel/.test(await page.textContent('.tip')), await page.textContent('.tip'));
      await page.mouse.click(aim.x, aim.y);
      await page.evaluate(() => window.__market.advance(3));
      const ob = await page.evaluate(() => window.__market.openedBook());
      check('clicking a named spine opens that book, showing its own title', ob?.name === spines[1] && /Gödel/.test(ob.title) && /Hofstadter|Gödel/.test(await note(page)), `${JSON.stringify(ob)} ${await note(page)}`);
      const again = await aimAt(page, spines[1], `open_${spines[1]}`); // a click on the open book itself
      if (again) { await page.mouse.click(again.x, again.y); await page.evaluate(() => window.__market.advance(3)); }
      check('clicking the open book again puts it back', (await page.evaluate(() => window.__market.openedBook())) === null);
    } else check('clicking a named spine opens that book, showing its own title', false, `no clear pixel on ${spines[1]}`);
    // a book from the bookseller's stock names itself too (items.json)
    await page.evaluate(() => window.__market.clickItem('act_book_201'));
    await page.evaluate(() => window.__market.advance(3));
    const stock = await page.evaluate(() => window.__market.openedBook());
    check('a stock book opens with its own title and author (items.json)', stock?.title === 'Siddhartha' && /Hesse/.test(await note(page)), `${JSON.stringify(stock)} ${await note(page)}`);

    await page.click('#pClose');
    await page.evaluate(() => window.__market.advance(3));
    const tagOff = await page.evaluate(() => ({ open: window.__market.openedBook(), visible: window.__market.item('act_book_201').visible }));
    check('closing the panel closes the book and puts it back', tagOff.open === null && tagOff.visible, JSON.stringify(tagOff));

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
    const ex0 = await state(page, 'exposure');
    // up to the top: the wheel runs fast until the rider's gondola is at the top, then holds there
    const rise = await page.evaluate(() => { const m = window.__market; let t = 0; while (m.rideStage === 'rising' && t < 60) { m.advance(0.5); t += 0.5; } return { t, stage: m.rideStage, cam: m.camera.position.y }; });
    check('Riesenrad: the ride stops at the top for the view', rise.stage === 'top' && rise.cam > 14, JSON.stringify(rise));
    await page.evaluate(() => window.__market.advance(2));
    check('Riesenrad: the exposure opens up for the view from the top', (await state(page, 'exposure')) > ex0 * 1.3, `${ex0} -> ${await state(page, 'exposure')}`);
    check('Riesenrad: the panel says the rider is at the top', /top/i.test(await note(page)), await note(page));
    await frames(page, 3);
    await shot(page, 'ride_riesenrad.jpg', '#stage');
    await page.click('#pActions [data-action="off"]');
    check('get off the wheel', (await state(page, 'riding')) === null);
    await page.evaluate(() => window.__market.advance(4));
    check('the exposure comes back down on the ground', (await state(page, 'exposure')) < ex0 * 1.1, String(await state(page, 'exposure')));

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
    await page.evaluate(() => window.__market.advance(2));
    check('lite: the key light fades out at home', (await page.evaluate(() => window.__market.keyLight().intensity)) < 1);

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
    await waitReady(page);
    // everything requested before the market opened (the page marks 'market-ready' just before its first frame)
    const atReady = await bytesAtReady(page);
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
    check('phone: the home view comes in closer than the desktop one', cam0[2] < 25 && cam0[1] < 7, JSON.stringify(cam0));
    await frames(page, 3);
    await shot(page, 'phone_home.jpg', null, { keepScroll: true });
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
    // a tap works like a click on the goods (touch screens have no hover)
    const t = await openPage(`${BASE}?snow=0`, { reducedMotion: 'reduce', viewport: { width: 390, height: 844 }, touch: true });
    await waitReady(t.page);
    await t.page.click('#places button[data-place="wurst"]');
    await frames(t.page, 2);
    const tAim = await aimAt(t.page, 'act_sausage_5');
    if (tAim) {
      const q0 = (await t.page.evaluate(() => window.__market.item('act_sausage_5'))).quaternion;
      await t.page.touchscreen.tap(tAim.x, tAim.y);
      await frames(t.page, 2);
      const q1 = (await t.page.evaluate(() => window.__market.item('act_sausage_5'))).quaternion;
      check('phone: tapping a sausage turns it', q0.some((v, i) => Math.abs(v - q1[i]) > 0.05), `${q0} -> ${q1}`);
    } else check('phone: tapping a sausage turns it', false, 'no clear pixel on act_sausage_5');
    await t.ctx.close();
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
    check('plain.html carries the books the 3D shelf features', /Gödel, Escher, Bach/.test(await page.textContent('#books')), (await page.textContent('#books')).slice(0, 200));
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
    check('missing glbs are reported as bindings that did not resolve (nothing guessed)', report.bindings.length >= 10 && report.bindings.every((b) => /not in site\/public\/models|no asset/.test(b.problem)), JSON.stringify(report.bindings.slice(0, 3)));
    await page.click('#places button[data-place="glueh"]');
    await page.click('#pActions [data-action="pour"]');
    check('stand-ins keep the actions working', /poured tonight: 1/.test(await note(page)), await note(page));
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
      await page.evaluate(() => window.__market.advance(1.5)); // the analysers feed the levels on each step
      const lv = (await state(page, 'audio')).levels;
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
