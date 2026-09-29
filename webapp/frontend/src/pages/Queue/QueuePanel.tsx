// The live queue as a compact column (the Загрузка page): the running job, the waiting ones and the
// latest finished ones; the full view is the Очередь page.
import { Button, Card, EmptyState, ErrorBanner, Icon, IconButton, Spinner } from '../../components';
import { FailedRow, FinishedRow, QueuedRow } from './JobRows';
import { CountChips, SectionHead } from './QueueParts';
import { JobCard } from './JobCard';
import { useQueue } from './useQueue';
import styles from './QueuePanel.module.css';

export function QueuePanel({ className }: { className?: string }) {
  const { jobs, groups, finished, recById, runById } = useQueue();
  const running = groups.running[0];
  return (
    <Card
      title="Очередь"
      className={[styles.panel, className].filter(Boolean).join(' ')}
      actions={jobs.data ? <CountChips groups={groups} /> : undefined}
    >
      {jobs.isError ? (
        <ErrorBanner error={jobs.error} onRetry={() => void jobs.refetch()} retrying={jobs.isFetching} />
      ) : jobs.isLoading ? (
        <div className={styles.center}>
          <Spinner size={24} />
        </div>
      ) : (
        <>
          {running ? (
            <JobCard job={running} recording={recById.get(running.recording_id)} variant="compact" />
          ) : (
            <div className={styles.idle}>
              <span className={styles.idleIc}>
                <Icon name="cpu" size={22} />
              </span>
              <div className={styles.idleT}>Детектор свободен</div>
              <IconButton icon="arrow-right" label="Открыть очередь" tooltip variant="white" size="sm" to="/queue" />
            </div>
          )}
          <div className={styles.lists}>
            {groups.queued.length > 0 && (
              <>
                <SectionHead title="Ждёт" count={groups.queued.length} />
                {groups.queued.map((j) => (
                  <QueuedRow key={j.id} job={j} recording={recById.get(j.recording_id)} compact />
                ))}
              </>
            )}
            <SectionHead title="Завершено" count={finished.length}>
              <Button variant="ghost" size="sm" iconRight="arrow-right" to="/queue">
                вся очередь
              </Button>
            </SectionHead>
            {finished.length === 0 ? (
              <EmptyState icon="list" size="sm" title="Пока пусто" />
            ) : (
              finished.map((j) =>
                j.status === 'done' ? (
                  <FinishedRow key={j.id} job={j} recording={recById.get(j.recording_id)} run={j.run_id ? runById.get(j.run_id) : undefined} compact />
                ) : (
                  <FailedRow key={j.id} job={j} recording={recById.get(j.recording_id)} compact />
                ),
              )
            )}
          </div>
        </>
      )}
    </Card>
  );
}
