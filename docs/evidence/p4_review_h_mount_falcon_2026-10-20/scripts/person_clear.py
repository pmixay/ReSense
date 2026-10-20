"""The Falcon clear-distance model against the person, the recording's known real object (P4, 20.10).

For every dumped frame (falcon_trace.py dumps of the shipped run): where the raw returns put something on the
track near the train (as near_person.py: |Y| < 1.2 m, 1.5-20 m ahead, 0.2-2.2 m above the calibrated mount plane;
at least ``--min`` returns), its nearest X, against the shipped run's decision and detections and the clear
distance the ROS node would report in its non-legacy (conservative) path, with the model on (falcon_prime) and off
(unknown), from falcon_pair.py's ``.c.jsonl``. A frame *overstates* when the reported clear distance is beyond the
nearest such return while the frame is not STOP.

    person_clear.py <dump dir> <pair prefix> [--plane -1.772] [--min 100]
"""
import argparse
import glob
import json
import os
import re

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("dump")
ap.add_argument("pair")
ap.add_argument("--plane", type=float, default=-1.772)
ap.add_argument("--min", type=int, default=100)
a = ap.parse_args()
on = [json.loads(line) for line in open(a.pair + ".on.jsonl")]
c = [json.loads(line) for line in open(a.pair + ".c.jsonl")]
over = []
for p in sorted(glob.glob(os.path.join(a.dump, "f*.npz"))):
    i = int(re.search(r"f(\d+)", os.path.basename(p)).group(1))
    xyz = np.load(p)["xyz"].astype(np.float64)
    hp = xyz[:, 2] - a.plane
    m = (xyz[:, 0] > 1.5) & (xyz[:, 0] < 20.0) & (np.abs(xyz[:, 1]) < 1.2) & (hp > 0.2) & (hp < 2.2)
    r, cc = on[i], c[i]
    con, coff = cc["conservative.falcon_prime"]["clear"], cc["conservative.unknown"]["clear"]
    if m.sum() >= a.min:
        q = xyz[m]
        x_near = float(np.percentile(q[:, 0], 1))
        flag = r["decision"] != "STOP" and con > x_near
        over += [i] if flag else []
        what = (f"{int(m.sum())} returns at X {x_near:.1f}..{q[:, 0].max():.1f} (p1..max), Y {q[:, 1].min():+.2f}..{q[:, 1].max():+.2f}, "
                f"up to {hp[m].max():.2f} m above the plane")
    else:
        what, flag = f"{int(m.sum())} returns in the band", False
    print(f"frame {i}: {r['decision']}; dets {[(d['d'], d['lat']) for d in r['dets']]}; {what}; clear: detector {cc['detector_clear']}, "
          f"node conservative model on {con} / off {coff}{'  OVERSTATES' if flag else ''}")
print(f"frames that overstate (not STOP, model-on clear beyond the nearest return on the track): {len(over)} {over}")
