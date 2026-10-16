import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { crc32, crcHex } from './chunkCodec';
import { FileReadError, SpeedMeter, UploadAbortedError, classifyError, cleanPath, dropsArea, suggestName, toUploadItems, uploadRecording, type UploadProgress } from './upload';
import type { Codec } from './codec';
import { ApiError } from './client';

const CHUNK = 64 * 1024;

// ------------------------------------------------------------------ a fake backend
// JSON endpoints answer through fetch; the PUTs of files and chunks through a XMLHttpRequest
// double that checks the CRC header and inflates gzip bodies like the server does.

interface Req {
  method: string;
  url: string;
  headers: Record<string, string>;
  size: number;
}
type Answer = { status: number; body?: unknown } | 'hold' | 'network';

const server = {
  files: new Map<string, Uint8Array>(), // whole files
  chunks: new Map<string, Map<number, Uint8Array>>(), // path -> chunk index -> raw bytes
  declared: new Map<string, { size: number; chunk: number }>(),
  have: [] as { path: string; size_bytes: number }[], // GET status: finished files (resume)
  missing: null as [number, number][] | null, // the declare answer (resume)
  status: 'ok' as 'ok' | 'fails',
  polls: 0,
  /** a hook per request: return an answer to override the default */
  hook: null as null | ((r: Req) => Answer | undefined),
  sent: [] as Req[],
  deleted: 0,
  finalize409: 0,
};

async function inflate(body: ArrayBuffer, gzip: boolean): Promise<Uint8Array> {
  if (!gzip) return new Uint8Array(body);
  const s = new Blob([body]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Uint8Array(await new Response(s).arrayBuffer());
}

class FakeXHR {
  static last: FakeXHR | null = null;
  static live = new Set<FakeXHR>();
  upload = { onprogress: null as null | ((e: { loaded: number }) => void) };
  onload: null | (() => void) = null;
  onerror: null | (() => void) = null;
  onabort: null | (() => void) = null;
  status = 0;
  responseText = '';
  private req: Req = { method: '', url: '', headers: {}, size: 0 };
  open(method: string, url: string) {
    this.req.method = method;
    this.req.url = url;
  }
  setRequestHeader(k: string, v: string) {
    this.req.headers[k] = v;
  }
  send(blob: Blob) {
    this.req.size = blob.size;
    server.sent.push(this.req);
    FakeXHR.last = this;
    FakeXHR.live.add(this);
    const ans = server.hook?.(this.req);
    if (ans === 'hold') return;
    void blob.arrayBuffer().then((body) => this.answer(body, ans));
  }
  private async answer(body: ArrayBuffer, ans: Exclude<Answer, 'hold'> | undefined) {
    this.upload.onprogress?.({ loaded: Math.floor(body.byteLength / 2) });
    await Promise.resolve();
    if (!FakeXHR.live.has(this)) return; // aborted meanwhile
    FakeXHR.live.delete(this);
    if (ans === 'network') {
      this.onerror?.();
      return;
    }
    if (ans) return this.reply(ans.status, ans.body);
    const u = new URL(this.req.url, 'http://x');
    const path = u.searchParams.get('path') ?? '';
    const raw = await inflate(body, this.req.headers['X-Content-Encoding'] === 'gzip');
    if (this.req.headers['X-Content-CRC32'] !== crcHex(crc32(raw))) return this.reply(400, { detail: 'Контрольная сумма не совпала' });
    const m = u.pathname.match(/\/chunked\/(\d+)$/);
    if (m) {
      const per = server.chunks.get(path) ?? new Map();
      per.set(Number(m[1]), raw);
      server.chunks.set(path, per);
      return this.reply(200, { path, received_chunks: per.size });
    }
    if (Number(u.searchParams.get('size')) !== raw.length) return this.reply(400, { detail: 'не полностью' });
    server.files.set(path, raw);
    return this.reply(200, { path, size_bytes: raw.length });
  }
  private reply(status: number, body: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.onload?.();
  }
  abort() {
    if (!FakeXHR.live.delete(this)) return;
    this.onabort?.();
  }
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function fakeFetch(url: string, init: RequestInit) {
  const u = new URL(url, 'http://x');
  const p = u.pathname;
  if (p === '/api/uploads' && init.method === 'POST') return json({ upload_id: 'u1' });
  if (p === '/api/uploads/u1/chunked') {
    const b = JSON.parse(String(init.body)) as { path: string; size_bytes: number; chunk_size: number; fingerprint: string };
    server.declared.set(b.path, { size: b.size_bytes, chunk: b.chunk_size });
    const n = Math.ceil(b.size_bytes / b.chunk_size);
    const missing = server.missing ?? [[0, n - 1]];
    const received = n - missing.reduce((s, [a, z]) => s + z - a + 1, 0);
    return json({ path: b.path, size_bytes: b.size_bytes, chunk_size: b.chunk_size, n_chunks: n, received_chunks: received, received_bytes: received * b.chunk_size, complete: false, missing });
  }
  if (p === '/api/uploads/u1/finalize') {
    expect(u.searchParams.get('wait')).toBe('false');
    if (server.finalize409 > 0) {
      server.finalize409 -= 1;
      return json({ detail: 'Файлы ещё передаются — дождитесь окончания загрузки' }, 409);
    }
    return json({ upload_id: 'u1', state: 'finalizing', finalize: { stage: 'starting', fraction: null }, error: null, recording: null }, 202);
  }
  if (p === '/api/uploads/u1' && init.method === 'GET') {
    if (server.status === 'fails') return json({ upload_id: 'u1', state: 'receiving', finalize: null, error: 'В загрузке не найдено ни записи rosbag2', recording: null, files: [], partial: [], bytes_received: 0 });
    server.polls += 1;
    if (server.polls === 1 && server.have.length) return json({ upload_id: 'u1', state: 'receiving', files: server.have, partial: [], bytes_received: 0, finalize: null, error: null, recording: null });
    if (server.polls <= (server.have.length ? 2 : 1))
      return json({ upload_id: 'u1', state: 'finalizing', finalize: { stage: 'unpacking', fraction: 0.5 }, error: null, recording: null });
    return json({ upload_id: 'u1', state: 'done', finalize: null, error: null, recording: { id: 'r1', name: 'doubleT' } });
  }
  if (p === '/api/uploads/u1' && init.method === 'DELETE') {
    server.deleted += 1;
    return new Response(null, { status: 204 });
  }
  return json({ detail: 'нет' }, 404);
}

function file(name: string, data: Uint8Array | number, rel = ''): File {
  const f = new File([typeof data === 'number' ? new Uint8Array(data) : (data as BlobPart)], name);
  if (rel) Object.defineProperty(f, 'webkitRelativePath', { value: rel });
  return f;
}

/** compressible bytes with some structure (like a point cloud) */
function cloudish(n: number): Uint8Array {
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i += 1) out[i] = (i % 26 < 12 ? (i * 7) & 0x3f : i % 26 === 16 ? i % 128 : 0) as number;
  return out;
}

function assembled(path: string): Uint8Array {
  const per = server.chunks.get(path) ?? new Map<number, Uint8Array>();
  const parts = [...per.entries()].sort((a, b) => a[0] - b[0]).map(([, v]) => v);
  const out = new Uint8Array(parts.reduce((s, p) => s + p.length, 0));
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

const chunkPuts = () => server.sent.filter((r) => r.url.includes('/chunked/'));

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  Object.assign(server, { files: new Map(), chunks: new Map(), declared: new Map(), have: [], missing: null, status: 'ok', polls: 0, hook: null, sent: [], deleted: 0, finalize409: 0 });
  FakeXHR.live.clear();
  vi.stubGlobal('XMLHttpRequest', FakeXHR);
  fetchMock = vi.fn((url: string, init: RequestInit) => Promise.resolve(fakeFetch(url, init)));
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const calls = (method: string, path: string) => fetchMock.mock.calls.filter(([u, i]) => (i as RequestInit).method === method && String(u).split('?')[0] === path);

describe('upload helpers', () => {
  it('cleans paths and derives names', () => {
    expect(cleanPath('..\\bag//./a.db3')).toBe('bag/a.db3');
    expect(cleanPath('/abs/../x.yaml')).toBe('abs/x.yaml');
    const items = toUploadItems([file('metadata.yaml', 3, 'doubleT/metadata.yaml'), file('a.db3', 5, 'doubleT/a.db3')]);
    expect(items.map((i) => i.path)).toEqual(['doubleT/metadata.yaml', 'doubleT/a.db3']);
    expect(suggestName(items)).toBe('doubleT');
    expect(suggestName(toUploadItems([file('doubleT_platform.zip', 1)]))).toBe('doubleT_platform');
  });

  it('measures speed over a window', () => {
    const m = new SpeedMeter(3000);
    m.push(0, 0);
    expect(m.rate).toBeNull();
    m.push(1000, 1_000_000);
    expect(m.rate).toBeCloseTo(1_000_000);
    m.push(5000, 3_000_000);
    expect(m.rate).toBeCloseTo(500_000); // window keeps (1000, 1e6) … (5000, 3e6)
    m.reset();
    expect(m.rate).toBeNull();
  });

  it('sorts errors into retry / pause / fatal', () => {
    expect(classifyError(new ApiError('связь', 0))).toBe('retry');
    expect(classifyError(new ApiError('crc', 400))).toBe('retry');
    expect(classifyError(new ApiError('прокси', 502))).toBe('retry');
    expect(classifyError(new ApiError('ещё передаются', 409))).toBe('retry'); // a dead connection's write
    expect(classifyError(new ApiError('диск', 507))).toBe('pause');
    expect(dropsArea(new ApiError('не запись', 422))).toBe(true);
    expect(dropsArea(new ApiError('ещё передаются', 409))).toBe(false);
    expect(dropsArea(new FileReadError('a.db3'))).toBe(false);
    expect(classifyError(new ApiError('нет', 404))).toBe('fatal');
    expect(classifyError(new ApiError('много', 413))).toBe('fatal');
    expect(classifyError(new Error('?'))).toBe('fatal');
  });
});

describe('uploadRecording', () => {
  it('sends small files whole, big ones in checked chunks (gzip when it pays), finalizes in the background', async () => {
    const seen: UploadProgress[] = [];
    const staged: string[] = [];
    const meta = new TextEncoder().encode('rosbag2: x');
    const db3 = cloudish(3 * CHUNK + 8192);
    const h = uploadRecording([file('metadata.yaml', meta, 'doubleT/metadata.yaml'), file('a.db3', db3, 'doubleT/a.db3')], {
      name: 'doubleT',
      pollMs: 10,
      chunkSize: CHUNK,
      onProgress: (p) => seen.push(p),
      onStaged: (id) => staged.push(id),
    });
    const rec = await h.promise;
    expect(rec.id).toBe('r1');
    expect(staged).toEqual(['u1']);
    expect(h.uploadId).toBe('u1');
    expect(JSON.parse(String(calls('POST', '/api/uploads')[0][1].body))).toEqual({ name: 'doubleT' });
    const decl = JSON.parse(String(calls('POST', '/api/uploads/u1/chunked')[0][1].body));
    expect(decl).toMatchObject({ path: 'doubleT/a.db3', size_bytes: db3.length, chunk_size: CHUNK });
    expect(decl.fingerprint).toMatch(/^[0-9a-f]+-[0-9a-f]{8}-[0-9a-f]{8}$/);

    expect(server.files.get('doubleT/metadata.yaml')).toEqual(meta);
    expect(server.sent.find((r) => r.url.includes('/files?'))?.url).toBe('/api/uploads/u1/files?path=doubleT%2Fmetadata.yaml&size=10');
    expect(chunkPuts().map((r) => r.url).sort()).toEqual([0, 1, 2, 3].map((i) => `/api/uploads/u1/chunked/${i}?path=doubleT%2Fa.db3`));
    expect(assembled('doubleT/a.db3')).toEqual(db3);
    const gz = chunkPuts().filter((r) => r.headers['X-Content-Encoding'] === 'gzip');
    expect(gz.length).toBeGreaterThan(0); // compressible: gzipped (and fewer bytes on the wire)
    expect(gz.every((r) => r.size < CHUNK / 2)).toBe(true);

    expect(seen[0].phase).toBe('staging');
    expect(seen.some((p) => p.phase === 'uploading' && p.fileCount === 2 && p.state === 'running')).toBe(true);
    expect(seen.some((p) => p.phase === 'finalizing' && p.finalize?.stage === 'unpacking' && p.finalize.fraction === 0.5)).toBe(true);
    const last = seen[seen.length - 1];
    expect(last).toMatchObject({ phase: 'done', loaded: meta.length + db3.length, total: meta.length + db3.length, fraction: 1, resumed: 0 });
    expect(seen.some((p) => p.compression !== null && p.compression < 0.5)).toBe(true);
  });

  it('resumes: sends only what the server does not hold', async () => {
    server.have = [{ path: 'doubleT/metadata.yaml', size_bytes: 10 }];
    server.missing = [[2, 3]];
    const seen: UploadProgress[] = [];
    const db3 = cloudish(3 * CHUNK + 100);
    const h = uploadRecording([file('metadata.yaml', 10, 'doubleT/metadata.yaml'), file('a.db3', db3, 'doubleT/a.db3')], {
      chunkSize: CHUNK,
      pollMs: 10,
      resumeId: 'u1',
      onProgress: (p) => seen.push(p),
    });
    expect((await h.promise).id).toBe('r1');
    expect(calls('POST', '/api/uploads')).toHaveLength(0); // no new staging area
    expect(server.sent.some((r) => r.url.includes('/files?'))).toBe(false);
    expect(chunkPuts().map((r) => r.url.split('?')[0]).sort()).toEqual(['/api/uploads/u1/chunked/2', '/api/uploads/u1/chunked/3']);
    expect(server.chunks.get('doubleT/a.db3')?.get(2)).toEqual(db3.subarray(2 * CHUNK, 3 * CHUNK));
    expect(seen[seen.length - 1].resumed).toBe(10 + 2 * CHUNK);
  });

  it('publishes acknowledged bytes and compression even within the progress throttle interval', async () => {
    const clock = vi.spyOn(performance, 'now').mockReturnValue(1);
    server.hook = (r) => (r.url.includes('/chunked/1?') ? 'hold' : undefined);
    const seen: UploadProgress[] = [];
    const h = uploadRecording([file('a.db3', cloudish(2 * CHUNK))], {
      chunkSize: CHUNK, concurrency: 1, pollMs: 10, onProgress: (p) => seen.push(p),
    });
    try {
      await vi.waitFor(() => expect(chunkPuts()).toHaveLength(2));
      expect(server.chunks.get('a.db3')?.size).toBe(1);
      expect(seen[seen.length - 1]).toMatchObject({ phase: 'uploading', loaded: CHUNK, compression: expect.any(Number) });
      expect(seen[seen.length - 1].compression).toBeLessThan(0.5);
    } finally {
      h.abort();
      await h.promise.catch(() => undefined);
      clock.mockRestore();
    }
  });

  it('starts over when the upload to resume is gone', async () => {
    const staged: string[] = [];
    // GET /uploads/old1 is a 404 in the fake (expired): a new area is made
    const h = uploadRecording([file('r.jsonl', 5)], { pollMs: 10, resumeId: 'old1', onStaged: (id) => staged.push(id) });
    await h.promise;
    expect(calls('POST', '/api/uploads')).toHaveLength(1);
    expect(staged).toEqual(['u1']);
  });

  it('retries a dropped connection and a corrupted chunk, showing the wait', async () => {
    const failed = new Set<string>();
    server.hook = (r) => {
      const key = r.url.split('?')[0];
      if (key.endsWith('/chunked/1') && !failed.has(key)) {
        failed.add(key);
        return 'network';
      }
      if (key.endsWith('/chunked/2') && !failed.has(key)) {
        failed.add(key);
        return { status: 400, body: { detail: 'Контрольная сумма части не совпала' } };
      }
      return undefined;
    };
    const seen: UploadProgress[] = [];
    const data = cloudish(3 * CHUNK);
    const h = uploadRecording([file('a.db3', data)], { chunkSize: CHUNK, concurrency: 1, pollMs: 10, onProgress: (p) => seen.push(p) });
    await h.promise;
    expect(assembled('a.db3')).toEqual(data);
    expect(chunkPuts().filter((r) => r.url.includes('/chunked/1'))).toHaveLength(2);
    expect(chunkPuts().filter((r) => r.url.includes('/chunked/2'))).toHaveLength(2);
    const waits = seen.filter((p) => p.state === 'waiting');
    expect(waits.length).toBeGreaterThan(0);
    expect(waits[0].retryInS).toBeGreaterThanOrEqual(1);
    expect(waits.some((p) => p.notice === 'Связь с сервером прервалась во время загрузки')).toBe(true);
    expect(server.deleted).toBe(0);
  }, 15_000);

  it('pauses (the transfer stops, what arrived stays) and resumes', async () => {
    let hold = true;
    server.hook = () => (hold ? 'hold' : undefined);
    const seen: UploadProgress[] = [];
    const h = uploadRecording([file('a.db3', cloudish(2 * CHUNK))], { chunkSize: CHUNK, concurrency: 1, pollMs: 10, onProgress: (p) => seen.push(p) });
    await vi.waitFor(() => expect(chunkPuts()).toHaveLength(1));
    h.pause();
    expect(FakeXHR.live.size).toBe(0); // aborted
    expect(seen[seen.length - 1].state).toBe('paused');
    await new Promise((r) => setTimeout(r, 30));
    expect(chunkPuts()).toHaveLength(1); // nothing new while paused
    hold = false;
    h.resume();
    await h.promise;
    expect(chunkPuts().filter((r) => r.url.includes('/chunked/0'))).toHaveLength(2); // the aborted one again
    expect(server.deleted).toBe(0);
  });

  it('pauses with the message when the server disk is full', async () => {
    let full = true;
    server.hook = (r) => (full && r.url.includes('/chunked/') ? { status: 507, body: { detail: 'Недостаточно места на диске сервера' } } : undefined);
    const seen: UploadProgress[] = [];
    const h = uploadRecording([file('a.db3', cloudish(2 * CHUNK))], { chunkSize: CHUNK, concurrency: 1, pollMs: 10, onProgress: (p) => seen.push(p) });
    await vi.waitFor(() => expect(seen.some((p) => p.state === 'paused')).toBe(true));
    expect(seen.find((p) => p.state === 'paused')?.notice).toBe('Недостаточно места на диске сервера');
    full = false;
    h.resume();
    expect((await h.promise).id).toBe('r1');
  });

  it('aborts: rejects with UploadAbortedError and drops the staging area', async () => {
    server.hook = () => 'hold';
    const h = uploadRecording([file('a.zip', 100)]);
    await vi.waitFor(() => expect(server.sent).toHaveLength(1));
    h.abort();
    await expect(h.promise).rejects.toBeInstanceOf(UploadAbortedError);
    await vi.waitFor(() => expect(server.deleted).toBe(1));
  });

  it('a finalize that finds nothing usable rejects with the server message and drops the area', async () => {
    server.status = 'fails';
    const h = uploadRecording([file('notes.txt', 5)], { pollMs: 10 });
    await expect(h.promise).rejects.toThrow('В загрузке не найдено ни записи rosbag2');
    await vi.waitFor(() => expect(server.deleted).toBe(1));
  });

  it('a request refused for good stops the upload', async () => {
    server.hook = (r) => (r.url.includes('/chunked/') ? { status: 413, body: { detail: 'Превышен максимальный размер загрузки (100 ГБ)' } } : undefined);
    const h = uploadRecording([file('a.db3', cloudish(2 * CHUNK))], { chunkSize: CHUNK });
    await expect(h.promise).rejects.toThrow('Превышен максимальный размер');
    await vi.waitFor(() => expect(server.deleted).toBe(1)); // it can never become a recording
  });

  it('a finalize refused while a dead connection still holds the area is retried, never deleted', async () => {
    server.finalize409 = 1;
    const seen: UploadProgress[] = [];
    const h = uploadRecording([file('r.jsonl', 5)], { pollMs: 10, onProgress: (p) => seen.push(p) });
    expect((await h.promise).id).toBe('r1');
    expect(calls('POST', '/api/uploads/u1/finalize')).toHaveLength(2);
    expect(seen.some((p) => p.state === 'waiting' && p.notice === 'Файлы ещё передаются — дождитесь окончания загрузки')).toBe(true);
    expect(server.deleted).toBe(0);
  }, 10_000);

  it('a file the browser can no longer read stops the upload but keeps what the server holds', async () => {
    const broken: Codec = {
      size: 1,
      gzip: false,
      prepare: () => Promise.reject(new DOMException('The requested file could not be read', 'NotReadableError')),
      fingerprint: () => Promise.resolve('fp'),
      dispose: () => undefined,
    };
    const h = uploadRecording([file('a.db3', cloudish(2 * CHUNK))], { chunkSize: CHUNK, codec: broken });
    const err = await h.promise.catch((e: unknown) => e);
    expect(err).toBeInstanceOf(FileReadError);
    expect((err as Error).message).toMatch(/^Не удалось прочитать «a\.db3»/);
    await new Promise((r) => setTimeout(r, 20));
    expect(server.deleted).toBe(0);
    expect(h.uploadId).toBe('u1');
  });

  it('rejects an empty selection in Russian', async () => {
    await expect(uploadRecording([]).promise).rejects.toThrow('Выберите файл или папку');
  });
});
