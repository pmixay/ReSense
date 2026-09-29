import { describe, expect, it } from 'vitest';
import type { EvalSummary, Run, RunSummary } from '../../api/types';
import { falseStops, firstStopPos, latencyHistogram, latestFirstStop, latestWithObject, playerRun } from './kpis';

const run = (id: string, s: Partial<RunSummary> = {}, r: Partial<Run> = {}): Run =>
  ({
    id,
    name: id,
    has_clouds: false,
    cloud_frames: 0,
    summary: { decisions: '', stop_episodes: 0, first_stop: null, eval: null, ...s } as RunSummary,
    ...r,
  }) as Run;
const ev = (e: Partial<EvalSummary>): EvalSummary =>
  ({ frames_with_object_in_gauge: 0, frames_detected: 0, false_stop_episodes: 0, raw: {}, ...e }) as EvalSummary;

describe('latencyHistogram', () => {
  it('bins the latencies and finds the p95 bin', () => {
    const lat = [10, 12, 14, 20, 30, 50];
    const h = latencyHistogram(lat, 45, 5);
    expect(h.max).toBe(50);
    expect(h.counts).toEqual([0, 3, 1, 1, 1]); // bins of 10 ms from 0
    expect(h.p95Bin).toBe(4);
    expect(latencyHistogram([], 20, 4).counts).toEqual([0, 0, 0, 0]);
  });
});

describe('latest runs for the tiles (newest first)', () => {
  const runs = [
    run('a', { eval: ev({}) }),
    run('b', { eval: ev({ frames_with_object_in_gauge: 5, frames_detected: 4 }), first_stop: { frame: 3, t: 0.3, distance: null } }),
    run('c', { first_stop: { frame: 8, t: 0.8, distance: 55.6 } }),
  ];
  it('pick the newest run that has the data', () => {
    expect(latestWithObject(runs)?.id).toBe('b');
    expect(latestFirstStop(runs)?.id).toBe('c');
    expect(latestWithObject(undefined)).toBeUndefined();
  });
});

describe('falseStops', () => {
  it('averages over the scored runs, oldest first on the line', () => {
    const fs = falseStops([run('new', { eval: ev({ false_stop_episodes: 2 }) }), run('none'), run('old', { eval: ev({ false_stop_episodes: 1 }) })]);
    expect(fs).toMatchObject({ total: 3, scored: 2, perRun: 1.5, perKm: null });
    expect(fs?.runs.map((r) => r.id)).toEqual(['old', 'new']);
    expect(falseStops([run('x')])).toBeNull();
  });
  it('per km when every scored run knows its distance', () => {
    const fs = falseStops([
      run('a', { eval: ev({ false_stop_episodes: 3, raw: { distance_km: 1 } }) }),
      run('b', { eval: ev({ false_stop_episodes: 1, raw: { distance_km: 3 } }) }),
    ]);
    expect(fs?.perKm).toBe(1);
  });
});

describe('player card', () => {
  it('prefers the newest run with clouds and a STOP, at its first STOP', () => {
    const runs = [
      run('noclouds', { first_stop: { frame: 1, t: 0, distance: 3 } }),
      run('clear', {}, { has_clouds: true, cloud_frames: 10 }),
      run('stop', { first_stop: { frame: 4, t: 0.4, distance: 100 } }, { has_clouds: true, cloud_frames: 10 }),
    ];
    expect(playerRun(runs)?.id).toBe('stop');
    expect(playerRun(runs.slice(0, 2))?.id).toBe('clear');
    expect(playerRun([runs[0]])).toBeUndefined();
    expect(firstStopPos('GGCSSG')).toBe(3);
    expect(firstStopPos('GGG')).toBe(0);
  });
});
