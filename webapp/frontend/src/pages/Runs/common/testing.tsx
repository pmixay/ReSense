// Test helpers of the analysis pages: API fixtures shaped like the backend's answers, a fetch stub
// routed by path, and a render with a fresh QueryClient and a memory router.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { vi } from 'vitest';
import type { Episode, EvalSummary, Run, RunDetail, RunLabels, RunSeries } from '../../../api/types';

export function makeRun(id: string, decisions: string, over: Partial<Run> = {}, ev: EvalSummary | null = null): Run {
  const n = decisions.length;
  const counts = { GO: 0, CAUTION: 0, STOP: 0, FAULT: 0 };
  for (const c of decisions) counts[c === 'S' ? 'STOP' : c === 'C' ? 'CAUTION' : c === 'F' ? 'FAULT' : 'GO'] += 1;
  const first = decisions.indexOf('S');
  return {
    id,
    name: id,
    recording_id: 'rec1',
    job_id: null,
    preset: { id: 'standard', name: 'Стандарт 1.0' },
    created_at: '2026-09-29T08:58:00Z',
    has_clouds: true,
    cloud_frames: n,
    source_kind: 'rosbag2',
    summary: {
      n_frames: n,
      duration_s: (n - 1) / 10,
      counts,
      decisions,
      stop_episodes: decisions.split(/[^S]+/).filter(Boolean).length,
      first_stop: first >= 0 ? { frame: first, t: first / 10, distance: 55.2 } : null,
      distance_min: first >= 0 ? 55.2 : null,
      distance_max: first >= 0 ? 55.3 : null,
      latency_ms: { p50: 20, p95: 25.1, max: 49.9 },
      processing_fps: 20.8,
      clear_distance_median: 184,
      visibility_median: 184,
      eval: ev,
    },
    ...over,
  };
}

export const EVAL: EvalSummary = {
  labels_name: 'demo_crossing (эталон демо)',
  frames_labelled: 20,
  frames_with_object_in_gauge: 6,
  frames_detected: 5,
  recall: 5 / 6,
  false_stop_frames: 2,
  false_stop_episodes: 1,
  first_detection_distance: 55.27,
  raw: {},
};

function episodes(decisions: string): Episode[] {
  const out: Episode[] = [];
  let i = 0;
  while (i < decisions.length) {
    let j = i;
    while (j + 1 < decisions.length && decisions[j + 1] === decisions[i]) j += 1;
    const d = decisions[i] === 'S' ? 'STOP' : decisions[i] === 'C' ? 'CAUTION' : decisions[i] === 'F' ? 'FAULT' : 'GO';
    out.push({ decision: d, first_frame: i, last_frame: j, t0: i / 10, t1: j / 10, n_frames: j - i + 1, distance_min: d === 'STOP' ? 55.22 : null, distance_max: d === 'STOP' ? 55.25 : null });
    i = j + 1;
  }
  return out;
}

export function makeDetail(run: Run, over: Partial<RunDetail> = {}): RunDetail {
  const eps = episodes(run.summary.decisions);
  return {
    ...run,
    episodes: eps,
    // as the backend's events_of: non-GO episodes and GO gaps between two STOP episodes
    events: eps.filter((e, k) => {
      if (e.decision !== 'GO') return true;
      const side = (step: number) => {
        for (let j = k + step; j >= 0 && j < eps.length; j += step) {
          if (eps[j].decision === 'STOP') return true;
          if (eps[j].decision === 'GO') return false;
        }
        return false;
      };
      return side(-1) && side(1);
    }),
    recording: null,
    options: { topic: null, every: 1, start: 0, limit: null, clouds: true, cloud_points: 30000, ego_speed: null, evaluate: true },
    overrides: {},
    sizes: { results_jsonl: 139_000, clouds: 23_000_000 },
    ...over,
  };
}

export function makeSeries(decisions: string, labels: boolean[] | null = null): RunSeries {
  const n = decisions.length;
  const idx = Array.from({ length: n }, (_, i) => i);
  return {
    frame: idx,
    t: idx.map((i) => i / 10),
    decisions,
    nearest: idx.map((i) => (decisions[i] === 'S' ? 55.2 : null)),
    clear: idx.map(() => 184),
    latency_ms: idx.map(() => 20),
    n_detections: idx.map((i) => (decisions[i] === 'S' ? 1 : 0)),
    n_warnings: idx.map(() => 0),
    n_points: idx.map(() => 100_000),
    visibility: idx.map(() => 184),
    labels_in_gauge: labels,
  };
}

export const NO_LABELS: RunLabels = { available: false, labels_name: null, in_gauge: [], near: [], far: [] };

type Handler = unknown | ((init: RequestInit | undefined, url: URL) => unknown);

/** Stubs global fetch: `routes` maps "METHOD /api/path" (or "/api/path" for GET) to a JSON body or a
 *  function of the request; anything else answers 404 {"detail": "Не найдено"}. */
export function stubFetch(routes: Record<string, Handler>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, 'http://test');
    const method = (init?.method ?? 'GET').toUpperCase();
    const key = routes[`${method} ${url.pathname}`] !== undefined ? `${method} ${url.pathname}` : method === 'GET' ? url.pathname : '';
    const h = key ? routes[key] : undefined;
    if (h === undefined) return new Response(JSON.stringify({ detail: 'Не найдено' }), { status: 404, headers: { 'Content-Type': 'application/json' } });
    const body = typeof h === 'function' ? (h as (i: RequestInit | undefined, u: URL) => unknown)(init, url) : h;
    if (body === null) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

/** Renders `element` at `path` (matched by `pattern`) with a fresh QueryClient; other paths render their path. */
export function renderAt(element: ReactElement, pattern: string, path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path={pattern} element={element} />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="elsewhere">{loc.pathname + loc.search}</div>;
}
