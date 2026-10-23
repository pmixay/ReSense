// One boot timeline (milliseconds from the moment the driver is seated) shared by the cab's 3D
// instruments, the live image's scan reveal and the DOM initialization overlay. No three.js here:
// the React side imports it without the 3D chunk.

/** The whole sequence; afterwards everything is steady and nothing animates on its own. */
export const CAB_BOOT_MS = 2100;
/** Accent light strips strike first. */
export const BOOT_ACCENTS = { start: 0, length: 360 };
/** Instrument screens power up one after another. */
export const BOOT_SCREENS = { start: 140, step: 110, length: 640 };
/** The windshield display: a scan line reveals the live LiDAR picture. */
export const BOOT_IMAGE = { start: 650, length: 1000 };
/** HUD annotations fade in once the picture is there. */
export const BOOT_HUD_MS = 1550;

/** Progress 0…1 of a step that starts at `start` and lasts `length` (both ms). */
export function bootProgress(t: number, start: number, length: number): number {
  return Math.min(1, Math.max(0, (t - start) / length));
}

export type BootState = 'off' | 'running' | 'on';

/** The Player page's boot: waiting for the walk-in to lift ('pending'), playing, or over. */
export interface CabBootInfo {
  state: 'pending' | 'running' | 'done';
  /** performance.now() when it started (running) */
  start: number;
}

/** The scene's instrument power for a page boot state. */
export function bootPower(boot: CabBootInfo, now = performance.now()): 'off' | 'on' | number {
  return boot.state === 'done' ? 'on' : boot.state === 'pending' ? 'off' : now - boot.start;
}
