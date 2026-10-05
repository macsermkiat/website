// The view from inside the mercury-glass ball (round 9, the reflection dive): a post pass between the bloom and the
// grade. It crossfades from a held frame (the reflection filling the view) into the live view from inside the
// glass, which it warps gently like a fisheye seen through curved glass, hushes (a little less colour and contrast,
// a warm silver cast, the glass's rim), and fills with a snow globe's slow drift of silvered flakes.
//   uMix   0 the held frame .. 1 the live view (warped by uWarp)
//   uWarp  0 none .. 1 the full curve and hush (the live view outside the glass is drawn with 0)
import * as THREE from 'three';
import { Pass, FullScreenQuad } from 'three/examples/jsm/postprocessing/Pass.js';

const vert = /* glsl */`
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }`;

const frag = /* glsl */`
uniform sampler2D tDiffuse;
uniform sampler2D tPrev;
uniform float uMix;
uniform float uWarp;
uniform float uTime;
uniform float uAspect;
uniform float uPrevZoom;
uniform float uFlakes;
uniform float uVeil;
varying vec2 vUv;

float hash12( vec2 p ) { vec3 p3 = fract( vec3( p.xyx ) * 0.1031 ); p3 += dot( p3, p3.yzx + 33.33 ); return fract( ( p3.x + p3.y ) * p3.z ); }

vec3 warped( vec2 uv ) {
  vec2 p = ( uv - 0.5 ) * vec2( uAspect, 1.0 );
  float r2 = dot( p, p );
  // barrel: the middle swells, the edges crowd in (the live view is drawn wider than it shows)
  float k = 0.24 * uWarp;
  vec2 q = p / ( 1.0 + k * r2 ) * ( 1.0 - 0.06 * uWarp );
  // the glass splits the colours a hair at the edge
  float ca = 0.006 * uWarp * r2;
  vec2 s = q / vec2( uAspect, 1.0 ) + 0.5;
  vec2 d = normalize( p + 1e-5 ) * ca / vec2( uAspect, 1.0 );
  vec3 c;
  c.r = texture2D( tDiffuse, s + d ).r;
  c.g = texture2D( tDiffuse, s ).g;
  c.b = texture2D( tDiffuse, s - d ).b;
  // hushed: a little less colour and contrast, a warm silver cast
  float l = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
  c = mix( c, vec3( l ), 0.22 * uWarp );
  c = mix( c, c * vec3( 1.04, 0.98, 0.9 ) + 0.012, uWarp );
  c *= 1.0 - 0.1 * uWarp;
  // the inside of the glass: dark toward the rim, with a thin bright ring of mercury
  float r = length( p ) / length( vec2( uAspect, 1.0 ) * 0.5 );
  float vig = smoothstep( 1.08, 0.45, r );
  float rim = smoothstep( 0.86, 0.95, r ) * smoothstep( 1.06, 0.95, r );
  c = c * mix( 1.0, vig, uWarp ) + vec3( 1.0, 0.9, 0.75 ) * rim * 0.07 * uWarp;
  // the snow globe's drift: silvered flakes, three layers, falling and turning slowly
  vec3 fl = vec3( 0.0 );
  for ( int i = 0; i < 3; i++ ) {
    float fi = float( i );
    float sc = 7.0 + fi * 5.0;
    vec2 g = vec2( uv.x * uAspect, uv.y ) * sc;
    g += vec2( sin( uTime * 0.21 + fi * 1.7 ) * 0.6, uTime * ( 0.22 + 0.09 * fi ) );
    g.x += sin( g.y * 0.7 + uTime * 0.3 + fi ) * 0.35;
    vec2 cell = floor( g );
    vec2 f = fract( g ) - 0.5;
    float h = hash12( cell + fi * 17.0 );
    if ( h > 0.62 ) {
      vec2 o = vec2( hash12( cell * 1.3 + 3.1 ), hash12( cell * 2.1 + 7.7 ) ) - 0.5;
      float sz = 0.05 + 0.07 * hash12( cell + 9.2 );
      float tw = 0.6 + 0.4 * sin( uTime * ( 1.5 + h * 3.0 ) + h * 30.0 );
      fl += vec3( 1.0, 0.95, 0.86 ) * smoothstep( sz, 0.0, length( f - o * 0.7 ) ) * tw * ( 0.55 - fi * 0.12 );
    }
  }
  c += fl * 0.5 * uFlakes * uWarp;
  return c;
}

void main() {
  vec3 live = warped( vUv );
  vec2 pz = ( vUv - 0.5 ) / uPrevZoom + 0.5;
  vec3 held = texture2D( tPrev, pz ).rgb;
  vec3 c = mix( held, live, uMix );
  // the sheen of the glass as the view passes through it
  c += vec3( 1.0, 0.92, 0.8 ) * 0.18 * sin( 3.14159 * clamp( uMix, 0.0, 1.0 ) ) * step( 0.001, uMix ) * step( uMix, 0.999 );
  // the glass passing in front of the eye on the way out
  c = mix( c, vec3( 0.9, 0.82, 0.68 ), uVeil );
  gl_FragColor = vec4( c, 1.0 );
}`;

const copyFrag = /* glsl */`
uniform sampler2D tDiffuse;
varying vec2 vUv;
void main() { gl_FragColor = texture2D( tDiffuse, vUv ); }`;

export class DivePass extends Pass {
  constructor() {
    super();
    this.enabled = false;
    this.needsSwap = true;
    this.uniforms = {
      tDiffuse: { value: null }, tPrev: { value: null }, uMix: { value: 1 }, uWarp: { value: 0 }, uTime: { value: 0 },
      uAspect: { value: 1 }, uPrevZoom: { value: 1 }, uFlakes: { value: 1 }, uVeil: { value: 0 },
    };
    this.material = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader: vert, fragmentShader: frag, depthTest: false, depthWrite: false });
    this.copy = new THREE.ShaderMaterial({ uniforms: { tDiffuse: { value: null } }, vertexShader: vert, fragmentShader: copyFrag, depthTest: false, depthWrite: false });
    this.quad = new FullScreenQuad(this.material);
    this.held = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
    this.uniforms.tPrev.value = this.held.texture;
    this.capture = false; // copy the next frame into the held frame
    this.captures = 0;
  }
  setSize(w, h) {
    this.held.setSize(Math.max(1, Math.round(w / 2)), Math.max(1, Math.round(h / 2)));
    this.uniforms.uAspect.value = w / Math.max(1, h);
  }
  render(renderer, writeBuffer, readBuffer) {
    if (this.capture) {
      this.capture = false;
      this.captures++;
      this.copy.uniforms.tDiffuse.value = readBuffer.texture;
      this.quad.material = this.copy;
      renderer.setRenderTarget(this.held);
      this.quad.render(renderer);
      this.quad.material = this.material;
    }
    this.uniforms.tDiffuse.value = readBuffer.texture;
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer);
    if (this.clear) renderer.clear();
    this.quad.render(renderer);
  }
  dispose() { this.material.dispose(); this.copy.dispose(); this.quad.dispose(); this.held.dispose(); }
}
