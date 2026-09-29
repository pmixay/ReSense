// Page chrome: the red top bar, the metro line, then the routed page.
import { Suspense, useState } from 'react';
import { Outlet } from 'react-router-dom';
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
  const [sub, setSub] = useState<string | undefined>(undefined);
  const system = useSystem();
  const counts = system.isError ? undefined : system.data?.counts;
  const queueBusy = !!counts && counts.jobs_running + counts.jobs_queued > 0;
  return (
    <RailContext.Provider value={setSub}>
      <div className={styles.shell}>
        <a href="#main" className={styles.skip}>
          К содержимому
        </a>
        <TopBar />
        <LineRail sub={sub} queueBusy={queueBusy} />
        <main id="main" className={styles.page} tabIndex={-1}>
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </RailContext.Provider>
  );
}
