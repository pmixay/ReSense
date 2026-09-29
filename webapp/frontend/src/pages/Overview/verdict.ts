// What a run says in one chip: against the labels when the run was scored (RunSummary.eval), else
// its STOP count. Used by «Последние прогоны» and the finished jobs of the queue.
import type { RunSummary } from '../../api/types';
import { countEpisodes } from '../../lib/decisions';
import { fmtInt, fmtPercent, plural } from '../../lib/format';

export type Verdict =
  /** scored: STOP on every labelled object, no false STOP */
  | { kind: 'ok'; text: string }
  /** scored: a false STOP or a missed object */
  | { kind: 'bad'; text: string }
  /** not scored: STOP episodes of the run (0 = no STOP) */
  | { kind: 'stops'; episodes: number };

const MISSES: readonly [string, string, string] = ['пропуск', 'пропуска', 'пропусков'];

export function runVerdict(s: Pick<RunSummary, 'eval' | 'stop_episodes'>): Verdict {
  const ev = s.eval;
  if (!ev) return { kind: 'stops', episodes: s.stop_episodes };
  const inGauge = ev.frames_with_object_in_gauge;
  const falseEp = ev.false_stop_episodes;
  if (inGauge > 0 && ev.frames_detected === 0) return { kind: 'bad', text: 'объект пропущен' };
  if (falseEp > 0) return { kind: 'bad', text: `ложный СТОП ×${fmtInt(falseEp)}` };
  if (inGauge > 0) {
    const missed = inGauge - ev.frames_detected;
    return {
      kind: 'ok',
      text: missed > 0 ? `верно · ${fmtInt(missed)} ${plural(missed, MISSES)}` : `верно · ${fmtInt(ev.frames_detected)} / ${fmtInt(inGauge)}`,
    };
  }
  return { kind: 'ok', text: '0 ложных' };
}

/** A verdict from a decision string alone (a finished job whose run is not loaded yet). */
export function decisionsVerdict(decisions: string): Verdict {
  return { kind: 'stops', episodes: countEpisodes(decisions, 'STOP') };
}

export type LabelsTag = { kind: 'object' | 'empty' | 'none'; text: string };

/** The «Разметка» cell: what the labels say about the recording. */
export function labelsTag(s: Pick<RunSummary, 'eval'>): LabelsTag {
  const ev = s.eval;
  if (!ev) return { kind: 'none', text: 'нет разметки' };
  if (ev.frames_with_object_in_gauge > 0) return { kind: 'object', text: 'препятствие' };
  return { kind: 'empty', text: 'пусто' };
}

/** "полнота 97 %" of a scored run with objects, else null. */
export function recallText(s: Pick<RunSummary, 'eval'>): string | null {
  const r = s.eval?.recall;
  return typeof r === 'number' ? `полнота ${fmtPercent(r)}` : null;
}
