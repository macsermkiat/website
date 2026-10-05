import { spawn } from 'node:child_process';
const pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
const { chromium } = pw.default || pw;
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', '4391', '--strictPort', '--outDir', process.argv[2]], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((r) => server.stdout.on('data', (d) => String(d).includes('localhost') && r()));
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 960, height: 640 } });
await p.goto('http://localhost:4391/website/?quality=lite&snow=0&perf', { timeout: 300000 });
await p.waitForFunction(() => document.documentElement.dataset.ready === 'true', null, { timeout: 300000 });
const out = await p.evaluate(async () => {
  const m = window.__market, r = m.renderer, seen = {};
  const orig = r.renderBufferDirect;
  r.renderBufferDirect = function (cam, sc, geo, mat, obj, grp) {
    const t0 = r.info.render.triangles;
    orig.call(this, cam, sc, geo, mat, obj, grp);
    if (Number.isFinite(t0) && !Number.isFinite(r.info.render.triangles)) {
      const k = `${obj.type} ${obj.name || obj.parent?.name || ''} geo=${geo.type} ic=${geo.instanceCount} max=${geo._maxInstanceCount} cnt=${obj.count} grp=${JSON.stringify(grp)} dr=${JSON.stringify(geo.drawRange)} idx=${geo.index?.count} pos=${geo.attributes.position?.count}`;
      seen[k] = (seen[k] || 0) + 1;
      r.info.render.triangles = t0;
    }
  };
  m.read('glueh.board');
  for (let i = 0; i < 6; i++) await new Promise((res) => requestAnimationFrame(res));
  m.closeRead();
  for (let i = 0; i < 4; i++) await new Promise((res) => requestAnimationFrame(res));
  return seen;
});
console.log(JSON.stringify(out, null, 1));
await b.close(); server.kill();
