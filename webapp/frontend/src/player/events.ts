// Event navigation of the player: the run's events (non-GO episodes and GO gaps inside STOP, as bag
// frame indices) mapped to processed positions, and the previous / next event of a playhead.
import type { Decision, Episode } from '../api/types';

export interface EventMark {
  /** processed-order position of the event's first frame */
  pos: number;
  /** position of its last frame */
  endPos: number;
  decision: Decision;
  /** bag frame index of the first frame (labels) */
  frame: number;
}

/** Position of a bag frame index in processed order (the first position at or after it). */
export function posOfFrame(frames: readonly number[] | null | undefined, frame: number): number {
  if (!frames || frames.length === 0) return Math.max(0, Math.round(frame));
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid] < frame) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** Events as positions, sorted, one per start position (the more severe one wins a tie). */
export function eventMarks(events: readonly Episode[] | null | undefined, frames?: readonly number[] | null): EventMark[] {
  if (!events?.length) return [];
  const rank: Record<Decision, number> = { GO: 0, CAUTION: 1, FAULT: 2, STOP: 3 };
  const byPos = new Map<number, EventMark>();
  for (const e of events) {
    const pos = posOfFrame(frames, e.first_frame);
    const endPos = Math.max(pos, posOfFrame(frames, e.last_frame));
    const prev = byPos.get(pos);
    if (!prev || rank[e.decision] > rank[prev.decision]) byPos.set(pos, { pos, endPos, decision: e.decision, frame: e.first_frame });
  }
  return [...byPos.values()].sort((a, b) => a.pos - b.pos);
}

/** Start of the first event after `pos` (null when none). */
export function nextEventPos(marks: readonly EventMark[], pos: number): number | null {
  for (const m of marks) if (m.pos > pos) return m.pos;
  return null;
}

/** Start of the last event before `pos`: inside an event this is its own start (null when none). */
export function prevEventPos(marks: readonly EventMark[], pos: number): number | null {
  for (let i = marks.length - 1; i >= 0; i -= 1) if (marks[i].pos < pos) return marks[i].pos;
  return null;
}

/** The event covering `pos` (null outside events). */
export function eventAt(marks: readonly EventMark[], pos: number): EventMark | null {
  for (const m of marks) if (m.pos <= pos && pos <= m.endPos) return m;
  return null;
}
