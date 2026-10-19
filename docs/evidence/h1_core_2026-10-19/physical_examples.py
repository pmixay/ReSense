"""Raw examples, independent NumPy boundary calculation and moving physical cases."""
import copy
import json
from pathlib import Path
import runpy
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from resense.clustering import FrameRays
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
helper = runpy.run_path(str(ROOT / 'tests/test_column_collision_core.py'))
cast, matched = helper['physical_column'], helper['matched']


def independent_interval(xyz, h, dy, x):
    proposals = [0.0]
    details = []
    for lo, hi in [(0.4, 1.4), (1.4, 2.4)]:
        for sign in [-1, 1]:
            bins = {}
            for px, py, ph in zip(xyz[:, 0], dy, h, strict=True):
                if 4 <= px < 250 and lo <= ph < hi and 1.4 < sign * py < 5:
                    bins.setdefault(int(np.floor(px / 2)), []).append(float(py))
            medians = {2 * b + 1: float(np.percentile(v, 50)) for b, v in bins.items() if len(v) >= 4}
            near = [v for station, v in medians.items() if 8 <= station <= 28]
            local = [v for station, v in medians.items() if abs(station - x) <= max(6, .16 * x)]
            if len(near) < 4 or len(local) < 2:
                return None, details
            a, b = float(np.median(near)), float(np.median(local))
            spread = max(abs(v - a) for v in near) + max(abs(v - b) for v in local) + .10
            proposals += [b - a - spread, b - a + spread]
            details.append(dict(height=[lo, hi], sign=sign, near_bins=len(near), local_bins=len(local),
                                near_median=a, local_median=b, spread=spread))
    return (min(proposals), max(proposals)), details


examples = []
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
for ax, distance, lateral in zip(axs, [67., 137., 67.], [.68, -.68, 1.29], strict=True):
    xyz, ring, labels = cast(distance=distance, lateral=lateral)
    obj = xyz[labels == 1]
    h, dy = xyz[:, 2] + 1.83, xyz[:, 1]
    cc = matched(xyz, ring, labels)
    row = dict(distance=distance, lateral=lateral, object_points=len(obj),
               raw_sample_xyz=obj[:8].tolist(), clusters=[])
    for c in cc:
        x = float(xyz[c.points_idx, 0].mean())
        direct, detail = independent_interval(xyz, h, dy, x)
        actual = FrameRays(xyz, ring, h, dy).collision_axis_interval(x)
        assert direct == actual
        row['clusters'].append(dict(zone=c.zone, reason=c.reason, core=c.collision_core,
                                    height=[c.height_min, c.height_max], voxels=c.n_gauge,
                                    independently_recomputed_interval=direct, profiles=detail))
    ax.scatter(obj[:, 1], obj[:, 2] + 1.83, s=10, label='all physical object returns')
    if cc:
        points = xyz[cc[0].points_idx]
        ax.scatter(points[:, 1], points[:, 2] + 1.83, s=5, label='candidate returns')
    for edge in [-1.05, 1.05]:
        ax.axvline(edge, color='red', linestyle='--')
    ax.axhline(3, color='grey', linestyle='--')
    status = 'outside: no STOP' if abs(lateral) - .23 > 1.05 else (
        'STOP eligible' if cc and cc[0].zone == 'gauge' else 'not fixed')
    ax.set(xlabel='true lateral [m]', ylabel='height above rail [m]', ylim=(0, 3.5),
           title=f'{distance:g} m, y={lateral:g}: ' + status)
    ax.legend(fontsize=7)
    examples.append(row)
    print('RAW', json.dumps(row))
fig.tight_layout()
if (HERE / 'physical-examples.png').exists() and not (HERE / 'physical-examples-first.png').exists():
    shutil.copy2(HERE / 'physical-examples.png', HERE / 'physical-examples-first.png')
fig.savefig(HERE / 'physical-examples.png', dpi=150)
plt.close(fig)

# Positive control: coherent boundary displacement must not disappear through averaging.
xyz, ring, labels = cast()
h, dy = xyz[:, 2] + 1.83, xyz[:, 1].copy()
move = (xyz[:, 0] > 40) & (np.abs(dy) > 1.4)
dy[move] += 0.7
expected, _ = independent_interval(xyz, h, dy, 67.)
actual = FrameRays(xyz, ring, h, dy).collision_axis_interval(67.)
assert expected == actual and actual is not None and actual[1] > .5

dynamic = []
for lateral in ([] if '--plots-only' in sys.argv else [-.68, .68]):
    for absorbing in [None, (2.54, 4.12)]:
        old, new = DetectorConfig(), DetectorConfig()
        old.cluster.column_core_margin = 0
        detectors = {'off': Detector(copy.deepcopy(old)), 'on': Detector(copy.deepcopy(new))}
        case = dict(lateral=lateral, top=4.12, absorbing=absorbing, speed_mps=22., dt_s=.1, rows=[])
        for i in range(56):
            distance = 155 - 2.2 * i
            xyz, ring, labels = cast(distance=distance, lateral=lateral, top=4.12,
                                     absorbing=absorbing, rails=True)
            row = dict(i=i, distance=distance, visible_rays=int((labels == 1).sum()))
            for side, d in detectors.items():
                r = d.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
                row[side] = dict(hit=any(abs(t.distance - distance) < 1 and abs(t.center[1] - lateral) < .5
                                         for t in r.detections),
                                 dets=[t.to_dict() for t in r.detections], track=r.track.to_dict())
            assert not row['off']['hit'] or row['on']['hit']
            case['rows'].append(row)
        dynamic.append(case)
        print('MOVING', lateral, absorbing, 'first',
              {s: next((r['distance'] for r in case['rows'] if r[s]['hit']), None) for s in ['off', 'on']})
name = 'physical-examples-plot-audit.json' if '--plots-only' in sys.argv else 'physical-examples.json'
with (HERE / name).open('x') as f:
    json.dump(dict(examples=examples, boundary_displacement_positive_control=actual, moving_cases=dynamic), f, indent=2)
