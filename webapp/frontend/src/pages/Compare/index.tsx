// Сравнение — placeholder: two runs side by side arrive with the page's own agent.
import { Card, EmptyState, PageHeader } from '../../components';

export default function Compare() {
  return (
    <>
      <PageHeader title="Сравнение" station={2} />
      <Card title="Два прогона" help="Одна запись с разными пресетами или две записи: решения по кадрам друг под другом.">
        <EmptyState icon="compare" title="Выберите два прогона">
          Страница в разработке.
        </EmptyState>
      </Card>
    </>
  );
}
