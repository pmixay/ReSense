// Generating a demo recording (POST /api/recordings/demo is synchronous: ~0.65–1.3 s per simulated
// second) with live progress from GET /api/recordings/demo/progress/{id}; until the first answer
// the fraction is estimated from the elapsed time. Used by Загрузка and the Главная «Демо».
//
// The generation lives in a module-level store, not in a component: it keeps running (and its
// progress stays visible) when the user switches pages, only one runs at a time, and its result is
// handed to the page that asked for it when that page is shown again.
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { ApiError, api, errorMessage } from '../../api/client';
import { qk } from '../../api/hooks';
import type { DemoCreate, DemoProgress, DemoScenario, Recording } from '../../api/types';
import { demoSeconds } from './estimate';

export interface DemoRequest {
  scenario: DemoScenario;
  seconds: number;
}

/** Who asked for the generation: its result and error are shown there only. */
export type DemoOrigin = 'overview' | 'upload';

export const SCENARIO_LABEL: Record<DemoScenario, string> = {
  approach: 'Приближение',
  crossing: 'Пересечение пути',
  clear: 'Чистый путь',
};

const POLL_AFTER_S = 0.8;
const newProgressId = () => `demo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

/** Progress 0..1 and seconds left: the server's fraction when known, else elapsed / expected. */
export function demoProgress(elapsedS: number, expectedS: number, real: number | null): { fraction: number; etaS: number } {
  if (real !== null && real > 0.03) {
    const f = Math.min(1, real);
    return { fraction: f, etaS: Math.max(0, (elapsedS * (1 - f)) / f) };
  }
  const f = expectedS > 0 ? Math.min(0.95, elapsedS / expectedS) : 0;
  return { fraction: f, etaS: Math.max(0, expectedS - elapsedS) };
}

// ---------------------------------------------------------------- the store

interface ActiveDemo {
  req: DemoRequest;
  id: string;
  t0: number;
  origin: DemoOrigin;
  promise: Promise<Recording | null>;
}

interface DemoStore {
  active: ActiveDemo | null;
  error: { origin: DemoOrigin; error: ApiError } | null;
  /** the last generated recording, until the page that asked for it takes it */
  result: { origin: DemoOrigin; recording: Recording } | null;
}

let store: DemoStore = { active: null, error: null, result: null };
const listeners = new Set<() => void>();
const setStore = (patch: Partial<DemoStore>) => {
  store = { ...store, ...patch };
  listeners.forEach((l) => l());
};
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
};
const snapshot = () => store;

/** Starts a generation; while one runs, its promise is returned instead of starting another. */
export function startDemo(qc: QueryClient, req: DemoRequest, origin: DemoOrigin): Promise<Recording | null> {
  if (store.active) return store.active.promise;
  const id = newProgressId();
  const body: DemoCreate = { scenario: req.scenario, seconds: req.seconds, progress_id: id };
  const promise = api
    .post<Recording>('/recordings/demo', body)
    .then((rec) => {
      qc.setQueryData(qk.recording(rec.id), rec);
      void qc.invalidateQueries({ queryKey: qk.recordings });
      void qc.invalidateQueries({ queryKey: qk.system });
      setStore({ active: null, result: { origin, recording: rec } });
      return rec;
    })
    .catch((err: unknown) => {
      const error = err instanceof ApiError ? err : new ApiError(errorMessage(err), 0);
      setStore({ active: null, error: { origin, error } });
      return null;
    });
  setStore({ active: { req, id, t0: Date.now(), origin, promise }, error: null, result: null });
  return promise;
}

/** The finished recording asked for by `origin` (once; null when there is none). */
export function takeDemoResult(origin: DemoOrigin): Recording | null {
  const r = store.result;
  if (!r || r.origin !== origin) return null;
  setStore({ result: null });
  return r.recording;
}

/** Test helper: forget everything. */
export function resetDemoStore(): void {
  setStore({ active: null, error: null, result: null });
}

// ---------------------------------------------------------------- the hook

export function useDemoGenerator(origin: DemoOrigin) {
  const qc = useQueryClient();
  const s = useSyncExternalStore(subscribe, snapshot, snapshot);
  const active = s.active;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const t = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(t);
  }, [active]);

  const elapsedS = active ? Math.max(0, (now - active.t0) / 1000) : 0;
  const poll = useQuery<DemoProgress, ApiError>({
    queryKey: ['demo-progress', active?.id ?? ''],
    queryFn: ({ signal }) => api.get<DemoProgress>(`/recordings/demo/progress/${encodeURIComponent(active?.id ?? '')}`, { signal }),
    // the POST registers the id when the server starts on it: give it a head start (no 404 race)
    enabled: !!active && elapsedS >= POLL_AFTER_S,
    refetchInterval: 400,
    retry: false,
    gcTime: 0,
  });

  const generate = useCallback((req: DemoRequest) => startDemo(qc, req, origin), [qc, origin]);
  const take = useCallback(() => takeDemoResult(origin), [origin]);
  const dismissError = useCallback(() => {
    if (store.error?.origin === origin) setStore({ error: null });
  }, [origin]);

  const real = active && poll.data && !poll.isError && poll.data.progress_id === active.id ? poll.data.fraction : null;
  const { fraction, etaS } = active ? demoProgress(elapsedS, demoSeconds(active.req.seconds), real) : { fraction: 0, etaS: 0 };

  return {
    generate,
    /** the request being generated (by any page), null when idle */
    active: active?.req ?? null,
    fraction,
    etaS,
    elapsedS,
    /** the failure of this page's last generation */
    error: s.error?.origin === origin ? s.error.error : null,
    dismissError,
    /** takes the recording this page asked for once it is ready (null otherwise) */
    take,
  };
}
