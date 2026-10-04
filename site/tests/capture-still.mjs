// Recapture the home still (public/stills/home.webp) from the built site: the full market's home view at the
// 1280 x 760 window the still was made for, once everything after the first frame is in. Run it after a lighting
// or layout change (npm run build && npm run still && npm run build), or the fade into the live market jumps.
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import path from 'node:path';
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const SITE = path.resolve(import.meta.dirname, '..');
const OUT = path.join(SITE, 'public', 'stills', 'home.webp');
const PORT = +(process.env.PORT || 4531);
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort'], { cwd: SITE, stdio: ['ignore', 'pipe', 'pipe'] });
const stop = () => { try { server.kill(); } catch { /* gone */ } };
process.on('exit', stop);
try {
  await new Promise((res, rej) => { const t = setTimeout(() => rej(new Error('preview did not start')), 30000); server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } }); });
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 760 }, deviceScaleFactor: 1 })).newPage();
  page.setDefaultTimeout(1800000);
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://localhost:${PORT}/website/?quality=full&snow=0`, { waitUntil: 'load' });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 1800000 });
  await page.evaluate(() => window.__market.settled());
  await page.evaluate(() => window.__market.streamReady());
  await page.evaluate(() => { window.__market.home(); window.__market.freeze(true); window.__market.advance(6); });
  const url = await page.evaluate(() => window.__market.snapshot('image/webp', 0.8));
  writeFileSync(OUT, Buffer.from(url.split(',')[1], 'base64'));
  console.log(`home still: ${OUT} (${Math.round(Buffer.byteLength(url.split(',')[1], 'base64') / 1024)} KB)${errors.length ? `; console errors: ${errors.join(' | ')}` : ''}`);
  await browser.close();
} finally { stop(); }
