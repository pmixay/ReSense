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
export const CAMERA_HUD: Record<CamMode, string> = { cab: 'кабина · вперёд', top: 'сверху · план пути', chase: 'сзади · над поездом' };

/** «2,1 × 3,0 м»: width and height of the clearance envelope (configs/default.yaml gauge.profile). */
export function envelopeText(): string {
  const b = profileBounds(ENVELOPE_PROFILE);
  return `${fmtNumTrim(b.yMax - b.yMin, 1)} × ${fmtNum(b.hMax, 1)} м`;
}

/** Benzin size of the decision tile's word, so «СВОБОДНО» fits the 230 px tile like «СТОП»
 *  (Benzin 800 capitals run about 1 em wide; 190 px of text width inside the padding). */
export function decisionWordSize(word: string): number {
  return Math.min(46, Math.floor(190 / Math.max(1, word.length)));
}

/** none = no value in this frame (a hollow lamp: nothing is claimed) */
export type Tone = 'ok' | 'warn' | 'error' | 'none';

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
      tone: error ? 'error' : vis === null ? 'none' : vis < minVisibility ? 'warn' : 'ok',
    },
    {
      key: 'rails',
      label: 'Захват рельсов',
      value: lock === null ? '—' : fmtPercent(lock, 0),
      tone: lock === null ? 'none' : lock < MIN_LOCK_RATE ? 'warn' : 'ok',
    },
    {
      key: 'calibration',
      label: 'Калибровка',
      value: calibrationLabel(status),
      tone: !status ? 'none' : status === 'fallback' ? 'warn' : 'ok',
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
  /** FAULT: the input is unusable, no free distance is claimed */
  unverified: boolean;
  title: string;
  /** the big number, metres (null = «—») */
  value: number | null;
  /** free part of the bar, m */
  free: number;
  /** monitored range (the hatched part), m */
  monitored: number | null;
}

/** The distance readout of a frame; without a frame (still loading, failed) the title follows the
 *  run's decision at the playhead and no number is claimed. */
export function distanceModel(frame: FrameResultDict | null, decision: Decision | null = null): DistanceModel {
  if (!frame) {
    const title = decision === 'STOP' ? 'До препятствия' : decision === 'FAULT' ? 'Путь не проверен' : 'Свободный путь';
    return { obstacle: false, unverified: decision === 'FAULT', title, value: null, free: 0, monitored: null };
  }
  const d = frame?.nearest_distance;
  const obstacle = typeof d === 'number' && !!frame?.obstacle;
  const monitored = typeof frame?.health?.monitored_range === 'number' ? frame.health.monitored_range : typeof frame?.health?.visibility === 'number' ? frame.health.visibility : null;
  const clear = typeof frame?.clear_distance === 'number' ? frame.clear_distance : null;
  if (obstacle) return { obstacle, unverified: false, title: 'До препятствия', value: d as number, free: d as number, monitored };
  if (frame?.decision === 'FAULT') return { obstacle: false, unverified: true, title: 'Путь не проверен', value: null, free: 0, monitored: null };
  return { obstacle: false, unverified: false, title: 'Свободный путь', value: clear, free: clear ?? 0, monitored };
}

/** Width of the scrubber's strip in stage px (1600 − the controls around it). */
export const SCRUB_LANE_W = 670;
/** Approximate width of a pin pill (DecisionStrip: Montserrat 800 11 px, 7 px padding). */
export const pinWidth = (label: string): number => 14 + 7 * label.length;

type PinAlign = NonNullable<StripMarker['align']>;
interface Pin {
  mark: EventMark;
  label: string;
  align: PinAlign;
}

/**
 * Pins above the scrubber: every event start as a pill. Pills at the ends hang inwards; two close
 * pills lean apart (the left one ends at its frame, the right one starts at it, as in the mockup);
 * a pill that would still overlap its neighbour is dropped. `laneW` = the strip width in px.
 */
export function scrubberMarkers(marks: readonly EventMark[], n: number, laneW = SCRUB_LANE_W, maxPins = 16): StripMarker[] {
  const GAP = 3;
  const N = Math.max(1, n);
  const extent = (p: Pin): [number, number] => {
    const w = pinWidth(p.label);
    if (p.align === 'start') {
      const x = (p.mark.pos / N) * laneW;
      return [x, x + w];
    }
    const x = ((p.mark.pos + 0.5) / N) * laneW;
    return p.align === 'end' ? [x - w, x] : [x - w / 2, x + w / 2];
  };
  const clash = (a: Pin | undefined, b: Pin): boolean => !!a && extent(a)[1] + GAP > extent(b)[0];
  const out: Pin[] = [];
  for (const mark of marks) {
    if (out.length >= maxPins) break;
    const label = String(mark.frame);
    let pin: Pin = { mark, label, align: 'center' };
    const [x0, x1] = extent(pin);
    if (x0 < 0) pin.align = 'start';
    else if (x1 > laneW) pin.align = 'end';
    const prev = out[out.length - 1];
    if (clash(prev, pin)) {
      const right: Pin = { ...pin, align: pin.align === 'end' ? 'end' : 'start' };
      const left: Pin | null = prev.align === 'start' ? null : { ...prev, align: 'end' };
      if (left && !clash(out[out.length - 2], left) && !clash(left, right)) {
        out[out.length - 1] = left;
        pin = right;
      } else if (!clash(prev, right)) pin = right;
      else continue;
    }
    out.push(pin);
  }
  return out.map((p) => ({ pos: p.mark.pos, label: p.label, tone: markerTone(p.mark.decision), align: p.align, title: `кадр ${p.mark.frame}` }));
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
