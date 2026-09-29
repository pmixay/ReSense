// «Дистанция»: the detector's nearest in-gauge distance over time with the labelled object's extent as
// a band, the first STOP and the minimum marked; a toggle shows the clear track length or the
// visibility instead. Hover shows frame / time / decision / value; a click opens the player there.
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { RunDetail, RunLabels, RunSeries } from '../../api/types';
import { Card, DecisionStrip, ErrorBanner, Segmented, Spinner } from '../../components';
import { DECISION_CHIP_LABEL, fromLetter } from '../../lib/decisions';
import { fmtDuration, fmtMeters, fmtRange } from '../../lib/format';
import { playerUrl } from '../Runs/common/analysis';
import { LineChart, type ChartBand, type ChartPoint } from '../Runs/common/LineChart';
import styles from './RunDetail.module.css';

type Metric = 'nearest' | 'clear' | 'visibility';

const HELP: Record<Metric, string> = {
  nearest: 'Дистанция до препятствия в габарите по кадрам; полоса — объект по разметке (от ближней до дальней грани), внизу — решения.',
  clear: 'Сколько метров пути впереди свободно по мнению детектора в каждом кадре.',
  visibility: 'До какой дальности датчик видит путь (падает в пыли, тумане, на поворотах).',
};

export function DistanceCard({
  r,
  series,
  seriesError,
  onRetry,
  labels,
  cursorPos,
}: {
  r: RunDetail;
  series: RunSeries | undefined;
  seriesError: unknown;
  onRetry: () => void;
  labels: RunLabels | undefined;
  cursorPos: number | null;
}) {
  const navigate = useNavigate();
  const hasNearest = !!series?.nearest.some((v) => v !== null);
  const [picked, setPicked] = useState<Metric | null>(null);
  const metric: Metric = picked ?? (series && !hasNearest ? 'clear' : 'nearest');
  const band = useMemo<ChartBand | null>(
    () => (series && metric === 'nearest' && labels?.available && labels.near.length === series.t.length ? { t: series.t, lo: labels.near, hi: labels.far } : null),
    [series, metric, labels],
  );
  // frames without a detection: «not confirmed yet» where the labels have an object in the gauge
  const emptyLabel = useCallback((i: number) => (band && band.lo[i] !== null && band.lo[i] !== undefined ? 'объект не подтверждён' : 'нет объекта в габарите'), [band]);
  const bandRange = useMemo(() => {
    if (!band) return null;
    const lo = band.lo.filter((v): v is number => v !== null);
    const hi = band.hi.filter((v): v is number => v !== null);
    return lo.length ? fmtRange(Math.min(...lo), Math.max(...hi)) : null;
  }, [band]);

  const values = !series ? [] : metric === 'nearest' ? series.nearest : metric === 'clear' ? series.clear : series.visibility;
  const lines = useMemo(() => (series ? [{ id: metric, color: '#16151A', t: series.t, v: values }] : []), [series, metric, values]);

  const points = useMemo<ChartPoint[]>(() => {
    if (!series || metric !== 'nearest') return [];
    const out: ChartPoint[] = [];
    const d = series.decisions;
    let minI = -1;
    for (let i = 0; i < d.length; i += 1) {
      const v = series.nearest[i];
      if (v === null || d[i] !== 'S') continue;
      if (minI < 0 || v < (series.nearest[minI] as number)) minI = i;
    }
    let cautions = 0;
    for (let i = 0; i < d.length && cautions < 60; i += 1) {
      const v = series.nearest[i];
      if (d[i] === 'C' && v !== null) {
        out.push({ t: series.t[i], v, kind: 'caution' });
        cautions += 1;
      }
    }
    if (minI >= 0) out.push({ t: series.t[minI], v: series.nearest[minI] as number, kind: 'min', label: `мин ${fmtMeters(series.nearest[minI])}` });
    const first = d.indexOf('S');
    if (first >= 0 && series.nearest[first] !== null) out.push({ t: series.t[first], v: series.nearest[first] as number, kind: 'stop' });
    return out;
  }, [series, metric]);

  const unitLabel = metric === 'nearest' ? 'детектор' : metric === 'clear' ? 'свободный путь' : 'видимость';

  return (
    <Card
      className={styles.dist}
      title="Дистанция"
      help={HELP[metric]}
      helpPlacement="bottom-start"
      headGap={4}
      actions={
        <>
          <div className={styles.chartLegend}>
            <span className={bandRange ? styles.hideNarrow : undefined}>
              <i className={styles.lgLine} aria-hidden />
              {unitLabel}
            </span>
            {bandRange && (
              <span>
                <i className={styles.lgBand} aria-hidden />
                разметка {bandRange}
              </span>
            )}
          </div>
          <Segmented<Metric>
            label="Что показать"
            size="sm"
            value={metric}
            onChange={setPicked}
            options={[
              { value: 'nearest', label: 'Объект', disabled: !!series && !hasNearest },
              { value: 'clear', label: 'Путь' },
              { value: 'visibility', label: 'Видимость' },
            ]}
          />
        </>
      }
    >
      <div className={styles.chartBox}>
        {seriesError ? (
          <div className={styles.center}>
            <ErrorBanner error={seriesError} onRetry={onRetry} compact />
          </div>
        ) : !series ? (
          <div className={styles.center}>
            <Spinner />
          </div>
        ) : (
          <LineChart
            lines={lines}
            band={band}
            points={points}
            unit="м"
            minSpan={metric === 'nearest' ? 1.5 : 10}
            emptyLabel={metric === 'nearest' ? emptyLabel : undefined}
            cursor={cursorPos !== null && cursorPos < series.t.length ? series.t[cursorPos] : null}
            ariaLabel={`График: ${unitLabel} по времени`}
            footer={<DecisionStrip decisions={series.decisions} height={7} radius={3.5} ariaLabel="Решения по времени" />}
            onPick={(_t, idx) => idx[0] >= 0 && navigate(playerUrl(r.id, idx[0]))}
            tooltip={(_t, idx) => {
              const i = idx[0];
              if (i < 0) return null;
              const dec = fromLetter(series.decisions[i] ?? 'G');
              const v = values[i];
              const near = band ? band.lo[i] : null;
              return (
                <>
                  <div className={styles.tipHead}>
                    кадр {series.frame[i]} · {fmtDuration(series.t[i])}
                  </div>
                  <div className={styles.tipBig}>
                    {DECISION_CHIP_LABEL[dec]}
                    {metric === 'nearest' && v !== null && v !== undefined ? ` ${fmtMeters(v)}` : ''}
                  </div>
                  {metric !== 'nearest' && (
                    <div className={styles.tipSub}>
                      {metric === 'clear' ? 'свободный путь' : 'видимость'} {fmtMeters(v, 0)}
                    </div>
                  )}
                  {near !== null && near !== undefined && <div className={styles.tipSub}>разметка {fmtRange(near, band?.hi[i] ?? near)}</div>}
                </>
              );
            }}
          />
        )}
      </div>
    </Card>
  );
}
