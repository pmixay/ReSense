// Очередь — placeholder: the job list (running / waiting / finished) arrives with the page's own agent.
import { isJobActive, useJobs } from '../../api/hooks';
import { Button, Card, Chip, EmptyState, ErrorBanner, PageHeader, Spinner } from '../../components';

export default function Queue() {
  const jobs = useJobs(undefined, { retry: false });
  const active = jobs.data?.filter(isJobActive).length ?? 0;
  return (
    <>
      <PageHeader
        title="Очередь"
        station={1}
        chips={jobs.data ? <Chip variant="outline">{active ? `${active} в работе или ждут` : 'нет активных задач'}</Chip> : undefined}
        actions={
          <Button variant="primary" icon="upload" to="/upload">
            Новая запись
          </Button>
        }
      />
      <Card title="Задачи" help="Детектор обрабатывает одну запись за раз; остальные ждут в порядке очереди.">
        {jobs.isError ? (
          <ErrorBanner error={jobs.error} onRetry={() => void jobs.refetch()} />
        ) : jobs.isLoading ? (
          <Spinner />
        ) : (
          <EmptyState icon="queue" title={jobs.data?.length ? `Задач: ${jobs.data.length}` : 'Очередь пуста'}>
            Страница в разработке.
          </EmptyState>
        )}
      </Card>
    </>
  );
}
