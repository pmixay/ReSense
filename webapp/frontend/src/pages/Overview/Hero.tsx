// «Новая запись»: the red hero — accepted formats, the latest recording, «Загрузить запись» and
// «Демо» (generates the approach scene, queues its processing and opens the queue).
import { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCreateJob, useRecordings } from '../../api/hooks';
import { Button, Card, ErrorBanner, Help, Icon, ProgressBar } from '../../components';
import { fmtBytes, fmtClock, fmtPercent, fmtRelDate } from '../../lib/format';
import { useUploadStore } from '../Upload/uploadStore';
import { SCENARIO_LABEL, useDemoGenerator, type DemoRequest } from '../Upload/useDemo';
import styles from './Overview.module.css';

const FORMATS = ['rosbag2 .zip', '.db3 + yaml', '.mcap', '.jsonl', '.npy / .npz'];
const QUICK_DEMO: DemoRequest = { scenario: 'approach', seconds: 15 };

export function Hero() {
  const recs = useRecordings({ retry: false });
  const last = recs.data?.[0];
  const demo = useDemoGenerator('overview');
  const upload = useUploadStore().run; // an upload started on Загрузка keeps going: show it here
  const createJob = useCreateJob();
  const navigate = useNavigate();
  const busy = demo.active !== null || createJob.isPending;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // the demo is queued even if the user has left the page meanwhile; only then no redirect
  const runDemo = async () => {
    createJob.reset();
    demo.dismissError();
    const rec = await demo.generate(QUICK_DEMO);
    if (!rec || demo.take()?.id !== rec.id) return; // failed, or another page's generation
    const job = await createJob.mutateAsync({ recording_id: rec.id }).catch(() => null);
    if (job && mounted.current) navigate('/queue');
  };

  const error = demo.error ?? createJob.error;
  return (
    <Card variant="red" className={styles.cta}>
      <svg className={styles.deco} viewBox="0 0 260 262" preserveAspectRatio="xMaxYMid slice" aria-hidden>
        <path className={styles.decoLine} d="M-10 150 H150 a40 40 0 0 0 40 -40 V-10" fill="none" stroke="rgba(255,255,255,.22)" strokeWidth="22" strokeLinecap="round" />
        <circle cx="190" cy="92" r="30" fill="#fff" fillOpacity=".16" stroke="rgba(255,255,255,.55)" strokeWidth="10" />
        <circle cx="96" cy="150" r="17" fill="none" stroke="rgba(255,255,255,.45)" strokeWidth="7" />
      </svg>
      <div className={styles.ctaHead}>
        <h2 className={styles.ctaTitle}>Новая запись</h2>
        <Help tone="light" placement="bottom-start" width={270}>
          Запись с лидара (rosbag2) или готовые результаты. «Демо» создаёт синтетическую запись «{SCENARIO_LABEL.approach}» на 15 с с эталонной разметкой и сразу
          ставит её в очередь.
        </Help>
      </div>
      <div className={styles.fmts}>
        {FORMATS.map((f) => (
          <span key={f} className={styles.fmt}>
            {f}
          </span>
        ))}
      </div>
      {demo.active ? (
        <div className={styles.demoProg} aria-live="polite">
          <div className={styles.last}>
            <span className={styles.lastIc}>
              <Icon name="sparkle" size={16} />
            </span>
            создаём демо <b>{SCENARIO_LABEL[demo.active.scenario]}</b> · {fmtPercent(demo.fraction)} · осталось ≈ {fmtClock(demo.etaS)}
          </div>
          <ProgressBar value={demo.fraction} height={8} track="glass" label="Создание демо-записи" className={styles.demoBar} />
        </div>
      ) : upload?.status === 'uploading' ? (
        <div className={styles.demoProg} aria-live="polite">
          <Link to="/upload" className={styles.last}>
            <span className={styles.lastIc}>
              <Icon name="upload" size={16} />
            </span>
            загружаем <b className={styles.lastName}>{upload.picked.name}</b>
            {upload.progress?.phase === 'uploading' && <> · {fmtPercent(upload.progress.fraction)}</>}
          </Link>
          <ProgressBar
            value={upload.progress?.phase === 'uploading' ? upload.progress.fraction : null}
            height={8}
            track="glass"
            label="Загрузка записи"
            className={styles.demoBar}
          />
        </div>
      ) : error ? (
        <ErrorBanner error={error} title="Демо не запущено" compact className={styles.ctaErr} />
      ) : last ? (
        <div className={styles.last}>
          <span className={styles.lastIc}>
            <Icon name="clock" size={16} />
          </span>
          последняя: <b className={styles.lastName}>{last.name}</b>
          <span className={styles.sz}>· {fmtBytes(last.size_bytes)}</span> · {fmtRelDate(last.created_at)}
        </div>
      ) : (
        <div className={styles.last}>
          <span className={styles.lastIc}>
            <Icon name={recs.isError ? 'wifi-off' : 'clock'} size={16} />
          </span>
          {recs.isError ? 'нет связи с бэкендом' : recs.isLoading ? 'загрузка…' : 'записей пока нет'}
        </div>
      )}
      <div className={styles.acts}>
        <Button variant="light" size="lg" icon="upload" to="/upload">
          Загрузить запись
        </Button>
        <Button variant="ghost-light" size="lg" icon="sparkle" onClick={() => void runDemo()} loading={busy}>
          Демо
        </Button>
      </div>
    </Card>
  );
}
