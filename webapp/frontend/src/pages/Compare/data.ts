// The compared runs' details and chart series, fetched in parallel under the same query keys as
// useRun / useRunSeries (api/hooks.ts), so the run page and this page share their caches.
import { useQueries } from '@tanstack/react-query';
import { useRef } from 'react';
import { api, type ApiError } from '../../api/client';
import { qk } from '../../api/hooks';
import type { RunDetail, RunSeries } from '../../api/types';
import { reconnect } from '../Runs/common/analysis';

export interface Compared {
  id: string;
  slot: number;
  run: RunDetail | undefined;
  series: RunSeries | undefined;
  error: ApiError | null;
  seriesError: ApiError | null;
  loading: boolean;
}

const enc = encodeURIComponent;

export function useCompared(slots: readonly (string | null)[]): Compared[] {
  const ids = slots.map((s, slot) => ({ id: s, slot })).filter((x): x is { id: string; slot: number } => !!x.id);
  const details = useQueries({
    queries: ids.map(({ id }) => ({
      queryKey: qk.run(id),
      queryFn: ({ signal }: { signal: AbortSignal }) => api.get<RunDetail>(`/runs/${enc(id)}`, { signal }),
      retry: (n: number, err: ApiError) => err.status !== 404 && !err.offline && n < 1,
      refetchInterval: reconnect,
    })),
  });
  const series = useQueries({
    queries: ids.map(({ id }) => ({
      queryKey: qk.runSeries(id),
      queryFn: ({ signal }: { signal: AbortSignal }) => api.get<RunSeries>(`/runs/${enc(id)}/series`, { signal }),
      staleTime: Infinity,
      retry: (n: number, err: ApiError) => err.status !== 404 && !err.offline && n < 1,
      refetchInterval: reconnect,
    })),
  });
  const next: Compared[] = ids.map(({ id, slot }, i) => ({
    id,
    slot,
    run: details[i]?.data,
    series: series[i]?.data,
    error: (details[i]?.error as ApiError | null) ?? null,
    seriesError: (series[i]?.error as ApiError | null) ?? null,
    loading: !!details[i]?.isLoading,
  }));
  // the same array while nothing changed, so charts and tables can memoize on it
  const prev = useRef<Compared[]>([]);
  if (!sameItems(prev.current, next)) prev.current = next;
  return prev.current;
}

function sameItems(a: readonly Compared[], b: readonly Compared[]): boolean {
  return (
    a.length === b.length &&
    a.every((x, i) => {
      const y = b[i];
      return x.id === y.id && x.slot === y.slot && x.run === y.run && x.series === y.series && x.error === y.error && x.seriesError === y.seriesError && x.loading === y.loading;
    })
  );
}
