// The scrubber at the foot of the console: play / pause, frame steps, previous / next event, the
// frame counter, the decision strip with event pins and a draggable playhead, speeds and loop.
import { memo } from 'react';
import { DecisionStrip, IconButton, type StripMarker } from '../../components';
import { fmtDuration, fmtInt, fmtNumTrim } from '../../lib/format';
import { SPEEDS } from '../../player/clock';
import styles from './Player.module.css';

export interface ScrubberProps {
  decisions: string;
  pos: number;
  n: number;
  /** bag frame index at the playhead and of the last frame */
  frameNo: number;
  lastFrameNo: number;
  t: number | null;
  duration: number | null;
  playing: boolean;
  speed: number;
  loop: boolean;
  markers: readonly StripMarker[];
  hasPrevEvent: boolean;
  hasNextEvent: boolean;
  posLabel: (pos: number) => string;
  onToggle: () => void;
  onStep: (d: number) => void;
  onPrevEvent: () => void;
  onNextEvent: () => void;
  onSeek: (pos: number) => void;
  onSpeed: (s: number) => void;
  onLoop: () => void;
}

const speedLabel = (s: number) => `${fmtNumTrim(s, 2)}×`;

/** ←/→ on the focused strip mean what they mean everywhere in the player (a frame, Shift ten, and
 *  a pause) instead of the slider's plain ±1 seek; Home / End / PageUp / PageDown stay the slider's. */
export function laneStep(e: Pick<KeyboardEvent, 'key' | 'shiftKey' | 'altKey' | 'ctrlKey' | 'metaKey'>): number | null {
  if (e.altKey || e.ctrlKey || e.metaKey) return null;
  if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return null;
  return (e.key === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1);
}

const Lane = memo(function Lane({
  decisions,
  pos,
  markers,
  onSeek,
  onStep,
  posLabel,
}: Pick<ScrubberProps, 'decisions' | 'pos' | 'markers' | 'onSeek' | 'onStep' | 'posLabel'>) {
  return (
    <div
      className={styles.tlane}
      onKeyDownCapture={(e) => {
        const d = laneStep(e);
        if (d === null) return;
        // stops the event before the slider (and the window's player keys): stepped once, here
        e.preventDefault();
        e.stopPropagation();
        onStep(d);
      }}
    >
      <DecisionStrip
        decisions={decisions}
        height={24}
        radius={12}
        markers={markers}
        playhead={pos}
        onSeek={onSeek}
        ticks
        posLabel={posLabel}
        ariaLabel="Кадр прогона"
      />
    </div>
  );
});

export function Scrubber(p: ScrubberProps) {
  return (
    <div className={styles.scrub}>
      <IconButton
        icon={p.playing ? 'pause' : 'play'}
        label={p.playing ? 'Пауза (пробел)' : 'Воспроизвести (пробел)'}
        variant="dark"
        className={styles.pbtn}
        onClick={p.onToggle}
        tooltip
      />
      <span className={styles.sgrp}>
        <IconButton icon="step-back" label="Кадр назад (←)" variant="well" className={styles.sbtn} onClick={() => p.onStep(-1)} disabled={p.pos <= 0} tooltip />
        <IconButton icon="step-forward" label="Кадр вперёд (→)" variant="well" className={styles.sbtn} onClick={() => p.onStep(1)} disabled={p.pos >= p.n - 1} tooltip />
      </span>
      <span className={styles.sgrp}>
        <IconButton icon="event-back" label="Предыдущее событие ([)" variant="well" className={styles.sbtn} onClick={p.onPrevEvent} disabled={!p.hasPrevEvent} tooltip />
        <IconButton icon="event-forward" label="Следующее событие (])" variant="well" className={styles.sbtn} onClick={p.onNextEvent} disabled={!p.hasNextEvent} tooltip />
      </span>
      <div className={styles.fc}>
        <span className={styles.fcA}>
          кадр {fmtInt(p.frameNo)} / {fmtInt(p.lastFrameNo)}
        </span>
        <span className={styles.fcB}>
          {fmtDuration(p.t)} из {fmtDuration(p.duration)}
        </span>
      </div>
      <Lane decisions={p.decisions} pos={p.pos} markers={p.markers} onSeek={p.onSeek} onStep={p.onStep} posLabel={p.posLabel} />
      <div className={styles.spd} role="group" aria-label="Скорость">
        {SPEEDS.map((s) => (
          <button key={s} type="button" aria-pressed={p.speed === s} className={p.speed === s ? styles.on : ''} onClick={() => p.onSpeed(s)}>
            {speedLabel(s)}
          </button>
        ))}
      </div>
      <IconButton icon="loop" label="Повтор по кругу" variant="well" className={`${styles.sbtn} ${styles.solo}`} active={p.loop} onClick={p.onLoop} tooltip tooltipPlacement="top-end" />
    </div>
  );
}
