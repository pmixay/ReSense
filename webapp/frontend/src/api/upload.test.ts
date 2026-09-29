import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SpeedMeter, UploadAbortedError, cleanPath, suggestName, toUploadItems, uploadRecording, type UploadProgress } from './upload';

// A minimal XMLHttpRequest double: records requests, reports progress, answers 200.
class FakeXHR {
  static sent: { method: string; url: string; size: number }[] = [];
  static hold = false;
  static last: FakeXHR | null = null;
  upload = { onprogress: null as null | ((e: { loaded: number }) => void) };
  onload: null | (() => void) = null;
  onerror: null | (() => void) = null;
  onabort: null | (() => void) = null;
  status = 0;
  responseText = '';
  private method = '';
  private url = '';
  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }
  setRequestHeader() {}
  send(body: Blob) {
    FakeXHR.sent.push({ method: this.method, url: this.url, size: body.size });
    FakeXHR.last = this;
    if (FakeXHR.hold) return;
    this.upload.onprogress?.({ loaded: Math.floor(body.size / 2) });
    this.status = 200;
    this.responseText = JSON.stringify({ path: decodeURIComponent(this.url.split('path=')[1]), size_bytes: body.size });
    this.onload?.();
  }
  abort() {
    this.onabort?.();
  }
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function file(name: string, size: number, rel = ''): File {
  const f = new File([new Uint8Array(size)], name);
  if (rel) Object.defineProperty(f, 'webkitRelativePath', { value: rel });
  return f;
}

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
  });
});

describe('uploadRecording', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    FakeXHR.sent = [];
    FakeXHR.hold = false;
    vi.stubGlobal('XMLHttpRequest', FakeXHR);
    fetchMock = vi.fn((url: string, init: RequestInit) => {
      if (url === '/api/uploads' && init.method === 'POST') return Promise.resolve(json({ upload_id: 'u1' }));
      if (url === '/api/uploads/u1/finalize') return Promise.resolve(json({ id: 'r1', name: 'doubleT' }, 201));
      if (url === '/api/uploads/u1' && init.method === 'DELETE') return Promise.resolve(new Response(null, { status: 204 }));
      return Promise.resolve(json({ detail: 'нет' }, 404));
    });
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it('stages, PUTs every file with its relative path, finalizes', async () => {
    const seen: UploadProgress[] = [];
    const h = uploadRecording([file('metadata.yaml', 10, 'doubleT/metadata.yaml'), file('a.db3', 30, 'doubleT/a.db3')], {
      name: 'doubleT',
      onProgress: (p) => seen.push(p),
    });
    const rec = await h.promise;
    expect(rec.id).toBe('r1');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ name: 'doubleT' });
    expect(FakeXHR.sent).toEqual([
      { method: 'PUT', url: '/api/uploads/u1/files?path=doubleT%2Fmetadata.yaml', size: 10 },
      { method: 'PUT', url: '/api/uploads/u1/files?path=doubleT%2Fa.db3', size: 30 },
    ]);
    expect(seen[0].phase).toBe('staging');
    expect(seen.some((p) => p.phase === 'uploading' && p.fileIndex === 1 && p.loaded === 25)).toBe(true);
    expect(seen[seen.length - 1]).toMatchObject({ phase: 'done', loaded: 40, total: 40, fraction: 1 });
  });

  it('aborts: rejects with UploadAbortedError and drops the staging area', async () => {
    FakeXHR.hold = true;
    const h = uploadRecording([file('a.zip', 100)]);
    await vi.waitFor(() => expect(FakeXHR.sent).toHaveLength(1));
    h.abort();
    await expect(h.promise).rejects.toBeInstanceOf(UploadAbortedError);
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([u, i]) => u === '/api/uploads/u1' && i.method === 'DELETE')).toBe(true));
  });

  it('rejects an empty selection in Russian', async () => {
    await expect(uploadRecording([]).promise).rejects.toThrow('Выберите файл или папку');
  });
});
