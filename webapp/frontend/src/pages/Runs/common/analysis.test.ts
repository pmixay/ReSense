import { describe, expect, it } from 'vitest';
import type { Episode, EvalSummary, ParamSpec, Run } from '../../../api/types';
import {
  bestIndices,
  compareUrl,
  computeMisses,
  describeEvent,
  detectionDelay,
  diffOverrides,
  evalVerdict,
  filterRuns,
  fmtParam,
  nearestIndex,
  niceDomain,
  niceTicks,
  parseRunIds,
  playerUrl,
  posOfFrame,
  spansText,
  stopGaps,
} from './analysis';

const ev = (over: Partial<EvalSummary> = {}): EvalSummary => ({
  labels_name: 'gt',
  frames_labelled: 100,
  frames_with_object_in_gauge: 24,
  frames_detected: 20,
  recall: 20 / 24,
  false_stop_frames: 0,
  false_stop_episodes: 0,
  first_detection_distance: 55.3,
  raw: {},
  ...over,
});

const run = (id: string, over: Partial<Run['summary']> = {}, rest: Partial<Run> = {}): Run => ({
  id,
  name: id,
  recording_id: 'rec',
  job_id: null,
  preset: { id: 'standard', name: 'Стандарт 1.0' },
  created_at: '2026-09-29T10:00:00Z',
  has_clouds: true,
  cloud_frames: 10,
  source_kind: 'rosbag2',
  summary: {
    n_frames: 10,
    duration_s: 0.9,
    counts: { GO: 10, CAUTION: 0, STOP: 0, FAULT: 0 },
    decisions: 'GGGGGGGGGG',
    stop_episodes: 0,
    first_stop: null,
    distance_min: null,
    distance_max: null,
    latency_ms: { p50: 20, p95: 30, max: 40 },
    processing_fps: 20,
    clear_distance_median: 180,
    visibility_median: 180,
    eval: null,
    ...over,
  },
  ...rest,
});

/** the formatters put a no-break space before units */
const sp = (s: string) => s.replace(/\u00a0/g, ' ');

describe('links', () => {
  it('builds player and compare urls', () => {
    expect(playerUrl('ab c')).toBe('/player/ab%20c');
    expect(playerUrl('r1', 44)).toBe('/player/r1?pos=44');
    expect(playerUrl('r1', null)).toBe('/player/r1');
    expect(compareUrl(['a', 'b', 'c', 'd', 'e'])).toBe('/compare?runs=a,b,c,d');
    expect(compareUrl([])).toBe('/compare');
  });

  it('parses the selection of /compare', () => {
    expect(parseRunIds(new URLSearchParams('runs=a,b,,a,c'))).toEqual(['a', 'b', 'c']);
    expect(parseRunIds(new URLSearchParams('a=x&b=y'))).toEqual(['x', 'y']);
    expect(parseRunIds(new URLSearchParams('runs=1,2,3,4,5'))).toEqual(['1', '2', '3', '4']);
    expect(parseRunIds(new URLSearchParams(''))).toEqual([]);
  });
});

describe('positions', () => {
  it('maps bag frames to processed positions', () => {
    expect(posOfFrame([10, 12, 14, 16], 14)).toBe(2);
    expect(posOfFrame([10, 12, 14, 16], 13)).toBe(2);
    expect(posOfFrame(undefined, 7)).toBe(7);
  });
  it('finds the nearest time sample', () => {
    const t = [0, 0.1, 0.2, 0.3];
    expect(nearestIndex(t, 0.14)).toBe(1);
    expect(nearestIndex(t, 0.16)).toBe(2);
    expect(nearestIndex(t, -1)).toBe(0);
    expect(nearestIndex(t, 9)).toBe(3);
    expect(nearestIndex([], 1)).toBe(-1);
  });
});

describe('misses', () => {
  it('counts GO / CAUTION gaps inside a STOP without labels', () => {
    expect(stopGaps('GGSSGCSSG')).toEqual([{ start: 4, end: 6 }]);
    expect(stopGaps('GGGG')).toEqual([]);
    const m = computeMisses('GGSSGCSSGS');
    expect(m).toEqual({ basis: 'gaps', count: 3, spans: [{ start: 4, end: 6 }, { start: 8, end: 9 }], beforeDetection: 0 });
  });

  it('counts labelled in-gauge frames without STOP, splitting the confirmation delay', () => {
    const labels = [false, true, true, true, true, true, false, true, true, false];
    const m = computeMisses('GCCSSGSGGG', labels);
    expect(m.basis).toBe('labels');
    expect(m.count).toBe(5); // 1, 2 (delay), 5 (dropout), 7, 8 (never detected)
    expect(m.beforeDetection).toBe(2);
    expect(sp(spansText(m.spans))).toBe('3 участка');
    expect(detectionDelay('GCCSSGSGGG', labels)).toBe(2);
    expect(detectionDelay('GGG', labels)).toBeNull();
    expect(detectionDelay('SSS', null)).toBeNull();
  });

  it('writes spans with bag frame numbers', () => {
    expect(spansText([{ start: 4, end: 5 }], (p) => p * 2)).toBe('кадр 8');
    expect(spansText([{ start: 4, end: 7 }])).toBe('кадры 4–6');
    expect(spansText([{ start: 1, end: 2 }, { start: 4, end: 7 }])).toBe('кадры 1, 4–6');
    expect(spansText([])).toBe('');
  });
});

describe('events and verdicts', () => {
  const ep = (over: Partial<Episode>): Episode => ({
    decision: 'STOP',
    first_frame: 44,
    last_frame: 66,
    t0: 4.4,
    t1: 6.6,
    n_frames: 23,
    distance_min: 55.22,
    distance_max: 55.25,
    ...over,
  });
  it('describes events', () => {
    const stop = describeEvent(ep({}));
    expect(stop).toMatchObject({ title: 'СТОП', value: { num: '55,2', unit: 'м' } });
    expect(sp(stop.meta)).toBe('кадры 44–66 · 4,4 с');
    expect(describeEvent(ep({}), { lastFrame: 66 }).title).toBe('СТОП до конца записи');
    const gap = describeEvent(ep({ decision: 'GO', first_frame: 111, last_frame: 111, t0: 11.1, n_frames: 1, distance_min: null }), { labelled: true });
    expect(gap).toMatchObject({ gap: true, title: 'Ложное «свободно»', value: { num: '1', unit: 'кадр' } });
    expect(sp(gap.meta)).toBe('кадр 111 · 11,1 с');
    expect(describeEvent(ep({ decision: 'CAUTION', n_frames: 3, distance_min: null })).value).toEqual({ num: '3', unit: 'кадра' });
    expect(describeEvent(ep({ decision: 'FAULT' })).title).toBe('Ошибка датчика');
  });

  it('summarises the verdict against labels', () => {
    expect(evalVerdict(null)).toEqual({ tone: 'none', label: 'нет разметки' });
    expect(evalVerdict(ev())).toEqual({ tone: 'ok', label: 'верно · 20 / 24' });
    expect(evalVerdict(ev({ frames_detected: 24 }))).toEqual({ tone: 'ok', label: 'верно' });
    expect(evalVerdict(ev({ false_stop_episodes: 2 }))).toEqual({ tone: 'false', label: 'ложный СТОП ×2' });
    expect(evalVerdict(ev({ frames_with_object_in_gauge: 0, frames_detected: 0, recall: null }))).toEqual({ tone: 'ok', label: '0 ложных' });
  });
});

describe('the runs list', () => {
  const runs = [
    run('b', { counts: { GO: 5, CAUTION: 0, STOP: 5, FAULT: 0 }, n_frames: 50 }, { created_at: '2026-09-29T09:00:00Z', name: 'Бета' }),
    run('a', { eval: ev(), n_frames: 20 }, { created_at: '2026-09-29T11:00:00Z', name: 'альфа', source_kind: 'jsonl' }),
    run('c', {}, { created_at: '2026-09-29T10:00:00Z', name: 'Гамма', preset: { id: 'p', name: 'Быстрый' } }),
  ];
  const base = { q: '', filter: 'all', kind: 'all', sort: 'date' } as const;
  it('filters and sorts', () => {
    expect(filterRuns(runs, base).map((r) => r.id)).toEqual(['a', 'c', 'b']);
    expect(filterRuns(runs, { ...base, sort: 'name' }).map((r) => r.id)).toEqual(['a', 'b', 'c']);
    expect(filterRuns(runs, { ...base, sort: 'frames' }).map((r) => r.id)).toEqual(['b', 'a', 'c']);
    expect(filterRuns(runs, { ...base, filter: 'stop' }).map((r) => r.id)).toEqual(['b']);
    expect(filterRuns(runs, { ...base, filter: 'nostop' }).map((r) => r.id)).toEqual(['a', 'c']);
    expect(filterRuns(runs, { ...base, filter: 'labels' }).map((r) => r.id)).toEqual(['a']);
    expect(filterRuns(runs, { ...base, kind: 'jsonl' }).map((r) => r.id)).toEqual(['a']);
    expect(filterRuns(runs, { ...base, q: 'АЛЬ' }).map((r) => r.id)).toEqual(['a']);
    expect(filterRuns(runs, { ...base, q: 'быстр' }).map((r) => r.id)).toEqual(['c']);
  });
});

describe('comparison', () => {
  it('marks the best values of a row', () => {
    expect([...bestIndices([1, 3, 3, null], 'max')]).toEqual([1, 2]);
    expect([...bestIndices([5, 2, 9], 'min')]).toEqual([1]);
    expect([...bestIndices([2, 2], 'min')]).toEqual([]);
    expect([...bestIndices([2, null], 'min')]).toEqual([]);
    expect([...bestIndices([1, 2], null)]).toEqual([]);
  });

  it('diffs preset overrides against the schema defaults', () => {
    const schema: ParamSpec[] = [
      { key: 'tracking.confirm_time_s', group: 'Трекинг', label: 'Время подтверждения', help: '', type: 'float', default: 0.5, unit: 'с' },
      { key: 'lowobj.enabled', group: 'Низкие', label: 'Низкие предметы', help: '', type: 'bool', default: true },
      { key: 'cluster.eps', group: 'Кластеризация', label: 'Радиус', help: '', type: 'float', default: 0.35, unit: 'м' },
    ];
    const d = diffOverrides([{}, { 'tracking.confirm_time_s': 0.2, 'lowobj.enabled': false, 'cluster.eps': 0.35 }], schema);
    expect(d.map((x) => [x.key, x.values])).toEqual([
      ['tracking.confirm_time_s', [0.5, 0.2]],
      ['lowobj.enabled', [true, false]],
    ]);
    expect(diffOverrides([{}, {}], schema)).toEqual([]);
    expect(fmtParam(0.2, 'с')).toBe('0,2 с');
    expect(fmtParam(150, 'м')).toBe('150 м');
    expect(fmtParam(false)).toBe('нет');
    expect(fmtParam(0.125)).toBe('0,125');
  });
});

describe('chart scales', () => {
  it('makes nice ticks and domains', () => {
    expect(niceTicks(0, 10, 6)).toEqual([0, 2, 4, 6, 8, 10]);
    expect(niceTicks(54.5, 57.5, 7)).toEqual([54.5, 55, 55.5, 56, 56.5, 57, 57.5]);
    const [lo, hi] = niceDomain([55.22, 55.25, null, 55.67]) ?? [0, 0];
    expect(lo).toBeLessThanOrEqual(55.2);
    expect(hi).toBeGreaterThanOrEqual(55.7);
    expect(niceDomain([null, undefined])).toBeNull();
    expect((niceDomain([1, 180]) ?? [-1])[0]).toBe(0); // distances never go negative
  });
});
