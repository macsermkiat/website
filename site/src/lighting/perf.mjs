// Frame-time profile of the real market with this lighting module.
//
//   cd site && node src/lighting/perf.mjs --gpu --headed            # on a laptop with a real GPU
//   cd site && node src/lighting/perf.mjs                           # software GL (SwiftShader), for a smoke test
//
// Options: --w 1440 --h 900 --dpr 1.75 --seconds 20 --q "quality=full&snow=0"
//          --fixed   turns the adaptive quality off (?lighting-adaptive=0), to measure the full profile as is
//          --runs "full-fixed=quality=full&lighting-adaptive=0,full=quality=full,lite=quality=lite"
// Prints one JSON line per run: rAF frame times (p50/p95/p99, fps), GPU time of the composer
// (EXT_disjoint_timer_query_webgl2, when the GPU offers it), draw calls, the quality level the
// adaptive step-down reached, and the GL renderer string.
import { spawn } from 'node:child_process';

let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const W = +opt('--w', 1440), H = +opt('--h', 900), DPR = +opt('--dpr', 1.75), SECONDS = +opt('--seconds', 20);
const PORT = +opt('--port', 4393);
const runs = Object.fromEntries((opt('--runs', '') || `${has('--fixed') ? 'full-fixed' : 'full'}=${opt('--q', 'quality=full&snow=0')}${has('--fixed') ? '&lighting-adaptive=0' : ''}`)
  .split(',').map((r) => { const [k, ...v] = r.split('='); return [k, v.join('=')]; }));

const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--config', 'src/lighting/vite.market.config.js', '--port', String(PORT), '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
await new Promise((res, rej) => {
  const t = setTimeout(() => rej(new Error('vite did not start')), 60000);
  server.stdout.on('data', (d) => { if (String(d).includes('localhost')) { clearTimeout(t); res(); } });
  server.on('exit', (c) => rej(new Error('vite exited ' + c)));
});
const gpuArgs = has('--gpu')
  ? ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--disable-frame-rate-limit']
  : ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ headless: !has('--headed'), args: gpuArgs });
try {
  for (const [name, qs] of Object.entries(runs)) {
    const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
    const page = await ctx.newPage();
    page.setDefaultTimeout(900000);
    page.on('pageerror', (e) => console.log(`  [${name}] pageerror: ${e.message}`));
    page.on('console', (m) => { if (/adaptive quality/.test(m.text())) console.log(`  [${name}] ${m.text()}`); });
    await page.goto(`http://localhost:${PORT}/website/?${qs}`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__market?.ready && window.__lighting, null, { timeout: 900000 });
    // let the first captures, probes and shader compiles pass
    await page.waitForTimeout(4000);
    const result = await page.evaluate(async (seconds) => {
      const L = window.__lighting, R = window.__market.renderer;
      const gl = R.getContext();
      const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      const gpuName = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
      const gpu = [], frames = [], calls = [];
      const pending = [];
      const render = L.composer.render.bind(L.composer);
      if (ext) {
        L.composer.render = (dt) => {
          const q = gl.createQuery();
          gl.beginQuery(ext.TIME_ELAPSED_EXT, q);
          render(dt);
          gl.endQuery(ext.TIME_ELAPSED_EXT);
          pending.push(q);
        };
      }
      const poll = () => {
        while (pending.length && gl.getQueryParameter(pending[0], gl.QUERY_RESULT_AVAILABLE)) {
          const q = pending.shift();
          if (!gl.getParameter(ext.GPU_DISJOINT_EXT)) gpu.push(gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6);
          gl.deleteQuery(q);
        }
      };
      const autoReset = R.info.autoReset;
      R.info.autoReset = false; // count every pass of a frame, not just the last one
      R.info.reset();
      await new Promise((done) => {
        let last = performance.now();
        const t0 = last;
        const f = (now) => {
          frames.push(now - last);
          last = now;
          calls.push(R.info.render.calls);
          R.info.reset();
          if (ext) poll();
          if (now - t0 < seconds * 1000) requestAnimationFrame(f); else done();
        };
        requestAnimationFrame(f);
      });
      L.composer.render = render;
      R.info.autoReset = autoReset;
      const stat = (a) => {
        if (!a.length) return null;
        const s = a.slice(1).sort((x, y) => x - y);
        const q = (p) => +s[Math.min(s.length - 1, Math.floor(p * s.length))].toFixed(2);
        return { n: s.length, p50: q(0.5), p95: q(0.95), p99: q(0.99), fps: +(1000 / q(0.5)).toFixed(1) };
      };
      return {
        gpuName, pixelRatio: R.getPixelRatio(), canvas: [R.domElement.width, R.domElement.height],
        frame: stat(frames), gpuComposer: ext ? stat(gpu) : 'EXT_disjoint_timer_query_webgl2 not available',
        drawCallsPerFrame: calls.length > 1 ? Math.round(calls.slice(1).reduce((a, b) => a + b, 0) / (calls.length - 1)) : null,
        lighting: L.stats(),
        report: { lighting: window.__market.report.lighting, lights: window.__market.report.lights, quality: window.__market.report.quality?.lite ? 'lite' : 'full' },
      };
    }, SECONDS);
    console.log(JSON.stringify({ run: name, viewport: [W, H], dpr: DPR, ...result }));
    await ctx.close();
  }
} finally {
  await browser.close();
  server.kill();
}
