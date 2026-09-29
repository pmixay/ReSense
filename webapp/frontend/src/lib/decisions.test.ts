import { describe, expect, it } from 'vitest';
import {
  DECISION_LABEL,
  binDecisions,
  countEpisodes,
  decideFrame,
  decisionAt,
  decisionCounts,
  decisionSegments,
  fromLetter,
  worstDecision,
} from './decisions';

// doubleT_obstacle: STOP from frame 8 to the end, one GO (111) and two CAUTION (117, 197)
const doubleT = (() => {
  const a = Array.from({ length: 201 }, (_, i): string => (i < 8 ? 'G' : 'S'));
  a[111] = 'G';
  a[117] = 'C';
  a[197] = 'C';
  return a.join('');
})();

describe('decisions', () => {
  it('has Russian labels', () => {
    expect(DECISION_LABEL).toEqual({ GO: 'свободно', CAUTION: 'внимание', STOP: 'стоп', FAULT: 'ошибка' });
  });
  it('maps letters, unknown as FAULT', () => {
    expect(['G', 'C', 'S', 'F', 'x'].map(fromLetter)).toEqual(['GO', 'CAUTION', 'STOP', 'FAULT', 'FAULT']);
    expect(decisionAt('GCS', 1)).toBe('CAUTION');
    expect(decisionAt('GCS', 3)).toBeNull();
  });
  it('splits into run-length segments', () => {
    expect(decisionSegments('GGCSSF')).toEqual([
      { decision: 'GO', start: 0, end: 2, length: 2 },
      { decision: 'CAUTION', start: 2, end: 3, length: 1 },
      { decision: 'STOP', start: 3, end: 5, length: 2 },
      { decision: 'FAULT', start: 5, end: 6, length: 1 },
    ]);
    expect(decisionSegments('')).toEqual([]);
  });
  it('counts', () => {
    expect(decisionCounts(doubleT)).toEqual({ GO: 9, CAUTION: 2, STOP: 190, FAULT: 0 });
    expect(countEpisodes(doubleT)).toBe(4); // 8–110, 112–116, 118–196, 198–200
    expect(countEpisodes('GGSSGGSGS')).toBe(3);
    expect(worstDecision('GGCF')).toBe('FAULT');
    expect(worstDecision('GSF')).toBe('STOP');
    expect(worstDecision('')).toBeNull();
  });
  it('bins by severity: STOP > FAULT > CAUTION > GO', () => {
    expect(Array.from(binDecisions('GGGCGFGSGG', 5))).toEqual([0, 1, 3, 2, 0]);
    expect(Array.from(binDecisions('GCS', 10))).toEqual([0, 1, 2]);
    const big = 'G'.repeat(11000) + 'S';
    const bins = binDecisions(big, 600);
    expect(bins.length).toBe(600);
    expect(bins[599]).toBe(2);
    expect(bins[0]).toBe(0);
  });
  it('applies the node rule', () => {
    expect(decideFrame({ obstacle: true, health: { level: 'error' } })).toBe('STOP');
    expect(decideFrame({ health: { level: 'error' } })).toBe('FAULT');
    expect(decideFrame({ warning: true })).toBe('CAUTION');
    expect(decideFrame({ health: { level: 'warn', decision_level: 'ok' } })).toBe('GO');
    expect(decideFrame({ health: { level: 'warn' } })).toBe('CAUTION');
    expect(decideFrame({ health: { level: 'ok' } })).toBe('GO');
  });
});
