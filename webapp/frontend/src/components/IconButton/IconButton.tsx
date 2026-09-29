// Round icon-only button; the label is its accessible name and, optionally, a tooltip.
import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../Icon/Icon';
import { Spinner } from '../Spinner/Spinner';
import { Tooltip, type TooltipPlacement } from '../Tooltip/Tooltip';
import styles from './IconButton.module.css';

export type IconButtonVariant = 'well' | 'white' | 'dark' | 'outline' | 'fault' | 'red' | 'glass';
export type IconButtonSize = 'xs' | 'sm' | 'md' | 'lg';

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icon: IconName;
  label: string;
  variant?: IconButtonVariant;
  size?: IconButtonSize;
  /** show the label as a tooltip too */
  tooltip?: boolean;
  tooltipPlacement?: TooltipPlacement;
  loading?: boolean;
  active?: boolean;
  to?: string;
}

const PX: Record<IconButtonSize, [number, number]> = { xs: [30, 14], sm: [36, 16], md: [40, 16], lg: [44, 20] };

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, label, variant = 'well', size = 'md', tooltip, tooltipPlacement = 'top', loading, active, to, className, disabled, type, style, ...rest },
  ref,
) {
  const [box, glyph] = PX[size];
  const cls = [styles.ib, styles[variant], active ? styles.active : '', className].filter(Boolean).join(' ');
  const inner = loading ? (
    <Spinner size={glyph} tone={variant === 'dark' || variant === 'fault' || variant === 'red' || variant === 'glass' ? 'light' : 'ink'} />
  ) : (
    <Icon name={icon} size={glyph} />
  );
  const el =
    to !== undefined && !disabled ? (
      <Link to={to} className={cls} aria-label={label} style={{ width: box, height: box, ...style }}>
        {inner}
      </Link>
    ) : (
      <button
        ref={ref}
        type={type ?? 'button'}
        className={cls}
        aria-label={label}
        aria-pressed={active === undefined ? undefined : active}
        disabled={disabled || loading}
        style={{ width: box, height: box, ...style }}
        {...rest}
      >
        {inner}
      </button>
    );
  return tooltip ? (
    <Tooltip content={label} placement={tooltipPlacement} width="auto">
      {el}
    </Tooltip>
  ) : (
    el
  );
});
