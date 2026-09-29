// Diagnostics of the real market with this lighting module (not part of the site build):
// dumps the placed warm lights and local glows, and optionally screenshots views of places.
//   cd site && node src/lighting/diag-market.mjs [--q "quality=full&snow=0"] [--out dir] [--places gluehwein,bierstand]
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(opt('--out', '../review/round-1/lighting/raw'));
const Q = opt('--q', 'quality=full&snow=0');
const PLACES = (opt('--places', '') || '').split(',').filter(Boolean);
const PORT = +opt('--port', 4394);
mkdirSync(OUT, { recursive: true });
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--config', 'src/lighting/vite.market.config.js', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite did not start')), 60000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.on('exit', (c) => rej(new Error('vite exited ' + c)));
});
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(900000);
  page.on('console', (m) => { const t = m.text(); if (m.type() === 'error' || /lighting/i.test(t)) console.log(`  ${m.type()}: ${t.slice(0, 300)}`); });
  page.on('pageerror', (e) => console.log(`  pageerror: ${e.message}`));
  await page.goto(`http://localhost:${PORT}/website/?${Q}`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__market?.ready && window.__lighting, null, { timeout: 900000 });
  // let the lighting run past frame 5 (captures, probes, the moon-caster trim)
  await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 7 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
  const dump = await page.evaluate(() => {
    const L = window.__lighting, scene = window.__market.scene;
    const holder = (o) => { while (o.parent && !o.parent.isScene) o = o.parent; return o; };
    const v = (p) => p.toArray().map((x) => +x.toFixed(2));
    const lights = [];
    scene.traverse((o) => {
      if (!(o.isPointLight || o.isSpotLight)) return;
      const h = holder(o);
      lights.push({ name: o.name, type: o.type, holder: h.userData.entry?.id || h.name, kind: o.userData.lightingKind, i: +o.intensity.toFixed(1), d: o.distance, shadow: o.castShadow, unsh: !!o.userData.unshadowed, front: !!o.userData.front, pos: v(o.getWorldPosition(new o.position.constructor())) });
    });
    const pools = scene.children.filter((o) => /^pool_/.test(o.name)).map((o) => o.name);
    const glows = L.shading.glows.map((g) => ({ tag: g.tag, a: v(g.a), b: v(g.b), i: g.intensity, r: g.reach, how: g.how, floor: g.floor, ceiling: g.ceiling }));
    const slots = Array.from(L.shading.data.slice(0, 4));
    const blockers = [];
    scene.traverse((o) => { if (o.name === 'lighting_shadow_blocker') blockers.push({ holder: holder(o).userData.entry?.id, shell: o.userData.shell }); });
    let casters = 0, meshes = 0, tiny = 0;
    scene.traverseVisible((o) => { if (!o.isMesh) return; meshes++; if (o.castShadow) { casters++; if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere(); const s = o.getWorldScale(new o.position.constructor()); if (o.geometry.boundingSphere.radius * Math.max(s.x, s.y, s.z) < 0.25 && !o.isInstancedMesh) tiny++; } });
    return { slots, blockers, report: window.__market.report?.lights, lighting: window.__market.report?.lighting, lights, pools, glows, casters, meshes, tiny, stats: L.stats() };
  });
  // draw calls of each of 6 frames (the moon shadow is redrawn on every 3rd)
  dump.calls = await page.evaluate(() => new Promise((r) => {
    const R = window.__market.renderer, out = [];
    R.info.autoReset = false;
    let n = 0;
    const f = () => { if (n > 0) out.push(R.info.render.calls); R.info.reset(); if (++n > 6) { R.info.autoReset = true; r(out); } else requestAnimationFrame(f); };
    requestAnimationFrame(f);
  }));
  writeFileSync(path.join(OUT, 'diag.json'), JSON.stringify(dump, null, 1));
  console.log(JSON.stringify({ calls: dump.calls, slotsUsed: dump.slots[0], blockers: dump.blockers, lights: dump.lights.length, pools: dump.pools.length, glows: dump.glows.length, casters: dump.casters, meshes: dump.meshes, tiny: dump.tiny }));
  for (const id of PLACES) {
    await page.evaluate((id) => window.__market.openPlace(id), id);
    await page.evaluate(() => window.__market.advance(4));
    await page.waitForTimeout(3000);
    await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 3 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
    await page.screenshot({ path: path.join(OUT, `place_${id}.png`), timeout: 900000 });
    console.log('shot', id);
  }
} finally {
  await browser.close();
  server.kill();
}
