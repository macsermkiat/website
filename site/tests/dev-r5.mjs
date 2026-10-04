// A quick look at the round-5 market (development aid): opens the built site, prints console errors and the
// stroll/reading state, and takes the screenshots named on the command line.
// Usage: node tests/dev-r5.mjs <outdir> [steps...]   steps: home | walk:<id> | read[:<piece>] | page | close | wait:<s> | shot:<name> | eval:<js>
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const [outDir, ...steps] = process.argv.slice(2);
const OUT = path.resolve(outDir || '.');
mkdirSync(OUT, { recursive: true });
const PORT = +(process.env.PORT || 4521);
const QS = process.env.QS || '?quality=full';
const VW = +(process.env.VW || 1280), VH = +(process.env.VH || 760);
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => { const t = setTimeout(() => rej(new Error('preview did not start')), 30000); server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } }); });
process.on('exit', () => server.kill());
process.on('uncaughtException', (e) => { console.error(e); server.kill(); process.exit(1); });
process.on('unhandledRejection', (e) => { console.error(e); server.kill(); process.exit(1); });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 1, reducedMotion: process.env.RM ? 'reduce' : 'no-preference', ...(process.env.TOUCH ? { hasTouch: true, isMobile: true } : {}) });
const page = await ctx.newPage();
page.setDefaultTimeout(600000);
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || (process.env.VERBOSE && m.type() === 'warning')) { errors.push(m.text()); console.log('console', m.type(), m.text().slice(0, 300)); } });
page.on('pageerror', (e) => { errors.push(e.message); console.log('pageerror', e.message, e.stack?.slice(0, 600)); });
page.on('response', (r) => { if (r.status() >= 400) { errors.push(`HTTP ${r.status()} ${r.url()}`); console.log('HTTP', r.status(), r.url()); } });
const t0 = Date.now();
await page.goto(`http://localhost:${PORT}/website/${QS}`, { waitUntil: 'load' });
await page.waitForFunction(() => document.documentElement.dataset.ready === 'true' || /could not/.test(document.getElementById('loadingText')?.textContent || ''), null, { timeout: 600000 });
console.log('ready', ((Date.now() - t0) / 1000).toFixed(1), 's', await page.evaluate(() => document.getElementById('loadingText').textContent));
const settle = async (max = 120) => { for (let i = 0; i < max; i++) { const s = await page.evaluate(() => window.__market?.cam()); if (s && !s.moving) return s; await page.waitForTimeout(500); } return null; };
for (const st of steps) {
  const [k, ...rest] = st.split(':');
  const arg = rest.join(':');
  const t = Date.now();
  if (k === 'home') await page.evaluate(() => window.__market.home());
  else if (k === 'walk') await page.evaluate((id) => window.__market.walkTo(id), arg);
  else if (k === 'read') await page.evaluate((id) => window.__market.read(id || undefined), arg);
  else if (k === 'page') await page.evaluate(() => window.__market.readPage(1));
  else if (k === 'close') await page.evaluate(() => window.__market.closeRead());
  else if (k === 'wait') await page.waitForTimeout(+arg * 1000);
  else if (k === 'settle') { await page.evaluate(() => { for (let i = 0; i < 40 && window.__market.cam().moving; i++) window.__market.advance(0.5); window.__market.advance(0.8); }); console.log('settled', JSON.stringify(await page.evaluate(() => window.__market.cam()))); }
  else if (k === 'adv') await page.evaluate((s) => window.__market.advance(s), +arg);
  else if (k === 'snap') { const url = await page.evaluate(() => window.__market.snapshot()); writeFileSync(path.join(OUT, arg.endsWith('.jpg') ? arg : `${arg}.jpg`), Buffer.from(url.split(',')[1], 'base64')); }
  else if (k === 'eval') console.log('eval', String(JSON.stringify(await page.evaluate(arg))).slice(0, 3000));
  else if (k === 'shot') { await page.evaluate(() => window.__market?.freeze(true)); await page.screenshot({ path: path.join(OUT, arg.endsWith('.jpg') ? arg : `${arg}.jpg`), type: 'jpeg', quality: 85, timeout: 900000 }); await page.evaluate(() => window.__market?.freeze(false)); }
  else if (k === 'shotcanvas') { await page.evaluate(() => window.__market?.freeze(true)); await page.locator('#stage canvas').screenshot({ path: path.join(OUT, arg), quality: 80, type: arg.endsWith('.png') ? 'png' : 'jpeg', timeout: 900000 }); await page.evaluate(() => window.__market?.freeze(false)); }
  console.log(st, `${((Date.now() - t) / 1000).toFixed(1)}s`);
}
console.log('errors', errors.length);
await browser.close();
server.kill();
