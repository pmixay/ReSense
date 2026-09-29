// The player entry: the newest run with stored clouds (one with a STOP preferred), shown in 3D at
// its first STOP (CloudPreview, lazy: three.js loads with it); play opens /player/<id>?pos=….
import { lazy, Suspense } from 'react';
import { Link } from 'react-router-dom';
import type { Run } from '../../api/types';
import { Chip, DecisionChip, Icon } from '../../components';
import { decisionAt } from '../../lib/decisions';
import { fmtInt } from '../../lib/format';
import { firstStopPos, playerRun } from './kpis';
import styles from './Overview.module.css';

const CloudPreview = lazy(() => import('../../player/CloudPreview'));

function Tunnel() {
  return (
    <svg className={styles.tunnel} viewBox="0 0 360 262" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <defs>
        <radialGradient id="ov-glow" cx="50%" cy="44%" r="60%">
          <stop offset="0" stopColor="#1B2A44" />
          <stop offset="1" stopColor="#05070D" />
        </radialGradient>
      </defs>
      <rect width="360" height="262" fill="url(#ov-glow)" />
      {[0, 1, 2, 3, 4, 5].map((i) => {
        const k = 1 - i * 0.16;
        const w = 150 * k;
        const h = 170 * k;
        return <rect key={i} x={180 - w / 2} y={128 - h * 0.62} width={w} height={h} fill="none" stroke="#2BD46F" strokeOpacity={0.25 + i * 0.1} strokeWidth="1.5" />;
      })}
      <path d="M100 262 L172 110 M260 262 L188 110" stroke="#2BD46F" strokeOpacity=".55" strokeWidth="1.5" />
      <path d="M150 262 L177 110 M210 262 L183 110" stroke="#fff" strokeOpacity=".5" strokeWidth="1.2" strokeDasharray="2 5" />
    </svg>
  );
}

export function PlayerCard({ runs, loading, offline }: { runs: Run[] | undefined; loading: boolean; offline?: boolean }) {
  const run = playerRun(runs);
  if (!run) {
    return (
      <Link to={runs?.length ? `/player/${runs[0].id}` : '/upload?source=demo'} className={styles.pc} aria-label="Плеер">
        <Tunnel />
        <div className={styles.pcBottom}>
          <div>
            <div className={styles.pcRow}>
              <h2 className={styles.pcTitle}>Плеер</h2>
            </div>
            <Chip variant="glass" size="sm">
              {offline ? 'нет связи' : loading ? 'загрузка…' : runs?.length ? 'без облаков точек' : 'нет прогонов'}
            </Chip>
          </div>
          <span className={styles.play}>
            <Icon name={runs?.length ? 'play' : 'sparkle'} size={24} />
          </span>
        </div>
      </Link>
    );
  }
  const pos = firstStopPos(run.summary.decisions);
  const decision = decisionAt(run.summary.decisions, pos) ?? 'GO';
  const frame = run.summary.first_stop?.frame ?? pos;
  return (
    <Link to={`/player/${run.id}?pos=${pos}`} className={styles.pc} aria-label={`Открыть в плеере: ${run.name}`}>
      <Suspense fallback={<Tunnel />}>
        <CloudPreview runId={run.id} pos={pos} height="100%" className={styles.preview} />
      </Suspense>
      <div className={styles.pcBottom}>
        <div className={styles.pcText}>
          <div className={styles.pcRow}>
            <h2 className={styles.pcTitle}>Плеер</h2>
            <Chip variant="glass" size="sm">
              кадр {fmtInt(frame)} / {fmtInt(run.summary.n_frames)}
            </Chip>
          </div>
          <div className={styles.pcRow}>
            <DecisionChip decision={decision} />
            <span className={styles.pcName} title={run.name}>
              {run.name}
            </span>
          </div>
        </div>
        <span className={styles.play}>
          <Icon name="play" size={24} />
        </span>
      </div>
    </Link>
  );
}
