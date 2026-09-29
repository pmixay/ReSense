import { QueryClient } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recording } from '../../api/types';
import type { UploadOptions, UploadProgress } from '../../api/upload';
import { guessKind } from './kinds';
import { abortUpload, dismissUpload, startUpload, takeUploadResult, useUploadStore, type Picked } from './uploadStore';

// uploadRecording answered by hand: each call is recorded with its options and its promise controls
const calls: { opts: UploadOptions; resolve: (r: Recording) => void; reject: (e: unknown) => void; abort: ReturnType<typeof vi.fn> }[] = [];
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
      opts.onProgress?.({ phase: 'staging', loaded: 0, total: 10, fraction: 0, fileIndex: 0, fileCount: 1, currentPath: 'a.jsonl', bytesPerSec: null, etaS: null });
      calls.push({ opts, resolve, reject, abort });
      return { promise, abort };
    },
  };
});

// the hook reads the store with useSyncExternalStore; outside React its snapshot is enough here
vi.mock('react', async (orig) => ({ ...(await orig<typeof import('react')>()), useSyncExternalStore: (_s: unknown, get: () => unknown) => get() }));

const picked = (name: string): Picked => ({ items: [{ file: new File(['x'], `${name}.jsonl`), path: `${name}.jsonl` }], guess: guessKind([`${name}.jsonl`]), name, bytes: 1 });
const rec = (id: string) => ({ id, name: id }) as Recording;
const progress = (fraction: number): UploadProgress => ({ phase: 'uploading', loaded: fraction * 10, total: 10, fraction, fileIndex: 0, fileCount: 1, currentPath: 'a', bytesPerSec: 5, etaS: 1 });
const settle = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  calls.length = 0;
  abortUpload();
  takeUploadResult();
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
