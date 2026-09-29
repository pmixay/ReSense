// Прогоны — placeholder: the table of results arrives with the page's own agent.
import { useRuns } from '../../api/hooks';
import { Button, Card, Chip, DecisionLegend, EmptyState, ErrorBanner, PageHeader, Spinner } from '../../components';
import { RUNS, fmtCount } from '../../lib/format';

export default function Runs() {
  const runs = useRuns({ retry: false });
  return (
    <>
      <PageHeader
        title="Прогоны"
        station={2}
        chips={runs.data ? <Chip variant="outline">{fmtCount(runs.data.length, RUNS)}</Chip> : undefined}
        actions={
          <Button variant="outline" icon="compare" to="/compare">
            Сравнить
          </Button>
        }
      />
      <Card title="Результаты" help="Каждый прогон — одна запись, обработанная детектором с выбранным пресетом." actions={<DecisionLegend />}>
        {runs.isError ? (
          <ErrorBanner error={runs.error} onRetry={() => void runs.refetch()} />
        ) : runs.isLoading ? (
          <Spinner />
        ) : (
          <EmptyState icon="list" title={runs.data?.length ? 'Таблица прогонов' : 'Прогонов пока нет'}>
            Страница в разработке.
          </EmptyState>
        )}
      </Card>
    </>
  );
}
