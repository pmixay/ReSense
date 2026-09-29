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

const Lane = memo(function Lane({
  decisions,
  pos,
  markers,
  onSeek,
  posLabel,
}: Pick<ScrubberProps, 'decisions' | 'pos' | 'markers' | 'onSeek' | 'posLabel'>) {
  return (
    <div className={styles.tlane}>
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
      <Lane decisions={p.decisions} pos={p.pos} markers={p.markers} onSeek={p.onSeek} posLabel={p.posLabel} />
      <div className={styles.spd} role="radiogroup" aria-label="Скорость">
        {SPEEDS.map((s) => (
          <button key={s} type="button" role="radio" aria-checked={p.speed === s} className={p.speed === s ? styles.on : ''} onClick={() => p.onSpeed(s)}>
            {speedLabel(s)}
          </button>
        ))}
      </div>
      <IconButton icon="loop" label={p.loop ? 'Повтор включён' : 'Повтор выключен'} variant="well" className={`${styles.sbtn} ${styles.solo}`} active={p.loop} onClick={p.onLoop} tooltip tooltipPlacement="top-end" />
    </div>
  );
}
