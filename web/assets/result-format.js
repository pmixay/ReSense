/* Shared input boundary for the dashboard and label tool. Older offline results may omit
 * optional fields; fields that are present must be usable by the renderers. Never coerce
 * strings to booleans/numbers or drop individual boxes from an otherwise invalid result. */
'use strict';
window.resenseFormat = (() => {
  const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const vector = (value, length) => Array.isArray(value) && value.length === length && value.every(finite);
  const numbers = (value, keys) => keys.every(key => value[key] == null || finite(value[key]));
  const decisions = new Set(['GO', 'CAUTION', 'STOP', 'FAULT']);
  const reasonLabels = {
    advisory_object: 'Предупреждение об объекте',
    health_warning: 'Снижена достоверность данных',
    doubt: 'Неоднозначный объект',
    margin_object: 'Объект у границы габарита',
    compact_range_object: 'Компактный объект в зоне контроля',
    incomplete_advisory: 'Недостаточно данных об объекте',
  };
  function cautionText(r, decision = r.decision) {
    if (decision !== 'CAUTION') return '';
    if (!r.caution_reason?.length) return 'Причина не передана';
    return [...new Set(r.caution_reason)].map(code => Object.hasOwn(reasonLabels, code)
      ? reasonLabels[code] : `Причина: ${code}`).join(' · ');
  }
  function detection(d) {
    return record(d) && vector(d.center, 3) && vector(d.size, 3) && d.size.every(v => v >= 0)
      && ['distance', 'lateral', 'confidence'].every(key => finite(d[key]))
      && numbers(d, ['height_min', 'intensity', 'n_points', 'age']);
  }
  function result(r) {
    if (!record(r) || typeof r.obstacle !== 'boolean'
        || (r.warning != null && typeof r.warning !== 'boolean')
        || (r.stop_held != null && typeof r.stop_held !== 'boolean')
        || (r.decision != null && !decisions.has(r.decision))
        || ('decision_policy' in r && typeof r.decision_policy !== 'string')
        || ('caution_reason' in r && (!Array.isArray(r.caution_reason)
          || !r.caution_reason.every(code => typeof code === 'string')))
        || !numbers(r, ['stamp', 'nearest_distance', 'clear_distance', 'n_points', 'n_corridor'])
        || (r.frame != null && (!Number.isSafeInteger(r.frame) || r.frame < 0))
        || ['nearest_distance', 'clear_distance'].some(key => r[key] != null && r[key] < 0)) return false;
    for (const key of ['detections', 'warnings']) {
      if (r[key] != null && (!Array.isArray(r[key]) || !r[key].every(detection))) return false;
    }
    for (const key of ['track', 'timing_ms', 'node', 'health', 'mount', 'freshness', 'gauge']) {
      if (r[key] != null && !record(r[key])) return false;
    }
    const t = r.track || {}, h = r.health || {}, f = r.freshness || {};
    const g = r.gauge;
    if (g != null && (typeof g.valid !== 'boolean' || typeof g.held !== 'boolean'
        || !numbers(g, ['drawn_range_m', 'solid_range_m', 'axis_valid_m', 'max_lateral_lag_m'])
        || !finite(g.drawn_range_m) || !finite(g.solid_range_m)
        || g.solid_range_m < 0 || g.drawn_range_m < g.solid_range_m
        || (g.valid && g.held) || (finite(g.axis_valid_m) && g.solid_range_m > g.axis_valid_m)
        || (!g.valid && g.solid_range_m !== 0)
        || (g.centerline != null && (!Array.isArray(g.centerline)
          || !g.centerline.every(p => vector(p, 3))
          || g.centerline.some((p, i) => i > 0 && p[0] <= g.centerline[i - 1][0]))))) return false;
    if (!numbers(t, ['center', 'yaw', 'curvature', 'curv_step', 'curv_knot', 'axis_valid', 'rail_offset'])
        || (t.floor_coef != null && (!Array.isArray(t.floor_coef) || !t.floor_coef.length || !t.floor_coef.every(finite)))
        || (t.floor_range != null && !vector(t.floor_range, 2))
        || !numbers(r.timing_ms || {}, ['total', 'track', 'corridor', 'cluster'])
        || !numbers(r.node || {}, ['latency_ms', 'fps', 'frames', 'dropped_frames', 'input_period_ms'])
        || !numbers(h, ['visibility', 'rail_lock'])
        || ['level', 'decision_level'].some(key => h[key] != null && !['ok', 'warn', 'error'].includes(h[key]))
        || (f.valid != null && typeof f.valid !== 'boolean')
        || !numbers(f, ['source_age_s', 'residence_age_s', 'evaluated_at_utc_s', 'transport_age_s',
                        'max_result_age_s', 'future_tolerance_s', 'queue_lag_s'])
        || (h.messages != null && (!Array.isArray(h.messages) || !h.messages.every(v => typeof v === 'string')))) return false;
    return true;
  }
  return { record, finite, vector, result, cautionText };
})();
