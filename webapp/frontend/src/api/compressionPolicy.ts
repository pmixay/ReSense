// Whether the next upload chunk goes gzipped. Compression pays when the codec workers together
// compress faster than the link carries the bytes and the data shrinks: lidar bags deflate to
// ~0.65 of their size, so on a 100 Mbit/s link a 25 GB bag goes up ~1.5× faster; on a fast LAN
// the codec would be the bottleneck and chunks go raw. Every measure is a moving average, and
// a chunk is compressed now and then anyway to follow data and links that change.

const ALPHA = 0.3;
/** above this wire / raw ratio compression saves too little */
export const MAX_RATIO = 0.92;
/** compress when that is at least this much faster */
const GAIN = 1.1;
/** with compression off, try one chunk again after this many */
export const PROBE_EVERY = 24;

const ema = (prev: number | null, x: number): number => (prev === null ? x : prev + ALPHA * (x - prev));

export interface PolicyStats {
  /** wire / raw of compressed chunks */
  ratio: number | null;
  /** raw bytes / s one worker compresses */
  codecRate: number | null;
  /** wire bytes / s the link carries */
  linkRate: number | null;
}

export class CompressionPolicy {
  private ratio: number | null = null;
  private codecRate: number | null = null;
  private linkRate: number | null = null;
  private skipped = 0;

  constructor(
    private readonly enabled: boolean,
    private readonly workers: number,
  ) {}

  get stats(): PolicyStats {
    return { ratio: this.ratio, codecRate: this.codecRate, linkRate: this.linkRate };
  }

  /** Compression is faster than sending raw (with what is known so far). */
  wins(): boolean {
    if (this.ratio === null || this.codecRate === null) return true; // not measured yet: try
    if (this.ratio > MAX_RATIO) return false;
    if (this.linkRate === null) return true;
    const withGzip = Math.min(this.codecRate * Math.max(1, this.workers), this.linkRate / this.ratio);
    return withGzip > this.linkRate * GAIN;
  }

  /** Decide for the next chunk. */
  next(): boolean {
    if (!this.enabled) return false;
    if (this.wins()) {
      this.skipped = 0;
      return true;
    }
    this.skipped += 1;
    if (this.skipped >= PROBE_EVERY) {
      this.skipped = 0;
      return true;
    }
    return false;
  }

  /** A chunk prepared with compression asked for: `wire` bytes out of `raw` in `ms` (a chunk
   *  that did not shrink went raw: its wire size is its raw size). */
  compressed(raw: number, wire: number, ms: number): void {
    if (raw <= 0) return;
    this.ratio = ema(this.ratio, Math.min(1, wire / raw));
    if (ms > 0) this.codecRate = ema(this.codecRate, (raw / ms) * 1000);
  }

  /** A request carried `wire` bytes in `ms` while `concurrent` requests shared the link. */
  sent(wire: number, ms: number, concurrent: number): void {
    if (wire <= 0 || ms <= 0) return;
    this.linkRate = ema(this.linkRate, (wire / ms) * 1000 * Math.max(1, concurrent));
  }
}
