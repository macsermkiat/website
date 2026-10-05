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
  float R = length( vec2( uAspect, 1.0 ) * 0.5 );
  float r = length( p ) / R;
  // barrel: the middle swells, the edges crowd in (the live view is drawn wider than it shows)
  float k = 0.34 * uWarp;
  vec2 q = p / ( 1.0 + k * r2 ) * ( 1.0 - 0.05 * uWarp );
  // toward the rim the mercury bends the view back on itself: a thin band of the market, mirrored inward
  float band = smoothstep( 0.78, 0.98, r ) * uWarp;
  q = mix( q, q * ( 1.0 - 0.55 * band ) , band );
  // the glass splits the colours a hair at the edge
  float ca = 0.0014 * uWarp * r2;
  vec2 s = q / vec2( uAspect, 1.0 ) + 0.5;
  vec2 d = normalize( p + 1e-5 ) * ca / vec2( uAspect, 1.0 );
  vec3 c;
  c.r = texture2D( tDiffuse, s + d ).r;
  c.g = texture2D( tDiffuse, s ).g;
  c.b = texture2D( tDiffuse, s - d ).b;
  // hushed: a little less colour and contrast, a warm silver cast
  float l = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
  c = mix( c, vec3( l ), 0.2 * uWarp );
  c = mix( c, c * vec3( 1.05, 0.98, 0.88 ) + vec3( 0.010, 0.009, 0.007 ), uWarp );
  c *= 1.0 - 0.08 * uWarp;
  // the inside of the glass: darker toward the rim, the mirrored band silvered, a thin bright ring of mercury
  float vig = smoothstep( 1.12, 0.5, r );
  float rim = smoothstep( 0.9, 0.965, r ) * smoothstep( 1.04, 0.965, r );
  c = c * mix( 1.0, vig, uWarp );
  c = mix( c, c * vec3( 0.95, 0.92, 0.86 ) * 1.25, band * 0.6 );
  c += vec3( 1.0, 0.88, 0.7 ) * rim * 0.05 * uWarp;
  // the window of the ball's own highlight, seen from inside: a soft curved streak high on the left
  vec2 hp = p - vec2( -0.42 * uAspect, 0.33 );
  float hd = length( hp * vec2( 1.0, 1.7 ) ) - 0.16;
  float hl = exp( -hd * hd * 900.0 ) * smoothstep( 0.15, -0.1, hp.x + hp.y * 0.4 );
  c += vec3( 1.0, 0.95, 0.88 ) * hl * 0.035 * uWarp;
  // the snow globe's drift: silver glitter in four layers, the near ones large, soft and faint, the far ones fine
  // and sharp; each fleck turns as it sinks, so it flashes now and then
  vec3 fl = vec3( 0.0 );
  for ( int i = 0; i < 4; i++ ) {
    float fi = float( i );
    float sc = 5.0 + fi * 6.5;
    vec2 g = vec2( uv.x * uAspect, uv.y ) * sc;
    g += vec2( sin( uTime * 0.17 + fi * 1.7 ) * ( 0.8 - fi * 0.12 ), uTime * ( 0.16 + 0.07 * fi ) );
    g.x += sin( g.y * 0.6 + uTime * 0.27 + fi * 2.1 ) * 0.4;
    vec2 cell = floor( g );
    vec2 f = fract( g ) - 0.5;
    float h = hash12( cell + fi * 17.0 );
    if ( h > 0.7 - fi * 0.05 ) {
      vec2 o = vec2( hash12( cell * 1.3 + 3.1 ), hash12( cell * 2.1 + 7.7 ) ) - 0.5;
      float near = 1.0 - fi / 3.0;
      float sz = mix( 0.03, 0.075, hash12( cell + 9.2 ) ) * mix( 0.6, 1.5, near );
      float soft = mix( 0.15, 0.85, near );
      float dd = length( f - o * 0.7 );
      float disc = 1.0 - smoothstep( sz * ( 1.0 - soft ), sz, dd );
      float turn = sin( uTime * ( 0.9 + h * 2.6 ) + h * 40.0 );
      float flash = 0.35 + 0.65 * pow( max( turn, 0.0 ), 6.0 );
      fl += mix( vec3( 0.86, 0.9, 1.0 ), vec3( 1.0, 0.86, 0.62 ), hash12( cell + 5.5 ) ) * disc * flash * mix( 0.9, 0.3, near );
    }
  }
  c += fl * 0.32 * uFlakes * uWarp;
  return c;
}

void main() {
  vec2 p = ( vUv - 0.5 ) * vec2( uAspect, 1.0 );
  float r = length( p ) / length( vec2( uAspect, 1.0 ) * 0.5 );
  // through the glass: the inside opens from the middle of the reflection outward, an iris of mercury whose edge
  // bends the picture like the lip of a lens as it sweeps past
  float front = uMix * 1.45;
  float busy = step( 0.001, uMix ) * step( uMix, 0.999 );
  float ed = ( r - front + 0.05 ) * 9.0;
  float lip = exp( -ed * ed ) * busy;
  vec2 dir = normalize( p + 1e-5 ) / vec2( uAspect, 1.0 );
  vec2 uvL = vUv - dir * lip * 0.035 * sign( ed );
  vec3 live = warped( uvL );
  vec2 pz = ( uvL - 0.5 ) / uPrevZoom + 0.5;
  vec3 held = texture2D( tPrev, pz ).rgb;
  float open = 1.0 - smoothstep( front - 0.12, front, r );
  open = uMix >= 0.999 ? 1.0 : open * step( 0.001, uMix );
  vec3 c = mix( held, live, open );
  // the silvered edge itself: a thin bright line, warm on the outside, cool on the inside
  float e1 = ( r - front + 0.06 ) * 60.0, e2 = ( r - front + 0.075 ) * 60.0;
  c += ( vec3( 1.0, 0.86, 0.62 ) * exp( -e1 * e1 ) + vec3( 0.7, 0.8, 1.0 ) * exp( -e2 * e2 ) * 0.6 ) * 0.09 * busy;
  // the glass passing in front of the eye on the way out: a silvered veil closing in from the rim
  float veil = uVeil * smoothstep( 1.2 * ( 1.0 - uVeil ) - 0.2, 1.2 * ( 1.0 - uVeil ) + 0.1, r + 0.25 * uVeil );
  float lum = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
  c = mix( c, vec3( 0.55, 0.5, 0.42 ) * ( 0.5 + lum ), clamp( veil, 0.0, 1.0 ) * 0.9 );
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
