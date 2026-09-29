// Плеер — a fullscreen route outside the AppShell: the dark cab view. Placeholder for now (the 3D
// scene with three.js arrives with the page's own agent; three stays in this chunk only).
import { useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useRun } from '../../api/hooks';
import { Chip, DecisionStrip, EmptyState, IconButton, Logo } from '../../components';
import styles from './Player.module.css';

export default function Player() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const run = useRun(runId, { retry: false });

  useEffect(() => {
    document.title = 'Плеер · ReSense';
  }, []);

  const back = () => {
    if (location.key !== 'default') navigate(-1);
    else navigate(runId ? `/runs/${runId}` : '/');
  };

  return (
    <div className={styles.cab}>
      <div className={styles.roof}>
        <IconButton icon="arrow-left" label="Назад" variant="white" size="lg" onClick={back} tooltip tooltipPlacement="bottom" />
        <div className={styles.rpill}>
          <span className={styles.mark}>
            <Logo compact />
          </span>
          <span className={styles.pn}>Плеер</span>
          <span className={styles.mline} aria-hidden>
            <i />
            <i />
            <i />
            <i className={styles.c} />
            <i />
          </span>
        </div>
        {runId && <Chip variant="white">{run.data?.name ?? runId}</Chip>}
      </div>
      <main className={styles.glass}>
        <EmptyState icon="cube" title="3D-вид из кабины">
          {runId ? 'Плеер в разработке.' : 'Откройте прогон, чтобы посмотреть его в 3D.'}
        </EmptyState>
      </main>
      <div className={styles.console}>
        {run.data ? (
          <DecisionStrip decisions={run.data.summary.decisions} height={26} radius={13} ticks />
        ) : (
          <span className={styles.hint}>шкала кадров</span>
        )}
      </div>
    </div>
  );
}
