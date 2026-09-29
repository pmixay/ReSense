// The HUD in the glass: camera / cloud chips, distance labels over the detection boxes, white
// brackets around the nearest obstacle, distance ticks on the bed, the envelope tag and the frame
// of the «крупно» inset. React renders the content at the snapshot rate; the positions are written
// straight into the DOM after every 3D render (the scene's overlay), so labels stick to the boxes
// at 60 fps without re-rendering React.
import { useCallback, useLayoutEffect, useRef } from 'react';
import type { DetectionDict, FrameResultDict } from '../../api/types';
import { Icon, IconButton, Spinner } from '../../components';
import { POINTS, fmtCount, fmtMeters, fmtNum, fmtNumTrim, plural } from '../../lib/format';
import { CAMERA_HUD, envelopeText } from './cab';
import { RULER_MARKS, type SceneOverlay } from '../../player/scene';
import { TICK_LABELS, type CamMode } from '../../player/geometry';
import type { Motion } from '../../player/motion';
import styles from './Player.module.css';

export type OverlaySink = (ov: SceneOverlay) => void;

/** Up to this many detection labels (the nearest carries the size line). */
const MAX_DET_LABELS = 3;
const MAX_WARN_LABELS = 2;
/** The inset's place in the glass (stage px, as in the mockup). */
export const PIP_RECT = { x: 1296, y: 136, w: 204, h: 204, radius: 26 };

/** Put a label at a screen point of the 3D view (hidden when the point is off screen). The
 *  individual `translate` property moves it without a layout pass. */
function place(el: HTMLElement | null | undefined, p: { visible: boolean; x: number; y: number } | undefined, dx = 0): void {
  if (!el) return;
  if (!p || !p.visible) {
    if (el.style.visibility !== 'hidden') el.style.visibility = 'hidden';
    return;
  }
  if (el.style.visibility !== 'visible') el.style.visibility = 'visible';
  el.style.translate = `${(p.x + dx).toFixed(1)}px ${p.y.toFixed(1)}px`;
}

function nearestWarnings(w: readonly DetectionDict[], k: number): number[] {
  return w
    .map((d, i) => ({ d: d.distance, i }))
    .sort((a, b) => a.d - b.d)
    .slice(0, k)
    .map((x) => x.i);
}

export interface HudProps {
  frame: FrameResultDict | null;
  mode: CamMode;
  free: boolean;
  onResetView: () => void;
  hasClouds: boolean;
  cloudLoading: boolean;
  /** the backend's message when the cloud under the playhead failed (retried automatically) */
  cloudError: string | null;
  buffering: boolean;
  /** the frames could not be loaded (the glass shows the error banner) */
  framesFailed: boolean;
  /** retry a failed cloud list (null when nothing to retry) */
  onRetryCloud: (() => void) | null;
  motion: Motion;
  /** registers the per-render position writer */
  register: (sink: OverlaySink | null) => void;
}

export function Hud({ frame, mode, free, onResetView, hasClouds, cloudLoading, cloudError, buffering, framesFailed, onRetryCloud, motion, register }: HudProps) {
  const detRefs = useRef<(HTMLDivElement | null)[]>([]);
  const warnRefs = useRef<(HTMLDivElement | null)[]>([]);
  const tickRefs = useRef<(HTMLDivElement | null)[]>([]);
  const envRef = useRef<HTMLDivElement>(null);
  const brkRef = useRef<SVGPathElement>(null);
  const pipRef = useRef<HTMLDivElement>(null);
  const rulerRef = useRef<SVGGElement>(null);

  const dets = frame?.detections ?? [];
  const warns = frame?.warnings ?? [];
  const warnIdx = dets.length ? [] : nearestWarnings(warns, MAX_WARN_LABELS);
  const subject: DetectionDict | null = dets[0] ?? (warnIdx.length ? warns[warnIdx[0]] : null);
  const warnIdxKey = warnIdx.join(',');

  const rulerMarks = useRef<SVGGElement[]>([]);
  const apply = useCallback<OverlaySink>(
    (ov) => {
      const dr = detRefs.current;
      for (let i = 0; i < dr.length; i += 1) place(dr[i], ov.detections[i]);
      const wr = warnRefs.current;
      for (let i = 0; i < wr.length; i += 1) {
        const el = wr[i];
        if (el) place(el, ov.warnings[Number(el.dataset.index)]);
      }
      const tr = tickRefs.current;
      for (let i = 0; i < tr.length; i += 1) place(tr[i], ov.ticks[i]);
      place(envRef.current, ov.envTag, 16);
      const b = ov.bracket;
      const path = brkRef.current;
      if (path) {
        if (b.visible) {
          const m = 8;
          const k = Math.min(11, Math.max(5, (b.x1 - b.x0) / 3));
          const x0 = b.x0 - m;
          const y0 = b.y0 - m;
          const x1 = b.x1 + m;
          const y1 = b.y1 + m;
          path.setAttribute(
            'd',
            `M${x0} ${y0 + k}V${y0}H${x0 + k} M${x1 - k} ${y0}H${x1}V${y0 + k} M${x1} ${y1 - k}V${y1}H${x1 - k} M${x0 + k} ${y1}H${x0}V${y1 - k}`,
          );
          path.style.visibility = 'visible';
        } else path.style.visibility = 'hidden';
      }
      if (pipRef.current) pipRef.current.style.visibility = ov.pip.visible ? 'visible' : 'hidden';
      const g = rulerRef.current;
      if (g && ov.pip.visible) {
        const ys = ov.pip.ys;
        const line = g.firstElementChild as SVGLineElement | null;
        if (line) {
          line.setAttribute('y1', ys[0].toFixed(1));
          line.setAttribute('y2', ys[ys.length - 1].toFixed(1));
        }
        const marks = rulerMarks.current;
        for (let i = 0; i < marks.length; i += 1) marks[i]?.setAttribute('transform', `translate(0 ${ys[i].toFixed(1)})`);
      }
    },
    // positions only touch the refs; the warning labels carry their index in data-index
    [],
  );

  useLayoutEffect(() => {
    register(apply);
    return () => register(null);
  }, [register, apply]);

  // new labels start hidden until the next render places them
  useLayoutEffect(() => {
    for (const el of [...detRefs.current, ...warnRefs.current]) if (el) el.style.visibility = 'hidden';
  }, [dets.length, warnIdxKey]);

  const nPoints = frame?.n_points;
  const framesLoading = buffering || (!frame && !framesFailed);
  // the speed the job or the detector reported; the glide's fallback (objects' shift) is not shown as one
  const speedShown = motion.v > 0.05 && (motion.source === 'given' || motion.source === 'estimated');
  return (
    <div className={styles.hud}>
      <div className={styles.hudc}>
        <div className={styles.g}>
          <Icon name="camera" size={16} />
          {free ? 'свободная камера' : CAMERA_HUD[mode]}
          {free && (
            <IconButton icon="retry" label="Вернуть камеру (двойной клик)" size="xs" variant="glass" onClick={onResetView} className={styles.gBtn} tooltip tooltipPlacement="right" />
          )}
        </div>
        {hasClouds ? (
          nPoints !== undefined && (
            <div className={styles.g}>
              облако <b>{fmtNum(nPoints, 0)}</b> {plural(nPoints, POINTS)}
            </div>
          )
        ) : (
          <div className={styles.g}>
            <Icon name="cube" size={16} />
            без облака точек
          </div>
        )}
        {speedShown && (
          <div className={styles.g}>
            скорость <b>{fmtNumTrim(motion.v, 1)}</b> м/с
          </div>
        )}
        {framesLoading || (!cloudError && cloudLoading) ? (
          <div className={styles.g}>
            <Spinner size={14} tone="light" label={framesLoading ? 'Загрузка кадров' : 'Загрузка облака'} />
            {framesLoading ? 'загрузка кадров' : 'загрузка облака'}
          </div>
        ) : cloudError ? (
          <div className={`${styles.g} ${styles.gErr}`} role="status">
            <Icon name="fault-circle" size={16} />
            {cloudError}
            {onRetryCloud && (
              <IconButton icon="retry" label="Загрузить облако снова" size="xs" variant="glass" onClick={onRetryCloud} className={styles.gBtn} tooltip tooltipPlacement="right" />
            )}
          </div>
        ) : null}
      </div>

      <svg className={styles.brk} width="1600" height="700" aria-hidden>
        <path ref={brkRef} fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" style={{ visibility: 'hidden' }} />
      </svg>

      {TICK_LABELS.map((m, i) => (
        <div
          key={m}
          ref={(el) => {
            tickRefs.current[i] = el;
          }}
          className={`${styles.tick} ${styles.follow} ${m === 50 ? styles.k50 : ''}`}
          style={{ visibility: 'hidden' }}
        >
          {m} м
        </div>
      ))}
      <div ref={envRef} className={`${styles.envtag} ${styles.follow}`} style={{ visibility: 'hidden' }}>
        <i />
        габарит {envelopeText()}
      </div>

      {dets.slice(0, MAX_DET_LABELS).map((d, i) => (
        <div
          key={`d${i}`}
          ref={(el) => {
            detRefs.current[i] = el;
          }}
          className={`${styles.olabel} ${styles.follow}`}
        >
          <div className={styles.op}>
            <Icon name="stop-octagon" size={20} strokeWidth={2.6} />
            <span className={styles.od}>{fmtMeters(d.distance)}</span>
          </div>
          {i === 0 && (
            <div className={styles.os}>
              препятствие · {fmtNum(d.size[1], 2)} × {fmtNum(d.size[2], 2)} м
            </div>
          )}
        </div>
      ))}
      {warnIdx.map((wi, k) => (
        <div
          key={`w${wi}`}
          ref={(el) => {
            warnRefs.current[k] = el;
          }}
          data-index={wi}
          className={`${styles.olabel} ${styles.follow} ${styles.warnLabel}`}
        >
          <div className={styles.op}>
            <Icon name="warning" size={18} strokeWidth={2.6} />
            <span className={styles.od}>{fmtMeters(warns[wi].distance)}</span>
          </div>
        </div>
      ))}

      <div ref={pipRef} className={`${styles.zoom} ${dets.length ? '' : styles.zoomWarn}`} style={{ visibility: 'hidden' }} aria-label="Крупно">
        <svg className={styles.rul} width={PIP_RECT.w} height={PIP_RECT.h} aria-hidden>
          <g ref={rulerRef}>
            <line x1="22" x2="22" y1="0" y2="0" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
            {RULER_MARKS.map((h, i) => {
              const big = Math.abs(h % 1) < 0.01;
              return (
                <g
                  key={h}
                  ref={(el) => {
                    if (el) rulerMarks.current[i] = el;
                  }}
                >
                  <line x1="22" x2={big ? 32 : 28} y1="0" y2="0" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
                  {big && (
                    <text x="36" y="4.2" fontFamily="Montserrat" fontWeight="800" fontSize="12" fill="#fff">
                      {h === 2 ? '2 м' : h}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
        <div className={styles.zt}>
          <span>крупно</span>
          {subject && (
            <span>
              {fmtCount(subject.n_points, POINTS)} · {fmtNum(subject.size[2], 2)} м
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
