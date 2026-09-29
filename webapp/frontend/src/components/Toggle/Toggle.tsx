// A switch (role="switch"); with `label` it renders the mockup's well row «Облака точек ⬤».
import { useId, type ReactNode } from 'react';
import styles from './Toggle.module.css';

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** visible label; without it pass ariaLabel */
  label?: ReactNode;
  ariaLabel?: string;
  disabled?: boolean;
  /** 'field' = inside a 46 px well row, 'inline' = the bare switch */
  layout?: 'field' | 'inline';
  className?: string;
}

export function Toggle({ checked, onChange, label, ariaLabel, disabled, layout = label ? 'field' : 'inline', className }: ToggleProps) {
  const id = useId();
  const sw = (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label ? undefined : ariaLabel}
      disabled={disabled}
      className={[styles.toggle, checked ? styles.on : ''].join(' ')}
      onClick={() => onChange(!checked)}
    >
      <span className={styles.knob} aria-hidden>
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path d="M6 12.5l4 4L18 8" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </button>
  );
  if (layout === 'inline' || !label) return <span className={className}>{sw}</span>;
  return (
    <label htmlFor={id} className={[styles.field, disabled ? styles.disabled : '', className].filter(Boolean).join(' ')}>
      <span className={styles.text}>{label}</span>
      {sw}
    </label>
  );
}
