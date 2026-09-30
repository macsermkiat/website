// Screenshots of the lighting test bench on software GL (Playwright + SwiftShader).
//   cd site && node src/lighting/shoot.mjs [--out ../review/round-1/lighting] [--only after,before,...]
// Starts the test-bench dev server itself. Writes PNGs; tools/compose (Python/PIL) makes the JPEGs.
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-2/lighting/raw'));
const ONLY = opt('--only', 'all');
const W = +opt('--w', 1280), H = +opt('--h', 720);
// --var name='?query' adds a one-off variant (tuning experiments)
const VARS = {};
args.forEach((a, i) => { if (a === '--var') { const [k, ...v] = args[i + 1].split('='); VARS[k] = v.join('='); } });
mkdirSync(OUT, { recursive: true });

const SHOTS = {
  after: '?shot=1',
  before: '?shot=1&mode=before',
  lite: '?shot=1&lite=1',
  snow: '?shot=1&snow=1&t=30',
  snow_lite: '?shot=1&snow=1&lite=1&t=30',
  wide: '?shot=1&view=wide',
  wide_snow: '?shot=1&view=wide&snow=1&t=30',
  sky: '?shot=1&view=sky',
  sky_lite: '?shot=1&view=sky&lite=1',
  capture: '?shot=1&capture=1',
};
Object.assign(SHOTS, VARS);
const only = Object.keys(VARS).length && ONLY === 'all' ? Object.keys(VARS) : null;

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--config', 'src/lighting/vite.test.config.js'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite did not start')), 30000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.stderr.on('data', (d) => process.stderr.write(d));
  server.on('exit', (c) => rej(new Error('vite exited ' + c)));
});

const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
try {
  for (const [name, qs] of Object.entries(SHOTS)) {
    if (only ? !only.includes(name) : ONLY !== 'all' && !ONLY.split(',').includes(name)) continue;
    const t0 = Date.now();
    const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.setDefaultTimeout(300000);
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log(`  [${name}] ${m.type()}: ${m.text().slice(0, 300)}`); });
    page.on('pageerror', (e) => console.log(`  [${name}] pageerror: ${e.message}`));
    await page.goto(`http://localhost:4390/src/lighting/test.html${qs}`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 300000 });
    await page.waitForTimeout(1500);
    const file = path.join(OUT, `${name}.png`);
    await page.screenshot({ path: file });
    const info = await page.evaluate(() => {
      const r = window.lighting?.composer?.renderer?.info?.render;
      return r ? { calls: r.calls, triangles: r.triangles } : null;
    });
    console.log(`${name}: ${file} (${((Date.now() - t0) / 1000).toFixed(1)} s) ${JSON.stringify(info)}`);
    await ctx.close();
  }
} finally {
  await browser.close();
  server.kill();
}
