// A popover menu behind a round "⋯" button (rename / delete of a run). Arrow keys move between the
// items, Escape and a click outside close it. The list lives in a portal with fixed coordinates so
// scrolling tables and cards with overflow never clip it.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { Icon, IconButton, type IconButtonProps, type IconName } from '../../../components';
import styles from './Menu.module.css';

export interface MenuItem {
  label: string;
  icon: IconName;
  onSelect: () => void;
  disabled?: boolean;
}

export interface MenuProps {
  items: readonly MenuItem[];
  label?: string;
  size?: IconButtonProps['size'];
  variant?: IconButtonProps['variant'];
  icon?: IconName;
}

const WIDTH = 220;

export function Menu({ items, label = 'Действия', size = 'md', variant = 'well', icon = 'more' }: MenuProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const anchor = useRef<HTMLSpanElement>(null);
  const list = useRef<HTMLDivElement>(null);

  const close = useCallback((refocus = false) => {
    setOpen(false);
    if (refocus) anchor.current?.querySelector('button')?.focus();
  }, []);

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const r = anchor.current?.getBoundingClientRect();
      if (!r) return;
      const h = list.current?.offsetHeight ?? 120;
      const below = r.bottom + 8 + h < window.innerHeight - 8;
      setPos({
        top: below ? r.bottom + 8 : r.top - 8 - h,
        left: Math.min(Math.max(8, r.right - WIDTH), window.innerWidth - WIDTH - 8),
      });
    };
    place();
    list.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!anchor.current?.contains(t) && !list.current?.contains(t)) close();
    };
    document.addEventListener('pointerdown', onDown, true);
    return () => document.removeEventListener('pointerdown', onDown, true);
  }, [open, close]);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const buttons = [...(list.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])];
    const i = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === 'Escape' || e.key === 'Tab') {
      e.preventDefault();
      e.stopPropagation();
      close(true);
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const next = (i + (e.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[next]?.focus();
    }
  };

  return (
    <span ref={anchor} className={styles.anchor}>
      <IconButton
        icon={icon}
        label={label}
        size={size}
        variant={variant}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
      />
      {open &&
        createPortal(
          <div
            ref={list}
            role="menu"
            aria-label={label}
            className={styles.menu}
            style={{ width: WIDTH, top: pos?.top ?? -9999, left: pos?.left ?? -9999, visibility: pos ? 'visible' : 'hidden' }}
            onKeyDown={onKey}
          >
            {items.map((it) => (
              <button
                key={it.label}
                type="button"
                role="menuitem"
                className={styles.item}
                disabled={it.disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  close();
                  it.onSelect();
                }}
              >
                <span className={styles.ic}>
                  <Icon name={it.icon} size={16} />
                </span>
                {it.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </span>
  );
}
