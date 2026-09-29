// Прямой эфир — placeholder: the replay simulation (WS /api/live/sim) and rosbridge arrive later.
import { Card, Chip, EmptyState, PageHeader } from '../../components';

export default function Live() {
  return (
    <>
      <PageHeader title="Прямой эфир" station={3} chips={<Chip variant="outline" dot="var(--hair-2)">нет узла</Chip>} />
      <Card title="Эфир" help="Симуляция воспроизводит готовый прогон с частотой 10 Гц; настоящий узел ROS 2 подключается через rosbridge.">
        <EmptyState icon="live" title="Эфир не запущен">
          Страница в разработке.
        </EmptyState>
      </Card>
    </>
  );
}
