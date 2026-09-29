// A small modal dialog (rename, confirm delete): a portal over a dimmed page, Escape / backdrop
// close it, focus moves in on open and back to the trigger on close.
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import styles from './Dialog.module.css';

export interface DialogProps {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  children?: ReactNode;
  actions?: ReactNode;
  /** CSS selector of the element to focus first (default: the first input, else the first button) */
  initialFocus?: string;
}

export function Dialog({ open, title, onClose, children, actions, initialFocus }: DialogProps) {
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const back = document.activeElement as HTMLElement | null;
    const el = box.current;
    const first = el?.querySelector<HTMLElement>(initialFocus ?? 'input, button[data-autofocus], button');
    first?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        closeRef.current();
      } else if (e.key === 'Tab' && el) {
        // keep Tab inside the dialog
        const items = [...el.querySelectorAll<HTMLElement>('button:not(:disabled), input, a[href]')];
        if (!items.length) return;
        const i = items.indexOf(document.activeElement as HTMLElement);
        if (e.shiftKey && i <= 0) {
          e.preventDefault();
          items[items.length - 1].focus();
        } else if (!e.shiftKey && i === items.length - 1) {
          e.preventDefault();
          items[0].focus();
        }
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
      back?.focus?.();
    };
  }, [open, initialFocus]);

  if (!open || typeof document === 'undefined') return null;
  return createPortal(
    <div className={styles.backdrop} onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={box} className={styles.box} role="dialog" aria-modal="true" aria-labelledby={id}>
        <h2 id={id} className={styles.title}>
          {title}
        </h2>
        {children && <div className={styles.body}>{children}</div>}
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
    </div>,
    document.body,
  );
}
