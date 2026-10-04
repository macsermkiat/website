// Vendor check shots in the real engine (three.js, software GL): a stall's goods close up, as a visitor sees
// them. Runs the site's vite dev server (models straight from site/public/models, nothing is built or
// written into site/), opens a place, flies to an item without clicking it, and saves a JPEG.
//
//   node blender/props/shoot_items.mjs --out review/round-4/vendor \
//        --shots bier:act_glass_4:three_pints.jpg[,deco-lebkuchen:act_heart_3:three_lebkuchen.jpg] [--query quality=full]
//        [--dist /scratch/dist [--build]]
//
// A shot is <place id>:<act_ node to fly to>:<file name>[:click]. Deco stalls open with openDeco(<id>).
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE = path.resolve(HERE, '../../site');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '.'));
const W = +opt('--w', 1280), H = +opt('--h', 720);
const shots = opt('--shots', 'bier:act_glass_4:three_pints.jpg').split(',').map((s) => s.split(':'));
const PORT = +opt('--port', 4397);

// --dist <dir>: serve a production build in <dir> (made with --build, or patched by hand) with vite preview,
// so rebuilding a glb in site/public mid-run cannot reload the page (the dev server's HMR does)
const DIST = opt('--dist', null) && path.resolve(opt('--dist'));
if (DIST && args.includes('--build')) {
  const b = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'build', '--outDir', DIST, '--emptyOutDir'],
    { cwd: SITE, stdio: 'inherit' });
  await new Promise((res, rej) => b.on('exit', (c) => (c ? rej(new Error(`vite build exited ${c}`)) : res())));
}
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', ...(DIST ? ['preview', '--outDir', DIST] : []),
  '--port', String(PORT), '--strictPort'], { cwd: SITE, stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  server.stdout.on('data', (d) => String(d).includes('localhost') && res());
  server.on('exit', (c) => rej(new Error(`vite exited ${c}`)));
});
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const errors = [];
try {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(1200000);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/website/?snow=0&${opt('--query', 'quality=full')}`, { timeout: 1200000 });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 1200000 });
  const M = (fn, a) => page.evaluate(fn, a);
  await M(() => window.__market.freeze(true));
  await M(() => window.__market.settled());
  for (const [place, node, file, click] of shots) {
    await M(([p, n, c]) => {
      const m = window.__market;
      if (p.startsWith('deco-')) m.openDeco(p); else m.openPlace(p);
      m.advance(2.5);
      if (n && n !== '-') { m.focusOn(n); m.advance(2.0); }
      // "click": click the item as a visitor would (a deco item shows its paper tag) and let it settle
      if (c === 'click') { m.clickItem(n); m.advance(1.8); }
      // hide the panel so the goods fill the frame
      for (const el of document.querySelectorAll('#panel, .panel, aside')) el.style.visibility = 'hidden';
    }, [place, node, click]);
    console.log(place, node, JSON.stringify(await M((n) => window.__market.item(n), node)));
    await M(() => window.__market.renderFrame());
    await page.screenshot({ path: path.join(OUT, file), type: 'jpeg', quality: 85 });
    console.log('shot', file);
    await M(() => window.__market?.resetView());
  }
  await ctx.close();
} finally {
  await browser.close();
  server.kill();
  console.log(errors.length ? 'ERRORS\n' + errors.join('\n') : 'no console errors');
}
