// Vehicle-frame track geometry from a result's `track` dict (resense/track.py TrackModel.to_dict()).
// Axes: X forward, Y left, Z up, metres, after the mount correction (the same frame as the RSC1 clouds).
//
//   centre line   y(x) = center + tan(yaw)·x + curvature·x²/2            (TrackModel.center_y)
//   bed level     z(x) = polyval(floor_coef, xc) + polyval'(floor_coef, xc)·(x − xc),
//                 xc = clamp(x, floor_range)                              (TrackModel.floor_z)
//   rail head     z(x) + rail_offset                                      (TrackModel.rail_z)
//   corridor      dy = Y − y(X), h = Z − rail_z(X)                        (gauge.corridor_coordinates)
//
// The envelope is a polygon in (dy, h) (configs/default.yaml gauge.profile) swept along the axis:
// its cross-section at X is the polygon shifted by (y(X), rail_z(X)), in the Y-Z plane.

export interface TrackModelDict {
  floor_coef: number[]; // np.polyval order (highest power first); usually [a2, a1, a0]
  floor_range: [number, number] | number[];
  center: number; // lateral offset of the axis at X = 0 (m, + left)
  yaw: number; // rad
  curvature: number; // 1/m (+ = left)
  rail_offset: number; // rail head above the bed reference (m)
  rail_score?: number;
  wall_quality?: number;
  axis_valid?: number; // X up to which the axis is supported by observed boundaries
  n_bins?: number;
  residual?: number;
  floor_verified?: number;
  rail_slabs?: number;
  axis_sides?: number;
  age?: number;
  floor_shadow?: number;
  floor_held?: boolean;
  floor_hold_run?: number;
}

export type Vec3 = [number, number, number];
export type Vec2 = [number, number];

/** gauge.profile of configs/default.yaml: (dy, h) above the rail head, 2.1 m wide × 3.0 m high from 0.12 m. */
export const ENVELOPE_PROFILE: readonly Vec2[] = [
  [-1.05, 0.12],
  [1.05, 0.12],
  [1.05, 3.0],
  [-1.05, 3.0],
];
/** gauge.warning_margin: the advisory zone widens the outer edges by this (m). */
export const WARNING_MARGIN = 0.35;
/** gauge.range_min / range_max (m). */
export const GAUGE_RANGE: Vec2 = [3.0, 250.0];
/** The farthest return seen in the organizers' recordings (m) — the scale of distance bars. */
export const SENSOR_REACH = 210;

/** Evaluates a polynomial in np.polyval order. */
export function polyval(c: readonly number[], x: number): number {
  let v = 0;
  for (let i = 0; i < c.length; i += 1) v = v * x + c[i];
  return v;
}

/** Derivative of a polynomial in np.polyval order at x. */
export function polyder(c: readonly number[], x: number): number {
  const n = c.length - 1;
  let v = 0;
  for (let i = 0; i < n; i += 1) v = v * x + c[i] * (n - i);
  return v;
}

/** Lateral position of the track axis at X (TrackModel.center_y). */
export function centerY(t: TrackModelDict, x: number): number {
  return t.center + Math.tan(t.yaw) * x + 0.5 * t.curvature * x * x;
}

/** Heading of the axis at X (rad, + = turning left): atan(dy/dx). */
export function headingAt(t: TrackModelDict, x: number): number {
  return Math.atan(Math.tan(t.yaw) + t.curvature * x);
}

/** Bed reference height at X, linearly extrapolated beyond floor_range (TrackModel.floor_z). */
export function floorZ(t: TrackModelDict, x: number): number {
  const c = t.floor_coef;
  const x0 = t.floor_range[0];
  const x1 = t.floor_range[1];
  const xc = Math.min(Math.max(x, x0), x1);
  return polyval(c, xc) + polyder(c, xc) * (x - xc);
}

/** Rail head level at X (TrackModel.rail_z). */
export function railZ(t: TrackModelDict, x: number): number {
  return floorZ(t, x) + t.rail_offset;
}

/** (dy, h): lateral offset from the axis and height above the rail head (gauge.corridor_coordinates). */
export function corridorCoordinates(t: TrackModelDict, p: Vec3 | readonly number[]): Vec2 {
  const x = p[0];
  return [p[1] - centerY(t, x), p[2] - railZ(t, x)];
}

/** Vehicle-frame point of corridor coordinates (dy, h) at X. */
export function fromCorridor(t: TrackModelDict, x: number, dy: number, h: number): Vec3 {
  return [x, centerY(t, x) + dy, railZ(t, x) + h];
}

/** Even-odd point-in-polygon, the same test as resense.gauge.point_in_polygon. */
export function pointInPolygon(px: number, py: number, poly: readonly Vec2[] | readonly (readonly number[])[]): boolean {
  let inside = false;
  const n = poly.length;
  for (let i = 0, j = n - 1; i < n; j = i, i += 1) {
    const xi = poly[i][0];
    const yi = poly[i][1];
    const xj = poly[j][0];
    const yj = poly[j][1];
    if (yi > py !== yj > py) {
      const xInt = xi + ((py - yi) * (xj - xi)) / (yj - yi);
      if (px < xInt) inside = !inside;
    }
  }
  return inside;
}

/** The profile with its outer (widest) edges pushed out by margin (resense.gauge.widened_profile). */
export function widenedProfile(profile: readonly Vec2[] = ENVELOPE_PROFILE, margin = WARNING_MARGIN): Vec2[] {
  const maxAbs = Math.max(...profile.map((p) => Math.abs(p[0])));
  return profile.map(([dy, h]) => (Math.abs(dy) >= 0.99 * maxAbs ? [dy + Math.sign(dy) * margin, h] : [dy, h]));
}

export function profileBounds(profile: readonly Vec2[] = ENVELOPE_PROFILE): {
  yMin: number;
  yMax: number;
  hMin: number;
  hMax: number;
} {
  const ys = profile.map((p) => p[0]);
  const hs = profile.map((p) => p[1]);
  return { yMin: Math.min(...ys), yMax: Math.max(...ys), hMin: Math.min(...hs), hMax: Math.max(...hs) };
}

/** Is a vehicle-frame point inside the (nominal, no edge margin) envelope within the gauge range? */
export function inEnvelope(t: TrackModelDict, p: Vec3 | readonly number[], profile: readonly Vec2[] = ENVELOPE_PROFILE): boolean {
  if (p[0] < GAUGE_RANGE[0] || p[0] > GAUGE_RANGE[1]) return false;
  const [dy, h] = corridorCoordinates(t, p);
  return pointInPolygon(dy, h, profile);
}

/** Cross-section of the envelope at X: the profile's vertices in the vehicle frame (a closed loop). */
export function envelopeSection(t: TrackModelDict, x: number, profile: readonly Vec2[] = ENVELOPE_PROFILE): Vec3[] {
  const yc = centerY(t, x);
  const zr = railZ(t, x);
  return profile.map(([dy, h]) => [x, yc + dy, zr + h]);
}

/** Sample positions from x0 to x1 (inclusive) with the given step. */
export function samples(x0: number, x1: number, step: number): number[] {
  const out: number[] = [];
  if (step <= 0 || x1 < x0) return out;
  const n = Math.floor((x1 - x0) / step + 1e-9);
  for (let i = 0; i <= n; i += 1) out.push(x0 + i * step);
  if (out[out.length - 1] < x1 - 1e-9) out.push(x1);
  return out;
}

/** The axis at rail-head height, as a polyline (for drawing the track / camera paths). */
export function axisPolyline(t: TrackModelDict, x0 = GAUGE_RANGE[0], x1 = 200, step = 2, h = 0): Vec3[] {
  return samples(x0, x1, step).map((x) => fromCorridor(t, x, 0, h));
}

/** track.rails_spacing: rail-head centres 1.59 m apart (1520 mm gauge + head). */
export const RAILS_SPACING = 1.59;

/** One rail (side = +1 left, −1 right) at rail-head height. */
export function railPolyline(t: TrackModelDict, side: 1 | -1, x0 = GAUGE_RANGE[0], x1 = 200, step = 2, spacing = RAILS_SPACING): Vec3[] {
  return samples(x0, x1, step).map((x) => fromCorridor(t, x, (side * spacing) / 2, 0));
}

/** Envelope edges swept along the axis: one polyline per profile vertex (the "rails" of the tube). */
export function envelopeEdges(t: TrackModelDict, x0 = GAUGE_RANGE[0], x1 = 200, step = 2, profile: readonly Vec2[] = ENVELOPE_PROFILE): Vec3[][] {
  const xs = samples(x0, x1, step);
  return profile.map(([dy, h]) => xs.map((x) => fromCorridor(t, x, dy, h)));
}

/** resense.track.default_track_model with configs/default.yaml: the fallback before the first result. */
export function defaultTrackModel(sensorHeight = 1.5): TrackModelDict {
  return {
    floor_coef: [0, 0, -sensorHeight],
    floor_range: [3, 120],
    center: -0.1,
    yaw: 0,
    curvature: 0,
    rail_offset: 0.35,
  };
}
