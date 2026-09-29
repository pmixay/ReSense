import { describe, expect, it, vi } from 'vitest';
import { laneStep } from './Scrubber';
import { keyAction } from './useCab';

const key = (k: string, mods: { shiftKey?: boolean; altKey?: boolean; ctrlKey?: boolean; metaKey?: boolean } = {}) => ({
  key: k,
  shiftKey: false,
  altKey: false,
  ctrlKey: false,
  metaKey: false,
  ...mods,
});

describe('laneStep', () => {
  it('keeps ←/→ (and Shift ±10) on the focused scrubber the same as everywhere in the player', () => {
    expect(laneStep(key('ArrowRight'))).toBe(1);
    expect(laneStep(key('ArrowLeft'))).toBe(-1);
    expect(laneStep(key('ArrowRight', { shiftKey: true }))).toBe(10);
    expect(laneStep(key('ArrowLeft', { shiftKey: true }))).toBe(-10);
  });

  it('leaves the slider its own keys and modified arrows to the browser', () => {
    for (const k of ['Home', 'End', 'PageUp', 'PageDown', 'ArrowUp', 'ArrowDown', ' ']) expect(laneStep(key(k))).toBeNull();
    expect(laneStep(key('ArrowLeft', { altKey: true }))).toBeNull();
    expect(laneStep(key('ArrowRight', { metaKey: true }))).toBeNull();
  });
});

describe('keyAction', () => {
  it('maps layout-independent codes to the player actions', () => {
    const step = vi.fn();
    const camera = vi.fn();
    const speed = vi.fn();
    keyAction('ArrowRight', true, { step })?.();
    keyAction('ArrowLeft', false, { step })?.();
    keyAction('Digit3', false, { camera })?.();
    keyAction('NumpadSubtract', false, { speed })?.();
    expect(step.mock.calls).toEqual([[10], [-1]]);
    expect(camera).toHaveBeenCalledWith(2);
    expect(speed).toHaveBeenCalledWith(-1);
  });

  it('leaves keys the screen does not use to the browser', () => {
    // the run picker only knows F and Esc: Space still presses a focused button, arrows scroll
    const keys = { fullscreen: vi.fn(), escape: vi.fn() };
    expect(keyAction('Space', false, keys)).toBeNull();
    expect(keyAction('ArrowDown', false, keys)).toBeNull();
    expect(keyAction('KeyQ', false, keys)).toBeNull();
    keyAction('KeyF', false, keys)?.();
    keyAction('Escape', false, keys)?.();
    expect(keys.fullscreen).toHaveBeenCalledOnce();
    expect(keys.escape).toHaveBeenCalledOnce();
  });
});
