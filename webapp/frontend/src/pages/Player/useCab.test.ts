import { describe, expect, it, vi } from 'vitest';
import { keyAction } from './useCab';

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
