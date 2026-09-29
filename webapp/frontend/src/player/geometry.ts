// Track geometry of the 3D scene as flat typed arrays (no three.js here, so it is unit-testable and
// the render loop only copies into preallocated GPU buffers): the clearance envelope swept along
// the track model of the current frame, its portal frames, the floor ribbon, the rails and the
// distance ticks; plus the camera poses (cab / top / chase / the «крупно» close-up).
//
// Everything is in the vehicle frame of the frame (X forward, Y left, Z up, metres). The envelope
// is attached to the train; its colour (green up to the obstacle, red at it, a dim outline beyond
// the monitored range) is decided in the shader from uniforms, so the obstacle can glide at 60 fps
// without rebuilding the buffers.
import {
  ENVELOPE_PROFILE,
  RAILS_SPACING,
  centerY,
  floorZ,
  railZ,
  type TrackModelDict,
  type Vec2,
  type Vec3,
} from '../lib/track';

/** Line kinds (the `aKind` attribute of the track shader). */
export const KIND_EDGE = 0; // longitudinal envelope edge: coloured by x, dashed beyond
export const KIND_PORTAL = 1; // portal frame: shown only before the obstacle and the monitored end
export const KIND_PLAIN = 2; // own colour (rails, ticks, the obstacle portal)
export const KIND_FLOOR = 3; // floor ribbon / walls (mesh): shown up to the obstacle

export const ENV_X0 = 2;
export const ENV_X1 = 200;
export const ENV_STEP = 1;
export const PORTAL_FIRST = 15;
export const PORTAL_STEP = 10;
export const TICK_STEP = 10;
export const TICK_MAX = 150;
/** Distances with a label on the track bed (m). */
export const TICK_LABELS: readonly number[] = [10, 20, 30, 50, 100, 150];
/** WebGL lines are 1 px: offset copies (in metres, so near frames read thicker) make a 2–3 px frame. */
const PORTAL_TK = 0.022;
export const PORTAL_OFFSETS: readonly Vec2[] = [
  [0, 0],
  [PORTAL_TK, 0],
  [-PORTAL_TK, 0],
  [0, PORTAL_TK],
  [0, -PORTAL_TK],
];

const clamp01 = (v: number): number => Math.min(1, Math.max(0, v));

export interface VertexBuffers {
  pos: Float32Array; // xyz
  col: Float32Array; // rgba
  kind: Float32Array;
  /** vertices written */
  count: number;
  capacity: number;
}

export function allocVertices(capacity: number): VertexBuffers {
  return { pos: new Float32Array(capacity * 3), col: new Float32Array(capacity * 4), kind: new Float32Array(capacity), count: 0, capacity };
}

function put(b: VertexBuffers, x: number, y: number, z: number, r: number, g: number, bl: number, a: number, kind: number): void {
  const i = b.count;
  if (i >= b.capacity) return;
  b.pos[i * 3] = x;
  b.pos[i * 3 + 1] = y;
  b.pos[i * 3 + 2] = z;
  b.col[i * 4] = r;
  b.col[i * 4 + 1] = g;
  b.col[i * 4 + 2] = bl;
  b.col[i * 4 + 3] = a;
  b.kind[i] = kind;
  b.count = i + 1;
}

const nSeg = Math.round((ENV_X1 - ENV_X0) / ENV_STEP);
const portalXs = (): number[] => {
  const out: number[] = [];
  for (let x = PORTAL_FIRST; x <= ENV_X1; x += PORTAL_STEP) out.push(x);
  return out;
};
const RAIL_X0 = 2;
const RAIL_X1 = 196;
const RAIL_STEP = 2;
const nRail = Math.round((RAIL_X1 - RAIL_X0) / RAIL_STEP);
/** The track axis: 2 m dashes every 4 m between the rails. */
const AXIS_X0 = 4;
const AXIS_STEP = 4;
const nAxis = Math.floor((RAIL_X1 - AXIS_X0) / AXIS_STEP);

/** Vertices needed by fillTrackLines for a profile. */
export function trackLineCapacity(profile: readonly Vec2[] = ENVELOPE_PROFILE): number {
  const p = profile.length;
  const edges = nSeg * p * 2;
  const portals = portalXs().length * p * PORTAL_OFFSETS.length * 2;
  const rails = 2 * nRail * 2;
  const axis = nAxis * 2;
  const ticks = Math.floor(TICK_MAX / TICK_STEP) * 2;
  return edges + portals + rails + axis + ticks;
}

/** Envelope edges, portals every 10 m, rails (2 m segments), the track axis (dashed) and the
 *  distance ticks of a track model. */
export function fillTrackLines(b: VertexBuffers, t: TrackModelDict, profile: readonly Vec2[] = ENVELOPE_PROFILE): void {
  b.count = 0;
  const hMin = Math.min(...profile.map((q) => q[1]));
  // longitudinal edges: one per profile vertex; bottom edges solid, the others lighter; faded near the train
  for (let s = 0; s < nSeg; s += 1) {
    const x1 = ENV_X0 + s * ENV_STEP;
    const x2 = x1 + ENV_STEP;
    const c1 = centerY(t, x1);
    const c2 = centerY(t, x2);
    const r1 = railZ(t, x1);
    const r2 = railZ(t, x2);
    const nearA = clamp01((x1 - 3) / 10) * 0.7 + 0.3;
    for (const [dy, h] of profile) {
      const a = (h <= hMin + 0.01 ? 0.95 : 0.5) * nearA;
      put(b, x1, c1 + dy, r1 + h, 1, 1, 1, a, KIND_EDGE);
      put(b, x2, c2 + dy, r2 + h, 1, 1, 1, a, KIND_EDGE);
    }
  }
  // portal frames: the profile polygon at x, drawn with offset copies
  for (const x of portalXs()) {
    const c = centerY(t, x);
    const r = railZ(t, x);
    for (const [ody, odz] of PORTAL_OFFSETS) {
      for (let k = 0; k < profile.length; k += 1) {
        const q = profile[k];
        const w = profile[(k + 1) % profile.length];
        put(b, x, c + q[0] + ody, r + q[1] + odz, 1, 1, 1, 0.55, KIND_PORTAL);
        put(b, x, c + w[0] + ody, r + w[1] + odz, 1, 1, 1, 0.55, KIND_PORTAL);
      }
    }
  }
  // the rail pair: dashed, bright near, fading far
  const half = RAILS_SPACING / 2;
  for (const side of [-1, 1]) {
    for (let i = 0; i < nRail; i += 1) {
      const x = RAIL_X0 + i * RAIL_STEP;
      const x2 = x + RAIL_STEP;
      const a = 0.8 * Math.exp(-((x / 170) ** 2)) * clamp01((x - 2) / 6);
      put(b, x, centerY(t, x) + side * half, railZ(t, x), 0.87, 0.91, 1, a, KIND_PLAIN);
      put(b, x2, centerY(t, x2) + side * half, railZ(t, x2), 0.87, 0.91, 1, a, KIND_PLAIN);
    }
  }
  // the track axis: a faint dashed centre line at rail-head height
  for (let i = 0; i < nAxis; i += 1) {
    const x = AXIS_X0 + i * AXIS_STEP;
    const x2 = x + AXIS_STEP / 2;
    const a = 0.3 * Math.exp(-((x / 170) ** 2)) * clamp01((x - 3) / 8);
    put(b, x, centerY(t, x), railZ(t, x), 0.87, 0.91, 1, a, KIND_PLAIN);
    put(b, x2, centerY(t, x2), railZ(t, x2), 0.87, 0.91, 1, a, KIND_PLAIN);
  }
  // distance ticks across the bed
  for (let x = TICK_STEP; x <= TICK_MAX; x += TICK_STEP) {
    const z = railZ(t, x) + 0.02;
    const c = centerY(t, x);
    const a = (x % 50 === 0 ? 0.6 : 0.28) * Math.exp(-((x / 150) ** 2));
    put(b, x, c - 1.3, z, 1, 1, 1, a, KIND_PLAIN);
    put(b, x, c + 1.3, z, 1, 1, 1, a, KIND_PLAIN);
  }
}

/** Profile edges that get a translucent surface: the bed (bottom) and the sides; not the roof. */
function meshEdges(profile: readonly Vec2[]): { i: number; alpha: number }[] {
  const hs = profile.map((q) => q[1]);
  const hMin = Math.min(...hs);
  const hMax = Math.max(...hs);
  const out: { i: number; alpha: number }[] = [];
  for (let i = 0; i < profile.length; i += 1) {
    const a = profile[i][1];
    const b = profile[(i + 1) % profile.length][1];
    if (a <= hMin + 0.01 && b <= hMin + 0.01) out.push({ i, alpha: 0.22 });
    else if (a >= hMax - 0.01 && b >= hMax - 0.01) continue;
    else out.push({ i, alpha: 0.035 });
  }
  return out;
}

export function trackMeshCapacity(profile: readonly Vec2[] = ENVELOPE_PROFILE): number {
  return nSeg * meshEdges(profile).length * 4;
}

/** Triangle indices of the mesh (fixed for a profile: two triangles per quad). */
export function trackMeshIndex(profile: readonly Vec2[] = ENVELOPE_PROFILE): Uint16Array {
  const quads = nSeg * meshEdges(profile).length;
  const idx = new Uint16Array(quads * 6);
  for (let q = 0; q < quads; q += 1) {
    const v = q * 4;
    idx.set([v, v + 1, v + 2, v, v + 2, v + 3], q * 6);
  }
  return idx;
}

/** Floor ribbon and walls of the envelope (quads every metre). */
export function fillTrackMesh(b: VertexBuffers, t: TrackModelDict, profile: readonly Vec2[] = ENVELOPE_PROFILE): void {
  b.count = 0;
  const edges = meshEdges(profile);
  for (let s = 0; s < nSeg; s += 1) {
    const x1 = ENV_X0 + s * ENV_STEP;
    const x2 = x1 + ENV_STEP;
    const c1 = centerY(t, x1);
    const c2 = centerY(t, x2);
    const r1 = railZ(t, x1);
    const r2 = railZ(t, x2);
    for (const { i, alpha } of edges) {
      const p = profile[i];
      const q = profile[(i + 1) % profile.length];
      put(b, x1, c1 + p[0], r1 + p[1], 1, 1, 1, alpha, KIND_FLOOR);
      put(b, x2, c2 + p[0], r2 + p[1], 1, 1, 1, alpha, KIND_FLOOR);
      put(b, x2, c2 + q[0], r2 + q[1], 1, 1, 1, alpha, KIND_FLOOR);
      put(b, x1, c1 + q[0], r1 + q[1], 1, 1, 1, alpha, KIND_FLOOR);
    }
  }
}

export function portalCapacity(profile: readonly Vec2[] = ENVELOPE_PROFILE): number {
  return profile.length * PORTAL_OFFSETS.length * 2;
}

/** One full-strength portal frame at x in a given colour (the obstacle's). */
export function fillPortal(b: VertexBuffers, t: TrackModelDict, x: number, rgb: Vec3, profile: readonly Vec2[] = ENVELOPE_PROFILE): void {
  b.count = 0;
  const c = centerY(t, x);
  const r = railZ(t, x);
  for (const [ody, odz] of PORTAL_OFFSETS) {
    for (let k = 0; k < profile.length; k += 1) {
      const q = profile[k];
      const w = profile[(k + 1) % profile.length];
      put(b, x, c + q[0] + ody, r + q[1] + odz, rgb[0], rgb[1], rgb[2], 1, KIND_PLAIN);
      put(b, x, c + w[0] + ody, r + w[1] + odz, rgb[0], rgb[1], rgb[2], 1, KIND_PLAIN);
    }
  }
}

/**
 * Where the envelope turns: `near` = the obstacle's near face, `far` = past its far face (the red
 * part ends), `end` = the monitored end min(clear_distance, axis_valid, 200). Without an obstacle
 * near = far = a large number.
 */
export interface EnvelopeSpan {
  near: number;
  far: number;
  end: number;
}

export const NO_OBSTACLE = 1e5;

export function envelopeSpan(
  obstacle: { center: readonly number[]; size: readonly number[] } | null | undefined,
  clearDistance: number | null | undefined,
  axisValid: number | null | undefined,
): EnvelopeSpan {
  const end = Math.min(
    Number.isFinite(clearDistance ?? NaN) ? (clearDistance as number) : ENV_X1,
    Number.isFinite(axisValid ?? NaN) && (axisValid as number) > 0 ? (axisValid as number) : ENV_X1,
    ENV_X1,
  );
  if (!obstacle) return { near: NO_OBSTACLE, far: NO_OBSTACLE, end: Math.max(0, end) };
  const near = obstacle.center[0] - obstacle.size[0] / 2 - 0.15;
  const far = obstacle.center[0] + obstacle.size[0] / 2 + 1.2;
  // the obstacle always ends the verified part, even if clear_distance says otherwise
  return { near, far, end: Math.max(0, Math.min(Math.max(end, far), ENV_X1)) };
}

/** Is a portal at x drawn (before the obstacle by 4 m and within the monitored range)? */
export function portalVisible(x: number, span: EnvelopeSpan): boolean {
  return x < span.near - 4 && x <= span.end;
}

// ---------------------------------------------------------------- cameras

export type CamMode = 'cab' | 'top' | 'chase';

export interface CamPose {
  pos: Vec3;
  target: Vec3;
  fov: number;
  /** exp² fog density (1/m) */
  fog: number;
  /** points nearer than this are dimmed (m) */
  nearDim: number;
  /** points higher than this above the bed are hidden (m; the vault in the top view) */
  ceil: number;
  /** brightness of the tunnel walls (the cab dims them so the track and the envelope lead) */
  wallDim: number;
  near: number;
  far: number;
}

const TOP_FOV = 30;

/** Camera poses of the three presets for a track model; `focusX` = the obstacle's distance (top). */
export function cameraPose(mode: CamMode, t: TrackModelDict, aspect: number, focusX: number | null = null): CamPose {
  if (mode === 'top') {
    // straight down, forward = screen right; framed from behind the train to past the obstacle,
    // the track a little below the middle (the HUD chips and the inset sit at the top)
    const x0 = -12;
    const xmax = Math.min(190, Math.max(50, (focusX ?? 38) + 22));
    const xc = (x0 + xmax) / 2;
    const half = ((xmax - x0) / 2) * 1.04;
    const tanV = Math.tan((TOP_FOV * Math.PI) / 360);
    const h = half / (tanV * Math.max(0.5, aspect));
    const c = centerY(t, xc) + 0.07 * h;
    const r = railZ(t, xc);
    return { pos: [xc, c - 0.02 * h, r + h], target: [xc, c, r], fov: TOP_FOV, fog: 0.0012, nearDim: 1.5, ceil: 3.3, wallDim: 0.9, near: 1, far: 900 };
  }
  if (mode === 'chase') {
    // behind and above the train, looking over its roof down the track (the vault hidden)
    return {
      pos: [-9, centerY(t, 0), railZ(t, 0) + 6.4],
      target: [40, centerY(t, 40), railZ(t, 40) + 0.5],
      fov: 40,
      fog: 0.005,
      nearDim: 8,
      ceil: 3.6,
      wallDim: 0.8,
      near: 0.5,
      far: 600,
    };
  }
  return {
    pos: [-1.2, centerY(t, 0), railZ(t, 0) + 1.78],
    target: [60, centerY(t, 60), railZ(t, 60) + 0.44],
    fov: 24,
    fog: 0.0072,
    nearDim: 12,
    ceil: 99,
    wallDim: 0.5,
    near: 0.5,
    far: 600,
  };
}

/** The «крупно» close-up of an object: from in front and to the right, framing its height. */
export function closeUpPose(
  center: readonly number[],
  size: readonly number[],
  t: TrackModelDict,
): { pos: Vec3; target: Vec3; fov: number; crop: [number, number, number, number] } {
  const [ox, oy] = center;
  const fz = floorZ(t, ox);
  const h = Math.max(0.5, size[2]);
  const dist = Math.min(12, Math.max(5.2, 3.5 * Math.max(size[0], size[1], size[2])));
  return {
    pos: [ox - dist, oy - dist / 2, fz + Math.max(1.4, 1.4 * h)],
    target: [ox, oy, fz + (h <= 2 ? 1.15 : 0.55 * h)],
    fov: 27,
    // points kept around the object: x from, x to, lateral centre, lateral half-width
    crop: [ox - size[0] / 2 - 2.5, ox + size[0] / 2 + 5, oy, Math.max(1.8, size[1] + 1)],
  };
}
