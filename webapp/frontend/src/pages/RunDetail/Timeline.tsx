// «Решения по кадрам»: the full-width decision strip with event markers, the labels lane and a legend.
// Click or drag scrubs the playhead; releasing (or Enter) opens the player at that frame.
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { RunDetail, RunSeries } from '../../api/types';
import { Card, DecisionLegend, DecisionStrip, markerTone, type StripMarker } from '../../components';
import { fmtNum } from '../../lib/format';
import { playerUrl } from '../Runs/common/analysis';
import styles from './RunDetail.module.css';

/** Markers above the strip: the first STOP, later STOP starts, gaps, CAUTION and FAULT episodes —
 *  thinned so the pills do not overlap (the first STOP always stays). */
export function stripMarkers(r: RunDetail, n: number, posOf: (frame: number) => number): StripMarker[] {
  const fs = r.summary.first_stop;
  const firstPos = fs ? posOf(fs.frame) : -1;
  const cand: StripMarker[] = [];
  for (const ev of r.events) {
    const pos = posOf(ev.first_frame);
    if (pos === firstPos) continue;
    cand.push({ pos, label: String(ev.first_frame), tone: markerTone(ev.decision), title: `кадр ${ev.first_frame}` });
  }
  const minGap = Math.max(1, n * 0.035);
  const kept: StripMarker[] = [];
  const first: StripMarker | null = fs ? { pos: firstPos, label: `кадр ${fs.frame} · СТОП`, tone: 'stop' } : null;
  // the first STOP's pill is wider (≈ 3 gaps)
  const blocked = (p: number) => (first ? p >= first.pos - minGap * 1.6 && p <= first.pos + minGap * 2.8 : false);
  for (const m of cand.sort((a, b) => a.pos - b.pos)) {
    if (blocked(m.pos)) continue;
    const prev = kept[kept.length - 1];
    if (prev && m.pos - prev.pos < minGap) continue;
    kept.push(m);
    if (kept.length >= 14) break;
  }
  const all = (first ? [first, ...kept] : kept).sort((a, b) => a.pos - b.pos);
  return all.map((m) => ({ ...m, align: m.pos < n * 0.05 || m === first ? (m.pos > n * 0.9 ? 'end' : 'start') : m.pos > n * 0.96 ? 'end' : 'center' }));
}

export function Timeline({
  r,
  series,
  labelsInGauge,
  playhead,
  frameOf,
  posOf,
}: {
  r: RunDetail;
  series: RunSeries | undefined;
  labelsInGauge: readonly boolean[] | null;
  playhead: number | null;
  frameOf: (pos: number) => number;
  posOf: (frame: number) => number;
}) {
  const navigate = useNavigate();
  const [scrub, setScrub] = useState<number | null>(null);
  const scrubRef = useRef<number | null>(null);
  // only a press on the strip itself opens the player (not on the axis or a marker pill)
  const pressed = useRef(false);
  const decisions = series?.decisions ?? r.summary.decisions;
  const n = decisions.length;
  const labelsCount = labelsInGauge ? labelsInGauge.filter(Boolean).length : null;
  const seek = (p: number) => {
    scrubRef.current = p;
    setScrub(p);
  };
  const open = () => {
    if (pressed.current && scrubRef.current !== null) navigate(playerUrl(r.id, scrubRef.current));
    pressed.current = false;
  };

  return (
    <Card
      className={styles.tl}
      title="Решения по кадрам"
      help={
        <>
          Верхняя полоса — решение детектора в каждом из <b>{fmtNum(n)}</b> кадров{labelsInGauge ? ', нижняя — ручная разметка: объект в габарите' : ''}. Клик
          или перетаскивание открывает кадр в плеере.
        </>
      }
      helpPlacement="right"
      helpWidth={300}
      headGap={6}
      actions={<DecisionLegend counts={r.summary.counts} labelsCount={labelsCount} className={styles.legend} />}
    >
      <div
        className={styles.stripWrap}
        onPointerDownCapture={(e) => {
          pressed.current = e.button === 0 && !!(e.target as Element).closest('[role="slider"]');
        }}
        onPointerUp={open}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            navigate(playerUrl(r.id, scrubRef.current ?? playhead ?? 0));
          }
        }}
      >
        <DecisionStrip
          decisions={decisions}
          height={44}
          radius={14}
          markers={stripMarkers(r, n, posOf)}
          playhead={scrub ?? playhead}
          onSeek={seek}
          labels={labelsInGauge}
          ticks
          tickUnit="кадр"
          posLabel={(p) => String(frameOf(p))}
          ariaLabel="Решения по кадрам: выберите кадр, чтобы открыть его в плеере"
        />
      </div>
    </Card>
  );
}
