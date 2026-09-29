// Плеер — a fullscreen route outside the AppShell: the drive through a run from the cab of a future
// train (webapp/design/mockup/player.html made live). The 1600×1000 composition is scaled to fit;
// the 3D view behind the glass is driven by the playback engine (src/player), the console tiles and
// the scrubber read its snapshot. Deep links: /player/<runId>?pos=<n>&speed=<x>&cam=cab|top|chase.
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { usePresetSchema, useRun, useRunClouds, useRunSeries } from '../../api/hooks';
import type { RunDetail } from '../../api/types';
import { Button, ErrorBanner, Spinner } from '../../components';
import { decisionAt } from '../../lib/decisions';
import { stepSpeed } from '../../player/clock';
import { PlayerEngine, type EngineSnapshot } from '../../player/engine';
import { eventMarks, nextEventPos, prevEventPos } from '../../player/events';
import type { CamMode } from '../../player/geometry';
import type { PlayerScene } from '../../player/scene';
import { CAMERAS, confirmTime, minVisibility, parsePlayerParams, playerSearch, scrubberMarkers, type PlayerUrlState } from './cab';
import { CabFrame } from './CabFrame';
import { Hud, type OverlaySink } from './Hud';
import { Roof } from './Roof';
import { PickerConsole, RunPickerGlass } from './RunPicker';
import { Scrubber } from './Scrubber';
import { DecisionTile, DistanceTile, HealthTile, MapTile, MetricsTile } from './Tiles';
import { useFullscreen, usePlayerKeys, useStageScale } from './useCab';
import { World } from './World';
import styles from './Player.module.css';

// ---------------------------------------------------------------- the stage

function useBack(runId?: string) {
  const navigate = useNavigate();
  const location = useLocation();
  return useCallback(() => {
    if (location.key !== 'default') navigate(-1);
    else navigate(runId ? `/runs/${encodeURIComponent(runId)}` : '/');
  }, [location.key, navigate, runId]);
}

interface StageProps {
  children: (ctx: { k: number; fs: ReturnType<typeof useFullscreen> }) => ReactNode;
  state?: string;
  rootRef?: React.RefObject<HTMLDivElement>;
}

/** The fixed 1600×1000 cab, scaled to the window; the root is the fullscreen element. */
function Stage({ children, state, rootRef }: StageProps) {
  const own = useRef<HTMLDivElement>(null);
  const ref = rootRef ?? own;
  const k = useStageScale();
  const fs = useFullscreen(ref);
  return (
    <div ref={ref} className={styles.root}>
      <div className={styles.stage} style={{ ['--k' as string]: k }} data-state={state}>
        {children({ k, fs })}
      </div>
    </div>
  );
}

/** Loading / error / picker: the cab with something in the glass and a quiet console. */
function CabShell({ runId, runName, glass, console: cons }: { runId?: string; runName?: string; glass: ReactNode; console?: ReactNode }) {
  const back = useBack(runId);
  return (
    <Stage>
      {({ fs }) => (
        <>
          <div className={styles.glassFill} />
          <CabFrame className={styles.cab} stop={false} obstacleM={null} />
          <div className={styles.glassArea}>{glass}</div>
          <Roof runId={runId} runName={runName} decision={null} fullscreen={fs.active} kiosk={fs.pseudo} onFullscreen={fs.toggle} onBack={back} />
          {cons}
          <ShellKeys onEscape={() => (fs.active ? void fs.exit() : back())} onFullscreen={fs.toggle} />
        </>
      )}
    </Stage>
  );
}

function ShellKeys({ onEscape, onFullscreen }: { onEscape: () => void; onFullscreen: () => void }) {
  usePlayerKeys({
    toggle: () => undefined,
    step: () => undefined,
    prevEvent: () => undefined,
    nextEvent: () => undefined,
    camera: () => undefined,
    speed: () => undefined,
    fullscreen: onFullscreen,
    escape: onEscape,
  });
  return null;
}

// ---------------------------------------------------------------- route

export default function Player() {
  const { runId } = useParams();
  useEffect(() => {
    document.title = 'Плеер · ReSense';
  }, []);
  if (!runId) {
    return <CabShell glass={<RunPickerGlass />} console={<PickerConsole />} />;
  }
  return <PlayerRun key={runId} runId={runId} />;
}

function PlayerRun({ runId }: { runId: string }) {
  const [params] = useSearchParams();
  const initial = useRef<PlayerUrlState>(parsePlayerParams(params));
  const run = useRun(runId, { retry: false });
  const series = useRunSeries(runId, { enabled: !!run.data });
  const clouds = useRunClouds(runId, { enabled: !!run.data?.has_clouds });

  if (run.isLoading) {
    return (
      <CabShell
        runId={runId}
        glass={
          <div className={styles.glassCenter}>
            <Spinner size={34} tone="light" label="Загрузка прогона" />
          </div>
        }
      />
    );
  }
  if (run.isError || !run.data) {
    return (
      <CabShell
        runId={runId}
        glass={
          <div className={styles.glassCenter}>
            <div className={styles.glassCard}>
              <ErrorBanner error={run.error} title="Прогон не открылся" onRetry={() => void run.refetch()} retrying={run.isFetching} />
              <div className={styles.glassActions}>
                <Button variant="dark" icon="play" to="/player">
                  Выбрать прогон
                </Button>
                <Button variant="outline" icon="list" to="/runs">
                  Все прогоны
                </Button>
              </div>
            </div>
          </div>
        }
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
const idleSnapshot = () => IDLE;

interface CabProps {
  run: RunDetail;
  seriesT: readonly number[] | null;
  seriesFrames: readonly number[] | null;
  latency: readonly number[] | null;
  cloudFrames: readonly number[] | null;
  initial: PlayerUrlState;
}

function Cab({ run, seriesT, seriesFrames, latency, cloudFrames, initial }: CabProps) {
  const n = run.summary.n_frames;
  const hasClouds = run.has_clouds && run.cloud_frames > 0;
  const [, setParams] = useSearchParams();
  const back = useBack(run.id);
  const schema = usePresetSchema();
  const rootRef = useRef<HTMLDivElement>(null);

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

  const snap = useSyncExternalStore(engine?.subscribe ?? noopSubscribe, engine?.getSnapshot ?? idleSnapshot);

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
  const nearestObstacle = frame?.obstacle ? (frame.nearest_distance ?? null) : null;

  // controls
  const fsRef = useRef<ReturnType<typeof useFullscreen> | null>(null);
  const seek = useCallback((p: number) => engine?.seek(p), [engine]);
  const prevEv = prevEventPos(marks, pos);
  const nextEv = nextEventPos(marks, pos);
  const actions = {
    toggle: () => engine?.toggle(),
    step: (d: number) => engine?.step(d),
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
    fullscreen: () => fsRef.current?.toggle(),
    escape: () => {
      if (sceneRef.current?.isFree) sceneRef.current.resetView();
      else if (fsRef.current?.active) void fsRef.current.exit();
      else back();
    },
  };
  usePlayerKeys(actions, !!engine);

  // the URL follows the player (replace, no history entries): on pause, speed and camera changes
  const urlPos = snap.playing ? -1 : pos;
  useEffect(() => {
    if (!engine) return;
    const id = window.setTimeout(() => {
      setParams(playerSearch({ pos: engine.clock.pos, speed: engine.clock.speed, cam: mode }), { replace: true, preventScrollReset: true });
    }, 300);
    return () => window.clearTimeout(id);
  }, [engine, urlPos, snap.speed, mode, setParams]);

  // measured render rate on the root (for performance checks; no UI)
  useEffect(() => {
    if (!engine) return;
    const id = window.setInterval(() => {
      if (rootRef.current) rootRef.current.dataset.renderFps = engine.renderFps.toFixed(1);
    }, 1000);
    return () => window.clearInterval(id);
  }, [engine]);

  const stateAttr = decision ? decision.toLowerCase() : undefined;
  return (
    <Stage state={stateAttr} rootRef={rootRef}>
      {({ k, fs }) => {
        fsRef.current = fs;
        const pr = Math.min(2, (window.devicePixelRatio || 1) * k);
        return (
          <>
            {engine && !webglError && (
              <World engine={engine} mode={mode} pixelRatio={pr} onFreeChange={setFree} sink={sink} sceneRef={sceneRef} onError={setWebglError} />
            )}
            {webglError && <div className={styles.glassFill} />}
            <CabFrame className={styles.cab} stop={decision === 'STOP'} obstacleM={nearestObstacle} />
            <Hud
              frame={frame}
              mode={mode}
              free={free}
              onResetView={() => sceneRef.current?.resetView()}
              hasClouds={hasClouds}
              cloudLoading={snap.cloudLoading}
              buffering={snap.buffering}
              motion={snap.motion}
              register={register}
            />
            {(webglError || snap.framesError !== null) && (
              <div className={styles.glassBanner}>
                <ErrorBanner
                  compact
                  error={webglError ?? snap.framesError}
                  title={webglError ? '3D-вид недоступен' : 'Кадры не загрузились'}
                  onRetry={webglError ? undefined : () => engine?.retry()}
                />
              </div>
            )}
            <Roof
              runId={run.id}
              runName={run.name}
              decision={decision}
              mode={mode}
              onMode={setMode}
              fullscreen={fs.active}
              kiosk={fs.pseudo}
              onFullscreen={fs.toggle}
              onBack={back}
            />
            <MapTile frame={frame} cloud={engine?.cloudAt(snap.cloudPos) ?? null} pixelRatio={pr} />
            {decision && <DecisionTile decision={decision} frame={frame} frameNo={frameNo} confirmS={confirmS} />}
            <DistanceTile frame={frame} />
            <MetricsTile frame={frame} latency={latency} pos={pos} p95={run.summary.latency_ms?.p95 ?? null} playFps={snap.playFps} speed={snap.speed} playing={snap.playing} />
            <HealthTile frame={frame} minVisibility={minVis} />
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
          </>
        );
      }}
    </Stage>
  );
}
