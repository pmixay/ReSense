// The playback clock of the player: a playhead over the processed positions of a run that advances
// at 10 Hz × speed. It keeps the fraction of the way to the next frame (the "live drive" glides the
// scene by that fraction between two 10 Hz frames), loops or stops at the end, and can hold before
// a frame whose data has not arrived yet (buffering). Pure: no timers, the owner calls tick(dt).

/** Frames per second at 1×: the detector's input rate. */
export const BASE_HZ = 10;
/** Speed presets of the scrubber (×). */
export const SPEEDS: readonly number[] = [0.25, 0.5, 1, 2, 5, 10];
export const MIN_SPEED = SPEEDS[0];
export const MAX_SPEED = SPEEDS[SPEEDS.length - 1];
/** Longest wall-clock step taken in one tick (s): a background tab must not jump the playhead. */
export const MAX_TICK_S = 0.25;

export const clampSpeed = (s: number): number => (Number.isFinite(s) ? Math.min(MAX_SPEED, Math.max(MIN_SPEED, s)) : 1);

/** The nearest preset (URL / keyboard input snaps to the pills). */
export function snapSpeed(s: number): number {
  const v = clampSpeed(s);
  let best = SPEEDS[0];
  for (const p of SPEEDS) if (Math.abs(Math.log(p / v)) < Math.abs(Math.log(best / v))) best = p;
  return best;
}

/** Next / previous preset (the +/- keys). */
export function stepSpeed(s: number, dir: 1 | -1): number {
  const i = SPEEDS.indexOf(snapSpeed(s));
  return SPEEDS[Math.min(SPEEDS.length - 1, Math.max(0, i + dir))];
}

export interface TickResult {
  /** positions advanced in this tick (0 while paused, holding or at the end) */
  steps: number;
  /** playback stopped at the last frame (no loop) */
  ended: boolean;
  /** waiting for the data of the next frame */
  holding: boolean;
}

export class PlaybackClock {
  n: number;
  pos = 0;
  /** 0..1: the way from `pos` to the next frame */
  frac = 0;
  playing = false;
  speed = 1;
  loop = false;

  constructor(n = 0) {
    this.n = Math.max(0, Math.floor(n));
  }

  get last(): number {
    return Math.max(0, this.n - 1);
  }

  setLength(n: number): void {
    this.n = Math.max(0, Math.floor(n));
    if (this.pos > this.last) this.pos = this.last;
    if (this.n <= 1) {
      this.playing = false;
      this.frac = 0;
    }
  }

  /** Jump to a position (clamped); the glide restarts from the frame itself. */
  seek(pos: number): number {
    const p = Number.isFinite(pos) ? Math.round(pos) : 0;
    this.pos = Math.min(this.last, Math.max(0, p));
    this.frac = 0;
    return this.pos;
  }

  step(delta: number): number {
    return this.seek(this.pos + delta);
  }

  play(): void {
    if (this.n <= 1) return;
    // at the end without a loop: start over, as media players do
    if (this.pos >= this.last && !this.loop) this.seek(0);
    this.playing = true;
  }

  pause(): void {
    this.playing = false;
    this.frac = 0;
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }

  setSpeed(s: number): number {
    this.speed = clampSpeed(s);
    return this.speed;
  }

  /**
   * Advance by a wall-clock interval in seconds. `canAdvance(next)` returning false holds the
   * playhead just before `next` (its data is still loading): the glide stops at a full frame.
   */
  tick(dt: number, canAdvance?: (next: number) => boolean): TickResult {
    const out: TickResult = { steps: 0, ended: false, holding: false };
    if (!this.playing || this.n <= 1 || !(dt > 0)) return out;
    this.frac += Math.min(dt, MAX_TICK_S) * BASE_HZ * this.speed;
    while (this.frac >= 1) {
      let next = this.pos + 1;
      if (next > this.last) {
        if (!this.loop) {
          this.frac = 0;
          this.playing = false;
          out.ended = true;
          return out;
        }
        next = 0;
      }
      if (canAdvance && !canAdvance(next)) {
        this.frac = 0.999;
        out.holding = true;
        return out;
      }
      this.frac -= 1;
      this.pos = next;
      out.steps += 1;
      // a loop restart: the glide of the last frame does not carry over into the first
      if (next === 0) this.frac = Math.min(this.frac, 0.5);
    }
    return out;
  }
}
