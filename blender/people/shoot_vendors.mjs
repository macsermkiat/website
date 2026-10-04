// Organizer round 6: browser (three.js) checks of the vendors' faces and the Buecherstand browsers.
// node shoot_vendors.mjs <distDir> <outDir> [stalls]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const [dist, out, stallArg] = process.argv.slice(2);
const STALLS = (stallArg || 'buecherstand,bierstand,gluehwein,bratwurst').split(',');
const PORT = 4473;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORT), '--strictPort', '--outDir', dist], { cwd: '/home/claude/website/site', stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res) => server.stdout.on('data', (d) => String(d).includes('localhost') && res()));
log('server up');
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const errors = [];
const save = (name, dataUrl) => { fs.writeFileSync(path.join(out, name), Buffer.from(dataUrl.split(',')[1], 'base64')); log('saved', name); };
const info = {};
try {
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 700 }, reducedMotion: 'reduce', deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(1800000);
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/website/?snow=0&quality=full&lod=300`, { timeout: 1800000 });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 1800000, polling: 2000 });
  log('ready');
  await page.evaluate(() => window.__market.freeze(true));
  await page.evaluate(() => window.__market.settled?.());
  log('settled');
  for (const stall of STALLS) {
    // the market stays frozen: the walk is stepped with advance() (simulation only, no frames drawn), which on
    // software GL is far faster than waiting for the walk to play out frame by frame
    // the guided walk is not used (this build's walkTo refuses from the frozen home view): every shot below places
    // the camera itself. ?lod=300 keeps every person on the full figure, as a visitor standing at the stall sees it.
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.evaluate(() => window.__market.advance(3.0));
    log('arrived', stall);
    if (stall === 'buecherstand') {
      info.people = await page.evaluate(() => window.__market.people().filter((p) => p.stall === 'buecherstand' || Math.hypot(p.pos[0] - 12.8, p.pos[2] - 2.6) < 5));
      info.hidden = await page.evaluate(() => window.__market.hiddenPeople());
      info.cam = await page.evaluate(() => window.__market.cam());
      // a high three-quarter view of the open stall with every person shown, so the browsers' feet and the carts read
      save('browser_buecherstand_overview.jpg', await page.evaluate(() => {
        const m = window.__market, { camera, scene } = m;
        const crowd = scene.getObjectByName('crowd');
        const vis = [];
        crowd?.children.forEach((o) => { vis.push([o, o.visible]); o.visible = true; });
        const p0 = camera.position.clone(), q0 = camera.quaternion.clone(), f0 = camera.fov;
        // stall at (12.8, 2.6) rotY -0.8: its front (+Z local) points toward the square
        const ry = -0.8, fx = Math.sin(ry), fz = Math.cos(ry);
        const c = { x: 12.8 + fx * 2.0, z: 2.6 + fz * 2.0 };
        camera.position.set(c.x + fx * 5.0 + fz * 1.6, 3.2, c.z + fz * 5.0 - fx * 1.6);
        camera.lookAt(c.x, 0.9, c.z);
        camera.fov = 48; camera.updateProjectionMatrix();
        const url = m.snapshot('image/jpeg', 0.9);
        camera.position.copy(p0); camera.quaternion.copy(q0); camera.fov = f0; camera.updateProjectionMatrix();
        vis.forEach(([o, v]) => { o.visible = v; });
        return url;
      }));
    }
    // vendor face close-up from across the counter
    const shot = await page.evaluate((s) => {
      const m = window.__market, { camera, scene } = m;
      const V3 = camera.position.constructor, Qt = camera.quaternion.constructor;
      const v = m.people().find((p) => p.vendor && p.stall === s);
      if (!v) return null;
      const g = scene.getObjectByName(v.name);
      g.updateMatrixWorld(true);
      const heads = [];
      g.traverse((o) => { if (/^head$/i.test(o.name)) { let vis = true; for (let p = o; p && p !== g; p = p.parent) if (!p.visible) vis = false; heads.push([o, vis]); } });
      const head = (heads.find((h) => h[1]) || heads[0] || [null])[0];
      const hp = new V3(); (head || g).getWorldPosition(hp);
      if (!head) hp.y += 1.55;
      const fwd = new V3(0, 0, 1).applyQuaternion(g.getWorldQuaternion(new Qt()));
      fwd.y = 0; fwd.normalize();
      const p0 = camera.position.clone(), q0 = camera.quaternion.clone(), f0 = camera.fov;
      camera.position.set(hp.x + fwd.x * 1.3, hp.y + 0.08, hp.z + fwd.z * 1.3);
      camera.lookAt(hp.x, hp.y - 0.16, hp.z);
      camera.fov = 30; camera.updateProjectionMatrix();
      const url = m.snapshot('image/jpeg', 0.92);
      camera.position.copy(p0); camera.quaternion.copy(q0); camera.fov = f0; camera.updateProjectionMatrix();
      const meshes = [];
      g.traverse((o) => { if (o.isMesh) { let vis = true; for (let p = o; p && p !== g; p = p.parent) if (!p.visible) vis = false; meshes.push(`${o.parent?.name}/${o.name}:${vis ? 'on' : 'off'}`); } });
      return { url, name: v.name, head: !!head, heads: heads.length, visible: g.visible, meshes };
    }, stall);
    if (shot) { const { url, ...rest } = shot; save(`browser_vendor_${stall}.jpg`, url); info[stall] = rest; }
    fs.writeFileSync(path.join(out, 'browser_info.json'), JSON.stringify(info, null, 1));
  }
} finally {
  log('errors', errors.length, errors.slice(0, 5).join(' | '));
  await browser.close();
  server.kill();
}
