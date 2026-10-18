// Display optics use the live LiDAR texture. No CPU readback, clock-driven color cycling,
// source-pixel decimation or additional animation loop is involved.
export const DISPLAY_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const DISPLAY_FRAGMENT = /* glsl */ `
  uniform sampler2D uImage;
  uniform sampler2D uEmission;
  uniform vec2 uSurfaceSize;
  varying vec2 vUv;
  void main() {
    vec3 image = texture2D(uImage, vUv).rgb;
    vec3 scatter = texture2D(uEmission, vUv).rgb;
    vec2 tap = 2.0 / uSurfaceSize;
    vec3 bloom = max(texture2D(uImage, vUv + vec2(tap.x, 0.0)).rgb - 0.18, 0.0);
    bloom += max(texture2D(uImage, vUv - vec2(tap.x, 0.0)).rgb - 0.18, 0.0);
    bloom += max(texture2D(uImage, vUv + vec2(0.0, tap.y)).rgb - 0.18, 0.0);
    bloom += max(texture2D(uImage, vUv - vec2(0.0, tap.y)).rgb - 0.18, 0.0);
    // Native content remains continuously sampled; the aperture changes luminance only.
    vec2 cell = fract(vUv * uSurfaceSize / 1.85);
    float aperture = smoothstep(0.02, 0.12, cell.x) * (1.0 - smoothstep(0.88, 0.98, cell.x));
    aperture *= smoothstep(0.02, 0.12, cell.y) * (1.0 - smoothstep(0.88, 0.98, cell.y));
    float stripe = floor(cell.x * 3.0);
    vec3 phosphor = stripe < 1.0 ? vec3(1.16, 0.90, 0.90)
      : stripe < 2.0 ? vec3(0.90, 1.16, 0.90) : vec3(0.90, 0.90, 1.16);
    vec3 light = image * mix(0.88, 1.06, aperture) * mix(vec3(1.0), phosphor, 0.42);
    light = light * 1.12 + bloom * 0.12 + scatter * 0.10;
    gl_FragColor = vec4(min(light, vec3(1.0)), 1.0);
  }
`;

export const FILTER_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

export const FILTER_FRAGMENT = /* glsl */ `
  uniform sampler2D uImage;
  uniform vec2 uDirection;
  uniform float uExtract;
  varying vec2 vUv;
  void main() {
    vec3 color = texture2D(uImage, vUv).rgb * 0.227027;
    color += texture2D(uImage, vUv + uDirection * 1.384615).rgb * 0.316216;
    color += texture2D(uImage, vUv - uDirection * 1.384615).rgb * 0.316216;
    color += texture2D(uImage, vUv + uDirection * 3.230769).rgb * 0.070270;
    color += texture2D(uImage, vUv - uDirection * 3.230769).rgb * 0.070270;
    vec3 extracted = max(vec3(0.0), color - 0.008) * 4.0;
    // Compress a single luminance scale, not separate channels, to retain emitted hue.
    extracted /= 1.0 + max(extracted.r, max(extracted.g, extracted.b));
    color = mix(color, extracted, uExtract);
    gl_FragColor = vec4(color, 1.0);
  }
`;

export const GLOW_FRAGMENT = /* glsl */ `
  uniform sampler2D uEmission;
  uniform vec2 uFaceScale;
  varying vec2 vUv;
  void main() {
    vec2 uv = (vUv - 0.5) * uFaceScale + 0.5;
    vec2 outside = max(abs(uv - 0.5) - 0.5, vec2(0.0));
    float falloff = exp(-length(outside * vec2(1.0, 0.65)) * 24.0);
    float feather = smoothstep(0.0, 0.12, vUv.x) * (1.0 - smoothstep(0.88, 1.0, vUv.x));
    feather *= smoothstep(0.0, 0.18, vUv.y) * (1.0 - smoothstep(0.82, 1.0, vUv.y));
    // Edge spill samples a little inside the image rather than its black cover-glass margin.
    vec2 sampleUv = clamp(uv, 0.10, 0.90);
    sampleUv.y = mix(sampleUv.y, 0.38, 0.30);
    vec3 local = texture2D(uEmission, sampleUv).rgb;
    vec3 ambient = texture2D(uEmission, vec2(0.25, 0.3)).rgb;
    ambient += texture2D(uEmission, vec2(0.50, 0.3)).rgb;
    ambient += texture2D(uEmission, vec2(0.75, 0.3)).rgb;
    ambient += texture2D(uEmission, vec2(0.25, 0.6)).rgb;
    ambient += texture2D(uEmission, vec2(0.50, 0.6)).rgb;
    ambient += texture2D(uEmission, vec2(0.75, 0.6)).rgb;
    vec3 radiance = local * 0.72 + ambient * (0.28 / 6.0);
    float energy = max(radiance.r, max(radiance.g, radiance.b));
    vec3 hue = radiance / max(0.025, energy);
    float emitted = clamp(sqrt(energy) * 2.8, 0.0, 1.0);
    vec3 color = mix(vec3(0.10, 0.14, 0.19), hue, emitted);
    float alpha = falloff * feather * (0.035 + emitted * 0.55);
    gl_FragColor = vec4(color, alpha);
  }
`;
