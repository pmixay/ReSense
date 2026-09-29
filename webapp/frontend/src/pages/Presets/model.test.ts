import { describe, expect, it } from 'vitest';
import type { Preset } from '../../api/types';
import {
  balanceColumns,
  changedKeys,
  coerce,
  defaultsOf,
  digitsOf,
  draftOf,
  fmtRange,
  fmtValue,
  groupSpecs,
  isNameError,
  overridesOf,
  paramOfError,
  sameDraft,
  splitTail,
  uniqueName,
  valuesOf,
} from './model';
import { SPECS } from './testing';

const preset = (overrides: Preset['overrides'], over: Partial<Preset> = {}): Preset => ({
  id: 'p1',
  name: 'Осторожный',
  description: '',
  builtin: false,
  overrides,
  created_at: '2026-09-29T10:00:00Z',
  ...over,
});

describe('values and overrides', () => {
  it('fills every parameter from the default and applies the overrides in their type', () => {
    expect(defaultsOf(SPECS)).toEqual({ 'gauge.range_max': 250, 'cluster.eps': 0.35, 'cluster.min_points': 5, 'tracking.min_hit_fraction': 0.6, 'lowobj.enabled': true });
    const v = valuesOf(preset({ 'cluster.eps': '0,4', 'lowobj.enabled': 'false', 'no.such': 3 }), SPECS);
    expect(v['cluster.eps']).toBe(0.4);
    expect(v['lowobj.enabled']).toBe(false);
    expect(v).not.toHaveProperty('no.such');
  });

  it('stores only what differs from the default, in the schema order', () => {
    const values = { ...defaultsOf(SPECS), 'lowobj.enabled': false, 'cluster.eps': 0.35000000001, 'gauge.range_max': 120 };
    const out = overridesOf(values, SPECS);
    expect(out).toEqual({ 'gauge.range_max': 120, 'lowobj.enabled': false });
    expect(Object.keys(out)).toEqual(['gauge.range_max', 'lowobj.enabled']);
    expect(changedKeys(values, SPECS)).toEqual(new Set(['gauge.range_max', 'lowobj.enabled']));
  });

  it('coerces stored strings and falls back to the default for garbage', () => {
    expect(coerce(SPECS[1], ' 0,45 ')).toBe(0.45);
    expect(coerce(SPECS[1], 'abc')).toBe(0.35);
    expect(coerce(SPECS[4], 'TRUE')).toBe(true);
    expect(coerce(SPECS[4], 0)).toBe(false);
  });

  it('compares drafts by trimmed name / description and every value', () => {
    const base = draftOf(preset({ 'cluster.min_points': 7 }, { description: 'для жюри' }), SPECS);
    expect(sameDraft({ ...base, name: ' Осторожный ' }, base, SPECS)).toBe(true);
    expect(sameDraft({ ...base, values: { ...base.values, 'cluster.min_points': 8 } }, base, SPECS)).toBe(false);
    expect(sameDraft({ ...base, description: 'другое' }, base, SPECS)).toBe(false);
  });

  it('finds a free name like the backend (case-insensitive)', () => {
    expect(uniqueName('Новый пресет', ['Стандарт 1.0'])).toBe('Новый пресет');
    expect(uniqueName('Новый пресет', ['новый пресет', 'Новый пресет 2'])).toBe('Новый пресет 3');
    expect(uniqueName('   ', [])).toBe('Пресет');
    expect(uniqueName('x'.repeat(100), []).length).toBeLessThanOrEqual(80);
  });
});

describe('groups and columns', () => {
  it('groups in the schema order', () => {
    expect(groupSpecs(SPECS).map((g) => [g.title, g.specs.length])).toEqual([
      ['Габарит', 1],
      ['Кластеризация', 2],
      ['Трекинг', 1],
      ['Низкие объекты', 1],
    ]);
  });

  it('balances items into columns keeping their order and using every column', () => {
    const cols = balanceColumns([276, 276, 526, 126, 326, 426, 176], 3, 16);
    expect(cols).toHaveLength(3);
    expect(cols.flat().sort((a, b) => a - b)).toEqual([0, 1, 2, 3, 4, 5, 6]);
    cols.forEach((c) => expect(c).toEqual([...c].sort((a, b) => a - b)));
    const h = cols.map((c) => c.reduce((s, i) => s + [276, 276, 526, 126, 326, 426, 176][i], 0) + 16 * (c.length - 1));
    expect(Math.max(...h)).toBeLessThanOrEqual(760);
    expect(balanceColumns([100, 100], 3)).toHaveLength(2);
    expect(balanceColumns([], 3)).toEqual([[]]);
  });
});

describe('formatting and backend errors', () => {
  it('formats values and ranges with the step’s precision', () => {
    expect(digitsOf(0.05)).toBe(2);
    expect(digitsOf(0.5)).toBe(1);
    expect(digitsOf(10)).toBe(0);
    expect(digitsOf(1e-7)).toBe(7);
    const flat = (s: string) => s.replace(/[  ]/g, ' ');
    expect(flat(fmtValue(SPECS[1], 0.3))).toBe('0,30 м');
    expect(flat(fmtValue(SPECS[2], 12))).toBe('12 шт');
    expect(fmtValue(SPECS[3], 0.6)).toBe('0,60');
    expect(fmtValue(SPECS[4], false)).toBe('нет');
    expect(flat(fmtRange(SPECS[0]))).toBe('30–250 м');
    expect(fmtRange(SPECS[4])).toBe('');
  });

  it('finds the parameter a 422 names, and recognises name errors', () => {
    const keys = SPECS.map((s) => s.key);
    expect(paramOfError('«Радиус объединения точек» (cluster.eps): значение 5 вне диапазона 0,1…1 м', keys)).toBe('cluster.eps');
    expect(paramOfError('Неизвестный параметр «cluster.nope»', keys)).toBeNull();
    expect(paramOfError('Неизвестный параметр «cluster.eps»', keys)).toBe('cluster.eps');
    expect(isNameError('Пресет с таким названием уже есть')).toBe(true);
    expect(isNameError('Укажите название пресета')).toBe(true);
    expect(isNameError('Пресет не найден')).toBe(false);
  });
});

describe('splitTail', () => {
  it('keeps the last word (and a short unit before it) together with the «?»', () => {
    expect(splitTail('Радиус объединения точек')).toEqual(['Радиус объединения ', 'точек']);
    expect(splitTail('Запас у края на 100 м')).toEqual(['Запас у края на ', '100 м']);
    expect(splitTail('Накопление')).toEqual(['', 'Накопление']);
    expect(splitTail('Бюджет задержки')).toEqual(['Бюджет ', 'задержки']);
  });
});
