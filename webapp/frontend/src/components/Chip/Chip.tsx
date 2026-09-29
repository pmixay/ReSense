// Small pill for facts and counts: well (default), outline (white + hairline), ink, red tint.
import type { HTMLAttributes, ReactNode } from 'react';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './Chip.module.css';

export type ChipVariant = 'well' | 'outline' | 'ink' | 'red' | 'white' | 'glass' | 'on-red';

export interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: ChipVariant;
  size?: 'sm' | 'md';
  icon?: IconName;
  /** a small colour dot before the text (e.g. var(--go)) */
  dot?: string;
  /** a rounded colour swatch (legends) */
  swatch?: string;
  children?: ReactNode;
}

export function Chip({ variant = 'well', size = 'md', icon, dot, swatch, className, children, ...rest }: ChipProps) {
  return (
    <span className={[styles.chip, styles[variant], styles[size], className].filter(Boolean).join(' ')} {...rest}>
      {dot && <span className={styles.dot} style={{ background: dot }} aria-hidden />}
      {swatch && <span className={styles.swatch} style={{ background: swatch }} aria-hidden />}
      {icon && <Icon name={icon} size={size === 'sm' ? 14 : 16} />}
      {children}
    </span>
  );
}
