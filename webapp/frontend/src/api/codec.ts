// A small pool of codec workers (codec.worker.ts) for the uploader: each chunk is read, summed and
// maybe gzipped off the main thread. Where Web Workers are not available (tests, a strict CSP) the
// same functions run inline.
import { canGzip, fingerprint, prepareChunk, type PreparedChunk } from './chunkCodec';

export type CodecRequest =
  | { id: number; op: 'chunk'; blob: Blob; start: number; end: number; gzip: boolean }
  | { id: number; op: 'fingerprint'; blob: Blob };
export type CodecResponse =
  | { id: number; ok: true; chunk?: PreparedChunk; fingerprint?: string }
  | { id: number; ok: false; error: string };

export interface Codec {
  /** parallel workers (1 when inline) */
  readonly size: number;
  readonly gzip: boolean;
  prepare(blob: Blob, start: number, end: number, gzip: boolean): Promise<PreparedChunk>;
  fingerprint(blob: Blob): Promise<string>;
  dispose(): void;
}

class InlineCodec implements Codec {
  readonly size = 1;
  readonly gzip = canGzip();
  prepare(blob: Blob, start: number, end: number, gzip: boolean): Promise<PreparedChunk> {
    return prepareChunk(blob, start, end, gzip && this.gzip);
  }
  fingerprint(blob: Blob): Promise<string> {
    return fingerprint(blob);
  }
  dispose(): void {}
}

interface Pending {
  req: CodecRequest;
  resolve: (r: CodecResponse & { ok: true }) => void;
  reject: (e: Error) => void;
  worker: number;
}

async function runInline(req: CodecRequest): Promise<CodecResponse & { ok: true }> {
  if (req.op === 'chunk') return { id: req.id, ok: true, chunk: await prepareChunk(req.blob, req.start, req.end, req.gzip) };
  return { id: req.id, ok: true, fingerprint: await fingerprint(req.blob) };
}

class WorkerCodec implements Codec {
  readonly gzip = canGzip();
  private seq = 0;
  private pending = new Map<number, Pending>();
  private load: number[];
  /** a worker failed to load or crashed: everything runs inline from then on */
  private broken = false;

  constructor(private readonly workers: Worker[]) {
    this.load = workers.map(() => 0);
    workers.forEach((w) => {
      w.onmessage = (e: MessageEvent<CodecResponse>) => this.settle(e.data);
      w.onerror = (e) => {
        e.preventDefault?.();
        this.fallBack();
      };
    });
  }

  get size(): number {
    return this.broken ? 1 : this.workers.length;
  }

  private settle(res: CodecResponse) {
    const p = this.pending.get(res.id);
    if (!p) return;
    this.pending.delete(res.id);
    this.load[p.worker] -= 1;
    if (res.ok) p.resolve(res);
    else p.reject(new Error(res.error));
  }

  private fallBack() {
    if (this.broken) return;
    this.broken = true;
    this.workers.forEach((w) => w.terminate());
    for (const [id, p] of this.pending) {
      this.pending.delete(id);
      runInline(p.req).then(p.resolve, p.reject);
    }
  }

  private send(req: CodecRequest): Promise<CodecResponse & { ok: true }> {
    if (this.broken) return runInline(req);
    let w = 0;
    for (let i = 1; i < this.load.length; i += 1) if (this.load[i] < this.load[w]) w = i;
    this.load[w] += 1;
    return new Promise((resolve, reject) => {
      this.pending.set(req.id, { req, resolve, reject, worker: w });
      this.workers[w].postMessage(req);
    });
  }

  async prepare(blob: Blob, start: number, end: number, gzip: boolean): Promise<PreparedChunk> {
    const res = await this.send({ id: (this.seq += 1), op: 'chunk', blob, start, end, gzip: gzip && this.gzip });
    return res.chunk as PreparedChunk;
  }

  async fingerprint(blob: Blob): Promise<string> {
    return (await this.send({ id: (this.seq += 1), op: 'fingerprint', blob })).fingerprint as string;
  }

  dispose(): void {
    this.workers.forEach((w) => w.terminate());
    for (const [id, p] of this.pending) {
      this.pending.delete(id);
      p.reject(new Error('Загрузка остановлена'));
    }
  }
}

/** Workers to run: one per spare core, 1..4. */
export function codecPoolSize(): number {
  const cores = typeof navigator !== 'undefined' && navigator.hardwareConcurrency ? navigator.hardwareConcurrency : 2;
  return Math.max(1, Math.min(4, cores - 1));
}

export function createCodec(size = codecPoolSize()): Codec {
  if (typeof Worker === 'undefined') return new InlineCodec();
  const workers: Worker[] = [];
  try {
    for (let i = 0; i < size; i += 1) workers.push(new Worker(new URL('./codec.worker.ts', import.meta.url), { type: 'module' }));
  } catch {
    workers.forEach((w) => w.terminate());
    return new InlineCodec();
  }
  return new WorkerCodec(workers);
}
