// Numeric stepper: − value + in a well; the value is also typeable. ArrowUp / ArrowDown step.
import { useEffect, useState } from 'react';
import { fmtNum } from '../../lib/format';
import { Icon } from '../Icon/Icon';
import styles from './Stepper.module.css';

export interface StepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /** decimals shown */
  digits?: number;
  unit?: string;
  label: string;
  disabled?: boolean;
  className?: string;
}

const parse = (s: string) => Number(s.replace(/\s| | /g, '').replace(',', '.').replace('−', '-'));

export function Stepper({ value, onChange, min = -Infinity, max = Infinity, step = 1, digits = 0, unit, label, disabled, className }: StepperProps) {
  const [text, setText] = useState(fmtNum(value, digits));
  useEffect(() => setText(fmtNum(value, digits)), [value, digits]);

  const clamp = (v: number) => {
    const r = Math.round(v / step) * step;
    return Math.min(max, Math.max(min, Number(r.toFixed(Math.max(digits, 6)))));
  };
  const commit = (v: number) => {
    if (!Number.isFinite(v)) {
      setText(fmtNum(value, digits));
      return;
    }
    const c = clamp(v);
    setText(fmtNum(c, digits));
    if (c !== value) onChange(c);
  };

  return (
    <div className={[styles.stepper, disabled ? styles.disabled : '', className].filter(Boolean).join(' ')}>
      <button type="button" className={styles.sb} aria-label={`${label}: меньше`} disabled={disabled || value <= min} onClick={() => commit(value - step)}>
        <Icon name="minus" size={16} strokeWidth={2.6} />
      </button>
      <span className={styles.val}>
        <input
          className={styles.input}
          value={text}
          inputMode="decimal"
          aria-label={label}
          role="spinbutton"
          aria-valuenow={value}
          aria-valuemin={Number.isFinite(min) ? min : undefined}
          aria-valuemax={Number.isFinite(max) ? max : undefined}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => commit(parse(text))}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit(parse(text));
            else if (e.key === 'ArrowUp') {
              e.preventDefault();
              commit(value + step);
            } else if (e.key === 'ArrowDown') {
              e.preventDefault();
              commit(value - step);
            }
          }}
          style={{ width: `${Math.max(2, text.length + 0.5)}ch` }}
        />
        {unit && <span className={styles.unit}>{unit}</span>}
      </span>
      <button type="button" className={styles.sb} aria-label={`${label}: больше`} disabled={disabled || value >= max} onClick={() => commit(value + step)}>
        <Icon name="plus" size={16} strokeWidth={2.6} />
      </button>
    </div>
  );
}
