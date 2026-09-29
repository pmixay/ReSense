// Параметры — placeholder: presets and the curated detector parameters arrive later.
import { usePresets } from '../../api/hooks';
import { Card, Chip, EmptyState, ErrorBanner, PageHeader, Spinner } from '../../components';
import { PRESETS, fmtCount } from '../../lib/format';

export default function Presets() {
  const presets = usePresets({ retry: false });
  return (
    <>
      <PageHeader title="Параметры" station={3} chips={presets.data ? <Chip variant="outline">{fmtCount(presets.data.length, PRESETS)}</Chip> : undefined} />
      <Card title="Пресеты" help="Пресет — набор параметров детектора; встроенный «standard» изменить нельзя.">
        {presets.isError ? (
          <ErrorBanner error={presets.error} onRetry={() => void presets.refetch()} />
        ) : presets.isLoading ? (
          <Spinner />
        ) : (
          <EmptyState icon="sliders" title="Пресеты детектора">
            Страница в разработке.
          </EmptyState>
        )}
      </Card>
    </>
  );
}
