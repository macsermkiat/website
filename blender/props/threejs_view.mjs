import { spawn } from 'node:child_process';
let pw; try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw.default || pw;
// node blender/props/threejs_view.mjs <glb name in site/public/models> <out.png>
// A plain three.js check of one prop glb outside the engine (AgX, a warm key and fill from the visitor's side,
// a dim sky), to tell a material problem from a lighting one. Serves the repo on localhost only.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const [name, out] = process.argv.slice(2);
const html = '/blender/props/threejs_view.html', glb = `/site/public/models/${name}`;
const srv = spawn('python3', ['-m', 'http.server', '4411', '--bind', '127.0.0.1', '--directory', REPO], { stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 1500));
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  p.on('console', (m) => console.log('console', m.text()));
  await p.goto(`http://localhost:4411${html}?glb=${encodeURIComponent(glb)}`);
  await p.waitForFunction(() => document.title.startsWith('done') || document.title.startsWith('err'), null, { timeout: 600000 });
  console.log(await p.title());
  await p.screenshot({ path: out });
} finally { await b.close(); srv.kill(); }
