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
    // Round 2 (Codex: "reduce glare and moon dominance"): the disc from 0.03 to 0.02 rad (~1.7x the
    // real moon; it was the brightest, biggest thing in the home view), 4.2 -> 2.8 so it blooms only at
    // its core, and a halo of 0.3 (was 0.55), which had lit a wide pale disc of sky over the town
    angularRadius: 0.02,
    discIntensity: 2.8,
    halo: 0x5d6fa8,
    haloStrength: 0.3,
    lightColor: 0x9ab0f0,
    lightIntensity: 0.36,
  },

  // Round 2: the ground colour is the warm bounce off the lit square (was a cold near-black #14161c).
  // It lifts what faces sideways and down (the crowd's coats and faces, the town's facades, the
  // underside of eaves) toward warm grey, while what faces up (roofs, cobbles) keeps the cool sky fill,
  // so the night is not flattened: the tops stay blue, the fronts get a little of the market's light
  hemi: { sky: 0x4a5c90, ground: 0x3a2c22, intensity: 0.4 },

  fog: {
    color: 0x0a1630,
    // Round 2: 0.0135 -> 0.0115, so the facades 50-60 m out keep their timbering and windows (the
    // transmittance there goes from 0.58 to 0.67) while the church and the far town still sink into haze
    density: 0.0115,
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
  // pass 4: strength 0.4 -> 0.32 and the second level 0.3 -> 0.2: the bulbs were 17-21 px blobs (Cycles
  // 13-16) and the left ones merged into one 143 px run (now 12-19 px; see README for what is left)
  bloom: { strength: 0.34, radius: 0.0, threshold: 1.6, knee: 1.2, clamp: 5, factors: [1.0, 0.2, 0.07, 0.025, 0.01] },
  // the lite profile blooms at half resolution, where every level is twice as wide on screen:
  // shift the weight toward the tight levels so the moon halo and lamp glows match full
  bloomHalf: { strength: 0.34, factors: [1.0, 0.1, 0.025, 0.005, 0.0] },

  // "size" of the point and spot lights for direct specular (see shading.js): a roughness floor
  lightSize: { minRoughness: 0.32, minClearcoatRoughness: 0.3 },

  // local glows (shading.js): cheap diffuse light with no shadow, evaluated per fragment
  glow: {
    // the bulb strings light what hangs near them (garland, lambrequin); 0.6 lit the fascia board
    // behind the bulbs to lightness 0.44 against 0.26 in Cycles (0.4 still gave 0.38)
    // (0.25 still left the lambrequin at 0.35; pass 4: 0.18)
    bulbs: { intensity: 0.18, reach: 0.9, maxLength: 5, maxHeight: 1.0 },
    // Every section and deco stall gets an interior glow at its light_ empty (dropped by `drop`),
    // whether or not the budget gave it a real light, so every stall front reads warm from the home
    // view. It is one-sided (only faces turned toward it are lit, so it cannot shine out through a
    // wall), and clipped below `floor` metres above the stall's base (no halo on the ground around
    // the walls) and above `ceiling` metres over the empty (the roof does not glow).
    // Intensity by case: `lit`, the stall's real light has a shadow (the glow stands in for the
    // light its walls bounce); `unshadowed`, a real light with no shadow; `only`, no real light.
    interior: { lit: 7, unshadowed: 6, only: 16, reach: 2.6, drop: 0.3, floor: 0.3, ceiling: 0.15 },
    // The front of the roof: a one-sided glow `out` m in front of each stall's front light_ empty and
    // `up` m above it, clipped below `below` m under the empty. It lights what faces it above the
    // eave line (the roof's front slope, or the soffit when the lamp hangs under the eave), which the
    // downward front-fill spot cannot reach. Cycles lights that strip with the light_ marker's point
    // light (lightness 0.2-0.37 there; 0.05 in pass 3).
    eave: { intensity: 38, reach: 3.0, out: 0.6, up: 0.5, below: 0.05 },
    // The warm pool on the cobbles around the stall front: a one-sided glow where the front fill hangs,
    // clipped above `ceiling` m over the base, so it lights the ground only (Cycles: warm grey beside
    // the stall, h4 l.27; pass 3: blue, h250, in the stall's moon shadow)
    // Round 2: 11 -> 7.5 and reach 8 -> 6 m: from the home view the pools around the four section
    // stalls were the brightest ground in the frame, bright ovals that read as glare
    spill: { intensity: 7.5, reach: 6, out: 0.8, up: 0.4, ceiling: 0.2 },
    // Round 2: a sign lamp over every stall's slot_sign (lights.js signRect / signFixture): a bar lamp
    // on two arms, `out` m in front of the board and `up` m over its top edge, `span` of the board's
    // width (at most 2 x maxHalf m). Its light is a one-sided line glow along the bar, clipped from
    // `below` m under the board to just under the lamp, so it lights the board and the fascia around it
    // but not the roof. Deco stalls get `decoScale` of it and a lower slot priority.
    // a light_ past the 2 real lights a stall may have (the Bücherstand's counter lamp): a small glow
    lamp: { intensity: 2.5, reach: 1.3 },
    sign: { intensity: 1.5, reach: 1.1, out: 0.3, up: 0.1, below: 0.08, span: 0.75, maxHalf: 1.0, decoScale: 0.6, fixture: true, fixtureEmissive: 2.2, reflectorEmissive: 0.35, hoodRadius: 0.035, color: [1.0, 0.74, 0.45] },
  },

  // Round 2 (Codex: "lift crowd and facade detail without flattening the night"): the town wash
  // (shading.js). Walls of the town ring (world radius past r0, full past r1; the market, the deco
  // rows and the Ferris wheel all sit inside 30 m) get a warm diffuse light, `facing` of it only on
  // walls that face the square, falling off over `height` m up the facade: the market's glow and the
  // street lamps below. Irradiance, linear; 0 turns it off.
  town: { color: [1.0, 0.74, 0.5], intensity: 0.22, r0: 36, r1: 46, height: 9, facing: 0.7 },

  // faint cool rim on edges that face the moon, for figures and posts in front of the stalls.
  // It is added as radiance, not multiplied by albedo (the crowd's coats are albedo 0.01-0.07), and
  // only on dark materials: it fades out between albedo `dark[0]` and `dark[1]`, so wood walls stay
  // near-black on their moon side as in Cycles while the coats keep their outline
  // round 2: 0.06 -> 0.09, so the crowd reads against the dark cobbles from the home view (still dark materials only)
  rim: { color: 0x9fb4ff, strength: 0.09, power: 1.6, dark: [0.07, 0.16] },

  // Emissives the lighting owns: bulbs_ (bulb_warm / bulb_cold) and window_warm.
  emissive: {
    // Round 2: 6 -> 4.8. Entered, a stall's bulbs are 2-3 m from the camera and fill 15-20 px each;
    // at 6 their white cores and halos were the glare the Codex judge saw close up (and they washed the
    // sign board above them). 4.8 keeps a warm-white core that still blooms.
    // Round 2, pass 3: 4.8 -> 3.9 and a deeper amber (1, .62, .30 -> 1, .55, .24). AgX turns any
    // channel past ~4 white, so at 4.8 every bulb seen from 2-3 m was a white disc with an orange rim.
    // At 3.9 the red channel still clears the bloom threshold (1.6) but green and blue stay below
    // white, so the core reads warm cream and the halo stays amber. Bloom strength goes up a hair
    // (0.32 -> 0.34) so the glow from the home view is unchanged.
    warm: { color: [1.0, 0.55, 0.24], intensity: 3.9 },
    cold: { color: [0.62, 0.76, 1.0], intensity: 5.0 },
    window: 1.5,
    // round 2: bulb bounce on the Ferris wheel (lights.js bulbBounce). Its rim, spokes and legs carry
    // hundreds of bulbs, which in Cycles light the cream steel round them evenly; in the browser the
    // bulbs are emissive only and the steel read near black (rides builder, round 2). A model with a
    // rot_wheel gets a faint warm self-light on its opaque materials above `minY` m (or turning with
    // the wheel): albedo x warm x `steel` (gondolas and paint: `other`). Full and lite alike; no lights.
    bounce: { steel: 0.22, other: 0.1, minY: 3, color: [1.0, 0.7, 0.42] },
  },

  // Warm real-time lights at light_ empties, by kind (three.js units; colour temperature in Kelvin).
  warm: {
    kelvin: 2900, // used only when color is not given
    color: [1.0, 0.6, 0.3], // linear: the Cycles previews' light colour (nmlib/render.py)
    frontColor: [1.0, 0.7, 0.36], // a little paler than the interior, so the cobbles in front read cream, not pink
    interiorShadow: 0.95, // near-opaque: no light through the walls
    perModel: 2, // real lights per model at most (BUILD.md); a stall's further light_ empties become glows
    // The static cube shadow of an interior light: the kernel is wide (a lamp has a size), and taken
    // with 12 taps rather than three's 5, so light through a hairline gap between wall planks spreads
    // into a faint soft band instead of a sharp dashed streak across the ground
    // The bias is in perspective depth, so it must be tiny: pass 2's -0.002 with a 5 cm near plane
    // was about 0.3 m at 2.7 m, which let the light through the wall base onto a pale strip of ground.
    // With near 0.15 m, -0.0003 is about 1.4 cm at 2.7 m and 2 mm at 1 m.
    // Round 2, pass 3: radius 5 -> 8 texels (taps 12 -> 16): the shelf boards' shadows on the back
    // wall had a hard 2-3 px edge close up; a real stall lamp is a 10 cm bulb a metre away, so the
    // penumbra should be a few centimetres wide
    shadowMap: { size: 512, radius: 8, near: 0.15, bias: -0.0003, normalBias: 0.02, taps: 16 },
    // a shadow-only shell just outside the walls of a stall with a shadowed interior light (lights.js
    // shadowBlocker): closes the plank gaps and the slot under the walls. floor: height over the base
    blocker: { pad: 0.012, floor: 0.05 },
    // interior lights with no shadow (the lite market's four): dropped below the eaves, short and at
    // 70 %, so the leak through the walls stays at the foot of the stall and the roof does not glow
    // (at 100 % the lite back wall washed out to lightness 0.72 against 0.39 in Cycles); the interior
    // glow brings the stall's warmth back up
    // pass 4: the light is clipped to the stall's interior box (shading.js), so it no longer lights the
    // barge boards, the eave, the plank edges in the wall gaps or the ground. `drop` is only the
    // fallback for a model with no closed interior to clip to.
    unshadowed: { distance: 3.2, scale: 0.5, drop: 0.3, clip: { pad: 0.01, fade: 0.01, floor: 0.3, front: 0.3 } },
    // point: inside a stall; a short reach keeps unshadowed ones from leaking far through the walls
    // front: a point under the front eave (the front fill: garland, counter front, sign, cobbles)
    // spot: stage lights high on a landmark, or any light_ empty with userData.type = 'spot'
    // front: the front fill is a wide spot aimed down and out (frontAngle, rad; frontPenumbra), hung
    // frontLift m above and frontOut m in front of the front light_ empty, aimed at the ground frontAim m
    // out from the empty. It lights the counter, the sign and the cobbles but not the fascia above it.
    // Pass 4: from further out and with a wide full-strength core (penumbra 0.25), its pool spills about
    // a metre further, onto the cobbles beside the stall (warm grey there in Cycles, blue in pass 3),
    // while the sign and the counter top, close under it, get less of it per unit of intensity.
    section: { point: 34, front: 9, frontAngle: 1.4, frontPenumbra: 0.25, frontAim: 1.7, frontLift: 0.4, frontOut: 0.8, spot: 34, pointDistance: 4.2, frontDistance: 9, spotDistance: 8 },
    // round 2: wash/washDistance/washHeight: a landmark light_ higher than washHeight m (the Ferris
    // wheel's hub, 14.7 m up) is a point wash over the steel instead of a downward stage spot (the rides
    // builder: the wheel read near black). It is the landmark's first light.
    landmark: { point: 26, spot: 40, pointDistance: 10, spotDistance: 12, wash: 60, washDistance: 16, washHeight: 8 },
    deco: { point: 18, front: 6, frontAngle: 1.4, frontPenumbra: 0.25, frontAim: 1.7, frontLift: 0.4, frontOut: 0.8, spot: 20, pointDistance: 3.6, frontDistance: 6, spotDistance: 7 },
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
    glows: 28, // local glows evaluated per fragment (stall interiors first, then bulb strings)
    adaptive: true, // step down MSAA, then composer pixel ratio, then bloom resolution if slow
    lightBudget: 14,
    // the place the visitor enters borrows up to this many unshadowed lights for its unlit light_ spots
    focusLights: 2,
    shadowedLights: 4, // interior lights of the section stalls nearest the view (static shadow maps)
    snowLayers: [
      // near: larger soft flakes, mid, far: fine dust. At most 3 cm and softness 0.45: the engine's
      // capFlakes (main.js) asked for that, as bigger, softer near flakes read as grey discs in front of
      // the market; with these values its cap changes nothing, and the test page matches the market
      { count: 3500, box: 14, size: [0.018, 0.03], soft: 0.45 },
      { count: 18000, box: 36, size: [0.02, 0.03], soft: 0.45 },
      { count: 7000, box: 90, size: [0.0185, 0.03], soft: 0.25 },
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
    // 16 (was 12): the four section signs' lamps are glows too (round 2)
    glows: 16,
    adaptive: false,
    lightBudget: 4,
    focusLights: 2,
    shadowedLights: 0,
    snowLayers: [
      { count: 1200, box: 14, size: [0.0185, 0.03], soft: 0.45 },
      { count: 5000, box: 36, size: [0.02, 0.03], soft: 0.45 },
      { count: 1800, box: 90, size: [0.0193, 0.03], soft: 0.25 },
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
