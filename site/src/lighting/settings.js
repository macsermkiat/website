// Every number that shapes the night lives here, so tuning is one file.
// Colours are sRGB hex (three converts them to linear); intensities are three.js physical units
// (a point light's intensity ~ Blender watts / 4π, a directional light's ~ Blender sun strength).

export const NIGHT = {
  // Tone mapping: AgX (same family as the Blender previews) with a blend toward Blender's "Punchy" look.
  exposure: 1.0,
  punch: 0.35, // 0 = AgX base, 1 = AgX Punchy (power 1.35, saturation 1.4); 0.45 pushed dark wood to red
  vignette: 0.28,
  grain: 0.012,

  sky: {
    zenith: 0x01030d,
    mid: 0x020719,
    horizon: 0x081430,
    ground: 0x07090f,
    glow: 0x221a12, // warm light pollution from the market and town, low on the horizon
    glowStrength: 0.35,
    starIntensity: 1.0,
    milkyWay: 0.35,
    clouds: 0.55,
  },

  moon: {
    // Where the disc sits in the sky: low over the town roofs, just left of centre in the home view
    // (camera [3,9,33] -> [0,2.2,-3] sees the sky from ~3 to ~10 degrees up above the rooftops).
    skyDirection: [-0.13, 0.125, -0.98],
    // Where the moonlight comes from: high on the left and a little toward the viewer, so stall fronts
    // and the cobbles get a cool grazing light and long soft shadows instead of pure backlight.
    // Deliberately not the disc's direction (a moon that low would silhouette every stall front).
    lightDirection: [-0.62, 0.72, 0.3],
    angularRadius: 0.03, // radians; ~2.5x the real moon, for the miniature look
    discIntensity: 4.2, // HDR, so the disc blooms
    halo: 0x5d6fa8,
    haloStrength: 0.55,
    lightColor: 0x9ab0f0,
    lightIntensity: 0.36,
  },

  hemi: { sky: 0x4a5c90, ground: 0x14161c, intensity: 0.38 },

  fog: {
    color: 0x0a1630,
    density: 0.0135,
    // height fog: thicker in the first metres above the cobbles
    mist: 1.1, // extra density multiplier at ground level
    mistHeight: 3.2, // metres over which the mist thins out
  },

  env: {
    intensity: 0.4, // the synthetic night (scene.environment)
    captureIntensity: 0.45, // the captured market (scene.environment on full)
    probeIntensity: 1.0, // local probes on copper, glass and glaze (captured radiance, physical)
    // No periodic refresh: the market is static apart from the rides and the crowd. The global map is
    // re-captured (one cube face per frame, six frames) only once the snow has settled after a toggle,
    // or when the engine calls refreshEnvironment() after changing the lights.
    settle: 0.5, // seconds after the snow blend reaches its target before the re-capture starts
  },

  // clamp caps what feeds the bloom (by the brightest channel, so hue is kept): a bulb (max 6) and a
  // specular glint on copper (hundreds) both enter at <= clamp, so a few glint pixels cannot outshine
  // a string of bulbs. factors weight the five blur levels (tight to wide): a crisp core with a short
  // tail, so the bulbs read as dots with a soft rim, as in the Cycles preview, not as blobs.
  bloom: { strength: 0.4, radius: 0.0, threshold: 1.6, knee: 1.2, clamp: 5, factors: [1.0, 0.3, 0.09, 0.03, 0.01] },
  // the lite profile blooms at half resolution, where every level is twice as wide on screen:
  // shift the weight toward the tight levels so the moon halo and lamp glows match full
  bloomHalf: { strength: 0.4, factors: [1.0, 0.15, 0.03, 0.006, 0.0] },

  // "size" of the point and spot lights for direct specular (see shading.js): a roughness floor
  lightSize: { minRoughness: 0.32, minClearcoatRoughness: 0.3 },

  // local glows (shading.js): cheap diffuse light with no shadow, evaluated per fragment
  glow: {
    // the bulb strings light what hangs near them (garland, lambrequin); 0.6 lit the fascia board
    // behind the bulbs to lightness 0.44 against 0.26 in Cycles (0.4 still gave 0.38)
    bulbs: { intensity: 0.25, reach: 0.9, maxLength: 5, maxHeight: 1.0 },
    // Every section and deco stall gets an interior glow at its light_ empty (dropped by `drop`),
    // whether or not the budget gave it a real light, so every stall front reads warm from the home
    // view. It is one-sided (only faces turned toward it are lit, so it cannot shine out through a
    // wall), and clipped below `floor` metres above the stall's base (no halo on the ground around
    // the walls) and above `ceiling` metres over the empty (the roof does not glow).
    // Intensity by case: `lit`, the stall's real light has a shadow (the glow stands in for the
    // light its walls bounce); `unshadowed`, a real light with no shadow; `only`, no real light.
    interior: { lit: 9, unshadowed: 6, only: 16, reach: 2.6, drop: 0.3, floor: 0.3, ceiling: 0.15 },
  },

  // faint cool rim on edges that face the moon, for figures and posts in front of the stalls.
  // It is added as radiance, not multiplied by albedo (the crowd's coats are albedo 0.01-0.07), and
  // only on dark materials: it fades out between albedo `dark[0]` and `dark[1]`, so wood walls stay
  // near-black on their moon side as in Cycles while the coats keep their outline
  rim: { color: 0x9fb4ff, strength: 0.06, power: 1.6, dark: [0.07, 0.16] },

  // Emissives the lighting owns: bulbs_ (bulb_warm / bulb_cold) and window_warm.
  emissive: {
    warm: { color: [1.0, 0.62, 0.3], intensity: 6 },
    cold: { color: [0.62, 0.76, 1.0], intensity: 5.0 },
    window: 1.5,
  },

  // Warm real-time lights at light_ empties, by kind (three.js units; colour temperature in Kelvin).
  warm: {
    kelvin: 2900, // used only when color is not given
    color: [1.0, 0.6, 0.3], // linear: the Cycles previews' light colour (nmlib/render.py)
    frontColor: [1.0, 0.7, 0.36], // a little paler than the interior, so the cobbles in front read cream, not pink
    interiorShadow: 0.95, // near-opaque: no light through the walls
    // The static cube shadow of an interior light: the kernel is wide (a lamp has a size), and taken
    // with 12 taps rather than three's 5, so light through a hairline gap between wall planks spreads
    // into a faint soft band instead of a sharp dashed streak across the ground
    // The bias is in perspective depth, so it must be tiny: pass 2's -0.002 with a 5 cm near plane
    // was about 0.3 m at 2.7 m, which let the light through the wall base onto a pale strip of ground.
    // With near 0.15 m, -0.0003 is about 1.4 cm at 2.7 m and 2 mm at 1 m.
    shadowMap: { size: 512, radius: 5, near: 0.15, bias: -0.0003, normalBias: 0.02, taps: 12 },
    // a shadow-only shell just outside the walls of a stall with a shadowed interior light (lights.js
    // shadowBlocker): closes the plank gaps and the slot under the walls. floor: height over the base
    blocker: { pad: 0.012, floor: 0.05 },
    // interior lights with no shadow (the lite market's four): dropped below the eaves, short and at
    // 70 %, so the leak through the walls stays at the foot of the stall and the roof does not glow
    // (at 100 % the lite back wall washed out to lightness 0.72 against 0.39 in Cycles); the interior
    // glow brings the stall's warmth back up
    unshadowed: { distance: 3.0, scale: 0.7, drop: 0.3 },
    // point: inside a stall; a short reach keeps unshadowed ones from leaking far through the walls
    // front: a point under the front eave (the front fill: garland, counter front, sign, cobbles)
    // spot: stage lights high on a landmark, or any light_ empty with userData.type = 'spot'
    // front: the front fill is a wide spot under the front eave aimed down and out (frontAngle, rad),
    // so it lights the counter front, the sign and the cobbles but not the fascia above it
    section: { point: 40, front: 13, frontAngle: 1.15, spot: 34, pointDistance: 4.2, frontDistance: 8, spotDistance: 8 },
    landmark: { point: 26, spot: 40, pointDistance: 10, spotDistance: 12 },
    deco: { point: 18, front: 8, frontAngle: 1.15, spot: 20, pointDistance: 3.6, frontDistance: 6, spotDistance: 7 },
    lamp: { point: 7, spot: 12, pointDistance: 10, spotDistance: 10 },
    tree: { point: 16, spot: 20, pointDistance: 10, spotDistance: 10 },
    strings: { point: 10, spot: 14, pointDistance: 12, spotDistance: 12 },
    other: { point: 10, spot: 16, pointDistance: 8, spotDistance: 8 },
  },

  snow: {
    // 0.017 at most: past that the stall lights and bulbs drown in the fog (the engine caps it there
    // too, see SNOW_FOG_MAX in main.js; with this value its cap changes nothing)
    fogDensity: 0.017,
    fogColor: 0x273250, // a touch paler than 0x222c4a, so the thinner fog still reads as falling snow
    hemiBoost: 1.35, // snow cover bounces more light
    moonDim: 0.55,
    starsLeft: 0.12,
    clouds: 0.95,
    fall: 0.85, // m/s mean
    wind: [0.9, 0.35], // m/s mean drift (x, z)
    gust: 0.8,
  },
};

export const PROFILES = {
  full: {
    shadows: true,
    // 1536² over the market's 84 m shadow box is 5.5 cm a texel, softened by the PCF radius anyway
    shadowMapSize: 1536,
    shadowRadius: 4,
    // the moon's shadow map is redrawn every Nth frame: the stalls and town are still, and people
    // walking with 20 Hz shadows read the same; it cuts the shadow pass's draw calls to a third
    moonShadowEvery: 3,
    // meshes smaller than this (world bounding radius, m) stop casting the moon's shadow once the
    // static interior shadows are drawn: at 5.5 cm a texel their shadow is a blur of a few texels
    minMoonCaster: 0.15,
    msaa: 4,
    bloomScale: 1,
    envSize: 256,
    envCapture: true,
    probes: 6, // local reflection probes for the nearest models with copper, glass or glaze
    probeSize: 128,
    glows: 24, // local glows evaluated per fragment (stall interiors first, then bulb strings)
    adaptive: true, // step down MSAA, then composer pixel ratio, then bloom resolution if slow
    lightBudget: 14,
    shadowedLights: 4, // interior lights of the section stalls nearest the view (static shadow maps)
    snowLayers: [
      // near: big soft flakes, mid, far: fine dust
      { count: 3500, box: 14, size: [0.03, 0.05], soft: 0.9 },
      { count: 18000, box: 36, size: [0.03, 0.045], soft: 0.5 },
      { count: 7000, box: 90, size: [0.04, 0.065], soft: 0.25 },
    ],
    clouds: true,
    grain: true,
  },
  lite: {
    shadows: false,
    shadowMapSize: 0,
    shadowRadius: 0,
    // 2x MSAA: with none, the hairline gaps between counter boards alias into rows of dots
    msaa: 2,
    bloomScale: 0.5,
    envSize: 128,
    envCapture: false,
    probes: 2,
    probeSize: 64,
    glows: 12,
    adaptive: false,
    lightBudget: 4,
    shadowedLights: 0,
    snowLayers: [
      { count: 1200, box: 14, size: [0.032, 0.052], soft: 0.9 },
      { count: 5000, box: 36, size: [0.032, 0.048], soft: 0.5 },
      { count: 1800, box: 90, size: [0.045, 0.07], soft: 0.25 },
    ],
    clouds: false,
    grain: false,
  },
};

/** Approximate sRGB-linear colour of a black body at `k` Kelvin (Tanner Helland's fit, normalised). */
export function kelvinRGB(k) {
  const t = k / 100;
  let r, g, b;
  if (t <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(t) - 161.1195681661;
    b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * Math.pow(t - 60, -0.1332047592);
    g = 288.1221695283 * Math.pow(t - 60, -0.0755148492);
    b = 255;
  }
  const c = (v) => Math.min(255, Math.max(0, v)) / 255;
  return [c(r), c(g), c(b)];
}
