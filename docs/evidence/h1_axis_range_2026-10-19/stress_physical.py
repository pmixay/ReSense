"""Pre-registered beam-phase, asymmetric-wall and off-centre-rail scenes."""
import json
import runpy

import numpy as np

from resense.clustering import FrameRays
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from run_checks import ROOT, HERE, archived

cast = runpy.run_path(str(ROOT / 'tests/fixtures/h1_physical.py'))['physical_column']


def main():
    source = archived.sources(ROOT)
    cases = [(dict(azimuth_phase=phase), side) for phase in [-.049, 0., .049] for side in [-.68, .68]]
    cases += [(dict(wall_left=3.25, wall_right=-1.85, rail_center=center), side)
              for center in [-.25, .25] for side in [-.68, .68]]
    report = dict(source_sha256=source, cases=[])
    for geometry, lateral in cases:
        center = geometry.get('rail_center', 0.)
        detector = Detector(DetectorConfig())
        rows = []
        for i in range(56):
            distance = 155 - 2.2 * i
            xyz, ring, labels = cast(distance=distance, lateral=center + lateral, top=4.12, rails=True, **geometry)
            if detector._previous_latency_ms is not None:
                detector._previous_latency_ms = 42.
            result = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            true_axis = detector.mount_rotation @ np.array([distance, center, -1.83])
            true_body = detector.mount_rotation @ np.array([distance, center + lateral, .23])
            detections = [dict(distance=float(d.distance), center=list(map(float, d.center))) for d in result.detections]
            hit = any(abs(d['distance'] - true_body[0]) < 1 and abs(d['center'][1] - true_body[1]) < .5 for d in detections)
            row = dict(i=i, distance=distance, hit=hit, detections=detections,
                object_returns=int((labels == 1).sum()), true_axis=true_axis.tolist(),
                model_axis=float(result.track.center_y(true_axis[0])), track=result.track.to_dict(),
                mount_rotation=detector.mount_rotation.tolist())
            # One scan in five checks interval coverage of the independently
            # specified world axis in exactly the detector's processed coordinates.
            if i % 5 == 0:
                rays = FrameRays(detector._frame_xyz, detector._frame_ring, detector._frame_hd[1],
                                 detector._frame_hd[0], result.track, detector.cfg.track)
                interval = rays.collision_axis_interval(float(true_axis[0]))
                row.update(interval=interval, anchor=rays.collision_axis_anchor(),
                           true_residual=float(true_axis[1] - row['model_axis']),
                           covered=bool(interval is not None and interval[0] <= true_axis[1] - row['model_axis'] <= interval[1]))
            rows.append(row)
        continuous = next((r['distance'] for j, r in enumerate(rows) if all(s['hit'] for s in rows[j:])), None)
        report['cases'].append(dict(geometry=geometry, lateral_from_rails=lateral, rows=rows,
            first=next((r['distance'] for r in rows if r['hit']), None), continuous_from=continuous,
            missed_at_or_below_100=[r['distance'] for r in rows if r['distance'] <= 100 and not r['hit']],
            interval_checks=sum('covered' in r for r in rows), uncovered=[r['i'] for r in rows if 'covered' in r and not r['covered']]))
        print('STRESS', geometry, lateral, {k: report['cases'][-1][k] for k in
              ['first', 'continuous_from', 'missed_at_or_below_100', 'uncovered']}, flush=True)
    assert source == archived.sources(ROOT)
    report['source_unchanged'] = True
    with (HERE / 'stress-d.json').open('x') as stream:
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
