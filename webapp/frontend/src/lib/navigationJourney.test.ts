import { describe, expect, it } from 'vitest';
import { navigationJourney } from './navigationJourney';
import { LINE, BRANCH, PAGES } from './nav';

describe('station-ordered page journeys', () => {
  it.each([
    ['/queue', '/player', 'right', ['runs']],
    ['/player/run-a', '/queue', 'left', ['runs']],
    ['/', '/compare', 'right', ['upload', 'queue', 'runs', 'player']],
    ['/about', '/queue', 'left', ['presets', 'live', 'compare', 'player', 'runs']],
    ['/queue', '/runs/run-a', 'right', []],
    ['/runs', '/queue', 'left', []],
  ])('orders every intervening page from %s to %s', (from, to, direction, via) => {
    const journey = navigationJourney(from, to);
    expect(journey.direction).toBe(direction);
    expect(journey.via).toEqual(via);
    expect(journey.steps).toBe(via.length + 1);
    expect(journey.duration).toBeGreaterThanOrEqual(410);
    expect(journey.duration).toBeLessThanOrEqual(1320);
  });
  it('has no travel within a section and handles off-rail routes', () => {
    expect(navigationJourney('/player/a', '/player/b')).toMatchObject({ steps: 0, via: [], duration: 0 });
    expect(navigationJourney('/unknown', '/runs')).toMatchObject({ steps: 1, via: [], direction: 'right' });
  });
  it('includes every station exactly once in both directions for all tab pairs', () => {
    const layout = [...LINE, ...BRANCH];
    for (let a = 0; a < layout.length; a++) for (let b = 0; b < layout.length; b++) {
      if (a === b) continue;
      const journey = navigationJourney(PAGES[layout[a]].path, PAGES[layout[b]].path);
      const actual = [layout[a], ...journey.via, journey.target];
      expect(actual).toHaveLength(Math.abs(b - a) + 1);
      for (let i = 0; i < actual.length; i++) expect(actual[i]).toBe(layout[a + i * Math.sign(b - a)]);
    }
  });
});
