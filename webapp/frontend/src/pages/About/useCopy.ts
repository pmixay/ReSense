import { useCallback, useEffect, useRef, useState } from 'react';

/** Copies text: the async Clipboard API, else a hidden textarea + execCommand (plain http on a
 *  LAN address is not a secure context, where navigator.clipboard is missing). */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall back below */
  }
  if (typeof document === 'undefined') return false;
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  ta.style.pointerEvents = 'none';
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = typeof document.execCommand === 'function' && document.execCommand('copy');
  } catch {
    ok = false;
  }
  ta.remove();
  return ok;
}

export type CopyState = 'idle' | 'copied' | 'failed';

/** [state, copy]: the state shows «скопировано» / «не удалось» for `resetMs`, then returns to idle. */
export function useCopy(resetMs = 1600): [CopyState, (text: string) => void] {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);
  const copy = useCallback(
    (text: string) => {
      void copyText(text).then((ok) => {
        if (!alive.current) return; // the card is gone: no state, no timer
        setState(ok ? 'copied' : 'failed');
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(() => setState('idle'), resetMs);
      });
    },
    [resetMs],
  );
  return [state, copy];
}
