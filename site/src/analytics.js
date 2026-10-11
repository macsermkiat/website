// Google Analytics 4 (Mac, 2026-10-11: "create site analytic with Google analytic"). The Measurement ID is set at
// build time (VITE_GA_ID in .env.production); without one nothing loads, so local runs and the tests send nothing.
// A browser that asks not to be tracked (Do Not Track, Global Privacy Control) is not tracked.
const ID = import.meta.env.VITE_GA_ID || '';
const declined = () => navigator.doNotTrack === '1' || window.doNotTrack === '1' || navigator.globalPrivacyControl === true;
let on = false;

export function initAnalytics() {
  if (!ID || on || declined()) return;
  on = true;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', ID);
  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ID)}`;
  document.head.appendChild(s);
  // the one-line note in "How to visit" (and the plain version's footer) shows only when analytics runs
  for (const n of document.querySelectorAll('[data-analytics-note]')) n.hidden = false;
}

/** One event: a stop reached, an item used, a page read. */
export function track(name, params = {}) {
  if (on) window.gtag('event', name, params);
}
