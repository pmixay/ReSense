// Segmented control (a radio group): well track, the chosen option in ink. Arrow keys move the choice.
import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './Segmented.module.css';

export interface SegmentedOption<T extends string> {
  value: T;
  label: ReactNode;
  icon?: IconName;
  disabled?: boolean;
  /** accessible name when the label is an icon only */
  ariaLabel?: string;
}

export interface SegmentedProps<T extends string> {
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  size?: 'sm' | 'md';
  /** 'white' track for use inside wells */
  tone?: 'well' | 'white';
  label: string;
  className?: string;
}

export function Segmented<T extends string>({ options, value, onChange, size = 'md', tone = 'well', label, className }: SegmentedProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0);

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const dir = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    let target = -1;
    if (dir) {
      const at = enabled.indexOf(i);
      target = enabled[(at + dir + enabled.length) % enabled.length];
    } else if (e.key === 'Home') target = enabled[0];
    else if (e.key === 'End') target = enabled[enabled.length - 1];
    if (target < 0 || target === undefined) return;
    e.preventDefault();
    onChange(options[target].value);
    refs.current[target]?.focus();
  };

  return (
    <div role="radiogroup" aria-label={label} className={[styles.seg, styles[size], styles[tone], className].filter(Boolean).join(' ')}>
      {options.map((o, i) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={o.ariaLabel}
            tabIndex={on ? 0 : -1}
            disabled={o.disabled}
            className={[styles.o, on ? styles.on : ''].join(' ')}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKey(e, i)}
          >
            {o.icon && <Icon name={o.icon} size={16} />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
