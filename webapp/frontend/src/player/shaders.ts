// GLSL of the player scene (three.js ShaderMaterial, GLSL 1 syntax — three converts it for WebGL 2).
// Colours are display values: colour management is off in the scene, nothing is converted.

/** Points: coloured on the GPU from height above the bed (the track model of the cloud's frame),
 *  intensity and the RSC1 flags, so switching a cloud is a plain buffer copy. */
export const POINTS_VERT = /* glsl */ `
attribute float aInt;
attribute float aFlag;
uniform float uScale;
uniform float uMinPx;
uniform float uMaxPx;
uniform float uFogD;
uniform float uNearDim;
uniform float uCeil;
uniform float uWallDim;
uniform float uHot;
uniform vec4 uCrop;
uniform vec3 uFloorC;
uniform vec2 uFloorR;
uniform vec4 uAxis;
uniform vec3 uRamp[6];
uniform vec3 uBedLo;
uniform vec3 uBedHi;
uniform vec3 uRail;
uniform vec3 uObj;
uniform vec3 uWarn;
uniform vec3 uCor;
uniform vec3 uHotRamp[4];
varying vec3 vC;
varying float vF;

float floorZ(float x) {
  float xc = clamp(x, uFloorR.x, uFloorR.y);
  float p = (uFloorC.x * xc + uFloorC.y) * xc + uFloorC.z;
  float d = 2.0 * uFloorC.x * xc + uFloorC.y;
  return p + d * (x - xc);
}
vec3 ramp(float t) {
  t = clamp(t, 0.0, 1.0);
  if (t < 0.18) return mix(uRamp[0], uRamp[1], t / 0.18);
  if (t < 0.42) return mix(uRamp[1], uRamp[2], (t - 0.18) / 0.24);
  if (t < 0.66) return mix(uRamp[2], uRamp[3], (t - 0.42) / 0.24);
  if (t < 0.86) return mix(uRamp[3], uRamp[4], (t - 0.66) / 0.20);
  return mix(uRamp[4], uRamp[5], (t - 0.86) / 0.14);
}
vec3 hotRamp(float t) {
  t = clamp(t, 0.0, 1.0) * 3.0;
  if (t < 1.0) return mix(uHotRamp[0], uHotRamp[1], t);
  if (t < 2.0) return mix(uHotRamp[1], uHotRamp[2], t - 1.0);
  return mix(uHotRamp[2], uHotRamp[3], t - 2.0);
}
bool bit(float f, float b) { return mod(floor(f / b + 0.001), 2.0) > 0.5; }

void main() {
  vec3 p = position;
  float hf = p.z - floorZ(p.x);
  float cy = uAxis.x + uAxis.y * p.x + 0.5 * uAxis.z * p.x * p.x;
  float dy = p.y - cy;
  bool hide = hf > uCeil;
  if (uCrop.y > uCrop.x) hide = hide || p.x < uCrop.x || p.x > uCrop.y || abs(p.y - uCrop.z) > uCrop.w;
  if (hide) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    vC = vec3(0.0);
    vF = 1.0;
    return;
  }
  float ki = clamp((aInt - 6.0) / 22.0, 0.0, 1.0);
  vec3 c;
  float s;
  if (bit(aFlag, 2.0)) {
    c = uHot > 0.5 ? hotRamp((aInt - 14.0) / 40.0) : uObj;
    s = 2.3;
  } else if (bit(aFlag, 4.0)) {
    c = uWarn;
    s = 2.0;
  } else if (bit(aFlag, 1.0)) {
    c = uCor;
    s = 1.8;
  } else if (hf < 0.32 && abs(dy) < 2.3) {
    bool onRail = hf > 0.06 && abs(abs(dy) - 0.795) < 0.12;
    c = onRail ? uRail * 1.1 : mix(uBedLo, uBedHi, 0.15 + 0.75 * ki) * (0.9 + 0.35 * ki);
    s = onRail ? 1.35 : 1.1;
  } else {
    c = ramp((hf - 0.3) / 4.6 * 0.95 + ki * 0.12) * (0.72 + 0.38 * ki);
    s = 1.0;
    if (hf > 0.6) { c *= uWallDim; s = 0.8; }
  }
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float d = max(0.5, -mv.z);
  gl_PointSize = clamp(uScale * s / d, uMinPx * s, uMaxPx * s);
  vC = c * mix(0.55, 1.0, smoothstep(1.5, max(1.6, uNearDim), d));
  vF = 1.0 - exp(-uFogD * uFogD * d * d);
}
`;

export const POINTS_FRAG = /* glsl */ `
uniform vec3 uFog;
varying vec3 vC;
varying float vF;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float r = dot(c, c);
  if (r > 0.25) discard;
  float a = smoothstep(0.25, 0.10, r);
  gl_FragColor = vec4(mix(vC, uFog, vF), a);
}
`;

/** Track lines and the envelope surfaces: colour and visibility decided per fragment from x and the
 *  obstacle span (uSpan = near, far, end), see geometry.ts for the kinds. */
export const TRACK_VERT = /* glsl */ `
attribute vec4 aCol;
attribute float aKind;
uniform float uFogD;
varying vec4 vCol;
varying float vX;
varying float vKind;
varying float vF;
void main() {
  vCol = aCol;
  vX = position.x;
  vKind = aKind;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  float d = -mv.z;
  vF = 1.0 - exp(-uFogD * uFogD * d * d);
}
`;

export const TRACK_FRAG = /* glsl */ `
uniform vec3 uSpan;
uniform vec3 uGreen;
uniform vec3 uRed;
uniform vec3 uWhite;
uniform vec3 uFog;
uniform float uGain;
varying vec4 vCol;
varying float vX;
varying float vKind;
varying float vF;
void main() {
  float x = vX;
  float near = uSpan.x;
  float far = uSpan.y;
  float end = uSpan.z;
  float beyondAt = min(far, end);
  bool beyond = x > beyondAt;
  vec3 c = vCol.rgb;
  float a = vCol.a;
  bool plain = vKind > 1.5 && vKind < 2.5;
  if (!plain) {
    c = x < near - 6.0 ? uGreen : (x < near ? mix(uGreen, uRed, (x - (near - 6.0)) / 6.0) : (x <= far ? uRed : uWhite));
    if (beyond) c = uWhite;
    a *= exp(-pow(x / 150.0, 2.0));
  }
  if (vKind < 0.5) {
    if (beyond) {
      if (mod(x, 2.0) > 1.0) discard;
      a *= 0.35;
    }
  } else if (vKind < 1.5) {
    if (x >= near - 4.0 || x > end) discard;
  } else if (vKind > 2.5) {
    if (x >= beyondAt) discard;
    a *= clamp((x - 4.0) / 12.0, 0.0, 1.0);
  }
  gl_FragColor = vec4(mix(c, uFog, vF), a * uGain);
}
`;

/** Flat colour (boxes) with fog; vertex colours when USE_COLOR (the train body). */
export const FLAT_VERT = /* glsl */ `
uniform float uFogD;
varying float vF;
varying vec3 vVC;
void main() {
  #ifdef USE_COLOR
  vVC = color;
  #else
  vVC = vec3(1.0);
  #endif
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  float d = -mv.z;
  vF = 1.0 - exp(-uFogD * uFogD * d * d);
}
`;

export const FLAT_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
uniform vec3 uFog;
varying float vF;
varying vec3 vVC;
void main() {
  gl_FragColor = vec4(mix(uColor * vVC, uFog, vF), uOpacity);
}
`;

/** The «крупно» inset: the close-up render target drawn as a rounded rectangle. */
export const INSET_VERT = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const INSET_FRAG = /* glsl */ `
uniform sampler2D uTex;
uniform vec2 uSize;
uniform float uRadius;
varying vec2 vUv;
void main() {
  vec2 p = vUv * uSize;
  vec2 q = abs(p - 0.5 * uSize) - (0.5 * uSize - uRadius);
  float d = length(max(q, 0.0)) - uRadius;
  float a = clamp(0.5 - d, 0.0, 1.0);
  gl_FragColor = vec4(texture2D(uTex, vUv).rgb, a);
}
`;
