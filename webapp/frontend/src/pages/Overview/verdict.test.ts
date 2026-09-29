import { describe, expect, it } from 'vitest';
import type { EvalSummary, RunSummary } from '../../api/types';
import { decisionsVerdict, labelsTag, recallText, runVerdict } from './verdict';

const ev = (e: Partial<EvalSummary>): EvalSummary => ({
  labels_name: 'gt',
  frames_labelled: 100,
  frames_with_object_in_gauge: 0,
  frames_detected: 0,
  recall: null,
  false_stop_frames: 0,
  false_stop_episodes: 0,
  first_detection_distance: null,
  raw: {},
  ...e,
});
const summary = (e: EvalSummary | null, stop_episodes = 0) => ({ eval: e, stop_episodes }) as Pick<RunSummary, 'eval' | 'stop_episodes'>;

describe('runVerdict', () => {
  it('without labels: the STOP episodes', () => {
    expect(runVerdict(summary(null, 3))).toEqual({ kind: 'stops', episodes: 3 });
    expect(runVerdict(summary(null, 0))).toEqual({ kind: 'stops', episodes: 0 });
  });
  it('an object answered with STOP: correct, with the missed frames', () => {
    expect(runVerdict(summary(ev({ frames_with_object_in_gauge: 120, frames_detected: 116, recall: 116 / 120 })))).toEqual({
      kind: 'ok',
      text: 'верно · 4 пропуска',
    });
    expect(runVerdict(summary(ev({ frames_with_object_in_gauge: 8, frames_detected: 8, recall: 1 })))).toEqual({ kind: 'ok', text: 'верно · 8 / 8' });
    expect(runVerdict(summary(ev({ frames_with_object_in_gauge: 30, frames_detected: 29 })))).toEqual({ kind: 'ok', text: 'верно · 1 пропуск' });
  });
  it('a missed object, then false STOP, outrank a correct answer', () => {
    expect(runVerdict(summary(ev({ frames_with_object_in_gauge: 10, frames_detected: 0, false_stop_episodes: 2 })))).toEqual({ kind: 'bad', text: 'объект пропущен' });
    expect(runVerdict(summary(ev({ frames_with_object_in_gauge: 24, frames_detected: 20, false_stop_episodes: 1 })))).toEqual({ kind: 'bad', text: 'ложный СТОП ×1' });
    expect(runVerdict(summary(ev({ false_stop_episodes: 30 })))).toEqual({ kind: 'bad', text: 'ложный СТОП ×30' });
  });
  it('an empty track without STOP', () => {
    expect(runVerdict(summary(ev({})))).toEqual({ kind: 'ok', text: '0 ложных' });
  });
});

describe('labels tag, recall, decision strings', () => {
  it('says what the labels hold', () => {
    expect(labelsTag(summary(null))).toEqual({ kind: 'none', text: 'нет разметки' });
    expect(labelsTag(summary(ev({ frames_with_object_in_gauge: 3 })))).toEqual({ kind: 'object', text: 'препятствие' });
    expect(labelsTag(summary(ev({})))).toEqual({ kind: 'empty', text: 'пусто' });
  });
  it('formats the recall in Russian', () => {
    expect(recallText(summary(ev({ recall: 0.9666 })))?.replace(/\u00a0/g, ' ')).toBe('полнота 97 %');
    expect(recallText(summary(null))).toBeNull();
  });
  it('counts STOP episodes of a decision string', () => {
    expect(decisionsVerdict('GGSSGCSSG')).toEqual({ kind: 'stops', episodes: 2 });
    expect(decisionsVerdict('')).toEqual({ kind: 'stops', episodes: 0 });
  });
});
