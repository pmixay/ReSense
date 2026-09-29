// Прямой эфир: the node's decision as it happens — from the real ROS 2 node (rosbridge,
// /resense/status) or from the backend's replay of a processed run (WS /api/live/sim). One shared
// view: the beacon with the distance, freshness, node stats, the last 30 s, objects, health and the
// 3D view (the run's stored clouds) or a top-down scheme drawn from the status JSON.
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePresetSchema, useRuns } from '../../api/hooks';
import type { Run } from '../../api/types';
import { rosbridgeUrl } from '../../api/ws';
import { Chip, PageHeader, Segmented } from '../../components';
import { Beacon } from './Beacon';
import { useLiveFeed } from './feed';
import { DetectionsCard, HealthCard, NodeCard } from './Panels';
import { SourceBar, type SourceKind } from './SourceBar';
import { MIN_VISIBILITY, VIEW_LABEL, buildSlots, type LiveView } from './timeline';
import { TimelineCard } from './TimelineCard';
import { store } from './useSize';
import { ViewCard } from './ViewCard';
import styles from './Live.module.css';

const KEY_SOURCE = 'resense.live.source';
const KEY_URL = 'resense.live.url';

const VIEW_DOT: Record<LiveView, string> = {
  idle: 'var(--hair-2)',
  connecting: 'var(--caution)',
  waiting: 'var(--caution)',
  live: 'var(--go)',
  stale: 'var(--fault)',
  paused: 'var(--ink)',
  ended: 'var(--ink)',
  error: 'var(--fault)',
};

/** The run the replay starts with: the newest with clouds (the 3D view needs them), else the newest. */
export function defaultRun(runs: readonly Run[] | undefined): Run | undefined {
  return runs?.find((r) => r.has_clouds && r.summary.n_frames > 0) ?? runs?.find((r) => r.summary.n_frames > 0) ?? runs?.[0];
}

export default function Live() {
  const [params] = useSearchParams();
  const [kind, setKind] = useState<SourceKind>(() => {
    const q = params.get('source') ?? store.get(KEY_SOURCE);
    return q === 'ros' ? 'ros' : 'sim';
  });
  const [url, setUrl] = useState(() => params.get('url') ?? store.get(KEY_URL) ?? rosbridgeUrl());
  const [runId, setRunId] = useState<string | null>(() => params.get('run'));
  const [speed, setSpeed] = useState(1);
  const [loop, setLoop] = useState(true);
  const [snap, feed] = useLiveFeed();

  const runs = useRuns({ retry: false });
  const schema = usePresetSchema({ retry: false });
  const specDefault = (key: string, fallback: number) => {
    const v = schema.data?.find((s) => s.key === key)?.default;
    return typeof v === 'number' ? v : fallback;
  };
  const minVisibility = specDefault('health.min_visibility', MIN_VISIBILITY);
  const latencyBudget = specDefault('health.latency_budget_ms', 100);
  const slots = useMemo(() => buildSlots(snap.samples, snap.timeNow), [snap.samples, snap.timeNow]);

  // pick a run once the list arrives (or when the chosen one disappears)
  const list = runs.isError ? undefined : runs.data;
  useEffect(() => {
    if (!list) return;
    if (!runId || !list.some((r) => r.id === runId)) setRunId(defaultRun(list)?.id ?? null);
  }, [list, runId]);
  const run = list?.find((r) => r.id === runId);

  useEffect(() => store.set(KEY_SOURCE, kind), [kind]);
  useEffect(() => store.set(KEY_URL, url), [url]);

  const changeKind = (k: SourceKind) => {
    if (k === kind) return;
    feed.stop();
    setKind(k);
  };

  const fresh = snap.view === 'live';
  // the 3D view follows the run on air (it may differ from the selection until «Запустить»)
  const liveRunId = snap.source?.kind === 'sim' ? snap.source.runId : null;
  const shownRun = (kind === 'sim' && liveRunId ? list?.find((r) => r.id === liveRunId) : undefined) ?? run;

  return (
    <>
      <PageHeader
        title="Прямой эфир"
        station={3}
        chips={
          <Chip variant="outline" dot={VIEW_DOT[snap.view]} aria-live="polite">
            {snap.reconnecting ? 'переподключение…' : VIEW_LABEL[snap.view]}
          </Chip>
        }
        actions={
          <Segmented
            tone="white"
            label="Источник эфира"
            value={kind}
            onChange={changeKind}
            options={[
              { value: 'ros', label: 'Узел ROS 2', icon: 'live' },
              { value: 'sim', label: 'Симуляция', icon: 'play' },
            ]}
          />
        }
      />
      <section className={`grid-12 fill-viewport ${styles.live}`}>
        <SourceBar
          kind={kind}
          snap={snap}
          feed={feed}
          url={url}
          onUrl={setUrl}
          runs={list}
          runsLoading={runs.isLoading}
          runsError={runs.isError ? runs.error : null}
          onRetryRuns={() => void runs.refetch()}
          run={run}
          onRun={setRunId}
          speed={speed}
          onSpeed={setSpeed}
          loop={loop}
          onLoop={setLoop}
        />
        <Beacon snap={snap} className={styles.beacon} />
        <ViewCard snap={snap} kind={kind} run={shownRun} fresh={fresh} className={styles.view} />
        <NodeCard snap={snap} kind={kind} latency={slots.latency} latencyBudget={latencyBudget} className={styles.node} />
        <TimelineCard slots={slots} live={fresh} className={styles.timeline} />
        <DetectionsCard snap={snap} fresh={fresh} className={styles.dets} />
        <HealthCard snap={snap} fresh={fresh} minVisibility={minVisibility} className={styles.health} />
      </section>
    </>
  );
}
