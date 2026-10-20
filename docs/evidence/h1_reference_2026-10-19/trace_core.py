"""Actual collision-core exits for all A-axis and stationary 137m target scans."""
from collections import Counter
import json
import linecache
from pathlib import Path
import runpy
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/tmp/opencode/h1-reference')
OLD = ROOT / 'docs/evidence/h1_axis_range_2026-10-19'
sys.path.insert(0, str(OLD))
from trace_ranges import fingerprint, normalize  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame  # noqa: E402


def observation(frame, result):
    state = frame.f_locals
    b, rays = state['b'], state['rays']
    interval = state.get('interval')
    detail = dict(result=bool(result), line=frame.f_lineno,
        executed_return=linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip(),
        size=b.size.tolist(), distance=float(b.pts[:, 0].mean()), n=b.n_vox,
        h=[float(state['h'][b.idx].min()), float(state['h'][b.idx].max())],
        dy=[float(state['dy'][b.idx].min()), float(state['dy'][b.idx].max())],
        interval=interval, k=int(state['k'].size) if 'k' in state else None,
        anchor=rays._core_anchor if rays is not None else None)
    if rays is not None and rays._core_boundaries is not None:
        x = detail['distance']
        detail['boundary_support'] = [dict(near=int(((xs >= 8) & (xs <= 28)).sum()),
            local=int((np.abs(xs - x) <= max(6., .16 * x)).sum())) for xs, _ in rays._core_boundaries]
    return detail


def main():
    sys.path.insert(0, str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts'))
    import range_test as evaluator
    original = evaluator.run_frame
    previous = json.loads((OLD / 'trace-ranges-d.json').read_text())['cases']['A-axis']['rows']
    records = []

    def run_frame(rep, xyz, inten, ring, metadata, index):
        local = sys._getframe(1).f_locals
        info = dict(local.get('info', {}))
        last = len(xyz) - 2 * info['n_obj']
        observed = []

        def profile(frame, event, arg):
            if event == 'return' and frame.f_code.co_name == '_collision_core':
                s = frame.f_locals
                fi = s['frame_idx'][s['b'].idx]
                fi = fi[fi >= 0]
                if info['n_obj'] and fi.size and np.mean(fi >= last) > .5:
                    observed.append(observation(frame, arg))
        assert np.isfinite(xyz).all()
        if rep.detector._previous_latency_ms is not None:
            rep.detector._previous_latency_ms = 42.
        sys.setprofile(profile)
        try:
            result = original(rep, xyz, inten, ring, metadata, index)
        finally:
            sys.setprofile(None)
        assert fingerprint(result) == previous[index]['raw_hash']
        records.append(dict(i=index, info=info, calls=observed,
            candidates=[dict(distance=c.distance, zone=c.zone, reason=c.reason, core=c.collision_core,
                             height=[c.height_min, c.height_max], size=c.size.tolist()) for c in result.candidates
                        if info['X'] is not None and abs(c.distance - info['X']) < 6.3]))
        return result

    evaluator.run_frame = run_frame
    sys.argv = [evaluator.__file__, '/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT',
        '/tmp/opencode/r3-h1/baseline/icp_roundT_squareT_pressureGate_squareT.json',
        str(WORK / 'd-core-trace-range'), '--obj', '.3,.3,2.8', '--start', '150', '--d0', '230', '--end', '340']
    evaluator.main()
    evaluated = json.loads((WORK / 'd-core-trace-range.json').read_text())
    missing = [records[r['k']] for r in evaluated['rows'] if r['X'] is not None and r['X'] > 3 and r['n_obj'] > 0 and not r['hit']]
    counts = Counter()
    for row in missing:
        for call in row['calls']:
            key = ('core' if call['result'] else 'no_interval' if call['interval'] is None else
                   'mask_empty' if call['k'] == 0 else 'shape_or_height')
            counts[key] += 1
        print('MISS', row['i'], row['info']['X'], row['candidates'], row['calls'], flush=True)
    cast = runpy.run_path(str(ROOT / 'tests/fixtures/h1_physical.py'))['physical_column']
    static = []
    for mode in ['plain', 'traced']:
        detector = Detector(DetectorConfig())
        results = []
        for i in range(20):
            xyz, ring, labels = cast(distance=137., lateral=-.68, top=4.12, rails=True)
            calls = []

            def profile(frame, event, arg):
                if event == 'return' and frame.f_code.co_name == '_collision_core':
                    s = frame.f_locals
                    fi = s['frame_idx'][s['b'].idx]
                    fi = fi[fi >= 0]
                    if fi.size and np.mean(labels[fi] == 1) > .5:
                        calls.append(observation(frame, arg))
            if detector._previous_latency_ms is not None:
                detector._previous_latency_ms = 42.
            if mode == 'traced':
                sys.setprofile(profile)
            try:
                result = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            finally:
                sys.setprofile(None)
            results.append(dict(i=i, result=normalize(result.to_dict())[0], calls=calls,
                model_axis=float(result.track.center_y(137.)),
                column_hist=[t.column_hist.copy() for t in detector.tracker.tracks]))
        static.append(results)
    assert all(a['result'] == b['result'] for a, b in zip(*static, strict=True))
    for row in static[-1]:
        print('STATIC', row['i'], row['model_axis'], row['calls'], bool(row['result']['detections']), flush=True)
    with (WORK / 'd-core-trace.json').open('x') as stream:
        json.dump(dict(all_A_raw_results_equal=True, A=records, missing_calls=dict(counts),
                       static_plain_traced_equal=True, static=static[-1]), stream, indent=2)


if __name__ == '__main__':
    main()
