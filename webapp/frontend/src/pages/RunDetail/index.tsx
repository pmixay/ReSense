// Прогон (/runs/:id, mockup run.html): KPIs, the decision timeline with the labels lane, the distance
// chart, events, the 3D preview, downloads and the evaluation against labels. Rename / delete in «⋯».
import { useCallback, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { usePresetSchema, useRun, useRunLabels, useRuns, useRunSeries } from '../../api/hooks';
import type { RunDetail as RunDetailT } from '../../api/types';
import { Button, Card, Chip, DecisionChip, EmptyState, ErrorBanner, PageHeader, useRailSub } from '../../components';
import { decisionAt } from '../../lib/decisions';
import { fmtBytes, fmtFrames, fmtMeters, fmtRelDate } from '../../lib/format';
import { compareUrl, playerUrl, posOfFrame, reconnect } from '../Runs/common/analysis';
import { Skeleton } from '../Runs/common/Bits';
import { Menu } from '../Runs/common/Menu';
import { useMedia } from '../Runs/common/useMedia';
import { DeleteDialog, RenameDialog } from '../Runs/common/RunDialogs';
import { DownloadsCard, EvalCard, EventsCard, PresetChip, PreviewCard } from './Cards';
import { DistanceCard } from './DistanceCard';
import { Kpis } from './Kpis';
import { Timeline } from './Timeline';
import styles from './RunDetail.module.css';

function Badge({ r, short }: { r: RunDetailT; short: boolean }) {
  const fs = r.summary.first_stop;
  if (fs) return <DecisionChip decision="STOP" size="lg" extra={`${short ? 'кадр' : 'с кадра'} ${fs.frame}${fs.distance !== null ? ` · ${fmtMeters(fs.distance)}` : ''}`} />;
  if (r.summary.counts.FAULT > 0) return <DecisionChip decision="FAULT" size="lg" extra={fmtFrames(r.summary.counts.FAULT)} />;
  return <DecisionChip decision="GO" size="lg" label="БЕЗ СТОП" />;
}

function LoadingBento() {
  return (
    <section className={styles.grid} aria-busy>
      <div className={styles.kpis}>
        {Array.from({ length: 8 }, (_, i) => (
          <Card key={i} padding="sm">
            <Skeleton rows={2} height={22} />
          </Card>
        ))}
      </div>
      <Card className={styles.tl}>
        <Skeleton rows={2} height={44} />
      </Card>
      <Card className={styles.dist}>
        <Skeleton rows={5} height={40} />
      </Card>
      <div className={styles.mid}>
        <Card className={styles.ev}>
          <Skeleton rows={4} height={44} />
        </Card>
      </div>
      <div className={styles.side}>
        <div className={styles.pv} />
        <Card className={styles.dl}>
          <Skeleton rows={2} height={30} />
        </Card>
      </div>
    </section>
  );
}

export default function RunDetail() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const run = useRun(id, { retry: (n, err) => err.status !== 404 && !err.offline && n < 1, refetchInterval: reconnect });
  const r = run.data;
  // after the run itself, so a wrong id costs one 404, not two
  const series = useRunSeries(r ? id : null, { retry: (n, err) => err.status !== 404 && n < 1 });
  const wantLabels = !!r && (!!r.summary.eval || !!series.data?.labels_in_gauge);
  const labels = useRunLabels(wantLabels ? id : null);
  const schema = usePresetSchema({ retry: false });
  const runs = useRuns({ retry: false, refetchInterval: reconnect });
  const [hoverPos, setHoverPos] = useState<number | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  useRailSub(r?.name);
  const narrow = useMedia('(max-width: 1320px)');

  const frames = series.data?.frame;
  const posOf = useCallback((frame: number) => posOfFrame(frames, frame), [frames]);
  const frameOf = useCallback((pos: number) => frames?.[pos] ?? pos, [frames]);
  const labelsInGauge = series.data?.labels_in_gauge ?? (labels.data?.available ? labels.data.in_gauge : null);

  // the frame the 3D card shows: the hovered event, else the first STOP, else the first event
  const defaultPos = useMemo(() => {
    if (!r) return 0;
    if (r.summary.first_stop) return posOf(r.summary.first_stop.frame);
    if (r.events.length) return posOf(r.events[0].first_frame);
    return 0;
  }, [r, posOf]);
  const focusPos = hoverPos ?? defaultPos;

  // «Сравнить»: this run and the newest other run of the same recording
  const sibling = r && runs.data?.find((x) => x.id !== r.id && x.recording_id !== null && x.recording_id === r.recording_id);
  const notFound = run.error?.status === 404;
  const decisions = series.data?.decisions ?? r?.summary.decisions ?? '';
  // a default name is "<recording> · <preset>": the preset chip already says the second half
  const suffix = r ? ` · ${r.preset.name}` : '';
  const title = r && r.name.endsWith(suffix) && r.name.length > suffix.length ? r.name.slice(0, -suffix.length) : r?.name;

  return (
    <>
      <PageHeader
        title={<span className={styles.title}>{title ?? (notFound ? 'Прогон не найден' : 'Прогон')}</span>}
        docTitle={r?.name ?? 'Прогон'}
        eyebrow="Прогон"
        back={{ to: '/runs', label: 'К прогонам' }}
        badge={r ? <Badge r={r} short={narrow} /> : undefined}
        chips={
          r ? (
            <>
              <Chip variant="outline" className={styles.hideNarrow}>
                {r.recording ? fmtBytes(r.recording.size_bytes) : 'запись удалена'}
              </Chip>
              <PresetChip r={r} schema={schema.data} />
              <Chip variant="outline" className={styles.hideNarrow}>
                {fmtRelDate(r.created_at)}
              </Chip>
            </>
          ) : undefined
        }
        actions={
          r ? (
            <>
              <Button variant="outline" icon="compare" to={compareUrl(sibling ? [r.id, sibling.id] : [r.id])}>
                Сравнить
              </Button>
              <Button variant="dark" icon="play" to={playerUrl(r.id)} aria-label="Открыть в плеере">
                {narrow ? 'Плеер' : 'Открыть в плеере'}
              </Button>
              <Menu
                label="Действия с прогоном"
                variant="white"
                size="lg"
                items={[
                  { label: 'Переименовать', icon: 'edit', onSelect: () => setRenaming(true) },
                  { label: 'Удалить', icon: 'trash', onSelect: () => setDeleting(true) },
                ]}
              />
            </>
          ) : undefined
        }
      />
      {notFound ? (
        <div className={styles.notFound}>
          <EmptyState
            icon="list"
            title="Возможно, его удалили"
            action={
              <Button variant="dark" icon="arrow-left" to="/runs">
                К прогонам
              </Button>
            }
          />
        </div>
      ) : !r && run.isError ? (
        <ErrorBanner error={run.error} onRetry={() => void run.refetch()} retrying={run.isFetching} />
      ) : !r ? (
        <LoadingBento />
      ) : (
        <section className={styles.grid}>
          <Kpis r={r} series={series.data} labels={labels.data} frameOf={frameOf} />
          <Timeline r={r} series={series.data} labelsInGauge={labelsInGauge} playhead={focusPos} frameOf={frameOf} posOf={posOf} />
          <DistanceCard
            r={r}
            series={series.data}
            seriesError={series.isError ? series.error : null}
            onRetry={() => void series.refetch()}
            labels={labels.data}
            cursorPos={hoverPos}
          />
          <div className={styles.mid}>
            <EventsCard r={r} posOf={posOf} labelsInGauge={labelsInGauge} selected={hoverPos} onSelect={setHoverPos} />
            {r.summary.eval && <EvalCard ev={r.summary.eval} />}
          </div>
          <div className={styles.side}>
            <PreviewCard r={r} pos={focusPos} frame={frameOf(focusPos)} decision={decisionAt(decisions, focusPos) ?? 'GO'} />
            <DownloadsCard r={r} />
          </div>
        </section>
      )}
      <RenameDialog run={renaming && r ? r : null} onClose={() => setRenaming(false)} />
      <DeleteDialog run={deleting && r ? r : null} onClose={() => setDeleting(false)} onDeleted={() => navigate('/runs', { replace: true })} />
    </>
  );
}
