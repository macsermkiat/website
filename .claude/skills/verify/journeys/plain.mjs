// plain.html, the text-only version: reached from the market's skip link, every section present, links out.
export default async (h) => {
  await h.open();
  // the skip link is hidden until focused: a visitor reaches it with the first Tab
  await h.page.keyboard.press('Tab');
  h.check('the first Tab focuses the skip link', await h.page.evaluate(() => document.activeElement?.matches('a.skip')), await h.page.evaluate(() => document.activeElement?.outerHTML.slice(0, 80)));
  await h.page.keyboard.press('Enter');
  await h.page.waitForURL(/plain\.html/);
  h.check('the skip link on the market page opens plain.html', /plain\.html/.test(h.page.url()), h.page.url());
  const heads = await h.page.locator('main#main h2').allTextContents();
  h.check('plain.html has a heading for each section (at least seven)', heads.length >= 7, heads.join(' | '));
  const links = await h.page.locator('main a[href^="http"]').count();
  h.check('plain.html links out (projects, contact)', links > 0, `${links} external links`);
  await h.shot('plain');
};
