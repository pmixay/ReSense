// Rows of the queue: a waiting job (its place, cancel), a finished one (decision strip, verdict,
// open / player) and a failed or cancelled one (the error, log, retry).
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCancelJob, useRetryJob } from '../../api/hooks';
import type { Job, Recording, Run } from '../../api/types';
import { Chip, DecisionChip, DecisionStrip, ErrorBanner, Icon, IconButton } from '../../components';
import { fmtDuration, fmtFrames } from '../../lib/format';
import { VerdictChip } from '../Overview/Verdict';
import { decisionsVerdict, runVerdict } from '../Overview/verdict';
import { SOURCE_ICON, SOURCE_LABEL, recordingMeta } from '../Upload/recording';
import { ConfirmButton } from './ConfirmButton';
import { jobElapsedS } from './jobs';
import styles from './JobRows.module.css';

interface RowProps {
  job: Job;
  recording?: Recording;
  compact?: boolean;
}

function Meta({ job, recording, children }: { job: Job; recording?: Recording; children?: ReactNode }) {
  return (
    <div className={styles.mt}>
      <Icon name={recording ? SOURCE_ICON[recording.source] : 'file'} size={15} />
      {recording && <b className={styles.src}>{SOURCE_LABEL[recording.source]} ·</b>}
      {children ?? <span>{job.preset_name}</span>}
    </div>
  );
}

export function QueuedRow({ job, recording, compact }: RowProps) {
  const cancel = useCancelJob();
  const frames = job.progress.frames_total;
  return (
    <div className={[styles.row, compact ? styles.compact : ''].join(' ')}>
      <span className={styles.qn} aria-label={`Место в очереди: ${job.position ?? '—'}`}>
        {job.position ?? '—'}
      </span>
      <div className={styles.w}>
        <div className={styles.nm} title={job.recording_name}>
          {job.recording_name}
        </div>
        <Meta job={job} recording={recording}>
          <span>
            {job.preset_name}
            {frames !== null ? ` · ${fmtFrames(frames)}` : ''}
            {recording && recording.duration_s !== null ? ` · ${fmtDuration(recording.duration_s)}` : ''}
          </span>
        </Meta>
      </div>
      <ConfirmButton icon="trash" label="Убрать из очереди" confirm="Убрать?" loading={cancel.isPending} onConfirm={() => cancel.mutate(job.id)} />
    </div>
  );
}

export function FinishedRow({ job, recording, run, compact }: RowProps & { run?: Run }) {
  const navigate = useNavigate();
  const took = jobElapsedS(job);
  const decisions = run?.summary.decisions ?? job.progress.decisions;
  const verdict = run ? runVerdict(run.summary) : decisionsVerdict(job.progress.decisions);
  const frames = run?.summary.n_frames ?? job.progress.frames_done;
  const open = job.run_id ? `/runs/${job.run_id}` : undefined;
  return (
    <div
      className={[styles.row, styles.link, compact ? styles.compact : ''].join(' ')}
      onClick={(e) => {
        if (open && !(e.target as HTMLElement).closest('a,button')) navigate(open);
      }}
    >
      <span className={styles.qd} aria-hidden>
        <Icon name="check" size={16} strokeWidth={3} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm} title={run?.name ?? job.recording_name}>
          {run?.name ?? job.recording_name}
        </div>
        <Meta job={job} recording={recording}>
          <span>
            {fmtFrames(frames)}
            {took !== null ? ` · за ${fmtDuration(took)}` : ''}
          </span>
        </Meta>
      </div>
      <div className={styles.strip}>
        <DecisionStrip decisions={decisions} height={18} radius={6} />
      </div>
      <VerdictChip verdict={verdict} className={styles.verdict} />
      {!compact && job.run_id && (
        <IconButton icon="cube" label="Открыть в плеере" tooltip variant="outline" size="sm" to={`/player/${job.run_id}`} />
      )}
      {open && <IconButton icon="arrow-right" label={`Открыть прогон ${job.recording_name}`} tooltip variant="dark" size="sm" to={open} />}
    </div>
  );
}

export function FailedRow({ job, recording, compact, onLog }: RowProps & { onLog?: (job: Job) => void }) {
  const retry = useRetryJob();
  const failed = job.status === 'failed';
  return (
    <div className={[styles.row, failed ? styles.err : styles.cancelled, compact ? styles.compact : ''].join(' ')}>
      <span className={[styles.qd, failed ? styles.fault : styles.off].join(' ')} aria-hidden>
        <Icon name={failed ? 'fault-circle' : 'x'} size={16} strokeWidth={2.6} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm} title={job.recording_name}>
          {job.recording_name}
        </div>
        <div className={styles.mt} title={job.error ?? undefined}>
          <Icon name={recording ? SOURCE_ICON[recording.source] : 'file'} size={15} />
          {failed ? (
            <span className={styles.ell}>
              <b>ошибка:</b> {job.error ?? 'неизвестная ошибка'}
            </span>
          ) : (
            <span className={styles.ell}>
              <b>отменено</b>
              {recording ? ` · ${recordingMeta(recording, false)}` : ''}
            </span>
          )}
        </div>
        {retry.isError && <ErrorBanner error={retry.error} compact className={styles.rowErr} />}
      </div>
      {!compact &&
        (failed ? (
          <DecisionChip decision="FAULT" size="sm" />
        ) : (
          <Chip variant="well" size="sm">
            отменено
          </Chip>
        ))}
      {onLog && <IconButton icon="list" label="Журнал обработки" tooltip variant="outline" size="sm" onClick={() => onLog(job)} />}
      <IconButton
        icon="retry"
        label="Повторить"
        tooltip
        variant={failed ? 'fault' : 'dark'}
        size="sm"
        loading={retry.isPending}
        onClick={() => retry.mutate(job.id)}
      />
    </div>
  );
}
