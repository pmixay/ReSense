// One full-workspace train scene. The live image and foreground railings have separate
// physical transforms; pressure motion uses the existing engine's on-demand render loop.
import { useEffect, useRef, useState, type RefObject } from 'react';
import type { PlayerEngine } from '../../player/engine';
import type { CamMode } from '../../player/geometry';
import { PlayerScene } from '../../player/scene';
import { displayPixelRatio } from '../../player/displayQuality';
import type { OverlaySink } from './Hud';
import styles from './Player.module.css';

export interface WorldProps {
  engine: PlayerEngine | null;
  mode: CamMode;
  pixelRatio: number;
  cloudBudget: number | null;
  displayRef: RefObject<HTMLDivElement>;
  onFreeChange: (free: boolean) => void;
  sink: { current: OverlaySink | null };
  sceneRef: { current: PlayerScene | null };
  onError: (message: string) => void;
}

export function World({ engine, mode, pixelRatio, cloudBudget, displayRef, onFreeChange, sink, sceneRef, onError }: WorldProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const live = useRef({ mode, pixelRatio, cloudBudget, onFreeChange, onError });
  live.current = { mode, pixelRatio, cloudBudget, onFreeChange, onError };
  const [ok, setOk] = useState(true);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const workspace = wrap.closest<HTMLElement>('[data-player-workspace]') ?? wrap;
    const canvas = document.createElement('canvas');
    canvas.className = styles.canvas;
    canvas.setAttribute('aria-label', engine ? '3D-вид из кабины' : 'Интерьер вагона');
    canvas.setAttribute('role', 'img');
    wrap.appendChild(canvas);
    let scene: PlayerScene;
    let raf = 0;
    let last = 0;
    const standaloneFrame = (now: number) => {
      raf = 0;
      scene.render(last ? Math.min(.1, (now - last) / 1000) : 1 / 60);
      last = now;
      if (scene.needsRender()) raf = requestAnimationFrame(standaloneFrame);
    };
    const invalidate = () => {
      if (!engine && !raf) raf = requestAnimationFrame(standaloneFrame);
    };
    try {
      scene = new PlayerScene(canvas, {
        screenDisplay: true,
        wallOnly: !engine,
        interactive: !!engine,
        onFreeChange: f => live.current.onFreeChange(f),
        onInvalidate: invalidate,
        onOverlay: ov => {
          const m = ov.viewport.motion;
          if (m) {
            canvas.dataset.sceneTiltX = String(m.sceneX);
            canvas.dataset.sceneTiltY = String(m.sceneY);
            canvas.dataset.sceneTiltZ = String(m.sceneZ);
            canvas.dataset.railTiltX = String(m.railX);
            canvas.dataset.railTiltY = String(m.railY);
            canvas.dataset.railTiltZ = String(m.railZ);
          }
          sink.current?.(ov);
        },
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
      const view = displayRef.current;
      if (!width || !height || !view) return;
      const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
      const constrained = (memory !== undefined && memory <= 4) || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 4);
      const ratio = displayPixelRatio(width, height, window.devicePixelRatio || live.current.pixelRatio, constrained);
      canvas.dataset.renderPixelRatio = String(ratio);
      scene.setSize(width, height, ratio, {
        width: view.clientWidth, left: view.offsetLeft, height: view.clientHeight, top: view.offsetTop,
      });
      const viewport = scene.overlay.viewport;
      const size = Math.max(80, Math.min(180, viewport.width * .16, viewport.height * .48));
      scene.setPipRect({ x: viewport.width - size - 14, y: 14, w: size, h: size, radius: 12 });
      invalidate();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(wrap);
    if (displayRef.current) observer.observe(displayRef.current);
    window.addEventListener('resize', resize);
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
    const reset = () => { scene.setPointer(0, 0); invalidate(); };
    const pointer = (event: PointerEvent) => {
      if (reduce.matches || event.pointerType !== 'mouse' || event.buttons !== 0) return;
      const r = canvas.getBoundingClientRect();
      const main = wrap.closest('main')?.getBoundingClientRect() ?? r;
      scene.setPointer((event.clientX - r.left) / r.width * 2 - 1, (event.clientY - main.top) / main.height * 2 - 1);
      invalidate();
    };
    workspace.addEventListener('pointermove', pointer, { passive: true });
    workspace.addEventListener('pointerup', pointer, { passive: true });
    workspace.addEventListener('pointerleave', reset);
    window.addEventListener('blur', reset);
    reduce.addEventListener('change', reset);
    if (live.current.cloudBudget) scene.reserve(live.current.cloudBudget);
    scene.setMode(live.current.mode, false);
    sceneRef.current = scene;
    engine?.attach(scene);
    const onLost = (event: Event) => {
      event.preventDefault();
      engine?.detach();
      live.current.onError('Видеокарта сбросила 3D-вид.');
    };
    canvas.addEventListener('webglcontextlost', onLost);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', resize);
      workspace.removeEventListener('pointermove', pointer);
      workspace.removeEventListener('pointerup', pointer);
      workspace.removeEventListener('pointerleave', reset);
      window.removeEventListener('blur', reset);
      reduce.removeEventListener('change', reset);
      cancelAnimationFrame(raf);
      canvas.removeEventListener('webglcontextlost', onLost);
      engine?.detach();
      sceneRef.current = null;
      scene.dispose();
      canvas.remove();
    };
  }, [engine, sink, sceneRef, displayRef]);

  useEffect(() => { sceneRef.current?.setMode(mode); }, [mode, sceneRef]);
  useEffect(() => { if (cloudBudget) sceneRef.current?.reserve(cloudBudget); }, [cloudBudget, sceneRef]);
  return <div ref={wrapRef} className={styles.world} data-webgl={ok ? 'ok' : 'off'} />;
}
