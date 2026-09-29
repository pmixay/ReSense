// The round "?" button that carries every explanation of the UI (minimal text on the page itself).
import type { ReactNode } from 'react';
import { Tooltip, type TooltipPlacement } from '../Tooltip/Tooltip';
import styles from './Help.module.css';

export interface HelpProps {
  children: ReactNode;
  placement?: TooltipPlacement;
  width?: number | 'auto';
  /** 'light' = white ring for red / dark backgrounds */
  tone?: 'dark' | 'light';
  /** accessible name of the button */
  label?: string;
  defaultOpen?: boolean;
  className?: string;
}

export function Help({ children, placement = 'bottom', width = 250, tone = 'dark', label = 'Подсказка', defaultOpen, className }: HelpProps) {
  return (
    <Tooltip content={children} placement={placement} width={width} defaultOpen={defaultOpen} className={className}>
      <button type="button" className={`${styles.q} ${tone === 'light' ? styles.light : ''}`} aria-label={label}>
        ?
      </button>
    </Tooltip>
  );
}
