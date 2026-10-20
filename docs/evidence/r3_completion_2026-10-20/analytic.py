"""Physical B2/B3 scenes, full payloads and actual tracker return tracing."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts'))
import raycast as rc  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.synthetic import effective_thickness  # noqa: E402


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def scene(kind, distance, motion, speed_known, enabled=True, lateral=0., trace=False):
    cfg = DetectorConfig()
    if not enabled:
        cfg.tracking.cable_confirm_time_s = 0.
    detector = Detector(cfg)
    rows = []
    events = []

    def observe(frame, event, arg):
        if (event == 'return' and frame.f_code.co_filename.endswith('/resense/tracking.py')
                and frame.f_code.co_name in ('_cable_kind', '_cable_confirmed', '_carried_along', '_qualifies')):
            events.append(dict(function=frame.f_code.co_name, line=frame.f_lineno, returned=arg))
        return observe

    for k in range(18):
        x = distance + dict(approach=-1., carried=0., recede=1.)[motion] * 10. * .1 * k
        # The original B2 uses 15 m/s, not the B3 approach's 10 m/s.
        speed = 15. if distance < 40. else 10.
        if motion == 'approach':
            x = distance - speed * .1 * k
        width = effective_thickness(.03, x)
        y = rc.AY + lateral
        bottom = rc.FLOOR + .18 + (2.7 if kind == 'hanging' else .2)
        box = (x, x + width, y - width / 2, y + width / 2, bottom, rc.AZ + rc.R + .5)
        boxes = [] if kind == 'empty' else [box]
        frame = rc.frame(boxes=boxes, seed=k, stamp=.1 * k)
        events.clear()
        if trace:
            sys.settrace(observe)
        try:
            result = detector.process(frame, ego_speed=speed if speed_known else None)
        finally:
            sys.settrace(None)
        near = [t for t in detector.tracker.tracks if t.last is not None and abs(t.last.distance - x) < 1.5]
        snapshots = []
        for t in near:
            snapshots.append({**{key: getattr(t, key) for key in
                ('id', 'hits', 'misses', 'span_s', 'confidence', 'zone', 'reported', 'stop_earned',
                 'cable_kind', 'cable_hits', 'cable_span_s', 'fresh_blocked', 'column_hist',
                 'explained_hist', 'clean_run', 'odo')},
                'carried_along': detector.tracker._carried_along(t),
                'cluster': asdict(t.last)})
        # Count raw returns near the known physical box, before calibration.
        xyz = frame.xyz
        physical = ((xyz[:, 0] >= box[0] - .1) & (xyz[:, 0] <= box[1] + .1)
                    & (xyz[:, 1] >= box[2] - .1) & (xyz[:, 1] <= box[3] + .1)
                    & (xyz[:, 2] >= box[4] - .1) & (xyz[:, 2] <= box[5] + .1))
        rows.append(dict(frame=k, box=boxes, xyz_sha256=hashlib.sha256(xyz.tobytes()).hexdigest(),
                         physical_points=xyz[physical].tolist(), result=result.to_dict(),
                         tracks=snapshots, trace=list(events),
                         matched=any(abs(d.distance - x) < 1. for d in result.detections)))
    return dict(kind=kind, distance=distance, motion=motion, speed_known=speed_known,
                enabled=enabled, lateral=lateral, rows=rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    cases = {}
    for kind in ('tall', 'hanging'):
        for distance in (30., 37.):
            for motion in ('carried', 'approach'):
                for enabled in (False, True):
                    name = f'{kind}-{distance:g}-{motion}-{"on" if enabled else "off"}'
                    cases[name] = scene(kind, distance, motion, True, enabled)
    for motion in ('approach', 'carried', 'recede'):
        for known in (False, True):
            for enabled in (False, True):
                name = f'tall-80-{motion}-{"known" if known else "unknown"}-{"on" if enabled else "off"}'
                cases[name] = scene('tall', 80., motion, known, enabled)
    for kind in ('tall', 'hanging'):
        cases[f'{kind}-outside'] = scene(kind, 37., 'carried', True, lateral=2.)
    cases['empty'] = scene('empty', 37., 'carried', True)
    cases['trace-control'] = scene('tall', 80., 'approach', True, trace=True)
    with a.out.open('x') as stream:
        json.dump(dict(cases=cases), stream, default=serial)
    print(json.dumps({name: [r['frame'] for r in value['rows'] if r['matched']]
                      for name, value in cases.items()}, indent=2))


if __name__ == '__main__':
    main()
