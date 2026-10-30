// Boarding the Player: the leaving page swings away as you turn right, walk to the driver's cab,
// open its door and sit down. The 3D chunk loads lazily; until it is ready the page stays as it
// was (the same element, flat), and any failure simply reveals the Player. Any key or click skips
// to the seat. The Player is already mounted (hidden) underneath, so the last frame is its view.
import { useEffect, useRef } from 'react';
import type { NavigationSnapshot } from '../../lib/navigationSnapshot';
import { mountNavigationSnapshot } from '../../lib/navigationSnapshot';
import { displayPixelRatio } from '../../player/displayQuality';
import type { CabEntryScene, EntryLayout } from '../../player/cabEntry';
import styles from './AppShell.module.css';

/** Height of the Player's control dock before it has been measured (px). */
const DOCK_GUESS = 160;

function constrained(): boolean {
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  return (memory !== undefined && memory <= 4) || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 4);
}

/** The Player's canvas and display region as they will be when the overlay lifts. */
export function measureCabDestination(): EntryLayout {
  const width = document.documentElement.clientWidth || window.innerWidth;
  const height = document.documentElement.clientHeight || window.innerHeight;
  const pixelRatio = displayPixelRatio(width, height, window.devicePixelRatio || 1, constrained());
  const backdrop = document.querySelector<HTMLElement>('main [data-train-backdrop]');
  const region = document.querySelector<HTMLElement>('main [data-cab-region]');
  if (backdrop && region && backdrop.clientWidth > 0 && backdrop.clientHeight > 0 && region.clientHeight > 0) {
    const c = backdrop.getBoundingClientRect();
    const r = region.getBoundingClientRect();
    return {
      viewport: { width, height },
      canvas: { left: c.left, top: c.top, width: backdrop.clientWidth, height: backdrop.clientHeight },
      region: { left: r.left - c.left, top: r.top - c.top, width: region.clientWidth, height: region.clientHeight },
      pixelRatio,
    };
  }
  // The Player's chunk is still loading: predict its workspace below the pinned rail.
  const main = document.querySelector<HTMLElement>('main')?.getBoundingClientRect();
  const top = main ? main.top : 84;
  const canvas = { left: 0, top, width, height: Math.max(1, height - top) };
  const pad = Math.min(40, Math.max(16, width * 0.025));
  return { viewport: { width, height }, canvas, region: { left: pad, top: 8, width: width - pad * 2, height: Math.max(140, canvas.height - DOCK_GUESS - 8) }, pixelRatio };
}

interface Props {
  phase: string;
  snapshot: NavigationSnapshot | null;
  onFinished: () => void;
}

export function CabEntry({ phase, snapshot, onFinished }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const finished = useRef(onFinished);
  finished.current = onFinished;

  useEffect(() => {
    const root = host.current;
    if (!root || !snapshot) return;
    let disposed = false;
    let raf = 0;
    let skip = false;
    let scene: CabEntryScene | null = null;
    const canvas = document.createElement('canvas');
    canvas.className = styles.cabEntryCanvas;
    const css = document.createElement('div');
    css.className = styles.cabEntryPage;
    // The leaving page: the same frozen copy the doors would cover, flat until the scene takes it.
    const page = document.createElement('div');
    page.className = `${styles.transitStage} ${styles.cabEntryStage}`;
    page.dataset.leavingPage = 'ready';
    const content = document.createElement('div');
    content.className = styles.snapshot;
    content.dataset.outgoingSnapshot = 'ready';
    page.append(content);
    root.append(canvas, css, page);
    mountNavigationSnapshot(content, snapshot);
    const restoreScroll = () => { for (const { node, top, left } of snapshot.scroll) { node.scrollTop = top; node.scrollLeft = left; } };
    const finish = () => { if (!disposed) finished.current(); };
    // A key skips to the seat and goes no further: the Player underneath must not act on it
    // (Esc would leave, the space bar would start playback before the cab has booted).
    const onKey = (event: KeyboardEvent) => {
      skip = true;
      event.preventDefault();
      event.stopImmediatePropagation();
    };
    const onSkip = () => { skip = true; };
    window.addEventListener('keydown', onKey, true);
    root.addEventListener('pointerdown', onSkip);
    void import('../../player/cabEntry').then(({ CabEntryScene: Scene, ENTRY_MS }) => {
      if (disposed) return;
      try {
        scene = new Scene(canvas, css, page);
        scene.setLayout(measureCabDestination());
        scene.warm();
        scene.frame(0);
      } catch {
        finish();
        return;
      }
      restoreScroll();
      root.dataset.entryReady = 'true';
      let start = 0;
      const tick = (now: number) => {
        if (disposed || !scene) return;
        if (!start) start = now;
        scene.setLayout(measureCabDestination());
        const t = skip ? ENTRY_MS : now - start;
        scene.frame(t);
        root.dataset.entryProgress = Math.min(1, t / ENTRY_MS).toFixed(3);
        if (t >= ENTRY_MS) {
          finish();
          return;
        }
        raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    }).catch(finish);
    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      window.removeEventListener('keydown', onKey, true);
      root.removeEventListener('pointerdown', onSkip);
      scene?.dispose();
      canvas.remove();
      css.remove();
      page.remove();
      delete root.dataset.entryReady;
      delete root.dataset.entryProgress;
    };
  }, [snapshot]);

  return <div ref={host} className={styles.cabEntry} data-cab-entry data-phase={phase} aria-hidden="true" />;
}
