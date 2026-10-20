"""Original P4 ray-cast A1, tunnel control and a real-size positive obstacle."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np
import resense
from resense import Detector, DetectorConfig
from resense.frame import Frame
import resense.calibration as cal

ROOT = Path(os.environ['RESENSE_REPO']).resolve()
assert Path(resense.__file__).resolve().parent == ROOT / 'resense'
sys.path.insert(0, str(ROOT / 'ros2_ws/src/resense_ros'))
from resense_ros.decision_policy import evaluate_decision  # noqa: E402


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in ('timing_ms', 'latency_p95_ms')}
    if isinstance(value, list):
        return [clean(v) for v in value if not (isinstance(v, str) and v.startswith('latency p95 '))]
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--trace', action='store_true')
    a = p.parse_args()
    path = ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts/scene.py'
    spec = importlib.util.spec_from_file_location('a1_original_scene', path)
    scene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene)
    rays, ring = scene.rays(-104, 106)
    report = {'repo': str(ROOT), 'scene_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'cases': {}}
    for case in (('open',) if a.trace else ('open', 'tunnel', 'positive')):
        frame, _ = scene.frame(rays, ring, *scene.cast(
            rays, tunnel=case == 'tunnel', open_air=case != 'tunnel',
            specs=[(40., 0., .45, 1.7)] if case == 'positive' else ()))
        detector, rows = Detector(DetectorConfig()), []
        for i in range(450):
            lines = []
            def trace(f, event, arg):
                if f.f_code.co_filename == cal.__file__ and f.f_code.co_name in ('directional_axes', 'update', '_finish'):
                    if event == 'line':
                        lines.append([f.f_code.co_name, f.f_lineno])
                    return trace
                return None
            if a.trace:
                sys.settrace(trace)
            try:
                result = detector.process(Frame(frame.xyz, frame.intensity, ring=frame.ring,
                                                stamp=.1 * i, frame_id='a1'))
            finally:
                sys.settrace(None)
            state = detector.calib
            row = {'frame': i, 'decision': evaluate_decision(result).decision,
                   'result': clean(deepcopy(result.to_dict())),
                   'state': {'forward': None if state._forward_axis is None else state._forward_axis.tolist(),
                             'config_passed': state._config_passed, 'frozen': state.frozen,
                             'observations': len(state._obs)}}
            if a.trace:
                row['trace_lines'] = lines
            rows.append(row)
        cue = cal.directional_axes(frame.xyz)
        report['cases'][case] = {'xyz_sha256': hashlib.sha256(frame.xyz.tobytes()).hexdigest(),
            'points': len(frame.xyz), 'positive_fraction': (frame.xyz > 0).mean(axis=0).tolist(),
            'cue': [None if x is None else x.tolist() for x in cue],
            'raw_examples': frame.xyz[np.linspace(0, len(frame.xyz) - 1, 8, dtype=int)].tolist(), 'rows': rows}
        print(case, {v: sum(r['decision'] == v for r in rows) for v in ('GO', 'CAUTION', 'STOP', 'FAULT')}, flush=True)
    with a.out.open('x') as f:
        json.dump(report, f)


if __name__ == '__main__':
    main()
