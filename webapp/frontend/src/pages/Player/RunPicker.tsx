// /player without a run: the runs to open, in the same cab — runs with stored clouds first.
import { Link } from 'react-router-dom';
import { useRuns } from '../../api/hooks';
import type { Run } from '../../api/types';
import { Button, Chip, DecisionChip, DecisionStrip, EmptyState, ErrorBanner, Icon, Spinner } from '../../components';
import { worstDecision } from '../../lib/decisions';
import { FRAMES, RUNS, fmtCount, fmtDuration, fmtRelDate } from '../../lib/format';
import { sortRunsForPlayer } from './Roof';
import styles from './Player.module.css';

function RunCard({ r }: { r: Run }) {
  const worst = worstDecision(r.summary.decisions) ?? 'GO';
  return (
    <Link to={`/player/${encodeURIComponent(r.id)}`} className={styles.pickCard} aria-label={`Открыть в плеере: ${r.name}`}>
      <div className={styles.pickTop}>
        <DecisionChip decision={worst} size="sm" />
        <span className={styles.pickDate}>{fmtRelDate(r.created_at)}</span>
      </div>
      <div className={styles.pickName} title={r.name}>
        {r.name}
      </div>
      <DecisionStrip decisions={r.summary.decisions} height={10} radius={5} ariaLabel={`Решения: ${r.name}`} />
      <div className={styles.pickBottom}>
        <span className={styles.pickMeta}>
          {fmtCount(r.summary.n_frames, FRAMES)} · {fmtDuration(r.summary.duration_s)}
        </span>
        {r.has_clouds ? (
          <Chip variant="glass" size="sm" icon="cube">
            3D
          </Chip>
        ) : (
          <Chip variant="glass" size="sm">
            без облака
          </Chip>
        )}
        <span className={styles.pickPlay} aria-hidden>
          <Icon name="play" size={18} />
        </span>
      </div>
    </Link>
  );
}

export function RunPickerGlass() {
  const runs = useRuns();
  if (runs.isLoading) {
    return (
      <div className={styles.glassCenter}>
        <Spinner size={34} tone="light" label="Загрузка прогонов" />
      </div>
    );
  }
  if (runs.isError) {
    return (
      <div className={styles.glassCenter}>
        <div className={styles.glassCard}>
          <ErrorBanner error={runs.error} title="Прогоны не загрузились" onRetry={() => void runs.refetch()} retrying={runs.isFetching} />
        </div>
      </div>
    );
  }
  const list = sortRunsForPlayer(runs.data ?? []);
  if (!list.length) {
    return (
      <div className={styles.glassCenter}>
        <div className={styles.glassCard}>
          <EmptyState
            icon="cube"
            title="Прогонов пока нет"
            action={
              <Button variant="primary" icon="sparkle" to="/upload?source=demo">
                Сделать демо-прогон
              </Button>
            }
          >
            Запишите демо или загрузите запись — и смотрите её здесь в 3D.
          </EmptyState>
        </div>
      </div>
    );
  }
  const withClouds = list.filter((r) => r.has_clouds).length;
  return (
    <div className={styles.pick}>
      <div className={styles.pickHead}>
        <h1 className={styles.pickTitle}>Выберите прогон</h1>
        <Chip variant="glass">{fmtCount(withClouds, RUNS)} в 3D</Chip>
      </div>
      <div className={styles.pickGrid}>
        {list.map((r) => (
          <RunCard key={r.id} r={r} />
        ))}
      </div>
    </div>
  );
}

/** The console of the picker: the keyboard of the player and where runs come from (no runs yet:
 *  the glass offers the demo, the tray an upload). */
export function PickerConsole() {
  const runs = useRuns();
  const empty = !!runs.data && runs.data.length === 0;
  const keys: [string, string][] = [
    ['пробел', 'пуск / пауза'],
    ['← →', 'кадр'],
    ['⇧ ← →', '±10 кадров'],
    ['[ ]', 'события'],
    ['1 2 3', 'камеры'],
    ['+ −', 'скорость'],
    ['F', 'весь экран'],
    ['Esc', 'назад'],
  ];
  return (
    <>
      <section className={`${styles.tile} ${styles.tKeys}`} aria-label="Клавиши плеера">
        <div className={styles.tt}>Клавиши</div>
        <div className={styles.keys}>
          {keys.map(([k, v]) => (
            <span key={k} className={styles.key}>
              <kbd>{k}</kbd>
              {v}
            </span>
          ))}
        </div>
      </section>
      <div className={`${styles.scrub} ${styles.scrubPick}`}>
        {empty ? (
          <Button variant="outline" icon="upload" to="/upload">
            Загрузить запись
          </Button>
        ) : (
          <>
            <Button variant="primary" icon="sparkle" to="/upload?source=demo">
              Сделать демо-прогон
            </Button>
            <Button variant="outline" icon="list" to="/runs">
              Все прогоны
            </Button>
          </>
        )}
      </div>
    </>
  );
}
