// Dev server for the carpenter's three.js stall check (not part of the site build):
//   node blender/stalls/web/shoot.mjs            (starts this server itself)
// Root is the repo, so the page can load site/public/models/*.glb and the lighting designer's
// site/src/lighting/ module exactly as the site does. `three` resolves to the site's copy.
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');
const three = resolve(repo, 'site/node_modules/three');

export default {
  root: repo,
  base: '/',
  logLevel: 'warn',
  resolve: { alias: [{ find: /^three$/, replacement: `${three}/build/three.module.js` },
                     { find: /^three\/(.*)$/, replacement: `${three}/$1` }] },
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { port: +(process.env.NM_SHOT_PORT || 4397), strictPort: true, fs: { allow: [repo] } },
};
