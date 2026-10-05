// The guide: where the visitor is on the stroll and how they move on. It ties the camera's walks to the stops,
// the streaming of full-detail stalls, the bar of things to do at a stop, the signpost and reading.
//   walkTo(id)   walk the lane to a place's stop          home()   back to the overview of the square
//   step(±1)     the previous / next stop                  read(id) read a piece (walking there first if need be)
//   back()       from a close-up (an item, a deco stall, a shelf) back to the stop's view

export function createGuide({ camera, rig, stroll, streamer, actions, world, stopbar, signboard, note, key, market, announce, sections, onMove }) {
  let here = null; // the stop the visitor is at, or walking to
  let arrived = false;
  let closeUp = false;
  let pendingRead = null;
  const name = (id) => sections[id]?.name || id;

  function prepare() {
    if (actions.rides.riding) actions.rides.endRide(true);
    if (world.isOpen) world.close({ silent: true, keepCamera: true });
    actions.retract();
    note.hide();
    closeUp = false;
    document.documentElement.classList.remove('closeup');
  }

  function walkTo(id, { read = null } = {}) {
    if (!sections[id]) return false;
    if (here === id && arrived && !closeUp && !world.isOpen && !actions.rides.riding) { if (read) world.open(read); return true; }
    // where the walk starts: this stop (or home) once there; mid-walk, the nearest stop
    const fromId = arrived ? here || 'home' : null;
    prepare();
    pendingRead = read;
    const path = stroll.pathTo(camera.position, id, fromId);
    if (!path) return false;
    here = id;
    arrived = false;
    // the stall in view and the one after it come in at full detail while the visitor walks
    streamer?.want([id, stroll.next(id)]);
    if (id === 'books' || stroll.next(id) === 'books') actions.items?.handlers?.prefetchBook?.();
    stopbar.hide();
    signboard.setCurrent(id);
    document.documentElement.dataset.stop = id;
    document.documentElement.dataset.walking = 'true';
    announce(`Walking to the ${name(id)}.`);
    // the Riesenrad: walk to the foot of the wheel, then rise to the view from the top gondola
    const rise = path.rise;
    rig.walkTo(path.points, path.view, { onArrive: () => (rise && here === id ? rig.flyTo(rise, { duration: 4.2, onArrive: () => arrive(id) }) : arrive(id)) });
    key?.follow(market.places[id] || null);
    onMove?.(id);
    return true;
  }

  function arrive(id) {
    if (here !== id) return;
    arrived = true;
    document.documentElement.dataset.walking = 'false';
    stopbar.show(id, { prevId: stroll.prev(id), nextId: stroll.next(id) });
    announce(sections[id]?.play ? `At the ${name(id)}: ${sections[id]?.sub || ''}. Click the ornaments, or use the buttons below.` : `At the ${name(id)}: ${sections[id]?.sub || ''}. Press Enter to read what is written here.`);
    if (pendingRead) { const r = pendingRead; pendingRead = null; world.open(r); }
  }

  function home() {
    prepare();
    pendingRead = null;
    here = null;
    arrived = true;
    stopbar.hide();
    signboard.setCurrent(null);
    delete document.documentElement.dataset.stop;
    document.documentElement.dataset.walking = 'false';
    key?.follow(null);
    rig.flyTo(null, { home: true });
    announce('The overview of the whole square.');
    streamer?.want([stroll.first()]);
    onMove?.(null);
  }

  function step(d) {
    if (!here) return walkTo(d > 0 ? stroll.stops[0] : stroll.stops[stroll.stops.length - 1]);
    return walkTo(d > 0 ? stroll.next(here) : stroll.prev(here));
  }

  /** The main piece to read at a stop (the board, the vom-Fass board, the menu, the card, the sheet, the noticeboard, the ticket). */
  function mainPiece(id) {
    return world.pieces().find((p) => p.placeId === id && !/coaster|placard|paper|book$/.test(p.id)) || world.pieces().find((p) => p.placeId === id) || null;
  }

  function read(id) {
    const piece = id ? world.piece(id) : here ? mainPiece(here) : null;
    if (!piece) return false;
    if (piece.placeId !== here || !arrived) return walkTo(piece.placeId, { read: piece.id });
    if (actions.rides.riding) actions.rides.endRide(true);
    closeUp = false;
    return world.open(piece.id);
  }

  /** From a close-up back to the stop's view (or home). */
  function back() {
    if (world.isOpen) { world.close(); return true; }
    if (!closeUp) return false;
    closeUp = false;
    document.documentElement.classList.remove('closeup');
    actions.retract();
    if (here) rig.flyTo(stroll.viewOf(here)); else rig.flyTo(null, { home: true });
    return true;
  }

  return {
    walkTo, home, step, read, back, mainPiece,
    get here() { return here; },
    get arrived() { return arrived; },
    get closeUp() { return closeUp; },
    /** The camera came in close to something at this stop (an item, a shelf, a deco stall). */
    markCloseUp() { closeUp = true; document.documentElement.classList.add('closeup'); },
    stopView: () => (here ? stroll.viewOf(here) : { pos: rig.home.pos.clone(), target: rig.home.target.clone() }),
  };
}

