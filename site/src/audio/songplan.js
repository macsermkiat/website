// The ballad's road map, from the music writer's manifest: where the song goes after each stretch.
//
//   head (0 .. loopEnd) -> the loop (loopStart .. loopEnd), `passes` times in all -> the written ending
//   (loopEnd .. the end of the file: the out head, ritardando, fermata) -> a short silence -> from the top.
//
// Pass 1 is the first time through the loop region, which the head runs straight into. On every second pass
// (2, 4, ...) the tenor plays his second written chorus: the manifest's `alternates` swap the sax and room stems
// for other files between `start` and `end`. The swap happens 0.25 s inside those edges, where the manifest
// promises the alternate files are identical to the main ones, so the cut cannot be heard.
//
// Pure functions of numbers: the stems player schedules the segments, the tests check the road map.

const EDGE = 0.25;

/**
 * plan(manifest, { passes }) -> { loopStart, loopEnd, end, passes, alt, segment(pos, pass), next(seg), length }
 * A segment is { from, to, pass, alt } in song seconds: `alt` true when the alternate stems play in it.
 */
export function songPlan(manifest, { passes, fileEnd } = {}) {
  const num = (v, d) => (Number.isFinite(Number(v)) ? Number(v) : d);
  const duration = num(manifest.duration, 0);
  const loopStart = Math.max(0, num(manifest.loopStart, 0));
  const loopEnd = num(manifest.loopEnd, duration);
  const hasLoop = loopEnd > loopStart + 0.5;
  // the ending runs to the last sound of the file (musicEnds, plus the room's tail), not past the audio
  const tail = num(manifest.ending?.musicEnds, duration);
  const end = Math.min(fileEnd || Infinity, Math.max(tail + 2.5, loopEnd), duration || Infinity);
  const n = Math.max(1, Math.round(num(passes ?? manifest.ending?.passes, 3)));
  const a = (manifest.alternates || []).find((x) => x && x.stems && num(x.end, 0) > num(x.start, 0) + 2 * EDGE + 1);
  const alt = a && hasLoop ? {
    stems: a.stems,
    start: num(a.start, 0), // the alternate files' sample 0 is this song time
    from: Math.max(loopStart, num(a.start, 0) + EDGE),
    to: Math.min(loopEnd, num(a.end, 0) - EDGE),
  } : null;
  const altPass = (pass) => !!alt && pass % 2 === 0;

  /** The stretch starting at `pos` in `pass`: up to the next place where something changes. */
  function segment(pos, pass) {
    const stops = [];
    if (hasLoop && pos < loopEnd) stops.push(loopEnd);
    else stops.push(end);
    if (altPass(pass) && pos < loopEnd) {
      if (pos < alt.from) stops.push(alt.from);
      else if (pos < alt.to) stops.push(alt.to);
    }
    const to = Math.min(...stops);
    return { from: pos, to, pass, alt: altPass(pass) && pos >= alt.from && pos < alt.to };
  }

  /** What follows a segment; null at the end of the song (the player rests, then starts from the top). */
  function next(seg) {
    if (seg.to >= end - 1e-6) return null;
    if (hasLoop && Math.abs(seg.to - loopEnd) < 1e-6) {
      if (seg.pass < n) return segment(loopStart, seg.pass + 1);
      return segment(loopEnd, seg.pass); // the written ending
    }
    return segment(seg.to, seg.pass);
  }

  /** Song time -> the same point after `t` seconds of playing from (pos, pass); for the mix and resuming. */
  function advance(pos, pass, t) {
    let seg = segment(pos, pass);
    let left = t;
    for (let guard = 0; guard < 100; guard++) {
      const len = seg.to - seg.from;
      if (left < len) return { pos: seg.from + left, pass: seg.pass };
      left -= len;
      const nx = next(seg);
      if (!nx) return { pos: end, pass: seg.pass, ended: true };
      seg = nx;
    }
    return { pos: seg.from, pass: seg.pass };
  }

  const length = hasLoop ? loopEnd + (n - 1) * (loopEnd - loopStart) + (end - loopEnd) : end;
  return { loopStart, loopEnd, end, passes: n, alt, hasLoop, segment, next, advance, length };
}
