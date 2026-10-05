// Every panel action, by place id: { hint, acts: [[label, fn]], play? }.
import { createStallActions } from './stalls.js';
import { createBandActions } from './band.js';
import { createRideActions } from './rides.js';
import { createAnimator } from './util.js';
import { createItems } from './items/index.js';

export function createActions(ctx) {
  const anim = createAnimator(ctx.motion);
  const full = { ...ctx, anim };
  // every item on the counters and shelves, clickable on its own; the panel buttons drive the same handlers
  const items = createItems(full);
  full.items = items;
  const stalls = createStallActions(full);
  const band = createBandActions(full);
  const rides = createRideActions(full);
  const byPlace = {
    glueh: stalls.glueh, bier: stalls.bier, wurst: stalls.wurst, books: stalls.books,
    band: band.band, ferris: rides.ferris, carousel: rides.carousel,
    // the ornament shop (ADR 0004): for play, its buttons are its ornaments' actions
    get schmuck() {
      const list = items.handlers.schmuckActs?.() || [];
      return list.length ? { hint: 'Three things to try: light the candle arch and watch the town wake, brush the twelve glass baubles to play the ballad, and look into the big mercury-glass ball.', acts: list } : null;
    },
  };
  return {
    get: (id) => byPlace[id] || null,
    items,
    /** Put back whatever stands out (an open book, a bottle being shown, a raised glass). */
    retract: () => items.retract(),
    featuredBooks: items.handlers.featuredBooks || [],
    rides,
    shop: items.shop,
    bandPositions: band.positions,
    update(dt, t, still) {
      anim.update(dt);
      items.update(dt, t, still);
      stalls.update(dt, t, still);
      band.update(dt, t, still);
      rides.update(dt);
    },
  };
}
