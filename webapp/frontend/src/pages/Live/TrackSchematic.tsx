// Top-down scheme of the path ahead, drawn from one status message: the track axis and rails from the
// node's track model (lib/track.ts), the 2,1 m envelope up to the monitored range (green only while
// the data is fresh), the advisory margin, the objects (in-gauge hatched red, advisory amber) with
// their distance. X forward to the right (0–200 m); the lateral scale is stretched to be readable.
import { useId } from 'react';
import { DECISION_COLOR } from '../../lib/decisions';
import { fmtInt, fmtNum } from '../../lib/format';
import { ENVELOPE_PROFILE, RAILS_SPACING, WARNING_MARGIN, centerY, defaultTrackModel, profileBounds, samples, type TrackModelDict } from '../../lib/track';
import { detectionRows, type StatusMessage } from './timeline';
import { useSize } from '../../lib/useSize';
import styles from './View.module.css';

const X_MAX = 200;
const LAT = 3.6; // ± metres shown across
const PAD = { l: 58, r: 26, t: 74, b: 40 };
const TICKS = [0, 50, 100, 150, 200];
/** A regular octagon of radius 6,5 around (0, 0): the STOP sign of the object labels. */
const OCTAGON = Array.from({ length: 8 }, (_, k) => {
  const a = ((22.5 + 45 * k) * Math.PI) / 180;
  return `${(6.5 * Math.cos(a)).toFixed(2)},${(6.5 * Math.sin(a)).toFixed(2)}`;
}).join(' ');

function trackOf(msg: StatusMessage | null): TrackModelDict {
  const t = msg?.track;
  return t && Array.isArray(t.floor_coef) && typeof t.center === 'number' ? t : defaultTrackModel();
}

export interface TrackSchematicProps {
  msg: StatusMessage | null;
  /** live data: the monitored envelope is green */
  fresh: boolean;
  /** draw the frame's objects and range (live, or a paused replay); off for stale data */
  show?: boolean;
}

export function TrackSchematic({ msg, fresh, show = fresh }: TrackSchematicProps) {
  const [ref, w, h] = useSize<HTMLDivElement>();
  const hatchId = useId().replace(/:/g, '');
  const track = trackOf(msg);
  const { yMin, yMax } = profileBounds(ENVELOPE_PROFILE);
  const iw = Math.max(1, w - PAD.l - PAD.r);
  const ih = Math.max(1, h - PAD.t - PAD.b);
  const sx = (x: number) => PAD.l + (Math.min(X_MAX, Math.max(0, x)) / X_MAX) * iw;
  const sy = (y: number) => PAD.t + ((LAT - y) / (2 * LAT)) * ih;

  // ОШИБКА: the path is not monitored — no envelope in green and no range, only the objects
  const monitored = show && msg?.decision !== 'FAULT';
  const clear = typeof msg?.clear_distance === 'number' && monitored ? Math.min(X_MAX, Math.max(3, msg.clear_distance)) : 3;
  const band = (x0: number, x1: number, lo: number, hi: number) => {
    const xs = samples(x0, x1, 2);
    if (xs.length < 2) return '';
    const top = xs.map((x) => `${sx(x).toFixed(1)},${sy(centerY(track, x) + hi).toFixed(1)}`);
    const bot = xs.map((x) => `${sx(x).toFixed(1)},${sy(centerY(track, x) + lo).toFixed(1)}`).reverse();
    return `M${top.join(' L')} L${bot.join(' L')} Z`;
  };
  const line = (x0: number, x1: number, off: number) =>
    'M' +
    samples(x0, x1, 2)
      .map((x) => `${sx(x).toFixed(1)},${sy(centerY(track, x) + off).toFixed(1)}`)
      .join(' L');

  const objects = show ? detectionRows(msg) : [];
  const ready = w > 0 && h > 0;

  return (
    <div ref={ref} className={styles.scheme} role="img" aria-label="Схема пути сверху: габарит, ось и объекты">
      {ready && (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <defs>
            <pattern id={hatchId} width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="7" height="7" fill={DECISION_COLOR.STOP} />
              <rect width="2.6" height="7" fill="rgba(255,255,255,.3)" />
            </pattern>
          </defs>
          {/* tunnel bed */}
          <path d={band(0, X_MAX, -2.5, 2.5)} className={styles.bed} />
          {/* distance grid */}
          {TICKS.map((x) => (
            <g key={x}>
              <line x1={sx(x)} x2={sx(x)} y1={PAD.t} y2={h - PAD.b + 6} className={styles.grid} />
              <text x={sx(x)} y={h - PAD.b + 24} className={styles.tick} textAnchor={x === 0 ? 'start' : x === X_MAX ? 'end' : 'middle'}>
                {x === X_MAX ? `${x} м` : x}
              </text>
            </g>
          ))}
          {/* envelope: monitored part, then the rest outlined */}
          <path d={band(3, X_MAX, yMin, yMax)} className={styles.envRest} />
          {monitored && <path d={band(3, clear, yMin, yMax)} className={fresh ? styles.env : styles.envPaused} />}
          {monitored && (
            <>
              <path d={line(3, clear, yMax + WARNING_MARGIN)} className={styles.margin} />
              <path d={line(3, clear, yMin - WARNING_MARGIN)} className={styles.margin} />
            </>
          )}
          <path d={line(0, X_MAX, RAILS_SPACING / 2)} className={styles.rail} />
          <path d={line(0, X_MAX, -RAILS_SPACING / 2)} className={styles.rail} />
          <path d={line(0, X_MAX, 0)} className={styles.axis} />
          {/* monitored range: the label sits in the bed under the envelope, clear of the card's
              header (view switch) and of the object labels above the objects */}
          {monitored && clear > 3 && (
            <g>
              <line x1={sx(clear)} x2={sx(clear)} y1={PAD.t} y2={h - PAD.b} className={styles.clearLine} />
              <text
                x={sx(clear) > w - 140 ? sx(clear) - 8 : sx(clear) + 8}
                y={sy(centerY(track, clear) - 2.5) - 10}
                className={styles.clearText}
                textAnchor={sx(clear) > w - 140 ? 'end' : 'start'}
              >
                контроль {fmtInt(clear)} м
              </text>
            </g>
          )}
          {/* the train */}
          <g>
            <rect x={PAD.l - 46} y={sy(1.45)} width={40} height={sy(-1.45) - sy(1.45)} rx={9} className={styles.train} />
            <rect x={PAD.l - 12} y={sy(1.45)} width={6} height={sy(-1.45) - sy(1.45)} rx={3} className={styles.nose} />
          </g>
          {/* objects */}
          {objects.map((o) => {
            const xc = o.distance + o.size[0] / 2;
            const cx = sx(xc);
            const cy = sy(centerY(track, xc) + o.lateral); // lateral is measured from the track axis
            const bw = Math.max(9, (o.size[0] / X_MAX) * iw);
            const bh = Math.max(9, (o.size[1] / (2 * LAT)) * ih);
            const gauge = o.zone === 'gauge';
            const label = `${fmtNum(o.distance, 1)} м`;
            const labelW = 34 + 7.6 * label.length;
            return (
              <g key={o.key}>
                <rect
                  x={cx - bw / 2}
                  y={cy - bh / 2}
                  width={bw}
                  height={bh}
                  rx={3}
                  fill={gauge ? `url(#${hatchId})` : DECISION_COLOR.CAUTION}
                  className={styles.obj}
                />
                {gauge && (
                  // the STOP distance as the decision is drawn everywhere: hatched red with the octagon
                  <g transform={`translate(${Math.min(Math.max(cx - labelW / 2, 4), w - labelW - 4)}, ${cy - bh / 2 - 30})`}>
                    <rect width={labelW} height={22} rx={11} fill={`url(#${hatchId})`} className={styles.objPill} />
                    <polygon points={OCTAGON} transform="translate(12 11)" className={styles.objOct} />
                    <line x1={8.8} x2={15.2} y1={11} y2={11} className={styles.objBar} />
                    <text x={23} y={15} className={styles.objText}>
                      {label}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
