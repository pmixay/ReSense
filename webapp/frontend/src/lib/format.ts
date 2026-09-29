// Russian number / unit / date formatting: comma decimals, thin-space digit groups ("11 271"),
// a no-break space before the unit ("54,9 м"). Deterministic (no Intl), so tests and browsers agree.

export const THIN = ' '; // digit groups
export const NBSP = ' '; // value ↔ unit
export const DASH = '—'; // missing value
export const MINUS = '−';

type Num = number | null | undefined;

const ok = (v: Num): v is number => typeof v === 'number' && Number.isFinite(v);

/** "11 271", "54,9", "−3,5"; null / NaN → "—". Groups from 4 digits (as in the mockups: "1 510"). */
export function fmtNum(v: Num, digits = 0): string {
  if (!ok(v)) return DASH;
  const fixed = Math.abs(v).toFixed(digits);
  const [int, frac] = fixed.split('.');
  const grouped = int.length > 3 ? int.replace(/\B(?=(\d{3})+(?!\d))/g, THIN) : int;
  const negative = v < 0 && Number(fixed) !== 0;
  return (negative ? MINUS : '') + grouped + (frac ? ',' + frac : '');
}

/** Like fmtNum but drops a trailing ",0" ("2" instead of "2,0"). */
export function fmtNumTrim(v: Num, digits = 1): string {
  const s = fmtNum(v, digits);
  return s.includes(',') ? s.replace(/,?0+$/, '') : s;
}

export const fmtInt = (v: Num): string => fmtNum(v === null || v === undefined ? v : Math.round(v), 0);

export const withUnit = (value: string, unit: string): string => (value === DASH ? DASH : value + NBSP + unit);

/** "54,9 м" */
export const fmtMeters = (v: Num, digits = 1): string => withUnit(fmtNum(v, digits), 'м');

/** "72 мс"; below 10 ms one decimal ("4,2 мс"). */
export function fmtMs(v: Num): string {
  if (!ok(v)) return DASH;
  return withUnit(fmtNum(v, Math.abs(v) < 10 ? 1 : 0), 'мс');
}

/** "64 %" from a 0..1 fraction. */
export const fmtPercent = (v01: Num, digits = 0): string => (ok(v01) ? withUnit(fmtNum(v01 * 100, digits), '%') : DASH);

/** "31 кадр/с" */
export const fmtFps = (v: Num): string => (ok(v) ? withUnit(fmtNum(v, v < 10 ? 1 : 0), 'кадр/с') : DASH);

/** "1:24", "12:05", "1:02:03" (players, ETA). */
export function fmtClock(seconds: Num): string {
  if (!ok(seconds)) return DASH;
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, '0');
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}

/** Durations the way the mockups write them: "20,4 с" (< 1 min), "1:24" (< 10 min), "20 мин" (< 1 h),
 *  "3 ч 12 мин". */
export function fmtDuration(seconds: Num): string {
  if (!ok(seconds)) return DASH;
  const s = Math.max(0, seconds);
  if (s < 59.95) return withUnit(fmtNum(s, 1), 'с');
  if (s < 600) return fmtClock(s);
  if (s < 3600) return withUnit(fmtInt(s / 60), 'мин');
  const h = Math.floor(s / 3600);
  const m = Math.round((s - h * 3600) / 60);
  if (m === 60) return withUnit(String(h + 1), 'ч');
  return m ? `${h}${NBSP}ч ${m}${NBSP}мин` : withUnit(String(h), 'ч');
}

const BYTE_UNITS = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];

/** "4,5 ГБ", "119 ГБ", "96 КБ", "512 Б" (binary multiples, as file managers show them). */
export function fmtBytes(bytes: Num): string {
  if (!ok(bytes)) return DASH;
  let v = Math.max(0, bytes);
  let i = 0;
  while (v >= 1024 && i < BYTE_UNITS.length - 1) {
    v /= 1024;
    i += 1;
  }
  // 1023.96 КБ would print as "1024 КБ": promote
  if (i < BYTE_UNITS.length - 1 && Math.round(v) >= 1024) {
    v /= 1024;
    i += 1;
  }
  const digits = i === 0 || v >= 10 ? 0 : 1;
  return withUnit(fmtNumTrim(v, digits), BYTE_UNITS[i]);
}

/** "45 МБ/с" */
export const fmtSpeed = (bytesPerSec: Num): string => (ok(bytesPerSec) ? fmtBytes(bytesPerSec) + '/с' : DASH);

/** Russian plural form: plural(1, ['кадр', 'кадра', 'кадров']) → 'кадр'. */
export function plural(n: number, forms: readonly [string, string, string]): string {
  const a = Math.abs(Math.trunc(n));
  const d10 = a % 10;
  const d100 = a % 100;
  if (d10 === 1 && d100 !== 11) return forms[0];
  if (d10 >= 2 && d10 <= 4 && (d100 < 12 || d100 > 14)) return forms[1];
  return forms[2];
}

/** "201 кадр", "1 510 кадров", "252 кадра" */
export const fmtCount = (n: Num, forms: readonly [string, string, string]): string =>
  ok(n) ? withUnit(fmtInt(n), plural(Math.round(n), forms)) : DASH;

export const FRAMES: readonly [string, string, string] = ['кадр', 'кадра', 'кадров'];
export const RUNS: readonly [string, string, string] = ['прогон', 'прогона', 'прогонов'];
export const RECORDINGS: readonly [string, string, string] = ['запись', 'записи', 'записей'];
export const EPISODES: readonly [string, string, string] = ['эпизод', 'эпизода', 'эпизодов'];
export const PRESETS: readonly [string, string, string] = ['пресет', 'пресета', 'пресетов'];
export const FILES: readonly [string, string, string] = ['файл', 'файла', 'файлов'];
export const POINTS: readonly [string, string, string] = ['точка', 'точки', 'точек'];
export const CORES: readonly [string, string, string] = ['ядро', 'ядра', 'ядер'];

export const fmtFrames = (n: Num): string => fmtCount(n, FRAMES);

/** "55,5–56,6 м" (one value when both round the same). */
export function fmtRange(a: Num, b: Num, digits = 1, unit = 'м'): string {
  if (!ok(a) && !ok(b)) return DASH;
  if (!ok(a) || !ok(b)) return withUnit(fmtNum(ok(a) ? a : b, digits), unit);
  const x = fmtNum(Math.min(a, b), digits);
  const y = fmtNum(Math.max(a, b), digits);
  return withUnit(x === y ? x : `${x}–${y}`, unit);
}

const pad2 = (n: number): string => String(n).padStart(2, '0');

function toDate(v: string | number | Date | null | undefined): Date | null {
  if (v === null || v === undefined || v === '') return null;
  const d = v instanceof Date ? v : new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "14:32" (local time) */
export function fmtTime(v: string | number | Date | null | undefined): string {
  const d = toDate(v);
  return d ? `${pad2(d.getHours())}:${pad2(d.getMinutes())}` : DASH;
}

/** "сегодня 14:32", "вчера 17:40", "28.09 14:32", "28.09.2025 14:32" (local time). */
export function fmtRelDate(v: string | number | Date | null | undefined, now: Date = new Date()): string {
  const d = toDate(v);
  if (!d) return DASH;
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((day(now) - day(d)) / 86_400_000);
  const time = fmtTime(d);
  if (diffDays === 0) return `сегодня ${time}`;
  if (diffDays === 1) return `вчера ${time}`;
  const date = `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)}`;
  return d.getFullYear() === now.getFullYear() ? `${date} ${time}` : `${date}.${d.getFullYear()} ${time}`;
}
