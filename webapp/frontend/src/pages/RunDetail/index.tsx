// Прогон — placeholder: KPIs, the decision timeline, distance chart and events arrive later.
import { useParams } from 'react-router-dom';
import { useRun } from '../../api/hooks';
import { Button, Card, Chip, DecisionChip, DecisionStrip, EmptyState, ErrorBanner, PageHeader, Spinner, useRailSub } from '../../components';
import { fmtBytes, fmtRelDate } from '../../lib/format';

export default function RunDetail() {
  const { id = '' } = useParams();
  const run = useRun(id, { retry: false });
  const r = run.data;
  useRailSub(r?.name ?? undefined);
  const first = r?.summary.first_stop;
  return (
    <>
      <PageHeader
        title={r?.name ?? 'Прогон'}
        docTitle={r?.name ?? 'Прогон'}
        eyebrow="Прогон"
        back={{ to: '/runs', label: 'К прогонам' }}
        badge={
          r ? (
            first ? (
              <DecisionChip decision="STOP" size="lg" extra={`с кадра ${first.frame}`} />
            ) : (
              <DecisionChip decision="GO" size="lg" label="БЕЗ СТОП" />
            )
          ) : undefined
        }
        chips={
          r ? (
            <>
              {r.recording && <Chip variant="outline">{fmtBytes(r.recording.size_bytes)}</Chip>}
              <Chip variant="outline">{r.preset.name}</Chip>
              <Chip variant="outline">{fmtRelDate(r.created_at)}</Chip>
            </>
          ) : undefined
        }
        actions={
          <>
            <Button variant="outline" icon="compare" to={`/compare?a=${encodeURIComponent(id)}`}>
              Сравнить
            </Button>
            <Button variant="dark" icon="play" to={`/player/${encodeURIComponent(id)}`}>
              Открыть в плеере
            </Button>
          </>
        }
      />
      <Card title="Решения по кадрам">
        {run.isError ? (
          <ErrorBanner error={run.error} onRetry={() => void run.refetch()} />
        ) : run.isLoading ? (
          <Spinner />
        ) : r ? (
          <DecisionStrip decisions={r.summary.decisions} height={44} radius={14} ticks tickUnit="кадр" />
        ) : (
          <EmptyState title="Прогон не найден" />
        )}
      </Card>
    </>
  );
}
