// Screenshots of the real market with this lighting module, through the site's own dev server
// (nothing is built or written into site/dist).
//   cd site && node src/lighting/shoot-market.mjs [--out dir] [--w 1280 --h 720] [--q "quality=full&snow=0"]
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-2/lighting/raw'));
const W = +opt('--w', 1280), H = +opt('--h', 720), PORT = +opt('--port', 4391);
const shots = {};
args.forEach((a, i) => { if (a === '--shot') { const [k, ...v] = args[i + 1].split('='); shots[k] = v.join('='); } });
if (!Object.keys(shots).length) Object.assign(shots, { market: 'quality=full&snow=0', market_snow: 'quality=full&snow=1', market_lite: 'quality=lite&snow=0' });
mkdirSync(OUT, { recursive: true });

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--config', 'src/lighting/vite.market.config.js', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite did not start')), 60000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.on('exit', (c) => rej(new Error('vite exited ' + c)));
});
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  for (const [name, qs] of Object.entries(shots)) {
    const t0 = Date.now();
    const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, reducedMotion: 'no-preference' });
    const page = await ctx.newPage();
    page.setDefaultTimeout(2400000);
    page.on('console', (m) => { const t = m.text(); if (m.type() === 'error' || /lighting|Lighting/.test(t)) console.log(`  [${name}] ${m.type()}: ${t.slice(0, 300)}`); });
    page.on('pageerror', (e) => console.log(`  [${name}] pageerror: ${e.message}`));
    // "query@open=glueh": enter a place after load (the flight is advanced without drawing)
    // "query@cam=x,y,z,tx,ty,tz": put the camera anywhere
    const [query, ...acts] = qs.split('@');
    await page.goto(`http://localhost:${PORT}/website/?${query}`, { waitUntil: 'load' });
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true' || /could not/.test(document.getElementById('loadingText')?.textContent || ''), null, { timeout: 2400000 });
    // the rides and the deco stalls arrive after the first frame: wait for them
    await page.evaluate(() => window.__market?.settled?.()).catch(() => {});
    await page.waitForTimeout(+opt('--settle', 8000));
    for (const a of acts) {
      const [k, v] = a.split('=');
      if (k === 'open') await page.evaluate((id) => { window.__market.openPlace(id); window.__market.advance(4); }, v);
      // "@cam=x,y,z,tx,ty,tz": any view (the lighting module's debugCamera; the round-1 module lacks it)
      if (k === 'cam') await page.evaluate((c) => { const n = c.split(',').map(Number); window.__lighting?.debugCamera?.(n.slice(0, 3), n.slice(3)); window.__market.advance(0.2); }, v);
    }
    // software GL draws the full market slowly: wait for a few real frames so the capture is current
    await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 2 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
    await page.waitForFunction(() => getComputedStyle(document.getElementById('loading')).opacity === '0' || document.getElementById('loading').classList.contains('done'));
    await page.waitForTimeout(3000);
    const rep = await page.evaluate(() => ({ lighting: window.__market?.report?.lighting, lights: window.__market?.report?.lights, warnings: window.__market?.report?.warnings, focus: window.__lighting?.focus, moves: window.__lighting?.focusMoves }));
    const file = path.join(OUT, `${name}.png`);
    // hold the last drawn frame, so the screenshot does not wait for another 20 s software-GL frame
    await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 2 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
    await page.evaluate(() => window.__market?.freeze?.(true));
    await page.screenshot({ path: file, timeout: 2400000 });
    console.log(`${name}: ${file} (${((Date.now() - t0) / 1000).toFixed(0)} s) ${JSON.stringify(rep).slice(0, 400)}`);
    await ctx.close();
  }
} finally {
  await browser.close();
  server.kill();
}
