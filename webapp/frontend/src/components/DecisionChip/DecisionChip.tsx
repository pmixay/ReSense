// A decision as a safety-coloured pill: GO deep green, CAUTION amber with ink text, STOP red with the
// white hatch and the octagon (never brand red), FAULT violet.
import type { ReactNode } from 'react';
import type { Decision } from '../../api/types';
import { DECISION_CHIP_LABEL } from '../../lib/decisions';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './DecisionChip.module.css';

export const DECISION_ICON: Record<Decision, IconName> = {
  GO: 'go-circle',
  CAUTION: 'warning',
  STOP: 'stop-octagon',
  FAULT: 'fault-circle',
};

export interface DecisionChipProps {
  decision: Decision;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** replaces the default label (e.g. "БЕЗ СТОП") */
  label?: ReactNode;
  /** extra text after the label in the body font ("с кадра 8 · 55,6 м", "×30") */
  extra?: ReactNode;
  /** pulsing halo (live STOP) */
  pulse?: boolean;
  className?: string;
  title?: string;
}

export function DecisionChip({ decision, size = 'md', label, extra, pulse, className, title }: DecisionChipProps) {
  const cls = [styles.dc, styles[decision.toLowerCase()], styles[size], pulse && decision === 'STOP' ? 'pulse' : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <span className={cls} title={title}>
      <Icon name={DECISION_ICON[decision]} className={styles.icon} strokeWidth={2.6} />
      <span className={styles.text}>{label ?? DECISION_CHIP_LABEL[decision]}</span>
      {extra !== undefined && extra !== null && <span className={styles.extra}>{extra}</span>}
    </span>
  );
}
