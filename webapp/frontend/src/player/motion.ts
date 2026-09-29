// The "live drive" between two 10 Hz frames: how fast the train moves, so the scene can glide back
// along the track by v·Δt at 60 fps instead of jumping every frame; and which stored cloud stands
// for a position (a long run keeps every k-th cloud).
import type { DetectionDict } from '../api/types';

/** given = the job's ego_speed, estimated = the detector's odometry, tracked = the shift of objects
 *  seen in both frames (static trackside objects), null = unknown (no glide). */
export type SpeedSource = 'given' | 'estimated' | 'tracked';

export interface Motion {
  /** m/s along the track, >= 0 */
  v: number;
  source: SpeedSource | null;
}

/** The fields of a frame result the speed needs. */
export interface MotionFrame {
  ego_speed?: number | null;
  ego_speed_source?: string;
  ego_speed_estimate?: number | null;
  ego_speed_confidence?: number;
  detections?: readonly DetectionDict[];
  warnings?: readonly DetectionDict[];
}

/** Below this confidence the detector's own estimate is not used. */
export const MIN_SPEED_CONFIDENCE = 0.5;
/** Faster than any metro train: anything above is a mismatch, not motion. */
export const MAX_SPEED_MPS = 40;
/** A tracked object that moved sideways more than this is walking, not standing (m). */
const MAX_LATERAL_SHIFT = 0.25;

const NONE: Motion = { v: 0, source: null };

function median(v: number[]): number {
  const s = [...v].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : 0.5 * (s[m - 1] + s[m]);
}

/**
 * Speed of the train between a frame and the next one (dt seconds later): the given ego speed, the
 * detector's estimate when confident, else the median approach of the objects tracked in both
 * frames (same track id, standing still sideways), else unknown.
 */
export function frameMotion(cur: MotionFrame | null | undefined, next: MotionFrame | null | undefined, dt: number): Motion {
  if (!cur) return NONE;
  const given = cur.ego_speed;
  if (typeof given === 'number' && Number.isFinite(given)) {
    return { v: Math.min(MAX_SPEED_MPS, Math.max(0, given)), source: cur.ego_speed_source === 'estimated' ? 'estimated' : 'given' };
  }
  const est = cur.ego_speed_estimate;
  if (typeof est === 'number' && Number.isFinite(est) && (cur.ego_speed_confidence ?? 0) >= MIN_SPEED_CONFIDENCE) {
    return { v: Math.min(MAX_SPEED_MPS, Math.max(0, est)), source: 'estimated' };
  }
  if (!next || !(dt > 0)) return NONE;
  const objs = [...(cur.detections ?? []), ...(cur.warnings ?? [])];
  const later = [...(next.detections ?? []), ...(next.warnings ?? [])];
  if (!objs.length || !later.length) return NONE;
  const byId = new Map<number, DetectionDict>();
  for (const o of later) byId.set(o.id, o);
  const shifts: number[] = [];
  for (const o of objs) {
    const m = byId.get(o.id);
    if (!m || !o.center || !m.center) continue;
    if (Math.abs(m.center[1] - o.center[1]) > MAX_LATERAL_SHIFT) continue;
    const dx = o.center[0] - m.center[0];
    if (dx < -0.05 || dx > MAX_SPEED_MPS * dt) continue;
    shifts.push(Math.max(0, dx));
  }
  if (!shifts.length) return NONE;
  return { v: median(shifts) / dt, source: 'tracked' };
}

/** Seconds from a position to the next one (the recording's own timing), clamped to a sane range. */
export function frameDt(t: readonly number[] | null | undefined, pos: number, fallback = 0.1): number {
  if (t && pos >= 0 && pos + 1 < t.length) {
    const d = t[pos + 1] - t[pos];
    if (Number.isFinite(d) && d > 0) return Math.min(1, d);
  }
  return fallback;
}

/** The stored cloud at or before `pos` (clouds lists positions ascending); null before the first. */
export function cloudAtOrBefore(clouds: readonly number[] | null | undefined, pos: number): number | null {
  if (!clouds || clouds.length === 0) return null;
  let lo = 0;
  let hi = clouds.length - 1;
  if (clouds[0] > pos) return null;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (clouds[mid] <= pos) lo = mid;
    else hi = mid - 1;
  }
  return clouds[lo];
}

/** Index of a cloud position in the list (−1 when absent). */
export function cloudIndex(clouds: readonly number[], cpos: number): number {
  let lo = 0;
  let hi = clouds.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (clouds[mid] === cpos) return mid;
    if (clouds[mid] < cpos) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

/**
 * The clouds to prefetch ahead of a playhead: the next `count` stored clouds, every `stride`-th
 * (at 5–10× only some frames reach the screen).
 */
export function cloudsAhead(clouds: readonly number[], pos: number, count: number, stride = 1): number[] {
  const out: number[] = [];
  if (!clouds.length || count <= 0) return out;
  const cur = cloudAtOrBefore(clouds, pos);
  let i = cur === null ? 0 : cloudIndex(clouds, cur) + 1;
  const k = Math.max(1, Math.floor(stride));
  for (; i < clouds.length && out.length < count; i += k) out.push(clouds[i]);
  return out;
}

/** Prefetch stride for a playback speed: about 30 clouds per second reach the screen at most. */
export function prefetchStride(speed: number, hz = 10): number {
  return Math.max(1, Math.round((speed * hz) / 30));
}
