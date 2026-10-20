import { describe, expect, it } from 'vitest';
import { isStatus } from './status';
import { cautionText, decideFrame } from '../lib/decisions';

describe('C1 input boundary and explanations', () => {
  it('preserves legacy and unknown text without inventing reasons', () => {
    expect(isStatus({ decision: 'CAUTION' })).toBe(true);
    expect(cautionText({ decision: 'CAUTION' })).toBe('Причина не передана');
    const r = { decision: 'CAUTION' as const, caution_reason: ['advisory_object', 'health_warning', 'advisory_object', '<b>new</b>'] };
    expect(isStatus(r)).toBe(true);
    expect(cautionText(r)).toBe('Предупреждение об объекте · Снижена достоверность данных · Причина: <b>new</b>');
    for (const decision of ['STOP', 'GO', 'FAULT'] as const) expect(cautionText({ ...r, decision })).toBe('');
  });

  it.each([
    { decision: 'GREEN' }, { obstacle: 'false' }, { warning: 0 }, { stop_held: 'false' },
    { caution_reason: null }, { caution_reason: 'health_warning' }, { caution_reason: [1] },
    { decision_policy: [] }, { health: { decision_level: 'unknown' } },
    { warnings: {} }, { detections: [{}] }, { freshness: { valid: 'true' } },
    { track: { curv_step: '-0.001' } }, { track: { curv_knot: [] } },
    { track: { curv_step: Infinity } }, { track: { curv_knot: NaN } },
  ])('rejects malformed fields: %j', fields => {
    expect(isStatus({ decision: 'GO', ...fields })).toBe(false);
  });

  it('has the shared v1 fallback priorities on invalid flags and health', () => {
    expect(decideFrame({ health: { decision_level: 'error' }, warning: true })).toBe('FAULT');
    expect(decideFrame({ obstacle: true, health: { level: 'error' } })).toBe('STOP');
    expect(decideFrame({ warning: 'false' } as never)).toBe('FAULT');
    expect(decideFrame({ health: [] } as never)).toBe('FAULT');
  });

  it('accepts piecewise tracks and optional legacy coefficients', () => {
    for (const track of [{}, { curv_step: null, curv_knot: null }, { curv_step: -0.001, curv_knot: 60 }]) {
      expect(isStatus({ decision: 'GO', track })).toBe(true);
    }
  });
});
