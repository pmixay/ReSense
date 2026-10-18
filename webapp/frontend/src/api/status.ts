// Shared HTTP / simulated WS / ROS boundary. Optional legacy fields may be absent;
// present fields must be usable. No coercion and no partial removal of bad boxes.
import type { LiveMessage } from './types';
import { isDecision } from '../lib/decisions';

const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const vector = (v: unknown) => Array.isArray(v) && v.length === 3 && v.every(finite);
const numbers = (r: Record<string, unknown>, keys: string[]) => keys.every(k => r[k] == null || finite(r[k]));

export function isStatus(v: unknown): v is LiveMessage {
  if (!record(v) || !isDecision(v.decision)) return false;
  if (['obstacle', 'warning', 'stop_held'].some(k => k in v && typeof v[k] !== 'boolean')) return false;
  if ('decision_policy' in v && typeof v.decision_policy !== 'string') return false;
  if ('caution_reason' in v && (!Array.isArray(v.caution_reason) || !v.caution_reason.every(x => typeof x === 'string'))) return false;
  if (!numbers(v, ['stamp', 'nearest_distance', 'clear_distance', 'pos', 'frame', 't', 'n_points', 'n_corridor'])) return false;
  if (['nearest_distance', 'clear_distance'].some(k => finite(v[k]) && v[k] < 0)) return false;
  for (const key of ['detections', 'warnings']) {
    const list = v[key];
    if (list != null && (!Array.isArray(list) || !list.every(d => record(d)
      && vector(d.center) && vector(d.size) && (d.size as number[]).every(x => x >= 0)
      && ['distance', 'lateral', 'confidence'].every(k => finite(d[k]))))) return false;
  }
  for (const key of ['health', 'freshness', 'node', 'track', 'mount', 'timing_ms']) {
    if (v[key] != null && !record(v[key])) return false;
  }
  const h = (v.health ?? {}) as Record<string, unknown>;
  const f = (v.freshness ?? {}) as Record<string, unknown>;
  if (['level', 'decision_level'].some(k => k in h && !['ok', 'warn', 'error'].includes(h[k] as string))) return false;
  if (h.messages != null && (!Array.isArray(h.messages) || !h.messages.every(x => typeof x === 'string'))) return false;
  if (!numbers(h, ['visibility', 'rail_lock'])) return false;
  if (['valid', 'go_allowed'].some(k => k in f && typeof f[k] !== 'boolean')) return false;
  if (!numbers(f, ['source_age_s', 'residence_age_s', 'evaluated_at_utc_s', 'max_result_age_s', 'future_tolerance_s', 'queue_lag_s'])) return false;
  return true;
}
