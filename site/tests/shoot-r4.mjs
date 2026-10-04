// Round 4 check shots: the Bierstand panel, a pint mid-pour and Prost (framed with the tap, vendor and pint),
// and the bandstand at rest (the sax on its stand). node tests/shoot-r4.mjs --out ../review/round-4/engineer
import { spawn } from 'node:child_process';
import path from 'node:path';
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '.'));
const W = +opt('--w', 1280), H = +opt('--h', 860);
const only = opt('--only', 'bier,band');
const PORT = 4392;
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res) => server.stdout.on('data', (d) => String(d).includes('localhost') && res()));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const errors = [];
try {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(900000);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/website/?snow=0&${opt('--query', 'quality=full')}`, { timeout: 900000 });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 900000 });
  const M = (fn, a) => page.evaluate(fn, a);
  await M(() => window.__market.freeze(true));
  await M(() => window.__market.settled());
  const shot = async (name) => { await M(() => window.__market.renderFrame()); await page.screenshot({ path: path.join(OUT, name), type: 'jpeg', quality: 82 }); console.log('shot', name); };
  const tag = opt('--tag', '');
  if (only.includes('bier')) {
    await M(() => { window.__market.openPlace('bier'); window.__market.advance(2.5); });
    await shot(`panel_bier${tag}.jpg`);
    await M(() => { window.__market.focusOn('act_glass_2'); window.__market.advance(1.7); window.__market.clickItem('act_glass_2'); window.__market.advance(1.9); });
    await shot(`item_bier_pouring${tag}.jpg`);
    await M(() => window.__market.advance(3));
    await M(() => { window.__market.focusOn('act_glass_0'); window.__market.advance(1.7); window.__market.clickItem('act_glass_0'); window.__market.advance(4.5); window.__market.clickItem('act_glass_0'); window.__market.advance(0.3); window.__market.clickItem('act_glass_2'); window.__market.advance(0.75); });
    console.log('glass states', JSON.stringify(await M(() => [window.__market.handlers.glassState('act_glass_0'), window.__market.handlers.glassState('act_glass_2')])));
    await shot(`item_bier_prost${tag}.jpg`);
    await M(() => window.__market.resetView());
  }
  if (only.includes('band')) {
    await M(() => { window.__market.openPlace('band'); window.__market.advance(2.5); });
    console.log('sax at rest', JSON.stringify(await M(() => window.__market.saxStand())));
    await shot(`panel_bandstand_rest${tag}.jpg`);
  }
  await ctx.close();
} finally {
  await browser.close();
  server.kill();
  console.log(errors.length ? 'ERRORS\n' + errors.join('\n') : 'no console errors');
}
