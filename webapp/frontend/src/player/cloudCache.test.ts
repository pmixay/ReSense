import { describe, expect, it, vi } from 'vitest';
import { CloudCache, LruCache, PRIO_AHEAD, PRIO_NOW } from './cloudCache';

/** A fetcher whose requests resolve / fail when the test says so. */
function controlled<T>() {
  const pending = new Map<number, { resolve: (v: T) => void; reject: (e: unknown) => void; signal: AbortSignal }>();
  const calls: number[] = [];
  const fetcher = (pos: number, signal: AbortSignal) =>
    new Promise<T>((resolve, reject) => {
      calls.push(pos);
      pending.set(pos, { resolve, reject, signal });
    });
  return { fetcher, pending, calls };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe('LruCache', () => {
  it('evicts the least recently used entry', () => {
    const c = new LruCache<number, string>(3);
    c.set(1, 'a');
    c.set(2, 'b');
    c.set(3, 'c');
    expect(c.get(1)).toBe('a'); // 1 is now the newest
    c.set(4, 'd');
    expect(c.has(2)).toBe(false);
    expect([...c.keys()]).toEqual([3, 1, 4]);
    expect(c.size).toBe(3);
  });

  it('peek does not touch the order; set of an existing key refreshes it', () => {
    const c = new LruCache<number, string>(2);
    c.set(1, 'a');
    c.set(2, 'b');
    expect(c.peek(1)).toBe('a');
    c.set(3, 'c');
    expect(c.has(1)).toBe(false);
    c.set(2, 'B');
    c.set(4, 'd');
    expect(c.get(2)).toBe('B');
    expect(c.has(3)).toBe(false);
  });
});

describe('CloudCache', () => {
  it('deduplicates requests and caches the result', async () => {
    const f = controlled<string>();
    const onChange = vi.fn();
    const cc = new CloudCache(f.fetcher, { onChange });
    cc.request(5);
    cc.request(5);
    expect(f.calls).toEqual([5]);
    expect(cc.status(5)).toBe('loading');
    f.pending.get(5)!.resolve('five');
    await flush();
    expect(cc.get(5)).toBe('five');
    expect(cc.status(5)).toBe('loaded');
    expect(onChange).toHaveBeenCalledWith(5);
    cc.request(5);
    expect(f.calls).toEqual([5]);
  });

  it('runs at most `concurrency` requests, the most urgent first', async () => {
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher, { concurrency: 2 });
    cc.prefetch([10, 11, 12, 13]);
    expect(f.calls).toEqual([10, 11]);
    expect(cc.status(12)).toBe('queued');
    cc.request(20, PRIO_NOW); // the cloud under the playhead jumps the prefetch queue
    f.pending.get(10)!.resolve(10);
    await flush();
    expect(f.calls).toEqual([10, 11, 20]);
    f.pending.get(11)!.resolve(11);
    await flush();
    expect(f.calls).toEqual([10, 11, 20, 12]);
    expect(cc.pending).toBe(3); // 20, 12 in flight + 13 queued
  });

  it('keeps the prefetch order among equal priorities', async () => {
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher, { concurrency: 1 });
    cc.request(1, PRIO_NOW);
    cc.prefetch([7, 3, 9], PRIO_AHEAD);
    for (const p of [1, 7, 3]) {
      f.pending.get(p)!.resolve(p);
      await flush();
    }
    expect(f.calls).toEqual([1, 7, 3, 9]);
  });

  it('drops queued prefetches after a seek and aborts in-flight ones on request', async () => {
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher, { concurrency: 1 });
    cc.prefetch([1, 2, 3, 50, 51]);
    cc.cancelQueued((p) => p >= 50);
    expect(cc.status(2)).toBe('idle');
    expect(cc.status(50)).toBe('queued');
    cc.abortInflight(() => false);
    expect(f.pending.get(1)!.signal.aborted).toBe(true);
    expect(f.calls).toEqual([1, 50]);
    // a late answer of the aborted request is ignored
    f.pending.get(1)!.resolve(1);
    await flush();
    expect(cc.get(1)).toBeUndefined();
  });

  it('remembers a failure for a while instead of hammering the backend', async () => {
    let now = 1000;
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher, { retryMs: 5000, now: () => now });
    cc.request(3);
    f.pending.get(3)!.reject(new Error('404 нет облака'));
    await flush();
    expect(cc.status(3)).toBe('failed');
    expect(cc.error(3)).toBe('404 нет облака');
    cc.request(3);
    expect(f.calls).toEqual([3]);
    now += 6000;
    expect(cc.error(3)).toBeNull();
    cc.request(3);
    expect(f.calls).toEqual([3, 3]);
  });

  it('keeps ~capacity clouds (LRU) and finds the newest one at or before a position', async () => {
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher, { capacity: 3, concurrency: 10 });
    for (const p of [2, 4, 6, 8]) cc.request(p);
    for (const p of [2, 4, 6, 8]) f.pending.get(p)!.resolve(p);
    await flush();
    expect(cc.cache.size).toBe(3);
    expect(cc.status(2)).toBe('idle'); // evicted
    expect(cc.latestAtOrBefore(7)).toBe(6);
    expect(cc.latestAtOrBefore(100)).toBe(8);
    expect(cc.latestAtOrBefore(3)).toBeNull();
  });

  it('aborts everything on dispose and ignores later requests', async () => {
    const f = controlled<number>();
    const cc = new CloudCache(f.fetcher);
    cc.request(1);
    cc.dispose();
    expect(f.pending.get(1)!.signal.aborted).toBe(true);
    cc.request(2);
    expect(f.calls).toEqual([1]);
  });
});
