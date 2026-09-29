// The mini metro line of the detector's processing stages: finished = ink with a check, current = a
// big ink ring with a spinning arc, pending = outlined. Neutral ink on purpose (no red: «габарит»
// must not read as breached).
import { Icon } from '../Icon/Icon';
import styles from './PipelineLine.module.css';

export const PIPELINE_STAGES = ['декодирование', 'калибровка', 'модель пути', 'габарит', 'кластеризация', 'трекинг'] as const;

export interface PipelineLineProps {
  /** index of the current stage; stages.length = all done; -1 = none started */
  current: number;
  /** spin the current stage's arc */
  active?: boolean;
  stages?: readonly string[];
  /** the failed stage shows in the fault colour */
  failed?: boolean;
  compact?: boolean;
  className?: string;
}

export function PipelineLine({ current, active = true, stages = PIPELINE_STAGES, failed, compact, className }: PipelineLineProps) {
  const n = stages.length;
  const last = Math.max(1, n - 1);
  const fill = current >= n ? 1 : Math.max(0, current) / last;
  const state = (i: number) => (i < current ? 'done' : i === current ? 'current' : 'pending');
  const label = current >= n ? 'все этапы пройдены' : current < 0 ? 'ожидание' : `этап ${current + 1} из ${n}: ${stages[current]}`;
  return (
    <div
      className={[styles.pl, compact ? styles.compact : '', failed ? styles.failed : '', className].filter(Boolean).join(' ')}
      style={{ ['--n' as string]: last }}
      role="img"
      aria-label={`Обработка: ${label}`}
    >
      <div className={styles.rail}>
        <b style={{ width: `${fill * 100}%` }} />
      </div>
      {stages.map((_s, i) => {
        const st = state(i);
        return (
          <span
            key={`s${i}`}
            className={[styles.s, styles[st], st === 'current' && active && !failed ? styles.spin : ''].join(' ')}
            style={{ ['--k' as string]: i }}
          >
            {st === 'done' && <Icon name="check" size={12} strokeWidth={3.4} />}
          </span>
        );
      })}
      {stages.map((s, i) => (
        <span
          key={`t${i}`}
          className={[styles.t, i % 2 ? styles.below : styles.above, i === current ? styles.cur : ''].join(' ')}
          style={{ ['--k' as string]: i }}
        >
          {s}
        </span>
      ))}
    </div>
  );
}
