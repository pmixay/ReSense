// Прямой эфир: the node's decision as it happens — from the real ROS 2 node (rosbridge,
// /resense/status) or from the backend's replay of a processed run (WS /api/live/sim). One shared
// view: the beacon with the distance, freshness, node stats, the last 30 s, objects, health and the
// 3D view (the run's stored clouds) or a top-down scheme drawn from the status JSON.
import { useEffect, useMemo, useRef, useState } from 'react';
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
import { store } from './storage';
import { ViewCard } from './ViewCard';
import styles from './Live.module.css';

const RECONNECT_MS = 3000;
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

/** Space toggles the replay unless the focus is on a control that uses the key itself. */
const OWN_SPACE = 'input, textarea, select, button, a[href], [role="radio"], [role="slider"], [role="option"], [role="listbox"], [contenteditable="true"]';

export default function Live() {
  const [params, setParams] = useSearchParams();
  const [kind, setKind] = useState<SourceKind>(() => {
    const q = params.get('source') ?? store.get(KEY_SOURCE);
    return q === 'ros' ? 'ros' : 'sim';
  });
  const [url, setUrl] = useState(() => params.get('url') ?? store.get(KEY_URL) ?? rosbridgeUrl());
  const [runId, setRunId] = useState<string | null>(() => params.get('run'));
  const [speed, setSpeed] = useState(1);
  const [loop, setLoop] = useState(true);
  const [snap, feed] = useLiveFeed();

  // while the backend is unreachable the lists are asked again: the page comes back by itself
  const runs = useRuns({ retry: false, refetchInterval: (q) => (q.state.error?.offline ? RECONNECT_MS : false) });
  const schema = usePresetSchema({ retry: false, refetchInterval: (q) => (q.state.error?.offline ? RECONNECT_MS : false) });
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

  // the address bar follows the choice (a link or a reload opens the same source and run)
  useEffect(() => {
    const next = new URLSearchParams(params);
    next.set('source', kind);
    if (kind === 'sim' && runId) next.set('run', runId);
    else next.delete('run');
    if (kind === 'ros' && url.trim()) next.set('url', url.trim());
    else next.delete('url');
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
  }, [kind, runId, url, params, setParams]);

  const changeKind = (k: SourceKind) => {
    if (k === kind) return;
    feed.reset(); // the other source's frames are not this one's
    setKind(k);
  };

  // Space: start / pause / resume the replay of the selected run (one listener; the state it acts
  // on is read at the key press)
  const latest = useRef({ kind, run, snap, speed, loop });
  useEffect(() => {
    latest.current = { kind, run, snap, speed, loop };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const { kind: k, run: r, snap: sn, speed: sp, loop: lp } = latest.current;
      if (k !== 'sim' || !r) return;
      if (e.key !== ' ' || e.repeat || e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.target instanceof Element && e.target.closest(OWN_SPACE)) return;
      e.preventDefault();
      const onThis = sn.source?.kind === 'sim' && sn.source.runId === r.id;
      if (!onThis || (sn.link !== 'open' && sn.link !== 'connecting')) {
        const resume = onThis && sn.link !== 'ended' && typeof sn.msg?.pos === 'number' ? sn.msg.pos : 0;
        feed.start({ kind: 'sim', runId: r.id, speed: sp, loop: lp, startPos: resume });
      } else if (sn.paused) feed.play();
      else feed.pause();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [feed]);

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
            {snap.reconnecting ? 'переподключение…' : snap.view === 'idle' ? (kind === 'sim' ? 'не запущен' : 'не подключено') : VIEW_LABEL[snap.view]}
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
        <Beacon snap={snap} kind={kind} className={styles.beacon} />
        <ViewCard snap={snap} kind={kind} run={shownRun} fresh={fresh} className={styles.view} />
        <NodeCard snap={snap} kind={kind} latency={slots.latency} latencyBudget={latencyBudget} className={styles.node} />
        <TimelineCard slots={slots} live={fresh} className={styles.timeline} />
        <DetectionsCard snap={snap} fresh={fresh} className={styles.dets} />
        <HealthCard snap={snap} fresh={fresh} minVisibility={minVisibility} className={styles.health} />
      </section>
    </>
  );
}
