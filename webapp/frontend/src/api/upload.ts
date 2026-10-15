// Upload of a recording (webapp/API.md, «Recordings»), resumable and safe for big files:
//   POST /api/uploads (or GET /api/uploads/{id} to resume one) → a file up to `chunkSize` goes in
//   one PUT …/files; a bigger one is declared (POST …/chunked: the server answers the chunks it
//   still needs) and sent chunk by chunk (PUT …/chunked/{i}) → POST …/finalize?wait=false → GET
//   /api/uploads/{id} until the recording is there (unpacking a big zip shows its progress).
// `concurrency` requests run at once. Every body carries the CRC-32 of its raw bytes and goes
// gzipped when that is faster (CompressionPolicy; the codec runs in Web Workers). A request that
// fails for the network or a server hiccup is retried with backoff (offline: as soon as the network
// is back), so a 25 GB upload survives a dropped connection without starting over; the user can
// pause and resume; after a reload the same files picked again continue where the server stopped
// (`resumeId`). Folders keep their relative paths (input webkitdirectory → File.webkitRelativePath;
// drag and drop → filesFromDataTransfer).
import { API_BASE, ApiError, OFFLINE_MESSAGE, api, detailMessage, errorMessage } from './client';
import { createCodec, type Codec } from './codec';
import { crcHex, type PreparedChunk } from './chunkCodec';
import { CompressionPolicy } from './compressionPolicy';
import type { ChunkedFileState, Recording, UploadCreated, UploadStatus } from './types';

export interface UploadItem {
  file: File;
  path: string; // relative, "/"-separated
}

export type UploadPhase = 'staging' | 'uploading' | 'finalizing' | 'done';
/** running; paused (by the user, or after an error that needs attention: `notice`); waiting (the
 *  connection is gone: retried automatically, `retryInS`) */
export type UploadState = 'running' | 'paused' | 'waiting';

export interface UploadProgress {
  phase: UploadPhase;
  state: UploadState;
  loaded: number; // raw bytes on the server or on their way (resumed ones included)
  total: number;
  fraction: number; // 0..1
  fileIndex: number; // 0-based, the first file not finished yet
  fileCount: number;
  currentPath: string;
  bytesPerSec: number | null; // raw bytes / s, moving average over the last seconds
  etaS: number | null;
  /** wire / raw bytes of what was sent (null until something went compressed) */
  compression: number | null;
  /** bytes that were already on the server when this upload (re)started */
  resumed: number;
  /** seconds to the next automatic retry (state "waiting") */
  retryInS: number | null;
  /** why it is paused / waiting */
  notice: string | null;
  /** the server's stage while finalizing */
  finalize: UploadStatus['finalize'];
}

export interface UploadOptions {
  name?: string;
  onProgress?: (p: UploadProgress) => void;
  /** the server's upload id, as soon as it is known (keep it to resume after a reload) */
  onStaged?: (uploadId: string) => void;
  signal?: AbortSignal;
  /** continue this upload: the files the server already holds are not sent again */
  resumeId?: string | null;
  concurrency?: number;
  chunkSize?: number;
  /** gzip chunks when that is faster (default true) */
  compress?: boolean;
  codec?: Codec;
  /** how often the finalize stage is polled (ms) */
  pollMs?: number;
}

export interface UploadHandle {
  promise: Promise<Recording>;
  /** cancel: the transfer stops and the server's staging area is removed */
  abort(): void;
  pause(): void;
  resume(): void;
  readonly uploadId: string | null;
}

export class UploadAbortedError extends Error {
  constructor() {
    super('Загрузка отменена');
    this.name = 'UploadAbortedError';
  }
}

export const CHUNK_SIZE = 8 * 1024 * 1024;
export const CONCURRENCY = 4;
/** smaller bodies are not worth compressing */
const MIN_GZIP = 64 * 1024;
/** already compressed: never gzipped again */
const PACKED = /\.(gz|tgz|zst|zstd|xz|bz2|7z|lz4|br|rar|png|jpe?g|mp4|webm)$/i;
/** no byte moving and no answer for this long: the connection is dead, the request is retried */
const STALL_MS = 60_000;
const BACKOFF_MAX_S = 30;
/** a request failing this often (not for the network) pauses the upload with the server's message:
 *  1 + 2 + 4 + 8 + 16 + 30 + 30 s of backoff, longer than the server waits for a silent body (60 s) */
const MAX_ATTEMPTS = 8;
const FINALIZE_POLL_MS = 1000;
const REPORT_MS = 100;

/** Normalises Files / {file, path} to upload items with a safe relative path. */
export function toUploadItems(files: Iterable<File | UploadItem> | ArrayLike<File>): UploadItem[] {
  const list = Array.from(files as Iterable<File | UploadItem>);
  return list.map((f) => {
    if (f instanceof File) return { file: f, path: cleanPath(f.webkitRelativePath || f.name) };
    return { file: f.file, path: cleanPath(f.path || f.file.name) };
  });
}

export function cleanPath(p: string): string {
  return p
    .replace(/\\/g, '/')
    .split('/')
    .filter((s) => s && s !== '.' && s !== '..')
    .join('/');
}

/** The name a user would recognise: the top folder of a folder upload, else the first file's stem. */
export function suggestName(items: UploadItem[]): string {
  if (!items.length) return '';
  const first = items[0].path;
  if (first.includes('/')) return first.split('/')[0];
  return first.replace(/\.(zip|db3|mcap|jsonl|npz|npy|yaml)$/i, '');
}

/** Moving-average speed over a sliding window of (time, bytes) samples. */
export class SpeedMeter {
  private samples: [number, number][] = [];
  constructor(private readonly windowMs = 3000) {}

  push(tMs: number, bytes: number): void {
    this.samples.push([tMs, bytes]);
    while (this.samples.length > 2 && tMs - this.samples[0][0] > this.windowMs) this.samples.shift();
  }

  reset(): void {
    this.samples = [];
  }

  /** bytes / second, or null until there is half a second of data. */
  get rate(): number | null {
    if (this.samples.length < 2) return null;
    const [t0, b0] = this.samples[0];
    const [t1, b1] = this.samples[this.samples.length - 1];
    const dt = (t1 - t0) / 1000;
    return dt >= 0.5 ? Math.max(0, (b1 - b0) / dt) : null;
  }
}

/** retry: the network or a passing server state (a corrupted body, a write of a dead connection
 *  still holding the area: 409); pause: needs the user (disk full); fatal: the upload cannot go on
 *  (gone, too big, not a recording, the file unreadable). */
export function classifyError(err: unknown): 'retry' | 'pause' | 'fatal' {
  if (!(err instanceof ApiError)) return 'fatal';
  const s = err.status;
  if (s === 507) return 'pause';
  if (s === 0 || s === 400 || s === 408 || s === 409 || s === 425 || s === 429 || (s >= 500 && s !== 501)) return 'retry';
  return 'fatal';
}

/** The failure makes the server's staging area useless (it is removed); after any other failure
 *  it is kept, so the same files picked again continue the upload. */
export function dropsArea(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 404 || err.status === 413 || err.status === 422);
}

/** The browser could not read the file any more (moved, deleted or changed on disk). */
export class FileReadError extends Error {
  constructor(path: string) {
    super(`Не удалось прочитать «${path}»: файл перемещён или изменён. Выберите его снова — загрузка продолжится с того же места`);
    this.name = 'FileReadError';
  }
}

class TransferAborted extends Error {}

interface Sent {
  wire: number;
  ms: number;
}

/** PUT of a prepared body with progress (wire bytes), a stall watchdog and the backend's errors. */
function xhrPut(url: string, prepared: PreparedChunk, onBytes: (wire: number) => void, register: (x: XMLHttpRequest | null) => void): Promise<Sent> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const t0 = performance.now();
    let stall: ReturnType<typeof setTimeout> | undefined;
    let stalled = false;
    const arm = () => {
      clearTimeout(stall);
      stall = setTimeout(() => {
        stalled = true;
        xhr.abort();
      }, STALL_MS);
    };
    const done = () => {
      clearTimeout(stall);
      register(null);
    };
    register(xhr);
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('X-Content-CRC32', crcHex(prepared.crc));
    if (prepared.encoding === 'gzip') xhr.setRequestHeader('X-Content-Encoding', 'gzip');
    xhr.upload.onprogress = (e) => {
      arm();
      onBytes(e.loaded);
    };
    xhr.onload = () => {
      done();
      if (xhr.status >= 200 && xhr.status < 300) {
        onBytes(prepared.body.byteLength);
        resolve({ wire: prepared.body.byteLength, ms: performance.now() - t0 });
        return;
      }
      let detail: unknown;
      try {
        detail = (JSON.parse(xhr.responseText) as { detail?: unknown }).detail;
      } catch {
        detail = undefined;
      }
      const offline = detail === undefined && xhr.status >= 500;
      reject(new ApiError(offline ? OFFLINE_MESSAGE : detailMessage(detail, xhr.status), xhr.status, detail, offline));
    };
    xhr.onerror = () => {
      done();
      reject(new ApiError('Связь с сервером прервалась во время загрузки', 0));
    };
    xhr.onabort = () => {
      done();
      reject(stalled ? new ApiError('Связь с сервером не отвечает', 0) : new TransferAborted());
    };
    arm();
    // a Blob, not the ArrayBuffer itself: Chromium streams it with steady progress events, and with
    // DevTools' network panel open it is not copied into the inspector (8 MiB bodies froze the page)
    xhr.send(new Blob([prepared.body]));
  });
}

interface Task {
  file: number; // index into items
  chunk: number | null; // null: the whole file in one PUT
  start: number;
  end: number;
  attempts: number;
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

class Uploader {
  readonly items: UploadItem[];
  readonly total: number;
  uploadId: string | null = null;
  private readonly chunkSize: number;
  private readonly concurrency: number;
  private readonly codec: Codec;
  private readonly ownCodec: boolean;
  private readonly policy: CompressionPolicy;
  private readonly ctrl = new AbortController();
  private readonly meter = new SpeedMeter(10_000);
  private queue: Task[] = [];
  private remaining: number[];
  private inflight = new Map<Task, { xhr: XMLHttpRequest | null; raw: number }>();
  private confirmed = 0;
  private resumed = 0;
  private rawSent = 0;
  private wireSent = 0;
  private phase: UploadPhase = 'staging';
  private paused = false;
  private aborted = false;
  private failed: unknown = null;
  private failures = 0;
  private backoffUntil = 0;
  private notice: string | null = null;
  private finalizeInfo: UploadStatus['finalize'] = null;
  private wakers: (() => void)[] = [];
  private lastReport = 0;

  constructor(
    items: UploadItem[],
    private readonly opts: UploadOptions,
  ) {
    this.items = items;
    this.total = items.reduce((s, it) => s + it.file.size, 0);
    this.remaining = items.map(() => 0);
    this.chunkSize = Math.max(64 * 1024, opts.chunkSize ?? CHUNK_SIZE);
    this.concurrency = Math.max(1, opts.concurrency ?? CONCURRENCY);
    this.ownCodec = !opts.codec;
    this.codec = opts.codec ?? createCodec();
    this.policy = new CompressionPolicy(opts.compress !== false && this.codec.gzip, this.codec.size);
  }

  // -- control ---------------------------------------------------------------------------------
  private wake() {
    const w = this.wakers;
    this.wakers = [];
    w.forEach((f) => f());
  }

  /** resolves on the next wake() or after `ms` */
  private nap(ms: number): Promise<void> {
    return new Promise((resolve) => {
      const t = setTimeout(resolve, ms);
      this.wakers.push(() => {
        clearTimeout(t);
        resolve();
      });
    });
  }

  private stopped(): boolean {
    return this.aborted || this.failed !== null;
  }

  private abortTransfers() {
    for (const f of this.inflight.values()) f.xhr?.abort();
  }

  pause() {
    if (this.stopped() || this.paused || this.phase === 'finalizing' || this.phase === 'done') return;
    this.paused = true;
    this.notice = null;
    this.abortTransfers(); // their chunks go back to the queue
    this.meter.reset();
    this.report(true);
  }

  resume() {
    if (this.stopped() || !this.paused) {
      this.retryNow();
      return;
    }
    this.paused = false;
    this.notice = null;
    this.failures = 0;
    this.backoffUntil = 0;
    this.meter.reset();
    this.wake();
    this.report(true);
  }

  /** the network is back (or the user wants it now): retry at once */
  retryNow() {
    if (this.backoffUntil > Date.now()) {
      this.backoffUntil = 0;
      this.wake();
    }
  }

  abort() {
    if (this.aborted) return;
    this.aborted = true;
    this.ctrl.abort();
    this.abortTransfers();
    this.wake();
    if (this.ownCodec) this.codec.dispose();
    if (this.uploadId) api.del(`/uploads/${encodeURIComponent(this.uploadId)}`).catch(() => undefined);
  }

  private fail(err: unknown) {
    if (this.failed === null) this.failed = err;
    this.abortTransfers();
    this.wake();
  }

  /** waits while paused or backing off; false when the upload stopped */
  private async gate(): Promise<boolean> {
    for (;;) {
      if (this.stopped()) return false;
      if (this.paused) {
        await this.nap(60_000);
        continue;
      }
      const wait = this.backoffUntil - Date.now();
      if (wait > 0) {
        this.report(true);
        await this.nap(Math.min(wait, 1000)); // a tick per second for the countdown
        continue;
      }
      return true;
    }
  }

  private backoff(err: unknown) {
    this.failures += 1;
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    const s = offline ? BACKOFF_MAX_S : Math.min(BACKOFF_MAX_S, 2 ** (this.failures - 1));
    this.backoffUntil = Math.max(this.backoffUntil, Date.now() + s * 1000 * (0.85 + Math.random() * 0.3));
    this.notice = offline ? 'Нет сети — загрузка продолжится, когда связь вернётся' : errorMessage(err);
    this.meter.reset();
    this.report(true);
  }

  private pauseWith(message: string) {
    this.paused = true;
    this.notice = message;
    this.abortTransfers();
    this.meter.reset();
    this.report(true);
  }

  /** a JSON request, retried like the transfers (network, server hiccups); others throw */
  private async retrying<T>(fn: () => Promise<T>): Promise<T> {
    let attempts = 0;
    for (;;) {
      if (!(await this.gate())) throw this.aborted ? new UploadAbortedError() : this.failed;
      try {
        const out = await fn();
        this.ok();
        return out;
      } catch (err) {
        if (this.aborted) throw new UploadAbortedError();
        const kind = classifyError(err);
        if (kind === 'fatal') throw err;
        const network = err instanceof ApiError && err.status === 0;
        attempts += network ? 0 : 1;
        if (kind === 'pause' || attempts >= MAX_ATTEMPTS) {
          attempts = 0;
          this.pauseWith(errorMessage(err));
        } else this.backoff(err);
      }
    }
  }

  private ok() {
    if (this.failures || this.notice) {
      this.failures = 0;
      this.notice = null;
      this.report(true);
    }
  }

  // -- progress --------------------------------------------------------------------------------
  private get loaded(): number {
    let n = this.confirmed;
    for (const f of this.inflight.values()) n += f.raw;
    return Math.min(this.total, n);
  }

  progress(): UploadProgress {
    const loaded = this.phase === 'finalizing' || this.phase === 'done' ? this.total : this.loaded;
    const now = Date.now();
    const waiting = !this.paused && this.backoffUntil > now;
    const state: UploadState = this.paused ? 'paused' : waiting ? 'waiting' : 'running';
    const rate = this.phase === 'uploading' && state === 'running' ? this.meter.rate : null;
    let fileIndex = this.remaining.findIndex((n) => n > 0);
    if (fileIndex < 0) fileIndex = Math.max(0, this.items.length - 1);
    return {
      phase: this.phase,
      state,
      loaded,
      total: this.total,
      fraction: this.total > 0 ? Math.min(1, loaded / this.total) : this.phase === 'done' ? 1 : 0,
      fileIndex,
      fileCount: this.items.length,
      currentPath: this.items[fileIndex]?.path ?? '',
      bytesPerSec: rate,
      etaS: rate && rate > 0 ? (this.total - loaded) / rate : null,
      compression: this.rawSent > 0 && this.wireSent < this.rawSent ? this.wireSent / this.rawSent : null,
      resumed: this.resumed,
      retryInS: waiting ? Math.max(1, Math.ceil((this.backoffUntil - now) / 1000)) : null,
      notice: this.paused || waiting ? this.notice : null,
      finalize: this.phase === 'finalizing' ? this.finalizeInfo : null,
    };
  }

  private report(force = false) {
    const now = performance.now();
    if (this.phase === 'uploading' && !this.paused) this.meter.push(now, this.loaded);
    if (!this.opts.onProgress || (!force && now - this.lastReport < REPORT_MS)) return;
    this.lastReport = now;
    this.opts.onProgress(this.progress());
  }

  // -- the upload ------------------------------------------------------------------------------
  async run(): Promise<Recording> {
    try {
      return await this.runInner();
    } catch (err) {
      if (this.aborted) throw new UploadAbortedError();
      throw err;
    } finally {
      if (this.ownCodec) this.codec.dispose();
    }
  }

  private async runInner(): Promise<Recording> {
    if (!this.items.length) throw new ApiError('Выберите файл или папку', 400);
    if (this.opts.signal?.aborted) throw new UploadAbortedError();
    this.report(true);
    const signal = this.ctrl.signal;
    let status: UploadStatus | null = null;
    if (this.opts.resumeId) {
      const id = this.opts.resumeId;
      status = await this.retrying(() => api.get<UploadStatus>(`/uploads/${encodeURIComponent(id)}`, { signal })).catch((err) => {
        if (err instanceof ApiError && err.status === 404) return null; // expired / removed: start over
        throw err;
      });
      if (status) this.uploadId = id;
    }
    if (!this.uploadId) {
      const created = await this.retrying(() => api.post<UploadCreated>('/uploads', this.opts.name ? { name: this.opts.name } : {}, { signal }));
      this.uploadId = created.upload_id;
    }
    this.opts.onStaged?.(this.uploadId);
    if (this.aborted) throw new UploadAbortedError();
    if (status?.state === 'done' && status.recording) return this.finish(status.recording);
    if (status?.state !== 'finalizing') {
      await this.plan(status);
      this.phase = 'uploading';
      this.meter.reset();
      this.report(true);
      await Promise.all(Array.from({ length: this.concurrency }, () => this.lane()));
      if (this.aborted) throw new UploadAbortedError();
      if (this.failed !== null) throw this.failed;
    }
    return this.finish(await this.finalize());
  }

  private finish(rec: Recording): Recording {
    this.phase = 'done';
    this.report(true);
    return rec;
  }

  /** What to send: everything the server does not hold yet. */
  private async plan(status: UploadStatus | null) {
    const id = encodeURIComponent(this.uploadId as string);
    const have = new Map((status?.files ?? []).map((f) => [f.path, f.size_bytes]));
    for (let i = 0; i < this.items.length; i += 1) {
      const { file, path } = this.items[i];
      if (have.get(path) === file.size) {
        this.confirmed += file.size; // already on the server
        this.resumed += file.size;
        continue;
      }
      if (file.size <= this.chunkSize) {
        this.queue.push({ file: i, chunk: null, start: 0, end: file.size, attempts: 0 });
        this.remaining[i] += 1;
        continue;
      }
      const fp = await this.codec.fingerprint(file);
      const body = { path, size_bytes: file.size, chunk_size: this.chunkSize, fingerprint: fp };
      const st = await this.retrying(() => api.post<ChunkedFileState>(`/uploads/${id}/chunked`, body, { signal: this.ctrl.signal }));
      this.confirmed += st.received_bytes;
      this.resumed += st.received_bytes;
      for (const [a, b] of st.missing ?? []) {
        for (let c = a; c <= b; c += 1) {
          const start = c * this.chunkSize;
          this.queue.push({ file: i, chunk: c, start, end: Math.min(file.size, start + this.chunkSize), attempts: 0 });
          this.remaining[i] += 1;
        }
      }
      this.report();
    }
  }

  private async lane(): Promise<void> {
    for (;;) {
      if (!(await this.gate())) return;
      const task = this.queue.shift();
      if (!task) return;
      try {
        await this.send(task);
        this.ok();
      } catch (err) {
        if (this.aborted) return;
        if (err instanceof TransferAborted) {
          this.queue.unshift(task); // paused, or another lane failed: sent again later
          continue;
        }
        task.attempts += 1;
        const kind = classifyError(err);
        const network = err instanceof ApiError && err.status === 0;
        if (kind === 'fatal') {
          this.fail(err);
          return;
        }
        this.queue.unshift(task);
        if (kind === 'pause' || (!network && task.attempts >= MAX_ATTEMPTS)) {
          task.attempts = 0;
          this.pauseWith(errorMessage(err));
        } else this.backoff(err);
      }
    }
  }

  private async send(task: Task) {
    const item = this.items[task.file];
    const size = task.end - task.start;
    const gzip = size >= MIN_GZIP && !PACKED.test(item.path) && this.policy.next();
    let prepared: PreparedChunk;
    try {
      prepared = await this.codec.prepare(item.file, task.start, task.end, gzip);
    } catch {
      if (this.paused || this.stopped()) throw new TransferAborted();
      throw new FileReadError(item.path);
    }
    if (gzip) this.policy.compressed(prepared.rawSize, prepared.body.byteLength, prepared.codecMs);
    if (this.paused || this.stopped()) throw new TransferAborted();
    const id = encodeURIComponent(this.uploadId as string);
    const path = encodeURIComponent(item.path);
    const url =
      task.chunk === null
        ? `${API_BASE}/uploads/${id}/files?path=${path}&size=${item.file.size}`
        : `${API_BASE}/uploads/${id}/chunked/${task.chunk}?path=${path}`;
    const slot = { xhr: null as XMLHttpRequest | null, raw: 0 };
    this.inflight.set(task, slot);
    const concurrent = this.inflight.size;
    const scale = prepared.body.byteLength > 0 ? prepared.rawSize / prepared.body.byteLength : 1;
    try {
      const sent = await xhrPut(
        url,
        prepared,
        (wire) => {
          slot.raw = Math.min(prepared.rawSize, Math.round(wire * scale));
          this.report();
        },
        (x) => (slot.xhr = x),
      );
      this.policy.sent(sent.wire, sent.ms, Math.max(concurrent, this.inflight.size));
    } finally {
      this.inflight.delete(task);
    }
    this.confirmed += prepared.rawSize;
    this.rawSent += prepared.rawSize;
    this.wireSent += prepared.body.byteLength;
    this.remaining[task.file] -= 1;
    this.report();
  }

  private async finalize(): Promise<Recording> {
    this.phase = 'finalizing';
    this.finalizeInfo = null;
    this.report(true);
    const id = encodeURIComponent(this.uploadId as string);
    const signal = this.ctrl.signal;
    const start = () => this.retrying(() => api.post<UploadStatus>(`/uploads/${id}/finalize`, undefined, { query: { wait: false }, signal }));
    let status = await start();
    for (;;) {
      if (status.state === 'done' && status.recording) return status.recording;
      if (status.error) throw new ApiError(status.error, 422, status.error);
      if (status.state === 'receiving') status = await start(); // a restarted server forgot the finalize
      else {
        this.finalizeInfo = status.finalize;
        this.report(true);
        await sleep(this.opts.pollMs ?? FINALIZE_POLL_MS);
        status = await this.retrying(() => api.get<UploadStatus>(`/uploads/${id}`, { signal }));
      }
    }
  }
}

/** Uploads files (a single file, several files or a whole folder) as one recording. */
export function uploadRecording(files: Iterable<File | UploadItem> | ArrayLike<File>, opts: UploadOptions = {}): UploadHandle {
  const up = new Uploader(toUploadItems(files), opts);
  opts.signal?.addEventListener('abort', () => up.abort(), { once: true });
  const online = () => up.retryNow();
  if (typeof window !== 'undefined') window.addEventListener('online', online);
  const promise = up.run();
  promise
    .catch((err: unknown) => {
      // a staging area that cannot become a recording is dropped; any other is kept for resuming
      if (dropsArea(err) && up.uploadId) api.del(`/uploads/${encodeURIComponent(up.uploadId)}`).catch(() => undefined);
    })
    .finally(() => {
      if (typeof window !== 'undefined') window.removeEventListener('online', online);
    });
  return {
    promise,
    abort: () => up.abort(),
    pause: () => up.pause(),
    resume: () => up.resume(),
    get uploadId() {
      return up.uploadId;
    },
  };
}

// ---------------------------------------------------------------- drag and drop of folders

interface FsEntry {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  fullPath: string;
}
interface FsFileEntry extends FsEntry {
  file(ok: (f: File) => void, err: (e: unknown) => void): void;
}
interface FsDirEntry extends FsEntry {
  createReader(): { readEntries(ok: (e: FsEntry[]) => void, err: (e: unknown) => void): void };
}

async function walk(entry: FsEntry, prefix: string, out: UploadItem[]): Promise<void> {
  if (entry.isFile) {
    const file = await new Promise<File>((ok, err) => (entry as FsFileEntry).file(ok, err));
    out.push({ file, path: cleanPath(prefix + entry.name) });
    return;
  }
  if (!entry.isDirectory) return;
  const reader = (entry as FsDirEntry).createReader();
  // readEntries returns batches (≤ 100 in Chromium) until an empty one
  for (;;) {
    const batch = await new Promise<FsEntry[]>((ok, err) => reader.readEntries(ok, err));
    if (!batch.length) break;
    for (const e of batch) await walk(e, `${prefix}${entry.name}/`, out);
  }
}

/** Files of a drop event, folders walked recursively with their relative paths. */
export async function filesFromDataTransfer(dt: DataTransfer): Promise<UploadItem[]> {
  const entries: FsEntry[] = [];
  const loose: File[] = [];
  for (const item of Array.from(dt.items ?? [])) {
    if (item.kind !== 'file') continue;
    const entry = (item as DataTransferItem & { webkitGetAsEntry?: () => FsEntry | null }).webkitGetAsEntry?.();
    if (entry) entries.push(entry);
    else {
      const f = item.getAsFile();
      if (f) loose.push(f);
    }
  }
  if (!entries.length && !loose.length) return toUploadItems(Array.from(dt.files ?? []));
  const out: UploadItem[] = toUploadItems(loose);
  for (const e of entries) await walk(e, '', out);
  return out;
}
