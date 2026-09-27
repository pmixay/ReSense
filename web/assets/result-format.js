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
  function detection(d) {
    return record(d) && vector(d.center, 3) && vector(d.size, 3) && d.size.every(v => v >= 0)
      && ['distance', 'lateral', 'confidence'].every(key => finite(d[key]))
      && numbers(d, ['height_min', 'intensity', 'n_points', 'age']);
  }
  function result(r) {
    if (!record(r) || typeof r.obstacle !== 'boolean'
        || (r.warning != null && typeof r.warning !== 'boolean')
        || (r.decision != null && !decisions.has(r.decision))
        || !numbers(r, ['stamp', 'nearest_distance', 'clear_distance', 'n_points', 'n_corridor'])
        || (r.frame != null && (!Number.isSafeInteger(r.frame) || r.frame < 0))) return false;
    for (const key of ['detections', 'warnings']) {
      if (r[key] != null && (!Array.isArray(r[key]) || !r[key].every(detection))) return false;
    }
    for (const key of ['track', 'timing_ms', 'node', 'health', 'mount', 'freshness']) {
      if (r[key] != null && !record(r[key])) return false;
    }
    const t = r.track || {}, h = r.health || {};
    if (!numbers(t, ['center', 'yaw', 'curvature', 'axis_valid', 'rail_offset'])
        || (t.floor_coef != null && (!Array.isArray(t.floor_coef) || !t.floor_coef.length || !t.floor_coef.every(finite)))
        || (t.floor_range != null && !vector(t.floor_range, 2))
        || !numbers(r.timing_ms || {}, ['total', 'track', 'corridor', 'cluster'])
        || !numbers(r.node || {}, ['latency_ms', 'fps', 'frames', 'dropped_frames', 'input_period_ms'])
        || !numbers(h, ['visibility', 'rail_lock'])
        || (h.messages != null && (!Array.isArray(h.messages) || !h.messages.every(v => typeof v === 'string')))) return false;
    return true;
  }
  return { record, finite, vector, result };
})();
