import { QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Component, Suspense, useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { PAGES, type PageKey } from '../../lib/nav';
import { NavigationPreviewContext } from '../../lib/navigationPreview';
import type { NavigationJourney } from '../../lib/navigationJourney';
import type { NavigationSnapshot } from '../../lib/navigationSnapshot';
import { sectionPages } from '../../sectionPages';
import { LineRail } from '../LineRail/LineRail';
import { TopBar } from '../TopBar/TopBar';
import { RailContext } from './rail';
import styles from './AppShell.module.css';

class PreviewBoundary extends Component<{ label: string; children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  override render() { return this.state.failed ? <div className={styles.previewFallback}>{this.props.label}</div> : this.props.children; }
}

function Outgoing({ snapshot }: { snapshot: NavigationSnapshot | null }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!ref.current || !snapshot) return;
    ref.current.replaceChildren(...snapshot.nodes);
    ref.current.style.setProperty('--site-chrome-h', snapshot.chromeHeight);
    for (const { node, top, left } of snapshot.scroll) { node.scrollTop = top; node.scrollLeft = left; }
  }, [snapshot]);
  return <div ref={ref} className={styles.snapshot} data-outgoing-snapshot={snapshot ? 'ready' : 'waiting'} />;
}

function PassingPage({ page }: { page: PageKey }) {
  const Page = sectionPages[page];
  return <div className={`${styles.shell} ${styles.transitStage}`} data-transit-page={page}>
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
  onPrepared: (ready: boolean) => void;
}

/** Isolated, inert memory routes share cached data, while only the target navigates the app. */
export function TransitPages({ phase, journey, snapshot, onPrepared }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const root = useRef<Root | null>(null);
  const client = useQueryClient();
  useEffect(() => {
    const container = document.createElement('div');
    host.current!.setAttribute('inert', '');
    host.current!.append(container);
    const independentRoot = createRoot(container);
    root.current = independentRoot;
    const check = () => onPrepared(!!container.querySelector('[data-outgoing-snapshot="ready"] > *') && !container.querySelector('[data-transit-loading]'));
    const observer = new MutationObserver(check);
    observer.observe(container, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      onPrepared(false);
      root.current = null;
      container.remove();
      // Do not synchronously unmount an independent root during the parent's React commit.
      queueMicrotask(() => independentRoot.unmount());
    };
  }, [client, onPrepared]);
  useEffect(() => {
    root.current?.render(
      <QueryClientProvider client={client}>
        <NavigationPreviewContext.Provider value>
          <RailContext.Provider value={() => undefined}>
            <div className={styles.transitStrip} data-travel-phase={phase} data-travel-direction={journey.direction}>
              <div className={styles.transitStage}><Outgoing snapshot={snapshot} /></div>
              {journey.via.map(page => <PassingPage key={page} page={page} />)}
            </div>
          </RailContext.Provider>
        </NavigationPreviewContext.Provider>
      </QueryClientProvider>,
    );
  }, [client, journey, phase, snapshot]);
  return <div ref={host} className={styles.transitViewport} data-transit-viewport aria-hidden="true" />;
}
