// Quick single view for iterating on one place: node tests/shoot-one.mjs --place books --act book --out file.jpg [--query quality=lite]
// Serves dist/ with vite preview, opens the market with reduced motion, opens a place, runs its actions, shoots.
import { spawn } from 'node:child_process';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const PORT = +opt('--port', 4391);
const place = opt('--place', 'books');
const acts = opt('--act', '').split(',').filter(Boolean);
const out = path.resolve(opt('--out', 'shot.jpg'));
const query = opt('--query', 'quality=full');
const W = +opt('--w', 1280), H = +opt('--h', 860);

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort', ...(opt('--dist') ? ['--outDir', path.resolve(opt('--dist'))] : [])], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res) => server.stdout.on('data', (d) => String(d).includes('localhost') && res()));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const errors = [];
try {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, reducedMotion: 'reduce', deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(900000);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/website/?snow=0&${query}`, { timeout: 900000 });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 900000 });
  if (opt('--settle', '1') === '1') { await page.evaluate(() => window.__market.freeze(true)); await page.evaluate(() => window.__market.settled?.()); await page.evaluate(() => window.__market.freeze(false)); }
  await page.evaluate(([p, a]) => { window.__market.openPlace(p); for (const k of a) window.__market.act(p, k); }, [place, acts]);
  await page.evaluate((n) => new Promise((res) => { let k = 0; const f = () => (++k >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); }), +opt('--frames', 3));
  if (opt('--eval')) console.log(JSON.stringify(await page.evaluate(opt('--eval'))));
  await page.evaluate(() => window.__market.freeze(true));
  await page.screenshot({ path: out, type: 'jpeg', quality: 86, timeout: 900000 });
  console.log('shot', out);
} finally {
  console.log('errors', errors.length, errors.slice(0, 5).join(' | '));
  await browser.close();
  server.kill();
}
