// Pure helpers of the live page: the display state of a feed, the rolling 30 s timeline (time slots
// with the most severe decision, gaps where no message arrived), the detections table and the
// health lamps — all derived from the /resense/status JSON (the sim sends the same keys).
import type { Decision, DetectionDict, LiveMessage, MountDict } from '../../api/types';
import { DECISION_LETTER, SEVERITY, fromLetter, type DecisionLetter } from '../../lib/decisions';
import { fmtMeters, fmtNum, fmtPercent } from '../../lib/format';

/** Rolling timeline window, its resolution and the freshness limit (the node's max_result_age). */
export const WINDOW_MS = 30_000;
export const SLOT_MS = 100;
export const STALE_MS = 500;

/** health.min_lock_rate of configs/default.yaml: the rail pair found in fewer recent frames is a warning. */
export const MIN_RAIL_LOCK = 0.3;
/** health.min_visibility of configs/default.yaml (the preset schema's default is used when loaded). */
export const MIN_VISIBILITY = 60;

// ---------------------------------------------------------------- the node's extra keys

/** The real node adds these to the status JSON (ros2_ws/.../detector_node.py); the sim does not. */
export interface NodeFreshness {
  valid?: boolean;
  reason?: string;
  go_allowed?: boolean;
  source_age_s?: number | null;
}

export type StatusMessage = Omit<LiveMessage, 'node'> & {
  /** absent in the node's watchdog / processing-error snapshots */
  node?: LiveMessage['node'];
  freshness?: NodeFreshness;
  stop_held?: boolean;
};

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

// ---------------------------------------------------------------- feed state

export type LinkStatus = 'idle' | 'connecting' | 'open' | 'ended' | 'error';
export type LiveView = 'idle' | 'connecting' | 'waiting' | 'live' | 'stale' | 'paused' | 'ended' | 'error';

/** What the page shows: `live` only while messages arrive at most STALE_MS apart. */
export function liveView(link: LinkStatus, lastAt: number | null, now: number, paused = false): LiveView {
  if (link !== 'open') return link;
  if (paused) return 'paused';
  if (lastAt === null) return 'waiting';
  return now - lastAt > STALE_MS ? 'stale' : 'live';
}

export const VIEW_LABEL: Record<LiveView, string> = {
  idle: 'не подключено',
  connecting: 'подключение…',
  waiting: 'ждём данные',
  live: 'в эфире',
  stale: 'данные устарели',
  paused: 'пауза',
  ended: 'конец записи',
  error: 'нет связи',
};

// ---------------------------------------------------------------- rolling timeline

export interface Sample {
  /** ms in the feed's time basis (recording time for the sim, receive time for the node) */
  at: number;
  d: Decision;
  /** the monitored free distance ahead (clear_distance, capped at the nearest obstacle; null on FAULT) */
  free: number | null;
  latency: number | null;
}

export function sampleOf(msg: StatusMessage, at: number): Sample {
  // ОШИБКА: nothing is monitored, whatever clear_distance the frame carries
  const free = msg.decision === 'FAULT' ? null : num(msg.clear_distance);
  return { at, d: msg.decision, free, latency: num(msg.node?.latency_ms) ?? num(msg.timing_ms?.total) };
}

/** Drops samples older than the window before `now` (keeps the array sorted by `at`). */
export function trimSamples(samples: Sample[], now: number, windowMs = WINDOW_MS): Sample[] {
  const t0 = now - windowMs - SLOT_MS;
  let i = 0;
  while (i < samples.length && samples[i].at < t0) i += 1;
  return i ? samples.slice(i) : samples;
}

export interface Slots {
  /** one letter per slot, null where no message arrived (and none within STALE_MS before) */
  letters: (DecisionLetter | null)[];
  free: (number | null)[];
  latency: (number | null)[];
}

/** Buckets the samples of the last `windowMs` into slots; a slot takes its most severe decision, the
 *  smallest free distance and the largest latency. A gap shorter than `holdMs` carries the previous
 *  slot forward (a 10 Hz stream received with jitter does not land in every 100 ms slot), a longer
 *  one stays empty: no data. */
export function buildSlots(samples: readonly Sample[], now: number, windowMs = WINDOW_MS, slotMs = SLOT_MS, holdMs = STALE_MS): Slots {
  const n = Math.max(1, Math.round(windowMs / slotMs));
  const t0 = now - windowMs;
  const letters: (DecisionLetter | null)[] = new Array(n).fill(null);
  const free: (number | null)[] = new Array(n).fill(null);
  const latency: (number | null)[] = new Array(n).fill(null);
  for (const s of samples) {
    let i = Math.floor((s.at - t0) / slotMs);
    if (i === n && s.at <= now) i = n - 1;
    if (i < 0 || i >= n) continue;
    const cur = letters[i];
    if (cur === null || SEVERITY[s.d] > SEVERITY[fromLetter(cur)]) letters[i] = DECISION_LETTER[s.d];
    if (s.free !== null) free[i] = free[i] === null ? s.free : Math.min(free[i] as number, s.free);
    if (s.latency !== null) latency[i] = Math.max(latency[i] ?? 0, s.latency);
  }
  const hold = Math.floor(holdMs / slotMs);
  let last = -Infinity;
  for (let i = 0; i < n; i += 1) {
    if (letters[i] !== null) {
      last = i;
      continue;
    }
    if (i - last <= hold && last >= 0) {
      letters[i] = letters[last];
      free[i] = free[last];
      latency[i] = latency[last];
    }
  }
  return { letters, free, latency };
}

export interface DataRun {
  start: number;
  end: number; // exclusive
  decisions: string;
}

/** Maximal blocks of slots with data (the strip draws one DecisionStrip per block). */
export function dataRuns(letters: readonly (DecisionLetter | null)[]): DataRun[] {
  const out: DataRun[] = [];
  let i = 0;
  while (i < letters.length) {
    if (letters[i] === null) {
      i += 1;
      continue;
    }
    let j = i;
    let s = '';
    while (j < letters.length && letters[j] !== null) {
      s += letters[j];
      j += 1;
    }
    out.push({ start: i, end: j, decisions: s });
    i = j;
  }
  return out;
}

// ---------------------------------------------------------------- detections

export interface DetectionRow {
  key: string;
  zone: 'gauge' | 'warning';
  distance: number;
  lateral: number;
  /** length × width × height (m), the detector's box extents along X, Y, Z */
  size: [number, number, number];
  confidence: number;
}

/** In-gauge objects and advisory ones (warnings), nearest first. */
export function detectionRows(msg: StatusMessage | null): DetectionRow[] {
  if (!msg) return [];
  const rows: DetectionRow[] = [];
  const add = (list: DetectionDict[] | undefined, zone: DetectionRow['zone']) => {
    (list ?? []).forEach((d, i) => {
      const distance = num(d.distance);
      if (distance === null) return;
      const size = Array.isArray(d.size) ? d.size : [0, 0, 0];
      rows.push({
        key: `${zone}-${d.id ?? i}`,
        zone,
        distance,
        lateral: num(d.lateral) ?? 0,
        size: [num(size[0]) ?? 0, num(size[1]) ?? 0, num(size[2]) ?? 0],
        confidence: num(d.confidence) ?? 0,
      });
    });
  };
  add(msg.detections, 'gauge');
  add(msg.warnings, 'warning');
  return rows.sort((a, b) => a.distance - b.distance || (a.zone === 'gauge' ? -1 : 1));
}

/** "0,1 м влево" / "0,3 м вправо" / "по оси" (lateral + = left of the train). */
export function fmtLateral(v: number): string {
  if (Math.abs(v) < 0.05) return 'по оси';
  return `${fmtMeters(Math.abs(v))} ${v > 0 ? 'влево' : 'вправо'}`;
}

/** "0,4 × 0,5 × 1,3 м" */
export function fmtSize(s: readonly number[]): string {
  return `${s.map((v) => fmtNum(v, 1)).join(' × ')} м`;
}

// ---------------------------------------------------------------- health lamps

export type Lamp = 'ok' | 'warn' | 'error' | 'wait' | 'off';

export interface HealthRow {
  key: 'visibility' | 'rails' | 'calibration';
  label: string;
  lamp: Lamp;
  value: string;
}

const MOUNT: Record<string, [Lamp, string]> = {
  ok: ['ok', 'норма'],
  identity: ['ok', 'норма'],
  provisional: ['ok', 'предварительно'],
  pending: ['wait', 'ожидание'],
  fallback: ['warn', 'запасная'],
  disabled: ['off', 'выключена'],
};

/** Visibility along the track, rail lock and the mount calibration. Lamps go dark (`off`) when the
 *  data is not fresh: an old value is never shown as a green light. */
export function healthRows(msg: StatusMessage | null, fresh: boolean, minVisibility = MIN_VISIBILITY): HealthRow[] {
  const h = msg?.health ?? {};
  const vis = num(h.visibility);
  const lock = num(h.rail_lock);
  const mount = (msg?.mount ?? {}) as MountDict;
  const [mLamp, mText] = MOUNT[String(mount.status ?? '')] ?? ['off', '—'];
  const gate = (l: Lamp): Lamp => (fresh ? l : 'off');
  return [
    { key: 'visibility', label: 'Видимость', lamp: gate(vis === null ? 'off' : vis >= minVisibility ? 'ok' : 'warn'), value: fmtMeters(vis, 0) },
    { key: 'rails', label: 'Захват рельсов', lamp: gate(lock === null ? 'off' : lock >= MIN_RAIL_LOCK ? 'ok' : 'warn'), value: fmtPercent(lock) },
    { key: 'calibration', label: 'Калибровка', lamp: gate(mLamp), value: mText },
  ];
}

/** The detector's overall health level of the frame (ok / warn / error), null without data. */
export function healthLevel(msg: StatusMessage | null): 'ok' | 'warn' | 'error' | null {
  const lv = msg?.health?.level;
  return lv === 'ok' || lv === 'warn' || lv === 'error' ? lv : null;
}
