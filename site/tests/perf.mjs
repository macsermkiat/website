// Frame time on a real GPU: the launch gate in NOTES.md. Run it on a machine with a graphics card (Mac's laptop),
// not on the build machine, whose software GL says nothing about real frame times.
//
//   cd site && npm ci && npm run build && npx playwright install chromium && npm run perf
//
// It serves dist/ with `vite preview`, opens the page in a visible Chromium window on the machine's own GPU with
// ?perf=tour, once for the full market and once for the lite one, and lets the ?perf tour visit its views (home,
// Glühwein, bandstand, Bücherstand, Riesenrad, home again) for a few seconds each. It prints one line per view and
// writes them all to review/perf/<date>.json. Exit code: 0 when every view meets its target, 1 when one misses,
// 2 when the browser drew on software GL (SwiftShader, llvmpipe), which is not a measurement.
//
// Round 8: each market's line also gives the first-load size (everything fetched before the market opened) and the
// crowd's cost: people, how many are drawn as far instances (the vertex-animation crowd beyond about 25 m), how many
// mixers ran or were throttled in the last frame, and the crowd's own update time per frame.
//
// Options: --market full,lite   --size 1440x900   --port 4319   --out ../review/perf   --headless (some GPUs only)
//          --software   run headless on SwiftShader (the build machine): sizes and crowd counts are real, frame times
//                       are not a GPU measurement (exit code 2 as always on software GL)
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const MARKETS = opt('--market', 'full,lite').split(',');
const [W, H] = opt('--size', '1440x900').split('x').map(Number);
const PORT = +opt('--port', 4319);
const OUT = path.resolve(opt('--out', '../review/perf'));
// Targets (ms). Full market on a laptop or desktop GPU: 60 fps median, no worse than 40 fps at the 95th percentile.
// Lite market (phones, integrated graphics): 30 fps median, 20 fps at the 95th percentile.
const TARGET = { full: { p50: 16.7, p95: 25 }, lite: { p50: 33.3, p95: 50 } };
const SOFTWARE = /swiftshader|llvmpipe|softpipe|software|basic render/i;

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite preview did not start (run npm run build first)')), 30000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.on('exit', (c) => rej(new Error('vite preview exited ' + c)));
});

const SOFT = args.includes('--software');
const browser = await chromium.launch(SOFT
  ? { headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }
  : { headless: args.includes('--headless'), args: ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--disable-frame-rate-limit', '--disable-gpu-vsync'] });
/** Everything requested before the market opened (the page marks 'market-ready' just before its first frame). */
const bytesAtReady = (page) => page.evaluate(() => {
  const t = performance.getEntriesByName('market-ready')[0]?.startTime ?? Infinity;
  const doc = performance.getEntriesByType('navigation')[0];
  return (doc?.encodedBodySize || 0) + performance.getEntriesByType('resource').filter((r) => r.startTime < t).reduce((a, r) => a + (r.encodedBodySize || r.decodedBodySize || 0), 0);
});
const report = { at: new Date().toISOString(), size: `${W}x${H}`, markets: {} };
let verdict = 0;
try {
  for (const market of MARKETS) {
    const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    const SLOW = SOFT ? 10 : 1; // software GL: minutes, not seconds
    await page.goto(`http://localhost:${PORT}/website/?perf=tour&quality=${market}&governor=0`, { waitUntil: 'load', timeout: 120000 * SLOW });
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 180000 * SLOW });
    const firstLoad = await bytesAtReady(page);
    const gpu = await page.evaluate(() => window.__market.perf()?.gpu || 'unknown');
    console.log(`\n${market} market on ${gpu}`);
    console.log(`  first load ${(firstLoad / 1e6).toFixed(2)} MB (fetched before the market opened)`);
    await page.waitForFunction(() => window.__market.perfTour(), null, { timeout: 240000 * SLOW, polling: 1000 });
    const tour = await page.evaluate(() => window.__market.perfTour());
    const t = TARGET[market] || TARGET.full;
    const stops = tour.lines.map((s) => ({ ...s, ok: s.p50 <= t.p50 && s.p95 <= t.p95 }));
    for (const s of stops) console.log(`  ${s.ok ? 'ok  ' : 'MISS'} ${s.view.padEnd(12)} median ${String(s.p50).padStart(5)} ms  p95 ${String(s.p95).padStart(5)} ms  ${s.calls} draws  ${(s.triangles / 1000).toFixed(0)}k tris`);
    const crowd = await page.evaluate(() => { const c = window.__market.crowd(); return { people: c.people, lodFar: c.lodFar, far: c.far, mixers: c.mixers, updateMs: c.updateMs }; });
    console.log(`  crowd ${crowd.people} people: ${crowd.far?.drawn ?? 0} drawn as far instances in ${crowd.far?.meshes ?? 0} draws (${crowd.far?.figures ?? 0} figures baked in ${crowd.far?.bakeMs ?? 0} ms); mixers ran ${crowd.mixers?.ran ?? '?'}, throttled ${crowd.mixers?.throttled ?? '?'}; crowd update ${crowd.updateMs ?? '?'} ms/frame`);
    const software = SOFTWARE.test(gpu);
    if (software) { console.log('  software GL: these numbers are not a GPU measurement'); verdict = 2; }
    else if (stops.some((s) => !s.ok) && verdict === 0) verdict = 1;
    report.markets[market] = { gpu, software, target: t, firstLoadBytes: firstLoad, crowd, stops, errors };
    await ctx.close();
  }
} finally {
  await browser.close();
  server.kill();
}
mkdirSync(OUT, { recursive: true });
const file = path.join(OUT, `${report.at.slice(0, 16).replace(/[:T]/g, '-')}.json`);
writeFileSync(file, JSON.stringify(report, null, 2));
console.log(`\n${verdict === 0 ? 'every view meets its target' : verdict === 1 ? 'a view misses its target' : 'not a real GPU'}; written to ${path.relative(process.cwd(), file)}`);
process.exit(verdict);
