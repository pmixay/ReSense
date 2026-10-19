"""Read-only P3 startup evidence audit; no detector changes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--repo', default='/home/aiops/resense')
p.add_argument('--cache', required=True)
p.add_argument('--frames', default='0,1,50,100')
p.add_argument('--out', required=True)
a = p.parse_args()
sys.path.insert(0, a.repo)
from resense.frame import sensor_to_vehicle  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.calibration import MountCalibrator, observe_mount, orientation_candidates  # noqa: E402

cfg = DetectorConfig()
cache = Path(a.cache)
meta = json.loads((cache / 'meta.json').read_text())
rows = []
for i in map(int, a.frames.split(',')):
    path = cache / f'f_{i:05d}.npz'
    with np.load(path) as d:
        xyz = sensor_to_vehicle(d['xyz'], cfg.sensor)
    sample = xyz[::max(1, int(np.ceil(len(xyz) / 16384)))].astype(float)
    unit = sample / np.linalg.norm(sample, axis=1)[:, None]
    fractions = (unit > 0).mean(axis=0)
    best = int(np.argmax(np.maximum(fractions, 1 - fractions)))
    sign = 1 if fractions[best] > .5 else -1
    forward = unit[:, best] * sign
    angles = np.degrees(np.arctan2(unit[:, [j for j in range(3) if j != best]], forward[:, None]))
    row = {'frame': i, 'points': len(xyz), 'has_ring': meta[i]['has_ring'],
           'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'positive_fraction': fractions.tolist(), 'forward_axis': best, 'forward_sign': sign,
           'transverse_angles_q': np.percentile(angles, [1, 2, 10, 50, 90, 98, 99], axis=0).tolist()}
    if i == 0:
        row['observations'] = []
        for k in (0, 4, 5):
            rot = orientation_candidates()[k]
            cloud = xyz @ rot.T
            ob = observe_mount(cloud, cfg.track)
            cal = MountCalibrator(cfg.calibration, cfg.track)
            cal.update(cloud, cloud, None)
            row['observations'].append({'rotation': k, 'observation': vars(ob),
                                        'accepted': cal._config_passed, 'mount': cal.state.to_dict(),
                                        'forward_evidence': (cal._forward_axis.tolist()
                                                             if getattr(cal, '_forward_axis', None) is not None else None),
                                        'up_evidence': (cal._directional_up.tolist()
                                                        if getattr(cal, '_directional_up', None) is not None else None)})
    rows.append(row)
Path(a.out).write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
