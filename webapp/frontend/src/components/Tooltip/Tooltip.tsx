// Tooltip: an ink bubble with an arrow, opened on hover AND keyboard focus (click pins it for touch),
// closed by Escape, pointer-out, blur or a click outside. One tooltip is open per screen. The bubble
// lives in a portal with fixed coordinates so cards with overflow:hidden never clip it; it is always
// in the DOM (hidden when closed) so aria-describedby on the trigger always resolves.
import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
  type ReactElement,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import styles from './Tooltip.module.css';

export type TooltipPlacement =
  | 'top'
  | 'bottom'
  | 'left'
  | 'right'
  | 'top-start'
  | 'top-end'
  | 'bottom-start'
  | 'bottom-end';

// ---- one open tooltip per screen
let current: { close: () => void } | null = null;
function claim(token: { close: () => void }) {
  if (current && current !== token) current.close();
  current = token;
}
function release(token: { close: () => void }) {
  if (current === token) current = null;
}

function isFocusVisible(el: HTMLElement): boolean {
  try {
    return el.matches(':focus-visible');
  } catch {
    return true; // engines without :focus-visible (jsdom): treat focus as keyboard focus
  }
}

const GAP = 10; // anchor ↔ bubble
const EDGE = 8; // viewport margin

interface Pos {
  top: number;
  left: number;
  side: 'top' | 'bottom' | 'left' | 'right';
  arrow: number; // px from the bubble's left (top/bottom) or top (left/right)
}

function computePosition(anchor: DOMRect, bubble: { width: number; height: number }, placement: TooltipPlacement): Pos {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const [base, align] = placement.split('-') as ['top' | 'bottom' | 'left' | 'right', 'start' | 'end' | undefined];
  let side = base;
  // flip when the preferred side has no room
  if (side === 'top' && anchor.top - GAP - bubble.height < EDGE) side = 'bottom';
  else if (side === 'bottom' && anchor.bottom + GAP + bubble.height > vh - EDGE) side = 'top';
  else if (side === 'left' && anchor.left - GAP - bubble.width < EDGE) side = 'right';
  else if (side === 'right' && anchor.right + GAP + bubble.width > vw - EDGE) side = 'left';

  const cx = anchor.left + anchor.width / 2;
  const cy = anchor.top + anchor.height / 2;
  let top: number;
  let left: number;
  if (side === 'top' || side === 'bottom') {
    top = side === 'top' ? anchor.top - GAP - bubble.height : anchor.bottom + GAP;
    if (align === 'start') left = cx - 22;
    else if (align === 'end') left = cx - bubble.width + 22;
    else left = cx - bubble.width / 2;
    left = Math.min(Math.max(left, EDGE), vw - EDGE - bubble.width);
    const arrow = Math.min(Math.max(cx - left, 16), bubble.width - 16);
    return { top, left, side, arrow };
  }
  left = side === 'left' ? anchor.left - GAP - bubble.width : anchor.right + GAP;
  top = Math.min(Math.max(cy - bubble.height / 2, EDGE), vh - EDGE - bubble.height);
  const arrow = Math.min(Math.max(cy - top, 14), bubble.height - 14);
  return { top, left, side, arrow };
}

export interface TooltipProps {
  content: ReactNode;
  /** the trigger: one focusable element (button, link…) */
  children: ReactElement;
  placement?: TooltipPlacement;
  /** px, or 'auto' for a single line; default 250 */
  width?: number | 'auto';
  disabled?: boolean;
  /** open on hover only after this delay (ms) */
  delay?: number;
  /** open once on mount (style guide, onboarding hints) */
  defaultOpen?: boolean;
  className?: string;
}

export function Tooltip({ content, children, placement = 'top', width = 250, disabled, delay = 0, defaultOpen, className }: TooltipProps) {
  const id = useId();
  const anchorRef = useRef<HTMLSpanElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<Pos | null>(null);
  const pinned = useRef(false);
  const hovering = useRef(false);
  const timer = useRef<number | undefined>(undefined);
  const token = useRef<{ close: () => void }>({ close: () => undefined });

  const close = useCallback(() => {
    window.clearTimeout(timer.current);
    pinned.current = false;
    setOpen(false);
    release(token.current);
  }, []);
  token.current.close = close;

  const show = useCallback(() => {
    if (disabled) return;
    window.clearTimeout(timer.current);
    claim(token.current);
    setOpen(true);
  }, [disabled]);

  const scheduleClose = useCallback(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (!pinned.current && !hovering.current) close();
    }, 120);
  }, [close]);

  // position after render, and follow scroll / resize while open
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const a = anchorRef.current?.getBoundingClientRect();
      const b = bubbleRef.current;
      if (!a || !b) return;
      setPos(computePosition(a, { width: b.offsetWidth, height: b.offsetHeight }, placement));
    };
    place();
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [open, placement, content]);

  // Escape anywhere, click outside
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        close();
      }
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!anchorRef.current?.contains(t) && !bubbleRef.current?.contains(t)) close();
    };
    document.addEventListener('keydown', onKey, true);
    document.addEventListener('pointerdown', onDown, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
      document.removeEventListener('pointerdown', onDown, true);
    };
  }, [open, close]);

  useEffect(() => {
    if (defaultOpen) {
      pinned.current = true;
      show();
    }
    const t = token.current;
    return () => {
      window.clearTimeout(timer.current);
      release(t);
    };
  }, []);

  if (!isValidElement(children)) return children;
  const childProps = children.props as Record<string, unknown>;
  const describedBy = [childProps['aria-describedby'], id].filter(Boolean).join(' ');
  const trigger = cloneElement(children as ReactElement<Record<string, unknown>>, {
    'aria-describedby': disabled ? childProps['aria-describedby'] : describedBy,
    'data-tip-open': open ? 'true' : undefined,
    onClick: (e: ReactMouseEvent) => {
      (childProps.onClick as ((e: ReactMouseEvent) => void) | undefined)?.(e);
      if (e.defaultPrevented || disabled) return;
      if (open && pinned.current) close();
      else {
        pinned.current = true;
        show();
      }
    },
  });

  const bubbleStyle: CSSProperties = {
    width: width === 'auto' ? 'max-content' : width,
    maxWidth: width === 'auto' ? 360 : undefined,
    top: pos?.top ?? -9999,
    left: pos?.left ?? -9999,
    ['--arrow' as string]: `${pos?.arrow ?? 0}px`,
    visibility: open && pos ? 'visible' : 'hidden',
  };

  return (
    <span
      ref={anchorRef}
      className={[styles.anchor, className].filter(Boolean).join(' ')}
      onMouseEnter={() => {
        hovering.current = true;
        if (delay) timer.current = window.setTimeout(show, delay);
        else show();
      }}
      onMouseLeave={() => {
        hovering.current = false;
        scheduleClose();
      }}
      onFocus={(e) => {
        // keyboard focus only; a mouse click focuses too but is handled by onClick
        if (isFocusVisible(e.target as HTMLElement)) show();
      }}
      onBlur={() => {
        pinned.current = false;
        scheduleClose();
      }}
    >
      {trigger}
      {typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={bubbleRef}
            id={id}
            role="tooltip"
            hidden={!open}
            className={styles.bubble}
            data-side={pos?.side ?? 'top'}
            style={bubbleStyle}
            onMouseEnter={() => {
              hovering.current = true;
              window.clearTimeout(timer.current);
            }}
            onMouseLeave={() => {
              hovering.current = false;
              scheduleClose();
            }}
          >
            {content}
          </div>,
          document.body,
        )}
    </span>
  );
}
