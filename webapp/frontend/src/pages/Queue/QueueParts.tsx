// Small shared parts of the queue views: the count chips and a section heading with a count.
import type { ReactNode } from 'react';
import { Chip } from '../../components';
import { fmtInt, plural } from '../../lib/format';
import type { JobGroups } from './jobs';
import styles from './QueueParts.module.css';

/** «1 в работе · 1 ждёт · 2 готово · 1 ошибка»; `outline` on the page background, `well` in cards. */
export function CountChips({ groups, variant = 'well' }: { groups: JobGroups; variant?: 'well' | 'outline' }) {
  const { running, queued, done, failed } = groups;
  const errors = failed.filter((j) => j.status === 'failed').length;
  return (
    <div className={styles.counts}>
      <Chip variant={running.length ? 'ink' : variant} size="sm">
        {fmtInt(running.length)} в работе
      </Chip>
      <Chip variant={variant} size="sm">
        {fmtInt(queued.length)} ждёт
      </Chip>
      <Chip variant={variant} size="sm">
        {fmtInt(done.length)} готово
      </Chip>
      {errors > 0 && (
        <Chip variant={variant} size="sm" dot="var(--fault)">
          {fmtInt(errors)} {plural(errors, ['ошибка', 'ошибки', 'ошибок'])}
        </Chip>
      )}
    </div>
  );
}

export function SectionHead({ title, count, children }: { title: string; count?: number; children?: ReactNode }) {
  return (
    <div className={styles.sec}>
      {title}
      {count !== undefined && <span className={styles.n}>{fmtInt(count)}</span>}
      {children && <span className={styles.right}>{children}</span>}
    </div>
  );
}
