// Numbers of the Главная KPI tiles, derived from the runs list (newest first) — pure, unit-tested.
import type { Run } from '../../api/types';

/** Histogram of per-frame latencies: `bins` equal bins over [0, max]; the bin holding p95. */
export function latencyHistogram(latency: readonly number[], p95: number, bins = 15): { counts: number[]; p95Bin: number; max: number } {
  const vals = latency.filter((v) => Number.isFinite(v) && v >= 0);
  const max = vals.length ? Math.max(...vals, p95) : Math.max(p95, 1);
  const counts = new Array<number>(bins).fill(0);
  const w = max / bins || 1;
  for (const v of vals) counts[Math.min(bins - 1, Math.floor(v / w))] += 1;
  const p95Bin = Math.min(bins - 1, Math.max(0, Math.floor(p95 / w)));
  return { counts, p95Bin, max };
}

/** The newest run scored against labels that had an object in the gauge. */
export function latestWithObject(runs: readonly Run[] | undefined): Run | undefined {
  return runs?.find((r) => (r.summary.eval?.frames_with_object_in_gauge ?? 0) > 0);
}

/** The newest run with a first STOP at a known distance. */
export function latestFirstStop(runs: readonly Run[] | undefined): Run | undefined {
  return runs?.find((r) => r.summary.first_stop && r.summary.first_stop.distance !== null);
}

export interface FalseStops {
  runs: Run[]; // scored runs, oldest → newest (at most `limit`)
  total: number; // false STOP episodes over all scored runs
  scored: number; // number of scored runs
  perKm: number | null; // when every scored run knows its travelled distance
  perRun: number;
}

/** False STOP episodes over the runs scored against labels (per km when distances are known). */
export function falseStops(runs: readonly Run[] | undefined, limit = 8): FalseStops | null {
  const scored = (runs ?? []).filter((r) => r.summary.eval);
  if (!scored.length) return null;
  const total = scored.reduce((s, r) => s + (r.summary.eval?.false_stop_episodes ?? 0), 0);
  const kms = scored.map((r) => {
    const km = r.summary.eval?.raw?.distance_km;
    return typeof km === 'number' && Number.isFinite(km) ? km : null;
  });
  const sumKm = kms.every((k) => k !== null) ? kms.reduce<number>((s, k) => s + (k ?? 0), 0) : null;
  return {
    runs: scored.slice(0, limit).reverse(),
    total,
    scored: scored.length,
    perKm: sumKm !== null && sumKm >= 0.01 ? total / sumKm : null,
    perRun: total / scored.length,
  };
}

/** Processed-order position of the first STOP of a decision string (0 when there is none). */
export function firstStopPos(decisions: string): number {
  const i = decisions.indexOf('S');
  return i < 0 ? 0 : i;
}

/** The run the player card shows: the newest with stored clouds and a STOP, else the newest with clouds. */
export function playerRun(runs: readonly Run[] | undefined): Run | undefined {
  const withClouds = (runs ?? []).filter((r) => r.has_clouds && r.cloud_frames > 0);
  return withClouds.find((r) => r.summary.first_stop) ?? withClouds[0];
}
