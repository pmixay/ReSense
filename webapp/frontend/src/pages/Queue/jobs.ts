// Pure helpers of the job queue (webapp/API.md «Jobs»): grouping, the processing line's current
// station, progress fractions, the per-frame stage timings and durations.
import type { Job, JobStage } from '../../api/types';

/** Stations of a job's processing line (the worker's stages, webapp/API.md JobProgress.stage). */
export const JOB_STAGES = ['открытие', 'детектор', 'оценка', 'сохранение'] as const;

const STAGE_INDEX: Record<JobStage, number> = {
  queued: -1,
  opening: 0,
  processing: 1,
  evaluating: 2,
  finalizing: 3,
  done: JOB_STAGES.length,
};

/** Index of the current station on JOB_STAGES (-1 = not started, JOB_STAGES.length = all done). */
export function jobStageIndex(job: Pick<Job, 'status' | 'progress'>): number {
  if (job.status === 'queued') return -1;
  if (job.status === 'done') return JOB_STAGES.length;
  return STAGE_INDEX[job.progress.stage] ?? -1;
}

/** 0..1 of the frames, 1 once the detector pass is over; null while the total is unknown. */
export function jobFraction(job: Pick<Job, 'status' | 'progress'>): number | null {
  const p = job.progress;
  if (job.status === 'done' || p.stage === 'evaluating' || p.stage === 'finalizing' || p.stage === 'done') return 1;
  if (job.status === 'queued') return 0;
  if (!p.frames_total) return p.frames_done > 0 ? null : 0;
  return Math.min(1, Math.max(0, p.frames_done / p.frames_total));
}

export interface JobGroups {
  running: Job[];
  queued: Job[];
  done: Job[];
  failed: Job[]; // failed and cancelled
}

/** Splits the /jobs list (running first, queued in order, finished newest first) into groups. */
export function groupJobs(jobs: readonly Job[] | undefined): JobGroups {
  const g: JobGroups = { running: [], queued: [], done: [], failed: [] };
  for (const j of jobs ?? []) {
    if (j.status === 'running') g.running.push(j);
    else if (j.status === 'queued') g.queued.push(j);
    else if (j.status === 'done') g.done.push(j);
    else g.failed.push(j);
  }
  g.queued.sort((a, b) => (a.position ?? Infinity) - (b.position ?? Infinity));
  return g;
}

/** The finished part of the list in the backend's order (newest first), done and failed mixed. */
export function finishedJobs(jobs: readonly Job[] | undefined): Job[] {
  return (jobs ?? []).filter((j) => j.status === 'done' || j.status === 'failed' || j.status === 'cancelled');
}

/** Russian names of the detector's timing_ms stages, in pipeline order ("stages" is the sum of the
 *  first six, "total" the whole frame: both are left out of the breakdown). */
export const STAGE_MS_LABEL: Record<string, string> = {
  track: 'модель пути',
  corridor: 'габарит',
  egomotion: 'движение',
  accumulate: 'накопление',
  cluster: 'кластеризация',
  tracking: 'трекинг',
  health: 'самоконтроль',
  result: 'итог',
};

export interface StageMs {
  key: string;
  label: string;
  ms: number;
}

/** stage_ms as the ordered parts of one frame: the known stages that took measurable time. */
export function stageBreakdown(stageMs: Record<string, number> | undefined, minMs = 0.05): StageMs[] {
  if (!stageMs) return [];
  return Object.keys(STAGE_MS_LABEL)
    .filter((k) => typeof stageMs[k] === 'number' && Number.isFinite(stageMs[k]) && stageMs[k] >= minMs)
    .map((k) => ({ key: k, label: STAGE_MS_LABEL[k], ms: stageMs[k] }));
}

export const LIDAR_HZ = 10;

/** How many seconds of recording the job covers per wall second (the LiDAR runs at 10 Hz). */
export function realtimeFactor(fps: number | null | undefined, every = 1): number | null {
  if (typeof fps !== 'number' || !Number.isFinite(fps) || fps <= 0) return null;
  return (fps * Math.max(1, every)) / LIDAR_HZ;
}

const ms = (iso: string | null | undefined): number | null => {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : t;
};

/** Wall seconds from start to finish (or to `now` while running); null before the start. */
export function jobElapsedS(job: Pick<Job, 'started_at' | 'finished_at'>, now: number = Date.now()): number | null {
  const a = ms(job.started_at);
  if (a === null) return null;
  const b = ms(job.finished_at) ?? now;
  return Math.max(0, (b - a) / 1000);
}
