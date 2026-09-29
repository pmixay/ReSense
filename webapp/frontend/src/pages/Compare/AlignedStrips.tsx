// The compared runs' decision strips on one time axis: each strip is as long as its recording, so the
// same second sits at the same x. Hovering reads the frame and decision of every run at that time;
// a click opens the player of the run under the pointer at that frame.
import { useRef, useState, type PointerEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { DecisionStrip, Spinner } from '../../components';
import { DECISION_LABEL, decisionAt } from '../../lib/decisions';
import { fmtDuration, fmtNumTrim } from '../../lib/format';
import { RUN_COLORS, nearestIndex, niceTicks, playerUrl } from '../Runs/common/analysis';
import type { Compared } from './data';
import { RunLabel, mixedPresets } from './Tables';
import styles from './Compare.module.css';

export function AlignedStrips({ items }: { items: readonly Compared[] }) {
  const navigate = useNavigate();
  const area = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const tMax = Math.max(0.1, ...items.map((c) => c.series?.t[c.series.t.length - 1] ?? c.run?.summary.duration_s ?? 0));
  const ticks = niceTicks(0, tMax, 8);
  const showPreset = mixedPresets(items);

  const tAt = (clientX: number) => {
    const r = area.current?.getBoundingClientRect();
    if (!r) return null;
    const f = (clientX - r.left) / Math.max(1, r.width);
    return f < 0 || f > 1 ? null : f * tMax;
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => setHover(tAt(e.clientX));
  const posAt = (c: Compared, t: number) => {
    const s = c.series;
    if (!s || !s.t.length || t > s.t[s.t.length - 1] + 0.05) return -1;
    return nearestIndex(s.t, t);
  };

  return (
    <div className={styles.strips}>
      {items.map((c) => {
        const s = c.series;
        const dur = s ? s.t[s.t.length - 1] ?? 0 : (c.run?.summary.duration_s ?? 0);
        const p = hover !== null ? posAt(c, hover) : -1;
        const d = p >= 0 && s ? decisionAt(s.decisions, p) : null;
        return (
          <div key={c.id} className={styles.stripRow}>
            <span className={styles.key} style={{ background: RUN_COLORS[c.slot] }} aria-hidden />
            <RunLabel c={c} showPreset={showPreset} className={styles.stripName} />
            <div className={styles.stripCell}>
              {s ? (
                <div style={{ width: `${Math.max(1, (Math.max(dur, 0.05) / tMax) * 100)}%` }}>
                  <DecisionStrip decisions={s.decisions} height={24} radius={8} ariaLabel={`Решения по кадрам: ${c.run?.name ?? c.id}`} />
                </div>
              ) : c.seriesError ? (
                <span className={styles.stripErr}>{c.seriesError.message}</span>
              ) : (
                <Spinner size={16} />
              )}
            </div>
            <span className={styles.stripRead}>
              {hover === null ? fmtDuration(dur) : p >= 0 && s ? `кадр ${s.frame[p]} · ${d ? DECISION_LABEL[d] : ''}` : '—'}
            </span>
          </div>
        );
      })}
      <div className={styles.axisRow}>
        <span />
        <span />
        <div className={styles.axis}>
          {ticks.map((t, i) => (
            <span key={t} className={i === 0 ? styles.t0 : undefined} style={{ left: `${(t / tMax) * 100}%` }}>
              {fmtNumTrim(t, 1)}
              {i === 0 ? ' с' : ''}
            </span>
          ))}
        </div>
        <span />
      </div>
      {/* the hover layer over the strip column */}
      <div
        ref={area}
        className={styles.hoverArea}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        onClick={(e) => {
          const t = tAt(e.clientX);
          if (t === null) return;
          // the row under the pointer
          const rows = [...(e.currentTarget.parentElement?.querySelectorAll<HTMLElement>(`.${styles.stripRow}`) ?? [])];
          const row = rows.findIndex((el) => {
            const r = el.getBoundingClientRect();
            return e.clientY >= r.top && e.clientY <= r.bottom;
          });
          const c = items[row];
          if (!c) return;
          const p = posAt(c, t);
          if (p >= 0) navigate(playerUrl(c.id, p));
        }}
        aria-hidden
      >
        {hover !== null && <span className={styles.hoverLine} style={{ left: `${(hover / tMax) * 100}%` }} />}
      </div>
    </div>
  );
}
