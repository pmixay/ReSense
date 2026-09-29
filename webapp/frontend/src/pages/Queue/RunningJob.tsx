// The job the detector is working on: its processing line, the big percentage, speed / ETA / frames
// and (full variant) the decision string growing frame by frame plus the per-frame stage timings.
import { useCancelJob } from '../../api/hooks';
import type { Job, Recording } from '../../api/types';
import { Chip, DecisionChip, DecisionStrip, ErrorBanner, Help, Icon, PipelineLine, ProgressBar } from '../../components';
import { fmtClock, fmtFps, fmtInt, fmtMeters, fmtMs, fmtNumTrim } from '../../lib/format';
import { SOURCE_ICON, SOURCE_LABEL, recordingMeta } from '../Upload/recording';
import { ConfirmButton } from './ConfirmButton';
import { JOB_STAGES, jobFraction, jobStageIndex, realtimeFactor, stageBreakdown } from './jobs';
import styles from './RunningJob.module.css';

export interface RunningJobProps {
  job: Job;
  recording?: Recording;
  /** full = the Очередь page (strip + stage timings); compact = the Загрузка column */
  variant?: 'full' | 'compact';
}

const STAGE_NOTE: Partial<Record<Job['progress']['stage'], string>> = {
  opening: 'открываем запись',
  evaluating: 'сверяем с разметкой',
  finalizing: 'сохраняем прогон',
};

function StageTimings({ stageMs }: { stageMs: Record<string, number> }) {
  const parts = stageBreakdown(stageMs);
  const sum = parts.reduce((s, p) => s + p.ms, 0);
  if (!parts.length || sum <= 0) return null;
  const total = stageMs.total ?? sum;
  return (
    <div className={styles.timings}>
      <div className={styles.secHead}>
        <span>Время кадра</span>
        <Help placement="top">
          Среднее время этапов детектора на кадр за последние 20 кадров. Бюджет — <b>100 мс</b> (лидар 10 Гц).
        </Help>
        <span className={styles.secVal}>{fmtMs(total)}</span>
      </div>
      <div className={styles.tbar} role="img" aria-label={`Время кадра по этапам: ${parts.map((p) => `${p.label} ${fmtMs(p.ms)}`).join(', ')}`}>
        {parts.map((p, i) => (
          <span key={p.key} className={styles.tseg} style={{ flexGrow: p.ms, ['--k' as string]: i }} />
        ))}
      </div>
      <div className={styles.tlegend}>
        {parts.map((p, i) => (
          <span key={p.key}>
            <i style={{ ['--k' as string]: i }} />
            {p.label} <b>{fmtNumTrim(p.ms, p.ms < 10 ? 1 : 0)}</b>
          </span>
        ))}
      </div>
    </div>
  );
}

export function RunningJob({ job, recording, variant = 'full' }: RunningJobProps) {
  const cancel = useCancelJob();
  const p = job.progress;
  const frac = jobFraction(job);
  const stage = jobStageIndex(job);
  const pct = frac === null ? null : Math.floor(frac * 100);
  const rt = realtimeFactor(p.fps, job.options.every);
  const full = variant === 'full';
  const note = STAGE_NOTE[p.stage];
  const stripWidth = p.frames_total ? Math.max(0.02, Math.min(1, p.frames_done / p.frames_total)) : 1;
  const last = p.last;

  return (
    <div className={[styles.job, full ? styles.full : styles.compact].join(' ')}>
      <div className={styles.head}>
        <div className={styles.title}>
          <div className={styles.nm} title={job.recording_name}>
            {job.recording_name}
          </div>
          <div className={styles.mt}>
            {recording && <Icon name={SOURCE_ICON[recording.source]} size={15} />}
            {recording && <b>{SOURCE_LABEL[recording.source]}</b>}
            {recording && recordingMeta(recording) && <span>· {recordingMeta(recording)}</span>}
            {!recording && <span>{job.preset_name}</span>}
          </div>
        </div>
        {full && (
          <Chip variant="white" icon="sliders" title="Пресет">
            {job.preset_name}
          </Chip>
        )}
        <ConfirmButton
          icon="x"
          label="Отменить обработку"
          confirm="Отменить?"
          variant="white"
          size={full ? 'md' : 'sm'}
          loading={cancel.isPending}
          onConfirm={() => cancel.mutate(job.id)}
        />
      </div>

      <PipelineLine stages={JOB_STAGES} current={stage} active compact={!full} className={styles.pl} />

      <div className={styles.prog}>
        <div className={styles.pc}>
          {pct === null ? '—' : pct}
          <small> %</small>
        </div>
        <div className={styles.barWrap}>
          {note && <div className={styles.note}>{note}</div>}
          <ProgressBar value={p.stage === 'opening' ? null : frac} height={14} track="white" label="Прогресс обработки" />
        </div>
      </div>

      <div className={styles.stats}>
        <div className={styles.js}>
          <div className={styles.v}>{fmtFps(p.fps)}</div>
          <div className={styles.l}>{rt !== null ? `×${fmtNumTrim(rt, rt < 10 ? 1 : 0)} реального времени` : 'скорость'}</div>
        </div>
        <div className={styles.js}>
          <div className={styles.v}>{p.eta_s !== null && p.stage === 'processing' ? fmtClock(p.eta_s) : '—'}</div>
          <div className={styles.l}>осталось</div>
        </div>
        <div className={styles.js}>
          <div className={styles.v}>{fmtInt(p.frames_done)}</div>
          <div className={styles.l}>{p.frames_total !== null ? `кадр из ${fmtInt(p.frames_total)}` : 'кадров'}</div>
        </div>
      </div>

      {full && (
        <div className={styles.decisions}>
          <div className={styles.secHead}>
            <span>Решения по кадрам</span>
            <Help placement="top">Решение детектора в каждом обработанном кадре; полоса растёт по мере обработки.</Help>
            <span className={styles.sp} />
            {last && (
              <span className={styles.last}>
                кадр {fmtInt(last.frame)}
                <DecisionChip
                  decision={last.decision}
                  extra={last.decision === 'STOP' && last.nearest_distance !== null ? fmtMeters(last.nearest_distance) : undefined}
                  pulse={last.decision === 'STOP'}
                />
              </span>
            )}
          </div>
          <div className={styles.stripTrack}>
            {p.decisions.length > 0 && (
              <div className={styles.stripGrow} style={{ width: `${stripWidth * 100}%` }}>
                <DecisionStrip decisions={p.decisions} height={30} radius={9} ariaLabel="Решения по обработанным кадрам" />
              </div>
            )}
          </div>
        </div>
      )}

      {full && <StageTimings stageMs={p.stage_ms} />}
      {cancel.isError && <ErrorBanner error={cancel.error} compact className={styles.err} />}
    </div>
  );
}
