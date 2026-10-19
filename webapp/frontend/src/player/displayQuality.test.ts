import { describe, expect, it } from 'vitest';
import { displayPixelRatio } from './displayQuality';

describe('physical scene resolution budget', () => {
  it('bounds high-DPI raster cost independently of readable DOM controls', () => {
    for (const [width, height] of [[1440, 844], [1920, 1024], [2560, 1440], [3840, 2160]]) {
      const ratio = displayPixelRatio(width, height, 3);
      expect(ratio).toBeLessThanOrEqual(1.5);
      expect(width * height * ratio * ratio).toBeLessThanOrEqual(2_600_001);
      expect(displayPixelRatio(width, height, 3, true)).toBeLessThanOrEqual(1);
    }
    expect(displayPixelRatio(1366, 768, 1)).toBe(1);
  });
});
