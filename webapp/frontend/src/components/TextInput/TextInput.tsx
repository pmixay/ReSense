// Text input (well, radius 12) and Field: a label row with an optional "?" above any control.
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from 'react';
import { Help } from '../Help/Help';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './TextInput.module.css';

export interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  icon?: IconName;
  /** text after the value ("м", "с") */
  suffix?: ReactNode;
  invalid?: boolean;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput({ icon, suffix, invalid, className, ...rest }, ref) {
  return (
    <div className={[styles.input, invalid ? styles.invalid : '', rest.disabled ? styles.disabled : '', className].filter(Boolean).join(' ')}>
      {icon && <Icon name={icon} size={16} />}
      <input ref={ref} className={styles.native} aria-invalid={invalid || undefined} {...rest} />
      {suffix && <span className={styles.suffix}>{suffix}</span>}
    </div>
  );
});

export interface FieldProps {
  label: ReactNode;
  help?: ReactNode;
  /** id of the control, for <label htmlFor>; a generated id is passed to render-prop children */
  htmlFor?: string;
  error?: ReactNode;
  children: ReactNode | ((id: string) => ReactNode);
  className?: string;
}

export function Field({ label, help, htmlFor, error, children, className }: FieldProps) {
  const gen = useId();
  const id = htmlFor ?? gen;
  return (
    <div className={[styles.field, className].filter(Boolean).join(' ')}>
      <div className={styles.fl}>
        <label htmlFor={id}>{label}</label>
        {help !== undefined && <Help>{help}</Help>}
      </div>
      {typeof children === 'function' ? children(id) : children}
      {error && <div className={styles.error}>{error}</div>}
    </div>
  );
}
