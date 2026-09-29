// Pure helpers of the cab's console: what each tile says for a frame result (real values only —
// a missing field reads «—»), the lamps of the health tile, the scrubber's event pins and the URL
// state of the player.
import type { Decision, FrameResultDict, RunDetail } from '../../api/types';
import { markerTone, type StripMarker } from '../../components';
import { fmtMeters, fmtNum, fmtNumTrim, fmtPercent } from '../../lib/format';
import { ENVELOPE_PROFILE, profileBounds } from '../../lib/track';
import { snapSpeed } from '../../player/clock';
import type { EventMark } from '../../player/events';
import type { CamMode } from '../../player/geometry';

export const CAMERAS: readonly CamMode[] = ['cab', 'top', 'chase'];

export const CAMERA_LABEL: Record<CamMode, string> = { cab: 'Кабина', top: 'Сверху', chase: 'Сзади' };

/** The HUD chip of the camera ("кабина · вперёд"). */
export const CAMERA_HUD: Record<CamMode, string> = { cab: 'кабина · вперёд', top: 'сверху · 0–200 м', chase: 'сзади · над поездом' };

/** «2,1 × 3,0 м»: width and height of the clearance envelope (configs/default.yaml gauge.profile). */
export function envelopeText(): string {
  const b = profileBounds(ENVELOPE_PROFILE);
  return `${fmtNumTrim(b.yMax - b.yMin, 1)} × ${fmtNum(b.hMax, 1)} м`;
}

/** Benzin size of the decision tile's word, so «ВНИМАНИЕ» fits the 230 px tile like «СТОП». */
export function decisionWordSize(word: string): number {
  if (word.length <= 4) return 46;
  if (word.length <= 6) return 36;
  return 28;
}

export type Tone = 'ok' | 'warn' | 'error';

export interface HealthRow {
  key: 'visibility' | 'rails' | 'calibration';
  label: string;
  value: string;
  tone: Tone;
}

/** health.min_lock_rate of configs/default.yaml (not a curated preset parameter). */
export const MIN_LOCK_RATE = 0.3;

const CALIB_LABEL: Record<string, string> = {
  ok: 'норма',
  identity: 'норма',
  provisional: 'уточняется',
  pending: 'ожидание',
  disabled: 'выкл.',
  fallback: 'запасная',
};

export function calibrationLabel(status: string | undefined): string {
  if (!status) return '—';
  return CALIB_LABEL[status] ?? status;
}

/** The three lamps of «Исправность» for a frame: visibility, rail lock, mount calibration. */
export function healthRows(frame: FrameResultDict | null, minVisibility = 60): HealthRow[] {
  const h = frame?.health ?? {};
  const error = h.level === 'error';
  const vis = typeof h.visibility === 'number' ? h.visibility : null;
  const lock = typeof h.rail_lock === 'number' ? h.rail_lock : null;
  const status = frame?.mount?.status;
  return [
    {
      key: 'visibility',
      label: 'Видимость',
      value: vis === null ? '—' : fmtMeters(vis, 0),
      tone: error ? 'error' : vis !== null && vis < minVisibility ? 'warn' : 'ok',
    },
    {
      key: 'rails',
      label: 'Захват рельсов',
      value: lock === null ? '—' : fmtPercent(lock, 0),
      tone: lock !== null && lock < MIN_LOCK_RATE ? 'warn' : 'ok',
    },
    {
      key: 'calibration',
      label: 'Калибровка',
      value: calibrationLabel(status),
      tone: status === 'fallback' ? 'warn' : 'ok',
    },
  ];
}

export interface DecisionText {
  /** first line under the word */
  line1: string;
  /** second line (with the «?») */
  line2: string;
  /** the tooltip of the second line */
  help: string;
}

/** Texts of the decision tile. `confirmS` = tracking.confirm_time_s of the run. */
export function decisionText(decision: Decision, frame: FrameResultDict | null, confirmS: number, hz = 10): DecisionText {
  const nConfirm = Math.max(1, Math.round(confirmS * hz));
  if (decision === 'STOP') {
    return {
      line1: `в габарите ${envelopeText()}`,
      line2: `подтверждено за ${fmtNumTrim(confirmS, 2)} с`,
      help: `СТОП выдаётся, когда объект держится в габарите ${fmtNumTrim(confirmS, 2)} с — ${nConfirm} кадров подряд.`,
    };
  }
  if (decision === 'CAUTION') {
    const w = frame?.warnings ?? [];
    if (w.length) {
      const d = Math.min(...w.map((x) => x.distance));
      return {
        line1: 'объект у габарита',
        line2: `ближайший ${fmtMeters(d)}`,
        help: 'Объект в зоне предупреждения — на 0,35 м шире габарита. Это внимание, не СТОП.',
      };
    }
    return {
      line1: 'исправность снижена',
      line2: 'проверьте датчик',
      help: 'Детектор предупреждает о входных данных: видимость, захват рельсов, калибровка или задержка.',
    };
  }
  if (decision === 'FAULT') {
    return {
      line1: 'сбой датчика',
      line2: 'путь не проверен',
      help: 'Входные данные непригодны (мало точек, закрыт обзор): детектор не может подтвердить свободный путь.',
    };
  }
  const clear = frame?.clear_distance;
  return {
    line1: 'путь свободен',
    line2: typeof clear === 'number' ? `на ${fmtMeters(clear, 0)}` : '—',
    help: 'Габарит свободен до этой дистанции: дальше детектор не видит путь или впереди объект вне габарита.',
  };
}

export interface DistanceModel {
  /** a confirmed obstacle in the envelope */
  obstacle: boolean;
  title: string;
  /** the big number, metres (null = «—») */
  value: number | null;
  /** free part of the bar, m */
  free: number;
  /** monitored range (the hatched part), m */
  monitored: number | null;
}

export function distanceModel(frame: FrameResultDict | null): DistanceModel {
  const d = frame?.nearest_distance;
  const obstacle = typeof d === 'number' && !!frame?.obstacle;
  const monitored = typeof frame?.health?.monitored_range === 'number' ? frame.health.monitored_range : typeof frame?.health?.visibility === 'number' ? frame.health.visibility : null;
  const clear = typeof frame?.clear_distance === 'number' ? frame.clear_distance : null;
  if (obstacle) return { obstacle, title: 'До препятствия', value: d as number, free: d as number, monitored };
  return { obstacle: false, title: 'Свободный путь', value: clear, free: clear ?? 0, monitored };
}

/** Pins above the scrubber: every event start, thinned so the pills do not overlap. */
export function scrubberMarkers(marks: readonly EventMark[], n: number, maxPins = 16): StripMarker[] {
  const minGap = Math.max(1, n * 0.03);
  const kept: EventMark[] = [];
  for (const m of marks) {
    const prev = kept[kept.length - 1];
    if (prev && m.pos - prev.pos < minGap) {
      // two close events: keep both when they are the only ones there (flags lean apart)
      if (m.pos - prev.pos < minGap * 0.35) continue;
    }
    kept.push(m);
    if (kept.length >= maxPins) break;
  }
  return kept.map((m, i) => {
    const prev = kept[i - 1];
    const next = kept[i + 1];
    const closePrev = !!prev && m.pos - prev.pos < minGap;
    const closeNext = !!next && next.pos - m.pos < minGap;
    const align: StripMarker['align'] = m.pos < n * 0.02 || closePrev ? 'start' : m.pos > n * 0.98 || closeNext ? 'end' : 'center';
    return { pos: m.pos, label: String(m.frame), tone: markerTone(m.decision), align, title: `кадр ${m.frame}` };
  });
}

/** tracking.confirm_time_s the run was made with (its overrides, else the preset schema default). */
export function confirmTime(run: Pick<RunDetail, 'overrides'> | null | undefined, schemaDefault: number | undefined): number {
  const v = run?.overrides?.['tracking.confirm_time_s'];
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string' && Number.isFinite(Number(v.replace(',', '.')))) return Number(v.replace(',', '.'));
  return schemaDefault ?? 0.5;
}

/** health.min_visibility of the run (override, else the schema default, else 60 m). */
export function minVisibility(run: Pick<RunDetail, 'overrides'> | null | undefined, schemaDefault: number | undefined): number {
  const v = run?.overrides?.['health.min_visibility'];
  return typeof v === 'number' && Number.isFinite(v) ? v : (schemaDefault ?? 60);
}

// ---------------------------------------------------------------- URL state

export interface PlayerUrlState {
  pos: number | null;
  speed: number;
  cam: CamMode;
}

export function parsePlayerParams(p: URLSearchParams): PlayerUrlState {
  const rawPos = p.get('pos');
  const pos = rawPos !== null && rawPos.trim() !== '' && Number.isFinite(Number(rawPos)) ? Math.max(0, Math.round(Number(rawPos))) : null;
  const rawSpeed = Number((p.get('speed') ?? '').replace(',', '.'));
  const speed = Number.isFinite(rawSpeed) && rawSpeed > 0 ? snapSpeed(rawSpeed) : 1;
  const c = p.get('cam');
  const cam: CamMode = c === 'top' || c === 'chase' || c === 'cab' ? c : 'cab';
  return { pos, speed, cam };
}

/** The query string of a player state (defaults are left out). */
export function playerSearch(s: { pos: number; speed: number; cam: CamMode }): string {
  const q = new URLSearchParams();
  q.set('pos', String(Math.max(0, Math.round(s.pos))));
  if (s.speed !== 1) q.set('speed', String(s.speed));
  if (s.cam !== 'cab') q.set('cam', s.cam);
  return q.toString();
}
