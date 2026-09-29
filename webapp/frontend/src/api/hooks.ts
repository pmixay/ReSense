// react-query hooks for every endpoint of webapp/API.md. Queries poll where the data moves (jobs
// every second while one is queued or running, the system every 5 s); mutations invalidate what
// they change. Results of a run (series, frames, clouds) never change: cached without refetching.
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api, apiUrl } from './client';
import { decodeRSC1, type DecodedCloud } from './cloud';
import type {
  CloudsIndex,
  DemoCreate,
  FramesPage,
  HealthOk,
  Job,
  JobCreate,
  LabelsFile,
  ParamSpec,
  Preset,
  PresetCreate,
  PresetPatch,
  Recording,
  Run,
  RunDetail,
  RunLabels,
  RunSeries,
  ServerListing,
  SystemInfo,
  UploadCreated,
} from './types';
import { UploadAbortedError, uploadRecording, type UploadItem, type UploadProgress } from './upload';

const enc = encodeURIComponent;

// ---------------------------------------------------------------- keys

export const qk = {
  system: ['system'] as const,
  health: ['health'] as const,
  serverFiles: (path: string) => ['server-files', path] as const,
  recordings: ['recordings'] as const,
  recording: (id: string) => ['recording', id] as const,
  jobs: (status?: string) => ['jobs', status ?? 'all'] as const,
  job: (id: string) => ['job', id] as const,
  jobLog: (id: string) => ['job-log', id] as const,
  runs: ['runs'] as const,
  run: (id: string) => ['run', id] as const,
  runSeries: (id: string) => ['run-series', id] as const,
  runLabels: (id: string) => ['run-labels', id] as const,
  runFrames: (id: string, from: number, count: number) => ['run-frames', id, from, count] as const,
  runClouds: (id: string) => ['run-clouds', id] as const,
  runCloud: (id: string, pos: number) => ['run-cloud', id, pos] as const,
  presets: ['presets'] as const,
  presetSchema: ['preset-schema'] as const,
};

/** Direct download links (use as <a href download>). */
export const downloads = {
  recording: (id: string) => apiUrl(`/recordings/${enc(id)}/download`),
  results: (runId: string) => apiUrl(`/runs/${enc(runId)}/download/results.jsonl`),
  report: (runId: string) => apiUrl(`/runs/${enc(runId)}/download/report.json`),
  csv: (runId: string) => apiUrl(`/runs/${enc(runId)}/download/frames.csv`),
};

type QueryOpts<T> = Omit<UseQueryOptions<T, ApiError>, 'queryKey' | 'queryFn'>;

const ACTIVE: ReadonlySet<Job['status']> = new Set(['queued', 'running']);
export const isJobActive = (j: Pick<Job, 'status'>): boolean => ACTIVE.has(j.status);

// ---------------------------------------------------------------- system

export const SYSTEM_POLL_MS = 5000;
export const JOBS_POLL_MS = 1000;
const JOBS_IDLE_POLL_MS = 10000;

export function useSystem(opts?: QueryOpts<SystemInfo>) {
  return useQuery<SystemInfo, ApiError>({
    queryKey: qk.system,
    queryFn: ({ signal }) => api.get<SystemInfo>('/system', { signal }),
    refetchInterval: SYSTEM_POLL_MS,
    retry: false,
    ...opts,
  });
}

export function useHealth(opts?: QueryOpts<HealthOk>) {
  return useQuery<HealthOk, ApiError>({
    queryKey: qk.health,
    queryFn: ({ signal }) => api.get<HealthOk>('/health', { signal }),
    retry: false,
    ...opts,
  });
}

/** 'online' | 'offline' | 'connecting' from the system poll (the top bar pill). */
export function useBackendStatus(): { status: 'online' | 'offline' | 'connecting'; system: SystemInfo | undefined } {
  const q = useSystem();
  const status = q.isError ? 'offline' : q.isSuccess ? 'online' : 'connecting';
  return { status, system: q.isError ? undefined : q.data };
}

// ---------------------------------------------------------------- recordings

export function useServerFiles(path: string, opts?: QueryOpts<ServerListing>) {
  return useQuery<ServerListing, ApiError>({
    queryKey: qk.serverFiles(path),
    queryFn: ({ signal }) => api.get<ServerListing>('/server-files', { query: { path }, signal }),
    placeholderData: keepPreviousData,
    ...opts,
  });
}

export function useRecordings(opts?: QueryOpts<Recording[]>) {
  return useQuery<Recording[], ApiError>({
    queryKey: qk.recordings,
    queryFn: ({ signal }) => api.get<Recording[]>('/recordings', { signal }),
    ...opts,
  });
}

export function useRecording(id: string | null | undefined, opts?: QueryOpts<Recording>) {
  return useQuery<Recording, ApiError>({
    queryKey: qk.recording(id ?? ''),
    queryFn: ({ signal }) => api.get<Recording>(`/recordings/${enc(id ?? '')}`, { signal }),
    enabled: !!id,
    ...opts,
  });
}

function onRecordingChanged(qc: QueryClient, rec?: Recording) {
  if (rec) qc.setQueryData(qk.recording(rec.id), rec);
  void qc.invalidateQueries({ queryKey: qk.recordings });
  void qc.invalidateQueries({ queryKey: qk.system });
}

export function useCreateUpload() {
  return useMutation<UploadCreated, ApiError, { name?: string } | void>({
    mutationFn: (body) => api.post<UploadCreated>('/uploads', body ?? {}),
  });
}

export function useFinalizeUpload() {
  const qc = useQueryClient();
  return useMutation<Recording, ApiError, string>({
    mutationFn: (uploadId) => api.post<Recording>(`/uploads/${enc(uploadId)}/finalize`),
    onSuccess: (rec) => onRecordingChanged(qc, rec),
  });
}

export function useAbortUpload() {
  return useMutation<void, ApiError, string>({
    mutationFn: (uploadId) => api.del(`/uploads/${enc(uploadId)}`),
  });
}

export function useRegisterServerRecording() {
  const qc = useQueryClient();
  return useMutation<Recording, ApiError, { path: string }>({
    mutationFn: (body) => api.post<Recording>('/recordings/from-server', body),
    onSuccess: (rec) => onRecordingChanged(qc, rec),
  });
}

export function useCreateDemo() {
  const qc = useQueryClient();
  return useMutation<Recording, ApiError, DemoCreate>({
    mutationFn: (body) => api.post<Recording>('/recordings/demo', body),
    onSuccess: (rec) => onRecordingChanged(qc, rec),
  });
}

export function useDeleteRecording() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => api.del(`/recordings/${enc(id)}`),
    onSuccess: (_v, id) => {
      qc.removeQueries({ queryKey: qk.recording(id) });
      onRecordingChanged(qc);
      void qc.invalidateQueries({ queryKey: qk.runs }); // their recording_id becomes null
    },
  });
}

/** PUT labels: a parsed labels object or the .json File as picked by the user. */
export function useUploadLabels() {
  const qc = useQueryClient();
  return useMutation<Recording, ApiError, { id: string; labels: LabelsFile | File }>({
    mutationFn: ({ id, labels }) =>
      api.put<Recording>(`/recordings/${enc(id)}/labels`, labels, {
        headers: labels instanceof File ? { 'Content-Type': 'application/json' } : undefined,
      }),
    onSuccess: (rec) => onRecordingChanged(qc, rec),
  });
}

export function useDeleteLabels() {
  const qc = useQueryClient();
  return useMutation<Recording, ApiError, string>({
    mutationFn: (id) => api.del<Recording>(`/recordings/${enc(id)}/labels`),
    onSuccess: (rec) => onRecordingChanged(qc, rec),
  });
}

// ---------------------------------------------------------------- upload with progress

export interface UploadState {
  status: 'idle' | 'uploading' | 'done' | 'error' | 'aborted';
  progress: UploadProgress | null;
  recording: Recording | null;
  error: string | null;
}

const UPLOAD_IDLE: UploadState = { status: 'idle', progress: null, recording: null, error: null };

/** One upload at a time with live progress; abortable; the recordings list refreshes on success. */
export function useUpload() {
  const qc = useQueryClient();
  const [state, setState] = useState<UploadState>(UPLOAD_IDLE);
  const handle = useRef<{ abort(): void } | null>(null);

  useEffect(() => () => handle.current?.abort(), []);

  const start = useCallback(
    async (files: Iterable<File | UploadItem> | ArrayLike<File>, name?: string): Promise<Recording | null> => {
      handle.current?.abort();
      setState({ ...UPLOAD_IDLE, status: 'uploading' });
      const h = uploadRecording(files, {
        name,
        onProgress: (progress) => setState((s) => (s.status === 'uploading' ? { ...s, progress } : s)),
      });
      handle.current = h;
      try {
        const rec = await h.promise;
        if (handle.current === h) {
          setState((s) => ({ ...s, status: 'done', recording: rec }));
          onRecordingChanged(qc, rec);
        }
        return rec;
      } catch (err) {
        if (handle.current === h) {
          const aborted = err instanceof UploadAbortedError;
          setState((s) => ({ ...s, status: aborted ? 'aborted' : 'error', error: err instanceof Error ? err.message : String(err) }));
        }
        return null;
      }
    },
    [qc],
  );

  const abort = useCallback(() => handle.current?.abort(), []);
  const reset = useCallback(() => {
    handle.current = null;
    setState(UPLOAD_IDLE);
  }, []);

  return { ...state, start, abort, reset };
}

// ---------------------------------------------------------------- jobs

export function useJobs(status?: string, opts?: QueryOpts<Job[]>) {
  return useQuery<Job[], ApiError>({
    queryKey: qk.jobs(status),
    queryFn: ({ signal }) => api.get<Job[]>('/jobs', { query: { status }, signal }),
    refetchInterval: (q) => (q.state.data?.some(isJobActive) ? JOBS_POLL_MS : JOBS_IDLE_POLL_MS),
    ...opts,
  });
}

export function useJob(id: string | null | undefined, opts?: QueryOpts<Job>) {
  return useQuery<Job, ApiError>({
    queryKey: qk.job(id ?? ''),
    queryFn: ({ signal }) => api.get<Job>(`/jobs/${enc(id ?? '')}`, { signal }),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data && isJobActive(q.state.data) ? JOBS_POLL_MS : false),
    ...opts,
  });
}

export function useJobLog(id: string | null | undefined, opts?: QueryOpts<string>) {
  return useQuery<string, ApiError>({
    queryKey: qk.jobLog(id ?? ''),
    queryFn: ({ signal }) => api.text(`/jobs/${enc(id ?? '')}/log`, { signal }),
    enabled: !!id,
    ...opts,
  });
}

function onJobsChanged(qc: QueryClient, job?: Job) {
  if (job) qc.setQueryData(qk.job(job.id), job);
  void qc.invalidateQueries({ queryKey: ['jobs'] });
  void qc.invalidateQueries({ queryKey: qk.system });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation<Job, ApiError, JobCreate>({
    mutationFn: (body) => api.post<Job>('/jobs', body),
    onSuccess: (job) => onJobsChanged(qc, job),
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation<Job, ApiError, string>({
    mutationFn: (id) => api.post<Job>(`/jobs/${enc(id)}/cancel`),
    onSuccess: (job) => onJobsChanged(qc, job),
  });
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation<Job, ApiError, string>({
    mutationFn: (id) => api.post<Job>(`/jobs/${enc(id)}/retry`),
    onSuccess: (job) => onJobsChanged(qc, job),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => api.del(`/jobs/${enc(id)}`),
    onSuccess: (_v, id) => {
      qc.removeQueries({ queryKey: qk.job(id) });
      onJobsChanged(qc);
    },
  });
}

export function useClearFinishedJobs() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, void>({
    mutationFn: () => api.del('/jobs', { query: { finished: true } }),
    onSuccess: () => onJobsChanged(qc),
  });
}

/** Keeps lists fresh without every page polling everything (installed once in main.tsx): when a
 *  polled job leaves queued/running, or the always-polled system counts change, the affected lists
 *  are invalidated. */
export function installJobWatcher(qc: QueryClient): () => void {
  const seen = new Map<string, Job['status']>();
  let counts: SystemInfo['counts'] | null = null;
  return qc.getQueryCache().subscribe((event) => {
    if (event.type !== 'updated' || event.action.type !== 'success') return;
    const root = event.query.queryKey[0];
    if (root === 'system') {
      const next = (event.query.state.data as SystemInfo | undefined)?.counts;
      if (!next) return;
      const prev = counts;
      counts = next;
      if (!prev) return;
      if (prev.runs !== next.runs) void qc.invalidateQueries({ queryKey: qk.runs });
      if (prev.recordings !== next.recordings) void qc.invalidateQueries({ queryKey: qk.recordings });
      if (prev.jobs_running !== next.jobs_running || prev.jobs_queued !== next.jobs_queued) {
        void qc.invalidateQueries({ queryKey: ['jobs'] });
      }
      return;
    }
    if (root !== 'jobs' && root !== 'job') return;
    const data = event.query.state.data as Job[] | Job | undefined;
    const jobs = Array.isArray(data) ? data : data ? [data] : [];
    let finished = false;
    for (const j of jobs) {
      const prev = seen.get(j.id);
      if (prev && ACTIVE.has(prev) && !isJobActive(j)) finished = true;
      seen.set(j.id, j.status);
    }
    if (finished) {
      void qc.invalidateQueries({ queryKey: qk.runs });
      void qc.invalidateQueries({ queryKey: qk.system });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

// ---------------------------------------------------------------- runs

export function useRuns(opts?: QueryOpts<Run[]>) {
  return useQuery<Run[], ApiError>({
    queryKey: qk.runs,
    queryFn: ({ signal }) => api.get<Run[]>('/runs', { signal }),
    ...opts,
  });
}

export function useRun(id: string | null | undefined, opts?: QueryOpts<RunDetail>) {
  return useQuery<RunDetail, ApiError>({
    queryKey: qk.run(id ?? ''),
    queryFn: ({ signal }) => api.get<RunDetail>(`/runs/${enc(id ?? '')}`, { signal }),
    enabled: !!id,
    ...opts,
  });
}

export function useRunSeries(id: string | null | undefined, opts?: QueryOpts<RunSeries>) {
  return useQuery<RunSeries, ApiError>({
    queryKey: qk.runSeries(id ?? ''),
    queryFn: ({ signal }) => api.get<RunSeries>(`/runs/${enc(id ?? '')}/series`, { signal }),
    enabled: !!id,
    staleTime: Infinity,
    ...opts,
  });
}

/** The run's labels per processed frame (the distance chart's band); `available: false` without labels. */
export function useRunLabels(id: string | null | undefined, opts?: QueryOpts<RunLabels>) {
  return useQuery<RunLabels, ApiError>({
    queryKey: qk.runLabels(id ?? ''),
    queryFn: ({ signal }) => api.get<RunLabels>(`/runs/${enc(id ?? '')}/labels`, { signal }),
    enabled: !!id,
    staleTime: Infinity,
    ...opts,
  });
}

export const FRAMES_PAGE_MAX = 500;

export function fetchRunFrames(id: string, from: number, count: number, signal?: AbortSignal): Promise<FramesPage> {
  return api.get<FramesPage>(`/runs/${enc(id)}/frames`, {
    query: { from: Math.max(0, Math.floor(from)), count: Math.min(FRAMES_PAGE_MAX, Math.max(1, Math.floor(count))) },
    signal,
  });
}

export function useRunFrames(id: string | null | undefined, from: number, count: number, opts?: QueryOpts<FramesPage>) {
  return useQuery<FramesPage, ApiError>({
    queryKey: qk.runFrames(id ?? '', from, count),
    queryFn: ({ signal }) => fetchRunFrames(id ?? '', from, count, signal),
    enabled: !!id,
    staleTime: Infinity,
    placeholderData: keepPreviousData,
    ...opts,
  });
}

export function useRunClouds(id: string | null | undefined, opts?: QueryOpts<CloudsIndex>) {
  return useQuery<CloudsIndex, ApiError>({
    queryKey: qk.runClouds(id ?? ''),
    queryFn: ({ signal }) => api.get<CloudsIndex>(`/runs/${enc(id ?? '')}/clouds`, { signal }),
    enabled: !!id,
    staleTime: Infinity,
    ...opts,
  });
}

export async function fetchRunCloud(id: string, pos: number, signal?: AbortSignal): Promise<DecodedCloud> {
  return decodeRSC1(await api.binary(`/runs/${enc(id)}/clouds/${pos}`, { signal }));
}

export function useRunCloud(id: string | null | undefined, pos: number | null | undefined, opts?: QueryOpts<DecodedCloud>) {
  return useQuery<DecodedCloud, ApiError>({
    queryKey: qk.runCloud(id ?? '', pos ?? -1),
    queryFn: ({ signal }) => fetchRunCloud(id ?? '', pos ?? 0, signal),
    enabled: !!id && pos !== null && pos !== undefined && pos >= 0,
    staleTime: Infinity,
    gcTime: 60_000,
    placeholderData: keepPreviousData,
    retry: (n, err) => err.status !== 404 && n < 1,
    ...opts,
  });
}

/** Warm the cache for the next clouds of a player. */
export function prefetchRunCloud(qc: QueryClient, id: string, pos: number): Promise<void> {
  return qc.prefetchQuery({
    queryKey: qk.runCloud(id, pos),
    queryFn: ({ signal }) => fetchRunCloud(id, pos, signal),
    staleTime: Infinity,
    gcTime: 60_000,
  });
}

function onRunsChanged(qc: QueryClient, run?: Run) {
  if (run) qc.setQueryData<RunDetail>(qk.run(run.id), (old) => (old ? { ...old, ...run } : old));
  void qc.invalidateQueries({ queryKey: qk.runs });
  void qc.invalidateQueries({ queryKey: qk.system });
}

export function useRenameRun() {
  const qc = useQueryClient();
  return useMutation<Run, ApiError, { id: string; name: string }>({
    mutationFn: ({ id, name }) => api.patch<Run>(`/runs/${enc(id)}`, { name }),
    onSuccess: (run) => onRunsChanged(qc, run),
  });
}

export function useDeleteRun() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => api.del(`/runs/${enc(id)}`),
    onSuccess: (_v, id) => {
      for (const root of ['run', 'run-series', 'run-labels', 'run-frames', 'run-clouds', 'run-cloud']) qc.removeQueries({ queryKey: [root, id] });
      onRunsChanged(qc);
    },
  });
}

// ---------------------------------------------------------------- presets

export function usePresets(opts?: QueryOpts<Preset[]>) {
  return useQuery<Preset[], ApiError>({
    queryKey: qk.presets,
    queryFn: ({ signal }) => api.get<Preset[]>('/presets', { signal }),
    ...opts,
  });
}

export function usePresetSchema(opts?: QueryOpts<ParamSpec[]>) {
  return useQuery<ParamSpec[], ApiError>({
    queryKey: qk.presetSchema,
    queryFn: ({ signal }) => api.get<ParamSpec[]>('/presets/schema', { signal }),
    staleTime: Infinity,
    ...opts,
  });
}

export function useCreatePreset() {
  const qc = useQueryClient();
  return useMutation<Preset, ApiError, PresetCreate>({
    mutationFn: (body) => api.post<Preset>('/presets', body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.presets }),
  });
}

export function useUpdatePreset() {
  const qc = useQueryClient();
  return useMutation<Preset, ApiError, { id: string; patch: PresetPatch }>({
    mutationFn: ({ id, patch }) => api.patch<Preset>(`/presets/${enc(id)}`, patch),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.presets }),
  });
}

export function useDeletePreset() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => api.del(`/presets/${enc(id)}`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.presets }),
  });
}
