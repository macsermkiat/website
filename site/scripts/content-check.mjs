// What still stops the deploy: every [[Mac: ...]] note, <!-- check --> or [check] marker and book page marked
// `review: check` in content/, with its file and line. The deploy's build runs with STRICT_CONTENT=1, which fails
// while any of these is left (plugins/market.js contentGate). Usage: npm run content:check [-- --books]
//   --books   list each book page still marked review: check (by default they are counted on one line)
import { contentMarkers, contentGate } from '../plugins/market.js';

const all = contentMarkers();
const showBooks = process.argv.includes('--books');
const pages = all.filter((m) => m.kind === 'review');
const rest = all.filter((m) => m.kind !== 'review').sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
let file = '';
for (const m of rest) {
  if (m.file !== file) { file = m.file; console.log(`\ncontent/${file}`); }
  console.log(`  ${String(m.line).padStart(4)}  ${m.kind === 'note' ? 'note ' : 'check'}  ${m.text}`);
}
if (pages.length) {
  console.log(`\ncontent/books/: ${pages.length} page${pages.length > 1 ? 's' : ''} marked review: check${showBooks ? '' : ' (--books lists them)'}`);
  if (showBooks) for (const m of pages) console.log(`  ${m.file}`);
}
const notes = rest.filter((m) => m.kind === 'note').length, checks = rest.length - notes;
console.log(`\n${all.length ? `${notes} notes, ${checks} check markers, ${pages.length} book pages to review. ${contentGate().message}` : 'Nothing left: the strict content gate lets the deploy through.'}`);
process.exit(all.length ? 1 : 0);
