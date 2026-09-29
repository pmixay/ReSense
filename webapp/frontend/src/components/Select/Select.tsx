// A select in the mockup's style (well, radius 16, optional icon, chevron) over a native <select>,
// so the keyboard and screen readers behave natively.
import { useId } from 'react';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './Select.module.css';

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SelectProps<T extends string = string> {
  options: readonly SelectOption<T>[];
  value: T;
  onChange: (value: T) => void;
  icon?: IconName;
  label: string;
  /** hides the label visually (it stays the accessible name) */
  hideLabel?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function Select<T extends string = string>({ options, value, onChange, icon, label, hideLabel = true, disabled, placeholder, className }: SelectProps<T>) {
  const id = useId();
  return (
    <div className={[styles.wrap, disabled ? styles.disabled : '', className].filter(Boolean).join(' ')}>
      <label htmlFor={id} className={hideLabel ? 'sr-only' : styles.label}>
        {label}
      </label>
      <div className={styles.select}>
        {icon && <Icon name={icon} size={16} className={styles.icon} />}
        <select
          id={id}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value as T)}
          className={[styles.native, icon ? styles.withIcon : ''].join(' ')}
        >
          {placeholder !== undefined && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>
              {o.label}
            </option>
          ))}
        </select>
        <Icon name="chevron-down" size={16} className={styles.chev} />
      </div>
    </div>
  );
}
