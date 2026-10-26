// The Glühwein stand (About): walk there from the on-screen signpost, pour a cup from the stop bar, then pour by
// clicking a mug in 3D. Proof: the stop is reached, the vendor's note counts each pour, before/after screenshots.
export default async (h) => {
  await h.open();
  await h.waitReady();
  await h.shot('overview');
  await h.page.click('#signboard .sb-arm[data-place="glueh"]');
  await h.waitArrived('glueh');
  h.check('the signpost arm walks to the Glühwein stand', await h.state(() => window.__market.stop) === 'glueh');
  h.check('the stop bar names the stall', /Glühwein/.test(await h.page.textContent('#hereName')), await h.page.textContent('#hereName'));
  h.check('the stop bar offers Pour a cup', await h.page.locator('#stopActs [data-action="pour"]').count() === 1);
  await h.shot('at-gluehwein');
  await h.tap('#stopActs [data-action="pour"]');
  h.check('Pour a cup: the vendor says the first cup is poured', await h.waitAnnounce(/poured tonight: 1\b/i), await h.announced());
  await h.shot('poured-1');
  // a mug on the counter is a clickable act_ item: a real mouse click on it pours too
  const mug = await h.state(() => Object.keys(window.__market.items()).find((k) => /^glueh:/.test(k)) && window.__market.glow().targets.find((n) => /mug/i.test(n)));
  if (mug && await h.click3D(mug)) {
    h.check(`a click on ${mug} in 3D pours a second`, await h.waitAnnounce(/poured tonight: 2\b/i), await h.announced());
    await h.shot('poured-2');
  } else h.check('a mug to click in 3D at the Glühwein stand', false, `no clear pixel (${mug || 'no mug among the glowing targets'})`);
};
