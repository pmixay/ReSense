// Title row of a page: line roundel (group number or icon) or a back button with an eyebrow,
// the Benzin title, chips, and actions on the right. Also sets document.title.
import { useEffect, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../Icon/Icon';
import styles from './PageHeader.module.css';

export interface PageHeaderProps {
  title: ReactNode;
  /** browser tab title (defaults to the title when it is a string) */
  docTitle?: string;
  /** the line roundel: nav group number (1–3) or an icon */
  station?: number | IconName;
  /** a back link instead of the roundel (detail pages) */
  back?: { to: string; label: string };
  /** small caps line above the title ("ПРОГОН") */
  eyebrow?: ReactNode;
  /** right after the title (e.g. a DecisionChip) */
  badge?: ReactNode;
  chips?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ title, docTitle, station, back, eyebrow, badge, chips, actions }: PageHeaderProps) {
  const tab = docTitle ?? (typeof title === 'string' ? title : undefined);
  useEffect(() => {
    document.title = tab ? `${tab} · ReSense` : 'ReSense';
  }, [tab]);

  return (
    <div className={styles.ph}>
      {back ? (
        <Link to={back.to} className={styles.back} aria-label={back.label} title={back.label}>
          <Icon name="arrow-left" size={16} />
        </Link>
      ) : station !== undefined ? (
        <span className={styles.rd} aria-hidden>
          {typeof station === 'number' ? station : <Icon name={station} size={18} strokeWidth={2.4} />}
        </span>
      ) : null}
      <div className={styles.ttl}>
        {eyebrow ? (
          <div className={styles.stack}>
            <span className={styles.eyebrow}>
              <i aria-hidden />
              {eyebrow}
            </span>
            <h1 className={styles.h1Small}>{title}</h1>
          </div>
        ) : (
          <h1 className={styles.h1}>{title}</h1>
        )}
        {badge}
        {chips && <div className={styles.chips}>{chips}</div>}
      </div>
      <span className={styles.sp} />
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
