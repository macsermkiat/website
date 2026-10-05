// Organizer round 8: browser (three.js) views of the busy deco lanes, from the stroll's own eye height.
//   node blender/people/shoot_lane.mjs <distDir> <outDir>
// Serves a Vite build (vite build --outDir <distDir>, so crowd.json is the current one) under Playwright with
// SwiftShader, at ?quality=full with the engine's default person LOD, steps the clips 3 s with advance(), then
// places the camera on the lane and draws one frame with __market.snapshot().
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const [dist, out] = process.argv.slice(2);
const PORT = 4474;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const ONLY = process.env.SHOTS ? process.env.SHOTS.split(',') : null;
const SHOTS_ALL = [
  // left deco lane, from the loop by the Kerzen looking north past Gebrannte Mandeln and Lebkuchen to the Riesenrad
  { name: 'browser_lane_left.jpg', pos: [-18.0, 1.7, 13.5], look: [-20.6, 1.25, -1.5], fov: 52 },
  // back row, from the lane west of the tree looking west past Heisse Maroni and Crepes toward the Riesenrad
  { name: 'browser_back_row.jpg', pos: [3.0, 1.7, -18.6], look: [-11.0, 1.1, -21.5], fov: 55 },
];
const SHOTS = SHOTS_ALL.filter((s) => !ONLY || ONLY.includes(s.name));
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort', '--outDir', dist], { cwd: '/home/claude/website/site', stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res) => server.stdout.on('data', (d) => String(d).includes('localhost') && res()));
log('server up');
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const errors = [];
try {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(1800000);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/website/?snow=0&quality=full`, { timeout: 1800000 });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 1800000, polling: 2000 });
  log('ready');
  await page.evaluate(() => window.__market.freeze(true));
  await page.evaluate(() => window.__market.settled?.());
  await page.evaluate(() => window.__market.advance(3.0));
  const stats = await page.evaluate(() => {
    const m = window.__market;
    const ppl = m.people();
    return { people: ppl.length, vendors: ppl.filter((p) => p.vendor).map((p) => p.stall), crowd: m.crowd?.stats?.() || null };
  });
  fs.writeFileSync(path.join(out, 'browser_lane_info.json'), JSON.stringify(stats, null, 1));
  log('people', stats.people, 'vendors', stats.vendors.length);
  for (const s of SHOTS) {
    const url = await page.evaluate((s) => {
      const m = window.__market, { camera } = m;
      const p0 = camera.position.clone(), q0 = camera.quaternion.clone(), f0 = camera.fov;
      camera.position.set(...s.pos);
      camera.lookAt(...s.look);
      camera.fov = s.fov; camera.updateProjectionMatrix();
      m.advance?.(0.05);
      camera.position.set(...s.pos);
      camera.lookAt(...s.look);
      const u = m.snapshot('image/jpeg', 0.9);
      camera.position.copy(p0); camera.quaternion.copy(q0); camera.fov = f0; camera.updateProjectionMatrix();
      return u;
    }, s);
    fs.writeFileSync(path.join(out, s.name), Buffer.from(url.split(',')[1], 'base64'));
    log('saved', s.name);
  }
} finally {
  log('errors', errors.length, errors.slice(0, 5).join(' | '));
  await browser.close();
  server.kill();
}
