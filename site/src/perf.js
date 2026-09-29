// A frame-time meter for measuring the market on real hardware: open the page with ?perf
// (add ?quality=full or ?quality=lite to pin the market). It shows the median and 95th-percentile frame
// time over the last 240 frames, the frame rate, draw calls and triangles, and "Copy" puts a one-line
// report on the clipboard to paste into NOTES.md.
export function createPerfMeter({ stage, renderer, lite }) {
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
  box.append(text, copy);
  stage.appendChild(box);
  // count every pass of the composer (render, outline, bloom, grade) as one frame
  renderer.info.autoReset = false;
  let calls = 0, triangles = 0;

  function stats() {
    const k = Math.min(n, N);
    const a = Array.from(ft.slice(0, k)).sort((x, y) => x - y);
    const q = (p) => (k ? a[Math.min(k - 1, Math.floor(p * k))] : 0);
    return {
      market: lite ? 'lite' : 'full',
      frames: total,
      p50: +q(0.5).toFixed(1),
      p95: +q(0.95).toFixed(1),
      fps: k ? +(1000 / q(0.5)).toFixed(1) : 0,
      calls,
      triangles,
      pixelRatio: renderer.getPixelRatio(),
      size: `${renderer.domElement.width}x${renderer.domElement.height}`,
      gpu: gpuName(renderer),
      adaptive: globalThis.__lighting?.quality?.level ?? null,
    };
  }
  copy.addEventListener('click', () => {
    const s = stats();
    const line = `${s.market} market, ${s.gpu}, ${s.size} @${s.pixelRatio}x: median ${s.p50} ms (${s.fps} fps), p95 ${s.p95} ms, ${s.calls} draw calls, ${s.triangles} triangles`;
    navigator.clipboard?.writeText(line).then(() => { copy.textContent = 'Copied'; setTimeout(() => (copy.textContent = 'Copy'), 1500); }, () => {});
  });

  return {
    stats,
    /** Call once per rendered frame with the unclamped frame time in seconds. */
    frame(dt) {
      calls = renderer.info.render.calls;
      triangles = renderer.info.render.triangles;
      renderer.info.reset();
      if (dt > 0 && dt < 2) { ft[n++ % N] = dt * 1000; total++; }
      const now = performance.now();
      if (now - last < 500) return;
      last = now;
      const s = stats();
      text.textContent = `${s.market} · ${s.fps} fps\nmedian ${s.p50} ms · p95 ${s.p95} ms\n${s.calls} draws · ${(s.triangles / 1000).toFixed(0)}k tris\n${s.size} @${s.pixelRatio}x`;
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
