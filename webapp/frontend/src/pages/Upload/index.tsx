// Загрузка — placeholder: source choice and processing options arrive with the page's own agent.
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSystem } from '../../api/hooks';
import { Button, Card, Chip, EmptyState, PageHeader, Segmented } from '../../components';
import { fmtBytes } from '../../lib/format';
import styles from './Upload.module.css';

type Source = 'file' | 'server' | 'demo';

export default function Upload() {
  const [params] = useSearchParams();
  const initial = (['file', 'server', 'demo'] as const).find((s) => s === params.get('source')) ?? 'file';
  const [source, setSource] = useState<Source>(initial);
  const sys = useSystem();
  const free = sys.isError ? undefined : sys.data?.disk_free_bytes;
  return (
    <>
      <PageHeader
        title="Загрузка"
        station={1}
        chips={<Chip variant="outline">rosbag2 · .mcap · .jsonl · .npy</Chip>}
        actions={
          <>
            <Chip variant="outline" icon="server">
              свободно {free !== undefined ? fmtBytes(free) : '—'}
            </Chip>
            <Button variant="outline" icon="sliders" to="/presets">
              Пресеты
            </Button>
          </>
        }
      />
      <section className={`grid-12 fill-viewport ${styles.grid}`}>
        <Card
          title="Источник"
          className={styles.src}
          actions={
            <Segmented
              label="Источник записи"
              value={source}
              onChange={setSource}
              options={[
                { value: 'file', label: 'Файл', icon: 'file' },
                { value: 'server', label: 'Папка на сервере', icon: 'server' },
                { value: 'demo', label: 'Демо-запись', icon: 'sparkle' },
              ]}
            />
          }
        >
          <div className={styles.drop}>
            <EmptyState
              icon={source === 'file' ? 'upload' : source === 'server' ? 'folder' : 'sparkle'}
              title={source === 'file' ? 'Перетащите запись' : source === 'server' ? 'Папка на сервере' : 'Демо-запись'}
            >
              Страница в разработке.
            </EmptyState>
          </div>
        </Card>
        <Card title="Обработка" className={styles.opts} help="Пресет, топик облака, шаг кадров и облака для плеера.">
          <EmptyState icon="sliders" size="sm" title="Параметры обработки" />
        </Card>
        <Card title="Очередь" className={styles.queue} actions={<Button variant="outline" size="sm" iconRight="arrow-right" to="/queue">Вся очередь</Button>}>
          <EmptyState icon="queue" title="Очередь" size="sm" />
        </Card>
      </section>
    </>
  );
}
