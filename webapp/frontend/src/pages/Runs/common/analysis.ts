// Pure helpers of the analysis pages (Прогоны, Прогон, Сравнение): positions ↔ bag frames, misses,
// events, the verdict against labels, list filtering, comparison metrics and chart ticks.
import type { Decision, Episode, EvalSummary, ParamSpec, ParamValue, Run, RecordingKind } from '../../../api/types';
import { fmtCount, fmtDuration, fmtFps, fmtMeters, fmtMs, fmtNum, fmtPercent, plural, FRAMES, EPISODES } from '../../../lib/format';

// ---------------------------------------------------------------- links

/** The fullscreen player of a run, optionally at a processed-order position (`?pos=`). */
export function playerUrl(runId: string, pos?: number | null): string {
  const base = `/player/${encodeURIComponent(runId)}`;
  return pos !== null && pos !== undefined && pos >= 0 ? `${base}?pos=${Math.round(pos)}` : base;
}

export const runUrl = (runId: string): string => `/runs/${encodeURIComponent(runId)}`;

export const MAX_COMPARE = 4;

export const compareUrl = (ids: readonly string[]): string =>
  ids.length ? `/compare?runs=${ids.slice(0, MAX_COMPARE).map(encodeURIComponent).join(',')}` : '/compare';

/** Run ids of a /compare URL: `?runs=a,b,c` (also the legacy `?a=&b=`), unique, at most 4. */
export function parseRunIds(params: URLSearchParams): string[] {
  const raw = [...(params.get('runs') ?? '').split(','), params.get('a') ?? '', params.get('b') ?? ''];
  const out: string[] = [];
  for (const r of raw) {
    const id = r.trim();
    if (id && !out.includes(id)) out.push(id);
  }
  return out.slice(0, MAX_COMPARE);
}

// ---------------------------------------------------------------- positions

/** Processed-order position of a bag frame index (frames increase); the frame itself without a map. */
export function posOfFrame(frames: readonly number[] | null | undefined, frame: number): number {
  if (!frames || frames.length === 0) return Math.max(0, frame);
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid] < frame) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** Index of the sample nearest to `t` in an increasing time array (-1 when empty). */
export function nearestIndex(t: readonly number[], x: number): number {
  const n = t.length;
  if (n === 0) return -1;
  if (x <= t[0]) return 0;
  if (x >= t[n - 1]) return n - 1;
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (t[mid] <= x) lo = mid;
    else hi = mid;
  }
  return x - t[lo] <= t[hi] - x ? lo : hi;
}

/** Frames per second of the recording as processed: (n − 1) / duration. */
export function frameRate(nFrames: number, durationS: number): number | null {
  return nFrames > 1 && durationS > 0 ? (nFrames - 1) / durationS : null;
}

// ---------------------------------------------------------------- misses

export interface Span {
  start: number; // position, inclusive
  end: number; // position, exclusive
}

const spanLen = (s: Span) => s.end - s.start;

/** Maximal runs of true in a boolean predicate over 0..n−1. */
function spansWhere(n: number, pred: (i: number) => boolean): Span[] {
  const out: Span[] = [];
  let i = 0;
  while (i < n) {
    if (!pred(i)) {
      i += 1;
      continue;
    }
    let j = i + 1;
    while (j < n && pred(j)) j += 1;
    out.push({ start: i, end: j });
    i = j;
  }
  return out;
}

/** Non-STOP stretches with a STOP frame on both sides (dropouts inside a STOP). */
export function stopGaps(decisions: string): Span[] {
  const first = decisions.indexOf('S');
  const last = decisions.lastIndexOf('S');
  if (first < 0 || first === last) return [];
  return spansWhere(last + 1, (i) => i > first && decisions[i] !== 'S');
}

export interface Misses {
  /** 'labels': labelled in-gauge frames without STOP; 'gaps': GO / CAUTION frames inside a STOP */
  basis: 'labels' | 'gaps';
  count: number;
  spans: Span[];
  /** of `count`, the frames before the first STOP of their labelled stretch (confirmation time) */
  beforeDetection: number;
}

export function computeMisses(decisions: string, labelsInGauge?: readonly boolean[] | null): Misses {
  const n = decisions.length;
  if (labelsInGauge && labelsInGauge.length) {
    const m = Math.min(n, labelsInGauge.length);
    const spans = spansWhere(m, (i) => !!labelsInGauge[i] && decisions[i] !== 'S');
    let before = 0;
    // a labelled stretch: frames before its first STOP are the confirmation delay
    for (const seg of spansWhere(m, (i) => !!labelsInGauge[i])) {
      let k = seg.start;
      while (k < seg.end && decisions[k] !== 'S') k += 1;
      if (k < seg.end) before += k - seg.start; // a stretch never detected counts as misses only
    }
    return { basis: 'labels', count: spans.reduce((s, x) => s + spanLen(x), 0), spans, beforeDetection: before };
  }
  const spans = stopGaps(decisions);
  return { basis: 'gaps', count: spans.reduce((s, x) => s + spanLen(x), 0), spans, beforeDetection: 0 };
}

/** "кадр 111", "кадры 40–43", "кадры 40–43, 90", "3 участка" (bag frame numbers). */
export function spansText(spans: readonly Span[], frameOf: (pos: number) => number = (p) => p): string {
  if (spans.length === 0) return '';
  const one = (s: Span) => (spanLen(s) === 1 ? `${frameOf(s.start)}` : `${frameOf(s.start)}–${frameOf(s.end - 1)}`);
  if (spans.length === 1) return spanLen(spans[0]) === 1 ? `кадр ${one(spans[0])}` : `кадры ${one(spans[0])}`;
  if (spans.length === 2) return `кадры ${one(spans[0])}, ${one(spans[1])}`;
  return fmtCount(spans.length, ['участок', 'участка', 'участков']);
}

/** Frames of the first labelled in-gauge stretch before the first STOP (null without labels / STOP). */
export function detectionDelay(decisions: string, labelsInGauge?: readonly boolean[] | null): number | null {
  if (!labelsInGauge || !labelsInGauge.length) return null;
  const firstLabel = labelsInGauge.indexOf(true);
  const firstStop = decisions.indexOf('S');
  if (firstLabel < 0 || firstStop < 0) return null;
  return Math.max(0, firstStop - firstLabel);
}

// ---------------------------------------------------------------- events

export interface EventInfo {
  decision: Decision;
  title: string;
  /** a GO gap inside a STOP */
  gap: boolean;
  /** "кадры 44–66 · 4,4 с" */
  meta: string;
  /** "55,2 м" (STOP) or "3 кадра" */
  value: { num: string; unit: string };
}

export function describeEvent(ev: Episode, opts: { lastFrame?: number; labelled?: boolean } = {}): EventInfo {
  const frames = ev.first_frame === ev.last_frame ? `кадр ${ev.first_frame}` : `кадры ${ev.first_frame}–${ev.last_frame}`;
  const meta = `${frames} · ${fmtDuration(ev.t0)}`;
  const count = { num: fmtNum(ev.n_frames), unit: plural(ev.n_frames, FRAMES) };
  switch (ev.decision) {
    case 'STOP': {
      const toEnd = opts.lastFrame !== undefined && ev.last_frame === opts.lastFrame;
      const d = ev.distance_min;
      return {
        decision: 'STOP',
        gap: false,
        title: toEnd ? 'СТОП до конца записи' : 'СТОП',
        meta,
        value: d !== null ? { num: fmtNum(d, 1), unit: 'м' } : count,
      };
    }
    case 'GO':
      return { decision: 'GO', gap: true, title: opts.labelled ? 'Ложное «свободно»' : 'Разрыв СТОП', meta, value: count };
    case 'CAUTION':
      return { decision: 'CAUTION', gap: false, title: 'Внимание', meta, value: count };
    default:
      return { decision: 'FAULT', gap: false, title: 'Ошибка датчика', meta, value: count };
  }
}

// ---------------------------------------------------------------- verdict against labels

export interface Verdict {
  tone: 'ok' | 'false' | 'none';
  label: string;
}

export function evalVerdict(ev: EvalSummary | null | undefined): Verdict {
  if (!ev) return { tone: 'none', label: 'нет разметки' };
  if (ev.false_stop_episodes > 0) return { tone: 'false', label: `ложный СТОП ×${ev.false_stop_episodes}` };
  if (ev.frames_with_object_in_gauge > 0) {
    const missed = ev.frames_with_object_in_gauge - ev.frames_detected;
    return { tone: 'ok', label: missed > 0 ? `верно · ${ev.frames_detected} / ${ev.frames_with_object_in_gauge}` : 'верно' };
  }
  return { tone: 'ok', label: '0 ложных' };
}

// ---------------------------------------------------------------- the runs list

export type RunFilter = 'all' | 'stop' | 'nostop' | 'labels';
export type RunSort = 'date' | 'name' | 'frames';
export type KindFilter = 'all' | RecordingKind;

export const KIND_LABEL: Record<RecordingKind, string> = { rosbag2: 'rosbag2', npy: 'npy / npz', jsonl: 'jsonl' };

export function matchesFilter(r: Run, f: RunFilter): boolean {
  if (f === 'stop') return r.summary.counts.STOP > 0;
  if (f === 'nostop') return r.summary.counts.STOP === 0;
  if (f === 'labels') return !!r.summary.eval;
  return true;
}

export function filterRuns(runs: readonly Run[], o: { q: string; filter: RunFilter; kind: KindFilter; sort: RunSort }): Run[] {
  const q = o.q.trim().toLocaleLowerCase('ru');
  const out = runs.filter(
    (r) =>
      matchesFilter(r, o.filter) &&
      (o.kind === 'all' || r.source_kind === o.kind) &&
      (!q || r.name.toLocaleLowerCase('ru').includes(q) || r.preset.name.toLocaleLowerCase('ru').includes(q)),
  );
  const byDate = (a: Run, b: Run) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : 0);
  if (o.sort === 'name') out.sort((a, b) => a.name.localeCompare(b.name, 'ru') || byDate(a, b));
  else if (o.sort === 'frames') out.sort((a, b) => b.summary.n_frames - a.summary.n_frames || byDate(a, b));
  else out.sort(byDate);
  return out;
}

// ---------------------------------------------------------------- comparison

/** Series colours of compared runs: distinct, never a safety colour (validated for CVD). */
export const RUN_COLORS = ['#16151A', '#1F5FD0', '#A0612B', '#0A8FA6'] as const;

export interface Metric {
  key: string;
  label: string;
  help: string;
  /** which value is best: the largest, the smallest, or none (a neutral fact) */
  better: 'max' | 'min' | null;
  value: (r: Run) => number | null;
  fmt: (v: number | null) => string;
}

const stopShare = (r: Run) => (r.summary.n_frames ? r.summary.counts.STOP / r.summary.n_frames : null);

export const METRICS: readonly Metric[] = [
  { key: 'frames', label: 'Кадров', help: 'Сколько кадров облака обработал детектор.', better: null, value: (r) => r.summary.n_frames, fmt: (v) => fmtNum(v) },
  { key: 'duration', label: 'Длительность', help: 'Время записи от первого до последнего обработанного кадра.', better: null, value: (r) => r.summary.duration_s, fmt: (v) => fmtDuration(v) },
  { key: 'stop_share', label: 'Кадры СТОП', help: 'Доля кадров с решением СТОП.', better: null, value: stopShare, fmt: (v) => fmtPercent(v, 1) },
  { key: 'stop_episodes', label: 'СТОП-эпизоды', help: 'Сколько раз решение переходило в СТОП.', better: null, value: (r) => r.summary.stop_episodes, fmt: (v) => fmtNum(v) },
  {
    key: 'first_stop',
    label: 'Первый СТОП',
    help: 'Дистанция до препятствия в первом кадре СТОП: чем дальше, тем раньше поезд начнёт тормозить.',
    better: 'max',
    value: (r) => r.summary.first_stop?.distance ?? null,
    fmt: (v) => fmtMeters(v),
  },
  { key: 'distance_min', label: 'Мин. дистанция', help: 'Ближайшее препятствие среди кадров СТОП.', better: null, value: (r) => r.summary.distance_min, fmt: (v) => fmtMeters(v) },
  { key: 'p95', label: 'p95 задержка', help: '95 % кадров детектор обработал быстрее этого времени.', better: 'min', value: (r) => r.summary.latency_ms.p95, fmt: (v) => fmtMs(v) },
  { key: 'fps', label: 'Скорость обработки', help: 'Кадров в секунду при обработке записи на сервере (датчик даёт 10).', better: 'max', value: (r) => r.summary.processing_fps, fmt: (v) => fmtFps(v) },
  {
    key: 'recall',
    label: 'Полнота',
    help: 'Доля кадров, где по разметке объект в габарите и детектор ответил СТОП.',
    better: 'max',
    value: (r) => r.summary.eval?.recall ?? null,
    fmt: (v) => fmtPercent(v, 1),
  },
  {
    key: 'false_frames',
    label: 'Ложные СТОП, кадры',
    help: 'Кадры СТОП, где по разметке в габарите пусто.',
    better: 'min',
    value: (r) => r.summary.eval?.false_stop_frames ?? null,
    fmt: (v) => fmtNum(v),
  },
  {
    key: 'false_episodes',
    label: 'Ложные СТОП, эпизоды',
    help: 'Сколько раз поезд остановился бы без причины.',
    better: 'min',
    value: (r) => r.summary.eval?.false_stop_episodes ?? null,
    fmt: (v) => fmtNum(v),
  },
];

/** Indices of the best values of a row (ties share it); none when fewer than two values or all equal. */
export function bestIndices(values: readonly (number | null)[], better: Metric['better']): Set<number> {
  const out = new Set<number>();
  if (!better) return out;
  const finite = values.map((v, i) => [v, i] as const).filter((x): x is readonly [number, number] => typeof x[0] === 'number' && Number.isFinite(x[0]));
  if (finite.length < 2) return out;
  const best = better === 'max' ? Math.max(...finite.map((x) => x[0])) : Math.min(...finite.map((x) => x[0]));
  if (finite.every((x) => x[0] === best)) return out;
  for (const [v, i] of finite) if (v === best) out.add(i);
  return out;
}

// ---------------------------------------------------------------- presets

export interface ParamDiff {
  key: string;
  label: string;
  unit?: string;
  help?: string;
  values: ParamValue[];
}

/** Parameters whose effective value differs between runs (overrides over the schema defaults). */
export function diffOverrides(overrides: readonly Record<string, ParamValue>[], schema: readonly ParamSpec[] | undefined): ParamDiff[] {
  const keys = new Set<string>();
  for (const o of overrides) for (const k of Object.keys(o)) keys.add(k);
  const spec = new Map((schema ?? []).map((s) => [s.key, s]));
  const out: ParamDiff[] = [];
  for (const key of keys) {
    const s = spec.get(key);
    const values = overrides.map((o) => (key in o ? o[key] : (s?.default ?? '—')));
    if (values.every((v) => String(v) === String(values[0]))) continue;
    out.push({ key, label: s?.label ?? key, unit: s?.unit, help: s?.help, values });
  }
  const order = (k: string) => {
    const i = (schema ?? []).findIndex((s) => s.key === k);
    return i < 0 ? 1e9 : i;
  };
  return out.sort((a, b) => order(a.key) - order(b.key));
}

/** A parameter value the Russian way: "0,2 с", "да" / "нет", "150 м". */
export function fmtParam(v: ParamValue, unit?: string): string {
  if (typeof v === 'boolean') return v ? 'да' : 'нет';
  if (typeof v === 'number') {
    const s = Number.isInteger(v) ? fmtNum(v) : fmtNum(v, Math.min(3, (String(v).split('.')[1] ?? '').length));
    return unit ? `${s} ${unit}` : s;
  }
  return String(v);
}

// ---------------------------------------------------------------- chart ticks

/** "Nice" tick values covering [lo, hi] with at most ~maxTicks ticks. */
export function niceTicks(lo: number, hi: number, maxTicks = 6): number[] {
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
  if (hi < lo) [lo, hi] = [hi, lo];
  if (hi === lo) return [lo];
  const raw = (hi - lo) / Math.max(1, maxTicks - 1);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  const start = Math.ceil(lo / step - 1e-9) * step;
  for (let v = start; v <= hi + step * 1e-9; v += step) out.push(Number(v.toFixed(10)));
  return out;
}

/** A y domain around the data: at least `minSpan` wide, snapped outwards to nice steps. */
export function niceDomain(values: readonly (number | null | undefined)[], minSpan = 1): [number, number] | null {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (typeof v !== 'number' || !Number.isFinite(v)) continue;
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (lo === Infinity) return null;
  const nonNegative = lo >= 0;
  if (hi - lo < minSpan) {
    const mid = (lo + hi) / 2;
    lo = mid - minSpan / 2;
    hi = mid + minSpan / 2;
  }
  const pad = (hi - lo) * 0.08;
  lo -= pad;
  hi += pad;
  const ticks = niceTicks(lo, hi, 6);
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 1;
  const a = Math.floor(lo / step) * step;
  return [nonNegative ? Math.max(0, a) : a, Math.ceil(hi / step) * step];
}

export const episodesText = (n: number): string => fmtCount(n, EPISODES);
