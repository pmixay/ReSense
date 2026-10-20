"""Paired E versus retained D physical scenes and repeated stationary trials."""
import json
import argparse
from pathlib import Path
import runpy

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-reference')
helpers = runpy.run_path(str(ROOT / 'tests/test_column_collision_core.py'))
cast, matched, stop = (helpers[n] for n in ['physical_column', 'matched', 'stop_history'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, default=Path('/tmp/opencode/h1-axis-range/physical-audit-d.json'))
    parser.add_argument('--out', type=Path, default=HERE / 'physical-e.json')
    args_cli = parser.parse_args()
    previous = json.loads(args_cli.baseline.read_text())
    report = dict(full=[], outside=[], moving=[])
    for case in previous['full']:
        args = {k: case[k] for k in ['distance', 'lateral', 'top', 'absorbing']}
        xyz, ring, labels = cast(**args)
        detector, rows = Detector(DetectorConfig()), []
        for i in range(14):
            result = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            detections = [d.to_dict() for d in result.detections]
            hit = any(abs(d['distance'] - case['distance']) < 1 and abs(d['center'][1] - case['lateral']) < .5 for d in detections)
            rows.append(dict(i=i, hit=hit, detections=detections, track=result.track.to_dict()))
        old, new = set(case['matched']), {r['i'] for r in rows if r['hit']}
        assert not old - new, (args, old - new)
        report['full'].append(dict(**args, old=sorted(old), matched=sorted(new), rows=rows))
        print('STATIC', args, len(old), '->', len(new), flush=True)
    for distance in [8., 17., 25., 37., 67., 109., 137.]:
        for lateral in [-1.29, 1.29, -1.5, 1.5]:
            for rails in [False, True]:
                xyz, ring, labels = cast(distance=distance, lateral=lateral, top=4.12, rails=rails)
                for error in [-.6, -.3, 0., .3, .6]:
                    cc = matched(xyz, ring, labels, axis_error=error)
                    core, detected = any(c.collision_core for c in cc), any(any(stop(c)) for c in cc)
                    report['outside'].append(dict(distance=distance, lateral=lateral, rails=rails, error=error,
                                                   core=core, stop=detected))
                    assert not core and not detected, report['outside'][-1]
    cases = [({}, lateral) for lateral in [-.68, .68]]
    cases += [(dict(azimuth_phase=phase), lateral) for phase in [-.049, 0., .049] for lateral in [-.68, .68]]
    cases += [(dict(wall_left=3.25, wall_right=-1.85, rail_center=center), lateral)
              for center in [-.25, .25] for lateral in [-.68, .68]]
    for geometry, lateral in cases:
        detector, rows = Detector(DetectorConfig()), []
        centre = geometry.get('rail_center', 0.)
        for i in range(56):
            distance = 155 - 2.2 * i
            xyz, ring, labels = cast(distance=distance, lateral=centre + lateral, top=4.12, **geometry)
            result = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            truth = detector.mount_rotation @ np.array([distance, centre + lateral, .23])
            detections = [d.to_dict() for d in result.detections]
            hit = any(abs(d['distance'] - truth[0]) < 1 and abs(d['center'][1] - truth[1]) < .5 for d in detections)
            rows.append(dict(i=i, distance=distance, hit=hit, detections=detections))
        continuous = next((r['distance'] for i, r in enumerate(rows) if all(s['hit'] for s in rows[i:])), None)
        assert all(r['hit'] for r in rows if r['distance'] <= 100), (geometry, lateral)
        report['moving'].append(dict(geometry=geometry, lateral=lateral, rows=rows, continuous_from=continuous))
        print('MOVING', geometry, lateral, continuous, flush=True)
    report['summary'] = dict(previous_matches=sum(len(c['old']) for c in report['full']),
        matched=sum(len(c['matched']) for c in report['full']), outside_cases=len(report['outside']),
        false_STOP=sum(r['stop'] for r in report['outside']), moving_cases=len(report['moving']))
    with args_cli.out.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(report['summary'], flush=True)


if __name__ == '__main__':
    main()
