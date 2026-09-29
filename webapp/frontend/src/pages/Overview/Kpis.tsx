// The four KPI tiles of Главная, each with a small real visual: the latest run's latency histogram
// (p95 highlighted), the labelled object frames answered with STOP, false STOP over the scored runs
// (a line of runs with a tick per false episode), the first STOP distance on the 0–210 m range.
import { useId } from 'react';
import { useRunSeries } from '../../api/hooks';
import type { Run } from '../../api/types';
import { Icon, KpiTile, StopMark } from '../../components';
import { fmtInt, fmtMs, fmtNum, fmtNumTrim, fmtPercent, plural } from '../../lib/format';
import { falseStops, latencyHistogram, latestFirstStop, latestWithObject } from './kpis';
import { useSize } from './useSize';
import styles from './Kpis.module.css';

const RANGE_M = 210;
const STOP = '#D0001B';
const INK = '#16151A';

function Hatch({ id }: { id: string }) {
  return (
    <pattern id={id} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="6" height="6" fill={STOP} />
      <rect width="2.2" height="6" fill="rgba(255,255,255,.28)" />
    </pattern>
  );
}

function LatencyViz({ latency, p95 }: { latency: readonly number[]; p95: number }) {
  const [ref, w, H] = useSize<HTMLDivElement>();
  const top = H - 22; // room for the "p95" label
  const { counts, p95Bin } = latencyHistogram(latency, p95);
  const peak = Math.max(1, ...counts);
  const n = counts.length;
  const gap = 3;
  const bw = w > 0 ? (w - gap * (n - 1)) / n : 0;
  return (
    <div ref={ref} className={styles.viz} role="img" aria-label={`Распределение задержки по кадрам, p95 ${fmtMs(p95)}`}>
      {w > 0 && (
        <svg width={w} height={H} viewBox={`0 0 ${w} ${H}`}>
          {counts.map((c, i) => {
            const h = 5 + (c / peak) * top;
            const x = i * (bw + gap);
            return <rect key={i} x={x} y={H - h} width={bw} height={h} rx={Math.min(3, bw / 2)} fill={i === p95Bin ? '#FFFFFF' : 'rgba(255,255,255,.3)'} />;
          })}
          <text
            x={p95Bin * (bw + gap) + bw / 2}
            y={H - (5 + (counts[p95Bin] / peak) * top) - 6}
            textAnchor="middle"
            fontFamily="Montserrat, sans-serif"
            fontWeight="800"
            fontSize="10.5"
            fill="#FFFFFF"
          >
            p95
          </text>
        </svg>
      )}
    </div>
  );
}

function ObjectsViz({ detected, total }: { detected: number; total: number }) {
  const pid = useId().replace(/:/g, '');
  const [ref, w, H] = useSize<HTMLDivElement>();
  const bh = Math.min(30, H - 8);
  const n = 10;
  let k = total > 0 ? Math.round((detected / total) * n) : 0;
  if (detected > 0) k = Math.max(1, k);
  if (detected < total) k = Math.min(n - 1, k);
  const gap = 4;
  const bw = w > 0 ? (w - gap * (n - 1) - 8) / n : 0;
  return (
    <div ref={ref} className={styles.viz} role="img" aria-label={`СТОП в ${detected} из ${total} кадров с объектом`}>
      {w > 0 && (
        <svg width={w} height={H} viewBox={`0 0 ${w} ${H}`}>
          <defs>
            <Hatch id={pid} />
          </defs>
          {Array.from({ length: n }, (_, i) => (
            <rect key={i} x={i * (bw + gap) + (i >= k ? 8 : 0)} y={(H - bh) / 2} width={bw} height={bh} rx={6} fill={i < k ? `url(#${pid})` : '#E3DDD5'} />
          ))}
        </svg>
      )}
    </div>
  );
}

function FalseStopViz({ runs }: { runs: readonly Run[] }) {
  const [ref, w, H] = useSize<HTMLDivElement>();
  const cy = H - 12;
  const n = runs.length;
  const pad = 8;
  const x = (i: number) => (n === 1 ? w / 2 : pad + (i * (w - 2 * pad)) / (n - 1));
  return (
    <div ref={ref} className={styles.viz} role="img" aria-label="Ложные СТОП по прогонам с разметкой">
      {w > 0 && (
        <svg width={w} height={H} viewBox={`0 0 ${w} ${H}`}>
          <rect x={0} y={cy - 4} width={w} height={8} rx={4} fill="#E4000D" />
          {runs.map((r, i) => {
            const fs = r.summary.eval?.false_stop_episodes ?? 0;
            const ticks = Math.min(5, fs);
            return (
              <g key={r.id}>
                {Array.from({ length: ticks }, (_, t) => (
                  <rect key={t} x={x(i) - (ticks * 5) / 2 + t * 5 + 1} y={cy - 28 + (t % 2) * 4} width={3.2} height={16 - (t % 2) * 4} rx={1.6} fill={STOP} />
                ))}
                <circle cx={x(i)} cy={cy} r={6} fill="#FFFFFF" stroke="#E4000D" strokeWidth={3} />
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}

function FirstStopViz({ distance }: { distance: number }) {
  const [ref, w, H] = useSize<HTMLDivElement>();
  const cy = Math.round(H * 0.4);
  const m = Math.min(RANGE_M, Math.max(0, distance));
  const r = 10;
  const x = w > 0 ? r + ((w - 2 * r) * m) / RANGE_M : 0;
  return (
    <div ref={ref} className={styles.viz} role="img" aria-label={`Первый СТОП на ${fmtNum(distance, 1)} м из ${RANGE_M} м дальности`}>
      {w > 0 && (
        <svg width={w} height={H} viewBox={`0 0 ${w} ${H}`}>
          <rect x={0} y={cy - 4} width={w} height={8} rx={4} fill="#EDE9E4" />
          <rect x={0} y={cy - 4} width={x} height={8} rx={4} fill="#12A150" />
          <circle cx={x} cy={cy} r={r} fill={STOP} stroke="#FFFFFF" strokeWidth={3} />
          <path d={`M${x - 4.5} ${cy}h9`} stroke="#FFFFFF" strokeWidth={2.6} strokeLinecap="round" />
          <text x={0} y={H - 3} fontFamily="Montserrat, sans-serif" fontWeight="700" fontSize="10.5" fill={INK}>
            0
          </text>
          <text x={w} y={H - 3} textAnchor="end" fontFamily="Montserrat, sans-serif" fontWeight="700" fontSize="10.5" fill={INK}>
            {RANGE_M} м
          </text>
        </svg>
      )}
    </div>
  );
}

/** A KPI value (and unit) that shrinks to its tile: font ≈ tile width / characters. */
function Fit({ v, u }: { v: string; u?: string }) {
  const n = v.length + (u ? u.length * 0.5 + 0.4 : 0);
  return (
    <span className={styles.fit} style={{ ['--n' as string]: Math.max(4, n) }}>
      {v}
      {u && <small>{u}</small>}
    </span>
  );
}

const Empty = ({ dark }: { dark?: boolean }) => <div className={[styles.vizEmpty, dark ? styles.vizEmptyDark : ''].join(' ')} aria-hidden />;

export function Kpis({ runs, offline }: { runs: Run[] | undefined; offline?: boolean }) {
  const latest = runs?.[0];
  const series = useRunSeries(latest?.id, { retry: false });
  const obj = latestWithObject(runs);
  const fs = falseStops(runs);
  const first = latestFirstStop(runs);
  const ev = obj?.summary.eval;
  const firstStop = first?.summary.first_stop;

  return (
    <div className={styles.kpis}>
      <KpiTile
        variant="dark"
        size="lg"
        className={styles.tile}
        icon={<Icon name="clock" size={17} />}
        label="p95 задержка"
        help="95 % кадров последнего прогона обработаны быстрее этого времени (весь конвейер детектора на кадр). Бюджет — 100 мс при 10 Гц."
        helpPlacement="top"
        viz={latest && series.data ? <LatencyViz latency={series.data.latency_ms} p95={latest.summary.latency_ms.p95} /> : <Empty dark />}
        value={latest ? <Fit v={fmtNum(latest.summary.latency_ms.p95)} u="мс" /> : '—'}
        sub={latest ? `p50 ${fmtMs(latest.summary.latency_ms.p50)} · ${latest.name}` : offline ? 'нет связи' : 'после первого прогона'}
      />
      <KpiTile
        size="lg"
        className={styles.tile}
        icon={<StopMark />}
        label="Объект в габарите"
        help="Кадры, где по разметке в габарите объект, и сколько из них детектор ответил СТОП (последний прогон с объектом)."
        helpPlacement="top"
        viz={ev ? <ObjectsViz detected={ev.frames_detected} total={ev.frames_with_object_in_gauge} /> : <Empty />}
        value={ev ? <Fit v={`${fmtInt(ev.frames_detected)} / ${fmtInt(ev.frames_with_object_in_gauge)}`} /> : '—'}
        sub={obj && ev ? `${obj.name} · ${fmtPercent(ev.recall)}` : offline ? 'нет связи' : 'нужна разметка с объектом'}
      />
      <KpiTile
        size="lg"
        className={styles.tile}
        icon={<Icon name="rails" size={17} />}
        label="Ложные СТОП"
        help={
          fs?.perKm !== null && fs?.perKm !== undefined
            ? 'Эпизоды СТОП без объекта в габарите по разметке, на километр пути прогонов с разметкой.'
            : 'Эпизоды СТОП без объекта в габарите по разметке, в среднем на прогон с разметкой. Станция — прогон, риска — ложный эпизод.'
        }
        helpPlacement="top"
        viz={fs ? <FalseStopViz runs={fs.runs} /> : <Empty />}
        value={fs ? <Fit v={fmtNumTrim(fs.perKm ?? fs.perRun, 1)} u={fs.perKm !== null ? '/ км' : '/ прогон'} /> : '—'}
        sub={
          fs
            ? `${fmtInt(fs.scored)} ${plural(fs.scored, ['прогон', 'прогона', 'прогонов'])} · ${fmtInt(fs.total)} ${plural(fs.total, ['эпизод', 'эпизода', 'эпизодов'])}`
            : offline
              ? 'нет связи'
              : 'нужна разметка'
        }
      />
      <KpiTile
        size="lg"
        className={styles.tile}
        icon={<StopMark />}
        label="Первый СТОП"
        help="Дистанция до препятствия в первом кадре со СТОП (последний прогон со СТОП); шкала — дальность лидара 210 м."
        helpPlacement="top"
        viz={firstStop && firstStop.distance !== null ? <FirstStopViz distance={firstStop.distance} /> : <Empty />}
        value={firstStop && firstStop.distance !== null ? <Fit v={fmtNum(firstStop.distance, 1)} u="м" /> : '—'}
        sub={first && firstStop ? `${first.name} · кадр ${fmtInt(firstStop.frame)}` : offline ? 'нет связи' : 'СТОП ещё не было'}
      />
    </div>
  );
}
