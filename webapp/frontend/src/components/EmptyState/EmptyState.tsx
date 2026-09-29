// A quiet "nothing here yet": round icon, a Benzin title, one short line, an optional action.
import type { ReactNode } from 'react';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './EmptyState.module.css';

export interface EmptyStateProps {
  icon?: IconName;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  size?: 'sm' | 'md';
  className?: string;
}

export function EmptyState({ icon = 'layers', title, children, action, size = 'md', className }: EmptyStateProps) {
  return (
    <div className={[styles.empty, styles[size], className].filter(Boolean).join(' ')}>
      <span className={styles.icon}>
        <Icon name={icon} size={size === 'sm' ? 20 : 26} />
      </span>
      <div className={styles.title}>{title}</div>
      {children && <div className={styles.text}>{children}</div>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
