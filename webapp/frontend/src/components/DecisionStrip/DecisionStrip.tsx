// The decision string as a coloured strip on a canvas: one column per frame, or per pixel when there
// are more frames than pixels (the most severe decision wins, STOP > FAULT > CAUTION > GO), so an
// 11 000-frame ride costs ~600 rectangles. STOP carries the white 45° hatch. Optional: marker pills
// above, a playhead, click / drag / keyboard seeking, a second lane for labels, an axis.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import type { Decision } from '../../api/types';
import { CODE_DECISION, DECISION_COLOR, DECISION_LABEL, binDecisions, decisionAt } from '../../lib/decisions';
import styles from './DecisionStrip.module.css';

export type MarkerTone = 'stop' | 'go' | 'caution' | 'fault' | 'ink';

export interface StripMarker {
  pos: number;
  label: ReactNode;
  tone?: MarkerTone;
  /** 'start' anchors the pill's left edge at the marker (the first marker near 0) */
  align?: 'center' | 'start' | 'end';
  title?: string;
}

export interface DecisionStripProps {
  decisions: string;
  height?: number;
  radius?: number;
  hatch?: boolean;
  markers?: readonly StripMarker[];
  playhead?: number | null;
  onSeek?: (pos: number) => void;
  /** second lane: per-frame "object in the gauge" from the labels (true = hatched ink) */
  labels?: readonly (boolean | null | undefined)[] | null;
  labelsHeight?: number;
  /** axis under the strip: true = automatic ticks, or explicit positions */
  ticks?: boolean | readonly number[];
  /** text of a tick / the hover label for a position (default: the position itself) */
  posLabel?: (pos: number) => string;
  /** unit after the first tick ("кадр") */
  tickUnit?: string;
  ariaLabel?: string;
  className?: string;
}

const MARKER_ROW = 30;
const LANE_GAP = 5;
const AXIS_H = 22;

const toneOf = (d: Decision): MarkerTone => (d === 'STOP' ? 'stop' : d === 'GO' ? 'go' : d === 'CAUTION' ? 'caution' : 'fault');
export const markerTone = toneOf;

function niceTicks(n: number, maxTicks = 9): number[] {
  if (n <= 1) return [0];
  const last = n - 1;
  const raw = last / (maxTicks - 1);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw && Number.isInteger(s)) ?? Math.ceil(raw);
  const out: number[] = [];
  for (let p = 0; p <= last; p += step) out.push(p);
  // the end tick, unless it would crowd the previous one
  if (out[out.length - 1] !== last) {
    if (last - out[out.length - 1] < step * 0.45) out.pop();
    out.push(last);
  }
  return out;
}

let hatchTile: HTMLCanvasElement | null = null;
function hatchPattern(ctx: CanvasRenderingContext2D, dpr: number): CanvasPattern | null {
  // vertical stripes (8 px period, 3 px white), rotated 45° by the pattern transform
  if (!hatchTile) {
    hatchTile = document.createElement('canvas');
  }
  const P = Math.max(4, Math.round(8 * dpr));
  hatchTile.width = P;
  hatchTile.height = P;
  const t = hatchTile.getContext('2d');
  if (!t) return null;
  t.clearRect(0, 0, P, P);
  t.fillStyle = 'rgba(255,255,255,0.22)';
  t.fillRect(0, 0, Math.round(3 * dpr), P);
  const pat = ctx.createPattern(hatchTile, 'repeat');
  if (pat && typeof DOMMatrix !== 'undefined') pat.setTransform(new DOMMatrix().rotateSelf(45));
  return pat;
}

function inkHatch(ctx: CanvasRenderingContext2D, dpr: number): CanvasPattern | null {
  const tile = document.createElement('canvas');
  const P = Math.max(4, Math.round(6.5 * dpr));
  tile.width = P;
  tile.height = P;
  const t = tile.getContext('2d');
  if (!t) return null;
  t.fillStyle = '#6B6870';
  t.fillRect(0, 0, P, P);
  t.fillStyle = '#16151A';
  t.fillRect(0, 0, Math.round(4 * dpr), P);
  const pat = ctx.createPattern(tile, 'repeat');
  if (pat && typeof DOMMatrix !== 'undefined') pat.setTransform(new DOMMatrix().rotateSelf(45));
  return pat;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const rr = Math.max(0, Math.min(r, h / 2, w / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

export function DecisionStrip({
  decisions,
  height = 22,
  radius = 7,
  hatch = true,
  markers,
  playhead,
  onSeek,
  labels,
  labelsHeight = 10,
  ticks,
  posLabel,
  tickUnit,
  ariaLabel = 'Решения по кадрам',
  className,
}: DecisionStripProps) {
  const n = decisions.length;
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const dragging = useRef(false);
  const hasLane = !!labels && labels.length > 0;
  const laneH = hasLane ? LANE_GAP + labelsHeight : 0;
  const topPad = markers && markers.length ? MARKER_ROW : 0;
  const fmtPos = posLabel ?? ((p: number) => String(p));

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    setWidth(el.clientWidth);
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width);
      setWidth((prev) => (prev === w ? prev : w));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // draw
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || width <= 0) return;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const H = height + laneH;
    cv.width = Math.round(width * dpr);
    cv.height = Math.round(H * dpr);
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, H);

    // main strip
    ctx.save();
    roundRect(ctx, 0, 0, width, height, radius);
    ctx.clip();
    if (n === 0) {
      ctx.fillStyle = '#EDE9E4';
      ctx.fillRect(0, 0, width, height);
    } else {
      const bins = binDecisions(decisions, Math.max(1, Math.floor(width * dpr)));
      const nb = bins.length;
      const pat = hatch ? hatchPattern(ctx, dpr) : null;
      let i = 0;
      while (i < nb) {
        let j = i + 1;
        while (j < nb && bins[j] === bins[i]) j += 1;
        const x0 = (i / nb) * width;
        const x1 = (j / nb) * width;
        const d = CODE_DECISION[bins[i]];
        ctx.fillStyle = DECISION_COLOR[d];
        // overlap by a hair so neighbours never show a seam
        ctx.fillRect(x0, 0, x1 - x0 + 0.5, height);
        if (d === 'STOP' && pat) {
          ctx.fillStyle = pat;
          ctx.fillRect(x0, 0, x1 - x0 + 0.5, height);
        }
        i = j;
      }
    }
    ctx.restore();

    // labels lane
    if (hasLane && labels) {
      const y = height + LANE_GAP;
      ctx.save();
      roundRect(ctx, 0, y, width, labelsHeight, labelsHeight / 2);
      ctx.clip();
      ctx.fillStyle = '#F5F3F0';
      ctx.fillRect(0, y, width, labelsHeight);
      const m = labels.length;
      const pat = inkHatch(ctx, dpr);
      ctx.fillStyle = pat ?? '#16151A';
      let k = 0;
      while (k < m) {
        if (!labels[k]) {
          k += 1;
          continue;
        }
        let e = k + 1;
        while (e < m && labels[e]) e += 1;
        const x0 = (k / m) * width;
        ctx.fillRect(x0, y, Math.max(1, ((e - k) / m) * width), labelsHeight);
        k = e;
      }
      ctx.restore();
    }
  }, [decisions, n, width, height, radius, hatch, labels, hasLane, laneH, labelsHeight]);

  const posAt = useCallback(
    (clientX: number): number => {
      const el = wrapRef.current;
      if (!el || n === 0) return 0;
      const r = el.getBoundingClientRect();
      const f = (clientX - r.left) / Math.max(1, r.width);
      return Number.isFinite(f) ? Math.min(n - 1, Math.max(0, Math.floor(f * n))) : 0;
    },
    [n],
  );

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (!onSeek || n === 0 || e.button > 0) return;
    dragging.current = true;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    onSeek(posAt(e.clientX));
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const p = posAt(e.clientX);
    setHover(p);
    if (dragging.current && onSeek) onSeek(p);
  };
  const onPointerUp = (e: PointerEvent<HTMLDivElement>) => {
    dragging.current = false;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!onSeek || n === 0) return;
    const cur = playhead ?? 0;
    const big = Math.max(10, Math.round(n / 20));
    const next =
      e.key === 'ArrowRight' || e.key === 'ArrowUp'
        ? cur + 1
        : e.key === 'ArrowLeft' || e.key === 'ArrowDown'
          ? cur - 1
          : e.key === 'PageUp'
            ? cur + big
            : e.key === 'PageDown'
              ? cur - big
              : e.key === 'Home'
                ? 0
                : e.key === 'End'
                  ? n - 1
                  : null;
    if (next === null) return;
    e.preventDefault();
    onSeek(Math.min(n - 1, Math.max(0, next)));
  };

  const pct = (p: number) => `${(((p + 0.5) / Math.max(1, n)) * 100).toFixed(4)}%`;
  const tickList = ticks === true ? niceTicks(n) : Array.isArray(ticks) ? ticks : [];
  const ph = playhead !== null && playhead !== undefined && n > 0 ? Math.min(n - 1, Math.max(0, playhead)) : null;
  const decisionText = (p: number) => {
    const d = decisionAt(decisions, p);
    return d ? DECISION_LABEL[d] : '';
  };

  const interactive = !!onSeek;
  return (
    <div className={[styles.root, className].filter(Boolean).join(' ')} style={{ paddingTop: topPad }}>
      {markers?.map((m, i) => (
        <div
          key={`${m.pos}-${i}`}
          className={[styles.mk, styles[m.tone ?? 'ink'], m.align === 'start' ? styles.start : m.align === 'end' ? styles.end : ''].join(' ')}
          style={{ left: m.align === 'start' ? `${((m.pos / Math.max(1, n)) * 100).toFixed(4)}%` : pct(m.pos) }}
          title={m.title}
        >
          <b>{m.label}</b>
          <i />
        </div>
      ))}
      <div
        ref={wrapRef}
        className={[styles.track, interactive ? styles.interactive : ''].join(' ')}
        style={{ height: height + laneH }}
        role={interactive ? 'slider' : 'img'}
        tabIndex={interactive ? 0 : undefined}
        aria-label={ariaLabel}
        aria-valuemin={interactive ? 0 : undefined}
        aria-valuemax={interactive ? Math.max(0, n - 1) : undefined}
        aria-valuenow={interactive && ph !== null ? ph : undefined}
        aria-valuetext={interactive && ph !== null ? `${fmtPos(ph)} · ${decisionText(ph)}` : undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onPointerLeave={() => setHover(null)}
        onKeyDown={onKeyDown}
      >
        <canvas ref={canvasRef} className={styles.canvas} style={{ width: '100%', height: height + laneH, borderRadius: radius }} />
        {interactive && hover !== null && !dragging.current && (
          <div className={styles.hover} style={{ left: pct(hover), height }}>
            <span className={styles.hoverTip}>
              {fmtPos(hover)} · {decisionText(hover)}
            </span>
          </div>
        )}
        {ph !== null && <div className={styles.playhead} style={{ left: pct(ph), top: -4, height: height + laneH + 8 }} />}
      </div>
      {tickList.length > 0 && (
        <div className={styles.axis} style={{ height: AXIS_H }}>
          {tickList.map((p, i) => {
            const first = i === 0 && p === 0;
            const last = i === tickList.length - 1 && p === n - 1;
            return (
              <span
                key={p}
                className={first ? styles.t0 : last ? styles.tN : undefined}
                style={{ left: first ? '0%' : last ? '100%' : pct(p) }}
              >
                {fmtPos(p)}
                {first && tickUnit ? ` ${tickUnit}` : ''}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** The legend of the four decisions (optionally with counts). */
export function DecisionLegend({ counts, labelsCount, className }: { counts?: Partial<Record<Decision, number>>; labelsCount?: number | null; className?: string }) {
  const order: Decision[] = ['GO', 'CAUTION', 'STOP', 'FAULT'];
  return (
    <div className={[styles.legend, className].filter(Boolean).join(' ')}>
      {order.map((d) => (
        <span key={d}>
          <i className={styles[`lg-${d.toLowerCase()}`]} aria-hidden />
          {DECISION_LABEL[d]}
          {counts && counts[d] !== undefined ? ` ${counts[d]}` : ''}
        </span>
      ))}
      {labelsCount !== undefined && labelsCount !== null && (
        <span>
          <i className={styles['lg-gt']} aria-hidden />
          разметка: в габарите {labelsCount}
        </span>
      )}
    </div>
  );
}
