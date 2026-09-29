import { describe, expect, it, vi } from 'vitest';
import { CHUNK, FrameStore, type FramesChunk } from './frameStore';

const flush = () => new Promise((r) => setTimeout(r, 0));

function fakeBackend(total: number) {
  const calls: [number, number][] = [];
  let fail = false;
  const fetcher = vi.fn(async (from: number, count: number): Promise<FramesChunk<{ pos: number }>> => {
    calls.push([from, count]);
    if (fail) throw new Error('503');
    const n = Math.max(0, Math.min(count, total - from));
    return { from, total, frames: Array.from({ length: n }, (_, i) => ({ pos: from + i })) };
  });
  return {
    fetcher,
    calls,
    setFail: (v: boolean) => {
      fail = v;
    },
  };
}

describe('FrameStore', () => {
  it('fetches the chunk of a position once and serves its frames', async () => {
    const b = fakeBackend(250);
    const onChange = vi.fn();
    const s = new FrameStore(b.fetcher, 250, { onChange });
    s.ensure(120);
    s.ensure(150);
    expect(b.calls).toEqual([[100, CHUNK]]);
    expect(s.loading(120)).toBe(true);
    await flush();
    expect(s.get(120)).toEqual({ pos: 120 });
    expect(s.has(199)).toBe(true);
    expect(s.has(200)).toBe(false);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('asks only for what exists in the last chunk', async () => {
    const b = fakeBackend(250);
    const s = new FrameStore(b.fetcher, 250);
    s.ensure(249);
    expect(b.calls).toEqual([[200, 50]]);
    await flush();
    expect(s.get(249)).toEqual({ pos: 249 });
    expect(s.get(250)).toBeUndefined();
    expect(s.get(-1)).toBeUndefined();
  });

  it('prefetches the next chunk in the second half and the previous one near a chunk start', () => {
    const b = fakeBackend(1000);
    const s = new FrameStore(b.fetcher, 1000);
    s.ensureAround(160);
    expect(b.calls).toEqual([
      [100, 100],
      [200, 100],
    ]);
    b.calls.length = 0;
    s.ensureAround(403);
    expect(b.calls).toEqual([
      [400, 100],
      [300, 100],
    ]);
  });

  it('remembers a failure for a moment; retry() forgets it', async () => {
    let now = 0;
    const b = fakeBackend(100);
    b.setFail(true);
    const s = new FrameStore(b.fetcher, 100, { retryMs: 3000, now: () => now });
    s.ensure(5);
    await flush();
    expect(s.lastError).toBeInstanceOf(Error);
    s.ensure(5);
    expect(b.calls).toHaveLength(1);
    now = 4000;
    s.ensure(5);
    expect(b.calls).toHaveLength(2);
    await flush();
    b.setFail(false);
    s.retry();
    expect(s.lastError).toBeNull();
    s.ensure(5);
    await flush();
    expect(s.get(5)).toEqual({ pos: 5 });
    expect(b.calls).toHaveLength(3);
  });

  it('ignores answers after dispose', async () => {
    const b = fakeBackend(100);
    const onChange = vi.fn();
    const s = new FrameStore(b.fetcher, 100, { onChange });
    s.ensure(0);
    s.dispose();
    await flush();
    expect(onChange).not.toHaveBeenCalled();
    expect(s.get(0)).toBeUndefined();
    s.ensure(0);
    expect(b.calls).toHaveLength(1);
  });
});
