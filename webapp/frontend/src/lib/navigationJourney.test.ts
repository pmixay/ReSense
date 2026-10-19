import { describe, expect, it } from 'vitest';
import { navigationJourney } from './navigationJourney';

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
    expect(journey.duration).toBeGreaterThanOrEqual(650);
    expect(journey.duration).toBeLessThanOrEqual(1700);
  });
  it('has no travel within a section and handles off-rail routes', () => {
    expect(navigationJourney('/player/a', '/player/b')).toMatchObject({ steps: 0, via: [], duration: 0 });
    expect(navigationJourney('/unknown', '/runs')).toMatchObject({ steps: 1, via: [], direction: 'right' });
  });
});
