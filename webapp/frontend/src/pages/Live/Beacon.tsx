// The beacon: the decision as a signal head (GO green, CAUTION amber, STOP hatched red with the
// octagon and a pulse, FAULT violet), the distance under it, a 0–210 m bar and the freshness of the
// last message. Anything not live (no link, waiting, stale, paused, ended) is ink or white — never
// a green light.
import type { Decision } from '../../api/types';
import { Card, DECISION_ICON, DecisionChip, Help, Icon, Spinner } from '../../components';
import { DECISION_CHIP_LABEL } from '../../lib/decisions';
import { fmtInt, fmtNum } from '../../lib/format';
import { SENSOR_REACH } from '../../lib/track';
import type { FeedSnapshot } from './feed';
import type { SourceKind } from './SourceBar';
import type { LiveView } from './timeline';
import styles from './Beacon.module.css';

const STATE_LABEL: Record<Exclude<LiveView, 'live'>, string> = {
  idle: 'НЕ ПОДКЛЮЧЕНО',
  connecting: 'ПОДКЛЮЧЕНИЕ',
  waiting: 'ЖДЁМ ДАННЫЕ',
  stale: 'ДАННЫЕ УСТАРЕЛИ',
  paused: 'ПАУЗА',
  ended: 'КОНЕЦ ЗАПИСИ',
  error: 'НЕТ СВЯЗИ',
};

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/** "0,08 с", "2,3 с", "12 с" */
export function fmtAge(ms: number | null): string {
  if (ms === null) return '—';
  const s = ms / 1000;
  return `${fmtNum(s, s < 1 ? 2 : s < 10 ? 1 : 0)} с`;
}

/** The idle state names what is to be done: connect the node or start the replay. */
export function stateLabel(view: Exclude<LiveView, 'live'>, kind: SourceKind): string {
  if (view === 'idle' && kind === 'sim') return 'ЭФИР НЕ ЗАПУЩЕН';
  return STATE_LABEL[view];
}

export interface BeaconProps {
  snap: FeedSnapshot;
  kind: SourceKind;
  className?: string;
}

export function Beacon({ snap, kind, className }: BeaconProps) {
  const { view, msg } = snap;
  const live = view === 'live';
  const decision: Decision | null = msg?.decision ?? null;
  const shown = live || view === 'paused'; // the frame's values are current (a paused replay is inspected on purpose)
  const obstacle = decision === 'STOP' ? num(msg?.nearest_distance) : null;
  // ОШИБКА: the input cannot be trusted — no monitored (green) distance, whatever the frame says
  const clear = decision === 'FAULT' ? null : num(msg?.clear_distance);
  const dist = !shown ? null : decision === 'STOP' ? obstacle : decision === 'FAULT' ? null : clear;
  const distLabel = decision === 'STOP' ? 'До препятствия' : decision === 'FAULT' ? 'Путь не контролируется' : 'Свободно впереди';
  const headTone = live && decision ? decision.toLowerCase() : view === 'idle' || view === 'connecting' || view === 'waiting' ? 'quiet' : 'ink';
  const busy = view === 'connecting' || view === 'waiting';
  // the clock only runs while the link delivers: after the end or an error an old age would read as fresh
  const age = view === 'live' || view === 'stale' || view === 'paused' ? snap.age : null;

  return (
    <Card className={[styles.beacon, className].filter(Boolean).join(' ')} padding="sm" aria-live="polite">
      <div className={[styles.head, styles[headTone], live && decision === 'STOP' ? 'pulse' : ''].join(' ')}>
        {live && decision ? (
          <>
            <Icon name={DECISION_ICON[decision]} size={40} strokeWidth={2.6} className={styles.icon} />
            <span className={[styles.label, DECISION_CHIP_LABEL[decision].length > 5 ? styles.long : ''].join(' ')}>{DECISION_CHIP_LABEL[decision]}</span>
          </>
        ) : (
          <>
            {busy ? (
              <Spinner size={30} tone="ink" />
            ) : (
              <Icon
                name={view === 'paused' ? 'pause' : view === 'idle' ? (kind === 'sim' ? 'play' : 'live') : view === 'error' ? 'wifi-off' : 'clock'}
                size={34}
                className={styles.icon}
              />
            )}
            <span className={[styles.label, styles.state].join(' ')}>{stateLabel(view as Exclude<LiveView, 'live'>, kind)}</span>
            {/* a paused replay is inspected on purpose: its frame's decision; stale data shows none */}
            {decision && view === 'paused' && <DecisionChip decision={decision} size="sm" className={styles.lastChip} title="Решение кадра на паузе" />}
          </>
        )}
        <Help
          placement="bottom-end"
          width={300}
          tone={headTone === 'caution' || headTone === 'quiet' ? 'dark' : 'light'}
          label="Правила решения"
          className={styles.help}
        >
          <b>СТОП</b> — подтверждённое препятствие в габарите 2,1 × 3,0 м.
          <br />
          <b>ОШИБКА</b> — входу нельзя доверять.
          <br />
          <b>ВНИМАНИЕ</b> — объект у габарита или сниженная исправность.
          <br />
          Иначе <b>СВОБОДНО</b>.
          <br />
          Нет сообщения дольше <b>0,5 с</b> — «данные устарели», зелёного нет.
        </Help>
      </div>

      <div className={styles.readout}>
        <div className={styles.rl}>{shown && decision ? distLabel : 'Дистанция'}</div>
        {dist === null ? (
          <div className={[styles.big, styles.none].join(' ')}>—</div>
        ) : (
          <div className={styles.big}>
            {fmtNum(dist, 1)}
            <small>м</small>
          </div>
        )}
        <DistanceBar clear={shown ? clear : null} obstacle={shown ? obstacle : null} live={live} />
      </div>

      <div className={styles.foot}>
        <span className={[styles.lamp, live ? styles.lampOk : snap.age !== null && view !== 'paused' ? styles.lampBad : ''].join(' ')} aria-hidden />
        <span className={styles.fl}>свежесть</span>
        <b>{fmtAge(age)}</b>
        <span className={styles.sp} />
        <Help placement="top-end" width={280} label="Свежесть">
          Время с последнего сообщения. Узел считает результат устаревшим старше <b>0,5 с</b> (max_result_age); здесь то же правило.
        </Help>
      </div>
    </Card>
  );
}

/** 0–210 m: green up to the monitored free distance, hatched beyond; the obstacle as an octagon. */
function DistanceBar({ clear, obstacle, live }: { clear: number | null; obstacle: number | null; live: boolean }) {
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / SENSOR_REACH) * 100)).toFixed(2)}%`;
  const reach = clear ?? obstacle;
  return (
    <div className={styles.barWrap}>
      <div className={styles.bar} aria-hidden>
        {reach !== null && <b className={[styles.fill, live ? styles.fillLive : ''].join(' ')} style={{ width: pct(reach) }} />}
        {obstacle !== null && (
          <span className={styles.obst} style={{ left: pct(obstacle) }}>
            <Icon name="stop-octagon" size={16} strokeWidth={2.8} />
          </span>
        )}
      </div>
      <div className={styles.scale} aria-hidden>
        <span>0</span>
        <span>≈ {fmtInt(SENSOR_REACH)} м</span>
      </div>
    </div>
  );
}
