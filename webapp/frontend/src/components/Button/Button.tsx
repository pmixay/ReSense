// Pill buttons: primary (brand red, the main call to action only), dark (ink), outline (white with a
// hairline), ghost (flat well), light / ghost-light (on red or dark surfaces). Renders a <button>, a
// router <Link> (`to`) or an <a> (`href`, e.g. downloads).
import { forwardRef, type ButtonHTMLAttributes, type ReactNode, type Ref } from 'react';
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../Icon/Icon';
import { Spinner } from '../Spinner/Spinner';
import styles from './Button.module.css';

export type ButtonVariant = 'primary' | 'dark' | 'outline' | 'ghost' | 'light' | 'ghost-light';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: IconName;
  iconRight?: IconName;
  loading?: boolean;
  /** router link */
  to?: string;
  /** plain link (downloads, external) */
  href?: string;
  download?: boolean | string;
  target?: string;
  fullWidth?: boolean;
  children?: ReactNode;
}

const ICON_SIZE: Record<ButtonSize, number> = { sm: 16, md: 16, lg: 20 };

export const Button = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(function Button(
  { variant = 'dark', size = 'md', icon, iconRight, loading, to, href, download, target, fullWidth, className, children, disabled, type, ...rest },
  ref,
) {
  const cls = [styles.btn, styles[variant], styles[size], fullWidth ? styles.full : '', loading ? styles.loading : '', className]
    .filter(Boolean)
    .join(' ');
  const spinnerTone = variant === 'outline' || variant === 'ghost' || variant === 'light' ? 'ink' : 'light';
  const inner = (
    <>
      {loading ? (
        <Spinner size={ICON_SIZE[size]} tone={spinnerTone} label="Выполняется" />
      ) : (
        icon && <Icon name={icon} size={ICON_SIZE[size]} />
      )}
      {children !== undefined && children !== null && <span className={styles.label}>{children}</span>}
      {iconRight && <Icon name={iconRight} size={ICON_SIZE[size]} />}
    </>
  );
  const inert = disabled || loading;
  if (to !== undefined && !inert) {
    return (
      <Link ref={ref as Ref<HTMLAnchorElement>} to={to} className={cls} aria-label={rest['aria-label']} title={rest.title}>
        {inner}
      </Link>
    );
  }
  if (href !== undefined && !inert) {
    return (
      <a
        ref={ref as Ref<HTMLAnchorElement>}
        href={href}
        download={download}
        target={target}
        rel={target === '_blank' ? 'noreferrer' : undefined}
        className={cls}
        aria-label={rest['aria-label']}
        title={rest.title}
      >
        {inner}
      </a>
    );
  }
  return (
    <button
      ref={ref as Ref<HTMLButtonElement>}
      type={type ?? 'button'}
      className={cls}
      disabled={inert}
      aria-busy={loading || undefined}
      {...rest}
    >
      {inner}
    </button>
  );
});
