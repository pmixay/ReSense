/** Bounded physical-scene resolution; the native DOM controls/HUD stay full resolution. */
export function displayPixelRatio(width: number, height: number, requested: number, constrained = false): number {
  return Math.max(.5, Math.min(requested || 1, constrained ? 1 : 1.5, Math.sqrt(2_600_000 / Math.max(1, width * height))));
}
