// The queue's data for a page: jobs (polled by useJobs), grouped, plus the recordings and runs they
// refer to (source / size of a recording, the scored verdict of a run).
import { useMemo } from 'react';
import { useJobs, useRecordings, useRuns } from '../../api/hooks';
import type { Recording, Run } from '../../api/types';
import { finishedJobs, groupJobs } from './jobs';

export function useQueue() {
  const jobs = useJobs(undefined, { retry: false });
  const recs = useRecordings({ retry: false });
  const runs = useRuns({ retry: false });
  const groups = useMemo(() => groupJobs(jobs.data), [jobs.data]);
  const finished = useMemo(() => finishedJobs(jobs.data), [jobs.data]);
  const recById = useMemo(() => new Map<string, Recording>((recs.data ?? []).map((r) => [r.id, r])), [recs.data]);
  const runById = useMemo(() => new Map<string, Run>((runs.data ?? []).map((r) => [r.id, r])), [runs.data]);
  return { jobs, groups, finished, recById, runById };
}
