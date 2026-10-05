// The interactive places and how to recognise them in file names, layout ids and node names.
// Round 8 (docs/adr/0004): the ornament shop (layout id deco-schmuck) is the eighth, a stop for play with no section text.
export const PLACE_ORDER = ['glueh', 'bier', 'wurst', 'books', 'band', 'ferris', 'carousel', 'schmuck'];

export const PLACE_ALIASES = {
  glueh: ['glueh', 'gluehwein', 'glühwein', 'gluhwein', 'about'],
  bier: ['bier', 'bierstand', 'beer', 'projects'],
  wurst: ['wurst', 'bratwurst', 'writing'],
  books: ['books', 'book', 'buecher', 'bücher', 'buecherstand', 'bücherstand', 'bookshop', 'bookstall', 'reading'],
  band: ['band', 'bandstand', 'music'],
  ferris: ['ferris', 'riesenrad', 'ferriswheel', 'wheel', 'big-questions', 'bigquestions'],
  carousel: ['carousel', 'karussell', 'carrousel', 'contact'],
  schmuck: ['schmuck', 'deco-schmuck', 'christbaumschmuck', 'ornaments', 'ornament-shop', 'stall-schmuck'],
};

export const SECTION_STALLS = ['glueh', 'bier', 'wurst', 'books'];
export const LANDMARKS = ['band', 'ferris', 'carousel'];
/** Places that are for play: a stop on the stroll with things to do, but no section text (the ornament shop). */
export const PLAY_PLACES = ['schmuck'];

const norm = (s) => String(s || '').toLowerCase().normalize('NFC').replace(/[\s_.]+/g, '-');

/** Map any id, file name or label to a place id, or null. */
export function placeFor(word) {
  const w = norm(word).replace(/\.lite$/, '').replace(/-?glb$/, '');
  if (!w) return null;
  for (const [id, list] of Object.entries(PLACE_ALIASES)) if (list.some((a) => norm(a) === w)) return id;
  const tokens = w.split('-');
  for (const [id, list] of Object.entries(PLACE_ALIASES)) if (list.some((a) => tokens.includes(norm(a)))) return id;
  return null;
}

/** Name tokens of a model file ("stalls/stall_gluehwein.lite.glb" -> ["stall","gluehwein"]). */
export function fileTokens(file) {
  const base = String(file).split('/').pop().replace(/\.(glb|gltf)$/i, '').replace(/\.lite$/i, '');
  return norm(base).split('-').filter(Boolean);
}
