import { useLayoutEffect, useRef, useState, type RefObject } from 'react';

/** The content box of an element (ResizeObserver), for SVG drawn in real pixels. */
export function useSize<T extends HTMLElement>(): [RefObject<T>, number, number] {
  const ref = useRef<T>(null);
  const [size, setSize] = useState<[number, number]>([0, 0]);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setSize([el.clientWidth, el.clientHeight]);
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      const next: [number, number] = [Math.round(r.width), Math.round(r.height)];
      setSize((prev) => (prev[0] === next[0] && prev[1] === next[1] ? prev : next));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, size[0], size[1]];
}
