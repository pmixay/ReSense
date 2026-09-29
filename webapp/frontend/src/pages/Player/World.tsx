// The 3D view behind the glass: a fresh canvas + PlayerScene per engine (disposed on unmount, so
// StrictMode's double mount and run switches never reuse a lost WebGL context), attached to the
// playback engine that drives it.
import { useEffect, useRef, useState } from 'react';
import type { PlayerEngine } from '../../player/engine';
import type { CamMode } from '../../player/geometry';
import { PlayerScene } from '../../player/scene';
import { PIP_RECT, type OverlaySink } from './Hud';
import styles from './Player.module.css';

export const WORLD_W = 1600;
export const WORLD_H = 700;

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
    scene.setSize(WORLD_W, WORLD_H, live.current.pixelRatio);
    if (live.current.cloudBudget) scene.reserve(live.current.cloudBudget);
    scene.setPipRect(PIP_RECT);
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
    sceneRef.current?.setSize(WORLD_W, WORLD_H, pixelRatio);
  }, [pixelRatio, sceneRef]);

  useEffect(() => {
    if (cloudBudget) sceneRef.current?.reserve(cloudBudget);
  }, [cloudBudget, sceneRef]);

  return <div ref={wrapRef} className={styles.world} data-webgl={ok ? 'ok' : 'off'} />;
}
