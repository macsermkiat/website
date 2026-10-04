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
    // the loading overlay must be gone before a place is opened: the intro resets the view when it fades
    await page.waitForFunction(() => getComputedStyle(document.getElementById('loading')).opacity === '0' || document.getElementById('loading').classList.contains('done'));
    // "@snap=name" captures the current view mid-sequence, so one page load (most of a software-GL
    // full-market shot) gives several views: "quality=full&snow=0@snap=market@front=place_bratwurst,7.5,1.7@snap=sign_wurst"
    const snap = async (snapName) => {
      await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 2 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
      await page.waitForTimeout(3000);
      await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 2 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
      await page.evaluate(() => window.__market?.freeze?.(true));
      const f = path.join(OUT, `${snapName}.png`);
      await page.screenshot({ path: f, timeout: 2400000 });
      await page.evaluate(() => window.__market?.freeze?.(false));
      const rep = await page.evaluate(() => ({ lights: window.__market?.report?.lights?.realtime, warnings: window.__market?.report?.warnings, focus: window.__lighting?.focus }));
      console.log(`${snapName}: ${f} (${((Date.now() - t0) / 1000).toFixed(0)} s) ${JSON.stringify(rep)}`);
    };
    for (const a of acts) {
      const [k, v] = a.split('=');
      if (k === 'snap') { await snap(v); continue; }
      // "@home": hand the camera back to the engine and leave any place
      if (k === 'home') { await page.evaluate(() => { window.__lighting?.debugCamera?.(null); window.__lighting?.focusPlace?.(null); window.__market.resetView(); window.__market.advance(4); }); continue; }
      // the engine does not call focusPlace yet, and software GL draws too few frames for the camera-based
      // detection to fire before the capture: call it as the engine would from openPlace
      if (k === 'open') await page.evaluate((id) => { window.__market.openPlace(id); window.__market.advance(4); window.__lighting?.focusPlace?.(id); window.__market.advance(0.5); }, v);
      // "@cam=x,y,z,tx,ty,tz": any view (the lighting module's debugCamera; the round-1 module lacks it)
      // "@front=place_bratwurst,7.5,1.7": a visitor's approach, `dist` m in front of the model's slot_sign
      // (along the model's +Z) at eye height `h`, looking at the sign
      if (k === 'front') console.log('  front view', await page.evaluate((c) => {
        const [name, dist, h] = c.split(','); const L = window.__lighting;
        let scene = L.moonLight; while (scene.parent) scene = scene.parent;
        const root = scene.getObjectByName(name); const sign = root?.getObjectByName('slot_sign');
        if (!sign) return 'no ' + name;
        root.updateMatrixWorld(true);
        const p = sign.getWorldPosition(sign.position.clone()), q = root.getWorldQuaternion(root.quaternion.clone());
        const f = sign.position.clone().set(0, 0, 1).applyQuaternion(q).setY(0).normalize();
        const cam = [p.x + f.x * +dist, +h, p.z + f.z * +dist], tgt = [p.x, p.y - 0.5, p.z];
        L.debugCamera(cam, tgt); window.__market.advance(0.2);
        return JSON.stringify({ cam: cam.map((v) => +v.toFixed(2)), tgt: tgt.map((v) => +v.toFixed(2)) });
      }, v));
      if (k === 'cam') await page.evaluate((c) => { const n = c.split(',').map(Number); window.__lighting?.debugCamera?.(n.slice(0, 3), n.slice(3)); window.__market.advance(0.2); }, v);
    }
    // software GL draws the full market slowly: wait for a few real frames so the capture is current
    await page.evaluate(() => new Promise((r) => { let n = 0; const f = () => (++n >= 2 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); }));
    await page.waitForTimeout(3000);
    const rep = await page.evaluate(() => ({ lighting: window.__market?.report?.lighting, lights: window.__market?.report?.lights, warnings: window.__market?.report?.warnings, panel: window.__market?.panel, focus: window.__lighting?.focus, moves: window.__lighting?.focusMoves }));
    if (name.startsWith('-')) { await ctx.close(); continue; } // "-name": only the @snap views
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
