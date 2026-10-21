// Procedural faces of the cab's instruments, in the application's palette (night ground, cool ink,
// GO green, CAUTION amber, STOP red). Decorative only: blocks, traces and dials, never a value that
// could be read as a measurement. `uPower` is the boot progress (0 dark glass → 1 steady): the
// backlight strikes with a flicker and a bright line, then the layout draws in. Steady screens do
// not depend on time, so a settled cab needs no further frames.
export const CAB_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

/** Kinds: 0 traction MFI (arc gauge), 1 train-diagnostics MFI (cars and doors), 2 platform camera,
 * 3 indicator LEDs, 4 analog manometer. */
export const MFI_FRAGMENT = /* glsl */ `
  uniform float uPower;
  uniform float uSeed;
  uniform float uKind;
  uniform vec2 uSize;
  varying vec2 vUv;

  const vec3 NIGHT = vec3(0.043, 0.055, 0.082);
  const vec3 BAR = vec3(0.10, 0.125, 0.17);
  const vec3 INK = vec3(0.80, 0.85, 0.90);
  const vec3 GO = vec3(0.0, 0.78, 0.47);
  const vec3 CAUTION = vec3(1.0, 0.69, 0.0);
  const vec3 STOP = vec3(0.95, 0.10, 0.22);

  float hash(float n) { return fract(sin(n) * 43758.5453123); }
  float aa(float d) { return max(fwidth(d), 1e-5) * 1.2; }
  float fill(float d) { return 1.0 - smoothstep(0.0, aa(d), d); }
  float stroke(float d, float w) { return 1.0 - smoothstep(w, w + aa(d), abs(d)); }
  float sdBox(vec2 p, vec2 b) { vec2 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
  float sdRound(vec2 p, vec2 b, float r) { return sdBox(p, b - r) - r; }

  void main() {
    float aspect = uSize.x / uSize.y;
    vec2 p = (vUv - 0.5) * vec2(aspect, 1.0);
    float power = clamp(uPower, 0.0, 1.0);
    float strike = power < 0.3 ? step(0.45, hash(floor(power * 46.0) + uSeed * 17.0)) : 1.0;
    // the layout draws in left to right behind a bright line (the "power-up" sweep)
    float draw = smoothstep(0.3, 1.0, power);
    float sweepX = draw * (aspect + 0.2) - aspect * 0.5 - 0.1;
    float drawn = step(p.x, sweepX);
    vec3 color = NIGHT;
    float x0 = -aspect * 0.5;

    if (uKind < 0.5) {
      color = mix(color, BAR, fill(-(p.y - 0.38)));
      color = mix(color, STOP, fill(sdRound(p - vec2(x0 + 0.09, 0.44), vec2(0.05, 0.03), 0.01)));
      for (int i = 0; i < 3; i++) color = mix(color, INK * 0.7, fill(sdRound(p - vec2(x0 + 0.24 + float(i) * 0.14, 0.44), vec2(0.05, 0.012), 0.006)));
      vec2 c = p - vec2(-aspect * 0.18, -0.06);
      float r = length(c);
      float a = atan(c.x, c.y) / 3.1415927;            // -1…1, 0 straight up
      float arc = step(abs(a), 0.68);
      color = mix(color, INK * 0.35, stroke(r - 0.27, 0.012) * arc);
      float level = 0.18 + 0.3 * hash(uSeed);
      float filled = step(a, -0.68 + 1.36 * level) * arc;
      color = mix(color, GO, stroke(r - 0.27, 0.022) * filled);
      float ticks = stroke(fract((a + 0.68) * 7.35) - 0.5, 0.06) * step(0.3, r) * step(r, 0.34) * arc;
      color = mix(color, INK, ticks * 0.8);
      color = mix(color, INK, fill(sdRound(c - vec2(0.0, -0.02), vec2(0.1, 0.05), 0.012)));
      for (int i = 0; i < 4; i++) {
        float y = 0.22 - float(i) * 0.13;
        vec3 tone = i == 1 ? CAUTION : (i == 3 ? GO : INK * 0.75);
        color = mix(color, tone, fill(sdRound(p - vec2(aspect * 0.2, y), vec2(aspect * 0.2 * (0.55 + 0.4 * hash(float(i) + uSeed)), 0.035), 0.01)));
      }
    } else if (uKind < 1.5) {
      color = mix(color, BAR, fill(-(p.y - 0.38)));
      color = mix(color, INK * 0.7, fill(sdRound(p - vec2(x0 + 0.2, 0.44), vec2(0.13, 0.015), 0.007)));
      float carW = (aspect - 0.16) / 6.0;
      for (int i = 0; i < 6; i++) {
        vec2 cc = p - vec2(x0 + 0.08 + carW * (float(i) + 0.5), 0.12);
        float body = sdRound(cc, vec2(carW * 0.44, 0.09), 0.025);
        color = mix(color, INK * 0.85, stroke(body, 0.006));
        for (int d = 0; d < 2; d++) {
          float door = fill(sdBox(cc - vec2((float(d) - 0.5) * carW * 0.4, -0.02), vec2(0.012, 0.05)));
          color = mix(color, GO, door);
        }
      }
      for (int i = 0; i < 3; i++) {
        vec3 tone = i == 2 ? CAUTION : GO;
        color = mix(color, tone, fill(sdRound(p - vec2(x0 + 0.2 + float(i) * 0.36, -0.14), vec2(0.14, 0.045), 0.02)) * 0.85);
      }
    } else if (uKind < 2.5) {
      // platform camera: tunnel-dark scene, the yellow platform edge line, a time strip
      vec3 sky = mix(vec3(0.05, 0.06, 0.07), vec3(0.16, 0.17, 0.18), smoothstep(-0.5, 0.3, p.y));
      color = sky;
      float edge = p.y + 0.5 - (p.x / aspect + 0.5) * 0.55;
      color = mix(color, vec3(0.30, 0.31, 0.32), step(edge, 0.0));
      color = mix(color, CAUTION * 0.85, stroke(edge, 0.012));
      color = mix(color, INK * 0.9, fill(sdRound(p - vec2(x0 + 0.18, 0.42), vec2(0.12, 0.018), 0.006)));
    } else if (uKind < 3.5) {
      // indicator LEDs in a strip
      vec2 cell = vec2(aspect / 8.0, 1.0);
      float k = floor((p.x - x0) / cell.x);
      vec2 kc = vec2(x0 + (k + 0.5) * cell.x, 0.0);
      float led = fill(length(p - kc) - 0.22);
      vec3 tone = mod(k, 4.0) < 1.0 ? STOP : (mod(k, 3.0) < 1.0 ? CAUTION : GO);
      color = mix(vec3(0.02), tone, led * step(k / 8.0, draw));
      drawn = 1.0;
    } else {
      // analog manometer: white ticks, a red needle that sweeps to its rest on power-up
      vec2 c = p;
      float r = length(c);
      float a = atan(c.x, c.y) / 3.1415927;
      color = vec3(0.025, 0.028, 0.032);
      float arc = step(abs(a), 0.75);
      color = mix(color, INK, stroke(fract((a + 0.75) * 10.0) - 0.5, 0.08) * step(0.33, r) * step(r, 0.42) * arc);
      color = mix(color, STOP, stroke(r - 0.40, 0.012) * step(0.45, a) * arc);
      float rest = -0.75 + 1.5 * (0.32 + 0.25 * hash(uSeed));
      float needleA = mix(-0.75, rest, smoothstep(0.35, 0.85, power)) + 0.25 * sin(power * 12.0) * (1.0 - smoothstep(0.6, 1.0, power));
      vec2 dir = vec2(sin(needleA * 3.1415927), cos(needleA * 3.1415927));
      float along = dot(c, dir);
      float across = abs(dot(c, vec2(-dir.y, dir.x)));
      color = mix(color, STOP, fill(across - 0.012) * step(-0.05, along) * step(along, 0.37));
      color = mix(color, INK * 0.6, fill(r - 0.045));
      color *= mix(vec3(1.0), vec3(1.05, 1.0, 0.86), 0.6);
      drawn = 1.0;
    }

    // power: dark glass → flicker → layout drawn in behind a bright sweep line
    vec3 off = vec3(0.012, 0.014, 0.018) + vec3(0.03) * (1.0 - vUv.y) * 0.5;
    vec3 shown = mix(NIGHT * step(0.02, power), color, drawn);
    float line = (1.0 - smoothstep(0.0, aa(p.x - sweepX) * 3.0, abs(p.x - sweepX))) * step(0.3, power) * (1.0 - step(0.999, power));
    shown += vec3(0.75, 0.88, 1.0) * line;
    shown += vec3(0.25, 0.32, 0.4) * (1.0 - smoothstep(0.02, 0.3, power)) * step(0.02, power);
    float scan = 0.94 + 0.06 * step(0.5, fract(vUv.y * uSize.y * 300.0));
    vec3 result = mix(off, shown * scan, strike * step(0.02, power));
    // a faint reflection on the cover glass
    result += vec3(0.05) * exp(-pow((vUv.x + vUv.y * 0.4 - 0.25) / 0.08, 2.0));
    gl_FragColor = vec4(result, 1.0);
  }
`;

/** Black laminated windshield glass beyond the active display area, with the bonded edge's
 * ceramic frit band: solid black at the edge, fading to dots towards the display. */
export const GLASS_FRAGMENT = /* glsl */ `
  uniform float uPower;
  uniform vec2 uSize;
  uniform float uBand;
  varying vec2 vUv;
  void main() {
    vec3 c = mix(vec3(0.006, 0.009, 0.014), vec3(0.016, 0.022, 0.030), vUv.y);
    float streak = exp(-pow((vUv.x + vUv.y * 0.32 - 0.22) / 0.045, 2.0));
    c += vec3(0.05, 0.055, 0.06) * streak * 0.3;
    vec2 m = vUv * uSize;
    float edge = min(min(m.x, uSize.x - m.x), min(m.y, uSize.y - m.y));
    float t = clamp(edge / max(uBand, 1e-4), 0.0, 1.0);
    vec2 cell = fract(m / 0.006) - 0.5;
    float dots = 1.0 - smoothstep(0.0, 0.08, length(cell) - (0.62 - t * 0.62) * 0.5);
    float frit = t < 0.45 ? 1.0 : dots * (1.0 - smoothstep(0.45, 1.0, t)) + (1.0 - step(0.45, t));
    c = mix(c, vec3(0.012, 0.013, 0.015), clamp(frit, 0.0, 1.0));
    gl_FragColor = vec4(c, 1.0);
  }
`;
