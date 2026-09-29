// Per-frame results of a run in chunks (GET /api/runs/{id}/frames?from&count): the chunk under the
// playhead and its neighbours are fetched ahead, a few dozen chunks are kept, failures are
// remembered for a moment so the render loop does not hammer a dead backend.
import { LruCache } from './cloudCache';

export const CHUNK = 100;

export interface FramesChunk<F> {
  from: number;
  frames: F[];
  total: number;
}

export type ChunkFetcher<F> = (from: number, count: number, signal: AbortSignal) => Promise<FramesChunk<F>>;

export interface FrameStoreOptions {
  capacity?: number;
  retryMs?: number;
  onChange?: () => void;
  now?: () => number;
}

export class FrameStore<F> {
  private readonly chunks: LruCache<number, F[]>;
  private readonly inflight = new Map<number, AbortController>();
  private readonly failed = new Map<number, { at: number; error: unknown }>();
  private disposed = false;
  private readonly retryMs: number;
  private readonly now: () => number;
  /** the last error (cleared by a success) */
  lastError: unknown = null;

  constructor(
    private readonly fetcher: ChunkFetcher<F>,
    public total: number,
    private readonly opts: FrameStoreOptions = {},
  ) {
    this.chunks = new LruCache<number, F[]>(opts.capacity ?? 40);
    this.retryMs = opts.retryMs ?? 3000;
    this.now = opts.now ?? (() => Date.now());
  }

  static chunkOf(pos: number): number {
    return Math.floor(pos / CHUNK);
  }

  get(pos: number): F | undefined {
    if (pos < 0 || pos >= this.total) return undefined;
    const c = this.chunks.get(FrameStore.chunkOf(pos));
    return c?.[pos - FrameStore.chunkOf(pos) * CHUNK];
  }

  has(pos: number): boolean {
    return this.get(pos) !== undefined;
  }

  loading(pos: number): boolean {
    return this.inflight.has(FrameStore.chunkOf(pos));
  }

  /** Fetch the chunk of `pos` when missing (no-op while loading or right after a failure). */
  ensure(pos: number): void {
    if (this.disposed || pos < 0 || pos >= this.total) return;
    const c = FrameStore.chunkOf(pos);
    if (this.chunks.has(c) || this.inflight.has(c)) return;
    const f = this.failed.get(c);
    if (f && this.now() - f.at < this.retryMs) return;
    this.load(c);
  }

  /** The chunk of `pos` plus the next one when the playhead is in the second half (and the previous
   *  one near the start of a chunk). */
  ensureAround(pos: number): void {
    this.ensure(pos);
    const off = pos % CHUNK;
    if (off >= CHUNK / 2) this.ensure(pos + CHUNK - off);
    else if (off < 10 && pos >= CHUNK) this.ensure(pos - off - 1);
  }

  /** Forget failures so the next ensure() retries at once. */
  retry(): void {
    this.failed.clear();
    this.lastError = null;
  }

  dispose(): void {
    this.disposed = true;
    for (const ac of this.inflight.values()) ac.abort();
    this.inflight.clear();
    this.chunks.clear();
  }

  private load(c: number): void {
    const ac = new AbortController();
    this.inflight.set(c, ac);
    const from = c * CHUNK;
    this.fetcher(from, Math.min(CHUNK, this.total - from), ac.signal).then(
      (res) => {
        if (this.inflight.get(c) !== ac) return;
        this.inflight.delete(c);
        this.failed.delete(c);
        this.lastError = null;
        if (Number.isFinite(res.total) && res.total > 0) this.total = res.total;
        this.chunks.set(c, res.frames);
        this.opts.onChange?.();
      },
      (err: unknown) => {
        if (this.inflight.get(c) !== ac) return;
        this.inflight.delete(c);
        if (ac.signal.aborted) return;
        this.failed.set(c, { at: this.now(), error: err });
        this.lastError = err;
        this.opts.onChange?.();
      },
    );
  }
}
