"""Actual tracker assignment trace and full plain/traced equality on the A-axis probe."""
from dataclasses import fields, is_dataclass
import hashlib
import json
import linecache
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-core')
R3 = Path('/tmp/opencode/r3-h1')
A = 'roundT_squareT_pressureGate_squareT'
revision = sys.argv[1] if len(sys.argv) > 1 else 'v2'
sys.path.insert(0, str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts'))
import range_test as t  # noqa: E402
from judge_runner import record  # noqa: E402
from resense.tracking import Tracker  # noqa: E402


def fingerprint(value):
    h = hashlib.sha256()

    def add(v):
        if isinstance(v, np.ndarray):
            h.update(str((v.shape, str(v.dtype))).encode())
            h.update(v.tobytes())
        elif is_dataclass(v):
            for field in fields(v):
                if field.name != 'timing_ms':
                    h.update(field.name.encode())
                    add(getattr(v, field.name))
        elif isinstance(v, dict):
            for key in sorted(v):
                h.update(str(key).encode())
                add(v[key])
        elif isinstance(v, (list, tuple)):
            h.update(str(len(v)).encode())
            for x in v:
                add(x)
        else:
            h.update(repr(v).encode())
    add(value)
    return h.hexdigest()


original = t.run_frame
results = {}
assignments = []


def trace(frame, event, arg):
    if frame.f_code is not Tracker.update.__code__:
        return None
    if event == 'line' and linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip().startswith('t.reported = (q or'):
        loc = frame.f_locals
        tr = loc['t']
        assignments.append(dict(id=tr.id, q=bool(loc['q']), reported_before=tr.reported,
                                misses=tr.misses, hold_misses=loc['self'].cfg.hold_misses,
                                hold=tr.hold, explained_blocked=bool(loc['explained_blocked']),
                                last_distance=tr.last.distance, core=tr.last.collision_core,
                                column_hist=tr.column_hist.copy(), zone_hist=tr.zone_hist.copy()))
    return trace


for mode in ['off', 'on']:
    records = []

    def run_frame(rep, xyz, inten, ring, m, k):
        info = dict(sys._getframe(1).f_locals.get('info', {}))
        if rep.detector._previous_latency_ms is not None:
            rep.detector._previous_latency_ms = 42.0
        start = len(assignments)
        if mode == 'on':
            sys.settrace(trace)
        try:
            r = original(rep, xyz, inten, ring, m, k)
        finally:
            sys.settrace(None)
        node = record(k, m['bag_t'], m['stamp'], r, 0., 0., m['frame_id'], m['topic'])
        node.pop('total_ms')  # record() reads the measured total despite zero timing arguments
        entry = dict(k=k, info=info, node=node, full_result_hash=fingerprint(r))
        if mode == 'on':
            entry['assignments'] = assignments[start:]
            entry['tracks'] = [dict(id=tr.id, misses=tr.misses, reported=tr.reported, zone=tr.zone,
                                    last_distance=tr.last.distance, last_core=tr.last.collision_core,
                                    column_hist=tr.column_hist.copy(), zone_hist=tr.zone_hist.copy())
                               for tr in rep.detector.tracker.tracks if tr.last is not None]
        records.append(entry)
        return r

    t.run_frame = run_frame
    out = WORK / f'axis-trace-{revision}-{mode}'
    sys.argv = [str(t.__file__), str(R3 / 'baseline/cache' / A), str(R3 / 'baseline' / f'icp_{A}.json'),
                str(out), '--obj', '0.3,0.3,2.8', '--start', '150', '--d0', '230', '--end', '340']
    t.main()
    results[mode] = records

assert len(results['off']) == len(results['on']) == 340
for b, c in zip(results['off'], results['on'], strict=True):
    assert b['info'] == c['info'] and b['node'] == c['node'] and b['full_result_hash'] == c['full_result_hash'], (
        c['k'], b['info'] == c['info'], b['node'] == c['node'], b['full_result_hash'] == c['full_result_hash'])
old = json.loads((WORK / 'supplement/reference-A-axis.json').read_text())
new = json.loads((WORK / f'axis-trace-{revision}-on.json').read_text())
added = [r['k'] for b, r in zip(old['rows'], new['rows'], strict=True) if r['hit'] and not b['hit']]
target = results['on'][335]
reported_ids = {d['id'] for d in target['tracks'] if d['reported'] and d['zone'] == 'gauge'}
fired = [r for r in target['assignments'] if r['id'] in reported_ids]
assert len(fired) == 1 and fired[0]['q'] is False and fired[0]['reported_before'] is True
assert fired[0]['misses'] == fired[0]['hold_misses'] == 1
assert target['info']['n_obj'] == 0 and 0 < target['info']['X'] < 3
result = dict(frames=340, full_plain_traced_equal=True, fixed_previous_latency_ms=42,
              added_matched_rows=added, added_unmatched_row=target,
              added_matched_states=[results['on'][k] for k in added])
name = 'axis-trace.json' if revision == 'v2' else f'axis-trace-{revision}.json'
with (HERE / name).open('x') as f:
    json.dump(result, f, indent=2)
print('Full raw/serialized plain-traced equality:340. Added matches:', added, 'k335 firing:', fired)
