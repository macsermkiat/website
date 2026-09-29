// The frame-time governor (full market only). The lighting module already steps its own costs down when the
// median frame is slower than ~55 fps (MSAA, pixel ratio, bloom size, moon-shadow rate). If the market still
// runs slower than ~30 fps after that, this takes the next steps, one per window of 120 frames:
//   1. the crowd's distance LOD comes in to 12 m      2. to 6 m
//   3. everyone draws their lite figure, and the crowd stops casting moon shadows
//   4. the "Running slowly? Switch to the lite market" button
// It never steps back up. Hidden-tab and loading hitches (frames over 250 ms) are not counted.
export const TARGET_MS = 33.3;

export function createGovernor({ crowd, lightingStats, suggestLite, onStep, target = TARGET_MS, window = 120 }) {
  const ft = new Float32Array(window);
  let n = 0, frames = 0;
  const state = { level: 0, lodFar: crowd.lod?.far ?? null, p50: null, target, steps: [] };
  const steps = [
    () => crowd.setLod(Math.min(crowd.lod.far, 12)),
    () => crowd.setLod(Math.min(crowd.lod.far, 6)),
    () => { crowd.setLod(0); crowd.group.traverse((o) => { if (o.isMesh) o.castShadow = false; }); },
    () => suggestLite(),
  ];
  return {
    state,
    frame(dt) {
      frames++;
      if (frames < 90 || !(dt > 0) || dt > 0.25 || state.level >= steps.length) return;
      ft[n++] = dt * 1000;
      if (n < window) return;
      n = 0;
      const p50 = Array.from(ft).sort((a, b) => a - b)[window >> 1];
      state.p50 = +p50.toFixed(1);
      if (p50 <= target) return;
      // let the lighting module make its (cheaper) cuts first
      const L = lightingStats?.();
      if (L && L.level != null && L.level < 2 && frames < 900) return;
      steps[state.level]();
      state.level++;
      state.lodFar = crowd.lod?.far ?? null;
      state.steps.push({ at: frames, p50: state.p50, level: state.level });
      onStep?.({ ...state });
    },
  };
}
