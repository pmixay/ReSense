// Generating a demo recording (POST /api/recordings/demo is synchronous: ~0.65 s per simulated
// second) with live progress from GET /api/recordings/demo/progress/{id}; until the first answer
// the fraction is estimated from the elapsed time. Used by Загрузка and the Главная «Демо».
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { ApiError, api } from '../../api/client';
import { useCreateDemo } from '../../api/hooks';
import type { DemoProgress, DemoScenario, Recording } from '../../api/types';
import { demoSeconds } from './estimate';

export interface DemoRequest {
  scenario: DemoScenario;
  seconds: number;
}

export const SCENARIO_LABEL: Record<DemoScenario, string> = {
  approach: 'Приближение',
  crossing: 'Пересечение пути',
  clear: 'Чистый путь',
};

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

export function useDemoGenerator() {
  const create = useCreateDemo();
  const { mutateAsync } = create;
  const [active, setActive] = useState<{ req: DemoRequest; id: string; t0: number } | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(t);
  }, [active]);

  const poll = useQuery<DemoProgress, ApiError>({
    queryKey: ['demo-progress', active?.id ?? ''],
    queryFn: ({ signal }) => api.get<DemoProgress>(`/recordings/demo/progress/${encodeURIComponent(active?.id ?? '')}`, { signal }),
    enabled: !!active,
    refetchInterval: 400,
    retry: false,
    gcTime: 0,
  });

  const generate = useCallback(
    async (req: DemoRequest): Promise<Recording | null> => {
      const id = newProgressId();
      setNow(Date.now());
      setActive({ req, id, t0: Date.now() });
      try {
        return await mutateAsync({ scenario: req.scenario, seconds: req.seconds, progress_id: id });
      } catch {
        return null; // the message is in `error`
      } finally {
        setActive(null);
      }
    },
    [mutateAsync],
  );

  const elapsedS = active ? Math.max(0, (now - active.t0) / 1000) : 0;
  const real = active && poll.data && !poll.isError ? poll.data.fraction : null;
  const { fraction, etaS } = active ? demoProgress(elapsedS, demoSeconds(active.req.seconds), real) : { fraction: 0, etaS: 0 };

  return {
    generate,
    /** the request being generated, null when idle */
    active: active?.req ?? null,
    fraction,
    etaS,
    elapsedS,
    error: create.error,
    recording: create.data ?? null,
    reset: create.reset,
  };
}
