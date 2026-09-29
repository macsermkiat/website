// Every panel action, by place id: { hint, acts: [[label, fn]], play? }.
import { createStallActions } from './stalls.js';
import { createBandActions } from './band.js';
import { createRideActions } from './rides.js';
import { createAnimator } from './util.js';

export function createActions(ctx) {
  const anim = createAnimator(ctx.motion);
  const full = { ...ctx, anim };
  const stalls = createStallActions(full);
  const band = createBandActions(full);
  const rides = createRideActions(full);
  const byPlace = {
    glueh: stalls.glueh, bier: stalls.bier, wurst: stalls.wurst, books: stalls.books,
    band: band.band, ferris: rides.ferris, carousel: rides.carousel,
  };
  return {
    get: (id) => byPlace[id] || null,
    pullBook: stalls.pullBook,
    rides,
    bandPositions: band.positions,
    update(dt, t, still) {
      anim.update(dt);
      stalls.update(dt, t, still);
      band.update(dt, t, still);
    },
  };
}
