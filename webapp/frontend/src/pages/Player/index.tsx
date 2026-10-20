// One responsive workspace in the shared application shell. The existing engine owns playback;
// the modeled display, controls, telemetry and timeline read the same snapshot.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { usePresetSchema, useRun, useRunClouds, useRunSeries } from '../../api/hooks';
import type { ApiError } from '../../api/client';
import type { RunDetail } from '../../api/types';
import { Button, ErrorBanner, Spinner } from '../../components';
import { cautionText, decisionAt } from '../../lib/decisions';
import { stepSpeed } from '../../player/clock';
import { PlayerEngine, type EngineSnapshot } from '../../player/engine';
import { eventMarks, nextEventPos, prevEventPos } from '../../player/events';
import type { CamMode } from '../../player/geometry';
import type { PlayerScene } from '../../player/scene';
import { CAMERAS, confirmTime, minVisibility, parsePlayerParams, playerSearch, scrubberMarkers, type PlayerUrlState } from './cab';
import { Hud, type OverlaySink } from './Hud';
import { ViewControls } from './ViewControls';
import { PickerConsole, RunPickerGlass } from './RunPicker';
import { Scrubber } from './Scrubber';
import { DecisionTile, DistanceTile, HealthTile, MapTile, MetricsTile } from './Tiles';
import { useFullscreen, usePlayerKeys } from './useCab';
import { World } from './World';
import { TelemetryTray } from './TelemetryTray';
import { useDockHeight } from './useDockHeight';
import styles from './Player.module.css';
import { useNavigationPreview } from '../../lib/navigationPreview';

// ---------------------------------------------------------------- the stage

function useBack(runId?: string) {
  const navigate = useNavigate();
  const location = useLocation();
  return useCallback(() => {
    if (location.key !== 'default') navigate(-1);
    else navigate(runId ? `/runs/${encodeURIComponent(runId)}` : '/');
  }, [location.key, navigate, runId]);
}

type Fullscreen = ReturnType<typeof useFullscreen>;
interface CabChrome {
  fs: Fullscreen;
  expanded: boolean;
  toggleHeight: () => void;
}

/** Fullscreen state outlives run switches and the picker; AppShell remains the fullscreen element. */
const ChromeContext = createContext<CabChrome>({ expanded: false, toggleHeight: () => undefined, fs: { active: false, real: false, pseudo: false, toggle: () => undefined, exit: async () => undefined } });

interface StageProps {
  children: ReactNode;
  state?: string;
  stageRef?: React.RefObject<HTMLDivElement>;
}

/** Normal page flow; controls and telemetry retain their native CSS size. */
function Stage({ children, state, stageRef }: StageProps) {
  return (
    <div ref={stageRef} className={styles.workspace} data-player-workspace data-state={state}>
      {children}
    </div>
  );
}

function SceneLayer({ children }: { children: ReactNode }) {
  return <div className={styles.sceneAnchor}><div className={styles.sceneLayer} data-train-backdrop>{children}</div></div>;
}

/** The console tray while a run loads: the scrubber's shape, still. */
function TraySkeleton() {
  return (
    <div className={`${styles.scrub} ${styles.scrubSkel}`} aria-hidden>
      <i className={styles.skPlay} />
      <i className={styles.skGrp} />
      <i className={styles.skGrp} />
      <i className={styles.skText} />
      <i className={styles.skLane} />
      <i className={styles.skSpd} />
    </div>
  );
}

/** The console tray when a run cannot be shown: where to go instead. */
function TrayActions() {
  return (
    <div className={`${styles.scrub} ${styles.scrubPick}`}>
      <Button variant="dark" icon="play" to="/player">
        Выбрать прогон
      </Button>
      <Button variant="outline" icon="list" to="/runs">
        Все прогоны
      </Button>
    </div>
  );
}

/** Picker, loading and error states participate in the same page layout. */
function CabShell({ runId, runName, glass, console: cons }: { runId?: string; runName?: string; glass: ReactNode; console?: ReactNode }) {
  const displayRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  useDockHeight(stageRef, dockRef);
  const sceneRef = useRef<PlayerScene | null>(null);
  const sink = useRef<OverlaySink | null>(null);
  const back = useBack(runId);
  const { fs } = useContext(ChromeContext);
  // without a run only F and Esc mean something; every other key keeps its default
  usePlayerKeys({ fullscreen: fs.toggle, escape: () => (fs.active ? void fs.exit() : back()) });
  return (
    <Stage stageRef={stageRef}>
      <SceneLayer>
        <World engine={null} mode="cab" pixelRatio={Math.min(2, window.devicePixelRatio || 1)} cloudBudget={null} displayRef={displayRef} sceneRef={sceneRef} sink={sink} onFreeChange={() => undefined} onError={() => undefined} />
      </SceneLayer>
      <div ref={displayRef} className={styles.stateArea}>{glass}</div>
      <div ref={dockRef} className={styles.controlDock} data-player-controls>
        <ViewControls runId={runId} runName={runName} decision={null} fullscreen={fs.active} onFullscreen={fs.toggle} />
        {cons}
      </div>
    </Stage>
  );
}

// ---------------------------------------------------------------- route

export default function Player() {
  const preview = useNavigationPreview();
  const { runId } = useParams();
  const rootRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const toggleHeight = useCallback(() => setExpanded(value => !value), []);
  const fs = useFullscreen(rootRef);
  const chrome = useMemo(() => ({ fs, expanded, toggleHeight }), [fs, expanded, toggleHeight]);
  useEffect(() => {
    if (preview) return;
    document.title = 'Плеер · ReSense';
  }, [preview]);
  return (
    <div ref={rootRef} className={styles.root} data-expanded={expanded || undefined}>
      <ChromeContext.Provider value={chrome}>
        {runId ? <PlayerRun key={runId} runId={runId} /> : <CabShell glass={<RunPickerGlass />} console={<PickerConsole />} />}
      </ChromeContext.Provider>
    </div>
  );
}

function PlayerRun({ runId }: { runId: string }) {
  const [params] = useSearchParams();
  const initial = useRef<PlayerUrlState>(parsePlayerParams(params));
  // an unreachable backend is asked again every few seconds (the banner says it reconnects itself)
  const run = useRun(runId, { retry: false, refetchInterval: (q) => (q.state.error?.offline ? 3000 : false) });
  const series = useRunSeries(runId, { enabled: !!run.data });
  const clouds = useRunClouds(runId, { enabled: !!run.data?.has_clouds });

  // a failed background refetch keeps the cab on screen: only a run that never arrived is an error
  if (!run.data && run.isError) {
    const gone = run.error.status === 404;
    return (
      <CabShell
        runId={runId}
        glass={
          <div className={styles.glassCenter}>
            <div className={styles.glassCard}>
              <ErrorBanner
                error={run.error}
                title="Прогон не открылся"
                onRetry={gone ? undefined : () => void run.refetch()}
                retrying={run.isFetching}
              />
            </div>
          </div>
        }
        console={<TrayActions />}
      />
    );
  }
  if (!run.data) {
    return (
      <CabShell
        runId={runId}
        glass={
          <div className={styles.glassCenter}>
            <Spinner size={34} tone="light" label="Загрузка прогона" />
          </div>
        }
        console={<TraySkeleton />}
      />
    );
  }
  return (
    <Cab
      run={run.data}
      seriesT={series.data?.t ?? null}
      seriesFrames={series.data?.frame ?? null}
      latency={series.data?.latency_ms ?? null}
      cloudFrames={clouds.data?.frames ?? null}
      cloudBudget={clouds.data?.points ?? null}
      cloudIndex={{ loading: clouds.isLoading, error: clouds.data ? null : clouds.error, retry: () => void clouds.refetch() }}
      initial={initial.current}
    />
  );
}

// ---------------------------------------------------------------- the cab

const IDLE: EngineSnapshot = {
  n: 0,
  pos: 0,
  playing: false,
  speed: 1,
  loop: false,
  frame: null,
  framePos: null,
  buffering: false,
  framesError: null,
  cloudPos: null,
  cloudLoading: false,
  cloudError: null,
  motion: { v: 0, source: null },
  playFps: null,
};
const noopSubscribe = () => () => undefined;

interface CabProps {
  run: RunDetail;
  seriesT: readonly number[] | null;
  seriesFrames: readonly number[] | null;
  latency: readonly number[] | null;
  cloudFrames: readonly number[] | null;
  cloudBudget: number | null;
  /** the run's cloud list (GET /clouds): while it loads nothing can be drawn; a failure is retried by hand */
  cloudIndex: { loading: boolean; error: ApiError | null; retry: () => void };
  initial: PlayerUrlState;
}

function Cab({ run, seriesT, seriesFrames, latency, cloudFrames, cloudBudget, cloudIndex, initial }: CabProps) {
  const n = run.summary.n_frames;
  const hasClouds = run.has_clouds && run.cloud_frames > 0;
  const back = useBack(run.id);
  const schema = usePresetSchema();
  const stageRef = useRef<HTMLDivElement>(null);
  const displayRef = useRef<HTMLDivElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  useDockHeight(stageRef, dockRef);
  useEffect(() => {
    document.title = `${run.name} · Плеер · ReSense`;
    return () => {
      document.title = 'Плеер · ReSense';
    };
  }, [run.name]);

  // the engine lives as long as the run (StrictMode mounts twice: each mount gets its own)
  const [engine, setEngine] = useState<PlayerEngine | null>(null);
  const startRef = useRef(initial);
  useEffect(() => {
    const s = startRef.current;
    const e = new PlayerEngine({ id: run.id, n, t: null, clouds: [] }, { initialPos: s.pos ?? 0, speed: s.speed });
    setEngine(e);
    if (s.pos === null) e.play();
    return () => {
      e.dispose();
      setEngine(null);
    };
  }, [run.id, n]);
  useEffect(() => {
    engine?.updateRun({ t: seriesT });
  }, [engine, seriesT]);
  useEffect(() => {
    engine?.updateRun({ clouds: hasClouds ? (cloudFrames ?? []) : [] });
  }, [engine, cloudFrames, hasClouds]);

  // before the engine exists (the first paint) the console already shows the deep link's position
  const idle = useMemo<EngineSnapshot>(
    () => ({ ...IDLE, n, pos: Math.min(Math.max(0, n - 1), startRef.current.pos ?? 0), speed: startRef.current.speed }),
    [n],
  );
  const snap = useSyncExternalStore(engine?.subscribe ?? noopSubscribe, engine?.getSnapshot ?? (() => idle));

  const [mode, setMode] = useState<CamMode>(initial.cam);
  const [free, setFree] = useState(false);
  const [webglError, setWebglError] = useState<string | null>(null);
  const sink = useRef<OverlaySink | null>(null);
  const sceneRef = useRef<PlayerScene | null>(null);
  const register = useCallback((s: OverlaySink | null) => {
    sink.current = s;
  }, []);

  // events
  const marks = useMemo(() => eventMarks(run.events, seriesFrames), [run.events, seriesFrames]);
  const markers = useMemo(() => scrubberMarkers(marks, n), [marks, n]);
  const posLabel = useCallback((p: number) => String(seriesFrames?.[p] ?? p), [seriesFrames]);

  const pos = snap.pos;
  const frame = snap.frame;
  const decision = frame && snap.framePos === pos ? frame.decision : (decisionAt(run.summary.decisions, pos) ?? frame?.decision ?? null);
  const frameNo = frame?.frame ?? seriesFrames?.[pos] ?? pos;
  const lastFrameNo = (seriesFrames?.[n - 1] ?? n - 1) + 1;
  const confirmS = confirmTime(run, schema.data?.find((p) => p.key === 'tracking.confirm_time_s')?.default as number | undefined);
  const minVis = minVisibility(run, schema.data?.find((p) => p.key === 'health.min_visibility')?.default as number | undefined);

  // controls
  const { fs, expanded, toggleHeight } = useContext(ChromeContext);
  const seek = useCallback((p: number) => engine?.seek(p), [engine]);
  const stepBy = useCallback((d: number) => engine?.step(d), [engine]);
  const prevEv = prevEventPos(marks, pos);
  const nextEv = nextEventPos(marks, pos);
  const actions = {
    toggle: () => engine?.toggle(),
    step: stepBy,
    prevEvent: () => {
      const p = prevEventPos(marks, engine?.clock.pos ?? pos);
      if (p !== null) {
        engine?.pause();
        engine?.seek(p);
      }
    },
    nextEvent: () => {
      const p = nextEventPos(marks, engine?.clock.pos ?? pos);
      if (p !== null) {
        engine?.pause();
        engine?.seek(p);
      }
    },
    camera: (i: number) => setMode(CAMERAS[i] ?? 'cab'),
    speed: (dir: 1 | -1) => engine?.setSpeed(stepSpeed(engine.clock.speed, dir)),
    fullscreen: fs.toggle,
    escape: () => {
      if (sceneRef.current?.isFree) sceneRef.current.resetView();
      else if (fs.active) void fs.exit();
      else back();
    },
  };
  usePlayerKeys(actions, !!engine);

  // the URL follows the player (replace, no history entries): once a second while playing, shortly
  // after a pause, seek, speed or camera change — a copied link opens where the jury is looking.
  // Written straight into the current history entry, and only while it is still this run's: a
  // router navigation would resolve later and could land on the entry the browser's back button
  // has just returned to (another run's position written into it).
  const urlPos = snap.playing ? -1 : pos;
  useEffect(() => {
    if (!engine) return;
    const path = `/player/${encodeURIComponent(run.id)}`;
    const write = () => {
      if (window.location.pathname.replace(/\/+$/, '') !== path) return;
      const q = playerSearch({ pos: engine.clock.pos, speed: engine.clock.speed, cam: mode });
      if (window.location.search.replace(/^\?/, '') !== q) window.history.replaceState(window.history.state, '', `${path}?${q}${window.location.hash}`);
    };
    if (snap.playing) {
      const id = window.setInterval(write, 1000);
      return () => window.clearInterval(id);
    }
    const id = window.setTimeout(write, 300);
    return () => window.clearTimeout(id);
  }, [engine, run.id, snap.playing, urlPos, snap.speed, mode]);

  // measured render rate on the stage (for performance checks; no UI)
  useEffect(() => {
    if (!engine) return;
    const id = window.setInterval(() => {
      if (stageRef.current) stageRef.current.dataset.renderFps = engine.renderFps.toFixed(1);
    }, 1000);
    return () => window.clearInterval(id);
  }, [engine]);

  const stateAttr = decision ? decision.toLowerCase() : undefined;
  const pr = Math.min(2, window.devicePixelRatio || 1);
  return (
    <Stage state={stateAttr} stageRef={stageRef}>
      <SceneLayer>
        {engine && !webglError && (
          <World
            engine={engine}
            mode={mode}
            pixelRatio={pr}
            cloudBudget={hasClouds ? cloudBudget : null}
            displayRef={displayRef}
            onFreeChange={setFree}
            sink={sink}
            sceneRef={sceneRef}
            onError={setWebglError}
          />
        )}
        {webglError && <div className={styles.viewUnavailable} />}
        <Hud
          frame={frame}
          mode={mode}
          free={free}
          onResetView={() => sceneRef.current?.resetView()}
          hasClouds={hasClouds}
          cloudLoading={snap.cloudLoading || (hasClouds && cloudIndex.loading)}
          cloudError={snap.cloudError ?? (hasClouds ? (cloudIndex.error?.message ?? null) : null)}
          onRetryCloud={hasClouds && cloudIndex.error ? cloudIndex.retry : null}
          buffering={snap.buffering}
          framesFailed={snap.framesError !== null}
          motion={snap.motion}
          register={register}
          noView={!!webglError}
        />
      </SceneLayer>
      <div ref={displayRef} className={styles.display} data-player-display>
        {(webglError || snap.framesError !== null) && (
          <div className={styles.glassBanner}>
            <ErrorBanner
              compact
              error={webglError ?? snap.framesError}
              title={webglError ? '3D-вид недоступен' : 'Кадры не загрузились'}
              onRetry={webglError ? () => setWebglError(null) : () => engine?.retry()}
            />
          </div>
        )}
      </div>
      <div ref={dockRef} className={styles.controlDock} data-player-controls>
        <TelemetryTray
          left={<>
            <MapTile frame={frame} cloud={engine?.cloudAt(snap.cloudPos) ?? null} pixelRatio={pr} />
            {decision && <DecisionTile decision={decision} frame={frame} frameNo={frameNo} confirmS={confirmS} />}
          </>}
          right={<>
            <DistanceTile frame={frame} decision={decision} />
            <MetricsTile frame={frame} latency={latency} pos={pos} p95={run.summary.latency_ms?.p95 ?? null} playFps={snap.playFps} speed={snap.speed} playing={snap.playing} />
            <HealthTile frame={frame} minVisibility={minVis} />
          </>}
        />
        <div className={styles.persistentControls} data-player-persistent>
          <ViewControls
            runId={run.id}
            runName={run.name}
            decision={decision}
            reason={decision === 'CAUTION' ? cautionText(frame) : undefined}
            mode={mode}
            onMode={setMode}
            fullscreen={fs.active}
            onFullscreen={fs.toggle}
            expanded={expanded}
            onHeight={toggleHeight}
          />
          <Scrubber
            decisions={run.summary.decisions}
            pos={pos}
            n={n}
            frameNo={frameNo}
            lastFrameNo={lastFrameNo}
            t={seriesT?.[pos] ?? frame?.t ?? null}
            duration={run.summary.duration_s}
            playing={snap.playing}
            speed={snap.speed}
            loop={snap.loop}
            markers={markers}
            hasPrevEvent={prevEv !== null}
            hasNextEvent={nextEv !== null}
            posLabel={posLabel}
            onToggle={actions.toggle}
            onStep={actions.step}
            onPrevEvent={actions.prevEvent}
            onNextEvent={actions.nextEvent}
            onSeek={seek}
            onSpeed={(s) => engine?.setSpeed(s)}
            onLoop={() => engine?.setLoop(!snap.loop)}
          />
        </div>
      </div>
    </Stage>
  );
}
