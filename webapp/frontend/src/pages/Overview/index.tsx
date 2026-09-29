// Главная: a new recording (upload or a one-click demo), the player at the latest STOP, the system,
// the latest runs and four KPI tiles — everything derived from the API.
import { useRuns, useSystem } from '../../api/hooks';
import { Button, Chip, PageHeader } from '../../components';
import { Hero } from './Hero';
import { Kpis } from './Kpis';
import { playerRun } from './kpis';
import { PlayerCard } from './PlayerCard';
import { RecentRuns } from './RecentRuns';
import { SystemCard } from './SystemCard';
import styles from './Overview.module.css';

export default function Overview() {
  const sys = useSystem();
  const runs = useRuns({ retry: false });
  const version = sys.isError ? undefined : sys.data?.detector_version;
  const data = runs.isError ? undefined : runs.data;
  const toPlayer = playerRun(data) ?? data?.[0];
  return (
    <>
      <PageHeader
        title="Главная"
        station="home"
        chips={
          <>
            <Chip variant="outline">команда «Молоток»</Chip>
            <Chip variant="outline">детектор {version ? `v${version}` : '—'}</Chip>
          </>
        }
        actions={
          <>
            <Button variant="outline" icon="live" to="/live">
              Прямой эфир
            </Button>
            <Button variant="dark" icon="play" to={toPlayer ? `/player/${toPlayer.id}` : '/player'}>
              Открыть плеер
            </Button>
          </>
        }
      />
      <section className={`grid-12 fill-viewport ${styles.ov}`}>
        <Hero />
        <PlayerCard runs={data} loading={runs.isLoading} offline={runs.isError} />
        <SystemCard />
        <RecentRuns runs={data} error={runs.isError ? runs.error : undefined} loading={runs.isLoading} retry={() => void runs.refetch()} />
        <Kpis runs={data} offline={runs.isError} />
      </section>
    </>
  );
}
