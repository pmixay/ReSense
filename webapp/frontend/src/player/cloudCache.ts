// Point clouds of the player: an LRU cache (~60 decoded clouds), deduplicated requests, a small
// priority queue with a concurrency limit (the cloud under the playhead first, then the prefetch
// ahead), cancellation of stale prefetches after a seek, and a failure memory so a missing cloud
// is not requested at 60 fps. Generic over the value and the fetcher, so it is testable without HTTP.

export class LruCache<K, V> {
  private readonly map = new Map<K, V>();

  constructor(readonly capacity: number) {}

  get size(): number {
    return this.map.size;
  }

  has(k: K): boolean {
    return this.map.has(k);
  }

  /** Read and mark as recently used. */
  get(k: K): V | undefined {
    const v = this.map.get(k);
    if (v !== undefined) {
      this.map.delete(k);
      this.map.set(k, v);
    }
    return v;
  }

  /** Read without touching the order. */
  peek(k: K): V | undefined {
    return this.map.get(k);
  }

  set(k: K, v: V): void {
    if (this.map.has(k)) this.map.delete(k);
    this.map.set(k, v);
    while (this.map.size > this.capacity) {
      const oldest = this.map.keys().next().value as K;
      this.map.delete(oldest);
    }
  }

  delete(k: K): void {
    this.map.delete(k);
  }

  keys(): IterableIterator<K> {
    return this.map.keys();
  }

  clear(): void {
    this.map.clear();
  }
}

export type Fetcher<T> = (pos: number, signal: AbortSignal) => Promise<T>;

export type CloudStatus = 'loaded' | 'loading' | 'queued' | 'failed' | 'idle';

interface Queued {
  pos: number;
  prio: number;
  seq: number;
}

export interface CloudCacheOptions {
  capacity?: number;
  concurrency?: number;
  /** a failed position is retried after this many ms */
  retryMs?: number;
  /** called after a cloud arrived (or failed) */
  onChange?: (pos: number) => void;
  now?: () => number;
}

/** Priorities: lower runs first. */
export const PRIO_NOW = 0;
export const PRIO_AHEAD = 10;

export class CloudCache<T> {
  readonly cache: LruCache<number, T>;
  private readonly inflight = new Map<number, AbortController>();
  private queue: Queued[] = [];
  private readonly failed = new Map<number, { at: number; message: string }>();
  private seq = 0;
  private disposed = false;
  private readonly concurrency: number;
  private readonly retryMs: number;
  private readonly now: () => number;

  constructor(
    private readonly fetcher: Fetcher<T>,
    private readonly opts: CloudCacheOptions = {},
  ) {
    this.cache = new LruCache<number, T>(opts.capacity ?? 60);
    this.concurrency = Math.max(1, opts.concurrency ?? 4);
    this.retryMs = opts.retryMs ?? 5000;
    this.now = opts.now ?? (() => Date.now());
  }

  get(pos: number): T | undefined {
    return this.cache.get(pos);
  }

  status(pos: number): CloudStatus {
    if (this.cache.has(pos)) return 'loaded';
    if (this.inflight.has(pos)) return 'loading';
    if (this.queue.some((q) => q.pos === pos)) return 'queued';
    if (this.failedRecently(pos)) return 'failed';
    return 'idle';
  }

  /** The error message of a recent failure of this position (null otherwise). */
  error(pos: number): string | null {
    return this.failedRecently(pos) ? (this.failed.get(pos)?.message ?? null) : null;
  }

  private failedRecently(pos: number): boolean {
    const f = this.failed.get(pos);
    return !!f && this.now() - f.at < this.retryMs;
  }

  /** Ask for a cloud; a lower `prio` runs earlier. No-op when cached, loading or recently failed. */
  request(pos: number, prio = PRIO_NOW): void {
    if (this.disposed || this.cache.has(pos) || this.inflight.has(pos) || this.failedRecently(pos)) return;
    const q = this.queue.find((e) => e.pos === pos);
    if (q) q.prio = Math.min(q.prio, prio);
    else this.queue.push({ pos, prio, seq: this.seq++ });
    this.pump();
  }

  /** Queue clouds ahead in the given order (after anything more urgent). */
  prefetch(positions: readonly number[], prio = PRIO_AHEAD): void {
    positions.forEach((p, i) => this.request(p, prio + i * 0.001));
  }

  /** Drop queued (not yet started) requests that `keep` rejects, e.g. after a seek. */
  cancelQueued(keep: (pos: number) => boolean = () => false): void {
    this.queue = this.queue.filter((q) => keep(q.pos));
  }

  /** Abort in-flight requests that `keep` rejects. */
  abortInflight(keep: (pos: number) => boolean = () => false): void {
    for (const [pos, ac] of this.inflight) {
      if (!keep(pos)) {
        ac.abort();
        this.inflight.delete(pos);
      }
    }
    this.pump();
  }

  /** The cached cloud with the largest position at or before `pos` (null when none). */
  latestAtOrBefore(pos: number): number | null {
    let best: number | null = null;
    for (const k of this.cache.keys()) if (k <= pos && (best === null || k > best)) best = k;
    return best;
  }

  get pending(): number {
    return this.inflight.size + this.queue.length;
  }

  dispose(): void {
    this.disposed = true;
    this.queue = [];
    for (const ac of this.inflight.values()) ac.abort();
    this.inflight.clear();
    this.cache.clear();
  }

  private pump(): void {
    while (!this.disposed && this.inflight.size < this.concurrency && this.queue.length) {
      let bi = 0;
      for (let i = 1; i < this.queue.length; i += 1) {
        const a = this.queue[i];
        const b = this.queue[bi];
        if (a.prio < b.prio || (a.prio === b.prio && a.seq < b.seq)) bi = i;
      }
      const [next] = this.queue.splice(bi, 1);
      this.start(next.pos);
    }
  }

  private start(pos: number): void {
    const ac = new AbortController();
    this.inflight.set(pos, ac);
    this.fetcher(pos, ac.signal).then(
      (value) => {
        if (this.inflight.get(pos) !== ac) return; // aborted or disposed meanwhile
        this.inflight.delete(pos);
        this.failed.delete(pos);
        this.cache.set(pos, value);
        this.opts.onChange?.(pos);
        this.pump();
      },
      (err: unknown) => {
        if (this.inflight.get(pos) !== ac) return;
        this.inflight.delete(pos);
        if (!ac.signal.aborted) {
          this.failed.set(pos, { at: this.now(), message: err instanceof Error ? err.message : String(err) });
          this.opts.onChange?.(pos);
        }
        this.pump();
      },
    );
  }
}
