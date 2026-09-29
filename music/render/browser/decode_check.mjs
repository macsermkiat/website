// Decode the shipped stems in Chromium (Playwright) the way the site does, with decodeAudioData,
// and hand back each stem's length plus three windows (start, loopStart, loopEnd) for
// music/render/browser_check.py to compare against the renderer's own timeline.
//   node music/render/browser/decode_check.mjs <port> <out.json>
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';

// playwright is installed globally on the build machine; fall back to `npm root -g`
const require = createRequire(import.meta.url);
let pw;
try { pw = require('playwright'); } catch { pw = require(`${execSync('npm root -g').toString().trim()}/playwright`); }
const { chromium } = pw;

const port = process.argv[2] || '8765';
const outPath = process.argv[3] || 'decode.json';
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined });
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${port}/manifest.json`);
const result = await page.evaluate(async () => {
  const man = await (await fetch('manifest.json')).json();
  const files = { ...man.stems, mix: man.mix };
  const out = { manifest: man, userAgent: navigator.userAgent, stems: {} };
  for (const rate of [44100, 48000]) {
    for (const [k, url] of Object.entries(files)) {
      const data = await (await fetch(url)).arrayBuffer();
      const ctx = new OfflineAudioContext(2, 1, rate);
      const buf = await ctx.decodeAudioData(data);
      const ch = buf.getChannelData(0);
      const win = (t0, secs) => {
        const a = Math.max(0, Math.round(t0 * buf.sampleRate));
        return Array.from(ch.subarray(a, a + Math.round(secs * buf.sampleRate)));
      };
      const rec = { sampleRate: buf.sampleRate, length: buf.length, duration: buf.duration };
      if (rate === 44100) {
        rec.start = win(0, 3.0);
        rec.atLoopStart = win(man.loopStart - 1.0, 2.0);
        rec.atLoopEnd = win(man.loopEnd - 1.0, 2.0);
      }
      out.stems[`${k}@${rate}`] = rec;
    }
  }
  return out;
});
fs.writeFileSync(outPath, JSON.stringify(result));
console.log(result.userAgent);
for (const [k, v] of Object.entries(result.stems)) console.log(k, v.sampleRate, v.length, v.duration.toFixed(6));
await browser.close();
