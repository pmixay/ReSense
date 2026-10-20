import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
sys.path.insert(0, a.repo)
import resense.calibration as mod  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.frame import sensor_to_vehicle  # noqa: E402

cfg = DetectorConfig()
path = Path('/tmp/opencode/resense-b4-data/decoded/doubleT_obstacle/f_00050.npz')
with np.load(path) as d:
    xyz = sensor_to_vehicle(d['xyz'], cfg.sensor) @ mod.rot_z(np.pi / 2).T.astype(np.float32)
cal = mod.MountCalibrator(cfg.calibration, cfg.track)
calls = []
original = mod.observe_mount


def observe(points, *args, **kwargs):
    calls.append(len(points))
    return original(points, *args, **kwargs)


mod.observe_mount = observe
times = []
for _ in range(6):
    start = time.perf_counter()
    result = cal._search_orientation(xyz)
    times.append(1000 * (time.perf_counter() - start))
record = {'repo': a.repo, 'points': len(xyz), 'search_ms': times[1:],
          'median_ms': float(np.median(times[1:])), 'max_observation_points': max(calls),
          'calls_per_search': len(calls) // 6, 'winning_candidate': result[0] if result else None,
          'scope': 'Five repetitions after warmup, current shared 8-vCPU development VM, not idle 4-vCPU acceptance.'}
Path(a.out).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
