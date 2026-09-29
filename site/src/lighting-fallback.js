// Minimal stand-in for the lighting designer's module (site/src/lighting/index.js).
// Same interface: createLighting({ scene, renderer, camera, lite }) -> { composer, update(dt, t), setSnow(on), dispose() }.
// Moonlit sky and hemisphere fill, a moon with soft shadows (full market only), fog, a night environment map for
// reflections, and bloom so the emissive bulbs glow.
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

function softDot(inner = 'rgba(255,255,255,1)') {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, inner); gr.addColorStop(0.4, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function skyMaterial() {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: new THREE.Color(0x02040c) }, mid: { value: new THREE.Color(0x0c1433) }, bot: { value: new THREE.Color(0x3a2a44) } },
    vertexShader: 'varying vec3 vP;void main(){vP=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: 'uniform vec3 top,mid,bot;varying vec3 vP;void main(){float h=vP.y;vec3 c=h>0.15?mix(mid,top,smoothstep(.15,.8,h)):mix(bot,mid,smoothstep(-.05,.15,h));gl_FragColor=vec4(c,1.);\n#include <colorspace_fragment>\n}',
  });
}

export function createLighting({ scene, renderer, camera, lite }) {
  const added = [];
  const add = (o) => { scene.add(o); added.push(o); return o; };

  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = !lite;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const fogColor = new THREE.Color(0x0b0f22);
  scene.fog = new THREE.FogExp2(fogColor, 0.016);
  scene.background = fogColor.clone();

  // sky, stars and moon
  add(new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), skyMaterial()));
  const n = lite ? 700 : 1800, pos = new Float32Array(n * 3);
  let s = 7;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < n; i++) {
    const u = R() * 6.283, v = 0.08 + R() * 0.9, rr = 380;
    pos[i * 3] = Math.cos(u) * Math.cos(v * 1.4) * rr; pos[i * 3 + 1] = Math.sin(v * 1.4) * rr; pos[i * 3 + 2] = Math.sin(u) * Math.cos(v * 1.4) * rr;
  }
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dot = softDot();
  add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85, map: dot, depthWrite: false })));
  const moon = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: softDot('rgba(255,244,220,1)'), color: new THREE.Color(2.2, 2.0, 1.7), fog: false, depthWrite: false })));
  moon.position.set(-120, 150, -260); moon.scale.set(26, 26, 1);
  const halo = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: 0x6a78b0, fog: false, transparent: true, opacity: 0.25, depthWrite: false })));
  halo.position.copy(moon.position); halo.scale.set(110, 110, 1);

  // moonlight and fill
  const hemi = add(new THREE.HemisphereLight(0x3a4a86, 0x2a1a10, 1.1));
  const moonLight = add(new THREE.DirectionalLight(0x9fb2ff, 1.3));
  moonLight.position.set(-30, 45, 25);
  if (!lite) {
    moonLight.castShadow = true;
    moonLight.shadow.mapSize.set(2048, 2048);
    Object.assign(moonLight.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, near: 1, far: 140 });
    moonLight.shadow.bias = -0.0004;
    moonLight.shadow.normalBias = 0.03;
  }

  // a dim night environment for reflections: dark sky, warm glows low on the horizon
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  envScene.add(new THREE.Mesh(new THREE.SphereGeometry(10, 16, 8), skyMaterial()));
  const glow = new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 1.8, 0.8) });
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.8, 8, 6), glow);
    m.position.set(Math.cos(a) * 8, 0.6, Math.sin(a) * 8);
    envScene.add(m);
  }
  const env = pmrem.fromScene(envScene, 0.04).texture;
  scene.environment = env;
  scene.environmentIntensity = 0.35;
  pmrem.dispose();

  // post: render -> bloom -> tone map + sRGB
  const size = renderer.getSize(new THREE.Vector2());
  const target = new THREE.WebGLRenderTarget(size.x || 256, size.y || 256, { type: THREE.HalfFloatType, samples: lite ? 0 : 4 });
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x || 256, size.y || 256), lite ? 0.7 : 0.85, 0.55, 1.0);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  let snowOn = false;
  return {
    composer,
    update() {},
    setSnow(on) {
      snowOn = on;
      scene.fog.density = on ? 0.02 : 0.016;
      scene.fog.color.set(on ? 0x151a2e : 0x0b0f22);
      scene.background.copy(scene.fog.color);
      hemi.intensity = on ? 1.35 : 1.1;
    },
    dispose() {
      added.forEach((o) => o.removeFromParent());
      env.dispose();
      composer.dispose?.();
    },
    get snow() { return snowOn; },
  };
}
