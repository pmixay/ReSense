import styles from './Spinner.module.css';

export interface SpinnerProps {
  size?: number;
  /** 'ink' on light surfaces, 'light' on ink / red */
  tone?: 'ink' | 'light';
  label?: string;
  className?: string;
}

export function Spinner({ size = 20, tone = 'ink', label = 'Загрузка', className }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={[styles.spinner, tone === 'light' ? styles.light : '', className].filter(Boolean).join(' ')}
      style={{ width: size, height: size, borderWidth: Math.max(2, Math.round(size / 8)) }}
    />
  );
}
