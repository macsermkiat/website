// three.js screenshots of the carpenter's stalls under the site's lighting (Playwright + SwiftShader).
//   node blender/stalls/web/shoot.mjs [--out review/round-2/carpenter/web] [--only stall_bier,...]
//        [--ao both|on|off] [--lite] [--w 1280 --h 720] [--props prop_a@slot_counter,prop_b@slot_shelf_1]
//        [--signspot] [--home] [--tag name] [--cam x,y,z,tx,ty,tz,lens]
//   --home   frame the stall from layout.json's home camera, the stall placed where layout.json puts it
// Starts its own Vite server (blender/stalls/web/vite.config.mjs) on port NM_SHOT_PORT (default 4397;
// the lighting designer's tools use 4395).
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

// Playwright: PLAYWRIGHT_MODULE (path to playwright/index.mjs), a local install, or the cloud machine's copy.
let pw;
try { pw = await import(process.env.PLAYWRIGHT_MODULE || 'playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, '../../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.resolve(REPO, opt('--out', 'review/round-2/carpenter/web'));
const W = +opt('--w', 1280), H = +opt('--h', 720);
const AO = opt('--ao', 'both');
const lite = args.includes('--lite');
// the Cycles preview cameras (Blender coordinates) of each stall script
const CAMS = {
  stall_gluehwein: '-4.3,-7.4,2.1,0.1,-0.6,2.15,30',
  stall_bratwurst: '-4.4,-6.9,2.35,0.0,-0.5,1.9,30',
  stall_bier: '-4.6,-7.4,2.1,0.1,-0.5,2.05,29',
  stall_buecher: '-4.5,-6.9,2.0,0.0,-0.4,1.8,30',
};
const only = opt('--only', Object.keys(CAMS).join(',')).split(',');
const props = opt('--props', '');
const signspot = args.includes('--signspot');
const home = args.includes('--home');
const tag = opt('--tag', '');
import { readFileSync } from 'node:fs';
const layout = JSON.parse(readFileSync(path.join(REPO, 'site/src/layout.json'), 'utf8'));
const placeOf = (name) => layout.places.find((p) => p.asset === `${name}.glb`);
mkdirSync(OUT, { recursive: true });

const vite = path.join(REPO, 'site/node_modules/vite/bin/vite.js');
const server = spawn(process.execPath, [vite, '--config', path.join(HERE, 'vite.config.mjs')], { cwd: REPO, stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite did not start')), 60000);
  const ok = (d) => { if (String(d).includes(String(process.env.NM_SHOT_PORT || 4397)) || String(d).includes('localhost')) { clearTimeout(t); res(); } };
  server.stdout.on('data', ok);
  server.stderr.on('data', (d) => { process.stderr.write(d); });
  server.on('exit', (c) => rej(new Error('vite exited ' + c)));
  setTimeout(() => { clearTimeout(t); res(); }, 8000);
});
// macOS: the real GPU through ANGLE/Metal; elsewhere (cloud machine) SwiftShader software GL.
const glArgs = process.platform === 'darwin'
  ? ['--use-angle=metal', '--ignore-gpu-blocklist']
  : ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ args: glArgs });
try {
  for (const name of only) {
    const cam = opt('--cam', CAMS[name] || '-2.9,-5.0,1.85,0.05,-0.45,2.05,28');
    for (const ao of AO === 'both' ? ['on', 'off'] : [AO]) {
      const t0 = Date.now();
      const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      page.setDefaultTimeout(600000);
      page.on('console', (m) => { if (m.type() === 'error' || process.env.NM_SHOT_DEBUG) console.log(`  [${name}] ${m.text().slice(0, 300)}`); });
      page.on('pageerror', (e) => console.log(`  [${name}] pageerror: ${e.message}`));
      let qs = `?shot=1&glb=${name}&cam=${cam}${ao === 'off' ? '&ao=0' : ''}${lite ? '&lite=1' : ''}`;
      if (props) qs += `&props=${props}`;
      if (signspot) qs += '&signspot=1';
      if (home) {
        const pl = placeOf(name), c = layout.camera.home;
        qs += `&place=${pl.pos[0]},${pl.pos[1]},${pl.rotY}&home=${[...c.pos, ...c.target, c.fov].join(',')}`;
      }
      await page.goto(`http://localhost:${process.env.NM_SHOT_PORT || 4397}/blender/stalls/web/stall_shot.html${qs}`, { waitUntil: 'load' });
      await page.waitForFunction(() => window.__stallReady === true, null, { timeout: 600000 });
      await page.waitForTimeout(1000);
      const file = path.join(OUT, `${name}${lite ? '.lite' : ''}_three${tag ? '_' + tag : ''}${ao === 'off' ? '_noao' : ''}.png`);
      await page.screenshot({ path: file });
      const inf = await page.evaluate(() => window.__info);
      console.log(`${path.relative(REPO, file)} ${((Date.now() - t0) / 1000).toFixed(0)} s ${JSON.stringify(inf)}`);
      await ctx.close();
    }
  }
} finally {
  await browser.close();
  server.kill();
}
