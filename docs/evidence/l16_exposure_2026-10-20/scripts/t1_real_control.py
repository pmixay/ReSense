"""Positive control for T1 on a real cloud: the first frame of a recording, decoded as the jury runner does
(fastcloud decode with the configured range limits, then R_vs), with its returns above the sensor (z > 0)
randomly thinned to a given share of all returns. directional_axes must give no cue on the untouched frame
(as the probe found) and (0, 0, -1) when the share drops below ~2 %: the probe's numbers then say how far
each real start is from the bug.

    RESENSE_REPO=<tree> python t1_real_control.py <bag dir or .db3>
"""
import os
import sys

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, ROOT + "/ros2_ws/src/resense_ros", ROOT + "/docs/evidence/judgement_2026-10-13/scripts"):
    sys.path.insert(0, p)
from judge_runner import NodeReplica, db3_files, iter_raw  # noqa: E402
from resense.calibration import directional_axes  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

rep = NodeReplica()
ts, topic, raw = next(iter_raw(db3_files(sys.argv[1])[0]))
msg = fastcloud.parse_pointcloud2(raw)
xyz_s, *_ = fastcloud.decode(fastcloud.packed(msg), rep.cfg.sensor.min_range, rep.cfg.sensor.max_range)
xyz = xyz_s @ rep.R_vs.T
above = xyz[:, 2] > 0
print(f"{sys.argv[1]} frame 0: {len(xyz)} returns, z>0 {above.mean():.4f}, x<0 {(xyz[:, 0] < 0).mean():.4f}")
rng = np.random.default_rng(0)
below, up = xyz[~above], xyz[above]
for share in (None, 0.10, 0.05, 0.03, 0.025, 0.02, 0.015, 0.01, 0.005, 0.002):
    if share is None:
        p = xyz
    else:
        m = int(round(share * len(below) / (1 - share)))
        p = np.concatenate([below, up[rng.choice(len(up), m, replace=False)]])
    f, u = directional_axes(p)
    print(f"  above share {'as recorded' if share is None else f'{share:.3f}':>11s}: z>0 {np.mean(p[:, 2] > 0):.4f} "
          f"x<0 {np.mean(p[:, 0] < 0):.4f} -> forward {None if f is None else f.tolist()}, "
          f"up {None if u is None else u.tolist()}")
