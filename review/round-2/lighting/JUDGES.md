# Judges on lighting, round 2 pass 2

## Ship

Failed:
- Real-GPU frame time measured: Not measured. The adaptive MSAA fallback at 16.7 ms helps, but the number is still unverified

Fixes:
- Run perf.mjs --gpu on Mac's laptop and record the p50; set full msaa=2 if it is over 16.7 ms
- Engineer: add the lighting.raw.focusPlace(id/null) calls in main.js openPlace and the close/reset paths
- Bake AO into the test-bench stall or switch the bench to the shipped stall

## Ship

Failed:
- Real-GPU frame time measured: Not measured (no GPU on this machine); mitigated by the adaptive step at settings adaptiveMs [16.7, 18.2] (index.js:412-430 drops MSAA 4x -> 2x), and README gives the laptop perf.mjs command.
