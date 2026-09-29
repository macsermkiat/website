// three.js screenshots of the organizer's figures, as the site draws them (Playwright + SwiftShader).
//   node blender/people/web/shoot.mjs --figs people_man_coat:idle:1,... [--lite] [--cam x,y,z,tx,ty,tz,fov]
//        [--gap 0.9] [--out review/round-1/organizer/threejs_x.jpg] [--w 1280 --h 720]
import { spawn } from 'node:child_process';
import path from 'node:path';

let pw;
try { pw = await import(process.env.PLAYWRIGHT_MODULE || 'playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, '../../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const W = +opt('--w', 1280), H = +opt('--h', 720);
const out = path.resolve(REPO, opt('--out', 'blender/out/people/renders/threejs.jpg'));
const qs = new URLSearchParams({ figs: opt('--figs', 'people_man_coat:idle:1'), gap: opt('--gap', '0.9') });
if (args.includes('--lite')) qs.set('lite', '1');
if (opt('--cam')) qs.set('cam', opt('--cam'));

const vite = path.join(REPO, 'site/node_modules/vite/bin/vite.js');
const server = spawn(process.execPath, [vite, '--config', path.join(HERE, 'vite.config.mjs')], { cwd: REPO, stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res) => setTimeout(res, 6000));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  const page = await (await browser.newContext({ viewport: { width: W, height: H } })).newPage();
  page.setDefaultTimeout(600000);
  page.on('console', (m) => { if (m.type() === 'error') console.log('  console:', m.text().slice(0, 300)); });
  page.on('pageerror', (e) => console.log('  pageerror:', e.message));
  await page.goto(`http://localhost:4396/blender/people/web/people_shot.html?${qs}`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 600000 });
  console.log((await page.evaluate(() => window.__info)).join('\n'));
  await page.screenshot({ path: out, type: 'jpeg', quality: 88 });
  console.log('wrote', out);
} finally {
  await browser.close();
  server.kill();
}
