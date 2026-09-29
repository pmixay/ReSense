import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { installJobWatcher, qk } from './hooks';
import type { Job, SystemInfo } from './types';

const job = (id: string, status: Job['status']) => ({ id, status }) as Job;

describe('installJobWatcher', () => {
  it('refreshes runs and the system when a polled job finishes', () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const stop = installJobWatcher(qc);
    qc.setQueryData(qk.jobs(), [job('a', 'running'), job('b', 'queued')]);
    expect(spy).not.toHaveBeenCalled();
    qc.setQueryData(qk.jobs(), [job('a', 'done'), job('b', 'running')]);
    expect(spy.mock.calls.map((c) => c[0]?.queryKey)).toEqual(expect.arrayContaining([qk.runs, qk.system]));
    stop();
  });

  it('refreshes the runs list when the polled system counts change', () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const stop = installJobWatcher(qc);
    const sys = (runs: number, running: number) => ({ counts: { recordings: 1, runs, jobs_queued: 0, jobs_running: running } }) as SystemInfo;
    qc.setQueryData(qk.system, sys(2, 1));
    qc.setQueryData(qk.system, sys(2, 1));
    expect(spy).not.toHaveBeenCalled();
    qc.setQueryData(qk.system, sys(3, 0));
    const keys = spy.mock.calls.map((c) => c[0]?.queryKey);
    expect(keys).toEqual(expect.arrayContaining([qk.runs, ['jobs']]));
    expect(keys).not.toContainEqual(qk.recordings);
    stop();
  });
});
