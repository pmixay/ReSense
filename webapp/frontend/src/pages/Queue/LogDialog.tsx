// The worker log of a job (GET /api/jobs/{id}/log, the last 64 KB) in a modal: Escape or a click
// outside closes it; it refreshes while the job is active.
import { useEffect, useId, useLayoutEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { isJobActive, useJobLog } from '../../api/hooks';
import type { Job } from '../../api/types';
import { Chip, EmptyState, ErrorBanner, IconButton, Spinner } from '../../components';
import { fmtRelDate } from '../../lib/format';
import styles from './LogDialog.module.css';

export function LogDialog({ job, onClose }: { job: Job; onClose: () => void }) {
  const titleId = useId();
  const log = useJobLog(job.id, { refetchInterval: isJobActive(job) ? 2000 : false });
  const panelRef = useRef<HTMLDivElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    // the dialog itself takes the focus (on the close button its tooltip would pop up at once)
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'Tab' && panelRef.current) {
        // keep the focus inside the dialog
        const els = Array.from(panelRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'));
        if (!els.length) return;
        const first = els[0];
        const last = els[els.length - 1];
        const inside = panelRef.current.contains(document.activeElement);
        if (e.shiftKey && (document.activeElement === first || !inside)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (document.activeElement === last || !inside)) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    // window + capture: before a hovered tooltip (document, capture) stops the Escape
    window.addEventListener('keydown', onKey, true);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      prev?.focus?.();
    };
  }, [onClose]);

  // follow the tail
  useLayoutEffect(() => {
    const el = preRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log.data]);

  return createPortal(
    <div className={styles.overlay} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={panelRef} className={styles.panel} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
        <header className={styles.head}>
          <h2 id={titleId} className={styles.title}>
            Журнал обработки
          </h2>
          <Chip variant="well" size="sm">
            {job.recording_name}
          </Chip>
          <Chip variant="outline" size="sm">
            {fmtRelDate(job.finished_at ?? job.started_at ?? job.created_at)}
          </Chip>
          <span className={styles.sp} />
          <IconButton icon="retry" label="Обновить" tooltip variant="well" loading={log.isFetching} onClick={() => void log.refetch()} />
          <IconButton icon="x" label="Закрыть" tooltip variant="dark" onClick={onClose} />
        </header>
        {job.error && <ErrorBanner error={job.error} title="Ошибка задачи" className={styles.err} />}
        {log.isError ? (
          <ErrorBanner error={log.error} onRetry={() => void log.refetch()} retrying={log.isFetching} />
        ) : log.isLoading ? (
          <div className={styles.center}>
            <Spinner size={28} />
          </div>
        ) : log.data && log.data.trim() ? (
          <pre ref={preRef} className={styles.pre} tabIndex={0} aria-label="Журнал">
            {log.data}
          </pre>
        ) : (
          <EmptyState icon="list" title="Журнал пуст" size="sm" />
        )}
      </div>
    </div>,
    document.body,
  );
}
