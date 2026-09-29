// A small 3D view of one stored cloud of a run (RunDetail 3D card, Overview player card, Live): the
// player's scene in its light mode — the cab camera, smaller points, the envelope along the frame's
// track and the detection boxes. three.js is loaded lazily with the scene module; the view renders
// on demand (data, resize, orbit) instead of running a loop.
import { useEffect, useRef, useState } from 'react';
import { useRunClouds, useRunCloud, useRunFrames } from '../api/hooks';
import { Spinner } from '../components/Spinner/Spinner';
import { Icon } from '../components/Icon/Icon';
import { cloudAtOrBefore } from './motion';
import type { PlayerScene } from './scene';
import styles from './CloudPreview.module.css';

export interface CloudPreviewProps {
  runId: string;
  /** processed-order position of the frame; the nearest stored cloud at or before it is shown */
  pos?: number;
  /** CSS height; the width follows the container */
  height?: number | string;
  /** allow orbiting with the mouse */
  interactive?: boolean;
  className?: string;
}

/** How long a frame / cloud that left the view stays cached (ms). */
const PASSED_GC_MS = 5000;

export default function CloudPreview({ runId, pos = 0, height = 240, interactive = false, className }: CloudPreviewProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<PlayerScene | null>(null);
  const rafRef = useRef(0);
  const [ready, setReady] = useState(false);
  const [sceneError, setSceneError] = useState<string | null>(null);

  const index = useRunClouds(runId);
  const p = Math.max(0, Math.round(pos));
  const cpos = index.data ? (cloudAtOrBefore(index.data.frames, p) ?? index.data.frames[0] ?? null) : null;
  // a live view moves the position at 10 Hz: frames and clouds already shown are not kept around
  const frames = useRunFrames(runId, p, 1, { gcTime: PASSED_GC_MS });
  const cloud = useRunCloud(runId, cpos, { gcTime: PASSED_GC_MS });
  const frame = frames.data?.frames[0] ?? null;

  const requestRender = () => {
    if (rafRef.current) return;
    let last = 0;
    const tick = (ts: number) => {
      rafRef.current = 0;
      const s = sceneRef.current;
      if (!s) return;
      s.render(last ? (ts - last) / 1000 : 0.016);
      last = ts;
      // keep going until the camera has settled on the frame (or while it is orbited)
      if (s.needsRender()) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  };

  // the scene: created once per mount (three arrives with the scene module)
  useEffect(() => {
    let cancelled = false;
    let scene: PlayerScene | null = null;
    let ro: ResizeObserver | null = null;
    import('./scene')
      .then(({ PlayerScene }) => {
        const canvas = canvasRef.current;
        const wrap = wrapRef.current;
        if (cancelled || !canvas || !wrap) return;
        try {
          scene = new PlayerScene(canvas, { preview: true, interactive, onInvalidate: () => requestRender() });
        } catch {
          setSceneError('WebGL недоступен');
          return;
        }
        sceneRef.current = scene;
        const fit = () => {
          if (!scene) return;
          scene.setSize(wrap.clientWidth, wrap.clientHeight, window.devicePixelRatio || 1);
          requestRender();
        };
        fit();
        if (typeof ResizeObserver !== 'undefined') {
          ro = new ResizeObserver(fit);
          ro.observe(wrap);
        }
        setReady(true);
      })
      .catch(() => setSceneError('3D-вид не загрузился'));
    return () => {
      cancelled = true;
      ro?.disconnect();
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
      sceneRef.current = null;
      scene?.dispose();
      // a new scene (interactive toggled) gets the frame and the cloud again
      setReady(false);
    };
  }, [interactive]);

  useEffect(() => {
    const s = sceneRef.current;
    if (!s || !ready) return;
    s.setFrame(frame);
    // the cloud is coloured along the frame's track (floor, axis) — also when it arrived first
    if (frame?.track) s.setCloudTrack(frame.track);
    requestRender();
  }, [frame, ready]);

  const budget = index.data?.points ?? 0;
  useEffect(() => {
    if (ready && budget) sceneRef.current?.reserve(budget);
  }, [budget, ready]);

  useEffect(() => {
    const s = sceneRef.current;
    if (!s || !ready) return;
    s.setCloud(cloud.data ?? null, frame?.track ?? null);
    requestRender();
    // the cloud's colouring follows the frame's track; a new frame alone is handled above
  }, [cloud.data, ready]);

  const noClouds = index.data && index.data.frames.length === 0;
  const loading = !sceneError && (!ready || index.isLoading || frames.isLoading || (!noClouds && cpos !== null && cloud.isLoading));
  const error =
    sceneError ??
    (index.isError
      ? index.error.message
      : frames.isError
        ? frames.error.message
        : cloud.isError && cloud.error.status !== 404
          ? cloud.error.message
          : null);

  return (
    <div ref={wrapRef} className={[styles.root, interactive ? styles.interactive : '', className].filter(Boolean).join(' ')} style={{ height }}>
      <canvas ref={canvasRef} className={styles.canvas} aria-label="3D-вид кадра" role="img" />
      {loading && (
        <span className={styles.state}>
          <Spinner size={22} tone="light" label="Загрузка облака" />
        </span>
      )}
      {!loading && error && (
        <span className={styles.state} role="alert">
          <span className={styles.err}>
            <Icon name="fault-circle" size={16} strokeWidth={2.4} />
            {error}
          </span>
        </span>
      )}
    </div>
  );
}
