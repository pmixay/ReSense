// Сравнение (/compare?runs=a,b,…): 2–4 runs side by side — a KPI table with the best value per row,
// the decision strips on one time axis, the distances overlaid, and «что изменилось» when runs of
// one recording used different presets. The URL holds the selection (colour slots included).
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { usePresetSchema, useRuns } from '../../api/hooks';
import { Button, Card, Chip, EmptyState, ErrorBanner, PageHeader, Segmented, Spinner } from '../../components';
import { DECISION_CHIP_LABEL, fromLetter } from '../../lib/decisions';
import { fmtDuration, fmtMeters } from '../../lib/format';
import { MAX_COMPARE, RUN_COLORS, RUN_LINES, addToSlots, lineSwatch, parseRunSlots, reconnect, runUrl, slotsParam } from '../Runs/common/analysis';
import { Skeleton } from '../Runs/common/Bits';
import { LineChart, type ChartLine } from '../Runs/common/LineChart';
import { useUrlParams } from '../Runs/common/useUrlParams';
import { AlignedStrips } from './AlignedStrips';
import { useCompared, type Compared } from './data';
import { AddRun, Chooser } from './Pickers';
import { KpiTable, PresetDiff, presetGroup } from './Tables';
import styles from './Compare.module.css';

type Metric = 'nearest' | 'clear' | 'visibility';

function RunChip({ c, onRemove }: { c: Compared; onRemove: () => void }) {
  const missing = c.error?.status === 404;
  return (
    <span className={[styles.runChip, missing ? styles.runChipBad : ''].join(' ')}>
      <span className={styles.key} style={{ background: RUN_COLORS[c.slot] }} aria-hidden />
      {c.run ? (
        <Link to={runUrl(c.id)} className={styles.ell} title={c.run.name}>
          {c.run.name}
        </Link>
      ) : (
        <span className={styles.ell}>{missing ? 'прогон удалён' : c.error ? (c.error.offline ? 'нет связи' : 'ошибка') : '…'}</span>
      )}
      <button type="button" onClick={onRemove} aria-label={`Убрать из сравнения: ${c.run?.name ?? c.id}`}>
        ×
      </button>
    </span>
  );
}

function DistanceOverlay({ items }: { items: readonly Compared[] }) {
  const [picked, setPicked] = useState<Metric | null>(null);
  const withSeries = useMemo(() => items.filter((c) => c.series), [items]);
  const anyNearest = withSeries.some((c) => c.series?.nearest.some((v) => v !== null));
  const metric: Metric = picked ?? (withSeries.length && !anyNearest ? 'clear' : 'nearest');
  // stable between hovers: the chart rebuilds its paths only when the data or the metric change
  const lines = useMemo<ChartLine[]>(
    () =>
      withSeries.map((c) => {
        const s = c.series!;
        return { id: c.id, color: RUN_COLORS[c.slot], ...RUN_LINES[c.slot], t: s.t, v: metric === 'nearest' ? s.nearest : metric === 'clear' ? s.clear : s.visibility };
      }),
    [withSeries, metric],
  );
  return (
    <Card
      className={styles.dist}
      title="Дистанция"
      help={
        metric === 'nearest'
          ? 'Дистанция до препятствия в габарите у каждого прогона, по времени записи.'
          : metric === 'clear'
            ? 'Сколько метров пути свободно по мнению детектора.'
            : 'До какой дальности датчик видит путь.'
      }
      helpPlacement="bottom-start"
      headGap={6}
      actions={
        <>
          <Segmented<Metric>
            label="Что показать"
            size="sm"
            value={metric}
            onChange={setPicked}
            options={[
              { value: 'nearest', label: 'Объект', disabled: withSeries.length > 0 && !anyNearest },
              { value: 'clear', label: 'Путь' },
              { value: 'visibility', label: 'Видимость' },
            ]}
          />
        </>
      }
    >
      <div className={styles.legend}>
        {items.map((c) => (
          <span key={c.id} className={styles.legendItem} title={c.run?.name}>
            <i style={{ background: lineSwatch(c.slot) }} aria-hidden />
            <span className={styles.ell}>{c.run?.name ?? '…'}</span>
          </span>
        ))}
      </div>
      <div className={styles.chartBox}>
        {withSeries.length === 0 ? (
          <div className={styles.center}>
            <Spinner />
          </div>
        ) : (
          <LineChart
            lines={lines}
            unit="м"
            minSpan={metric === 'nearest' ? 1.5 : 10}
            ariaLabel="Дистанция по времени, все прогоны"
            tooltip={(t, idx) => (
              <>
                <div className={styles.tipHead}>{fmtDuration(t)}</div>
                {withSeries.map((c, i) => {
                  const k = idx[i];
                  const s = c.series!;
                  const inside = k >= 0 && t <= (s.t[s.t.length - 1] ?? 0) + 0.05;
                  const v = inside ? lines[i].v[k] : null;
                  return (
                    <div key={c.id} className={styles.tipRow}>
                      <i style={{ background: RUN_COLORS[c.slot] }} aria-hidden />
                      <b>{v !== null && v !== undefined ? fmtMeters(v) : '—'}</b>
                      <span>{inside ? `${DECISION_CHIP_LABEL[fromLetter(s.decisions[k])]} · кадр ${s.frame[k]}` : 'запись кончилась'}</span>
                    </div>
                  );
                })}
              </>
            )}
          />
        )}
      </div>
    </Card>
  );
}

export default function Compare() {
  const [params, update] = useUrlParams();
  const slots = useMemo(() => parseRunSlots(params), [params]);
  const chosen = slots.filter((s): s is string => !!s);
  const runs = useRuns({ refetchInterval: reconnect });
  const schema = usePresetSchema({ retry: false });
  const items = useCompared(slots);
  const ok = useMemo(() => items.filter((c) => !c.error), [items]);
  const group = presetGroup(ok);

  // each change starts from the latest requested slots (two quick removals both apply)
  const setSlots = (change: (current: (string | null)[]) => (string | null)[]) =>
    update((p) => {
      const v = slotsParam(change(parseRunSlots(p)));
      p.delete('a');
      p.delete('b');
      if (v) p.set('runs', v);
      else p.delete('runs');
    });
  const add = (id: string) => setSlots((s) => addToSlots(s, id));
  const remove = (id: string) => setSlots((s) => s.map((x) => (x === id ? null : x)));
  const toggle = (id: string) => setSlots((s) => (s.includes(id) ? s.map((x) => (x === id ? null : x)) : addToSlots(s, id)));

  const ready = ok.length >= 2;
  // a compared run that failed for another reason than «deleted» (e.g. the backend is down)
  const failed = items.find((c) => c.error && c.error.status !== 404);

  return (
    <>
      <PageHeader
        title="Сравнение"
        station={2}
        chips={
          <div className={styles.chips}>
            {items.map((c) => (
              <RunChip key={c.id} c={c} onRemove={() => remove(c.id)} />
            ))}
            {runs.data && chosen.length > 0 && chosen.length < MAX_COMPARE && <AddRun runs={runs.data} chosen={chosen} onAdd={add} />}
          </div>
        }
        actions={
          <Button variant="outline" icon="list" to="/runs">
            Все прогоны
          </Button>
        }
      />
      {ready ? (
        <section className={`grid-12 fill-viewport ${styles.grid}`}>
          <div className={styles.left}>
            <Card
              className={styles.stripsCard}
              title="Решения по кадрам"
              help="Полосы на общей шкале времени: одна секунда записи — одно место по горизонтали. Наведите, чтобы прочитать кадр каждого прогона; клик откроет кадр в плеере."
              helpPlacement="bottom-start"
              helpWidth={300}
              headGap={10}
            >
              <AlignedStrips items={ok} />
            </Card>
            <DistanceOverlay items={ok} />
          </div>
          <div className={styles.right}>
            <Card className={styles.kpiCard} title="Показатели" help="Лучшее значение в строке — на тёмной плашке (там, где лучше больше или меньше)." helpPlacement="bottom-end" headGap={8}>
              <div className={styles.tableScroll}>
                <KpiTable items={ok} />
              </div>
            </Card>
            {group && (
              <Card
                className={styles.diffCard}
                title="Что изменилось"
                badges={<Chip size="sm">{group[0].run?.recording?.name ?? 'одна запись'}</Chip>}
                help="Прогоны одной записи с разными пресетами: параметры детектора, которые отличаются."
                helpPlacement="top-end"
                headGap={8}
              >
                <div className={styles.tableScroll}>
                  <PresetDiff group={group} schema={schema.data} />
                </div>
              </Card>
            )}
          </div>
        </section>
      ) : (
        <Card
          className={`fill-viewport ${styles.chooseCard}`}
          // an error needs no title of its own: the banner says it
          title={runs.isError || failed ? undefined : chosen.length ? 'Добавьте ещё прогон' : 'Выберите прогоны'}
          help={runs.isError || failed ? undefined : `От 2 до ${MAX_COMPARE}: одна запись с разными пресетами или разные записи.`}
          helpPlacement="bottom-start"
        >
          {runs.isError || failed ? (
            <ErrorBanner error={runs.error ?? failed?.error} onRetry={() => void runs.refetch()} retrying={runs.isFetching} />
          ) : runs.isLoading || (chosen.length > 0 && items.some((c) => c.loading)) ? (
            <Skeleton rows={4} height={70} />
          ) : !runs.data?.length ? (
            <div className={styles.center}>
              <EmptyState
                icon="compare"
                title="Сравнивать пока нечего"
                action={
                  <Button variant="dark" icon="upload" to="/upload">
                    Загрузить запись
                  </Button>
                }
              >
                Нужны хотя бы два прогона.
              </EmptyState>
            </div>
          ) : (
            <Chooser runs={runs.data} chosen={chosen} onToggle={toggle} />
          )}
        </Card>
      )}
    </>
  );
}
