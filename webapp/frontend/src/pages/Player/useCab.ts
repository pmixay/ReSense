// Small hooks of the cab: the 1600×1000 composition scaled to fit the viewport, the Fullscreen API
// with a fallback when the browser refuses it, and the player's keyboard map.
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

export const STAGE_W = 1600;
export const STAGE_H = 1000;

const fitScale = (): number =>
  typeof window === 'undefined' ? 1 : Math.max(0.3, Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H));

/** Scale of the fixed 1600×1000 cab so it fits the window (both ways, letterboxed). */
export function useStageScale(): number {
  const [k, setK] = useState(fitScale);
  useEffect(() => {
    const on = () => setK(fitScale());
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return k;
}

/** Fullscreen on an element; when the browser refuses (iframe, policy), a "pseudo" mode instead. */
export function useFullscreen(ref: RefObject<HTMLElement>) {
  const [real, setReal] = useState(false);
  const [pseudo, setPseudo] = useState(false);

  useEffect(() => {
    const on = () => setReal(!!document.fullscreenElement && document.fullscreenElement === ref.current);
    document.addEventListener('fullscreenchange', on);
    return () => document.removeEventListener('fullscreenchange', on);
  }, [ref]);

  const enter = useCallback(async () => {
    const el = ref.current;
    if (el && typeof el.requestFullscreen === 'function' && document.fullscreenEnabled !== false) {
      try {
        await el.requestFullscreen();
        return;
      } catch {
        // refused: fall through to the pseudo mode
      }
    }
    setPseudo(true);
  }, [ref]);

  const exit = useCallback(async () => {
    setPseudo(false);
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch {
        // already left
      }
    }
  }, []);

  const active = real || pseudo;
  const toggle = useCallback(() => void (active ? exit() : enter()), [active, enter, exit]);
  return { active, real, pseudo, toggle, exit };
}

export interface PlayerKeys {
  toggle(): void;
  step(delta: number): void;
  prevEvent(): void;
  nextEvent(): void;
  camera(index: number): void;
  fullscreen(): void;
  speed(dir: 1 | -1): void;
  escape(): void;
}

/** A key's action, or null when this screen does not use it (the key keeps its default then). */
export function keyAction(code: string, shift: boolean, k: Partial<PlayerKeys>): (() => void) | null {
  const on = <A extends unknown[]>(fn: ((...a: A) => void) | undefined, ...args: A) => (fn ? () => fn(...args) : null);
  switch (code) {
    case 'Space':
      return on(k.toggle);
    case 'ArrowLeft':
      return on(k.step, shift ? -10 : -1);
    case 'ArrowRight':
      return on(k.step, shift ? 10 : 1);
    case 'BracketLeft':
      return on(k.prevEvent);
    case 'BracketRight':
      return on(k.nextEvent);
    case 'Digit1':
    case 'Numpad1':
      return on(k.camera, 0);
    case 'Digit2':
    case 'Numpad2':
      return on(k.camera, 1);
    case 'Digit3':
    case 'Numpad3':
      return on(k.camera, 2);
    case 'KeyF':
      return on(k.fullscreen);
    case 'Equal':
    case 'NumpadAdd':
      return on(k.speed, 1);
    case 'Minus':
    case 'NumpadSubtract':
      return on(k.speed, -1);
    case 'Escape':
      return on(k.escape);
    default:
      return null;
  }
}

/** The player's keyboard map (layout-independent key codes, so a Russian layout works too). A screen
 *  passes only the keys it uses: the others keep their default (Space on a focused button, arrows
 *  scrolling a list). */
export function usePlayerKeys(keys: Partial<PlayerKeys>, enabled = true): void {
  const ref = useRef(keys);
  ref.current = keys;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
      const el = e.target instanceof HTMLElement ? e.target : null;
      if (el?.closest('input, textarea, select, [contenteditable="true"]')) return;
      const act = keyAction(e.code, e.shiftKey, ref.current);
      if (!act) return;
      e.preventDefault();
      act();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
}
