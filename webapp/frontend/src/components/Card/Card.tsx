// White card (radius 28) with an optional header: Benzin title · "?" help · actions on the right.
import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';
import { Help } from '../Help/Help';
import type { TooltipPlacement } from '../Tooltip/Tooltip';
import styles from './Card.module.css';

export type CardVariant = 'white' | 'dark' | 'red' | 'night' | 'well';

export interface CardProps extends Omit<HTMLAttributes<HTMLElement>, 'title'> {
  title?: ReactNode;
  help?: ReactNode;
  helpPlacement?: TooltipPlacement;
  helpWidth?: number | 'auto';
  /** chips next to the title */
  badges?: ReactNode;
  /** right side of the header */
  actions?: ReactNode;
  variant?: CardVariant;
  /** 'none' for edge-to-edge content (3D views) */
  padding?: 'none' | 'sm' | 'md';
  /** header spacing below */
  headGap?: number;
  as?: 'section' | 'div' | 'article';
  style?: CSSProperties;
  children?: ReactNode;
}

export function Card({
  title,
  help,
  helpPlacement = 'bottom',
  helpWidth,
  badges,
  actions,
  variant = 'white',
  padding = 'md',
  headGap,
  as: Tag = 'section',
  className,
  children,
  ...rest
}: CardProps) {
  const hasHead = title !== undefined || help !== undefined || actions !== undefined || badges !== undefined;
  const light = variant === 'dark' || variant === 'red' || variant === 'night';
  return (
    <Tag className={[styles.card, styles[variant], styles[`pad-${padding}`], className].filter(Boolean).join(' ')} {...rest}>
      {hasHead && (
        <header className={styles.head} style={headGap !== undefined ? { marginBottom: headGap } : undefined}>
          {title !== undefined && <h2 className={styles.title}>{title}</h2>}
          {badges}
          {help !== undefined && (
            <Help placement={helpPlacement} width={helpWidth} tone={light ? 'light' : 'dark'}>
              {help}
            </Help>
          )}
          <span className={styles.sp} />
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
