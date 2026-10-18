// The 3D view behind the glass: a fresh canvas + PlayerScene per engine (disposed on unmount, so
// StrictMode's double mount and run switches never reuse a lost WebGL context), attached to the
// playback engine that drives it.
import { useEffect, useRef, useState } from 'react';
import type { PlayerEngine } from '../../player/engine';
import type { CamMode } from '../../player/geometry';
import { PlayerScene } from '../../player/scene';
import type { OverlaySink } from './Hud';
import styles from './Player.module.css';

export interface WorldProps {
  engine: PlayerEngine;
  mode: CamMode;
  pixelRatio: number;
  /** points per stored cloud of the run (the buffers are preallocated for it) */
  cloudBudget: number | null;
  onFreeChange: (free: boolean) => void;
  /** the HUD's per-render position writer */
  sink: { current: OverlaySink | null };
  /** the scene, for the "reset view" button */
  sceneRef: { current: PlayerScene | null };
  onError: (message: string) => void;
}

export function World({ engine, mode, pixelRatio, cloudBudget, onFreeChange, sink, sceneRef, onError }: WorldProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const live = useRef({ mode, pixelRatio, cloudBudget, onFreeChange, onError });
  live.current = { mode, pixelRatio, cloudBudget, onFreeChange, onError };
  const [ok, setOk] = useState(true);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const canvas = document.createElement('canvas');
    canvas.className = styles.canvas;
    canvas.setAttribute('aria-label', '3D-вид из кабины');
    canvas.setAttribute('role', 'img');
    wrap.appendChild(canvas);
    let scene: PlayerScene;
    try {
      scene = new PlayerScene(canvas, {
        screenDisplay: true,
        interactive: true,
        onFreeChange: (f) => live.current.onFreeChange(f),
        onOverlay: (ov) => sink.current?.(ov),
      });
    } catch {
      canvas.remove();
      setOk(false);
      live.current.onError('WebGL недоступен в этом браузере — 3D-вид не показать.');
      return;
    }
    const resize = () => {
      const width = wrap.clientWidth;
      const height = wrap.clientHeight;
      if (!width || !height) return;
      scene.setSize(width, height, Math.min(2, window.devicePixelRatio || live.current.pixelRatio));
      const viewport = scene.overlay.viewport;
      const size = Math.max(80, Math.min(180, viewport.width * 0.16, viewport.height * 0.48));
      scene.setPipRect({ x: viewport.width - size - 14, y: 14, w: size, h: size, radius: 12 });
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(wrap);
    window.addEventListener('resize', resize);
    if (live.current.cloudBudget) scene.reserve(live.current.cloudBudget);
    scene.setMode(live.current.mode, false);
    sceneRef.current = scene;
    engine.attach(scene);
    // a GPU reset takes the context away: say so (the owner rebuilds the view on «Повторить»)
    const onLost = (e: Event) => {
      e.preventDefault();
      engine.detach();
      live.current.onError('Видеокарта сбросила 3D-вид.');
    };
    canvas.addEventListener('webglcontextlost', onLost);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', resize);
      // removed first: dispose() drops the context on purpose
      canvas.removeEventListener('webglcontextlost', onLost);
      engine.detach();
      sceneRef.current = null;
      scene.dispose();
      canvas.remove();
    };
  }, [engine, sink, sceneRef]);

  useEffect(() => {
    sceneRef.current?.setMode(mode);
  }, [mode, sceneRef]);

  useEffect(() => {
    if (cloudBudget) sceneRef.current?.reserve(cloudBudget);
  }, [cloudBudget, sceneRef]);

  return <div ref={wrapRef} className={styles.world} data-webgl={ok ? 'ok' : 'off'} />;
}
