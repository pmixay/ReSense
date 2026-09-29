import { describe, expect, it } from 'vitest';
import type { DetectionDict } from '../api/types';
import { MAX_SPEED_MPS, cloudAtOrBefore, cloudIndex, cloudsAhead, frameDt, frameMotion, prefetchStride } from './motion';

const obj = (id: number, x: number, y = 1.8): DetectionDict => ({ id, center: [x, y, 0], size: [0.5, 0.5, 1] }) as DetectionDict;

describe('frameMotion', () => {
  it('uses the given ego speed first', () => {
    expect(frameMotion({ ego_speed: 12.5, ego_speed_source: 'given' }, null, 0.1)).toEqual({ v: 12.5, source: 'given' });
    expect(frameMotion({ ego_speed: -3 }, null, 0.1).v).toBe(0);
    expect(frameMotion({ ego_speed: 500 }, null, 0.1).v).toBe(MAX_SPEED_MPS);
  });

  it('uses the detector estimate only when confident', () => {
    expect(frameMotion({ ego_speed_estimate: 8, ego_speed_confidence: 0.9 }, null, 0.1)).toEqual({ v: 8, source: 'estimated' });
    expect(frameMotion({ ego_speed_estimate: 8, ego_speed_confidence: 0.2 }, null, 0.1)).toEqual({ v: 0, source: null });
  });

  it('falls back to the shift of objects tracked in both frames (median, standing still sideways)', () => {
    const cur = { detections: [obj(1, 50), obj(2, 30)], warnings: [obj(3, 20)] };
    const next = { detections: [obj(1, 49.2), obj(2, 29.25)], warnings: [obj(3, 19.2)] };
    const m = frameMotion(cur, next, 0.1);
    expect(m.source).toBe('tracked');
    expect(m.v).toBeCloseTo(8, 5);
  });

  it('ignores objects that walk sideways or jump implausibly', () => {
    const cur = { detections: [obj(1, 50, 0), obj(2, 30)] };
    const next = { detections: [obj(1, 49, 1), obj(2, 20)] };
    expect(frameMotion(cur, next, 0.1)).toEqual({ v: 0, source: null });
  });

  it('is unknown without data', () => {
    expect(frameMotion(null, null, 0.1)).toEqual({ v: 0, source: null });
    expect(frameMotion({ detections: [obj(1, 5)] }, null, 0.1).source).toBeNull();
    expect(frameMotion({ detections: [obj(1, 5)] }, { detections: [obj(1, 4)] }, 0).source).toBeNull();
  });
});

describe('frameDt', () => {
  it('reads the recording timing and clamps it', () => {
    const t = [0, 0.1, 0.25, 0.25, 5];
    expect(frameDt(t, 0)).toBeCloseTo(0.1);
    expect(frameDt(t, 1)).toBeCloseTo(0.15);
    expect(frameDt(t, 2)).toBe(0.1); // zero gap: fallback
    expect(frameDt(t, 3)).toBe(1); // clamped
    expect(frameDt(t, 4)).toBe(0.1); // no next frame
    expect(frameDt(null, 0)).toBe(0.1);
  });
});

describe('stored clouds of a run', () => {
  const clouds = [0, 5, 10, 15, 20];

  it('picks the stored cloud at or before a position', () => {
    expect(cloudAtOrBefore(clouds, 0)).toBe(0);
    expect(cloudAtOrBefore(clouds, 7)).toBe(5);
    expect(cloudAtOrBefore(clouds, 20)).toBe(20);
    expect(cloudAtOrBefore(clouds, 99)).toBe(20);
    expect(cloudAtOrBefore([3, 6], 1)).toBeNull();
    expect(cloudAtOrBefore([], 1)).toBeNull();
    expect(cloudAtOrBefore(null, 1)).toBeNull();
  });

  it('finds the index of a stored cloud', () => {
    expect(cloudIndex(clouds, 10)).toBe(2);
    expect(cloudIndex(clouds, 11)).toBe(-1);
  });

  it('lists the clouds ahead of the playhead with a stride', () => {
    expect(cloudsAhead(clouds, 0, 2)).toEqual([5, 10]);
    expect(cloudsAhead(clouds, 7, 10)).toEqual([10, 15, 20]);
    expect(cloudsAhead(clouds, 0, 10, 2)).toEqual([5, 15]);
    expect(cloudsAhead([3, 6], 1, 5)).toEqual([3, 6]);
    expect(cloudsAhead(clouds, 20, 5)).toEqual([]);
    expect(cloudsAhead(clouds, 0, 0)).toEqual([]);
  });

  it('thins the prefetch at high speeds', () => {
    expect(prefetchStride(1)).toBe(1);
    expect(prefetchStride(2)).toBe(1);
    expect(prefetchStride(5)).toBe(2);
    expect(prefetchStride(10)).toBe(3);
  });
});
