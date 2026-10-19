// Page chrome: the red top bar, the metro line, then the routed page.
import { Suspense, useLayoutEffect, useRef, useState } from 'react';
import { Outlet, useLocation, useMatch } from 'react-router-dom';
import { useSystem } from '../../api/hooks';
import { LineRail } from '../LineRail/LineRail';
import { Spinner } from '../Spinner/Spinner';
import { TopBar } from '../TopBar/TopBar';
import styles from './AppShell.module.css';
import { RailContext } from './rail';

export function PageFallback() {
  return (
    <div className={styles.fallback}>
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
      <div className={styles.shell} data-app-shell>
        <a href="#main" className={styles.skip}>
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
      </div>
    </RailContext.Provider>
  );
}
