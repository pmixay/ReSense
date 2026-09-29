// An SVG line chart over time (s): one or more series (null = a gap), an optional band (the labelled
// object's extent), point markers, shaded stretches without data, and a crosshair + tooltip on hover
// and keyboard focus (←/→ step one sample, Enter picks). Sized to its container.
import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent, type ReactNode } from 'react';
import { fmtNum, fmtNumTrim } from '../../../lib/format';
import { nearestIndex, niceDomain, niceTicks } from './analysis';
import styles from './LineChart.module.css';

export interface ChartLine {
  id: string;
  color: string;
  t: readonly number[];
  v: readonly (number | null)[];
  width?: number;
  /** stroke-dasharray (a secondary encoding when lines overlap) */
  dash?: string;
}

export interface ChartBand {
  t: readonly number[];
  lo: readonly (number | null)[];
  hi: readonly (number | null)[];
}

export interface ChartPoint {
  t: number;
  v: number;
  kind: 'stop' | 'min' | 'caution';
  label?: string;
}

export interface LineChartProps {
  lines: readonly ChartLine[];
  band?: ChartBand | null;
  points?: readonly ChartPoint[];
  /** the x range is 0..xMax (default: the longest line) */
  xMax?: number;
  unit: string;
  /** smallest y span (units) so a flat line does not fill the plot with noise */
  minSpan?: number;
  /** tooltip body at the hovered sample (idx = nearest index per line, −1 when a line has no data) */
  tooltip?: (t: number, idx: readonly number[]) => ReactNode;
  onPick?: (t: number, idx: readonly number[]) => void;
  /** shade the stretches where the first line has no value, labelled (per sample index: a stretch
   *  is split where its label changes) */
  emptyLabel?: string | ((index: number) => string);
  /** under the x labels, aligned with the plot (e.g. a thin decision strip) */
  footer?: ReactNode;
  /** a cursor set from outside (e.g. the hovered event), in seconds */
  cursor?: number | null;
  ariaLabel: string;
  className?: string;
}

const L = 60;
const R = 14;
const T = 12;
const X_LABELS = 28;
const FOOTER = 14;

function linePath(t: readonly number[], v: readonly (number | null)[], X: (t: number) => number, Y: (v: number) => number): string {
  let d = '';
  let pen = false;
  const n = Math.min(t.length, v.length);
  for (let i = 0; i < n; i += 1) {
    const y = v[i];
    if (y === null || y === undefined || !Number.isFinite(y)) {
      pen = false;
      continue;
    }
    d += `${pen ? 'L' : 'M'}${X(t[i]).toFixed(1)} ${Y(y).toFixed(1)}`;
    pen = true;
  }
  return d;
}

function bandPaths(b: ChartBand, X: (t: number) => number, Y: (v: number) => number): { fill: string; edges: string } {
  let fill = '';
  let edges = '';
  const n = Math.min(b.t.length, b.lo.length, b.hi.length);
  let i = 0;
  while (i < n) {
    if (b.lo[i] === null || b.hi[i] === null) {
      i += 1;
      continue;
    }
    let j = i;
    while (j + 1 < n && b.lo[j + 1] !== null && b.hi[j + 1] !== null) j += 1;
    // one sample wide stretches get half a frame on each side so they stay visible
    const dt = n > 1 ? (b.t[Math.min(n - 1, i + 1)] - b.t[Math.max(0, i - 1)]) / 4 : 0.05;
    const x0 = X(b.t[i] - (i === j ? dt : 0));
    const x1 = X(b.t[j] + (i === j ? dt : 0));
    let top = '';
    let bot = '';
    for (let k = i; k <= j; k += 1) {
      const x = i === j ? (k === i ? x0 : x1) : X(b.t[k]);
      top += `${k === i ? 'M' : 'L'}${x.toFixed(1)} ${Y(b.hi[k] as number).toFixed(1)}`;
      bot = `L${x.toFixed(1)} ${Y(b.lo[k] as number).toFixed(1)}` + bot;
    }
    if (i === j) {
      top += `L${x1.toFixed(1)} ${Y(b.hi[i] as number).toFixed(1)}`;
      bot = `L${x1.toFixed(1)} ${Y(b.lo[i] as number).toFixed(1)}` + bot;
    }
    fill += `${top}${bot}Z`;
    edges += top;
    edges += bot.replace(/^L/, 'M');
    i = j + 1;
  }
  return { fill, edges };
}

export function LineChart({ lines, band, points, xMax, unit, minSpan = 1, tooltip, onPick, emptyLabel, footer, cursor, ariaLabel, className }: LineChartProps) {
  const wrap = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [hoverT, setHoverT] = useState<number | null>(null);

  useLayoutEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const measure = () => setSize((s) => (s.w === el.clientWidth && s.h === el.clientHeight ? s : { w: el.clientWidth, h: el.clientHeight }));
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const B = X_LABELS + (footer ? FOOTER : 0);
  const geo = useMemo(() => {
    const { w, h } = size;
    const x1 = Math.max(0.1, xMax ?? Math.max(0.1, ...lines.map((l) => l.t[l.t.length - 1] ?? 0)));
    const all: (number | null)[] = [];
    for (const l of lines) all.push(...l.v);
    if (band) all.push(...band.lo, ...band.hi);
    for (const p of points ?? []) all.push(p.v);
    const dom = niceDomain(all, minSpan);
    if (!dom || w < 80 || h < 60) return null;
    const pw = w - L - R;
    const phh = h - T - B;
    // snap the domain to the tick step so the top and bottom lines are labelled
    const raw = niceTicks(dom[0], dom[1], Math.max(3, Math.min(8, Math.floor(phh / 44))));
    const yStep = raw.length > 1 ? raw[1] - raw[0] : 1;
    const y0 = Math.floor(dom[0] / yStep + 1e-9) * yStep;
    const y1 = Math.ceil(dom[1] / yStep - 1e-9) * yStep;
    const yTicks = niceTicks(y0, y1, Math.round((y1 - y0) / yStep) + 1);
    const X = (t: number) => L + (Math.min(Math.max(t, 0), x1) / x1) * pw;
    const Y = (v: number) => T + (1 - (v - y0) / (y1 - y0 || 1)) * phh;
    const yDigits = yStep < 1 ? (yStep < 0.1 ? 2 : 1) : 0;
    const xTicks = niceTicks(0, x1, Math.max(3, Math.min(10, Math.floor(pw / 90))));
    const paths = lines.map((l) => linePath(l.t, l.v, X, Y));
    const bp = band ? bandPaths(band, X, Y) : null;
    // stretches of the first line without a value
    const empties: { x0: number; x1: number; label: string }[] = [];
    const first = lines[0];
    if (emptyLabel && first && first.v.some((v) => v !== null)) {
      const n = first.t.length;
      const labelAt = (k: number) => (typeof emptyLabel === 'function' ? emptyLabel(k) : emptyLabel);
      let i = 0;
      while (i < n) {
        if (first.v[i] !== null) {
          i += 1;
          continue;
        }
        const label = labelAt(i);
        let j = i;
        while (j + 1 < n && first.v[j + 1] === null && labelAt(j + 1) === label) j += 1;
        const a = i === 0 ? L : (X(first.t[i - 1]) + X(first.t[i])) / 2;
        const b = j === n - 1 ? L + pw : (X(first.t[j]) + X(first.t[j + 1])) / 2;
        // stretches with different labels side by side keep a hairline between them
        const joined = empties.length > 0 && Math.abs(empties[empties.length - 1].x1 - a) < 0.5;
        if (joined) empties[empties.length - 1].x1 -= 1;
        if (b - a >= 6) empties.push({ x0: joined ? a + 1 : a, x1: b, label });
        i = j + 1;
      }
    }
    return { X, Y, x1, pw, phh, yTicks, yDigits, xTicks, paths, bp, empties };
  }, [size, lines, band, points, xMax, minSpan, emptyLabel, B]);

  const shownT = hoverT ?? cursor ?? null;
  const idx = useMemo(() => (shownT === null ? [] : lines.map((l) => nearestIndex(l.t, shownT))), [shownT, lines]);

  const tAt = (clientX: number): number | null => {
    const el = wrap.current;
    if (!el || !geo) return null;
    const r = el.getBoundingClientRect();
    const f = (clientX - r.left - L) / geo.pw;
    if (f < -0.02 || f > 1.02) return null;
    return Math.min(Math.max(f, 0), 1) * geo.x1;
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => setHoverT(tAt(e.clientX));
  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    const t = tAt(e.clientX);
    if (t !== null && onPick) onPick(t, lines.map((l) => nearestIndex(l.t, t)));
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const main = lines[0];
    if (!main || !main.t.length) return;
    const cur = shownT === null ? -1 : nearestIndex(main.t, shownT);
    const big = Math.max(5, Math.round(main.t.length / 20));
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : e.key === 'PageUp' ? big : e.key === 'PageDown' ? -big : 0;
    if (step) {
      e.preventDefault();
      const next = cur < 0 ? 0 : Math.min(main.t.length - 1, Math.max(0, cur + step));
      setHoverT(main.t[next]);
    } else if (e.key === 'Enter' && shownT !== null && onPick) {
      e.preventDefault();
      onPick(shownT, lines.map((l) => nearestIndex(l.t, shownT)));
    } else if (e.key === 'Escape') setHoverT(null);
  };

  // the crosshair snaps to the first line's nearest sample
  const snapT = shownT === null ? null : lines[0] && idx[0] >= 0 ? lines[0].t[idx[0]] : shownT;
  const crossX = geo && snapT !== null ? geo.X(snapT) : null;
  const tipLeft = crossX !== null && geo ? crossX > L + geo.pw * 0.62 : false;

  return (
    <div
      ref={wrap}
      className={[styles.wrap, onPick ? styles.pick : '', className].filter(Boolean).join(' ')}
      tabIndex={0}
      role="group"
      aria-roledescription="график"
      aria-label={ariaLabel}
      onPointerMove={onMove}
      onPointerLeave={() => setHoverT(null)}
      onClick={onClick}
      onKeyDown={onKey}
      onBlur={() => setHoverT(null)}
    >
      {geo && (
        <svg className={styles.svg} width={size.w} height={size.h} aria-hidden>
          {geo.empties.map((e, i) => {
            const wdt = e.x1 - e.x0;
            // the label runs up the stretch when it fits (≈ 6.4 px per character at 11.5 px)
            const fits = wdt >= 18 && e.label.length * 6.4 + 20 < geo.phh;
            return (
              <g key={i}>
                <rect x={e.x0} y={T} width={wdt} height={geo.phh} rx={6} className={styles.empty} />
                {fits && (
                  <text className={styles.emptyText} transform={`translate(${(e.x0 + e.x1) / 2 + 4} ${T + geo.phh - 10}) rotate(-90)`}>
                    {e.label}
                  </text>
                )}
              </g>
            );
          })}
          {geo.yTicks.map((v) => (
            <g key={v}>
              <line x1={L} x2={L + geo.pw} y1={geo.Y(v)} y2={geo.Y(v)} className={styles.grid} />
              <text x={L - 10} y={geo.Y(v) + 4} textAnchor="end" className={styles.axisText}>
                {`${fmtNum(v, geo.yDigits)} ${unit}`}
              </text>
            </g>
          ))}
          {geo.xTicks.map((t, i) => (
            <text
              key={t}
              x={geo.X(t)}
              y={T + geo.phh + 19}
              textAnchor={i === 0 ? 'start' : t >= geo.x1 - 1e-9 ? 'end' : 'middle'}
              className={styles.axisText}
            >
              {`${fmtNumTrim(t, 1)} с`}
            </text>
          ))}
          {geo.bp && (
            <g>
              <path d={geo.bp.fill} className={styles.band} />
              <path d={geo.bp.edges} className={styles.bandEdge} />
            </g>
          )}
          {geo.paths.map((d, i) => (
            <path
              key={lines[i].id}
              d={d}
              fill="none"
              stroke={lines[i].color}
              strokeWidth={lines[i].width ?? 2.4}
              strokeDasharray={lines[i].dash}
              strokeLinejoin="round"
              strokeLinecap={lines[i].dash ? 'butt' : 'round'}
            />
          ))}
          {points?.map((p, i) => {
            const x = geo.X(p.t);
            const y = geo.Y(p.v);
            if (p.kind === 'stop') return <circle key={i} cx={x} cy={y} r={7} className={styles.pStop} />;
            if (p.kind === 'caution') return <circle key={i} cx={x} cy={y} r={5} className={styles.pCaution} />;
            const below = y + 26 < T + geo.phh;
            return (
              <g key={i}>
                <circle cx={x} cy={y} r={4.5} className={styles.pMin} />
                {p.label && (
                  <text x={Math.min(Math.max(x, L + 40), L + geo.pw - 40)} y={below ? y + 22 : y - 12} textAnchor="middle" className={styles.pLabel}>
                    {p.label}
                  </text>
                )}
              </g>
            );
          })}
          {crossX !== null && (
            <g>
              <line x1={crossX} x2={crossX} y1={T} y2={T + geo.phh} className={styles.cross} />
              {lines.map((l, i) => {
                const k = idx[i];
                const v = k >= 0 ? l.v[k] : null;
                return v === null || v === undefined ? null : <circle key={l.id} cx={geo.X(l.t[k])} cy={geo.Y(v)} r={5} fill="#fff" stroke={l.color} strokeWidth={3} />;
              })}
            </g>
          )}
        </svg>
      )}
      {footer && geo && (
        <div className={styles.footer} style={{ left: L, right: R }}>
          {footer}
        </div>
      )}
      {tooltip && geo && crossX !== null && shownT !== null && (
        <div className={styles.tip} style={tipLeft ? { right: size.w - crossX + 12, top: T + 6 } : { left: crossX + 12, top: T + 6 }}>
          {tooltip(shownT, idx)}
        </div>
      )}
    </div>
  );
}
