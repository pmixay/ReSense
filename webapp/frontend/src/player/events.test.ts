import { describe, expect, it } from 'vitest';
import type { Episode } from '../api/types';
import { eventAt, eventMarks, nextEventPos, posOfFrame, prevEventPos } from './events';

const ep = (decision: Episode['decision'], first: number, last: number): Episode => ({ decision, first_frame: first, last_frame: last }) as Episode;

describe('posOfFrame', () => {
  it('is the identity without a frame list', () => {
    expect(posOfFrame(null, 12)).toBe(12);
    expect(posOfFrame([], 3.4)).toBe(3);
    expect(posOfFrame(undefined, -2)).toBe(0);
  });

  it('finds the first position at or after a bag frame index', () => {
    const frames = [0, 2, 4, 6, 8, 10];
    expect(posOfFrame(frames, 0)).toBe(0);
    expect(posOfFrame(frames, 4)).toBe(2);
    expect(posOfFrame(frames, 5)).toBe(3);
    expect(posOfFrame(frames, 10)).toBe(5);
    expect(posOfFrame(frames, 99)).toBe(5);
  });
});

describe('eventMarks', () => {
  it('maps events to sorted positions', () => {
    const marks = eventMarks([ep('CAUTION', 40, 42), ep('STOP', 4, 30), ep('GO', 31, 33)], null);
    expect(marks.map((m) => [m.pos, m.endPos, m.decision, m.frame])).toEqual([
      [4, 30, 'STOP', 4],
      [31, 33, 'GO', 31],
      [40, 42, 'CAUTION', 40],
    ]);
  });

  it('keeps the more severe event when two start at the same position', () => {
    const marks = eventMarks([ep('CAUTION', 10, 12), ep('STOP', 10, 20), ep('FAULT', 10, 11)], null);
    expect(marks).toHaveLength(1);
    expect(marks[0].decision).toBe('STOP');
    expect(marks[0].endPos).toBe(20);
  });

  it('uses the processed order of a run that skipped frames', () => {
    const marks = eventMarks([ep('STOP', 20, 40)], [0, 10, 20, 30, 40, 50]);
    expect(marks[0].pos).toBe(2);
    expect(marks[0].endPos).toBe(4);
    expect(marks[0].frame).toBe(20);
  });

  it('is empty without events', () => {
    expect(eventMarks(null)).toEqual([]);
    expect(eventMarks([])).toEqual([]);
  });
});

describe('event navigation', () => {
  const marks = eventMarks([ep('STOP', 10, 20), ep('GO', 21, 23), ep('CAUTION', 50, 55)], null);

  it('jumps to the next event start after the playhead', () => {
    expect(nextEventPos(marks, 0)).toBe(10);
    expect(nextEventPos(marks, 10)).toBe(21);
    expect(nextEventPos(marks, 30)).toBe(50);
    expect(nextEventPos(marks, 50)).toBeNull();
  });

  it('jumps to the start of the event before the playhead (inside an event: its own start)', () => {
    expect(prevEventPos(marks, 60)).toBe(50);
    expect(prevEventPos(marks, 52)).toBe(50);
    expect(prevEventPos(marks, 50)).toBe(21);
    expect(prevEventPos(marks, 15)).toBe(10);
    expect(prevEventPos(marks, 10)).toBeNull();
  });

  it('finds the event covering a position', () => {
    expect(eventAt(marks, 15)?.decision).toBe('STOP');
    expect(eventAt(marks, 22)?.decision).toBe('GO');
    expect(eventAt(marks, 30)).toBeNull();
  });
});
