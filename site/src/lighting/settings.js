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
    refresh: 30, // seconds between re-captures of the market (full only; spread over 6 frames)
  },

  // factors weight the five blur levels, tight to wide: a crisp core with a short soft tail
  // clamp caps what feeds the bloom (by the brightest channel, so hue is kept): a bulb (max 6) and a
  // specular glint on copper (hundreds) both enter at <= clamp, so a few glint pixels cannot outshine
  // a string of bulbs. factors weight the five blur levels (tight to wide): a crisp core, short tail.
  bloom: { strength: 0.4, radius: 0.0, threshold: 1.6, knee: 1.2, clamp: 5, factors: [1.0, 0.4, 0.13, 0.045, 0.015] },
  // the lite profile blooms at half resolution, where every level is twice as wide on screen:
  // shift the weight toward the tight levels so the moon halo and lamp glows match full
  bloomHalf: { strength: 0.4, factors: [1.0, 0.2, 0.04, 0.008, 0.0] },

  // "size" of the point and spot lights for direct specular (see shading.js): a roughness floor
  lightSize: { minRoughness: 0.32, minClearcoatRoughness: 0.3 },

  // local glows (shading.js): the bulb strings light what hangs near them (garland, lambrequin)
  glow: { bulbs: { intensity: 0.6, reach: 1.1, maxLength: 5, maxHeight: 1.0 } },

  // faint cool rim on edges that face the moon (figures and posts in front of the stalls)
  // (radiance at the very edge, not multiplied by albedo: the crowd's coats are albedo 0.01-0.07)
  rim: { color: 0x9fb4ff, strength: 0.09, power: 1.6 },

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
    bounce: { intensity: 9, reach: 2.4 }, // unshadowed glow standing in for wall bounce (shadowed stalls)
    // interior lights with no shadow: dropped below the eaves, shorter and a little dimmer
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
    fogDensity: 0.024,
    fogColor: 0x222c4a,
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
    shadowMapSize: 2048,
    shadowRadius: 4,
    // the moon's shadow map is redrawn every Nth frame: the stalls and town are still, and people
    // walking at 30 Hz shadows read the same; it halves the shadow pass's draw calls
    moonShadowEvery: 2,
    msaa: 4,
    bloomScale: 1,
    envSize: 256,
    envCapture: true,
    envRefresh: true,
    probes: 6, // local reflection probes for the nearest models with copper, glass or glaze
    probeSize: 128,
    glows: 16, // local glows evaluated per fragment (bulb strings + bounce)
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
    msaa: 0,
    bloomScale: 0.5,
    envSize: 128,
    envCapture: false,
    envRefresh: false,
    probes: 2,
    probeSize: 64,
    glows: 6,
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
