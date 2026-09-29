// Dev server for the lighting test bench only (not part of the site build):
//   cd site && npx vite --config src/lighting/vite.test.config.js
//   open http://localhost:4390/src/lighting/test.html
// Serves the repo's review/ folder at /review so the page can load the reference stall.
import { defineConfig } from 'vite';
import { resolve, normalize, extname } from 'node:path';
import { createReadStream, existsSync, statSync } from 'node:fs';

const site = resolve(import.meta.dirname, '../..');
const repo = resolve(site, '..');
const TYPES = { '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };

export default defineConfig({
  root: site,
  base: '/',
  optimizeDeps: { entries: ['src/lighting/test.html'] },
  server: { port: 4390, strictPort: true, fs: { allow: [repo] } },
  plugins: [{
    name: 'lighting-review-files',
    configureServer(server) {
      server.middlewares.use('/review', (req, res, next) => {
        const file = normalize(resolve(repo, 'review', '.' + decodeURIComponent(req.url.split('?')[0])));
        if (!file.startsWith(resolve(repo, 'review')) || !existsSync(file) || !statSync(file).isFile()) return next();
        res.setHeader('Content-Type', TYPES[extname(file)] || 'application/octet-stream');
        createReadStream(file).pipe(res);
      });
    },
  }],
});
