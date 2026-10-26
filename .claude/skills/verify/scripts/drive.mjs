#!/usr/bin/env node
// Drive the market a visitor's way and keep the evidence.
// Usage: node .claude/skills/verify/scripts/drive.mjs <journey> [--port 4417] [--quality lite|full] [--size 1280x760]
//        [--reduced-motion] [--touch] [--real-time]
// <journey> is a file in .claude/skills/verify/journeys/ (without .mjs) or a path to one. It exports
// `default async (h) => {}` and uses the helpers below. Evidence goes to .verify/evidence/<time>-<journey>/:
// screenshots, result.json (checks, console errors, failed requests) and a log. Exit 1 if any check fails or
// the page logged an error.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const flag = (k) => args.includes(k);
const name = args[0];
if (!name || name.startsWith('--')) { console.error('usage: drive.mjs <journey> [--port 4417] [--quality lite|full] [--size WxH] [--reduced-motion] [--touch]'); process.exit(2); }
const journeyFile = existsSync(name) ? path.resolve(name) : path.join(HERE, '../journeys', `${name}.mjs`);
const PORT = +opt('--port', 4417);
const QUALITY = opt('--quality', 'lite');
const [W, H] = opt('--size', '1280x760').split('x').map(Number);
const BASE = `http://localhost:${PORT}/website/`;
const REAL = flag('--real-time');
const LONG = 240000; // software GL (SwiftShader) can take minutes for the full market

let pw;
try { pw = createRequire(path.join(ROOT, 'site/package.json'))('playwright'); } catch {
  pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs').catch(() => { console.error('playwright not found: cd site && npm i --no-save playwright && npx playwright install chromium'); process.exit(2); });
}
const { chromium } = pw.default || pw;

const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const OUT = path.join(ROOT, '.verify/evidence', `${stamp}-${path.basename(journeyFile, '.mjs')}`);
mkdirSync(OUT, { recursive: true });
const lines = [];
const log = (...a) => { const s = a.join(' '); lines.push(s); console.log('·', s); };
const checks = [];
const check = (what, ok, detail = '') => { checks.push({ what, ok: !!ok, detail: String(detail).slice(0, 400) }); console.log(ok ? '  ok  ' : '  FAIL', what, detail ? `(${String(detail).slice(0, 160)})` : ''); return !!ok; };
const errors = [];

const browser = await chromium.launch({
  // software GL: works without a GPU (cloud containers); on a Mac with a GPU it still works, only slower
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const ctx = await browser.newContext({
  viewport: { width: W, height: H }, deviceScaleFactor: 1,
  reducedMotion: flag('--reduced-motion') ? 'reduce' : 'no-preference',
  ...(flag('--touch') ? { hasTouch: true, isMobile: true } : {}),
});
const page = await ctx.newPage();
page.setDefaultTimeout(LONG);
page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
page.on('requestfailed', (r) => { const f = r.failure()?.errorText || ''; if (!(/ERR_ABORTED/.test(f) && /\.(mp3|ogg|m4a|opus|webm)$/.test(r.url()))) errors.push(`request failed: ${r.url()} ${f}`); });
page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`); });

const m = (fn, arg) => page.evaluate(fn, arg);
let shots = 0;
const h = {
  page, base: BASE, out: OUT, log, check, errors, quality: QUALITY,
  /** Open the market (or plain.html) at this run's quality, snow off so frames stay cheap. */
  async open(extra = '', file = '') {
    const url = `${BASE}${file}?quality=${QUALITY}&snow=0${extra}`;
    log('open', url);
    await page.goto(url, { waitUntil: 'load', timeout: LONG });
    return url;
  },
  /** Wait until the market says it is usable: <html data-ready="true">, or fail with the loading text. */
  async waitReady() {
    const t0 = Date.now();
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true' || /could not/.test(document.getElementById('loadingText')?.textContent || ''), null, { timeout: LONG });
    const ok = await m(() => document.documentElement.dataset.ready === 'true');
    if (!ok) throw new Error('market did not start: ' + await page.textContent('#loadingText'));
    log(`market ready in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  },
  /**
   * Let market time pass. Software GL draws about one frame a second and each frame moves the clock at most 0.1 s,
   * so a 4 s walk would take minutes: with --real-time (a real GPU) it waits on the wall clock, otherwise it steps the
   * page's own clock (window.__market.advance). This moves time only; it never clicks, walks or acts for the visitor.
   */
  async pass(seconds) {
    if (REAL) await page.waitForTimeout(seconds * 1000);
    else await m((s) => window.__market.advance(s), seconds);
  },
  /** Let time pass until the walk ends: arrived at the stop and the camera at rest (at most 60 s of market time). */
  async waitArrived(id) {
    for (let t = 0; t < 60; t += 1) {
      if (await m((id) => window.__market.stop === id && window.__market.arrived, id)) return true;
      await h.pass(1);
    }
    throw new Error(`did not arrive at ${id}: stop=${await m(() => window.__market.stop)}`);
  },
  /** Wait for the screen-reader live region (#announce, the same words as the note over the counter) to match. */
  async waitAnnounce(re, seconds = 20) {
    const said = () => m((src) => new RegExp(src).test(document.getElementById('announce')?.textContent || ''), re.source);
    for (let t = 0; t < seconds; t += 0.5) { if (await said()) return true; await h.pass(0.5); }
    return said();
  },
  announced: () => page.textContent('#announce'),
  /** Click a stop-bar button the way a visitor does, opening the folded bar first on a small screen. */
  async tap(sel) {
    if (await m(() => document.getElementById('stopbar')?.classList.contains('folded'))) await page.click('#stopFold');
    await page.click(sel);
  },
  /** A screen point where a click lands on the named 3D item (act_*, write_*), or null. */
  aimAt: (item) => m((name) => {
    const st = document.getElementById('stage');
    const r = st.getBoundingClientRect();
    if (r.top < 0 || r.bottom > innerHeight) st.scrollIntoView({ block: 'nearest', behavior: 'instant' });
    const mk = window.__market, c = mk.screenPoint(name), canvas = st.querySelector('canvas');
    if (!c) return null;
    for (let rad = 0; rad <= 16; rad += 2) for (let a = 0; a < 12; a++) {
      const x = c.x + Math.cos(a * Math.PI / 6) * rad, y = c.y + Math.sin(a * Math.PI / 6) * rad;
      if (document.elementFromPoint(x, y) === canvas && mk.itemAt(x, y) === name) return { x, y };
    }
    return null;
  }, item),
  /** A real mouse click on a 3D item. Returns false when no clear pixel of it is on screen. */
  async click3D(item) {
    const p = await h.aimAt(item);
    if (!p) return false;
    await page.mouse.move(p.x, p.y);
    await page.mouse.click(p.x, p.y);
    return true;
  },
  /** Read-only state from the page's test handle (window.__market). Use it to observe, never to act. */
  state: (fn, arg) => m(fn, arg),
  /** Screenshot the whole page (DOM bar and note included) into the evidence folder. */
  async shot(label) {
    const file = path.join(OUT, `${String(++shots).padStart(2, '0')}-${label}.jpg`);
    await page.mouse.move(1, 1).catch(() => {});
    // draw the current state, hold it, then capture: a SwiftShader frame can take seconds
    const frozen = await m(() => { const k = window.__market; if (!k?.freeze) return false; k.renderFrame?.(); k.freeze(true); return true; });
    await page.screenshot({ path: file, type: 'jpeg', quality: 86, timeout: 900000 });
    if (frozen) await m(() => window.__market.freeze(false));
    log('screenshot', path.relative(ROOT, file));
    return file;
  },
};

let crashed = null;
try {
  const journey = (await import(pathToFileURL(journeyFile).href)).default;
  await journey(h);
} catch (e) { crashed = e; check('journey ran to the end', false, e.stack || e.message); }
check('no console errors, failed requests or HTTP errors', errors.length === 0, errors.slice(0, 5).join(' | '));
if (crashed) await h.shot('at-failure').catch(() => {});
await browser.close();
const result = { journey: path.basename(journeyFile, '.mjs'), base: BASE, quality: QUALITY, size: `${W}x${H}`, ok: checks.every((c) => c.ok), checks, errors, log: lines };
writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(result, null, 2));
console.log(`${result.ok ? 'PASS' : 'FAIL'}  evidence: ${path.relative(process.cwd(), OUT)}`);
process.exit(result.ok ? 0 : 1);
