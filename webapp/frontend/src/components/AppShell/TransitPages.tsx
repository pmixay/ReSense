import { QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Component, Suspense, useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { PAGES, type PageKey } from '../../lib/nav';
import { NavigationPreviewContext } from '../../lib/navigationPreview';
import type { NavigationJourney } from '../../lib/navigationJourney';
import { duplicateNavigationSnapshot, mountNavigationSnapshot, navigationSnapshot, type NavigationSnapshot } from '../../lib/navigationSnapshot';
import { sectionPages } from '../../sectionPages';
import { rasterizeNavigationBlur } from '../../lib/navigationRaster';
import { LineRail } from '../LineRail/LineRail';
import { TopBar } from '../TopBar/TopBar';
import { RailContext } from './rail';
import styles from './AppShell.module.css';

class PreviewBoundary extends Component<{ label: string; children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  override render() { return this.state.failed ? <div className={styles.previewFallback}>{this.props.label}</div> : this.props.children; }
}

function PassingPage({ page }: { page: PageKey }) {
  const Page = sectionPages[page];
  return <div className={`${styles.shell} ${styles.transitStage}`} data-preparing-page={page}>
    <MemoryRouter initialEntries={[PAGES[page].path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className={styles.chrome}>
        {page !== 'player' && <TopBar />}
        <LineRail hideBranch={page === 'player'} />
      </div>
      <div className={`${styles.page} ${page === 'player' ? styles.playerPage : ''}`}>
        <PreviewBoundary label={PAGES[page].label}>
          <Suspense fallback={<div className={styles.previewFallback} data-transit-loading>{PAGES[page].label}</div>}><Page /></Suspense>
        </PreviewBoundary>
      </div>
    </MemoryRouter>
  </div>;
}

interface Props {
  phase: string;
  journey: NavigationJourney;
  snapshot: NavigationSnapshot | null;
  captureDestination: () => NavigationSnapshot | null;
  onPrepared: (ready: boolean) => void;
  onFinished: () => void;
}

/** Prepare live views once, then move a single frozen strip with transform/opacity only. */
export function TransitPages({ phase, journey, snapshot, captureDestination, onPrepared, onFinished }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const strip = useRef<HTMLDivElement>(null);
  const preparation = useRef<HTMLDivElement>(null);
  const root = useRef<Root | null>(null);
  const frozen = useRef(false);
  const client = useQueryClient();
  const latest = useRef({ captureDestination, onFinished });
  latest.current = { captureDestination, onFinished };

  useEffect(() => {
    // Chunk fetches can overlap closing; mounting six live views must wait for closed doors.
    if (phase !== 'covered') return;
    const container = document.createElement('div');
    preparation.current!.append(container);
    const independentRoot = createRoot(container);
    root.current = independentRoot;
    independentRoot.render(<QueryClientProvider client={client}>
      <NavigationPreviewContext.Provider value>
        <RailContext.Provider value={() => undefined}>
          {journey.via.map(page => <PassingPage key={page} page={page} />)}
        </RailContext.Provider>
      </NavigationPreviewContext.Provider>
    </QueryClientProvider>);
    return () => {
      container.remove();
      if (root.current === independentRoot) {
        root.current = null;
        queueMicrotask(() => independentRoot.unmount());
      }
    };
  }, [client, journey, phase]);

  useLayoutEffect(() => {
    host.current?.setAttribute('inert', '');
    if (!snapshot || !strip.current) return;
    const outgoing = document.createElement('div');
    outgoing.className = styles.transitStage;
    const content = document.createElement('div');
    content.className = styles.snapshot;
    content.dataset.outgoingSnapshot = 'ready';
    outgoing.append(content);
    strip.current.replaceChildren(outgoing);
    mountNavigationSnapshot(content, snapshot);
  }, [snapshot]);

  useEffect(() => {
    if (phase !== 'covered' || !snapshot || frozen.current) return;
    let raf = 0;
    let settle = 0;
    let changed = performance.now();
    let cancelled = false;
    const started = changed;
    const prep = preparation.current!;
    const observer = new MutationObserver(() => { changed = performance.now(); });
    observer.observe(prep, { childList: true, subtree: true, characterData: true });
    const bake = async () => {
      const views = Array.from(strip.current!.querySelectorAll<HTMLElement>(`.${styles.frozenBlur}`));
      const width = host.current!.clientWidth;
      const height = host.current!.clientHeight;
      const bitmaps = await Promise.all(views.map(view => rasterizeNavigationBlur(view, width, height)));
      if (cancelled) return;
      views.forEach((view, i) => view.replaceChildren(bitmaps[i]));
      // Give layout and cached bitmap surfaces two full paints before starting the compositor.
      const warm = () => { if (++settle === 3) onPrepared(true); else raf = requestAnimationFrame(warm); };
      raf = requestAnimationFrame(warm);
    };
    const prepare = (now: number) => {
      if (prep.querySelectorAll('[data-preparing-page]').length !== journey.via.length || prep.querySelector('[data-transit-loading]') || document.querySelector('[data-page-fallback]') || document.fonts.status === 'loading' || (now - changed < 60 && now - started < 850)) {
        raf = requestAnimationFrame(prepare);
        return;
      }
      observer.disconnect();
      const target = latest.current.captureDestination();
      if (!target) return;
      const snapshots = [snapshot, ...Array.from(prep.querySelectorAll<HTMLElement>('[data-preparing-page]')).map(stage =>
        navigationSnapshot(stage.children[0] as HTMLElement, stage.children[1] as HTMLElement, false)), target];
      const restore: Array<{ target: HTMLElement; image: NavigationSnapshot }> = [];
      const stages = snapshots.map((image, i) => {
        const stage = document.createElement('div');
        stage.className = styles.transitStage;
        if (i === 0) stage.dataset.outgoingSnapshot = 'ready';
        else if (i === snapshots.length - 1) stage.dataset.destinationSnapshot = 'ready';
        else stage.dataset.transitPage = journey.via[i - 1];
        const blurred = document.createElement('div');
        blurred.className = `${styles.snapshot} ${styles.frozenBlur}`;
        if (i === 0 || i === snapshots.length - 1) {
          const sharp = document.createElement('div');
          sharp.className = `${styles.snapshot} ${styles.frozenSharp}`;
          sharp.dataset.sharpEndpoint = i === 0 ? 'outgoing' : 'destination';
          stage.append(blurred, sharp);
          mountNavigationSnapshot(sharp, image);
          restore.push({ target: sharp, image });
          // Duplicate only the endpoints; keep blur cached and animate opacity instead.
          const copy = duplicateNavigationSnapshot(image);
          mountNavigationSnapshot(blurred, copy);
          restore.push({ target: blurred, image: copy });
        } else {
          stage.append(blurred);
          mountNavigationSnapshot(blurred, image);
          restore.push({ target: blurred, image });
        }
        return stage;
      });
      strip.current!.replaceChildren(...stages);
      for (const { image } of restore) for (const { node, top, left } of image.scroll) { node.scrollTop = top; node.scrollLeft = left; }
      strip.current!.dataset.transitFrozen = 'true';
      frozen.current = true;
      // Dispose all preview effects before travel. API updates can no longer change its pixels.
      const previewRoot = root.current;
      root.current = null;
      previewRoot?.unmount();
      prep.replaceChildren();
      // If browser rasterization fails, readiness stays false and the covered fallback reveals safely.
      void bake().catch(error => {
        if (!cancelled && host.current) host.current.dataset.transitPreparationError = error instanceof Error ? error.message : String(error);
      });
    };
    raf = requestAnimationFrame(prepare);
    return () => { cancelled = true; observer.disconnect(); cancelAnimationFrame(raf); };
  }, [phase, snapshot, journey, onPrepared]);

  useLayoutEffect(() => {
    if (phase !== 'travelling' || !frozen.current) return;
    const track = strip.current!;
    const distance = (journey.direction === 'right' ? -1 : 1) * journey.steps * host.current!.clientWidth;
    const timing = { duration: journey.duration, easing: 'cubic-bezier(.35, .05, .2, 1)', fill: 'both' as const };
    const movement = track.animate([{ transform: 'translate3d(0,0,0)' }, { transform: `translate3d(${distance}px,0,0)` }], timing);
    movement.id = 'section-travel';
    const outgoing = track.querySelector<HTMLElement>('[data-sharp-endpoint="outgoing"]')!.animate([
      { opacity: 1, offset: 0 }, { opacity: 0, offset: .2 }, { opacity: 0, offset: 1 },
    ], { ...timing, easing: 'linear' });
    outgoing.id = 'section-outgoing-sharp';
    const incoming = track.querySelector<HTMLElement>('[data-sharp-endpoint="destination"]')!.animate([
      { opacity: 0, offset: 0 }, { opacity: 0, offset: .74 }, { opacity: 1, offset: 1 },
    ], { ...timing, easing: 'linear' });
    incoming.id = 'section-incoming-sharp';
    const animations = [movement, outgoing, incoming];
    const start = document.timeline.currentTime;
    for (const animation of animations) animation.startTime = start;
    let cancelled = false;
    void movement.finished.then(() => { if (!cancelled) latest.current.onFinished(); }).catch(() => undefined);
    const finish = () => { for (const animation of animations) animation.finish(); };
    const visibility = () => { if (document.hidden) finish(); };
    window.addEventListener('resize', finish);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      cancelled = true;
      animations.forEach(animation => animation.cancel());
      window.removeEventListener('resize', finish);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [phase, journey]);

  useEffect(() => () => onPrepared(false), [onPrepared]);
  return <div ref={host} className={styles.transitViewport} data-transit-viewport aria-hidden="true">
    <div ref={strip} className={styles.transitStrip} data-travel-direction={journey.direction} />
    <div ref={preparation} className={styles.transitPreparation} data-transit-preparation />
  </div>;
}
