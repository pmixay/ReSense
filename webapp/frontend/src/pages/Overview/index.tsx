// Главная — foundation placeholder: the bento of the «Линия» overview wired to live data where it is
// cheap (system, recordings, runs); the full page is built later on top of this layout.
import { Link } from 'react-router-dom';
import { useRecordings, useRuns, useSystem } from '../../api/hooks';
import type { Run, SystemInfo } from '../../api/types';
import {
  Button,
  Card,
  Chip,
  DecisionLegend,
  DecisionStrip,
  EmptyState,
  ErrorBanner,
  Icon,
  IconButton,
  KpiTile,
  PageHeader,
  Spinner,
  StopMark,
} from '../../components';
import { CORES, RECORDINGS, fmtBytes, fmtCount, fmtDuration, fmtFrames, fmtMs, fmtNum, fmtRelDate, fmtTime, plural } from '../../lib/format';
import styles from './Overview.module.css';

const FORMATS = ['rosbag2 .zip', '.db3 + yaml', '.mcap', '.jsonl', '.npy / .npz'];

/** "0,7 ядра", "1 ядро", "2 ядра", "5 ядер": fractions take the genitive singular. */
const coresWord = (v: number) => (fmtNum(v, 1).endsWith(',0') ? plural(Math.round(v), CORES) : 'ядра');

function Cta() {
  const recs = useRecordings({ retry: false });
  const last = recs.data?.[0];
  return (
    <Card variant="red" className={styles.cta}>
      <svg className={styles.deco} viewBox="0 0 260 262" preserveAspectRatio="xMaxYMid slice" aria-hidden>
        <path d="M-10 150 H150 a40 40 0 0 0 40 -40 V-10" fill="none" stroke="rgba(255,255,255,.22)" strokeWidth="22" strokeLinecap="round" />
        <circle cx="190" cy="92" r="30" fill="#fff" fillOpacity=".16" stroke="rgba(255,255,255,.55)" strokeWidth="10" />
        <circle cx="96" cy="150" r="17" fill="none" stroke="rgba(255,255,255,.45)" strokeWidth="7" />
      </svg>
      <h2 className={styles.ctaTitle}>Новая запись</h2>
      <div className={styles.fmts}>
        {FORMATS.map((f) => (
          <span key={f} className={styles.fmt}>
            {f}
          </span>
        ))}
      </div>
      {last && (
        <div className={styles.last}>
          <span className={styles.lastIc}>
            <Icon name="clock" size={16} />
          </span>
          последняя: <b>{last.name}</b>
          <span className={styles.sz}>· {fmtBytes(last.size_bytes)}</span> · {fmtTime(last.created_at)}
        </div>
      )}
      <div className={styles.acts}>
        <Button variant="light" size="lg" icon="upload" to="/upload">
          Загрузить запись
        </Button>
        <Button variant="ghost-light" size="lg" icon="sparkle" to="/upload?source=demo">
          Демо
        </Button>
      </div>
    </Card>
  );
}

function PlayerEntry({ run }: { run: Run | undefined }) {
  return (
    <Link to={run ? `/player/${run.id}` : '/player'} className={styles.pc} aria-label="Открыть плеер">
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
      <div className={styles.pcBottom}>
        <div>
          <h2 className={styles.pcTitle}>Плеер</h2>
          <span className={styles.pcName}>{run ? run.name : 'откройте прогон'}</span>
        </div>
        <span className={styles.play}>
          <Icon name="play" size={24} />
        </span>
      </div>
    </Link>
  );
}

function SystemCard() {
  const sys = useSystem();
  const s: SystemInfo | undefined = sys.isError ? undefined : sys.data;
  const busy = s ? Math.min(s.cpu_count, s.cpu_cores_busy) : 0;
  return (
    <Card
      title="Система"
      className={styles.sys}
      badges={
        <Chip variant="outline" size="sm" dot={s ? 'var(--go)' : sys.isError ? 'var(--fault)' : 'var(--caution)'}>
          {s ? 'онлайн' : sys.isError ? 'офлайн' : 'связь…'}
        </Chip>
      }
      help="Бэкенд обрабатывает записи на этой машине; узел ROS 2 для эфира подключается отдельно."
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
            <div className={styles.cores} aria-hidden>
              {Array.from({ length: Math.min(16, s.cpu_count) }, (_, i) => (
                <i key={i}>
                  <b style={{ width: `${Math.max(0, Math.min(1, busy - i)) * 100}%` }} />
                </i>
              ))}
            </div>
            <div className={styles.meta}>из {s.cpu_count} · нагрузка за минуту</div>
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
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="live" size={17} />
              </span>
              <span className={styles.sn}>Эфир</span>
              <span className={styles.sv}>
                <Chip variant="outline" size="sm">
                  нет узла
                </Chip>
              </span>
            </div>
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="folder" size={17} />
              </span>
              <span className={styles.sn}>Записи</span>
              <span className={styles.sv}>{fmtCount(s.counts.recordings, RECORDINGS)}</span>
            </div>
            <div className={styles.srow}>
              <span className={styles.sic}>
                <Icon name="database" size={17} />
              </span>
              <span className={styles.sn}>Диск</span>
              <span className={styles.sv}>свободно {fmtBytes(s.disk_free_bytes)}</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

function RecentRuns({ runs, error, loading, retry }: { runs: Run[] | undefined; error: unknown; loading: boolean; retry: () => void }) {
  const list = (runs ?? []).slice(0, 6);
  return (
    <Card
      title="Последние прогоны"
      help="Полоса — решение детектора в каждом кадре записи."
      helpPlacement="bottom-start"
      className={styles.runs}
      actions={
        <>
          <DecisionLegend className={styles.legend} />
          <Button variant="outline" size="sm" iconRight="arrow-right" to="/runs">
            Все прогоны
          </Button>
        </>
      }
    >
      {error ? (
        <ErrorBanner error={error} onRetry={retry} />
      ) : loading ? (
        <div className={styles.center}>
          <Spinner />
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon="list"
          title="Прогонов пока нет"
          action={
            <Button variant="dark" icon="upload" to="/upload">
              Загрузить запись
            </Button>
          }
        >
          Загрузите запись или создайте демо — результат появится здесь.
        </EmptyState>
      ) : (
        <table className={styles.rt}>
          <colgroup>
            <col className={styles.cNm} />
            <col className={styles.cSt} />
            <col className={styles.cDc} />
            <col className={styles.cWh} />
            <col className={styles.cAr} />
          </colgroup>
          <thead>
            <tr>
              <th>Запись</th>
              <th>Решения по кадрам</th>
              <th>СТОП</th>
              <th>Когда</th>
              <th aria-label="Открыть" />
            </tr>
          </thead>
          <tbody>
            {list.map((r) => (
              <tr key={r.id}>
                <td>
                  <div className={styles.nm} title={r.name}>
                    {r.name}
                  </div>
                  <div className={styles.mt}>
                    {fmtFrames(r.summary.n_frames)} · {fmtDuration(r.summary.duration_s)}
                  </div>
                </td>
                <td>
                  <DecisionStrip decisions={r.summary.decisions} height={22} />
                </td>
                <td className={styles.wh}>
                  {r.summary.first_stop ? `с кадра ${r.summary.first_stop.frame}` : 'нет'}
                </td>
                <td className={styles.wh}>{fmtRelDate(r.created_at)}</td>
                <td>
                  <IconButton icon="arrow-right" label={`Открыть прогон ${r.name}`} to={`/runs/${r.id}`} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function Kpis({ runs }: { runs: Run[] | undefined }) {
  const latest = runs?.[0];
  const withStop = runs?.find((r) => r.summary.first_stop);
  const stops = runs?.reduce((s, r) => s + r.summary.stop_episodes, 0);
  return (
    <div className={styles.kpis}>
      <KpiTile
        variant="dark"
        size="lg"
        label="p95 задержка"
        icon={<Icon name="clock" size={17} />}
        value={latest ? fmtNum(latest.summary.latency_ms.p95) : '—'}
        unit={latest ? 'мс' : undefined}
        sub={latest ? `макс. ${fmtMs(latest.summary.latency_ms.max)} · ${latest.name}` : 'после первого прогона'}
      />
      <KpiTile
        size="lg"
        label="Прогонов"
        icon={<Icon name="list" size={17} />}
        value={runs ? fmtNum(runs.length) : '—'}
        sub={latest ? `последний ${fmtRelDate(latest.created_at)}` : 'пока нет'}
      />
      <KpiTile
        size="lg"
        label="СТОП-эпизоды"
        icon={<StopMark />}
        help="Сколько раз решение переходило в СТОП, по всем прогонам."
        helpPlacement="top"
        value={stops !== undefined ? fmtNum(stops) : '—'}
        sub={runs ? `в ${fmtCount(runs.length, ['прогоне', 'прогонах', 'прогонах'])}` : '—'}
      />
      <KpiTile
        size="lg"
        label="Первый СТОП"
        icon={<StopMark />}
        value={withStop?.summary.first_stop?.distance !== null && withStop?.summary.first_stop?.distance !== undefined ? fmtNum(withStop.summary.first_stop.distance, 1) : '—'}
        unit={withStop?.summary.first_stop?.distance !== null && withStop?.summary.first_stop?.distance !== undefined ? 'м' : undefined}
        sub={withStop ? `${withStop.name} · кадр ${withStop.summary.first_stop?.frame}` : 'нет СТОП'}
      />
    </div>
  );
}

export default function Overview() {
  const sys = useSystem();
  const runs = useRuns({ retry: false });
  const version = sys.isError ? undefined : sys.data?.detector_version;
  const lastRun = runs.data?.[0];
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
            <Button variant="dark" icon="play" to={lastRun ? `/player/${lastRun.id}` : '/player'}>
              Открыть плеер
            </Button>
          </>
        }
      />
      <section className={`grid-12 fill-viewport ${styles.ov}`}>
        <Cta />
        <PlayerEntry run={lastRun} />
        <SystemCard />
        <RecentRuns runs={runs.data} error={runs.isError ? runs.error : undefined} loading={runs.isLoading} retry={() => void runs.refetch()} />
        <Kpis runs={runs.isError ? undefined : runs.data} />
      </section>
    </>
  );
}
