// Small pieces shared by the analysis pages: the verdict against labels, a checkbox, the decision
// icon tile and skeleton bars.
import type { InputHTMLAttributes } from 'react';
import type { Decision, EvalSummary } from '../../../api/types';
import { DECISION_ICON, Icon } from '../../../components';
import { evalVerdict } from './analysis';
import styles from './Bits.module.css';

/** Detector vs labels as an outlined chip: ✓ «верно · 20 / 24», dashed-red «ложный СТОП ×2», or «нет разметки». */
export function EvalChip({ ev, size = 'md' }: { ev: EvalSummary | null | undefined; size?: 'sm' | 'md' }) {
  const v = evalVerdict(ev);
  if (v.tone === 'none') return <span className={[styles.vd, styles.none, styles[size]].join(' ')}>{v.label}</span>;
  return (
    <span className={[styles.vd, v.tone === 'ok' ? styles.ok : styles.fa, styles[size]].join(' ')}>
      <span className={styles.vi} aria-hidden>
        <Icon name={v.tone === 'ok' ? 'check' : 'stop-octagon'} size={v.tone === 'ok' ? 13 : 18} strokeWidth={v.tone === 'ok' ? 3.2 : 2.4} />
      </span>
      {v.label}
    </span>
  );
}

/** A native checkbox drawn as the mockup's rounded ink check. */
export function Check({ className, ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  return (
    <span className={[styles.check, className].filter(Boolean).join(' ')}>
      <input type="checkbox" {...rest} />
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M5.5 12.5l4 4L18.5 8" />
      </svg>
    </span>
  );
}

/** The rounded square with a decision's icon (events lists). */
export function DecisionTile({ decision, size = 38 }: { decision: Decision; size?: number }) {
  return (
    <span className={[styles.tile, styles[`t-${decision.toLowerCase()}`]].join(' ')} style={{ width: size, height: size }} aria-hidden>
      <Icon name={DECISION_ICON[decision]} size={Math.round(size * 0.53)} strokeWidth={2.4} />
    </span>
  );
}

/** Loading placeholder bars (no text). */
export function Skeleton({ rows = 4, height = 44 }: { rows?: number; height?: number }) {
  return (
    <div className={styles.skel} role="status" aria-label="Загрузка">
      {Array.from({ length: rows }, (_, i) => (
        <span key={i} style={{ height }} />
      ))}
    </div>
  );
}
