import { describe, expect, it } from 'vitest';
import type { Job, JobProgress } from '../../api/types';
import { JOB_STAGES, groupJobs, jobElapsedS, jobFraction, jobStageIndex, realtimeFactor, stageBreakdown } from './jobs';

const progress = (p: Partial<JobProgress> = {}): JobProgress => ({
  frames_done: 0,
  frames_total: 100,
  fps: null,
  eta_s: null,
  stage: 'queued',
  stage_ms: {},
  decisions: '',
  last: null,
  ...p,
});

const job = (id: string, status: Job['status'], p: Partial<JobProgress> = {}, extra: Partial<Job> = {}): Job =>
  ({ id, status, position: null, progress: progress(p), started_at: null, finished_at: null, ...extra }) as Job;

describe('jobStageIndex', () => {
  it('maps the worker stages onto the processing line', () => {
    expect(jobStageIndex(job('a', 'queued'))).toBe(-1);
    expect(jobStageIndex(job('a', 'running', { stage: 'opening' }))).toBe(0);
    expect(jobStageIndex(job('a', 'running', { stage: 'processing' }))).toBe(1);
    expect(jobStageIndex(job('a', 'running', { stage: 'evaluating' }))).toBe(2);
    expect(jobStageIndex(job('a', 'running', { stage: 'finalizing' }))).toBe(3);
    expect(jobStageIndex(job('a', 'done', { stage: 'processing' }))).toBe(JOB_STAGES.length);
    // a failed job keeps the stage it failed in
    expect(jobStageIndex(job('a', 'failed', { stage: 'processing' }))).toBe(1);
  });
});

describe('jobFraction', () => {
  it('is frames done over the total while processing', () => {
    expect(jobFraction(job('a', 'running', { stage: 'processing', frames_done: 25 }))).toBe(0.25);
    expect(jobFraction(job('a', 'running', { stage: 'processing', frames_done: 250 }))).toBe(1);
  });
  it('is complete once the detector pass is over, zero while queued', () => {
    expect(jobFraction(job('a', 'running', { stage: 'evaluating', frames_done: 3 }))).toBe(1);
    expect(jobFraction(job('a', 'done'))).toBe(1);
    expect(jobFraction(job('a', 'queued'))).toBe(0);
  });
  it('is unknown without a total once frames flow', () => {
    expect(jobFraction(job('a', 'running', { stage: 'processing', frames_total: null, frames_done: 5 }))).toBeNull();
    expect(jobFraction(job('a', 'running', { stage: 'opening', frames_total: null }))).toBe(0);
  });
});

describe('groupJobs', () => {
  it('splits the list and orders the waiting jobs by position', () => {
    const g = groupJobs([
      job('r', 'running'),
      job('q2', 'queued', {}, { position: 2 }),
      job('q1', 'queued', {}, { position: 1 }),
      job('d', 'done'),
      job('f', 'failed'),
      job('c', 'cancelled'),
    ]);
    expect(g.running.map((j) => j.id)).toEqual(['r']);
    expect(g.queued.map((j) => j.id)).toEqual(['q1', 'q2']);
    expect(g.done.map((j) => j.id)).toEqual(['d']);
    expect(g.failed.map((j) => j.id)).toEqual(['f', 'c']);
    expect(groupJobs(undefined).running).toEqual([]);
  });
});

describe('stageBreakdown', () => {
  it('keeps the known detector stages in pipeline order, without the sums and idle stages', () => {
    const parts = stageBreakdown({ total: 43, stages: 40, cluster: 15, track: 16, egomotion: 0, health: 3.5, result: 0.01, custom: 2 });
    expect(parts.map((p) => p.key)).toEqual(['track', 'cluster', 'health']);
    expect(parts[0]).toEqual({ key: 'track', label: 'модель пути', ms: 16 });
    expect(stageBreakdown(undefined)).toEqual([]);
  });
});

describe('realtimeFactor and jobElapsedS', () => {
  it('covers fps × step seconds of a 10 Hz recording per second', () => {
    expect(realtimeFactor(31, 1)).toBeCloseTo(3.1);
    expect(realtimeFactor(10, 2)).toBe(2);
    expect(realtimeFactor(null)).toBeNull();
    expect(realtimeFactor(0)).toBeNull();
  });
  it('measures from start to finish, or to now while running', () => {
    expect(jobElapsedS({ started_at: '2026-09-29T10:00:00Z', finished_at: '2026-09-29T10:00:19.5Z' })).toBe(19.5);
    expect(jobElapsedS({ started_at: '2026-09-29T10:00:00Z', finished_at: null }, Date.parse('2026-09-29T10:01:00Z'))).toBe(60);
    expect(jobElapsedS({ started_at: null, finished_at: null })).toBeNull();
  });
});
