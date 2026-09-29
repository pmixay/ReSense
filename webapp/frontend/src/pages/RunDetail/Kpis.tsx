// The KPI row of a run: frames, duration, STOP episodes, first STOP, min distance, misses, p95
// latency (dark) and false alarms (green when none against the labels). Each explains itself in «?».
import type { RunDetail, RunLabels, RunSeries } from '../../api/types';
import { GoodMark, KpiTile, StopMark } from '../../components';
import { FRAMES, NBSP, fmtBytes, fmtDuration, fmtMeters, fmtMs, fmtNum, fmtNumTrim, plural } from '../../lib/format';
import { computeMisses, detectionDelay, episodesText, frameRate, spansText } from '../Runs/common/analysis';
import styles from './RunDetail.module.css';

/** "20,4 с" → ["20,4", "с"]; forms without a single unit stay whole ("1:24"). */
function split(s: string): [string, string | undefined] {
  const parts = s.split(NBSP);
  return parts.length === 2 ? [parts[0], parts[1]] : [s, undefined];
}

const framesWord = (n: number) => plural(n, FRAMES);

export function Kpis({ r, series, labels, frameOf }: { r: RunDetail; series: RunSeries | undefined; labels: RunLabels | undefined; frameOf: (pos: number) => number }) {
  const s = r.summary;
  const ev = s.eval;
  const lanes = series?.labels_in_gauge ?? (labels?.available ? labels.in_gauge : null);
  const misses = series ? computeMisses(series.decisions, lanes) : null;
  const delay = series ? detectionDelay(series.decisions, lanes) : null;
  const fr = frameRate(s.n_frames, s.duration_s);
  const every = r.options?.every ?? 1;
  const [durV, durU] = split(fmtDuration(s.duration_s));
  const stopEps = r.episodes.filter((e) => e.decision === 'STOP');
  const firstEp = stopEps[0];
  const epFrames = firstEp ? (firstEp.first_frame === firstEp.last_frame ? `кадр ${firstEp.first_frame}` : `кадры ${firstEp.first_frame}–${firstEp.last_frame}`) : null;
  const fs = s.first_stop;
  const labelNear = labels?.available ? labels.near.filter((v): v is number => v !== null) : [];
  const labelMin = labelNear.length ? Math.min(...labelNear) : null;
  const clouds = r.sizes?.clouds ?? null;

  return (
    <div className={styles.kpis}>
      <KpiTile
        className={styles.kpi}
        label="Кадров"
        help="Сколько кадров облака обработал детектор; ниже — частота кадров записи."
        value={fmtNum(s.n_frames)}
        sub={fr ? `${fmtNumTrim(fr, 1)} Гц${every > 1 ? ` · шаг ${every}` : ''}` : '—'}
      />
      <KpiTile
        className={styles.kpi}
        label="Длительность"
        help="От первого до последнего обработанного кадра; ниже — объём облаков точек, сохранённых для плеера."
        value={durV}
        unit={durU}
        sub={clouds ? `${fmtBytes(clouds)} облаков` : r.recording ? `запись ${fmtBytes(r.recording.size_bytes)}` : r.source_kind}
      />
      <KpiTile
        className={styles.kpi}
        icon={
          <span className={styles.kpiIcon}>
            <StopMark />
          </span>
        }
        label="СТОП-эпизоды"
        help={
          stopEps.length ? (
            <>
              Сколько раз решение переходило в СТОП: <b>{episodesText(stopEps.length)}</b>, всего <b>{fmtNum(s.counts.STOP)}</b> {framesWord(s.counts.STOP)} СТОП.
            </>
          ) : (
            'Сколько раз решение переходило в СТОП. В этом прогоне — ни разу.'
          )
        }
        value={fmtNum(s.stop_episodes)}
        sub={epFrames ? (stopEps.length > 1 ? `первый: ${epFrames}` : epFrames) : 'нет СТОП'}
      />
      <KpiTile
        className={styles.kpi}
        icon={
          <span className={styles.kpiIcon}>
            <StopMark />
          </span>
        }
        label="Первый СТОП"
        help={
          fs ? (
            <>
              Кадр <b>{fs.frame}</b> — первый с решением СТОП; дистанция до препятствия в нём.
              {delay !== null && (
                <>
                  {' '}
                  Задержка — кадров от появления объекта в габарите по разметке: <b>{delay}</b>.
                </>
              )}
            </>
          ) : (
            'Первый кадр с решением СТОП и дистанция до препятствия в нём.'
          )
        }
        value={fs?.distance !== null && fs?.distance !== undefined ? fmtNum(fs.distance, 1) : '—'}
        unit={fs?.distance !== null && fs?.distance !== undefined ? 'м' : undefined}
        sub={fs ? `кадр ${fs.frame} · ${delay !== null ? `задержка ${delay}` : fmtDuration(fs.t)}` : 'нет СТОП'}
      />
      <KpiTile
        className={styles.kpi}
        label="Мин. дистанция"
        help="Ближайшее препятствие среди кадров СТОП; по разметке — ближняя грань объекта."
        value={s.distance_min !== null ? fmtNum(s.distance_min, 1) : '—'}
        unit={s.distance_min !== null ? 'м' : undefined}
        sub={labelMin !== null ? `разметка ${fmtMeters(labelMin)}` : s.distance_max !== null ? `макс. ${fmtMeters(s.distance_max)}` : 'нет СТОП'}
      />
      <KpiTile
        className={styles.kpi}
        label="Пропуски"
        help={
          misses?.basis === 'labels' ? (
            <>
              Объект в габарите по разметке, а решения СТОП нет.
              {misses.beforeDetection > 0 && (
                <>
                  {' '}
                  Из них <b>{misses.beforeDetection}</b> — до подтверждения объекта трекером.
                </>
              )}
            </>
          ) : (
            'Кадры СВОБОДНО или ВНИМАНИЕ внутри СТОП: объект был, решение на время снялось. Разметки нет — считаем по разрывам.'
          )
        }
        value={misses ? fmtNum(misses.count) : '—'}
        unit={misses ? framesWord(misses.count) : undefined}
        sub={misses ? (misses.count ? spansText(misses.spans, frameOf) : lanes ? 'против разметки' : 'нет разрывов') : '—'}
      />
      <KpiTile
        className={styles.kpi}
        variant="dark"
        label="p95 задержка"
        help="95 % кадров детектор обработал быстрее этого времени (без чтения файла). Бюджет — 100 мс на кадр при 10 Гц."
        value={fmtNum(s.latency_ms.p95, s.latency_ms.p95 < 10 ? 1 : 0)}
        unit="мс"
        sub={`p50 ${fmtNum(s.latency_ms.p50)} · макс ${fmtMs(s.latency_ms.max)}`}
      />
      <KpiTile
        className={styles.kpi}
        variant={ev && ev.false_stop_episodes === 0 ? 'green' : 'light'}
        label="Ложные тревоги"
        help={
          ev
            ? 'Эпизоды СТОП, где по разметке в габарите пусто: поезд остановился бы без причины.'
            : 'Считаются по разметке — у этой записи её нет. Загрузите разметку к записи и обработайте снова.'
        }
        value={ev ? fmtNum(ev.false_stop_episodes) : '—'}
        unit={ev && ev.false_stop_episodes > 0 ? plural(ev.false_stop_episodes, ['эпизод', 'эпизода', 'эпизодов']) : undefined}
        after={ev && ev.false_stop_episodes === 0 ? <GoodMark /> : undefined}
        sub={ev ? (ev.false_stop_frames ? `${fmtNum(ev.false_stop_frames)} ${framesWord(ev.false_stop_frames)} СТОП` : 'против разметки') : 'нет разметки'}
      />
    </div>
  );
}
