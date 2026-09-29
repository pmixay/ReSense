// Small shared parts of the queue views: the count chips and a section heading with a count.
import type { ReactNode } from 'react';
import { Chip } from '../../components';
import { fmtInt, plural } from '../../lib/format';
import type { JobGroups } from './jobs';
import styles from './QueueParts.module.css';

export function CountChips({ groups }: { groups: JobGroups }) {
  const { running, queued, done, failed } = groups;
  const errors = failed.filter((j) => j.status === 'failed').length;
  return (
    <div className={styles.counts}>
      <Chip variant={running.length ? 'ink' : 'well'} size="sm">
        {fmtInt(running.length)} в работе
      </Chip>
      <Chip size="sm">{fmtInt(queued.length)} ждёт</Chip>
      <Chip size="sm">{fmtInt(done.length)} готово</Chip>
      {errors > 0 && (
        <Chip size="sm" dot="var(--fault)">
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
