"""Observe H1 predicate state without changing detector results."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.gauge import gauge_core_mask
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[3]
cast = runpy.run_path(str(ROOT / 'tests/fixtures/h1_physical.py'))['physical_column']
normalize = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))['normalize']


def run_case(distance, lateral, top, moving=False):
    runs = {}
    for mode in ['plain', 'traced']:
        detector = Detector(DetectorConfig())
        saved = []
        for i in range(56 if moving else 14):
            x = distance - 2.2 * i if moving else distance
            xyz, ring, labels = cast(distance=x, lateral=lateral, top=top, rails=True)
            observed = []

            def profile(frame, event, arg):
                if event != 'return' or frame.f_code.co_name != '_collision_core':
                    return
                v = frame.f_locals
                b = v['b']
                fi = v['frame_idx'][b.idx]
                fi = fi[fi >= 0]
                if not fi.size or np.mean(labels[fi] == 1) <= .5:
                    return
                current = (v['frame_idx'][b.idx] >= 0) & v['in_gauge'][b.idx] & v['in_rail'][b.idx]
                k = b.idx[current]
                inner = replace(v['gauge'], edge_margin=v['gauge'].edge_margin + v['cfg'].column_core_margin)
                interval = v.get('interval')
                kept = []
                if interval is not None:
                    keep = np.ones(len(k), dtype=bool)
                    for endpoint in interval:
                        keep &= gauge_core_mask(v['dy'][k] - endpoint, v['h'][k], b.pts[current, 0], inner)
                    kept = k[keep]
                observed.append(dict(result=bool(arg), executed_locals=sorted(v), size=b.size.tolist(),
                    total_points=len(b.idx), current_rail_points=len(k), interval=interval,
                    robust_points=len(kept), robust_voxels=int(np.unique(v['inv'][kept]).size) if len(kept) else 0,
                    robust_span=float(np.ptp(v['h'][kept])) if len(kept) else 0.,
                    target_sample=xyz[fi][:6].tolist(), h_span=[float(v['h'][b.idx].min()), float(v['h'][b.idx].max())],
                    lateral_span=[float(v['dy'][b.idx].min()), float(v['dy'][b.idx].max())]))

            if detector._previous_latency_ms is not None:
                detector._previous_latency_ms = 42.
            if mode == 'traced':
                sys.setprofile(profile)
            try:
                result = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            finally:
                sys.setprofile(None)
            row = dict(i=i, distance=x, result=normalize(result.to_dict())[0],
                       hit=any(abs(d.distance - x) < 1 and abs(d.center[1] - lateral) < .5 for d in result.detections))
            if mode == 'traced':
                row.update(predicates=observed, track=result.track.to_dict(),
                    candidates=[dict(reason=c.reason, core=c.collision_core, distance=c.distance,
                                     lateral=c.lateral, height=[c.height_min, c.height_max]) for c in result.candidates],
                    xyz_sha256=hashlib.sha256(xyz.tobytes()).hexdigest(), object_points=int((labels == 1).sum()))
            saved.append(row)
        runs[mode] = saved
    assert all(a['result'] == b['result'] and a['hit'] == b['hit']
               for a, b in zip(runs['plain'], runs['traced'], strict=True))
    return dict(distance=distance, lateral=lateral, top=top, moving=moving, plain_traced_equal=True, rows=runs['traced'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cases = []
    for distance in [67., 109., 137.]:
        for lateral in [-.68, .68]:
            for top in [2.72, 3.22, 4.12]:
                case = run_case(distance, lateral, top)
                cases.append(case)
                print(distance, lateral, top, sum(r['hit'] for r in case['rows']), case['rows'][-1]['predicates'], flush=True)
    for lateral in [-.68, .68]:
        case = run_case(155., lateral, 4.12, moving=True)
        cases.append(case)
        for row in case['rows']:
            if row['distance'] >= 90 or row['hit']:
                print('moving', lateral, round(row['distance'], 1), row['hit'], row['predicates'], flush=True)
    with args.out.open('x') as stream:
        json.dump(dict(cases=cases), stream, indent=2)


if __name__ == '__main__':
    main()
