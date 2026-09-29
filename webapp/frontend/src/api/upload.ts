// Upload of a recording (webapp/API.md): POST /api/uploads → XHR PUT of every file (streamed, with
// progress) → POST /api/uploads/{id}/finalize → Recording. Folders keep their relative paths
// (input webkitdirectory → File.webkitRelativePath; drag and drop → filesFromDataTransfer).
import { API_BASE, ApiError, OFFLINE_MESSAGE, api, detailMessage } from './client';
import type { Recording, UploadCreated, UploadedFile } from './types';

export interface UploadItem {
  file: File;
  path: string; // relative, "/"-separated
}

export interface UploadProgress {
  phase: 'staging' | 'uploading' | 'finalizing' | 'done';
  loaded: number; // bytes sent over all files
  total: number;
  fraction: number; // 0..1
  fileIndex: number; // 0-based, the file being sent
  fileCount: number;
  currentPath: string;
  bytesPerSec: number | null; // moving average over the last few seconds
  etaS: number | null;
}

export interface UploadOptions {
  name?: string;
  onProgress?: (p: UploadProgress) => void;
  signal?: AbortSignal;
}

export interface UploadHandle {
  promise: Promise<Recording>;
  abort(): void;
}

export class UploadAbortedError extends Error {
  constructor() {
    super('Загрузка отменена');
    this.name = 'UploadAbortedError';
  }
}

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

  /** bytes / second, or null until there is half a second of data. */
  get rate(): number | null {
    if (this.samples.length < 2) return null;
    const [t0, b0] = this.samples[0];
    const [t1, b1] = this.samples[this.samples.length - 1];
    const dt = (t1 - t0) / 1000;
    return dt >= 0.5 ? Math.max(0, (b1 - b0) / dt) : null;
  }
}

function putFile(uploadId: string, item: UploadItem, onBytes: (loaded: number) => void, register: (x: XMLHttpRequest) => void): Promise<UploadedFile> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    register(xhr);
    const url = `${API_BASE}/uploads/${encodeURIComponent(uploadId)}/files?path=${encodeURIComponent(item.path)}`;
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.upload.onprogress = (e) => onBytes(e.loaded);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onBytes(item.file.size);
        try {
          resolve(JSON.parse(xhr.responseText) as UploadedFile);
        } catch {
          resolve({ path: item.path, size_bytes: item.file.size });
        }
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
    xhr.onerror = () => reject(new ApiError('Связь с сервером прервалась во время загрузки', 0));
    xhr.onabort = () => reject(new UploadAbortedError());
    xhr.send(item.file);
  });
}

/** Uploads files (a single file, several files or a whole folder) as one recording. */
export function uploadRecording(files: Iterable<File | UploadItem> | ArrayLike<File>, opts: UploadOptions = {}): UploadHandle {
  const items = toUploadItems(files);
  const total = items.reduce((s, it) => s + it.file.size, 0);
  let aborted = false;
  let xhr: XMLHttpRequest | null = null;
  let uploadId: string | null = null;
  const meter = new SpeedMeter();

  const report = (phase: UploadProgress['phase'], fileIndex: number, loaded: number) => {
    if (!opts.onProgress) return;
    meter.push(performance.now(), loaded);
    const rate = phase === 'uploading' ? meter.rate : null;
    opts.onProgress({
      phase,
      loaded,
      total,
      fraction: total > 0 ? Math.min(1, loaded / total) : phase === 'done' ? 1 : 0,
      fileIndex,
      fileCount: items.length,
      currentPath: items[Math.min(fileIndex, items.length - 1)]?.path ?? '',
      bytesPerSec: rate,
      etaS: rate && rate > 0 ? (total - loaded) / rate : null,
    });
  };

  const abort = () => {
    if (aborted) return;
    aborted = true;
    xhr?.abort();
    if (uploadId) api.del(`/uploads/${encodeURIComponent(uploadId)}`).catch(() => undefined);
  };
  opts.signal?.addEventListener('abort', abort, { once: true });

  const promise = (async () => {
    if (!items.length) throw new ApiError('Выберите файл или папку', 400);
    if (opts.signal?.aborted) throw new UploadAbortedError();
    report('staging', 0, 0);
    const created = await api.post<UploadCreated>('/uploads', opts.name ? { name: opts.name } : {});
    uploadId = created.upload_id;
    if (aborted) {
      api.del(`/uploads/${encodeURIComponent(uploadId)}`).catch(() => undefined);
      throw new UploadAbortedError();
    }
    let done = 0;
    for (let i = 0; i < items.length; i += 1) {
      if (aborted) throw new UploadAbortedError();
      const base = done;
      report('uploading', i, base);
      await putFile(uploadId, items[i], (b) => report('uploading', i, base + b), (x) => (xhr = x));
      done += items[i].file.size;
    }
    xhr = null;
    if (aborted) throw new UploadAbortedError();
    report('finalizing', items.length - 1, total);
    const rec = await api.post<Recording>(`/uploads/${encodeURIComponent(uploadId)}/finalize`);
    report('done', items.length - 1, total);
    return rec;
  })();

  promise.catch(() => {
    // a failed (not aborted) upload leaves a staging area behind: drop it
    if (!aborted && uploadId) api.del(`/uploads/${encodeURIComponent(uploadId)}`).catch(() => undefined);
  });

  return { promise, abort };
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
