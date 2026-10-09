import { QueryClient } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recording } from '../../api/types';
import type { UploadOptions, UploadProgress } from '../../api/upload';
import { guessKind } from './kinds';
import {
  abortUpload,
  discardPending,
  dismissUpload,
  matchesPending,
  pauseUpload,
  restorePending,
  resumeUpload,
  startUpload,
  takeUploadResult,
  useUploadStore,
  type PendingUpload,
  type Picked,
} from './uploadStore';

const BASE: UploadProgress = {
  phase: 'staging',
  state: 'running',
  loaded: 0,
  total: 10,
  fraction: 0,
  fileIndex: 0,
  fileCount: 1,
  currentPath: 'a.jsonl',
  bytesPerSec: null,
  etaS: null,
  compression: null,
  resumed: 0,
  retryInS: null,
  notice: null,
  finalize: null,
};

// a localStorage for the node test environment
const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
  removeItem: (k: string) => void storage.delete(k),
});
const SESSION = 'resense.upload.v1';

// uploadRecording answered by hand: each call is recorded with its options and its promise controls
const calls: {
  opts: UploadOptions;
  resolve: (r: Recording) => void;
  reject: (e: unknown) => void;
  abort: ReturnType<typeof vi.fn>;
  pause: ReturnType<typeof vi.fn>;
  resume: ReturnType<typeof vi.fn>;
}[] = [];
vi.mock('../../api/upload', async (orig) => {
  const real = await orig<typeof import('../../api/upload')>();
  return {
    ...real,
    uploadRecording: (_files: unknown, opts: UploadOptions) => {
      let resolve!: (r: Recording) => void;
      let reject!: (e: unknown) => void;
      const promise = new Promise<Recording>((ok, err) => {
        resolve = ok;
        reject = err;
      });
      const abort = vi.fn(() => reject(new real.UploadAbortedError()));
      const pause = vi.fn();
      const resume = vi.fn();
      opts.onProgress?.({ ...BASE });
      calls.push({ opts, resolve, reject, abort, pause, resume });
      return { promise, abort, pause, resume, uploadId: null };
    },
  };
});

// the hook reads the store with useSyncExternalStore; outside React its snapshot is enough here
vi.mock('react', async (orig) => ({ ...(await orig<typeof import('react')>()), useSyncExternalStore: (_s: unknown, get: () => unknown) => get() }));

const picked = (name: string): Picked => ({ items: [{ file: new File(['x'], `${name}.jsonl`), path: `${name}.jsonl` }], guess: guessKind([`${name}.jsonl`]), name, bytes: 1 });
const rec = (id: string) => ({ id, name: id }) as Recording;
const progress = (fraction: number): UploadProgress => ({ ...BASE, phase: 'uploading', loaded: fraction * 10, fraction, currentPath: 'a', bytesPerSec: 5, etaS: 1 });
const settle = () => new Promise((r) => setTimeout(r, 0));

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

beforeEach(() => {
  calls.length = 0;
  abortUpload();
  discardPending();
  takeUploadResult();
  storage.clear();
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
});

describe('upload store', () => {
  it('follows the progress and hands the finished recording over once', async () => {
    const qc = new QueryClient();
    startUpload(qc, picked('ride'));
    expect(useUploadStore().run).toMatchObject({ status: 'uploading', picked: { name: 'ride' } });
    expect(useUploadStore().run?.progress?.phase).toBe('staging'); // the synchronous first report
    calls[0].opts.onProgress?.(progress(0.5));
    expect(useUploadStore().run?.progress?.fraction).toBe(0.5);

    calls[0].resolve(rec('r1'));
    await settle();
    expect(useUploadStore().run).toBeNull();
    expect(takeUploadResult()).toEqual(rec('r1'));
    expect(takeUploadResult()).toBeNull();
  });

  it('keeps a failure (with the server message) until it is dismissed; cancel forgets the upload', async () => {
    const qc = new QueryClient();
    startUpload(qc, picked('bad'));
    calls[0].reject(new Error('В загрузке не найдено ни записи rosbag2'));
    await settle();
    expect(useUploadStore().run).toMatchObject({ status: 'error', error: 'В загрузке не найдено ни записи rosbag2' });
    dismissUpload();
    expect(useUploadStore().run).toBeNull();

    startUpload(qc, picked('big'));
    abortUpload();
    expect(calls[1].abort).toHaveBeenCalled();
    await settle();
    expect(useUploadStore().run).toBeNull();
    expect(takeUploadResult()).toBeNull();
  });

  it('a new upload replaces the running one; the old one no longer reports', async () => {
    const qc = new QueryClient();
    startUpload(qc, picked('first'));
    startUpload(qc, picked('second'));
    expect(calls[0].abort).toHaveBeenCalled();
    calls[0].opts.onProgress?.(progress(0.9));
    expect(useUploadStore().run).toMatchObject({ picked: { name: 'second' } });
    expect(useUploadStore().run?.progress?.fraction).toBe(0);
    calls[1].resolve(rec('r2'));
    await settle();
    expect(takeUploadResult()).toEqual(rec('r2'));
  });
});

describe('resumable sessions', () => {
  const file = (name: string, size: number, lastModified = 1000) => new File([new Uint8Array(size)], name, { lastModified });
  const pending = (over: Partial<PendingUpload> = {}): PendingUpload => ({
    uploadId: 'u9',
    name: 'ride',
    files: [{ path: 'ride.zip', size: 3, lastModified: 1000 }],
    bytes: 3,
    folder: false,
    savedAt: '2026-10-09T10:00:00Z',
    ...over,
  });

  it('matches the same files only', () => {
    const p = pending();
    expect(matchesPending(p, [{ file: file('ride.zip', 3), path: 'ride.zip' }])).toBe(true);
    expect(matchesPending(p, [{ file: file('ride.zip', 4), path: 'ride.zip' }])).toBe(false); // size
    expect(matchesPending(p, [{ file: file('ride.zip', 3, 2000), path: 'ride.zip' }])).toBe(false); // modified
    expect(matchesPending(p, [{ file: file('other.zip', 3), path: 'other.zip' }])).toBe(false);
    expect(matchesPending(p, [])).toBe(false);
  });

  it('keeps the server id while uploading, forgets it when done; pause / resume reach the transfer', async () => {
    const qc = new QueryClient();
    startUpload(qc, picked('ride'));
    calls[0].opts.onStaged?.('u1');
    expect(JSON.parse(storage.get(SESSION) ?? '{}')).toMatchObject({ uploadId: 'u1', name: 'ride', bytes: 1, folder: false });
    pauseUpload();
    expect(calls[0].pause).toHaveBeenCalled();
    resumeUpload();
    expect(calls[0].resume).toHaveBeenCalled();
    calls[0].resolve(rec('r1'));
    await settle();
    expect(storage.has(SESSION)).toBe(false);
  });

  it('cancel forgets the session; a resumed upload passes its id', async () => {
    const qc = new QueryClient();
    startUpload(qc, picked('ride'));
    calls[0].opts.onStaged?.('u1');
    abortUpload();
    expect(storage.has(SESSION)).toBe(false);
    startUpload(qc, picked('ride'), 'u7');
    expect(calls[1].opts.resumeId).toBe('u7');
  });

  const answer = (body: unknown, status = 200) => fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(body), { status }));

  it('after a reload the unfinished upload comes back with what the server holds', async () => {
    storage.set(SESSION, JSON.stringify(pending()));
    answer({ state: 'receiving', bytes_received: 2 });
    await restorePending();
    expect(useUploadStore()).toMatchObject({ pending: { uploadId: 'u9', name: 'ride' }, pendingReceived: 2 });
    expect(String(fetchMock.mock.calls[0][0])).toBe('/api/uploads/u9');

    discardPending(); // «Удалить»: forgotten here and removed on the server
    expect(useUploadStore().pending).toBeNull();
    expect(storage.has(SESSION)).toBe(false);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/uploads/u9');
    expect(fetchMock.mock.calls[1][1].method).toBe('DELETE');
  });

  it('an expired one is dropped; one finished meanwhile hands its recording over', async () => {
    storage.set(SESSION, JSON.stringify(pending()));
    answer({ detail: 'Загрузка не найдена' }, 404);
    await restorePending();
    expect(useUploadStore().pending).toBeNull();
    expect(storage.has(SESSION)).toBe(false);

    storage.set(SESSION, JSON.stringify(pending()));
    answer({ state: 'done', bytes_received: 3, recording: rec('r5') });
    await restorePending();
    expect(useUploadStore().pending).toBeNull();
    expect(takeUploadResult()).toEqual(rec('r5'));
  });

  it('other files replace the unfinished upload; the same ones resume it', async () => {
    const qc = new QueryClient();
    storage.set(SESSION, JSON.stringify(pending()));
    answer({ state: 'receiving', bytes_received: 2 });
    await restorePending();
    startUpload(qc, picked('ride'), 'u9'); // resumed: kept on the server
    expect(calls[0].opts.resumeId).toBe('u9');
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === 'DELETE')).toBe(false);
    abortUpload();

    storage.set(SESSION, JSON.stringify(pending()));
    answer({ state: 'receiving', bytes_received: 2 });
    await restorePending();
    startUpload(qc, picked('other')); // confirmed in the page: the old one is removed
    expect(fetchMock.mock.calls.some(([u, i]) => u === '/api/uploads/u9' && i?.method === 'DELETE')).toBe(true);
  });
});
