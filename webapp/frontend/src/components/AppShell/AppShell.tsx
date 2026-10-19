// Page chrome: the red top bar, the metro line, then the routed page.
import { Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { Outlet, useLocation, useMatch } from 'react-router-dom';
import { useSystem } from '../../api/hooks';
import { LineRail } from '../LineRail/LineRail';
import { Spinner } from '../Spinner/Spinner';
import { TopBar } from '../TopBar/TopBar';
import styles from './AppShell.module.css';
import { RailContext } from './rail';
import { TrainDoors, useTrainDoors } from './TrainDoors';
import { TransitPages } from './TransitPages';
import { navigationSnapshot, type NavigationSnapshot } from '../../lib/navigationSnapshot';

export function PageFallback() {
  return (
    <div className={styles.fallback} data-page-fallback>
      <Spinner size={28} label="Страница загружается" />
    </div>
  );
}

export function AppShell() {
  const chromeRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLElement>(null);
  const { key } = useLocation();
  const player = useMatch('/player/*');
  const [sub, setSub] = useState<string | undefined>(undefined);
  const [snapshot, setSnapshot] = useState<NavigationSnapshot | null>(null);
  const prepared = useRef(false);
  const completeTravel = useRef<(() => void) | null>(null);
  const registerFinish = useCallback((finish: (() => void) | null) => { completeTravel.current = finish; }, []);
  const onPrepared = useCallback((ready: boolean) => { prepared.current = ready; }, []);
  const capture = useCallback(() => {
    if (chromeRef.current && pageRef.current) setSnapshot(navigationSnapshot(chromeRef.current, pageRef.current));
  }, []);
  const captureDestination = useCallback(() => chromeRef.current && pageRef.current ? navigationSnapshot(chromeRef.current, pageRef.current) : null, []);
  const doors = useTrainDoors({ onCover: capture, isPrepared: () => prepared.current, onFinishRequested: () => completeTravel.current?.() });
  useEffect(() => { if (!doors.active) setSnapshot(null); }, [doors.active]);
  const wasTransitioning = useRef(false);
  useLayoutEffect(() => {
    chromeRef.current?.toggleAttribute('inert', doors.active);
    pageRef.current?.toggleAttribute('inert', doors.active);
    if (!doors.active && wasTransitioning.current) pageRef.current?.focus({ preventScroll: true });
    wasTransitioning.current = doors.active;
  }, [doors.active]);
  useLayoutEffect(() => {
    const chrome = chromeRef.current;
    if (!chrome) return;
    const measure = () => chrome.parentElement?.style.setProperty('--site-chrome-h', `${chrome.offsetHeight}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(chrome);
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    pageRef.current?.scrollTo(0, 0);
  }, [key]);
  const system = useSystem();
  const counts = system.isError ? undefined : system.data?.counts;
  const queueBusy = !!counts && counts.jobs_running + counts.jobs_queued > 0;
  return (
    <RailContext.Provider value={setSub}>
      <div className={styles.shell} data-app-shell data-section-motion={doors.phase} data-travel-direction={doors.journey.direction}
        style={{ '--travel-sign': doors.journey.direction === 'right' ? 1 : -1, '--travel-steps': doors.journey.steps, '--travel-duration': `${doors.journey.duration}ms` } as CSSProperties}>
        <a href="#main" className={styles.skip} tabIndex={doors.active ? -1 : undefined}>
          К содержимому
        </a>
        <div ref={chromeRef} className={styles.chrome}>
          {!player && <TopBar />}
          <LineRail sub={sub} queueBusy={queueBusy} hideBranch={!!player} />
        </div>
        <main ref={pageRef} id="main" className={`${styles.page} ${player ? styles.playerPage : ''}`} tabIndex={-1}>
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </main>
        {doors.active && !doors.reduced && doors.phase !== 'opening' && <TransitPages phase={doors.phase} journey={doors.journey} snapshot={snapshot} captureDestination={captureDestination} onPrepared={onPrepared} onFinished={doors.finishTravel} registerFinish={registerFinish} />}
        <TrainDoors phase={doors.phase} />
      </div>
    </RailContext.Provider>
  );
}
