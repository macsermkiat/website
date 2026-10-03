// Unit checks that need no browser: the GPU classes behind the lite-market choice, the ballad's road map, the
// strict content gate, the asset credits and the download budgets.
// Usage: node tests/unit.mjs
import { readFileSync } from 'node:fs';
import { gpuTier, detectLite } from '../src/quality.js';
import { songPlan } from '../src/audio/songplan.js';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { contentGate, assetCredits, buildLibrary, libraryHtml } from '../plugins/market.js';
import { mkdirSync } from 'node:fs';
import { readGlb, budget } from '../scripts/budget.mjs';

let failed = 0;
const check = (name, ok, detail = '') => { if (!ok) failed++; console.log(ok ? '  ok  ' : '  FAIL', name, detail ? `(${detail})` : ''); };

// ---------- GPU classes ----------
const GPUS = [
  ['ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)', 'software'],
  ['llvmpipe (LLVM 15.0.7, 256 bits)', 'software'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00005917) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) UHD Graphics (0x00009A78) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x00009A49) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Intel Inc., Intel(R) Iris(TM) Plus Graphics 655, OpenGL 4.1)', 'integrated'],
  ['Mesa Intel(R) UHD Graphics 620 (KBL GT2)', 'integrated'],
  ['Mesa Intel(R) Xe Graphics (TGL GT2)', 'integrated'],
  ['ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001638) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'integrated'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)', 'integrated'],
  ['Apple GPU', 'integrated'],
  ['ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)', 'discrete'],
  ['ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'discrete'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)', 'discrete'],
  ['ANGLE (Intel, Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['ANGLE (Intel, Intel(R) HD Graphics 520 (0x00001916) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['Intel HD Graphics 5000', 'weak'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 600 (0x00003185) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'weak'],
  ['Mesa Intel(R) UHD Graphics 605 (GLK 3)', 'weak'],
  ['Mali-T860', 'weak'],
  ['Mali-G52', 'weak'],
  ['Mali-G78', 'integrated'],
  ['Adreno (TM) 506', 'weak'],
  ['Adreno (TM) 660', 'integrated'],
  ['PowerVR Rogue GE8320', 'weak'],
];
for (const [r, want] of GPUS) check(`GPU class: ${r.slice(0, 70)}`, gpuTier(r) === want, `${gpuTier(r)} (want ${want})`);
const env = (ua, extra = {}) => ({ navigator: { userAgent: ua, deviceMemory: 8, hardwareConcurrency: 8, ...extra }, matchMedia: () => ({ matches: /iPhone|Android/.test(ua) }), screen: { width: /iPhone|Android/.test(ua) ? 390 : 1920, height: 844 } });
const desk = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36';
check('a UHD 620 laptop gets the full market', detectLite({ renderer: GPUS[2][0], maxTex: 16384 }, env(desk)).lite === false);
check('an Iris Xe laptop gets the full market', detectLite({ renderer: GPUS[5][0], maxTex: 16384 }, env(desk)).lite === false);
check('an HD 4000 laptop gets the lite market', detectLite({ renderer: GPUS[15][0], maxTex: 16384 }, env(desk)).lite === true);
check('a phone gets the lite market', detectLite({ renderer: 'Apple GPU', maxTex: 16384 }, env('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148 Safari/604.1')).lite === true);
check('a 4 GB laptop gets the lite market', detectLite({ renderer: GPUS[2][0], maxTex: 16384 }, env(desk, { deviceMemory: 4 })).lite === true);

// ---------- the ballad's road map ----------
const manifest = JSON.parse(readFileSync(new URL('../public/audio/manifest.json', import.meta.url)));
const plan = songPlan(manifest, { fileEnd: manifest.decodedDuration });
const road = [];
for (let s = plan.segment(0, 1); s; s = plan.next(s)) road.push(s);
check('the head runs into the loop', road[0].from === 0 && Math.abs(road[0].to - manifest.loopEnd) < 1e-6);
check(`the loop plays ${plan.passes} passes`, Math.max(...road.map((s) => s.pass)) === plan.passes);
check('the last stretch is the written ending, past loopEnd to the fermata', Math.abs(road.at(-1).from - manifest.loopEnd) < 1e-6 && road.at(-1).to > manifest.ending.fermata, JSON.stringify(road.at(-1)));
if (manifest.alternates?.length) {
  const alt = road.filter((s) => s.alt);
  check('pass 2 plays the second tenor chorus from the alternates', alt.length === 1 && alt[0].pass === 2 && alt[0].from > manifest.alternates[0].start && alt[0].to < manifest.alternates[0].end, JSON.stringify(alt));
  check('pass 1 and pass 3 play the main chorus', !road.some((s) => s.alt && s.pass !== 2));
}
check('segments join up with no gap', road.every((s, i) => i === 0 || Math.abs(road[i - 1].to - s.from) < 1e-6 || (Math.abs(road[i - 1].to - plan.loopEnd) < 1e-6 && (Math.abs(s.from - plan.loopStart) < 1e-6 || Math.abs(s.from - plan.loopEnd) < 1e-6))));
check('the song is about ten minutes before it rests and starts again', plan.length > 480 && plan.length < 720, `${plan.length.toFixed(0)} s`);

// ---------- content gate, credits, budgets ----------
{
  const dir = mkdtempSync(path.join(tmpdir(), 'nm-content-'));
  writeFileSync(path.join(dir, 'a.md'), 'A line. <!-- check -->\n\nAnother [check: the year].\n');
  writeFileSync(path.join(dir, 'b.md'), 'All confirmed.\n');
  const g = contentGate(dir);
  check('the strict content gate counts <!-- check --> comments and [check] tags', g.left.length === 1 && g.left[0].checks === 2 && /check marker/.test(g.message), g.message);
  mkdirSync(path.join(dir, 'books'));
  writeFileSync(path.join(dir, 'books', 'chaos.md'), '---\ntitle: "Chaos"\nauthor: "James Gleick"\none_line: "Order in disorder."\nreview: "check"\n---\n\n## In short\n\nText.\n');
  writeFileSync(path.join(dir, 'bookshelf.json'), JSON.stringify({ books: [{ title: 'Chaos', author: 'James Gleick' }, { title: 'Grit', author: 'Angela Duckworth' }] }));
  const g2 = contentGate(dir);
  check('the strict content gate counts a book page still marked review: check', g2.left.some((l) => l.file === 'books/chaos.md' && l.checks === 1), g2.message);
  const lib = buildLibrary(dir);
  check('Mac\'s bookshelf: every chosen title, with its one-line summary where the writer has one', lib.books.length === 2 && lib.books[0].oneLine === 'Order in disorder.' && lib.books[1].oneLine === '', JSON.stringify(lib.books));
  check('Mac\'s bookshelf renders as a list for the panel and the text page', /<details class="library"[\s\S]*<em>Chaos<\/em> · James Gleick\. <span class="one-line">Order in disorder\.<\/span>/.test(libraryHtml(lib)));
  check('no bookshelf file: an empty library, no error', buildLibrary(path.join(dir, 'nowhere')).books.length === 0);
  const credits = assetCredits();
  check('asset credits from CREDITS.md carry source URLs and licences', /<details class="credits-all"/.test(credits) && /href="https:\/\/github\.com\/mrdoob\/three\.js"/.test(credits) && /MIT/.test(credits));
  const b = budget();
  const glb = readGlb(new URL('../public/models/deco_lebkuchen.glb', import.meta.url).pathname);
  check('budget: a glb\'s external textures are counted with it', glb.images.length > 0 && b.rows.find((r) => r.id === 'deco-lebkuchen').full.textures > 0, glb.images.join(' '));
  check('budget: both first loads are under their aims', !b.totals.full.over && !b.totals.lite.over, `${(b.totals.full.firstLoad / 1e6).toFixed(2)} / ${(b.totals.lite.firstLoad / 1e6).toFixed(2)} MB`);
}

console.log(failed ? `\n${failed} unit checks failed` : '\nall unit checks passed');
process.exit(failed ? 1 : 0);
