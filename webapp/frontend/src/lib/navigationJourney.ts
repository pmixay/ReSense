import { BRANCH, LINE, pageOfPath, type PageKey } from './nav';

export interface NavigationJourney {
  direction: 'left' | 'right';
  via: PageKey[];
  target: PageKey | null;
  steps: number;
  duration: number;
}

/** Follow the same spatial order as the visible station rail and its system branch. */
export function navigationJourney(from: string, to: string): NavigationJourney {
  const order = [...LINE, ...BRANCH];
  const a = order.indexOf(pageOfPath(from)!);
  const target = pageOfPath(to);
  const b = order.indexOf(target!);
  const steps = a >= 0 && b >= 0 ? Math.abs(b - a) : 1;
  const direction = a >= 0 && b >= 0 && b < a ? 'left' : 'right';
  const via = a < 0 || b < 0 ? [] : order.slice(Math.min(a, b) + 1, Math.max(a, b));
  if (direction === 'left') via.reverse();
  return { direction, via, target, steps, duration: steps ? 280 + steps * 130 : 0 };
}
