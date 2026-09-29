// The small cards of the live page: node stats, objects of the current frame, health lamps.
import type { ReactNode } from 'react';
import { Card, Chip, EmptyState, Icon, Sparkline } from '../../components';
import { fmtInt, fmtNum, fmtPercent } from '../../lib/format';
import type { FeedSnapshot } from './feed';
import type { SourceKind } from './SourceBar';
import { detectionRows, fmtLateral, fmtSize, healthLevel, healthRows, type Lamp } from './timeline';
import { useSize } from '../../lib/useSize';
import styles from './Panels.module.css';

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(' ');

// ---------------------------------------------------------------- node

/** The chart between a stat's label and its value, drawn at the height the tile has left for it
 *  (none on short tiles: it never covers the label). */
function StatViz({ render }: { render: (height: number) => ReactNode }) {
  const [ref, , h] = useSize<HTMLDivElement>();
  return (
    <div ref={ref} className={styles.statViz}>
      {h >= 16 && render(Math.min(36, h))}
    </div>
  );
}

function Stat({ label, value, unit, viz }: { label: string; value: string; unit?: string; viz?: (height: number) => ReactNode }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statL}>{label}</span>
      {viz ? <StatViz render={viz} /> : <span className={styles.statGap} />}
      <span className={styles.statV}>
        {value}
        {unit && value !== '—' && <small>{unit}</small>}
      </span>
    </div>
  );
}

export interface NodeCardProps {
  snap: FeedSnapshot;
  kind: SourceKind;
  /** per-slot latency of the last 30 s (Slots.latency) */
  latency: readonly (number | null)[];
  latencyBudget: number;
  className?: string;
}

export function NodeCard({ snap, kind, latency, latencyBudget, className }: NodeCardProps) {
  const node = snap.msg?.node;
  // a rate is only true while messages arrive: a stale, paused or ended feed has none
  const fps = snap.view === 'live' ? num(node?.fps) : null;
  // the frame's own processing time: current while live, or for the frame a paused replay shows
  const lat = snap.view === 'live' || snap.view === 'paused' ? (num(node?.latency_ms) ?? num(snap.msg?.timing_ms?.total)) : null;
  const frames = num(node?.frames) ?? (snap.count || null);
  const dropped = num(node?.dropped_frames);
  const first = latency.findIndex((v) => v !== null);
  const recent = first < 0 ? [] : latency.slice(first); // from the first sample of the window
  return (
    <Card
      title="Узел"
      className={cx(styles.node, className)}
      badges={
        <Chip size="sm" variant={kind === 'sim' ? 'well' : 'outline'} icon={kind === 'sim' ? 'play' : 'live'}>
          {kind === 'sim' ? 'симуляция' : 'ROS 2'}
        </Chip>
      }
      help={
        <>
          <b>Частота</b> — сообщений в секунду, лидар даёт 10. <b>Задержка</b> — обработка кадра (у узла — декодирование + детектор), график — последние 30 с
          (бюджет {fmtInt(latencyBudget)} мс — порог предупреждения исправности). <b>Кадров</b> — за это подключение. <b>Пропущено</b> — кадры, которые узел не
          получил или пропустил, догоняя поток.
        </>
      }
      helpPlacement="bottom-end"
    >
      <div className={styles.stats}>
        <Stat label="Частота" value={fmtNum(fps, 1)} unit="Гц" />
        <Stat
          label="Задержка"
          value={lat === null ? '—' : fmtNum(lat, lat < 10 ? 1 : 0)}
          unit="мс"
          viz={
            recent.length > 1
              ? (h) => (
                  <Sparkline
                    values={recent}
                    min={0}
                    max={Math.max(latencyBudget, ...recent.map((v) => v ?? 0))}
                    height={h}
                    dot={false}
                    label="Задержка за 30 с"
                  />
                )
              : undefined
          }
        />
        <Stat label="Кадров" value={fmtInt(frames)} />
        <Stat label="Пропущено" value={fmtInt(dropped)} />
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------- objects

export function DetectionsCard({ snap, fresh, className }: { snap: FeedSnapshot; fresh: boolean; className?: string }) {
  const shown = fresh || snap.view === 'paused';
  const rows = shown ? detectionRows(snap.msg) : [];
  return (
    <Card
      title="Объекты"
      className={cx(styles.dets, className)}
      badges={shown ? <Chip size="sm">{fmtInt(rows.length)}</Chip> : undefined}
      help={
        <>
          Объекты текущего кадра, ближние сверху: <b>в габарите</b> (подтверждённый — это СТОП) и <b>рядом</b> — в зоне предупреждения. Смещение — от оси пути;
          размер — длина × ширина × высота.
        </>
      }
      helpPlacement="bottom-end"
    >
      {!shown ? (
        <EmptyState size="sm" icon="target" title="Нет данных" className={styles.empty} />
      ) : !rows.length ? (
        <EmptyState size="sm" icon="check" title="Объектов нет" className={styles.empty} />
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Зона</th>
                <th>Дистанция</th>
                <th>Смещение</th>
                <th>Размер</th>
                <th>Увер.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key}>
                  <td>
                    <span className={cx(styles.zone, r.zone === 'gauge' ? styles.zGauge : styles.zNear)}>{r.zone === 'gauge' ? 'габарит' : 'рядом'}</span>
                  </td>
                  <td className={styles.dist}>
                    {fmtNum(r.distance, 1)}
                    <small>м</small>
                  </td>
                  <td>{fmtLateral(r.lateral)}</td>
                  <td>{fmtSize(r.size)}</td>
                  <td>{fmtPercent(r.confidence)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- health

const LEVEL: Record<'ok' | 'warn' | 'error', [string, string]> = {
  ok: ['норма', 'var(--go)'],
  warn: ['снижена', 'var(--caution)'],
  error: ['ошибка', 'var(--fault)'],
};

function LampDot({ lamp }: { lamp: Lamp }) {
  return <span className={cx(styles.lamp, styles[`l-${lamp}`])} aria-hidden />;
}

export function HealthCard({ snap, fresh, minVisibility, className }: { snap: FeedSnapshot; fresh: boolean; minVisibility: number; className?: string }) {
  const rows = healthRows(snap.msg, fresh, minVisibility);
  const level = fresh ? healthLevel(snap.msg) : null;
  const freshness = snap.msg?.freshness;
  // violet «нет» only when data should arrive and does not (stale, a broken link, the node's own
  // check); a stopped replay, a disconnected node or the end of the record are just dark
  const late = snap.view === 'stale' || snap.view === 'error' || snap.reconnecting;
  const freshLamp: Lamp =
    snap.age === null ? 'off' : snap.view === 'paused' ? 'wait' : fresh ? (freshness?.valid === false ? 'error' : 'ok') : late ? 'error' : 'off';
  const freshText = freshLamp === 'off' ? '—' : freshLamp === 'wait' ? 'пауза' : freshLamp === 'ok' ? 'да' : 'нет';
  return (
    <Card
      title="Исправность"
      className={cx(styles.health, className)}
      actions={
        level ? (
          <Chip size="sm" variant="outline" dot={LEVEL[level][1]}>
            {LEVEL[level][0]}
          </Chip>
        ) : undefined
      }
      help={
        <>
          <b>Свежесть</b> — сообщение не старше 0,5 с (у узла — ещё и его проверка часов). <b>Видимость</b> — как далеко вдоль пути виден тоннель (норма от{' '}
          {fmtInt(minVisibility)} м). <b>Захват рельсов</b> — доля последних кадров с найденной парой рельсов. <b>Калибровка</b> — крепления лидара по рельсам.
          Значок у заголовка — общий уровень исправности кадра. Устаревшие данные гасят все лампы.
        </>
      }
      helpPlacement="bottom-end"
    >
      <ul className={styles.lamps}>
        <li>
          <LampDot lamp={freshLamp} />
          <span className={styles.ln}>
            <Icon name="clock" size={16} />
            Свежесть
          </span>
          <b>{freshText}</b>
        </li>
        {rows.map((r) => (
          <li key={r.key}>
            <LampDot lamp={r.lamp} />
            <span className={styles.ln}>
              <Icon name={r.key === 'visibility' ? 'eye' : r.key === 'rails' ? 'rails' : 'target'} size={16} />
              {r.label}
            </span>
            <b>{snap.msg ? r.value : '—'}</b>
          </li>
        ))}
      </ul>
    </Card>
  );
}
