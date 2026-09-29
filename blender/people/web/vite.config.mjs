// Dev server for the organizer's three.js figure check (not part of the site build):
//   node blender/people/web/shoot.mjs   (starts this server itself)
// Root is the repo, so the page loads site/public/models/people_*.glb as the site does.
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
  server: { port: 4396, strictPort: true, fs: { allow: [repo] } },
};
