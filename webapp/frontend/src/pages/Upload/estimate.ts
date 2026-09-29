// Estimates for the «Обработка» card and the demo generator (shown as «≈»): frames after the step,
// processing time at the measured ~10 frames/s, the stored clouds for the player, demo size / time.

/** Processed frames per wall second of the worker on the reference machine (≈ real time). */
export const PROCESS_FPS = 10;
/** A run keeps at most this many clouds (webapp/API.md). */
export const MAX_CLOUDS = 3000;
/** RSC1: int16 x/y/z + uint8 intensity + uint8 flags per point, a 8-byte header per cloud. */
export const CLOUD_BYTES_PER_POINT = 8;
export const DEFAULT_CLOUD_POINTS = 30000;
/** Demo bags: ≈ 33 MB per second of recording, ≈ 0.65 s of generation per second. */
export const DEMO_BYTES_PER_S = 33 * 1024 * 1024;
export const DEMO_GEN_S_PER_S = 0.65;

/** Frames a job processes: ceil((n − start) / every), capped by limit (the backend's frames_total). */
export function framesToProcess(nFrames: number | null, every = 1, start = 0, limit: number | null = null): number | null {
  if (nFrames === null || !Number.isFinite(nFrames)) return null;
  let n = Math.max(0, Math.ceil((nFrames - start) / Math.max(1, every)));
  if (limit) n = Math.min(n, limit);
  return n;
}

/** Seconds of processing at PROCESS_FPS. */
export function processSeconds(frames: number | null): number | null {
  return frames === null ? null : frames / PROCESS_FPS;
}

/** Upper bound of the stored clouds (bytes). */
export function cloudBytes(frames: number | null, points = DEFAULT_CLOUD_POINTS): number | null {
  if (frames === null) return null;
  const n = Math.min(frames, MAX_CLOUDS);
  return n * (points * CLOUD_BYTES_PER_POINT + 8);
}

export const demoBytes = (seconds: number): number => seconds * DEMO_BYTES_PER_S;
export const demoSeconds = (seconds: number): number => seconds * DEMO_GEN_S_PER_S;
