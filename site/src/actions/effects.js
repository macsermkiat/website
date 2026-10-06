// Steam over the Glühwein pot and smoke over the grill: soft sprites that rise and fade.
import * as THREE from 'three';

let smokeTex = null;
function texture() {
  if (smokeTex) return smokeTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  let s = 3;
  const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 14; i++) {
    const x = 40 + R() * 48, y = 40 + R() * 48, r = 18 + R() * 26;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, 'rgba(255,255,255,.18)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  }
  smokeTex = new THREE.CanvasTexture(c);
  return smokeTex;
}

// One draw per emitter (round 10): the puffs are instances of one camera-facing quad (an InstancedMesh with
// three's sprite shader, per-instance opacity), not one Sprite each. They are drawn back to front, sorted by the
// camera of the frame before, as three sorted the sprites.
let puffGeometry = null;
function puffMaterial(color) {
  return new THREE.ShaderMaterial({
    name: 'effect_puff',
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { diffuse: { value: new THREE.Color(color) }, map: { value: null } }]),
    vertexShader: /* glsl */`
      attribute float iOpacity;
      varying vec2 vUv;
      varying float vOpacity;
      #include <common>
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        vOpacity = iOpacity;
        vec4 mvPosition = modelViewMatrix * vec4( instanceMatrix[ 3 ].xyz, 1.0 );
        vec2 scale = vec2( length( instanceMatrix[ 0 ].xyz ), length( instanceMatrix[ 1 ].xyz ) );
        mvPosition.xy += position.xy * scale;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 diffuse;
      uniform sampler2D map;
      varying vec2 vUv;
      varying float vOpacity;
      #include <common>
      #include <fog_pars_fragment>
      void main() {
        vec4 diffuseColor = vec4( diffuse, vOpacity ) * texture2D( map, vUv );
        vec3 outgoingLight = diffuseColor.rgb;
        #include <opaque_fragment>
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
    transparent: true,
    depthWrite: false,
    fog: true,
  });
}

export function createEmitter(scene, pos, { color, n, rise, spread, scale, opacity }) {
  puffGeometry ||= new THREE.PlaneGeometry(1, 1);
  const mat = puffMaterial(color);
  mat.uniforms.map.value = texture();
  const im = new THREE.InstancedMesh(puffGeometry, mat, n);
  im.name = 'effect_puff';
  const op = new THREE.InstancedBufferAttribute(new Float32Array(n), 1);
  op.setUsage(THREE.DynamicDrawUsage);
  im.geometry = puffGeometry.clone(); // its own instance attribute
  im.geometry.setAttribute('iOpacity', op);
  im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  // bounds: the column the puffs rise in (the instances move; the quad's own bounds say nothing about them)
  im.boundingSphere = new THREE.Sphere(new THREE.Vector3(pos.x, pos.y + rise / 2, pos.z), rise / 2 + spread + scale * 1.3);
  im.raycast = () => {};
  const eye = new THREE.Vector3(0, 0, 1e6);
  im.onBeforeRender = (r, sc, camera) => { eye.setFromMatrixPosition(camera.matrixWorld); };
  scene.add(im);
  const arr = [];
  for (let i = 0; i < n; i++) arr.push({ t: i / n, p: new THREE.Vector3(), sc: 0, op: 0, d: 0 });
  const m = new THREE.Matrix4();
  const em = {
    pos, base: opacity, boost: 0, mesh: im,
    dispose() { im.removeFromParent(); im.geometry.dispose(); mat.dispose(); arr.length = 0; },
    update(dt, still) {
      em.boost *= Math.exp(-dt * 0.8);
      const o = em.base * (1 + em.boost);
      for (const q of arr) {
        if (!still) q.t = (q.t + dt / (rise * 1.3)) % 1;
        const t = q.t;
        q.p.set(pos.x + Math.sin(t * 6 + q.t * 40) * spread * t, pos.y + t * rise, pos.z + Math.cos(t * 5) * spread * 0.5 * t);
        q.sc = scale * (0.3 + t);
        q.op = o * Math.sin(t * Math.PI);
        q.d = q.p.distanceToSquared(eye);
      }
      // back to front, as three draws transparent sprites
      const order = arr.slice().sort((a, b) => b.d - a.d);
      order.forEach((q, i) => {
        m.makeScale(q.sc, q.sc, 1).setPosition(q.p);
        im.setMatrixAt(i, m);
        op.array[i] = q.op;
      });
      im.instanceMatrix.needsUpdate = true;
      op.needsUpdate = true;
    },
  };
  return em;
}
