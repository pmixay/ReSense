// Neutral progress (ink on a well): value 0..1, or null for an indeterminate stripe.
import styles from './ProgressBar.module.css';

export interface ProgressBarProps {
  value: number | null;
  height?: number;
  /** track colour: 'well' on white cards, 'white' inside wells */
  track?: 'well' | 'white' | 'glass';
  label?: string;
  className?: string;
}

export function ProgressBar({ value, height = 12, track = 'well', label = 'Прогресс', className }: ProgressBarProps) {
  const v = value === null ? null : Math.min(1, Math.max(0, value));
  return (
    <div
      className={[styles.bar, styles[track], className].filter(Boolean).join(' ')}
      style={{ height, borderRadius: height / 2 }}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={v === null ? undefined : Math.round(v * 100)}
    >
      {v === null ? (
        <span className={styles.indeterminate} style={{ borderRadius: height / 2 }} />
      ) : (
        <span className={styles.fill} style={{ width: `${v * 100}%`, borderRadius: height / 2 }} />
      )}
    </div>
  );
}
