"""Independently check every critical range hit from full detector outputs."""
from dataclasses import fields, is_dataclass
import hashlib
import json
import linecache
from pathlib import Path
import runpy
import sys

import numpy as np

from run_checks import ROOT, HERE, WORK, archived
from resense.tracking import Tracker

sys.path.insert(0, str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts'))
import range_test as evaluator  # noqa: E402

normalize = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))['normalize']
R3 = Path('/tmp/opencode/r3-h1')
A, C = 'roundT_squareT_pressureGate_squareT', 'roundT_pressureGate_roundT'


def fingerprint(value):
    digest = hashlib.sha256()

    def add(v):
        if isinstance(v, np.ndarray):
            digest.update(str((v.shape, str(v.dtype))).encode())
            digest.update(v.tobytes())
        elif is_dataclass(v):
            for field in fields(v):
                if field.name != 'timing_ms':
                    digest.update(field.name.encode())
                    add(getattr(v, field.name))
        elif isinstance(v, dict):
            for key in sorted(v):
                digest.update(str(key).encode())
                add(v[key])
        elif isinstance(v, (list, tuple)):
            digest.update(str(len(v)).encode())
            for item in v:
                add(item)
        else:
            digest.update(repr(v).encode())
    add(value)
    return digest.hexdigest()


def main():
    revision = sys.argv[1]
    before = archived.sources(ROOT)
    original = evaluator.run_frame
    report = dict(revision=revision, source_sha256=before, cases={})
    cases = [
        ('A-axis', [R3 / 'baseline/cache' / A, R3 / 'baseline' / f'icp_{A}.json'],
         ['--obj', '0.3,0.3,2.8', '--start', '150', '--d0', '230', '--end', '340']),
        ('C-person', [R3 / 'supplement-range/decoded' / C, R3 / 'supplement-range' / f'icp_{C}.json'],
         ['--obj', '0.5,0.5,1.75', '--start', '0', '--d0', '230']),
        ('E6', [R3 / 'baseline/cache' / A, R3 / 'baseline' / f'icp_{A}.json'],
         ['--obj', '0.05,0.05,2.6', '--start', '150', '--d0', '230', '--end', '340', '--base', '0.2']),
    ]
    for label, positional, flags in cases:
        runs = {}
        for mode in (['plain', 'traced'] if label == 'A-axis' else ['plain']):
            records, assignments = [], []

            def trace(frame, event, arg):
                if frame.f_code is not Tracker.update.__code__:
                    return None
                if event == 'line' and linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip().startswith('t.reported = (q or'):
                    v, t = frame.f_locals, frame.f_locals['t']
                    assignments.append(dict(id=t.id, q=bool(v['q']), reported_before=t.reported,
                        misses=t.misses, hold_misses=v['self'].cfg.hold_misses, last_core=t.last.collision_core,
                        column_hist=t.column_hist.copy(), zone_hist=t.zone_hist.copy()))
                return trace

            def run_frame(rep, xyz, inten, ring, meta, index):
                info = dict(sys._getframe(1).f_locals.get('info', {}))
                if rep.detector._previous_latency_ms is not None:
                    rep.detector._previous_latency_ms = 42.
                start = len(assignments)
                if mode == 'traced':
                    sys.settrace(trace)
                try:
                    result = original(rep, xyz, inten, ring, meta, index)
                finally:
                    sys.settrace(None)
                records.append(dict(i=index, info=info, result=normalize(result.to_dict())[0],
                    raw_hash=fingerprint(result), detections=[dict(distance=float(d.distance), center=list(map(float, d.center)))
                                                              for d in result.detections],
                    assignments=assignments[start:]))
                return result

            evaluator.run_frame = run_frame
            prefix = WORK / f'trace-{revision}-{label}-{mode}'
            sys.argv = [str(evaluator.__file__), *map(str, positional), str(prefix), *flags]
            evaluator.main()
            output = json.loads(prefix.with_suffix('.json').read_text())
            original_output = json.loads((WORK / f'probes-{revision}-candidate' / f'{label}.json').read_text())
            length, width = output['summary']['obj'][:2]
            for row, record, old in zip(output['rows'], records, original_output['rows'], strict=True):
                match = (row['X'] is not None and row['X'] > 3 and 'Y' in row
                         and any(abs(d['distance'] - row['X']) <= max(2., .03 * row['X']) + length / 2
                                 and abs(d['center'][1] - row['Y']) <= 1 + width / 2 for d in record['detections']))
                assert match == row['hit'] == old['hit']
                assert row['n_obj'] == old['n_obj'] and row['X'] == old['X']
            runs[mode] = records
        if label == 'A-axis':
            for a, b in zip(runs['plain'], runs['traced'], strict=True):
                assert a['raw_hash'] == b['raw_hash'] and a['result'] == b['result'] and a['info'] == b['info']
        report['cases'][label] = dict(rows=runs.get('traced', runs['plain']),
            independently_checked_rows=len(runs['plain']), full_plain_traced_equal=label == 'A-axis')
        print('INDEPENDENT', label, len(runs['plain']), flush=True)
    assert archived.sources(ROOT) == before
    report['source_unchanged'] = True
    with (HERE / f'trace-ranges-{revision}.json').open('x') as stream:
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
