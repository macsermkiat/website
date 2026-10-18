// GitHub Pages sends .glb files uncompressed, and gzip takes about 45% off them even after meshopt. A build
// writes <name>.glb.gz beside each glb in dist/models; the engine's loader (engine/loader.js) fetches that
// and unpacks it in the browser, falling back to the plain glb.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

export default function gzipModels() {
  let outDir = null;
  return {
    name: 'nachtmarkt-gzip-models',
    apply: 'build',
    configResolved(cfg) { outDir = path.resolve(cfg.root, cfg.build.outDir); },
    closeBundle() {
      const dir = path.join(outDir, 'models');
      if (!fs.existsSync(dir)) return;
      let raw = 0, packed = 0;
      for (const f of fs.readdirSync(dir)) {
        if (!f.endsWith('.glb')) continue;
        const bytes = fs.readFileSync(path.join(dir, f));
        const gz = zlib.gzipSync(bytes, { level: 9 });
        fs.writeFileSync(path.join(dir, `${f}.gz`), gz);
        raw += bytes.length;
        packed += gz.length;
      }
      console.log(`models: gzip twins ${(raw / 1e6).toFixed(2)} MB -> ${(packed / 1e6).toFixed(2)} MB`);
    },
  };
}
