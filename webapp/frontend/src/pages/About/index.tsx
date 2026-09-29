// О системе — placeholder: how the detector works, its limits and the evidence arrive later.
import { Card, EmptyState, PageHeader } from '../../components';

export default function About() {
  return (
    <>
      <PageHeader title="О системе" station={3} />
      <Card title="Как это работает" help="Декодирование → калибровка → модель пути → габарит → кластеризация → трекинг.">
        <EmptyState icon="info" title="ReSense">
          Страница в разработке.
        </EmptyState>
      </Card>
    </>
  );
}
