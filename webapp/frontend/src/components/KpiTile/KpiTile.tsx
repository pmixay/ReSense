// KPI tile: a label (+ icon, + "?"), a big Benzin value with a small unit, one sub-line; an optional
// visual on top. Variants: light (white), dark (ink), green (a good result).
import type { ReactNode } from 'react';
import { Help } from '../Help/Help';
import type { TooltipPlacement } from '../Tooltip/Tooltip';
import styles from './KpiTile.module.css';

export interface KpiTileProps {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  sub?: ReactNode;
  help?: ReactNode;
  helpPlacement?: TooltipPlacement;
  icon?: ReactNode;
  /** small visual above the label (sparkline, bars…) */
  viz?: ReactNode;
  /** after the value (e.g. a check badge) */
  after?: ReactNode;
  variant?: 'light' | 'dark' | 'green';
  size?: 'md' | 'lg';
  className?: string;
}

export function KpiTile({ label, value, unit, sub, help, helpPlacement = 'bottom', icon, viz, after, variant = 'light', size = 'md', className }: KpiTileProps) {
  return (
    <div className={[styles.kpi, styles[variant], styles[size], className].filter(Boolean).join(' ')}>
      {viz && <div className={styles.viz}>{viz}</div>}
      <div className={[styles.label, viz ? styles.labelLow : ''].join(' ')}>
        {icon}
        <span className={styles.labelText}>{label}</span>
        {help !== undefined && (
          <Help placement={helpPlacement} tone={variant === 'dark' ? 'light' : 'dark'}>
            {help}
          </Help>
        )}
      </div>
      <div className={styles.value}>
        {value}
        {unit !== undefined && <small>{unit}</small>}
        {after}
      </div>
      {sub !== undefined && <div className={styles.sub}>{sub}</div>}
    </div>
  );
}

/** The small hatched STOP roundel used before KPI labels. */
export function StopMark() {
  return (
    <span className={styles.stopMark} aria-hidden>
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2z" />
        <path d="M8 12h8" strokeWidth="2.8" />
      </svg>
    </span>
  );
}

/** Round green check after a good value. */
export function GoodMark() {
  return (
    <span className={styles.goodMark} aria-hidden>
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12.5l4.5 4.5L19 7.5" />
      </svg>
    </span>
  );
}
