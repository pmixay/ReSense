import { describe, expect, it } from 'vitest';
import {
  NBSP,
  THIN,
  fmtBytes,
  fmtClock,
  fmtCount,
  fmtDuration,
  fmtFrames,
  fmtInt,
  fmtMeters,
  fmtMs,
  fmtNum,
  fmtNumTrim,
  fmtPercent,
  fmtRange,
  fmtRelDate,
  plural,
} from './format';

// Test strings are written with visible markers: '_' = thin space, '~' = no-break space.
const s = (x: string) => x.replaceAll('_', THIN).replaceAll('~', NBSP);

describe('numbers', () => {
  it('uses comma decimals and thin-space groups', () => {
    expect(fmtNum(54.94, 1)).toBe('54,9');
    expect(fmtNum(11271)).toBe(s('11_271'));
    expect(fmtNum(1510)).toBe(s('1_510'));
    expect(fmtNum(999)).toBe('999');
    expect(fmtNum(1234567.891, 2)).toBe(s('1_234_567,89'));
    expect(fmtNum(-3.5, 1)).toBe('−3,5');
    expect(fmtNum(-0.04, 1)).toBe('0,0');
    expect(fmtInt(7213.6)).toBe(s('7_214'));
  });
  it('prints a dash for missing values', () => {
    expect(fmtNum(null)).toBe('—');
    expect(fmtNum(undefined)).toBe('—');
    expect(fmtNum(Number.NaN)).toBe('—');
    expect(fmtMeters(null)).toBe('—');
  });
  it('trims trailing zeros on request', () => {
    expect(fmtNumTrim(2.0)).toBe('2');
    expect(fmtNumTrim(10.0)).toBe('10');
    expect(fmtNumTrim(2.3)).toBe('2,3');
    expect(fmtNumTrim(100.5, 2)).toBe('100,5');
  });
  it('formats units', () => {
    expect(fmtMeters(54.9)).toBe(s('54,9~м'));
    expect(fmtMs(72.4)).toBe(s('72~мс'));
    expect(fmtMs(4.23)).toBe(s('4,2~мс'));
    expect(fmtPercent(0.64)).toBe(s('64~%'));
    expect(fmtRange(56.6, 55.5)).toBe(s('55,5–56,6~м'));
    expect(fmtRange(55.5, 55.51)).toBe(s('55,5~м'));
    expect(fmtRange(null, 12)).toBe(s('12,0~м'));
  });
});

describe('plural', () => {
  it('follows the Russian rules', () => {
    const f = ['кадр', 'кадра', 'кадров'] as const;
    expect([1, 2, 4, 5, 11, 12, 14, 21, 22, 25, 101, 111, 201, 252, 1510, 11271].map((n) => plural(n, f))).toEqual([
      'кадр', 'кадра', 'кадра', 'кадров', 'кадров', 'кадров', 'кадров', 'кадр', 'кадра', 'кадров', 'кадр', 'кадров',
      'кадр', 'кадра', 'кадров', 'кадр',
    ]);
    expect(fmtFrames(201)).toBe(s('201~кадр'));
    expect(fmtFrames(11271)).toBe(s('11_271~кадр'));
    expect(fmtFrames(1510)).toBe(s('1_510~кадров'));
    expect(fmtCount(3, ['пресет', 'пресета', 'пресетов'])).toBe(s('3~пресета'));
  });
});

describe('durations', () => {
  it('matches the mockups', () => {
    expect(fmtDuration(20.43)).toBe(s('20,4~с'));
    expect(fmtDuration(0)).toBe(s('0,0~с'));
    expect(fmtDuration(84)).toBe('1:24');
    expect(fmtDuration(59.96)).toBe('1:00');
    expect(fmtDuration(1200)).toBe(s('20~мин'));
    expect(fmtDuration(3 * 3600 + 12 * 60)).toBe(s('3~ч 12~мин'));
    expect(fmtDuration(2 * 3600)).toBe(s('2~ч'));
    expect(fmtDuration(null)).toBe('—');
  });
  it('prints clocks', () => {
    expect(fmtClock(131)).toBe('2:11');
    expect(fmtClock(5)).toBe('0:05');
    expect(fmtClock(3723)).toBe('1:02:03');
  });
});

describe('bytes', () => {
  it('uses binary multiples with Russian units', () => {
    expect(fmtBytes(4.5 * 1024 ** 3)).toBe(s('4,5~ГБ'));
    expect(fmtBytes(119 * 1024 ** 3)).toBe(s('119~ГБ'));
    expect(fmtBytes(96 * 1024)).toBe(s('96~КБ'));
    expect(fmtBytes(1.2 * 1024 ** 2)).toBe(s('1,2~МБ'));
    expect(fmtBytes(512)).toBe(s('512~Б'));
    expect(fmtBytes(0)).toBe(s('0~Б'));
    expect(fmtBytes(2 * 1024 ** 3)).toBe(s('2~ГБ'));
    expect(fmtBytes(1024 * 1024 - 10)).toBe(s('1~МБ'));
  });
});

describe('relative dates', () => {
  const now = new Date(2026, 8, 29, 18, 0);
  it('says today / yesterday / the date', () => {
    expect(fmtRelDate(new Date(2026, 8, 29, 14, 32).toISOString(), now)).toBe('сегодня 14:32');
    expect(fmtRelDate(new Date(2026, 8, 28, 17, 40).toISOString(), now)).toBe('вчера 17:40');
    expect(fmtRelDate(new Date(2026, 8, 26, 9, 5).toISOString(), now)).toBe('26.09 09:05');
    expect(fmtRelDate(new Date(2025, 11, 31, 23, 59).toISOString(), now)).toBe('31.12.2025 23:59');
    expect(fmtRelDate('not a date', now)).toBe('—');
    expect(fmtRelDate(null, now)).toBe('—');
  });
});
