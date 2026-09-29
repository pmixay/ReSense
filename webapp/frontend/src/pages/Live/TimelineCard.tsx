// The last 30 seconds: the decision per 0,1 s (gaps where no message came) and the monitored free
// distance ahead under it.
import { useMemo } from 'react';
import { Card, DecisionStrip, Sparkline } from '../../components';
import { fmtInt, fmtNum } from '../../lib/format';
import { dataRuns, type Slots } from './timeline';
import { useSize } from '../../lib/useSize';
import styles from './Panels.module.css';

const pct = (f: number) => `${(f * 100).toFixed(3)}%`;

export function TimelineCard({ slots, live, className }: { slots: Slots; live: boolean; className?: string }) {
  const runs = useMemo(() => dataRuns(slots.letters), [slots]);
  const [ref, , sparkH] = useSize<HTMLDivElement>();
  const n = slots.letters.length;
  const finite = slots.free.filter((v): v is number => v !== null);
  const max = Math.max(50, ...finite) * 1.08;
  const last = slots.free[n - 1] ?? null; // the current slot only: no old value as «now»

  return (
    <Card
      title="Последние 30 с"
      className={[styles.tl, className].filter(Boolean).join(' ')}
      help={
        <>
          Решение по времени, шаг <b>0,1 с</b>; разрыв — сообщений не было. Ниже — свободный путь впереди (clear_distance, м): до препятствия, а без него —
          оценка дальности контроля.
        </>
      }
      actions={
        live && last !== null ? (
          <span className={styles.tlNow}>
            {fmtNum(last, 0)}
            <small>м</small>
          </span>
        ) : undefined
      }
    >
      <div className={styles.roll} role="img" aria-label="Решения за последние 30 секунд">
        {runs.map((r, i) => (
          <div
            key={i}
            className={styles.piece}
            style={{
              left: pct(r.start / n),
              width: pct((r.end - r.start) / n),
            }}
          >
            <DecisionStrip decisions={r.decisions} height={30} radius={6} />
          </div>
        ))}
        {!runs.length && <span className={styles.nodata}>нет данных</span>}
      </div>
      <div className={styles.spark}>
        {finite.length > 0 && (
          <div className={styles.yl} aria-hidden>
            <span>{fmtInt(max)} м</span>
            <span>0</span>
          </div>
        )}
        <div ref={ref} className={styles.sparkBox}>
          {sparkH > 0 && <Sparkline values={slots.free} min={0} max={max} height={sparkH} label="Свободный путь впереди за 30 секунд, м" />}
        </div>
      </div>
      <div className={styles.taxis} aria-hidden>
        <span>−30 с</span>
        <span>−20 с</span>
        <span>−10 с</span>
        <span>сейчас</span>
      </div>
    </Card>
  );
}
