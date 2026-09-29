// The console tiles of the cab (glass touch screens seated on the curved console): «Схема пути»,
// the decision, «До препятствия», latency / rate and «Исправность». Every value comes from the
// frame result under the playhead or the run; explanations live in the «?» tooltips.
import type { CSSProperties, ReactNode } from 'react';
import type { DecodedCloud } from '../../api/cloud';
import type { Decision, FrameResultDict } from '../../api/types';
import { DECISION_ICON, Help, Icon } from '../../components';
import { DECISION_CHIP_LABEL } from '../../lib/decisions';
import { DASH, fmtInt, fmtMeters, fmtMs, fmtNum } from '../../lib/format';
import { SENSOR_REACH } from '../../lib/track';
import { decisionText, decisionWordSize, distanceModel, envelopeText, healthRows, type Tone } from './cab';
import { MiniMap } from './MiniMap';
import styles from './Player.module.css';

/** Tiles ride the console arc: the top on the curve, skewed to its slope; the outer ones turn to the driver. */
export function tileStyle(left: number, width: number, ry = 0): CSSProperties {
  const cx = left + width / 2;
  const top = 694 - 40 * ((cx - 800) / 800) ** 2;
  const a = (Math.atan((-80 * (cx - 800)) / 640000) * 180) / Math.PI;
  return {
    left,
    width,
    top: Math.round(top * 10) / 10,
    transform: `${ry ? `perspective(1400px) rotateY(${ry}deg) ` : ''}skewY(${a.toFixed(2)}deg)`,
  };
}

function Title({ children, icon }: { children: ReactNode; icon?: 'clock' | 'live' }) {
  return (
    <div className={styles.tt}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- map

export function MapTile({ frame, cloud, pixelRatio }: { frame: FrameResultDict | null; cloud: DecodedCloud | null; pixelRatio: number }) {
  return (
    <section className={`${styles.tile} ${styles.tMap}`} style={tileStyle(38, 292, 10)} aria-label="Схема пути">
      <MiniMap frame={frame} cloud={cloud} pixelRatio={pixelRatio} />
      <div className={`${styles.tt} ${styles.mapTitle}`}>
        <span>Схема пути</span>
        <Help placement="top-start" tone="light" width={240}>
          Вид сверху: вдоль пути 0–200 м, поперёк растянуто ×18. Зелёное — габарит свободен, пунктир — дальше не проверено.
        </Help>
        <span className={styles.rt}>0–200 м</span>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- decision

export function DecisionTile({ decision, frame, frameNo, confirmS }: { decision: Decision; frame: FrameResultDict | null; frameNo: number | null; confirmS: number }) {
  const word = DECISION_CHIP_LABEL[decision];
  const t = decisionText(decision, frame, confirmS);
  const light = decision !== 'CAUTION';
  return (
    <section className={`${styles.tile} ${styles.tDec} ${styles[`dec_${decision.toLowerCase()}`]}`} style={tileStyle(342, 230)} aria-label="Решение">
      <div className={styles.decTop}>
        <span className={styles.decO}>
          <Icon name={DECISION_ICON[decision]} size={28} strokeWidth={2.6} />
        </span>
        {frameNo !== null && <span className={styles.decFrame}>кадр {fmtInt(frameNo)}</span>}
      </div>
      <div className={styles.decBig} style={{ fontSize: decisionWordSize(word) }}>
        {word}
      </div>
      <div className={styles.decL1}>{t.line1}</div>
      <div className={styles.decL2}>
        {t.line2}
        <Help placement="top" tone={light ? 'light' : 'dark'} width={240}>
          {t.help}
        </Help>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- distance

function DistanceBar({
  free,
  monitored,
  obstacle,
  unverified,
  value,
}: {
  free: number;
  monitored: number | null;
  obstacle: boolean;
  unverified: boolean;
  value: number | null;
}) {
  const W = 426;
  const x = (m: number) => (Math.min(SENSOR_REACH, Math.max(0, m)) / SENSOR_REACH) * W;
  const mon = monitored !== null ? x(monitored) : null;
  const fx = x(free);
  const labelX = Math.min(W - 150, Math.max(70, fx));
  return (
    <svg width={W} height="42" viewBox={`0 0 ${W} 42`} className={styles.dbar} aria-hidden>
      <defs>
        <pattern id="pl-mh" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="7" height="7" fill="#EDE9E4" />
          <rect width="2.5" height="7" fill="#D6CFC6" />
        </pattern>
      </defs>
      <rect x="0" y="5" width={W} height="14" rx="7" fill={unverified ? '#5B4E9C' : '#E7E2DB'} />
      {mon !== null && <rect x="0" y="5" width={Math.max(14, mon + 1.5)} height="14" rx="7" fill="url(#pl-mh)" />}
      {fx > 0.5 && <rect x="0" y="5" width={Math.max(14, fx)} height="14" rx="7" fill="#12A150" />}
      {mon !== null && <rect x={Math.max(0, mon - 1.5)} y="0" width="3" height="24" rx="1.5" fill="#16151A" />}
      {obstacle && (
        <g>
          <circle cx={fx} cy="12" r="10" fill="#D0001B" stroke="#fff" strokeWidth="3" />
          <path d={`M${fx - 4.5} 12h9`} stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
        </g>
      )}
      <text x="0" y="39" fontFamily="Montserrat" fontWeight="800" fontSize="12" fill="#16151A">
        {unverified ? 'не проверено' : 'свободно'}
      </text>
      {value !== null && obstacle && (
        <text x={labelX} y="39" textAnchor="middle" fontFamily="Montserrat" fontWeight="800" fontSize="12" fill="#16151A">
          {fmtNum(value, 1)}
        </text>
      )}
      {mon !== null && (
        <text x={Math.max(150, mon + 2)} y="39" textAnchor="end" fontFamily="Montserrat" fontWeight="800" fontSize="12" fill="#16151A">
          контроль {fmtNum(monitored, 0)} м
        </text>
      )}
    </svg>
  );
}

export function DistanceTile({ frame, decision }: { frame: FrameResultDict | null; decision: Decision | null }) {
  const m = distanceModel(frame, decision);
  return (
    <section className={`${styles.tile} ${styles.tDist}`} style={tileStyle(584, 462)} aria-label={m.title}>
      <div className={styles.tt}>
        {m.title}
        <Help placement="top" width={268}>
          {m.obstacle ? (
            <>
              От датчика до ближайшей точки объекта <b>в этом кадре</b>. Полоса — дальность лидара {fmtMeters(SENSOR_REACH, 0)}: зелёное свободно, штриховка — под
              контролем.
            </>
          ) : m.unverified ? (
            <>
              Входные данные датчика непригодны: <b>в этом кадре</b> путь не проверен, свободная дистанция не заявляется.
            </>
          ) : (
            <>
              Габарит {envelopeText()} свободен до этой дистанции <b>в этом кадре</b>. Полоса — дальность лидара {fmtMeters(SENSOR_REACH, 0)}: штриховка — под
              контролем.
            </>
          )}
        </Help>
      </div>
      <div className={styles.distNum}>
        {m.value !== null ? fmtNum(m.value, 1) : DASH}
        {m.value !== null && <small>м</small>}
      </div>
      <DistanceBar free={m.free} monitored={m.monitored} obstacle={m.obstacle} unverified={m.unverified} value={m.value} />
    </section>
  );
}

// ---------------------------------------------------------------- latency / rate

export function MetricsTile({
  frame,
  latency,
  pos,
  p95,
  playFps,
  speed,
  playing,
}: {
  frame: FrameResultDict | null;
  latency: readonly number[] | null;
  pos: number;
  p95: number | null;
  playFps: number | null;
  speed: number;
  playing: boolean;
}) {
  const total = typeof frame?.timing_ms?.total === 'number' ? frame.timing_ms.total : null;
  const bars: number[] = [];
  if (latency) for (let i = Math.max(0, pos - 13); i <= pos && i < latency.length; i += 1) bars.push(latency[i]);
  const maxBar = Math.max(1, ...bars);
  const target = 10 * speed;
  return (
    <section className={`${styles.tile} ${styles.tMet}`} style={tileStyle(1058, 238)} aria-label="Задержка и частота">
      <div className={styles.tt}>
        <Icon name="clock" size={16} />
        Задержка
        <Help placement="top" width={236}>
          <b>{fmtMs(total)}</b> — обработка этого кадра детектором; p95 по всей записи — <b>{fmtMs(p95)}</b>.
        </Help>
        <span className={styles.tchip}>p95 {p95 !== null ? fmtNum(p95, 0) : DASH}</span>
      </div>
      <div className={styles.metRow}>
        <div className={styles.metV}>
          {total !== null ? fmtNum(total, total < 10 ? 1 : 0) : DASH}
          {total !== null && <small>мс</small>}
        </div>
        <div className={styles.spark} aria-hidden>
          {bars.map((v, i) => (
            <i key={i} style={{ height: Math.max(3, (v / maxBar) * 30), background: i === bars.length - 1 ? '#16151A' : '#D6CFC6' }} />
          ))}
        </div>
      </div>
      <div className={styles.metSep} />
      <Title icon="live">
        Частота
        <span className={styles.tchip}>цель {fmtNum(target, target < 10 ? 1 : 0)}</span>
      </Title>
      <div className={styles.metV} style={{ marginTop: 10 }}>
        {playing && playFps !== null ? fmtNum(playFps, 1) : playing ? DASH : 'пауза'}
        {playing && <small>кадр/с</small>}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- health

const LAMP: Record<Tone, string> = { ok: styles.lampOk, warn: styles.lampWarn, error: styles.lampErr, none: styles.lampNone };

export function HealthTile({ frame, minVisibility }: { frame: FrameResultDict | null; minVisibility: number }) {
  const rows = healthRows(frame, minVisibility);
  return (
    <section className={`${styles.tile} ${styles.tHl}`} style={tileStyle(1308, 254, -10)} aria-label="Исправность">
      <div className={styles.tt} style={{ marginBottom: 4 }}>
        Исправность
        <Help placement="top-end" width={250}>
          <b>Видимость</b> — докуда лидар видит полотно пути (норма от {fmtMeters(minVisibility, 0)}). <b>Захват рельсов</b> — доля последних кадров, где
          найдена пара рельсов. <b>Калибровка</b> — установка датчика.
        </Help>
      </div>
      {rows.map((r) => (
        <div key={r.key} className={styles.hrow}>
          <span className={`${styles.lamp} ${LAMP[r.tone]}`} aria-hidden />
          {r.label}
          <span className={`${styles.hv} ${r.key === 'calibration' ? styles.hvw : ''}`}>{r.value}</span>
        </div>
      ))}
    </section>
  );
}
