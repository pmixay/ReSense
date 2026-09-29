// Очередь: the job the detector works on (processing line, progress, the decision string growing),
// the waiting jobs with their place, and the finished / failed ones (open, player, log, retry).
import { useCallback, useState, type ReactNode } from 'react';
import { useClearFinishedJobs } from '../../api/hooks';
import type { Job } from '../../api/types';
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Spinner } from '../../components';
import { FailedRow, FinishedRow, QueuedRow } from './JobRows';
import { LogDialog } from './LogDialog';
import { CountChips } from './QueueParts';
import { JobActions, JobCard } from './JobCard';
import { useQueue } from './useQueue';
import styles from './Queue.module.css';

export default function Queue() {
  const { jobs, groups, finished, recById, runById } = useQueue();
  const clear = useClearFinishedJobs();
  const [logOf, setLogJob] = useState<Job | null>(null);
  const closeLog = useCallback(() => setLogJob(null), []);
  // the log follows the job's live state (a running job's log refreshes until it finishes)
  const logJob = logOf ? (jobs.data?.find((j) => j.id === logOf.id) ?? logOf) : null;
  const running = groups.running[0];
  const lastFinished = finished[0];
  const loading = jobs.isLoading;

  // the error is shown once (the main card); the side cards only say that there is no data
  const body = (content: ReactNode, main = false) =>
    jobs.isError ? (
      main ? (
        <ErrorBanner error={jobs.error} onRetry={() => void jobs.refetch()} retrying={jobs.isFetching} />
      ) : (
        <div className={styles.emptyLine}>{jobs.error.offline ? 'нет связи с бэкендом' : 'нет данных'}</div>
      )
    ) : loading ? (
      <div className={styles.center}>
        <Spinner size={24} />
      </div>
    ) : (
      content
    );

  return (
    <>
      <PageHeader
        title="Очередь"
        station={1}
        chips={jobs.data ? <CountChips groups={groups} variant="outline" /> : undefined}
        actions={
          <>
            <Button variant="outline" icon="trash" onClick={() => clear.mutate()} loading={clear.isPending} disabled={finished.length === 0}>
              Убрать готовые
            </Button>
            <Button variant="primary" icon="upload" to="/upload">
              Новая запись
            </Button>
          </>
        }
      />
      {clear.isError && <ErrorBanner error={clear.error} compact className={styles.topErr} />}
      <section className={`grid-12 fill-viewport ${styles.grid}`}>
        <Card
          title={running || !lastFinished ? 'В работе' : 'Последняя задача'}
          help="Детектор обрабатывает одну запись за раз, остальные ждут в порядке очереди. Готовый прогон появляется в «Прогонах»."
          helpPlacement="bottom-start"
          className={styles.main}
          actions={!running && lastFinished ? <JobActions job={lastFinished} onLog={setLogJob} /> : undefined}
        >
          {body(
            running ? (
              <JobCard job={running} recording={recById.get(running.recording_id)} variant="full" onLog={setLogJob} />
            ) : lastFinished ? (
              <JobCard job={lastFinished} recording={recById.get(lastFinished.recording_id)} variant="full" headActions={false} />
            ) : (
              <EmptyState
                icon="cpu"
                title="Детектор свободен"
                action={
                  <div className={styles.acts}>
                    <Button variant="dark" icon="upload" to="/upload">
                      Загрузить запись
                    </Button>
                    <Button variant="outline" icon="sparkle" to="/upload?source=demo">
                      Демо
                    </Button>
                  </div>
                }
              >
                {groups.queued.length ? 'Следующая задача запускается…' : 'Новая задача начнётся сразу.'}
              </EmptyState>
            ),
            true,
          )}
        </Card>

        <div className={styles.side}>
          <Card title="Ждут" badges={jobs.data ? <span className={styles.n}>{groups.queued.length}</span> : undefined} className={styles.waiting}>
            {body(
              groups.queued.length ? (
                <div className={styles.scroll}>
                  {groups.queued.map((j) => (
                    <QueuedRow key={j.id} job={j} recording={recById.get(j.recording_id)} />
                  ))}
                </div>
              ) : (
                <div className={styles.emptyLine}>Очередь пуста</div>
              ),
            )}
          </Card>

          <Card
            title="Завершено"
            badges={jobs.data ? <span className={styles.n}>{finished.length}</span> : undefined}
            help="Галочка — прогон готов; чип — итог по разметке или число СТОП. Ошибку можно повторить с теми же параметрами."
            helpPlacement="bottom"
            className={styles.finished}
            actions={
              <Button variant="outline" size="sm" iconRight="arrow-right" to="/runs">
                Все прогоны
              </Button>
            }
          >
            {body(
              finished.length ? (
                <div className={styles.scroll}>
                  {finished.map((j) =>
                    j.status === 'done' ? (
                      <FinishedRow key={j.id} job={j} recording={recById.get(j.recording_id)} run={j.run_id ? runById.get(j.run_id) : undefined} />
                    ) : (
                      <FailedRow key={j.id} job={j} recording={recById.get(j.recording_id)} onLog={setLogJob} />
                    ),
                  )}
                </div>
              ) : (
                <EmptyState icon="list" size="sm" title="Готовых задач нет" />
              ),
            )}
          </Card>
        </div>
      </section>
      {logJob && <LogDialog job={logJob} onClose={closeLog} />}
    </>
  );
}
