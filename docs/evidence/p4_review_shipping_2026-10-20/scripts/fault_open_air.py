"""Review A finding 1 (L16/S3): the dataset's full-revolution Pandar mount (valid returns -104..+106 deg, DATASET.md), correct
configured mapping (-y/+x/+z handled upstream: cloud given in the vehicle frame), starting in OPEN AIR
(bed, rails, ground, masts every 60 m). 450 frames, zero tilt; then the same with a tunnel start (control).
Runs on any checkout (before L16/S3 the cue is reported as n/a):
    PYTHONPATH=<checkout> python fault_open_air.py <checkout>"""
import sys, numpy as np
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import rays, cast, frame
from resense import Detector, DetectorConfig
from resense.frame import Frame
try:
    from resense.calibration import directional_axes
except ImportError:                 # before L16/S3
    directional_axes = lambda p: "n/a"
sys.path.insert(0, sys.argv[1] + "/ros2_ws/src/resense_ros")
from resense_ros.decision_policy import evaluate_decision
d, ring = rays(-104, 106)
for start in ("open", "tunnel"):
    f, _ = frame(d, ring, *cast(d, tunnel=start == "tunnel", open_air=start == "open"))
    print(start, "n=", len(f.xyz), "frac above sensor=%.4f" % np.mean(f.xyz[:, 2] > 0), "frac behind=%.3f" % np.mean(f.xyz[:, 0] < 0),
          "directional_axes=", directional_axes(f.xyz))
    det = Detector(DetectorConfig())
    dec = {}
    for i in range(450):
        res = det.process(Frame(xyz=f.xyz.copy(), intensity=f.intensity.copy(), ring=f.ring.copy(), stamp=0.1 * i, frame_id="s"))
        w = evaluate_decision(res).decision
        dec[w] = dec.get(w, 0) + 1
    m = res.mount
    print(f"   decisions over 450 frames: {dec}; final status={m['status']} confirmed={m['orientation_confirmed']} "
          f"conflict={m['orientation_conflict']} msg={m['message'][:60]!r}")
