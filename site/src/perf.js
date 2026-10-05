// A frame-time meter for measuring the market on real hardware: open the page with ?perf
// (add ?quality=full or ?quality=lite to pin the market, ?lod=<metres> to pin the crowd's distance LOD and
// ?governor=0 to stop the engine's own step-downs). It shows the median and 95th-percentile frame time over the
// last 240 frames, the frame rate, draw calls and triangles, and "Copy" puts a one-line report on the clipboard.
// "Tour" visits five views (home, Glühwein, bandstand, Bücherstand, Riesenrad) for a few seconds each and copies
// one line per view: the numbers NOTES.md asks for.
export function createPerfMeter({ stage, renderer, lite, governor, tour }) {
  const N = 240;
  const ft = new Float32Array(N);
  let n = 0, total = 0, last = 0;
  const box = document.createElement('div');
  box.className = 'perf';
  box.setAttribute('aria-live', 'off');
  const text = document.createElement('pre');
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'btn';
  copy.textContent = 'Copy';
  const tourBtn = document.createElement('button');
  tourBtn.type = 'button';
  tourBtn.className = 'btn';
  tourBtn.textContent = 'Tour';
  box.append(text, copy, tourBtn);
  stage.appendChild(box);
  // count every pass of the composer (render, outline, bloom, grade) as one frame
  renderer.info.autoReset = false;
  let calls = 0, triangles = 0;

  function stats(samples = null) {
    const a = (samples ? samples.slice() : Array.from(ft.slice(0, Math.min(n, N)))).sort((x, y) => x - y);
    const q = (p) => (a.length ? a[Math.min(a.length - 1, Math.floor(p * a.length))] : 0);
    return {
      market: lite ? 'lite' : 'full',
      frames: total,
      p50: +q(0.5).toFixed(1),
      p95: +q(0.95).toFixed(1),
      fps: a.length ? +(1000 / q(0.5)).toFixed(1) : 0,
      calls,
      triangles,
      pixelRatio: renderer.getPixelRatio(),
      size: `${renderer.domElement.width}x${renderer.domElement.height}`,
      gpu: gpuName(renderer),
      adaptive: globalThis.__lighting?.quality?.level ?? null,
      governor: governor?.() || null,
    };
  }
  const line = (s, label = '') => `${label ? label + ': ' : ''}${s.market} market, ${s.gpu}, ${s.size} @${s.pixelRatio}x: median ${s.p50} ms (${s.fps} fps), p95 ${s.p95} ms, ${s.calls} draw calls, ${s.triangles} triangles, lighting step ${s.adaptive ?? '-'}, governor ${s.governor ? `${s.governor.level} (LOD ${s.governor.lodFar} m)` : '-'}`;
  const toClipboard = (t, btn, label) => navigator.clipboard?.writeText(t).then(() => { btn.textContent = 'Copied'; setTimeout(() => (btn.textContent = label), 1500); }, () => {});
  copy.addEventListener('click', () => toClipboard(line(stats()), copy, 'Copy'));

  // ---------- the tour ----------
  const STOPS = [['home', null], ['Glühwein', 'glueh'], ['bandstand', 'band'], ['Bücherstand', 'books'], ['Riesenrad', 'ferris'], ['home again', null]];
  let run = null; // { i, phase: 'fly' | 'measure', t0, n0, lines, stops }
  let tourJson = null;
  function startTour() {
    if (!tour || run) return;
    run = { i: -1, lines: [], stops: [], t0: 0 };
    tourBtn.textContent = 'Touring…';
    nextStop();
  }
  function nextStop() {
    run.i++;
    if (run.i >= STOPS.length) {
      const out = run.lines.join('\n');
      const run_lines = run.stops;
      run = null;
      text.dataset.tour = out;
      tourJson = { lines: run_lines, url: location.href, at: new Date().toISOString() };
      console.info('[perf] tour\n' + out);
      tourBtn.textContent = 'Tour';
      toClipboard(out, tourBtn, 'Tour');
      return;
    }
    const [, id] = STOPS[run.i];
    if (id) tour.openPlace(id); else tour.resetView();
    run.phase = 'fly';
    run.t0 = performance.now();
  }
  function tourFrame(now) {
    if (!run) return;
    if (run.phase === 'fly' && now - run.t0 > 2500) { run.phase = 'measure'; run.t0 = now; run.samples = []; }
    else if (run.phase === 'measure' && now - run.t0 > 4000 && run.samples.length >= 10) {
      const st = stats(run.samples);
      run.lines.push(line(st, STOPS[run.i][0]));
      run.stops.push({ view: STOPS[run.i][0], ...st });
      nextStop();
    }
  }
  tourBtn.addEventListener('click', startTour);

  return {
    stats,
    startTour,
    get tourResult() { return text.dataset.tour || null; },
    /** The finished tour, one record per view (tests/perf.mjs reads it). */
    get tourData() { return tourJson; },
    /** Call once per rendered frame with the unclamped frame time in seconds. */
    frame(dt) {
      calls = renderer.info.render.calls;
      triangles = renderer.info.render.triangles;
      renderer.info.reset();
      if (dt > 0 && dt < 2) { ft[n++ % N] = dt * 1000; total++; }
      // the tour keeps every frame, however slow (on software GL a frame can take seconds: the tour must still end)
      if (dt > 0 && run?.phase === 'measure') run.samples.push(dt * 1000);
      const now = performance.now();
      tourFrame(now);
      if (now - last < 500) return;
      last = now;
      const s = stats();
      text.textContent = `${s.market} · ${s.fps} fps\nmedian ${s.p50} ms · p95 ${s.p95} ms\n${s.calls} draws · ${(s.triangles / 1000).toFixed(0)}k tris\n${s.size} @${s.pixelRatio}x${s.governor ? ` · gov ${s.governor.level}` : ''}`;
    },
  };
}

function gpuName(renderer) {
  try {
    const gl = renderer.getContext();
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    return String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)).slice(0, 60);
  } catch {
    return 'unknown GPU';
  }
}
