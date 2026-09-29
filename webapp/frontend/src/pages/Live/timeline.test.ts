import { describe, expect, it } from 'vitest';
import {
  STALE_MS,
  WINDOW_MS,
  buildSlots,
  dataRuns,
  detectionRows,
  fmtLateral,
  fmtSize,
  healthLevel,
  healthRows,
  liveView,
  sampleOf,
  trimSamples,
  type Sample,
  type StatusMessage,
} from './timeline';

const msg = (over: Partial<StatusMessage> = {}): StatusMessage => ({ decision: 'GO', snapshot_kind: 'frame', ...over }) as StatusMessage;
const flat = (s: string) => s.replace(/[  ]/g, ' ');

describe('liveView', () => {
  it('is live only while messages arrive at most 0,5 s apart', () => {
    expect(liveView('idle', null, 0)).toBe('idle');
    expect(liveView('connecting', null, 0)).toBe('connecting');
    expect(liveView('error', 100, 200)).toBe('error');
    expect(liveView('ended', 100, 200)).toBe('ended');
    expect(liveView('open', null, 1000)).toBe('waiting');
    expect(liveView('open', 1000, 1000 + STALE_MS)).toBe('live');
    expect(liveView('open', 1000, 1000 + STALE_MS + 1)).toBe('stale');
    expect(liveView('open', 1000, 1100, true)).toBe('paused');
  });
});

describe('rolling timeline', () => {
  const tenHz = (from: number, n: number, d: Sample['d'] = 'GO', free = 100): Sample[] =>
    Array.from({ length: n }, (_, i) => ({ at: from + i * 100 + 5, d, free: free - i, latency: 20 + i }));

  it('buckets a 10 Hz stream into 0,1 s slots without gaps', () => {
    const now = 10_000;
    const s = tenHz(now - 3000, 30);
    const slots = buildSlots(s, now);
    expect(slots.letters).toHaveLength(WINDOW_MS / 100);
    const filled = slots.letters.filter((l) => l !== null);
    expect(filled.length).toBeGreaterThanOrEqual(29);
    expect(new Set(filled)).toEqual(new Set(['G']));
    expect(slots.letters.slice(0, 200).every((l) => l === null)).toBe(true);
    expect(slots.free.filter((v) => v !== null).at(-1)).toBe(71);
  });

  it('takes the most severe decision of a slot and the smallest free distance', () => {
    const now = 5000;
    const s: Sample[] = [
      { at: 4905, d: 'GO', free: 80, latency: 10 },
      { at: 4950, d: 'STOP', free: 55, latency: 30 },
      { at: 4990, d: 'CAUTION', free: 60, latency: 12 },
    ];
    const slots = buildSlots(s, now);
    expect(slots.letters.at(-1)).toBe('S');
    expect(slots.free.at(-1)).toBe(55);
    expect(slots.latency.at(-1)).toBe(30);
  });

  it('carries a slot over a short receive jitter, latency included (a continuous sparkline)', () => {
    const now = 10_000;
    // received with jitter: two messages in one slot, none in the next
    const s: Sample[] = [
      { at: 9_605, d: 'GO', free: 90, latency: 40 },
      { at: 9_695, d: 'GO', free: 89, latency: 42 },
      { at: 9_895, d: 'GO', free: 88, latency: 41 },
      { at: 9_905, d: 'GO', free: 87, latency: 43 },
    ];
    const slots = buildSlots(s, now);
    const tail = slots.latency.slice(-4);
    expect(tail.every((v) => v !== null)).toBe(true);
    expect(tail).toEqual([42, 42, 41, 43]);
    expect(slots.letters.slice(-4).every((l) => l === 'G')).toBe(true);
  });

  it('leaves a gap longer than 0,5 s empty (no data is not a decision)', () => {
    const now = 20_000;
    const s = [...tenHz(now - 6000, 10), ...tenHz(now - 2000, 10, 'STOP')];
    const runs = dataRuns(buildSlots(s, now).letters);
    expect(runs).toHaveLength(2);
    expect(runs[0].decisions).toMatch(/^G+$/);
    expect(runs[1].decisions).toMatch(/^S+$/);
    expect(runs[1].start - runs[0].end).toBeGreaterThan(STALE_MS / 100);
  });

  it('trims samples older than the window', () => {
    const s = tenHz(0, 400); // 40 s
    const kept = trimSamples(s, 40_000);
    expect(kept[0].at).toBeGreaterThanOrEqual(40_000 - WINDOW_MS - 100);
    expect(kept.at(-1)).toBe(s.at(-1));
    expect(trimSamples(kept, 40_000)).toBe(kept); // nothing to drop: same array
  });

  it('samples the free distance and the node latency (timing total as a fallback)', () => {
    expect(sampleOf(msg({ clear_distance: 120.5, node: { fps: 10, latency_ms: 41, frames: 1, dropped_frames: 0 } }), 7)).toEqual({ at: 7, d: 'GO', free: 120.5, latency: 41 });
    expect(sampleOf(msg({ decision: 'FAULT', timing_ms: { total: 12 } as never }), 8)).toEqual({ at: 8, d: 'FAULT', free: null, latency: 12 });
    // a FAULT frame never plots a monitored distance, even when it carries one
    expect(sampleOf(msg({ decision: 'FAULT', clear_distance: 150 }), 9).free).toBeNull();
  });
});

describe('detections', () => {
  it('lists in-gauge objects and advisory ones, nearest first', () => {
    const rows = detectionRows(
      msg({
        decision: 'STOP',
        detections: [{ id: 3, distance: 55.2, lateral: 0.02, size: [0.4, 0.5, 1.7], confidence: 0.93 }] as never,
        warnings: [{ id: 9, distance: 12.3, lateral: -1.4, size: [0.3, 0.2, 0.4], confidence: 0.5 }] as never,
      }),
    );
    expect(rows.map((r) => [r.zone, r.distance])).toEqual([
      ['warning', 12.3],
      ['gauge', 55.2],
    ]);
    expect(rows[1].key).toBe('gauge-3');
    expect(detectionRows(null)).toEqual([]);
    expect(detectionRows(msg())).toEqual([]);
  });

  it('formats the lateral offset and the size in Russian', () => {
    expect(fmtLateral(0.02)).toBe('по оси');
    expect(flat(fmtLateral(0.34))).toBe('0,3 м влево');
    expect(flat(fmtLateral(-1.25))).toBe('1,3 м вправо');
    expect(fmtSize([0.44, 0.5, 1.71])).toBe('0,4 × 0,5 × 1,7 м');
  });
});

describe('health lamps', () => {
  const m = msg({ health: { level: 'warn', visibility: 42, rail_lock: 0.9 } as never, mount: { status: 'ok' } as never });

  it('lights the lamps from the frame while the data is fresh', () => {
    const rows = healthRows(m, true, 60);
    expect(rows.map((r) => [r.key, r.lamp])).toEqual([
      ['visibility', 'warn'],
      ['rails', 'ok'],
      ['calibration', 'ok'],
    ]);
    expect(flat(rows[0].value)).toBe('42 м');
    expect(healthLevel(m)).toBe('warn');
  });

  it('turns every lamp off when the data is stale — never an old green', () => {
    expect(healthRows(m, false, 60).every((r) => r.lamp === 'off')).toBe(true);
  });

  it('maps the mount calibration states and handles missing data', () => {
    expect(healthRows(msg({ mount: { status: 'pending' } as never }), true)[2]).toMatchObject({ lamp: 'wait', value: 'ожидание' });
    expect(healthRows(msg({ mount: { status: 'fallback' } as never }), true)[2].lamp).toBe('warn');
    expect(healthRows(null, true).map((r) => r.lamp)).toEqual(['off', 'off', 'off']);
    expect(healthLevel(null)).toBeNull();
  });
});
