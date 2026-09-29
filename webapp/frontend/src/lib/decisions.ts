// Decisions (GO / CAUTION / STOP / FAULT): labels, colours and the per-frame decision string
// ("GGCSSSF…", one letter per processed frame, webapp/API.md).
import type { Decision } from '../api/types';

export type { Decision };
export type DecisionLetter = 'G' | 'C' | 'S' | 'F';

export const DECISIONS: readonly Decision[] = ['GO', 'CAUTION', 'STOP', 'FAULT'];

export const DECISION_LETTER: Record<Decision, DecisionLetter> = { GO: 'G', CAUTION: 'C', STOP: 'S', FAULT: 'F' };
const LETTER_DECISION: Record<string, Decision> = { G: 'GO', C: 'CAUTION', S: 'STOP', F: 'FAULT' };

/** Russian labels (lower case, for text and legends). */
export const DECISION_LABEL: Record<Decision, string> = {
  GO: 'свободно',
  CAUTION: 'внимание',
  STOP: 'стоп',
  FAULT: 'ошибка',
};

/** Upper-case labels for decision chips and beacons (Benzin). */
export const DECISION_CHIP_LABEL: Record<Decision, string> = {
  GO: 'СВОБОДНО',
  CAUTION: 'ВНИМАНИЕ',
  STOP: 'СТОП',
  FAULT: 'ОШИБКА',
};

/** Fill colours (strips, lamps). STOP is always drawn with the white 45° hatch on top. */
export const DECISION_COLOR: Record<Decision, string> = {
  GO: '#12A150',
  CAUTION: '#FFB300',
  STOP: '#D0001B',
  FAULT: '#5B4E9C',
};

/** Background under text (GO uses the deeper green so white text has contrast). */
export const DECISION_BG: Record<Decision, string> = {
  GO: '#0B7A3B',
  CAUTION: '#FFB300',
  STOP: '#D0001B',
  FAULT: '#5B4E9C',
};

/** Text colour on DECISION_BG: ink on amber, white otherwise. */
export const DECISION_INK: Record<Decision, string> = {
  GO: '#FFFFFF',
  CAUTION: '#16151A',
  STOP: '#FFFFFF',
  FAULT: '#FFFFFF',
};

/** Numeric codes used by the strip renderer: 0 GO, 1 CAUTION, 2 STOP, 3 FAULT. */
export const DECISION_CODE: Record<Decision, number> = { GO: 0, CAUTION: 1, STOP: 2, FAULT: 3 };
export const CODE_DECISION: readonly Decision[] = ['GO', 'CAUTION', 'STOP', 'FAULT'];

/** When several frames share one pixel, the most severe wins: STOP > FAULT > CAUTION > GO. */
export const SEVERITY: Record<Decision, number> = { GO: 0, CAUTION: 1, FAULT: 2, STOP: 3 };

export function isDecision(v: unknown): v is Decision {
  return v === 'GO' || v === 'CAUTION' || v === 'STOP' || v === 'FAULT';
}

/** Letter → decision; anything unknown reads as FAULT (never silently as GO). */
export function fromLetter(ch: string): Decision {
  return LETTER_DECISION[ch] ?? 'FAULT';
}

export function decisionAt(decisions: string, pos: number): Decision | null {
  if (pos < 0 || pos >= decisions.length) return null;
  return fromLetter(decisions[pos]);
}

export interface DecisionSegment {
  decision: Decision;
  start: number; // first position (0-based, processed order)
  end: number; // exclusive
  length: number;
}

/** Run-length segments of a decision string. */
export function decisionSegments(decisions: string): DecisionSegment[] {
  const out: DecisionSegment[] = [];
  const n = decisions.length;
  let i = 0;
  while (i < n) {
    const ch = decisions[i];
    let j = i + 1;
    while (j < n && decisions[j] === ch) j += 1;
    out.push({ decision: fromLetter(ch), start: i, end: j, length: j - i });
    i = j;
  }
  return out;
}

export function decisionCounts(decisions: string): Record<Decision, number> {
  const c: Record<Decision, number> = { GO: 0, CAUTION: 0, STOP: 0, FAULT: 0 };
  for (let i = 0; i < decisions.length; i += 1) c[fromLetter(decisions[i])] += 1;
  return c;
}

/** Number of maximal STOP blocks. */
export function countEpisodes(decisions: string, decision: Decision = 'STOP'): number {
  return decisionSegments(decisions).filter((s) => s.decision === decision).length;
}

/** The most severe decision of a string (null when empty). */
export function worstDecision(decisions: string): Decision | null {
  let worst: Decision | null = null;
  for (let i = 0; i < decisions.length; i += 1) {
    const d = fromLetter(decisions[i]);
    if (worst === null || SEVERITY[d] > SEVERITY[worst]) worst = d;
    if (worst === 'STOP') break;
  }
  return worst;
}

/** Codes (DECISION_CODE) per bin, the most severe decision of each bin; bins >= n returns one per frame. */
export function binDecisions(decisions: string, bins: number): Uint8Array {
  const n = decisions.length;
  if (n === 0 || bins <= 0) return new Uint8Array(0);
  if (bins >= n) {
    const out = new Uint8Array(n);
    for (let i = 0; i < n; i += 1) out[i] = DECISION_CODE[fromLetter(decisions[i])];
    return out;
  }
  const out = new Uint8Array(bins);
  const k = n / bins;
  for (let b = 0; b < bins; b += 1) {
    const i0 = Math.floor(b * k);
    const i1 = Math.max(i0 + 1, Math.floor((b + 1) * k));
    let worst: Decision = 'GO';
    for (let i = i0; i < i1 && i < n; i += 1) {
      const d = fromLetter(decisions[i]);
      if (SEVERITY[d] > SEVERITY[worst]) worst = d;
      if (worst === 'STOP') break;
    }
    out[b] = DECISION_CODE[worst];
  }
  return out;
}

/** The ROS node's rule (webapp/API.md) for a FrameResult-like dict that carries no decision. */
export function decideFrame(r: {
  obstacle?: boolean;
  warning?: boolean;
  health?: { level?: string; decision_level?: string } | null;
}): Decision {
  if (r.obstacle) return 'STOP';
  const level = r.health?.level;
  if (level === 'error') return 'FAULT';
  const dlevel = r.health?.decision_level ?? level;
  if (r.warning || dlevel === 'warn') return 'CAUTION';
  return 'GO';
}
