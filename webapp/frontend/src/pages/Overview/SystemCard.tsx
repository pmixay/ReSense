// «Система»: CPU load (cores busy of all, with a sparkline of the polls since the page opened),
// backend uptime, the live node, recordings and free disk — all from /api/system (+ /recordings).
import { useEffect, useSyncExternalStore } from 'react';
import { Link } from 'react-router-dom';
import { useRecordings, useSystem } from '../../api/hooks';
import type { SystemInfo } from '../../api/types';
import { Card, Chip, ErrorBanner, Icon, Sparkline, Spinner } from '../../components';
import { CORES, fmtBytes, fmtDuration, fmtInt, fmtNum, plural } from '../../lib/format';
import styles from './Overview.module.css';

/** "0,7 ядра", "1 ядро", "2 ядра", "5 ядер": fractions take the genitive singular. */
const coresWord = (v: number) => (fmtNum(v, 1).endsWith(',0') ? plural(Math.round(v), CORES) : 'ядра');

// CPU samples of this browser session (kept across page switches; the backend has no history)
const MAX_SAMPLES = 72; // 6 min at the 5 s system poll
let samples: { t: number; busy: number }[] = [];
const listeners = new Set<() => void>();
function pushSample(t: number, busy: number) {
  if (samples.length && samples[samples.length - 1].t === t) return;
  samples = [...samples, { t, busy }].slice(-MAX_SAMPLES);
  listeners.forEach((l) => l());
}
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};
const snapshot = () => samples;

export function SystemCard() {
  const sys = useSystem();
  const recs = useRecordings({ retry: false });
  const s: SystemInfo | undefined = sys.isError ? undefined : sys.data;
  const history = useSyncExternalStore(subscribe, snapshot);
  const busy = s ? Math.min(s.cpu_count, s.cpu_cores_busy) : 0;

  useEffect(() => {
    if (s) pushSample(sys.dataUpdatedAt, Math.min(s.cpu_count, s.cpu_cores_busy));
  }, [s, sys.dataUpdatedAt]);

  const recBytes = recs.data?.reduce((sum, r) => sum + r.size_bytes, 0);
  const minutes = history.length > 1 ? Math.max(1, Math.round((history[history.length - 1].t - history[0].t) / 60000)) : 0;

  return (
    <Card
      title="Система"
      className={styles.sys}
      badges={
        <Chip variant="outline" size="sm" dot={s ? 'var(--go)' : sys.isError ? 'var(--fault)' : 'var(--caution)'}>
          {s ? 'онлайн' : sys.isError ? 'офлайн' : 'связь…'}
        </Chip>
      }
      help="Бэкенд обрабатывает записи на этой машине; узел ROS 2 для прямого эфира подключается отдельно."
      helpPlacement="bottom-end"
    >
      {sys.isError ? (
        <ErrorBanner error={sys.error} onRetry={() => void sys.refetch()} retrying={sys.isFetching} compact />
      ) : !s ? (
        <div className={styles.center}>
          <Spinner />
        </div>
      ) : (
        <div className={styles.sysBody}>
          <div className={styles.cpu}>
            <div className={styles.lab}>Загрузка CPU</div>
            <div className={styles.cpuV}>
              {fmtNum(busy, 1)}
              <small>{coresWord(busy)}</small>
            </div>
            <div className={styles.cores} style={{ gridTemplateColumns: `repeat(${Math.min(16, s.cpu_count)}, 1fr)` }} aria-hidden>
              {Array.from({ length: Math.min(16, s.cpu_count) }, (_, i) => (
                <i key={i}>
                  <b style={{ width: `${Math.max(0, Math.min(1, busy - i)) * 100}%` }} />
                </i>
              ))}
            </div>
            <div className={styles.meta}>
              из {fmtInt(s.cpu_count)}
              {minutes > 0 ? ` · за ${minutes} мин` : ''}
            </div>
            <Sparkline
              values={history.map((h) => h.busy)}
              min={0}
              max={Math.max(1, ...history.map((h) => h.busy)) * 1.15}
              height={30}
              className={styles.spk}
              label="Загрузка CPU за последние минуты"
            />
          </div>
          <div className={styles.srows}>
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="server" size={17} />
              </span>
              <span className={styles.sn}>Бэкенд</span>
              <span className={styles.sv}>
                <span className={styles.ldot} />
                {fmtDuration(s.uptime_s)}
              </span>
            </div>
            <Link to="/live" className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="live" size={17} />
              </span>
              <span className={styles.sn}>Эфир</span>
              <span className={styles.sv}>
                <Chip variant="outline" size="sm">
                  нет узла
                </Chip>
              </span>
            </Link>
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="folder" size={17} />
              </span>
              <span className={styles.sn}>Записи</span>
              <span className={styles.sv}>
                <span>
                  {fmtInt(s.counts.recordings)}
                  {recBytes !== undefined && recBytes > 0 && <span className={styles.recSz}> · {fmtBytes(recBytes)}</span>}
                </span>
              </span>
            </div>
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="database" size={17} />
              </span>
              <span className={styles.sn}>Свободно</span>
              <span className={styles.sv}>{fmtBytes(s.disk_free_bytes)}</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
