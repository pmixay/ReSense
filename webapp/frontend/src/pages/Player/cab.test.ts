import { describe, expect, it } from 'vitest';
import type { FrameResultDict } from '../../api/types';
import type { EventMark } from '../../player/events';
import {
  calibrationLabel,
  confirmTime,
  decisionText,
  decisionWordSize,
  distanceModel,
  envelopeText,
  healthRows,
  minVisibility,
  parsePlayerParams,
  pinWidth,
  playerSearch,
  scrubberMarkers,
} from './cab';

const fr = (o: Partial<FrameResultDict>): FrameResultDict => o as FrameResultDict;
/** Russian formatting puts non-breaking spaces before units: compare with plain ones. */
const sp = (s: string): string => s.replace(/[\u00a0\u202f]/g, ' ');
const mark = (pos: number, decision: EventMark['decision'] = 'STOP'): EventMark => ({ pos, endPos: pos + 2, decision, frame: pos });

describe('texts', () => {
  it('formats the envelope in Russian', () => {
    expect(sp(envelopeText())).toBe('2,1 × 3,0 м');
  });

  it('sizes the decision word to the tile', () => {
    expect(decisionWordSize('СТОП')).toBe(46);
    expect(decisionWordSize('ОШИБКА')).toBe(31);
    expect(decisionWordSize('ВНИМАНИЕ')).toBe(23);
    expect(decisionWordSize('СВОБОДНО')).toBe(23);
  });

  it('explains a STOP with the confirmation time of the run', () => {
    const t = decisionText('STOP', null, 0.5);
    expect(sp(t.line1)).toBe('в габарите 2,1 × 3,0 м');
    expect(sp(t.line2)).toBe('подтверждено за 0,5 с');
    expect(t.help).toContain('5 кадров');
  });

  it('names the nearest warning of a CAUTION, else the health', () => {
    const w = decisionText('CAUTION', fr({ warnings: [{ distance: 30.2 }, { distance: 12.34 }] as FrameResultDict['warnings'] }), 0.5);
    expect(sp(w.line2)).toBe('ближайший 12,3 м');
    expect(decisionText('CAUTION', fr({ warnings: [] }), 0.5).line1).toBe('исправность снижена');
  });

  it('says how far the track is clear on GO', () => {
    expect(sp(decisionText('GO', fr({ clear_distance: 187.4 }), 0.5).line2)).toBe('на 187 м');
    expect(decisionText('GO', null, 0.5).line2).toBe('—');
  });

  it('maps the mount status', () => {
    expect(calibrationLabel('ok')).toBe('норма');
    expect(calibrationLabel('pending')).toBe('ожидание');
    expect(calibrationLabel(undefined)).toBe('—');
    expect(calibrationLabel('weird')).toBe('weird');
  });
});

describe('distanceModel', () => {
  it('reads the obstacle distance and the monitored range', () => {
    const m = distanceModel(fr({ obstacle: true, nearest_distance: 54.9, clear_distance: 54.8, health: { monitored_range: 197 } }));
    expect(m).toEqual({ obstacle: true, unverified: false, title: 'До препятствия', value: 54.9, free: 54.9, monitored: 197 });
  });

  it('shows the free track without an obstacle', () => {
    const m = distanceModel(fr({ obstacle: false, nearest_distance: null, clear_distance: 120, health: { visibility: 150 } }));
    expect(m).toEqual({ obstacle: false, unverified: false, title: 'Свободный путь', value: 120, free: 120, monitored: 150 });
    expect(distanceModel(null).value).toBeNull();
    // no frame yet: the title follows the run's decision, nothing is claimed
    expect(distanceModel(null, 'STOP')).toMatchObject({ title: 'До препятствия', value: null, free: 0, obstacle: false });
    expect(distanceModel(null, 'FAULT')).toMatchObject({ title: 'Путь не проверен', unverified: true });
  });

  it('claims no free distance on FAULT (nothing is verified)', () => {
    const m = distanceModel(fr({ decision: 'FAULT', obstacle: false, clear_distance: 183, health: { level: 'error', monitored_range: 183 } }));
    expect(m).toEqual({ obstacle: false, unverified: true, title: 'Путь не проверен', value: null, free: 0, monitored: null });
    // an obstacle still wins (STOP outranks FAULT)
    expect(distanceModel(fr({ decision: 'STOP', obstacle: true, nearest_distance: 20 })).obstacle).toBe(true);
  });
});

describe('healthRows', () => {
  it('lights the three lamps from the health and mount of the frame', () => {
    const rows = healthRows(fr({ health: { visibility: 197, rail_lock: 1 }, mount: { status: 'ok' } as FrameResultDict['mount'] }), 60);
    expect(rows.map((r) => [r.label, sp(r.value), r.tone])).toEqual([
      ['Видимость', '197 м', 'ok'],
      ['Захват рельсов', '100 %', 'ok'],
      ['Калибровка', 'норма', 'ok'],
    ]);
  });

  it('warns on low visibility / rail lock and fails on a health error', () => {
    const rows = healthRows(fr({ health: { visibility: 40, rail_lock: 0.1, level: 'error' }, mount: { status: 'fallback' } as FrameResultDict['mount'] }), 60);
    expect(rows.map((r) => r.tone)).toEqual(['error', 'warn', 'warn']);
    expect(healthRows(null).map((r) => r.value)).toEqual(['—', '—', '—']);
    // no value, no claim: the lamps stay hollow instead of green
    expect(healthRows(null).map((r) => r.tone)).toEqual(['none', 'none', 'none']);
  });
});

describe('run parameters', () => {
  it('uses the run overrides, else the schema default', () => {
    expect(confirmTime({ overrides: { 'tracking.confirm_time_s': 0.8 } }, 0.5)).toBe(0.8);
    expect(confirmTime({ overrides: { 'tracking.confirm_time_s': '0,3' } }, 0.5)).toBe(0.3);
    expect(confirmTime({ overrides: {} }, 0.4)).toBe(0.4);
    expect(confirmTime(null, undefined)).toBe(0.5);
    expect(minVisibility({ overrides: { 'health.min_visibility': 80 } }, 60)).toBe(80);
    expect(minVisibility(null, undefined)).toBe(60);
  });
});

describe('scrubberMarkers', () => {
  const W = 660;
  const extent = (m: { pos: number; label: unknown; align?: string }, n: number): [number, number] => {
    const w = pinWidth(String(m.label));
    if (m.align === 'start') return [(m.pos / n) * W, (m.pos / n) * W + w];
    const x = ((m.pos + 0.5) / n) * W;
    return m.align === 'end' ? [x - w, x] : [x - w / 2, x + w / 2];
  };

  it('keeps well separated events centred', () => {
    const out = scrubberMarkers([mark(20), mark(60, 'CAUTION')], 100, W);
    expect(out.map((m) => [m.pos, m.label, m.tone, m.align])).toEqual([
      [20, '20', 'stop', 'center'],
      [60, '60', 'caution', 'center'],
    ]);
  });

  it('hangs pills at the ends of the strip inwards', () => {
    const out = scrubberMarkers([mark(0), mark(199, 'GO')], 200, W);
    expect(out.map((m) => m.align)).toEqual(['start', 'end']);
  });

  it('leans two close pills apart (the mockup 111 / 117) so they never overlap', () => {
    const out = scrubberMarkers([mark(41, 'CAUTION'), mark(44)], 100, W);
    expect(out.map((m) => m.align)).toEqual(['end', 'start']);
    const [a, b] = out.map((m) => extent(m, 100));
    expect(a[1]).toBeLessThanOrEqual(b[0]);
  });

  it('drops a pill that cannot be placed without overlapping', () => {
    const out = scrubberMarkers([mark(40), mark(41), mark(42), mark(43)], 100, W);
    expect(out.length).toBeLessThan(4);
    for (let i = 1; i < out.length; i += 1) expect(extent(out[i - 1], 100)[1]).toBeLessThanOrEqual(extent(out[i], 100)[0]);
  });

  it('caps the number of pins', () => {
    const many = Array.from({ length: 40 }, (_, i) => mark(i * 50));
    expect(scrubberMarkers(many, 2000, 10 * W, 16)).toHaveLength(16);
  });
});

describe('URL state', () => {
  it('parses a deep link', () => {
    expect(parsePlayerParams(new URLSearchParams('pos=112&speed=2&cam=top'))).toEqual({ pos: 112, speed: 2, cam: 'top' });
    expect(parsePlayerParams(new URLSearchParams('speed=0,5'))).toEqual({ pos: null, speed: 0.5, cam: 'cab' });
    expect(parsePlayerParams(new URLSearchParams('pos=-4&speed=abc&cam=drone'))).toEqual({ pos: 0, speed: 1, cam: 'cab' });
    expect(parsePlayerParams(new URLSearchParams('speed=3'))).toEqual({ pos: null, speed: 2, cam: 'cab' });
  });

  it('writes only what differs from the defaults', () => {
    expect(playerSearch({ pos: 12, speed: 1, cam: 'cab' })).toBe('pos=12');
    expect(playerSearch({ pos: 12.4, speed: 0.25, cam: 'chase' })).toBe('pos=12&speed=0.25&cam=chase');
  });
});
